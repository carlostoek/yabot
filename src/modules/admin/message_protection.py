"""
Message Protection System - Channel Administration Module

This module implements message protection functionality leveraging Telegram API patterns
as specified in Requirement 3.5.

The system handles:
- Telegram API message protection flags (protect_content=True for VIP)
- Message access restriction validation
- VIP content protection against forwarding and downloads
- Protection level management and metadata
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field
import uuid

from src.events.models import BaseEvent
from src.events.bus import EventBus
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient
    from aiogram import Bot
    from aiogram.types import Message


class ProtectionLevel(str, Enum):
    """
    Protection level enumeration
    """
    NONE = "none"
    FREE = "free"
    VIP_ONLY = "vip_only"
    ADMIN_ONLY = "admin_only"
    TIMED_ACCESS = "timed_access"
    PREMIUM = "premium"


class AccessResult(str, Enum):
    """
    Access validation result enumeration
    """
    GRANTED = "granted"
    DENIED = "denied"
    EXPIRED = "expired"
    INSUFFICIENT_LEVEL = "insufficient_level"
    UNAUTHORIZED = "unauthorized"


class MessageProtectionRule(BaseModel):
    """
    Protection rule configuration
    """
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    protection_level: ProtectionLevel
    rules: Dict[str, Any] = Field(default_factory=dict)
    applied_to: List[str] = Field(default_factory=list)  # channel_ids
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True

    def get_telegram_options(self) -> Dict[str, Any]:
        """
        Get Telegram API message options based on protection rules

        Returns:
            Dictionary with Telegram API options
        """
        options = {}

        # VIP content protection - ALWAYS apply protect_content=True for VIP
        if self.protection_level in [ProtectionLevel.VIP_ONLY, ProtectionLevel.PREMIUM]:
            options["protect_content"] = True

        # Disable web page preview for sensitive content
        if self.rules.get("disable_web_preview", False):
            options["disable_web_page_preview"] = True

        # Disable notification for low-priority content
        if self.rules.get("disable_notification", False):
            options["disable_notification"] = True

        return options


class MessageProtection(BaseModel):
    """
    Message protection record following the specification design
    """
    protection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str
    channel_id: str
    protection_level: ProtectionLevel
    access_conditions: Dict[str, Any] = Field(default_factory=dict)
    created_time: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    telegram_message_id: Optional[str] = None
    is_protected: bool = False  # Whether Telegram protect_content was applied

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: str
        }


class AccessValidationResult(BaseModel):
    """
    Result of message access validation
    """
    granted: bool
    result: AccessResult
    message_id: str
    user_id: str
    protection_level: ProtectionLevel
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageProtectionEvent(BaseEvent):
    """
    Event for message protection operations
    """
    event_type: str = "message_protection_applied"
    message_id: str
    channel_id: str
    protection_level: str
    user_id: Optional[str] = None


class MessageAccessEvent(BaseEvent):
    """
    Event for message access validation
    """
    event_type: str = "message_access_checked"
    message_id: str
    user_id: str
    access_granted: bool
    protection_level: str
    result: str


class MessageProtectionSystem:
    """
    Message protection system for VIP content and access control

    Implements requirement 3.5:
    - Applies Telegram API flags to restrict message access (protect_content=True)
    - Validates user access to protected messages
    - Manages VIP content protection against forwarding/downloads
    - Enforces protection rules and access conditions

    Critical: ALL VIP messages MUST use protect_content=True (non-negotiable rule)
    """

    def __init__(self, db_client: 'AsyncIOMotorClient', event_bus: EventBus, telegram_bot: 'Bot'):
        """
        Initialize the message protection system

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing protection events
            telegram_bot: Telegram bot instance for API operations
        """
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.telegram_bot = telegram_bot
        self.logger = get_logger(self.__class__.__name__)

        # Collection references
        self.message_protection_collection = self.db.message_protection
        self.protection_rules_collection = self.db.protection_rules
        self.access_log_collection = self.db.message_access_log

        # Initialize default protection rules
        # Note: This should be called asynchronously after initialization

    async def _initialize_protection_rules(self) -> None:
        """
        Initialize default protection rules following DianaBot requirements
        """
        try:
            default_rules = [
                MessageProtectionRule(
                    name="vip_content_protection",
                    protection_level=ProtectionLevel.VIP_ONLY,
                    rules={
                        "vip_content_protected": True,
                        "disable_forwarding": True,
                        "disable_download": True,
                        "require_vip_subscription": True,
                        "telegram_protect_content": True  # CRITICAL: Always true for VIP
                    }
                ),
                MessageProtectionRule(
                    name="admin_only_protection",
                    protection_level=ProtectionLevel.ADMIN_ONLY,
                    rules={
                        "admin_only": True,
                        "require_admin_role": True,
                        "telegram_protect_content": True
                    }
                ),
                MessageProtectionRule(
                    name="premium_protection",
                    protection_level=ProtectionLevel.PREMIUM,
                    rules={
                        "premium_content": True,
                        "disable_forwarding": True,
                        "require_premium_subscription": True,
                        "telegram_protect_content": True
                    }
                ),
                MessageProtectionRule(
                    name="timed_access_protection",
                    protection_level=ProtectionLevel.TIMED_ACCESS,
                    rules={
                        "time_limited": True,
                        "check_expiration": True,
                        "auto_revoke_expired": True
                    }
                ),
                MessageProtectionRule(
                    name="free_content",
                    protection_level=ProtectionLevel.FREE,
                    rules={
                        "public_access": True,
                        "no_restrictions": True
                    }
                )
            ]

            # Store rules in database
            for rule in default_rules:
                await self.protection_rules_collection.replace_one(
                    {"name": rule.name},
                    rule.dict(),
                    upsert=True
                )

            self.logger.info(f"Initialized {len(default_rules)} default protection rules")

        except Exception as e:
            self.logger.error(
                "Error initializing protection rules",
                error=str(e),
                error_type=type(e).__name__
            )

    async def protect_message(self, message_id: str, channel_id: str,
                            protection_level: ProtectionLevel,
                            access_conditions: Optional[Dict[str, Any]] = None,
                            expires_at: Optional[datetime] = None,
                            telegram_message_id: Optional[str] = None) -> bool:
        """
        Apply protection to a message

        Args:
            message_id: Internal message identifier
            channel_id: Channel ID where message was sent
            protection_level: Level of protection to apply
            access_conditions: Additional access conditions
            expires_at: Optional expiration time
            telegram_message_id: Telegram message ID if available

        Returns:
            True if protection was applied successfully
        """
        try:
            self.logger.info(
                "Applying message protection",
                message_id=message_id,
                channel_id=channel_id,
                protection_level=protection_level.value
            )

            # Get protection rule
            rule = await self._get_protection_rule(protection_level)
            if not rule:
                self.logger.error(f"Protection rule not found for level: {protection_level.value}")
                return False

            # Determine if Telegram protect_content should be applied
            is_protected = protection_level in [
                ProtectionLevel.VIP_ONLY,
                ProtectionLevel.PREMIUM,
                ProtectionLevel.ADMIN_ONLY
            ]

            # Create protection record
            protection = MessageProtection(
                message_id=message_id,
                channel_id=channel_id,
                protection_level=protection_level,
                access_conditions=access_conditions or {},
                expires_at=expires_at,
                telegram_message_id=telegram_message_id,
                is_protected=is_protected,
                metadata={
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "telegram_options_applied": rule.get_telegram_options()
                }
            )

            # Store protection record
            await self.message_protection_collection.insert_one(protection.dict())

            # Log protection application
            await self._log_protection_access(
                action="protection_applied",
                message_id=message_id,
                protection_level=protection_level.value,
                success=True,
                metadata={
                    "is_protected": is_protected,
                    "channel_id": channel_id
                }
            )

            # Publish protection event
            await self._publish_protection_event(
                message_id=message_id,
                channel_id=channel_id,
                protection_level=protection_level.value,
                event_type="message_protection_applied"
            )

            self.logger.info(
                "Message protection applied successfully",
                message_id=message_id,
                protection_level=protection_level.value,
                is_protected=is_protected
            )

            return True

        except Exception as e:
            self.logger.error(
                "Error applying message protection",
                message_id=message_id,
                channel_id=channel_id,
                protection_level=protection_level.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def check_message_access(self, user_id: str, message_id: str) -> AccessValidationResult:
        """
        Check if user has access to a protected message

        Args:
            user_id: User ID requesting access
            message_id: Message ID to check access for

        Returns:
            AccessValidationResult with validation details
        """
        try:
            self.logger.debug(
                "Checking message access",
                user_id=user_id,
                message_id=message_id
            )

            # Get message protection record
            protection_doc = await self.message_protection_collection.find_one({
                "message_id": message_id
            })

            if not protection_doc:
                # No protection record = free access
                result = AccessValidationResult(
                    granted=True,
                    result=AccessResult.GRANTED,
                    message_id=message_id,
                    user_id=user_id,
                    protection_level=ProtectionLevel.FREE,
                    reason="No protection applied"
                )

                await self._publish_access_event(user_id, message_id, True, "free", "granted")
                return result

            protection = MessageProtection(**protection_doc)

            # Check if protection has expired
            if protection.expires_at and datetime.utcnow() > protection.expires_at:
                # Protection expired
                result = AccessValidationResult(
                    granted=False,
                    result=AccessResult.EXPIRED,
                    message_id=message_id,
                    user_id=user_id,
                    protection_level=protection.protection_level,
                    reason="Protection expired",
                    expires_at=protection.expires_at
                )

                await self._log_access_attempt(user_id, message_id, False, "expired")
                await self._publish_access_event(user_id, message_id, False,
                                               protection.protection_level.value, "expired")
                return result

            # Validate access based on protection level
            access_granted = False
            result_type = AccessResult.DENIED
            reason = "Access denied"

            if protection.protection_level == ProtectionLevel.FREE:
                access_granted = True
                result_type = AccessResult.GRANTED
                reason = "Free access"

            elif protection.protection_level == ProtectionLevel.VIP_ONLY:
                # Check VIP subscription
                vip_status = await self._check_user_vip_status(user_id)
                if vip_status.get("is_vip", False):
                    access_granted = True
                    result_type = AccessResult.GRANTED
                    reason = "VIP access granted"
                else:
                    result_type = AccessResult.INSUFFICIENT_LEVEL
                    reason = "VIP subscription required"

            elif protection.protection_level == ProtectionLevel.ADMIN_ONLY:
                # Check admin role
                is_admin = await self._check_user_admin_status(user_id)
                if is_admin:
                    access_granted = True
                    result_type = AccessResult.GRANTED
                    reason = "Admin access granted"
                else:
                    result_type = AccessResult.UNAUTHORIZED
                    reason = "Admin privileges required"

            elif protection.protection_level == ProtectionLevel.PREMIUM:
                # Check premium subscription
                premium_status = await self._check_user_premium_status(user_id)
                if premium_status:
                    access_granted = True
                    result_type = AccessResult.GRANTED
                    reason = "Premium access granted"
                else:
                    result_type = AccessResult.INSUFFICIENT_LEVEL
                    reason = "Premium subscription required"

            elif protection.protection_level == ProtectionLevel.TIMED_ACCESS:
                # Check timed access conditions
                timed_access = await self._check_timed_access(user_id, protection.access_conditions)
                if timed_access.get("granted", False):
                    access_granted = True
                    result_type = AccessResult.GRANTED
                    reason = "Timed access granted"
                else:
                    result_type = AccessResult.EXPIRED
                    reason = "Timed access expired"

            # Log access attempt
            await self._log_access_attempt(user_id, message_id, access_granted, result_type.value)

            # Publish access event
            await self._publish_access_event(
                user_id=user_id,
                message_id=message_id,
                access_granted=access_granted,
                protection_level=protection.protection_level.value,
                result=result_type.value
            )

            result = AccessValidationResult(
                granted=access_granted,
                result=result_type,
                message_id=message_id,
                user_id=user_id,
                protection_level=protection.protection_level,
                reason=reason,
                expires_at=protection.expires_at,
                metadata={
                    "protection_id": protection.protection_id,
                    "is_telegram_protected": protection.is_protected
                }
            )

            self.logger.info(
                "Message access validation completed",
                user_id=user_id,
                message_id=message_id,
                access_granted=access_granted,
                result=result_type.value
            )

            return result

        except Exception as e:
            self.logger.error(
                "Error checking message access",
                user_id=user_id,
                message_id=message_id,
                error=str(e),
                error_type=type(e).__name__
            )

            # Return denied access on error
            return AccessValidationResult(
                granted=False,
                result=AccessResult.DENIED,
                message_id=message_id,
                user_id=user_id,
                protection_level=ProtectionLevel.NONE,
                reason=f"Access validation error: {str(e)}",
                metadata={"error": True}
            )

    async def get_protection_options(self, protection_level: ProtectionLevel) -> Dict[str, Any]:
        """
        Get Telegram API options for a protection level

        Args:
            protection_level: Protection level

        Returns:
            Dictionary with Telegram API options
        """
        try:
            rule = await self._get_protection_rule(protection_level)
            if rule:
                return rule.get_telegram_options()

            # Default fallback options
            if protection_level in [ProtectionLevel.VIP_ONLY, ProtectionLevel.PREMIUM, ProtectionLevel.ADMIN_ONLY]:
                return {"protect_content": True}

            return {}

        except Exception as e:
            self.logger.error(
                "Error getting protection options",
                protection_level=protection_level.value,
                error=str(e)
            )
            return {}

    async def revoke_message_protection(self, message_id: str) -> bool:
        """
        Revoke protection from a message

        Args:
            message_id: Message ID to revoke protection from

        Returns:
            True if revocation was successful
        """
        try:
            result = await self.message_protection_collection.delete_one({
                "message_id": message_id
            })

            if result.deleted_count > 0:
                await self._log_protection_access(
                    action="protection_revoked",
                    message_id=message_id,
                    success=True
                )

                self.logger.info(
                    "Message protection revoked",
                    message_id=message_id
                )
                return True
            else:
                self.logger.warning(
                    "No protection found to revoke",
                    message_id=message_id
                )
                return False

        except Exception as e:
            self.logger.error(
                "Error revoking message protection",
                message_id=message_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def update_protection_level(self, message_id: str, new_level: ProtectionLevel) -> bool:
        """
        Update protection level of a message

        Args:
            message_id: Message ID to update
            new_level: New protection level

        Returns:
            True if update was successful
        """
        try:
            # Get new protection rule
            rule = await self._get_protection_rule(new_level)
            if not rule:
                self.logger.error(f"Protection rule not found for level: {new_level.value}")
                return False

            # Determine new protection status
            is_protected = new_level in [
                ProtectionLevel.VIP_ONLY,
                ProtectionLevel.PREMIUM,
                ProtectionLevel.ADMIN_ONLY
            ]

            # Update protection record
            result = await self.message_protection_collection.update_one(
                {"message_id": message_id},
                {
                    "$set": {
                        "protection_level": new_level.value,
                        "is_protected": is_protected,
                        "updated_at": datetime.utcnow(),
                        "metadata.rule_id": rule.rule_id,
                        "metadata.rule_name": rule.name,
                        "metadata.telegram_options_applied": rule.get_telegram_options()
                    }
                }
            )

            if result.modified_count > 0:
                await self._log_protection_access(
                    action="protection_updated",
                    message_id=message_id,
                    protection_level=new_level.value,
                    success=True,
                    metadata={"new_level": new_level.value}
                )

                self.logger.info(
                    "Message protection level updated",
                    message_id=message_id,
                    new_level=new_level.value
                )
                return True
            else:
                self.logger.warning(
                    "No protection record found to update",
                    message_id=message_id
                )
                return False

        except Exception as e:
            self.logger.error(
                "Error updating protection level",
                message_id=message_id,
                new_level=new_level.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def get_protected_messages(self, channel_id: Optional[str] = None,
                                   protection_level: Optional[ProtectionLevel] = None) -> List[MessageProtection]:
        """
        Get protected messages with optional filtering

        Args:
            channel_id: Filter by channel ID
            protection_level: Filter by protection level

        Returns:
            List of protected messages
        """
        try:
            query = {}
            if channel_id:
                query["channel_id"] = channel_id
            if protection_level:
                query["protection_level"] = protection_level.value

            cursor = self.message_protection_collection.find(query).sort("created_time", -1)

            messages = []
            async for doc in cursor:
                # Convert ObjectId to string
                if "_id" in doc:
                    doc.pop("_id")

                message = MessageProtection(**doc)
                messages.append(message)

            return messages

        except Exception as e:
            self.logger.error(
                "Error getting protected messages",
                channel_id=channel_id,
                protection_level=protection_level.value if protection_level else None,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def cleanup_expired_protections(self) -> int:
        """
        Clean up expired message protections

        Returns:
            Number of expired protections cleaned up
        """
        try:
            current_time = datetime.utcnow()
            result = await self.message_protection_collection.delete_many({
                "expires_at": {"$lte": current_time}
            })

            if result.deleted_count > 0:
                self.logger.info(
                    "Cleaned up expired message protections",
                    count=result.deleted_count
                )

            return result.deleted_count

        except Exception as e:
            self.logger.error(
                "Error cleaning up expired protections",
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

    async def _get_protection_rule(self, protection_level: ProtectionLevel) -> Optional[MessageProtectionRule]:
        """
        Get protection rule for a level

        Args:
            protection_level: Protection level

        Returns:
            MessageProtectionRule if found, None otherwise
        """
        try:
            rule_doc = await self.protection_rules_collection.find_one({
                "protection_level": protection_level.value,
                "active": True
            })

            if rule_doc:
                return MessageProtectionRule(**rule_doc)
            return None

        except Exception as e:
            self.logger.error(
                "Error getting protection rule",
                protection_level=protection_level.value,
                error=str(e)
            )
            return None

    async def _check_user_vip_status(self, user_id: str) -> Dict[str, Any]:
        """
        Check user VIP status

        Args:
            user_id: User ID

        Returns:
            Dictionary with VIP status information
        """
        try:
            # Check with subscription service
            try:
                from src.services.subscription import SubscriptionService
                from src.database.manager import DatabaseManager

                db_manager = DatabaseManager(self.db.client)
                subscription_service = SubscriptionService(db_manager)
                is_vip = await subscription_service.check_subscription_status(user_id)
            except Exception:
                # Fallback: check directly from database
                subscription = await self.db.subscriptions.find_one({
                    "user_id": user_id,
                    "status": "active"
                })
                is_vip = subscription is not None

            return {
                "is_vip": is_vip,
                "checked_at": datetime.utcnow()
            }

        except Exception as e:
            self.logger.error(
                "Error checking VIP status",
                user_id=user_id,
                error=str(e)
            )
            return {"is_vip": False}

    async def _check_user_admin_status(self, user_id: str) -> bool:
        """
        Check if user has admin status

        Args:
            user_id: User ID

        Returns:
            True if user is admin
        """
        try:
            user_doc = await self.db.users.find_one({"user_id": user_id})
            if user_doc:
                return user_doc.get("role") == "admin"
            return False

        except Exception as e:
            self.logger.error(
                "Error checking admin status",
                user_id=user_id,
                error=str(e)
            )
            return False

    async def _check_user_premium_status(self, user_id: str) -> bool:
        """
        Check if user has premium status

        Args:
            user_id: User ID

        Returns:
            True if user has premium access
        """
        try:
            # For now, treat premium same as VIP
            vip_status = await self._check_user_vip_status(user_id)
            return vip_status.get("is_vip", False)

        except Exception as e:
            self.logger.error(
                "Error checking premium status",
                user_id=user_id,
                error=str(e)
            )
            return False

    async def _check_timed_access(self, user_id: str, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check timed access conditions

        Args:
            user_id: User ID
            conditions: Access conditions

        Returns:
            Dictionary with timed access result
        """
        try:
            # Get user's timed access record
            access_doc = await self.db.timed_access.find_one({
                "user_id": user_id,
                "active": True
            })

            if not access_doc:
                return {"granted": False, "reason": "No timed access record"}

            expires_at = access_doc.get("expires_at")
            if expires_at and datetime.utcnow() > expires_at:
                return {"granted": False, "reason": "Timed access expired"}

            return {
                "granted": True,
                "expires_at": expires_at
            }

        except Exception as e:
            self.logger.error(
                "Error checking timed access",
                user_id=user_id,
                error=str(e)
            )
            return {"granted": False, "reason": "Error validating timed access"}

    async def _log_access_attempt(self, user_id: str, message_id: str, success: bool, result: str) -> None:
        """
        Log message access attempt

        Args:
            user_id: User ID
            message_id: Message ID
            success: Whether access was granted
            result: Access result
        """
        try:
            log_doc = {
                "user_id": user_id,
                "message_id": message_id,
                "success": success,
                "result": result,
                "timestamp": datetime.utcnow()
            }

            await self.access_log_collection.insert_one(log_doc)

        except Exception as e:
            self.logger.error(
                "Error logging access attempt",
                user_id=user_id,
                message_id=message_id,
                error=str(e)
            )

    async def _log_protection_access(self, action: str, message_id: str, success: bool,
                                   protection_level: Optional[str] = None,
                                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log protection-related actions

        Args:
            action: Action performed
            message_id: Message ID
            success: Whether action was successful
            protection_level: Protection level
            metadata: Additional metadata
        """
        try:
            log_doc = {
                "action": action,
                "message_id": message_id,
                "success": success,
                "protection_level": protection_level,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow()
            }

            await self.access_log_collection.insert_one(log_doc)

        except Exception as e:
            self.logger.error(
                "Error logging protection action",
                action=action,
                message_id=message_id,
                error=str(e)
            )

    async def _publish_protection_event(self, message_id: str, channel_id: str,
                                      protection_level: str, event_type: str) -> None:
        """
        Publish protection-related events

        Args:
            message_id: Message ID
            channel_id: Channel ID
            protection_level: Protection level
            event_type: Type of event
        """
        try:
            event_payload = {
                "message_id": message_id,
                "channel_id": channel_id,
                "protection_level": protection_level,
                "timestamp": datetime.utcnow().isoformat()
            }

            event = BaseEvent(
                event_type=event_type,
                payload=event_payload
            )

            await self.event_bus.publish(event_type, event)

            self.logger.debug(
                "Protection event published",
                event_type=event_type,
                message_id=message_id,
                protection_level=protection_level
            )

        except Exception as e:
            self.logger.error(
                "Error publishing protection event",
                event_type=event_type,
                message_id=message_id,
                error=str(e),
                error_type=type(e).__name__
            )

    async def _publish_access_event(self, user_id: str, message_id: str, access_granted: bool,
                                  protection_level: str, result: str) -> None:
        """
        Publish access validation events

        Args:
            user_id: User ID
            message_id: Message ID
            access_granted: Whether access was granted
            protection_level: Protection level
            result: Access result
        """
        try:
            event_payload = {
                "user_id": user_id,
                "message_id": message_id,
                "access_granted": access_granted,
                "protection_level": protection_level,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }

            event = BaseEvent(
                event_type="message_access_checked",
                user_id=user_id,
                payload=event_payload
            )

            await self.event_bus.publish("message_access_checked", event)

            self.logger.debug(
                "Access event published",
                user_id=user_id,
                message_id=message_id,
                access_granted=access_granted
            )

        except Exception as e:
            self.logger.error(
                "Error publishing access event",
                user_id=user_id,
                message_id=message_id,
                error=str(e),
                error_type=type(e).__name__
            )

    async def get_protection_stats(self) -> Dict[str, int]:
        """
        Get message protection statistics

        Returns:
            Dictionary with protection statistics
        """
        try:
            stats = {}

            # Count messages by protection level
            for level in ProtectionLevel:
                count = await self.message_protection_collection.count_documents({
                    "protection_level": level.value
                })
                stats[f"protected_{level.value}"] = count

            # Count protected vs unprotected
            stats["telegram_protected"] = await self.message_protection_collection.count_documents({
                "is_protected": True
            })

            stats["total_protections"] = await self.message_protection_collection.count_documents({})

            return stats

        except Exception as e:
            self.logger.error(
                "Error getting protection stats",
                error=str(e),
                error_type=type(e).__name__
            )
            return {}