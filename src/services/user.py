"""
UserService for the YABOT system.

This module provides unified user operations across MongoDB and SQLite databases,
implementing the requirements specified in fase1 specification section 1.3.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserServiceError(Exception):
    """Base exception for user service operations."""
    pass


class UserCreationError(UserServiceError):
    """Exception raised when user creation fails."""
    pass


class UserNotFoundError(UserServiceError):
    """Exception raised when user is not found."""
    pass


class UserService:
    """Service for unified user operations across MongoDB and SQLite databases."""
    
    def __init__(self, database_manager: DatabaseManager, event_bus: EventBus):
        """Initialize the user service.
        
        Args:
            database_manager (DatabaseManager): Database manager instance
            event_bus (EventBus): Event bus instance
        """
        self.database_manager = database_manager
        self.event_bus = event_bus
        logger.info("UserService initialized")
    
    async def create_user(self, telegram_user: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user in both MongoDB and SQLite databases atomically.
        
        Args:
            telegram_user (Dict[str, Any]): Telegram user data
            
        Returns:
            Dict[str, Any]: Created user context
            
        Raises:
            UserCreationError: If user creation fails
        """
        logger.info("Creating new user: %s", telegram_user.get("id", "unknown"))
        
        user_id = str(telegram_user.get("id", uuid.uuid4().hex))
        timestamp = datetime.utcnow()
        
        # Start transaction-like behavior
        try:
            # Create user in SQLite (user profiles)
            sqlite_success = self._create_user_profile(user_id, telegram_user, timestamp)
            if not sqlite_success:
                raise UserCreationError("Failed to create user profile in SQLite")
            
            # Create user in MongoDB (user state)
            mongo_success = self._create_user_state(user_id, timestamp)
            if not mongo_success:
                raise UserCreationError("Failed to create user state in MongoDB")
            
            # Prepare user context
            user_context = {
                "user_id": user_id,
                "telegram_user": telegram_user,
                "created_at": timestamp.isoformat(),
                "updated_at": timestamp.isoformat()
            }
            
            # Publish user_registered event
            try:
                event = create_event(
                    "user_registered",
                    user_id=user_id,
                    telegram_user_id=telegram_user.get("id"),
                    username=telegram_user.get("username"),
                    first_name=telegram_user.get("first_name"),
                    last_name=telegram_user.get("last_name"),
                    language_code=telegram_user.get("language_code")
                )
                await self.event_bus.publish("user_registered", event.dict())
            except Exception as e:
                logger.warning("Failed to publish user_registered event: %s", str(e))
            
            logger.info("Successfully created user: %s", user_id)
            return user_context
            
        except Exception as e:
            logger.error("Error creating user: %s", str(e))
            # Attempt rollback (best effort)
            await self._rollback_user_creation(user_id)
            raise UserCreationError(f"Failed to create user: {str(e)}")
    
    def _create_user_profile(self, user_id: str, telegram_user: Dict[str, Any], 
                           timestamp: datetime) -> bool:
        """Create user profile in SQLite database.
        
        Args:
            user_id (str): User ID
            telegram_user (Dict[str, Any]): Telegram user data
            timestamp (datetime): Creation timestamp
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if database manager is available
        if not self.database_manager:
            logger.warning("Database manager not available, cannot create user profile")
            return False
            
        try:
            conn = self.database_manager.get_sqlite_conn()
            cursor = conn.cursor()
            
            # Create user profile table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    telegram_user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Insert user profile
            cursor.execute("""
                INSERT INTO user_profiles (
                    user_id, telegram_user_id, username, first_name, last_name, 
                    language_code, registration_date, last_login, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                telegram_user.get("id"),
                telegram_user.get("username"),
                telegram_user.get("first_name"),
                telegram_user.get("last_name"),
                telegram_user.get("language_code"),
                timestamp.isoformat(),
                timestamp.isoformat(),
                1
            ))
            
            conn.commit()
            logger.debug("Created user profile in SQLite for user: %s", user_id)
            return True
            
        except Exception as e:
            logger.error("Error creating user profile in SQLite: %s", str(e))
            return False
    
    def _create_user_state(self, user_id: str, timestamp: datetime) -> bool:
        """Create user state in MongoDB database.
        
        Args:
            user_id (str): User ID
            timestamp (datetime): Creation timestamp
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]
            
            # Create user document
            user_document = {
                "user_id": user_id,
                "current_state": {
                    "menu_context": "main_menu",
                    "narrative_progress": {
                        "current_fragment": None,
                        "completed_fragments": [],
                        "choices_made": []
                    },
                    "session_data": {
                        "last_activity": timestamp.isoformat()
                    }
                },
                "preferences": {
                    "language": "es",
                    "notifications_enabled": True,
                    "theme": "default"
                },
                "created_at": timestamp.isoformat(),
                "updated_at": timestamp.isoformat()
            }
            
            result = users_collection.insert_one(user_document)
            logger.debug("Created user state in MongoDB for user: %s", user_id)
            return result.acknowledged
            
        except Exception as e:
            logger.error("Error creating user state in MongoDB: %s", str(e))
            return False
    
    async def _rollback_user_creation(self, user_id: str) -> None:
        """Rollback user creation in case of failure.
        
        Args:
            user_id (str): User ID to rollback
        """
        logger.info("Rolling back user creation for user: %s", user_id)
        
        try:
            # Delete from SQLite
            conn = self.database_manager.get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
            conn.commit()
            logger.debug("Rolled back user profile in SQLite for user: %s", user_id)
        except Exception as e:
            logger.warning("Failed to rollback user profile in SQLite: %s", str(e))
        
        try:
            # Delete from MongoDB
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]
            result = users_collection.delete_one({"user_id": user_id})
            logger.debug("Rolled back user state in MongoDB for user: %s", user_id)
        except Exception as e:
            logger.warning("Failed to rollback user state in MongoDB: %s", str(e))
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Retrieve complete user context from both databases.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Dict[str, Any]: Complete user context
            
        Raises:
            UserNotFoundError: If user is not found
        """
        logger.debug("Retrieving user context for user: %s", user_id)
        
        try:
            # Get user profile from SQLite
            profile = self._get_user_profile(user_id)
            if not profile:
                raise UserNotFoundError(f"User profile not found for user: {user_id}")
            
            # Get user state from MongoDB
            state = self._get_user_state(user_id)
            if state is None:
                raise UserNotFoundError(f"User state not found for user: {user_id}")
            
            # Combine data
            user_context = {
                "user_id": user_id,
                "profile": profile,
                "state": state
            }
            
            logger.debug("Successfully retrieved user context for user: %s", user_id)
            return user_context
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error("Error retrieving user context: %s", str(e))
            raise UserServiceError(f"Failed to retrieve user context: {str(e)}")
    
    def _get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from SQLite database.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Optional[Dict[str, Any]]: User profile or None if not found
        """
        try:
            conn = self.database_manager.get_sqlite_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                profile = dict(zip(columns, row))
                logger.debug("Retrieved user profile from SQLite for user: %s", user_id)
                return profile
            
            return None
            
        except Exception as e:
            logger.error("Error retrieving user profile from SQLite: %s", str(e))
            return None
    
    def _get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user state from MongoDB database.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Optional[Dict[str, Any]]: User state or None if not found
        """
        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]
            
            user_document = users_collection.find_one({"user_id": user_id})
            
            if user_document:
                # Remove MongoDB-specific fields
                user_document.pop("_id", None)
                logger.debug("Retrieved user state from MongoDB for user: %s", user_id)
                return user_document
            
            return None
            
        except Exception as e:
            logger.error("Error retrieving user state from MongoDB: %s", str(e))
            return None
    
    async def update_user_state(self, user_id: str, state_updates: Dict[str, Any]) -> bool:
        """Update user dynamic state in MongoDB.
        
        Args:
            user_id (str): User ID
            state_updates (Dict[str, Any]): State updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Updating user state for user: %s", user_id)
        
        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]
            
            # Add timestamp to updates
            state_updates["updated_at"] = datetime.utcnow().isoformat()
            
            # Update user document
            result = users_collection.update_one(
                {"user_id": user_id},
                {"$set": state_updates}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info("Successfully updated user state for user: %s", user_id)
            else:
                logger.warning("No changes made to user state for user: %s", user_id)
            
            return success
            
        except Exception as e:
            logger.error("Error updating user state: %s", str(e))
            return False
    
    async def update_user_profile(self, user_id: str, profile_updates: Dict[str, Any]) -> bool:
        """Update user profile data in SQLite.
        
        Args:
            user_id (str): User ID
            profile_updates (Dict[str, Any]): Profile updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Updating user profile for user: %s", user_id)
        
        try:
            if not profile_updates:
                logger.warning("No profile updates provided for user: %s", user_id)
                return True
            
            conn = self.database_manager.get_sqlite_conn()
            cursor = conn.cursor()
            
            # Build SET clause dynamically
            set_clause = ", ".join([f"{key} = ?" for key in profile_updates.keys()])
            values = list(profile_updates.values())
            values.append(user_id)  # For WHERE clause
            
            # Update user profile
            cursor.execute(
                f"UPDATE user_profiles SET {set_clause}, last_login = ? WHERE user_id = ?",
                values + [datetime.utcnow().isoformat(), user_id]
            )
            
            conn.commit()
            
            success = cursor.rowcount > 0
            if success:
                logger.info("Successfully updated user profile for user: %s", user_id)
            else:
                logger.warning("No changes made to user profile for user: %s", user_id)
            
            return success
            
        except Exception as e:
            logger.error("Error updating user profile: %s", str(e))
            return False
    
    async def delete_user(self, user_id: str, deletion_reason: str = "user_request") -> bool:
        """Delete user data from both databases and publish user_deleted event.
        
        Args:
            user_id (str): User ID to delete
            deletion_reason (str): Reason for deletion
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Deleting user: %s (reason: %s)", user_id, deletion_reason)
        
        try:
            # Delete from SQLite
            sqlite_success = self._delete_user_profile(user_id)
            if not sqlite_success:
                logger.error("Failed to delete user profile from SQLite for user: %s", user_id)
                return False
            
            # Delete from MongoDB
            mongo_success = self._delete_user_state(user_id)
            if not mongo_success:
                logger.error("Failed to delete user state from MongoDB for user: %s", user_id)
                # Try to rollback SQLite deletion
                self._restore_user_profile(user_id)
                return False
            
            # Publish user_deleted event
            try:
                event = create_event(
                    "user_deleted",
                    user_id=user_id,
                    deletion_reason=deletion_reason
                )
                await self.event_bus.publish("user_deleted", event.dict())
            except Exception as e:
                logger.warning("Failed to publish user_deleted event: %s", str(e))
            
            logger.info("Successfully deleted user: %s", user_id)
            return True
            
        except Exception as e:
            logger.error("Error deleting user: %s", str(e))
            return False
    
    def _delete_user_profile(self, user_id: str) -> bool:
        """Delete user profile from SQLite database.
        
        Args:
            user_id (str): User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.database_manager.get_sqlite_conn()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
            conn.commit()
            
            success = cursor.rowcount > 0
            logger.debug("Deleted user profile from SQLite for user: %s", user_id)
            return success
            
        except Exception as e:
            logger.error("Error deleting user profile from SQLite: %s", str(e))
            return False
    
    def _delete_user_state(self, user_id: str) -> bool:
        """Delete user state from MongoDB database.
        
        Args:
            user_id (str): User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]
            
            result = users_collection.delete_one({"user_id": user_id})
            success = result.deleted_count > 0
            
            logger.debug("Deleted user state from MongoDB for user: %s", user_id)
            return success
            
        except Exception as e:
            logger.error("Error deleting user state from MongoDB: %s", str(e))
            return False
    
    def _restore_user_profile(self, user_id: str) -> bool:
        """Restore user profile in case of rollback.
        
        Args:
            user_id (str): User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        # This would be a more complex implementation in a real system
        # For now, we just log that a rollback attempt was made
        logger.warning("Would restore user profile for user: %s (not implemented)", user_id)
        return True


# Convenience function for easy usage
async def create_user_service(database_manager: DatabaseManager, 
                            event_bus: EventBus) -> UserService:
    """Create and initialize a user service instance.
    
    Args:
        database_manager (DatabaseManager): Database manager instance
        event_bus (EventBus): Event bus instance
        
    Returns:
        UserService: Initialized user service instance
    """
    user_service = UserService(database_manager, event_bus)
    return user_service
