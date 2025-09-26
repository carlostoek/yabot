"""
Access Control System - Channel Administration Module

This module implements access control functionality for validating user permissions
and channel access as specified in Requirement 3.1 and 3.5.

The system handles:
- User permission validation via Telegram API
- Channel access verification
- Access grant/revoke operations
- Event publishing for access operations
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel

from src.events.models import BaseEvent
from src.events.bus import EventBus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient
    from aiogram import Bot


class AccessLevel(str, Enum):
    """
    Enumeration for access levels
    """
    NONE = "none"
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"
    ADMIN = "admin"
    MODERATOR = "moderator"


class AccessResult(BaseModel):
    """
    Result of an access validation operation
    """
    granted: bool
    access_level: AccessLevel
    user_id: str
    channel_id: str
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class UserAccessEvent(BaseEvent):
    """
    Event for user access operations
    """
    event_type: str = "user_access_checked"
    user_id: str
    channel_id: str
    access_granted: bool
    access_level: str
    operation: str  # "validate", "grant", "revoke"
    expires_at: Optional[datetime] = None


class AccessControl:
    """
    Access control system for channel administration

    Implements requirements 3.1, 3.5:
    - 3.1: User access validation using Telegram API
    - 3.5: Channel access management and permission verification
    """

    def __init__(self, db_client: 'AsyncIOMotorClient', event_bus: EventBus, telegram_bot: 'Bot'):
        """
        Initialize the access control system

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing access events
            telegram_bot: Telegram bot instance for API calls
        """
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.telegram_bot = telegram_bot
        self.logger = get_logger(self.__class__.__name__)

        # Collection references
        self.users_collection = self.db.users
        self.access_control_collection = self.db.access_control
        self.channels_collection = self.db.channels

    async def validate_access(self, user_id: str, channel_id: str) -> AccessResult:
        """
        Validate user access to a specific channel

        Implements requirement 3.1: User access validation using Telegram API

        Args:
            user_id: User identifier
            channel_id: Channel identifier

        Returns:
            AccessResult with validation details
        """
        try:
            self.logger.debug(
                "Validating user access to channel",
                user_id=user_id,
                channel_id=channel_id
            )

            # First check database for stored access permissions
            access_doc = await self.access_control_collection.find_one({
                "user_id": user_id,
                "channel_id": channel_id
            })

            # Check if access has expired
            if access_doc and access_doc.get("expires_at"):
                if datetime.utcnow() > access_doc["expires_at"]:
                    # Access expired, revoke it
                    await self._revoke_expired_access(user_id, channel_id, access_doc["_id"])
                    access_doc = None

            # If we have valid database access, verify with Telegram API
            if access_doc:
                # Verify with Telegram API that user still has access
                telegram_access = await self._check_telegram_access(user_id, channel_id)

                if telegram_access["has_access"]:
                    access_level = AccessLevel(access_doc.get("access_level", "basic"))

                    # Publish access checked event
                    await self._publish_access_event(
                        user_id=user_id,
                        channel_id=channel_id,
                        access_granted=True,
                        access_level=access_level.value,
                        operation="validate",
                        expires_at=access_doc.get("expires_at")
                    )

                    self.logger.info(
                        "User access validated successfully",
                        user_id=user_id,
                        channel_id=channel_id,
                        access_level=access_level.value
                    )

                    return AccessResult(
                        granted=True,
                        access_level=access_level,
                        user_id=user_id,
                        channel_id=channel_id,
                        expires_at=access_doc.get("expires_at"),
                        metadata={
                            "source": "database",
                            "telegram_verified": True,
                            "granted_at": access_doc.get("granted_at"),
                            "granted_by": access_doc.get("granted_by")
                        }
                    )
                else:
                    # Telegram says no access, remove from database
                    await self.revoke_access(user_id, channel_id)

                    return AccessResult(
                        granted=False,
                        access_level=AccessLevel.NONE,
                        user_id=user_id,
                        channel_id=channel_id,
                        reason="Access revoked by Telegram API verification",
                        metadata={"source": "telegram_verification"}
                    )

            # No database access found, check directly with Telegram
            telegram_access = await self._check_telegram_access(user_id, channel_id)

            if telegram_access["has_access"]:
                # Determine access level based on Telegram role
                access_level = self._determine_access_level(telegram_access.get("status", "member"))

                # Store the access in database for future reference
                await self._store_access_record(
                    user_id=user_id,
                    channel_id=channel_id,
                    access_level=access_level,
                    source="telegram_api"
                )

                # Publish access event
                await self._publish_access_event(
                    user_id=user_id,
                    channel_id=channel_id,
                    access_granted=True,
                    access_level=access_level.value,
                    operation="validate"
                )

                self.logger.info(
                    "User access granted via Telegram API",
                    user_id=user_id,
                    channel_id=channel_id,
                    access_level=access_level.value
                )

                return AccessResult(
                    granted=True,
                    access_level=access_level,
                    user_id=user_id,
                    channel_id=channel_id,
                    metadata={
                        "source": "telegram_api",
                        "telegram_status": telegram_access.get("status"),
                        "auto_granted": True
                    }
                )
            else:
                # No access
                await self._publish_access_event(
                    user_id=user_id,
                    channel_id=channel_id,
                    access_granted=False,
                    access_level=AccessLevel.NONE.value,
                    operation="validate"
                )

                self.logger.info(
                    "User access denied",
                    user_id=user_id,
                    channel_id=channel_id,
                    reason="Not a channel member"
                )

                return AccessResult(
                    granted=False,
                    access_level=AccessLevel.NONE,
                    user_id=user_id,
                    channel_id=channel_id,
                    reason="User is not a member of the channel",
                    metadata={"source": "telegram_api"}
                )

        except Exception as e:
            self.logger.error(
                "Error validating user access",
                user_id=user_id,
                channel_id=channel_id,
                error=str(e),
                error_type=type(e).__name__
            )

            # In case of error, deny access
            return AccessResult(
                granted=False,
                access_level=AccessLevel.NONE,
                user_id=user_id,
                channel_id=channel_id,
                reason=f"Access validation error: {str(e)}",
                metadata={"error": True}
            )

    async def grant_access(self, user_id: str, channel_id: str, access_level: AccessLevel,
                          duration_hours: Optional[int] = None, granted_by: str = "system") -> bool:
        """
        Grant access to a user for a specific channel

        Args:
            user_id: User identifier
            channel_id: Channel identifier
            access_level: Level of access to grant
            duration_hours: Optional duration in hours (None for permanent)
            granted_by: Who granted the access

        Returns:
            True if access was granted successfully
        """
        try:
            expires_at = None
            if duration_hours:
                expires_at = datetime.utcnow() + timedelta(hours=duration_hours)

            access_doc = {
                "user_id": user_id,
                "channel_id": channel_id,
                "access_level": access_level.value,
                "granted_at": datetime.utcnow(),
                "granted_by": granted_by,
                "expires_at": expires_at,
                "active": True,
                "source": "manual_grant",
                "updated_at": datetime.utcnow()
            }

            # Use upsert to replace existing access record
            await self.access_control_collection.replace_one(
                {"user_id": user_id, "channel_id": channel_id},
                access_doc,
                upsert=True
            )

            # Publish access granted event
            await self._publish_access_event(
                user_id=user_id,
                channel_id=channel_id,
                access_granted=True,
                access_level=access_level.value,
                operation="grant",
                expires_at=expires_at
            )

            self.logger.info(
                "Access granted to user",
                user_id=user_id,
                channel_id=channel_id,
                access_level=access_level.value,
                expires_at=expires_at,
                granted_by=granted_by
            )

            return True

        except Exception as e:
            self.logger.error(
                "Error granting access to user",
                user_id=user_id,
                channel_id=channel_id,
                access_level=access_level.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def revoke_access(self, user_id: str, channel_id: str) -> bool:
        """
        Revoke user access to a specific channel

        Args:
            user_id: User identifier
            channel_id: Channel identifier

        Returns:
            True if access was revoked successfully
        """
        try:
            result = await self.access_control_collection.delete_one({
                "user_id": user_id,
                "channel_id": channel_id
            })

            if result.deleted_count > 0:
                # Publish access revoked event
                await self._publish_access_event(
                    user_id=user_id,
                    channel_id=channel_id,
                    access_granted=False,
                    access_level=AccessLevel.NONE.value,
                    operation="revoke"
                )

                self.logger.info(
                    "Access revoked for user",
                    user_id=user_id,
                    channel_id=channel_id
                )

                return True
            else:
                self.logger.warning(
                    "No access found to revoke",
                    user_id=user_id,
                    channel_id=channel_id
                )
                return False

        except Exception as e:
            self.logger.error(
                "Error revoking user access",
                user_id=user_id,
                channel_id=channel_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def get_user_access_list(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all channel access records for a user

        Args:
            user_id: User identifier

        Returns:
            List of access records for the user
        """
        try:
            cursor = self.access_control_collection.find(
                {"user_id": user_id, "active": True}
            ).sort("granted_at", -1)

            access_list = []
            async for doc in cursor:
                # Convert ObjectId to string
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                access_list.append(doc)

            return access_list

        except Exception as e:
            self.logger.error(
                "Error getting user access list",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def get_channel_users(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Get all users with access to a specific channel

        Args:
            channel_id: Channel identifier

        Returns:
            List of users with access to the channel
        """
        try:
            cursor = self.access_control_collection.find(
                {"channel_id": channel_id, "active": True}
            ).sort("granted_at", -1)

            users_list = []
            async for doc in cursor:
                # Convert ObjectId to string
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                users_list.append(doc)

            return users_list

        except Exception as e:
            self.logger.error(
                "Error getting channel users",
                channel_id=channel_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def cleanup_expired_access(self) -> int:
        """
        Clean up expired access records

        Returns:
            Number of expired records cleaned up
        """
        try:
            current_time = datetime.utcnow()
            result = await self.access_control_collection.delete_many({
                "expires_at": {"$lte": current_time},
                "active": True
            })

            if result.deleted_count > 0:
                self.logger.info(
                    "Cleaned up expired access records",
                    count=result.deleted_count
                )

            return result.deleted_count

        except Exception as e:
            self.logger.error(
                "Error cleaning up expired access",
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

    async def _check_telegram_access(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """
        Check user access via Telegram API

        Args:
            user_id: User identifier
            channel_id: Channel identifier

        Returns:
            Dictionary with access information from Telegram
        """
        try:
            # Use Telegram Bot API to get chat member information
            chat_member = await self.telegram_bot.get_chat_member(chat_id=channel_id, user_id=int(user_id))

            # Check member status
            has_access = chat_member.status in ["creator", "administrator", "member"]

            return {
                "has_access": has_access,
                "status": chat_member.status,
                "user_info": {
                    "is_chat_member": chat_member.status != "left",
                    "is_chat_admin": chat_member.status in ["creator", "administrator"],
                    "can_be_edited": getattr(chat_member, "can_be_edited", False),
                    "can_post_messages": getattr(chat_member, "can_post_messages", False),
                },
                "checked_at": datetime.utcnow()
            }

        except Exception as e:
            self.logger.error(
                "Error checking Telegram access",
                user_id=user_id,
                channel_id=channel_id,
                error=str(e),
                error_type=type(e).__name__
            )

            # If we can't check with Telegram, assume no access
            return {
                "has_access": False,
                "status": "unknown",
                "error": str(e),
                "checked_at": datetime.utcnow()
            }

    def _determine_access_level(self, telegram_status: str) -> AccessLevel:
        """
        Determine access level based on Telegram member status

        Args:
            telegram_status: Telegram member status

        Returns:
            Appropriate AccessLevel
        """
        status_to_level = {
            "creator": AccessLevel.ADMIN,
            "administrator": AccessLevel.MODERATOR,
            "member": AccessLevel.BASIC,
            "restricted": AccessLevel.BASIC,
            "left": AccessLevel.NONE,
            "kicked": AccessLevel.NONE
        }

        return status_to_level.get(telegram_status, AccessLevel.BASIC)

    async def _store_access_record(self, user_id: str, channel_id: str, access_level: AccessLevel, source: str) -> None:
        """
        Store access record in database

        Args:
            user_id: User identifier
            channel_id: Channel identifier
            access_level: Access level to store
            source: Source of the access grant
        """
        try:
            access_doc = {
                "user_id": user_id,
                "channel_id": channel_id,
                "access_level": access_level.value,
                "granted_at": datetime.utcnow(),
                "granted_by": "telegram_api",
                "expires_at": None,
                "active": True,
                "source": source,
                "updated_at": datetime.utcnow()
            }

            await self.access_control_collection.replace_one(
                {"user_id": user_id, "channel_id": channel_id},
                access_doc,
                upsert=True
            )

        except Exception as e:
            self.logger.error(
                "Error storing access record",
                user_id=user_id,
                channel_id=channel_id,
                error=str(e)
            )

    async def _revoke_expired_access(self, user_id: str, channel_id: str, access_id: str) -> None:
        """
        Revoke expired access record

        Args:
            user_id: User identifier
            channel_id: Channel identifier
            access_id: Access record ID
        """
        try:
            await self.access_control_collection.delete_one({"_id": access_id})

            # Publish revocation event
            await self._publish_access_event(
                user_id=user_id,
                channel_id=channel_id,
                access_granted=False,
                access_level=AccessLevel.NONE.value,
                operation="revoke"
            )

            self.logger.info(
                "Expired access revoked",
                user_id=user_id,
                channel_id=channel_id
            )

        except Exception as e:
            self.logger.error(
                "Error revoking expired access",
                user_id=user_id,
                channel_id=channel_id,
                error=str(e)
            )

    async def _publish_access_event(self, user_id: str, channel_id: str, access_granted: bool,
                                  access_level: str, operation: str,
                                  expires_at: Optional[datetime] = None) -> None:
        """
        Publish an access event to the event bus

        Args:
            user_id: User identifier
            channel_id: Channel identifier
            access_granted: Whether access was granted
            access_level: Access level
            operation: Type of operation (validate, grant, revoke)
            expires_at: Optional expiration time
        """
        try:
            event_payload = {
                "user_id": user_id,
                "channel_id": channel_id,
                "access_granted": access_granted,
                "access_level": access_level,
                "operation": operation,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "timestamp": datetime.utcnow().isoformat()
            }

            event = BaseEvent(
                event_type="user_access_checked",
                user_id=user_id,
                payload=event_payload
            )

            await self.event_bus.publish("user_access_checked", event)

            self.logger.debug(
                "Access event published",
                user_id=user_id,
                channel_id=channel_id,
                operation=operation,
                access_granted=access_granted
            )

        except Exception as e:
            self.logger.error(
                "Error publishing access event",
                user_id=user_id,
                channel_id=channel_id,
                operation=operation,
                error=str(e),
                error_type=type(e).__name__
            )