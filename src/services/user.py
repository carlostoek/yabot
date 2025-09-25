"""
Fase1 - Task 16
UserService for unified user operations

Implements unified user data operations across MongoDB and SQLite
as specified in Requirement 1.3: User CRUD Operations.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from src.database.manager import DatabaseManager
from src.events.models import UserRegistrationEvent, UserInteractionEvent
from src.utils.logger import LoggerMixin, get_logger


class UserStatus(str, Enum):
    """Enumeration for user status values"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class UserService(LoggerMixin):
    """
    Unified user data operations across MongoDB and SQLite
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        # LoggerMixin provides the logger property automatically
        
    async def create_user(self, telegram_user: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Create user in both databases atomically
        
        Args:
            telegram_user: Telegram user data from update
            
        Returns:
            Created user data or None if creation failed
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Creating new user", user_id=telegram_user.get("id"))
            
            # Prepare user data for both databases
            user_id = str(telegram_user["id"])
            
            # MongoDB user document (dynamic state)
            mongo_user_doc = {
                "user_id": user_id,
                "current_state": {
                    "menu_context": "main_menu",
                    "narrative_progress": {
                        "current_fragment": None,
                        "completed_fragments": [],
                        "choices_made": []
                    },
                    "session_data": {"last_activity": datetime.utcnow().isoformat()}
                },
                "preferences": {
                    "language": telegram_user.get("language_code", "es"),
                    "notifications_enabled": True,
                    "theme": "default"
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # SQLite user profile (for ACID compliance)
            sqlite_user_profile = {
                "user_id": user_id,
                "telegram_user_id": telegram_user["id"],
                "username": telegram_user.get("username"),
                "first_name": telegram_user.get("first_name"),
                "last_name": telegram_user.get("last_name"),
                "language_code": telegram_user.get("language_code"),
                "registration_date": datetime.utcnow(),
                "last_login": datetime.utcnow(),
                "is_active": True
            }
            
            # Create user in both databases (atomic operation)
            result = await self.db_manager.create_user_atomic(
                user_id, 
                mongo_user_doc, 
                sqlite_user_profile
            )
            
            if result:
                # Publish user registration event
                if event_bus:
                    event = UserRegistrationEvent(
                        user_id=user_id,
                        telegram_data=telegram_user
                    )
                    await event_bus.publish("user_registered", event.dict())
                
                self.logger.info("User created successfully", user_id=user_id)
                return {
                    "user_id": user_id,
                    "mongo_created": True,
                    "sqlite_created": True,
                    "profile": sqlite_user_profile
                }
            else:
                self.logger.error("Failed to create user atomically", user_id=user_id)
                return None

        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}", user_id=telegram_user.get("id"))
            raise
    
    async def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete user context combining data from both databases
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Complete user context or None if user not found
        """
        try:
            self.logger.debug("Retrieving user context", user_id=user_id)
            
            # Get user data from MongoDB (dynamic state)
            mongo_user = await self.db_manager.get_user_from_mongo(user_id)
            if not mongo_user:
                self.logger.warning("User not found in MongoDB", user_id=user_id)
                return None
            
            # Get user profile from SQLite
            sqlite_profile = await self.db_manager.get_user_profile_from_sqlite(user_id)
            if not sqlite_profile:
                self.logger.warning("User profile not found in SQLite", user_id=user_id)
                return None
            
            # Combine user context
            user_context = {
                "user_id": user_id,
                "mongo_data": mongo_user,
                "profile_data": sqlite_profile,
                "combined_context": {
                    **mongo_user,
                    "profile": sqlite_profile
                }
            }
            
            self.logger.info("User context retrieved successfully", user_id=user_id)
            return user_context
            
        except Exception as e:
            self.logger.error(f"Error retrieving user context: {str(e)}", user_id=user_id)
            raise
    
    async def update_user_state(self, user_id: str, new_state: Dict[str, Any], **kwargs) -> bool:
        """
        Update MongoDB dynamic state
        
        Args:
            user_id: Telegram user ID
            new_state: Updated user state
            
        Returns:
            True if update successful, False otherwise
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Updating user state", user_id=user_id)
            
            update_data = {
                "$set": {
                    "current_state": new_state,
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await self.db_manager.update_user_in_mongo(user_id, update_data)
            
            if result:
                # Publish user state update event
                if event_bus:
                    event = UserInteractionEvent(
                        user_id=user_id,
                        action="update_state",
                        context=new_state
                    )
                    await event_bus.publish("user_state_updated", event.dict())
                
                self.logger.info("User state updated successfully", user_id=user_id)
                return True
            else:
                self.logger.warning("Failed to update user state", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating user state: {str(e)}", user_id=user_id)
            raise
    
    async def update_user_profile(self, user_id: str, profile_updates: Dict[str, Any]) -> bool:
        """
        Update SQLite profile data
        
        Args:
            user_id: Telegram user ID
            profile_updates: Updated profile data
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            self.logger.info("Updating user profile", user_id=user_id)
            
            # Update profile in SQLite
            result = await self.db_manager.update_user_profile_in_sqlite(user_id, profile_updates)
            
            if result:
                self.logger.info("User profile updated successfully", user_id=user_id)
                return True
            else:
                self.logger.warning("Failed to update user profile", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating user profile: {str(e)}", user_id=user_id)
            raise
    
    async def get_user_subscription_status(self, user_id: str) -> Optional[str]:
        """
        Get user subscription status from SQLite
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Subscription status string or None
        """
        try:
            self.logger.debug("Retrieving user subscription status", user_id=user_id)
            
            subscription = await self.db_manager.get_subscription_from_sqlite(user_id)
            if subscription:
                status = subscription.get("status", "inactive")
                self.logger.info("Subscription status retrieved", user_id=user_id, status=status)
                return status
            else:
                self.logger.info("No subscription found", user_id=user_id)
                return "inactive"
                
        except Exception as e:
            self.logger.error(f"Error retrieving subscription status: {str(e)}", user_id=user_id)
            raise
    
    async def delete_user(self, user_id: str, **kwargs) -> bool:
        """
        Remove user from both databases and publish user_deleted event
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if deletion successful, False otherwise
        """
        event_bus = kwargs.get('event_bus')
        try:
            self.logger.info("Deleting user", user_id=user_id)
            
            # Delete from both databases
            mongo_deleted = await self.db_manager.delete_user_from_mongo(user_id)
            sqlite_deleted = await self.db_manager.delete_user_profile_from_sqlite(user_id)
            
            if mongo_deleted and sqlite_deleted:
                # Publish user deletion event
                if event_bus:
                    event_data = {
                        "event_type": "user_deleted",
                        "user_id": user_id,
                        "timestamp": datetime.utcnow(),
                    }
                    await event_bus.publish("user_deleted", event_data)
                
                self.logger.info("User deleted successfully", user_id=user_id)
                return True
            else:
                self.logger.warning(
                    "Partial user deletion", 
                    user_id=user_id, 
                    mongo_deleted=mongo_deleted, 
                    sqlite_deleted=sqlite_deleted
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting user: {str(e)}", user_id=user_id)
            raise

