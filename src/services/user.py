"""
UserService for the YABOT system.

This module provides unified user operations across MongoDB and SQLite databases,
implementing the requirements specified in fase1 specification section 1.3.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger
from src.ui.lucien_voice_generator import (
    LucienVoiceProfile, InteractionHistory, WorthinessProgression,
    BehavioralAssessment, RelationshipLevel, FormalityLevel,
    EvaluationMode, ProtectiveStance, SophisticationDisplay
)

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

    async def get_or_create_user_context(self, user_id: str, telegram_user: Dict[str, Any] = None) -> Dict[str, Any]:
        """Retrieve user context or create new user if not found.

        Args:
            user_id (str): User ID
            telegram_user (Dict[str, Any], optional): Telegram user data for creation

        Returns:
            Dict[str, Any]: Complete user context
        """
        logger.debug("Getting or creating user context for user: %s", user_id)

        try:
            # Try to get existing user context
            return await self.get_user_context(user_id)
        except UserNotFoundError:
            # User doesn't exist, create a new one
            logger.info("User not found, creating new user: %s", user_id)

            # Create minimal telegram_user data if not provided
            if telegram_user is None:
                telegram_user = {
                    "id": int(user_id),
                    "first_name": "Usuario",
                    "is_bot": False
                }

            # Create new user
            try:
                user_context = await self.create_user(telegram_user)
                logger.info("Successfully created new user context for: %s", user_id)
                return user_context
            except Exception as e:
                logger.error("Failed to create new user: %s", str(e))
                raise UserServiceError(f"Failed to create new user: {str(e)}")
        except Exception as e:
            logger.error("Error getting or creating user context: %s", str(e))
            raise UserServiceError(f"Failed to get or create user context: {str(e)}")
    
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
                # Publish user_updated event for state changes
                try:
                    event = create_event(
                        "user_updated",
                        user_id=user_id,
                        update_type="state",
                        updated_fields=state_updates
                    )
                    await self.event_bus.publish("user_updated", event.dict())
                except Exception as e:
                    logger.warning("Failed to publish user_updated event for state change: %s", str(e))
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
                # Publish user_updated event for profile changes
                try:
                    event = create_event(
                        "user_updated",
                        user_id=user_id,
                        update_type="profile",
                        updated_fields=profile_updates
                    )
                    await self.event_bus.publish("user_updated", event.dict())
                except Exception as e:
                    logger.warning("Failed to publish user_updated event for profile change: %s", str(e))
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
            # Get user data before deletion for event metadata
            user_profile = self._get_user_profile(user_id)
            user_state = self._get_user_state(user_id)
            
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
                    deletion_reason=deletion_reason,
                    metadata={
                        "user_profile": user_profile,
                        "user_state": user_state
                    }
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

    async def get_user_besitos(self, user_id: str) -> int:
        """Get the number of besitos a user has"""
        try:
            # Get user state from MongoDB which may contain besitos
            state = self._get_user_state(user_id)
            if state:
                # Check if besitos field exists in the user's state
                return state.get('besitos', 0)
            return 0
        except Exception as e:
            logger.error("Error getting user besitos: %s", str(e))
            return 0

    async def award_besitos(self, user_id: str, amount: int) -> None:
        """Award besitos to a user"""
        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]
            
            # Update user's besitos using $inc to increment atomically
            result = users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"besitos": amount}, "$set": {"updated_at": datetime.utcnow().isoformat()}}
            )
            
            if result.modified_count > 0:
                logger.info("Awarded %d besitos to user: %s", amount, user_id)
                # Publish besitos_awarded event
                try:
                    event = create_event(
                        "besitos_awarded",
                        user_id=user_id,
                        amount=amount,
                        new_balance=(await self.get_user_besitos(user_id))
                    )
                    await self.event_bus.publish("besitos_awarded", event.dict())
                except Exception as e:
                    logger.warning("Failed to publish besitos_awarded event: %s", str(e))
            else:
                logger.warning("No user found to award besitos: %s", user_id)
        except Exception as e:
            logger.error("Error awarding besitos: %s", str(e))

    async def deduct_besitos(self, user_id: str, amount: int) -> None:
        """Deduct besitos from a user"""
        try:
            current_besitos = await self.get_user_besitos(user_id)
            if current_besitos < amount:
                raise UserServiceError(f"Insufficient besitos: {current_besitos} < {amount}")
            
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]
            
            # Update user's besitos using $inc to decrement atomically
            result = users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"besitos": -amount}, "$set": {"updated_at": datetime.utcnow().isoformat()}}
            )
            
            if result.modified_count > 0:
                logger.info("Deducted %d besitos from user: %s", amount, user_id)
                # Publish besitos_spent event
                try:
                    event = create_event(
                        "besitos_spent",
                        user_id=user_id,
                        amount=amount,
                        new_balance=(await self.get_user_besitos(user_id))
                    )
                    await self.event_bus.publish("besitos_spent", event.dict())
                except Exception as e:
                    logger.warning("Failed to publish besitos_spent event: %s", str(e))
            else:
                logger.warning("No user found to deduct besitos: %s", user_id)
        except Exception as e:
            logger.error("Error deducting besitos: %s", str(e))
            raise

    async def publish_user_interaction(self, user_id: str, action: str, context: Dict[str, Any] = None) -> None:
        """Publish a user interaction event.

        Args:
            user_id (str): User ID
            action (str): User action
            context (Dict[str, Any]): Context of the interaction
        """
        try:
            event = create_event(
                "user_interaction",
                user_id=user_id,
                action=action,
                context=context or {}
            )
            await self.event_bus.publish("user_interaction", event.dict())
            logger.debug("Published user interaction event for user: %s, action: %s", user_id, action)
        except Exception as e:
            logger.warning("Failed to publish user_interaction event: %s", str(e))

    async def update_emotional_signature(self, user_id: str, signature_data: Dict[str, Any]) -> bool:
        """Update user's emotional signature and archetype classification in MongoDB.

        This method implements REQ-1 requirements for real-time behavioral analysis engine
        and Complete Integration requirements for total system connectivity.

        Args:
            user_id (str): User ID
            signature_data (Dict[str, Any]): Emotional signature data containing:
                - archetype: User's emotional archetype
                - authenticity_score: Authenticity score (0.0-1.0)
                - vulnerability_level: Vulnerability level (0.0-1.0)
                - response_patterns: User's response patterns
                - signature_strength: Classification confidence (0.0-1.0)

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Updating emotional signature for user: %s", user_id)

        try:
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]

            # Get current emotional signature for comparison
            current_user = users_collection.find_one({"user_id": user_id})
            if not current_user:
                logger.warning("User not found for emotional signature update: %s", user_id)
                return False

            current_signature = current_user.get("emotional_signature", {})
            previous_archetype = current_signature.get("archetype")

            # Prepare signature updates with timestamp
            timestamp = datetime.utcnow()
            signature_updates = {
                "emotional_signature.archetype": signature_data.get("archetype"),
                "emotional_signature.authenticity_score": signature_data.get("authenticity_score", 0.0),
                "emotional_signature.vulnerability_level": signature_data.get("vulnerability_level", 0.0),
                "emotional_signature.response_patterns": signature_data.get("response_patterns", {}),
                "emotional_signature.signature_strength": signature_data.get("signature_strength", 0.0),
                "emotional_signature.last_analysis": timestamp,
                "emotional_signature.updated_at": timestamp,
                "updated_at": timestamp.isoformat()
            }

            # Set created_at if this is the first emotional signature
            if not current_signature:
                signature_updates["emotional_signature.created_at"] = timestamp

            # Update user document
            result = users_collection.update_one(
                {"user_id": user_id},
                {"$set": signature_updates}
            )

            success = result.modified_count > 0
            if success:
                logger.info("Successfully updated emotional signature for user: %s", user_id)

                # Publish emotional_signature_updated event for cross-module coordination
                try:
                    event = create_event(
                        "emotional_signature_updated",
                        user_id=user_id,
                        archetype=signature_data.get("archetype"),
                        authenticity_score=signature_data.get("authenticity_score", 0.0),
                        signature_strength=signature_data.get("signature_strength", 0.0),
                        previous_archetype=previous_archetype,
                        metadata={
                            "vulnerability_level": signature_data.get("vulnerability_level", 0.0),
                            "response_patterns": signature_data.get("response_patterns", {}),
                            "analysis_timestamp": timestamp.isoformat(),
                            "signature_change": previous_archetype != signature_data.get("archetype")
                        }
                    )
                    await self.event_bus.publish("emotional_signature_updated", event.dict())
                    logger.debug("Published emotional_signature_updated event for user: %s", user_id)
                except Exception as e:
                    logger.warning("Failed to publish emotional_signature_updated event: %s", str(e))

                # Publish user_updated event for general state changes
                try:
                    event = create_event(
                        "user_updated",
                        user_id=user_id,
                        update_type="emotional_signature",
                        updated_fields={"emotional_signature": signature_data}
                    )
                    await self.event_bus.publish("user_updated", event.dict())
                except Exception as e:
                    logger.warning("Failed to publish user_updated event for emotional signature: %s", str(e))

            else:
                logger.warning("No changes made to emotional signature for user: %s", user_id)

            return success

        except Exception as e:
            logger.error("Error updating emotional signature: %s", str(e))
            return False

    async def get_emotional_journey_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user's current emotional journey state from the database.

        This method implements REQ-2 requirements for progressive narrative level management
        by retrieving the user's current emotional journey data including current level,
        progression history, milestones, and related emotional journey metadata.

        Args:
            user_id (str): User ID

        Returns:
            Optional[Dict[str, Any]]: Emotional journey state containing:
                - current_level: Current emotional level (1-6)
                - level_entry_date: When user entered current level
                - progression_history: List of level progression events
                - emotional_milestones: Achieved emotional milestones
                - authenticity_history: History of authenticity measurements
                - vulnerability_progression: Vulnerability development data
                - relationship_depth: Current relationship depth score
                - journey_metadata: Additional journey context
                Or None if user not found or no emotional journey data exists

        Raises:
            UserServiceError: If error occurs during retrieval
        """
        logger.debug("Retrieving emotional journey state for user: %s", user_id)

        try:
            # Get user context using existing pattern
            user_context = await self.get_user_context(user_id)
            if not user_context:
                logger.warning("User context not found for emotional journey state: %s", user_id)
                return None

            # Extract emotional journey data from user state
            emotional_journey = user_context.get("state", {}).get("emotional_journey")

            if not emotional_journey:
                # Initialize default emotional journey state if none exists
                logger.debug("No emotional journey found for user %s, returning default state", user_id)
                return {
                    "current_level": 1,
                    "level_entry_date": None,
                    "progression_history": [],
                    "emotional_milestones": [],
                    "authenticity_history": [],
                    "vulnerability_progression": {
                        "current_score": 0.0,
                        "historical_scores": []
                    },
                    "relationship_depth": 0.0,
                    "journey_metadata": {
                        "initialized": False,
                        "journey_started": None
                    },
                    "last_progression_check": None,
                    "updated_at": None
                }

            logger.debug("Successfully retrieved emotional journey state for user: %s", user_id)
            return emotional_journey

        except UserNotFoundError:
            logger.warning("User not found for emotional journey state retrieval: %s", user_id)
            return None
        except Exception as e:
            logger.error("Error retrieving emotional journey state for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to retrieve emotional journey state: {str(e)}")

    async def advance_diana_level(self, user_id: str, new_level: int, milestone_data: Dict[str, Any]) -> bool:
        """Advance user's Diana level with complete emotional journey progression tracking.

        This method implements REQ-2 requirements for progressive narrative level management
        and Complete Integration requirements for total system connectivity by managing
        Diana level progression through Los Kinkys (1-3) and Diván (4-6) levels with
        comprehensive tracking and cross-module coordination.

        Args:
            user_id (str): User ID
            new_level (int): New Diana level (1-6)
            milestone_data (Dict[str, Any]): Milestone data containing:
                - progression_reason: Reason for level advancement
                - emotional_metrics: Current emotional metrics
                - milestone_type: Type of milestone reached
                - authenticity_score: Current authenticity score
                - vulnerability_level: Current vulnerability level
                - relationship_depth: Current relationship depth
                - vip_access_required: Whether VIP access is required

        Returns:
            bool: True if successful, False otherwise

        Raises:
            UserServiceError: If error occurs during level advancement
        """
        logger.info("Advancing Diana level for user %s to level %d", user_id, new_level)

        # Validate level range
        if not (1 <= new_level <= 6):
            logger.error("Invalid Diana level %d for user %s", new_level, user_id)
            raise UserServiceError(f"Invalid Diana level: {new_level}. Must be between 1 and 6.")

        try:
            # Get current emotional journey state
            current_journey = await self.get_emotional_journey_state(user_id)
            if current_journey is None:
                logger.error("Could not retrieve emotional journey state for user: %s", user_id)
                return False

            current_level = current_journey.get("current_level", 1)

            # Validate progression (can't skip levels backwards or jump more than 1 level forward)
            if new_level < current_level:
                logger.warning("Cannot regress Diana level from %d to %d for user %s",
                             current_level, new_level, user_id)
                return False
            elif new_level > current_level + 1:
                logger.warning("Cannot skip Diana levels from %d to %d for user %s",
                             current_level, new_level, user_id)
                return False
            elif new_level == current_level:
                logger.debug("User %s already at Diana level %d", user_id, new_level)
                return True

            # Determine stage context
            stage_context = "los_kinkys" if new_level <= 3 else "divan"
            previous_stage = "los_kinkys" if current_level <= 3 else "divan"
            stage_transition = stage_context != previous_stage

            # Prepare timestamp
            timestamp = datetime.utcnow()

            # Create progression history entry
            progression_entry = {
                "from_level": current_level,
                "to_level": new_level,
                "progression_date": timestamp,
                "progression_reason": milestone_data.get("progression_reason", "milestone_reached"),
                "stage_context": stage_context,
                "stage_transition": stage_transition,
                "emotional_metrics": milestone_data.get("emotional_metrics", {}),
                "milestone_data": {
                    "milestone_type": milestone_data.get("milestone_type", "level_progression"),
                    "authenticity_score": milestone_data.get("authenticity_score", 0.0),
                    "vulnerability_level": milestone_data.get("vulnerability_level", 0.0),
                    "relationship_depth": milestone_data.get("relationship_depth", 0.0)
                },
                "vip_access_required": milestone_data.get("vip_access_required", new_level >= 4)
            }

            # Update emotional journey state
            updated_journey = {
                **current_journey,
                "current_level": new_level,
                "level_entry_date": timestamp,
                "stage_context": stage_context,
                "progression_history": current_journey.get("progression_history", []) + [progression_entry],
                "emotional_milestones": current_journey.get("emotional_milestones", []) + [
                    {
                        "milestone_id": f"diana_level_{new_level}",
                        "milestone_type": milestone_data.get("milestone_type", "level_progression"),
                        "achieved_date": timestamp,
                        "level": new_level,
                        "stage": stage_context,
                        "milestone_data": milestone_data
                    }
                ],
                "relationship_depth": milestone_data.get("relationship_depth",
                                                       current_journey.get("relationship_depth", 0.0)),
                "last_progression_check": timestamp,
                "updated_at": timestamp
            }

            # Update vulnerability progression if provided
            if "vulnerability_level" in milestone_data:
                vulnerability_progression = current_journey.get("vulnerability_progression", {
                    "current_score": 0.0,
                    "historical_scores": []
                })
                vulnerability_progression["current_score"] = milestone_data["vulnerability_level"]
                vulnerability_progression["historical_scores"] = (
                    vulnerability_progression.get("historical_scores", []) + [
                        {
                            "score": milestone_data["vulnerability_level"],
                            "timestamp": timestamp,
                            "level": new_level,
                            "context": "level_progression"
                        }
                    ]
                )
                updated_journey["vulnerability_progression"] = vulnerability_progression

            # Update authenticity history if provided
            if "authenticity_score" in milestone_data:
                authenticity_history = current_journey.get("authenticity_history", [])
                authenticity_history.append({
                    "score": milestone_data["authenticity_score"],
                    "timestamp": timestamp,
                    "level": new_level,
                    "context": "level_progression"
                })
                updated_journey["authenticity_history"] = authenticity_history

            # Initialize journey metadata if needed
            if not current_journey.get("journey_metadata", {}).get("initialized"):
                updated_journey["journey_metadata"] = {
                    "initialized": True,
                    "journey_started": timestamp,
                    "first_level_progression": timestamp
                }

            # Update user state in MongoDB using existing pattern
            state_updates = {
                "emotional_journey": updated_journey,
                "updated_at": timestamp.isoformat()
            }

            success = await self.update_user_state(user_id, state_updates)

            if success:
                logger.info("Successfully advanced Diana level for user %s from %d to %d",
                           user_id, current_level, new_level)

                # Publish Diana level progression event for cross-module coordination
                try:
                    event = create_event(
                        "diana_level_progression",
                        user_id=user_id,
                        previous_level=current_level,
                        new_level=new_level,
                        progression_reason=milestone_data.get("progression_reason", "milestone_reached"),
                        emotional_metrics=milestone_data.get("emotional_metrics", {}),
                        vip_access_required=milestone_data.get("vip_access_required", new_level >= 4),
                        metadata={
                            "stage_context": stage_context,
                            "stage_transition": stage_transition,
                            "previous_stage": previous_stage,
                            "milestone_data": milestone_data,
                            "progression_timestamp": timestamp.isoformat(),
                            "authenticity_score": milestone_data.get("authenticity_score", 0.0),
                            "vulnerability_level": milestone_data.get("vulnerability_level", 0.0),
                            "relationship_depth": milestone_data.get("relationship_depth", 0.0)
                        }
                    )
                    await self.event_bus.publish("diana_level_progression", event.dict())
                    logger.debug("Published diana_level_progression event for user: %s", user_id)
                except Exception as e:
                    logger.warning("Failed to publish diana_level_progression event: %s", str(e))

                # Publish emotional milestone reached event
                try:
                    event = create_event(
                        "emotional_milestone_reached",
                        user_id=user_id,
                        milestone_type=f"diana_level_{new_level}",
                        milestone_data={
                            "level": new_level,
                            "stage": stage_context,
                            "progression_data": progression_entry
                        },
                        reward_besitos=milestone_data.get("reward_besitos", 0),
                        unlock_content=milestone_data.get("unlock_content"),
                        metadata={
                            "level_progression": True,
                            "stage_transition": stage_transition,
                            "vip_access_required": milestone_data.get("vip_access_required", new_level >= 4)
                        }
                    )
                    await self.event_bus.publish("emotional_milestone_reached", event.dict())
                    logger.debug("Published emotional_milestone_reached event for user: %s", user_id)
                except Exception as e:
                    logger.warning("Failed to publish emotional_milestone_reached event: %s", str(e))

            else:
                logger.error("Failed to update user state for Diana level progression: %s", user_id)

            return success

        except UserNotFoundError:
            logger.error("User not found for Diana level advancement: %s", user_id)
            return False
        except Exception as e:
            logger.error("Error advancing Diana level for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to advance Diana level: {str(e)}")

    async def get_lucien_interaction_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user's Lucien interaction context from the database.

        This method implements the Lucien-Mediated Experience Ecosystem by managing
        the complete interaction context between users and Lucien's sophisticated
        evaluation system.

        Args:
            user_id (str): User ID

        Returns:
            Optional[Dict[str, Any]]: Lucien interaction context containing:
                - current_evaluation_level: User's current evaluation level (1-6)
                - relationship_with_lucien: Current relationship state
                - user_archetype_assessment: Archetype evaluation data
                - interaction_tone: Current interaction tone
                - diana_encounters_earned: Number of earned Diana encounters
                - last_diana_encounter: Timestamp of last Diana encounter
                - behavioral_assessment_history: History of behavioral assessments
                - worthiness_progression: User worthiness development data
                - sophistication_level: Current sophistication assessment
                Or None if user not found or no interaction context exists

        Raises:
            UserServiceError: If error occurs during retrieval
        """
        logger.debug("Retrieving Lucien interaction context for user: %s", user_id)

        try:
            # Get or create user context using safe pattern
            user_context = await self.get_or_create_user_context(user_id)
            if not user_context:
                logger.warning("User context could not be retrieved or created for Lucien interaction context: %s", user_id)
                return None

            # Extract Lucien interaction data from user state
            lucien_context = user_context.get("state", {}).get("lucien_interaction_context")

            if not lucien_context:
                # Initialize default Lucien interaction context if none exists
                logger.debug("No Lucien interaction context found for user %s, returning default state", user_id)
                return {
                    "current_evaluation_level": 1,
                    "relationship_with_lucien": RelationshipLevel.FORMAL_EXAMINER.value,
                    "user_archetype_assessment": {
                        "detected_archetype": None,
                        "confidence_score": 0.0,
                        "assessment_date": None,
                        "behavioral_indicators": []
                    },
                    "interaction_tone": "cold_professional",
                    "diana_encounters_earned": 0,
                    "last_diana_encounter": None,
                    "next_diana_opportunity": None,
                    "behavioral_assessment_history": [],
                    "worthiness_progression": {
                        "current_worthiness_score": 0.0,
                        "character_assessments": [],
                        "behavioral_improvements": [],
                        "sophistication_growth": 0.0,
                        "emotional_intelligence_development": 0.0,
                        "diana_encounter_readiness": 0.0
                    },
                    "sophistication_level": {
                        "current_score": 0.0,
                        "cultural_sophistication": 0.0,
                        "language_sophistication": 0.0,
                        "behavioral_sophistication": 0.0
                    },
                    "lucien_voice_profile": {
                        "formality_level": FormalityLevel.DISTANT_FORMAL.value,
                        "evaluation_mode": EvaluationMode.SKEPTICAL_OBSERVER.value,
                        "protective_stance": ProtectiveStance.ABSOLUTE_GATEKEEPER.value,
                        "sophistication_display": SophisticationDisplay.BASIC_ELEGANCE.value,
                        "user_relationship_level": RelationshipLevel.FORMAL_EXAMINER.value,
                        "interaction_history": {
                            "total_interactions": 0,
                            "successful_challenges": 0,
                            "failed_evaluations": 0,
                            "diana_encounter_requests": 0,
                            "sophistication_demonstrations": 0,
                            "authentic_vulnerability_moments": 0,
                            "last_interaction": None,
                            "evaluation_progression": []
                        },
                        "sarcasm_intensity": 0.3,
                        "cultural_reference_frequency": 0.2,
                        "diana_protection_intensity": 1.0
                    },
                    "last_evaluation_timestamp": None,
                    "current_testing_focus": None,
                    "pending_challenges": [],
                    "created_at": None,
                    "updated_at": None
                }

            logger.debug("Successfully retrieved Lucien interaction context for user: %s", user_id)
            return lucien_context

        except UserNotFoundError:
            logger.warning("User not found for Lucien interaction context retrieval: %s", user_id)
            return None
        except Exception as e:
            logger.error("Error retrieving Lucien interaction context for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to retrieve Lucien interaction context: {str(e)}")

    async def update_lucien_interaction_context(self, user_id: str, context_updates: Dict[str, Any]) -> bool:
        """Update user's Lucien interaction context in MongoDB.

        This method implements the Lucien-Mediated Experience Ecosystem by updating
        the sophisticated evaluation system that tracks user interactions with Lucien.

        Args:
            user_id (str): User ID
            context_updates (Dict[str, Any]): Context updates to apply containing:
                - evaluation_level_change: New evaluation level if changed
                - relationship_progression: Relationship level progression data
                - archetype_update: Updated archetype assessment
                - behavioral_assessment: New behavioral assessment data
                - worthiness_update: Worthiness progression update
                - interaction_metadata: Additional interaction context

        Returns:
            bool: True if successful, False otherwise

        Raises:
            UserServiceError: If error occurs during update
        """
        logger.debug("Updating Lucien interaction context for user: %s", user_id)

        try:
            # Get current Lucien interaction context
            current_context = await self.get_lucien_interaction_context(user_id)
            if current_context is None:
                logger.error("Could not retrieve Lucien interaction context for user: %s", user_id)
                return False

            # Prepare timestamp
            timestamp = datetime.utcnow()

            # Update interaction history if provided
            if "interaction_metadata" in context_updates:
                interaction_history = current_context.get("lucien_voice_profile", {}).get("interaction_history", {})
                interaction_history["total_interactions"] = interaction_history.get("total_interactions", 0) + 1
                interaction_history["last_interaction"] = timestamp

                # Update specific interaction metrics
                metadata = context_updates["interaction_metadata"]
                if metadata.get("challenge_successful"):
                    interaction_history["successful_challenges"] = interaction_history.get("successful_challenges", 0) + 1
                if metadata.get("evaluation_failed"):
                    interaction_history["failed_evaluations"] = interaction_history.get("failed_evaluations", 0) + 1
                if metadata.get("diana_encounter_requested"):
                    interaction_history["diana_encounter_requests"] = interaction_history.get("diana_encounter_requests", 0) + 1
                if metadata.get("sophistication_demonstrated"):
                    interaction_history["sophistication_demonstrations"] = interaction_history.get("sophistication_demonstrations", 0) + 1
                if metadata.get("authentic_vulnerability_shown"):
                    interaction_history["authentic_vulnerability_moments"] = interaction_history.get("authentic_vulnerability_moments", 0) + 1

                # Update evaluation progression history
                if metadata.get("evaluation_progression"):
                    evaluation_progression = interaction_history.get("evaluation_progression", [])
                    evaluation_progression.append({
                        "timestamp": timestamp,
                        "progression_type": metadata["evaluation_progression"],
                        "context": metadata.get("progression_context", "")
                    })
                    interaction_history["evaluation_progression"] = evaluation_progression

                current_context["lucien_voice_profile"]["interaction_history"] = interaction_history

            # Update behavioral assessment history
            if "behavioral_assessment" in context_updates:
                assessment_data = context_updates["behavioral_assessment"]
                behavioral_history = current_context.get("behavioral_assessment_history", [])
                behavioral_history.append({
                    "assessment_id": assessment_data.get("assessment_id", str(uuid.uuid4())),
                    "timestamp": timestamp,
                    "behavior_observed": assessment_data.get("behavior_observed", ""),
                    "lucien_evaluation": assessment_data.get("lucien_evaluation", ""),
                    "sophistication_impact": assessment_data.get("sophistication_impact", 0.0),
                    "worthiness_impact": assessment_data.get("worthiness_impact", 0.0),
                    "archetype_confirmation": assessment_data.get("archetype_confirmation"),
                    "diana_protection_factor": assessment_data.get("diana_protection_factor", 0.0)
                })
                current_context["behavioral_assessment_history"] = behavioral_history

            # Update worthiness progression
            if "worthiness_update" in context_updates:
                worthiness_data = context_updates["worthiness_update"]
                worthiness_progression = current_context.get("worthiness_progression", {})

                # Update current worthiness score
                if "worthiness_change" in worthiness_data:
                    current_score = worthiness_progression.get("current_worthiness_score", 0.0)
                    new_score = max(0.0, min(1.0, current_score + worthiness_data["worthiness_change"]))
                    worthiness_progression["current_worthiness_score"] = new_score

                # Add character assessment if provided
                if "character_assessment" in worthiness_data:
                    character_assessments = worthiness_progression.get("character_assessments", [])
                    character_assessments.append({
                        "assessment": worthiness_data["character_assessment"],
                        "timestamp": timestamp,
                        "assessment_context": worthiness_data.get("assessment_context", "")
                    })
                    worthiness_progression["character_assessments"] = character_assessments

                # Update other metrics
                for metric in ["sophistication_growth", "emotional_intelligence_development", "diana_encounter_readiness"]:
                    if metric in worthiness_data:
                        worthiness_progression[metric] = worthiness_data[metric]

                current_context["worthiness_progression"] = worthiness_progression

            # Update relationship level if provided
            if "relationship_progression" in context_updates:
                relationship_data = context_updates["relationship_progression"]
                current_context["relationship_with_lucien"] = relationship_data.get("new_relationship_level", current_context["relationship_with_lucien"])
                current_context["current_evaluation_level"] = relationship_data.get("new_evaluation_level", current_context["current_evaluation_level"])

                # Update voice profile relationship level
                if "lucien_voice_profile" in current_context:
                    current_context["lucien_voice_profile"]["user_relationship_level"] = relationship_data.get("new_relationship_level", current_context["lucien_voice_profile"]["user_relationship_level"])

            # Update archetype assessment if provided
            if "archetype_update" in context_updates:
                archetype_data = context_updates["archetype_update"]
                current_context["user_archetype_assessment"] = {
                    "detected_archetype": archetype_data.get("archetype"),
                    "confidence_score": archetype_data.get("confidence_score", 0.0),
                    "assessment_date": timestamp,
                    "behavioral_indicators": archetype_data.get("behavioral_indicators", []),
                    "previous_archetype": current_context.get("user_archetype_assessment", {}).get("detected_archetype")
                }

            # Update Diana encounter data if provided
            if "diana_encounter_update" in context_updates:
                diana_data = context_updates["diana_encounter_update"]
                if diana_data.get("encounter_occurred"):
                    current_context["diana_encounters_earned"] = current_context.get("diana_encounters_earned", 0) + 1
                    current_context["last_diana_encounter"] = timestamp
                if "next_opportunity" in diana_data:
                    current_context["next_diana_opportunity"] = diana_data["next_opportunity"]

            # Update sophistication level if provided
            if "sophistication_update" in context_updates:
                sophistication_data = context_updates["sophistication_update"]
                sophistication_level = current_context.get("sophistication_level", {})
                for metric in ["current_score", "cultural_sophistication", "language_sophistication", "behavioral_sophistication"]:
                    if metric in sophistication_data:
                        sophistication_level[metric] = sophistication_data[metric]
                current_context["sophistication_level"] = sophistication_level

            # Update other context fields
            if "evaluation_focus" in context_updates:
                current_context["current_testing_focus"] = context_updates["evaluation_focus"]

            if "pending_challenges" in context_updates:
                current_context["pending_challenges"] = context_updates["pending_challenges"]

            # Update timestamps
            current_context["last_evaluation_timestamp"] = timestamp
            current_context["updated_at"] = timestamp
            if current_context.get("created_at") is None:
                current_context["created_at"] = timestamp

            # Update user state in MongoDB
            state_updates = {
                "lucien_interaction_context": current_context,
                "updated_at": timestamp.isoformat()
            }

            success = await self.update_user_state(user_id, state_updates)

            if success:
                logger.info("Successfully updated Lucien interaction context for user: %s", user_id)

                # Publish Lucien interaction update event for cross-module coordination
                try:
                    event = create_event(
                        "lucien_interaction_updated",
                        user_id=user_id,
                        relationship_level=current_context["relationship_with_lucien"],
                        evaluation_level=current_context["current_evaluation_level"],
                        worthiness_score=current_context.get("worthiness_progression", {}).get("current_worthiness_score", 0.0),
                        diana_encounters_earned=current_context.get("diana_encounters_earned", 0),
                        metadata={
                            "update_type": list(context_updates.keys()),
                            "archetype": current_context.get("user_archetype_assessment", {}).get("detected_archetype"),
                            "sophistication_score": current_context.get("sophistication_level", {}).get("current_score", 0.0),
                            "interaction_count": current_context.get("lucien_voice_profile", {}).get("interaction_history", {}).get("total_interactions", 0),
                            "update_timestamp": timestamp.isoformat()
                        }
                    )
                    await self.event_bus.publish("lucien_interaction_updated", event.dict())
                    logger.debug("Published lucien_interaction_updated event for user: %s", user_id)
                except Exception as e:
                    logger.warning("Failed to publish lucien_interaction_updated event: %s", str(e))

            else:
                logger.error("Failed to update user state for Lucien interaction context: %s", user_id)

            return success

        except UserNotFoundError:
            logger.error("User not found for Lucien interaction context update: %s", user_id)
            return False
        except Exception as e:
            logger.error("Error updating Lucien interaction context for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to update Lucien interaction context: {str(e)}")

    async def create_lucien_voice_profile(self, user_id: str, initial_archetype: Optional[str] = None) -> LucienVoiceProfile:
        """Create a new LucienVoiceProfile instance from user's interaction context.

        This method creates a LucienVoiceProfile dataclass instance populated with
        the user's current interaction context data, providing a complete voice
        adaptation profile for Lucien's sophisticated interface personality.

        Args:
            user_id (str): User ID
            initial_archetype (Optional[str]): Initial archetype if detected

        Returns:
            LucienVoiceProfile: Configured voice profile for Lucien interactions

        Raises:
            UserServiceError: If error occurs during profile creation
        """
        logger.debug("Creating Lucien voice profile for user: %s", user_id)

        try:
            # Get current interaction context
            interaction_context = await self.get_lucien_interaction_context(user_id)
            if interaction_context is None:
                # Initialize with default context if none exists
                interaction_context = await self.get_lucien_interaction_context(user_id)

            # Extract voice profile data
            voice_profile_data = interaction_context.get("lucien_voice_profile", {})
            worthiness_data = interaction_context.get("worthiness_progression", {})
            interaction_history_data = voice_profile_data.get("interaction_history", {})

            # Create InteractionHistory instance
            interaction_history = InteractionHistory(
                total_interactions=interaction_history_data.get("total_interactions", 0),
                successful_challenges=interaction_history_data.get("successful_challenges", 0),
                failed_evaluations=interaction_history_data.get("failed_evaluations", 0),
                diana_encounter_requests=interaction_history_data.get("diana_encounter_requests", 0),
                sophistication_demonstrations=interaction_history_data.get("sophistication_demonstrations", 0),
                authentic_vulnerability_moments=interaction_history_data.get("authentic_vulnerability_moments", 0),
                last_interaction=interaction_history_data.get("last_interaction"),
                evaluation_progression=interaction_history_data.get("evaluation_progression", [])
            )

            # Create WorthinessProgression instance
            worthiness_progression = WorthinessProgression(
                current_worthiness_score=worthiness_data.get("current_worthiness_score", 0.0),
                character_assessments=worthiness_data.get("character_assessments", []),
                behavioral_improvements=worthiness_data.get("behavioral_improvements", []),
                sophistication_growth=worthiness_data.get("sophistication_growth", 0.0),
                emotional_intelligence_development=worthiness_data.get("emotional_intelligence_development", 0.0),
                diana_encounter_readiness=worthiness_data.get("diana_encounter_readiness", 0.0)
            )

            # Create behavioral assessment history
            behavioral_assessments = []
            for assessment_data in interaction_context.get("behavioral_assessment_history", []):
                behavioral_assessments.append(BehavioralAssessment(
                    assessment_id=assessment_data.get("assessment_id", ""),
                    timestamp=assessment_data.get("timestamp", datetime.utcnow()),
                    behavior_observed=assessment_data.get("behavior_observed", ""),
                    lucien_evaluation=assessment_data.get("lucien_evaluation", ""),
                    sophistication_impact=assessment_data.get("sophistication_impact", 0.0),
                    worthiness_impact=assessment_data.get("worthiness_impact", 0.0),
                    archetype_confirmation=assessment_data.get("archetype_confirmation"),
                    diana_protection_factor=assessment_data.get("diana_protection_factor", 0.0)
                ))

            # Create LucienVoiceProfile instance
            voice_profile = LucienVoiceProfile(
                formality_level=FormalityLevel(voice_profile_data.get("formality_level", FormalityLevel.DISTANT_FORMAL.value)),
                evaluation_mode=EvaluationMode(voice_profile_data.get("evaluation_mode", EvaluationMode.SKEPTICAL_OBSERVER.value)),
                protective_stance=ProtectiveStance(voice_profile_data.get("protective_stance", ProtectiveStance.ABSOLUTE_GATEKEEPER.value)),
                sophistication_display=SophisticationDisplay(voice_profile_data.get("sophistication_display", SophisticationDisplay.BASIC_ELEGANCE.value)),
                user_relationship_level=RelationshipLevel(voice_profile_data.get("user_relationship_level", RelationshipLevel.FORMAL_EXAMINER.value)),
                interaction_history=interaction_history,
                worthiness_progression=worthiness_progression,
                behavioral_assessment_history=behavioral_assessments,
                sarcasm_intensity=voice_profile_data.get("sarcasm_intensity", 0.3),
                cultural_reference_frequency=voice_profile_data.get("cultural_reference_frequency", 0.2),
                diana_protection_intensity=voice_profile_data.get("diana_protection_intensity", 1.0),
                last_evaluation_timestamp=interaction_context.get("last_evaluation_timestamp"),
                current_testing_focus=interaction_context.get("current_testing_focus"),
                pending_challenges=interaction_context.get("pending_challenges", [])
            )

            # Apply initial archetype if provided
            if initial_archetype:
                voice_profile.adapt_to_archetype(initial_archetype)

            logger.debug("Successfully created Lucien voice profile for user: %s", user_id)
            return voice_profile

        except Exception as e:
            logger.error("Error creating Lucien voice profile for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to create Lucien voice profile: {str(e)}")

    async def save_lucien_voice_profile(self, user_id: str, voice_profile: LucienVoiceProfile) -> bool:
        """Save LucienVoiceProfile instance back to user's interaction context.

        This method saves the current state of a LucienVoiceProfile instance
        back to the user's interaction context in the database.

        Args:
            user_id (str): User ID
            voice_profile (LucienVoiceProfile): Voice profile to save

        Returns:
            bool: True if successful, False otherwise

        Raises:
            UserServiceError: If error occurs during save
        """
        logger.debug("Saving Lucien voice profile for user: %s", user_id)

        try:
            # Convert voice profile to dictionary format
            context_updates = {
                "lucien_voice_profile_update": {
                    "formality_level": voice_profile.formality_level.value,
                    "evaluation_mode": voice_profile.evaluation_mode.value,
                    "protective_stance": voice_profile.protective_stance.value,
                    "sophistication_display": voice_profile.sophistication_display.value,
                    "user_relationship_level": voice_profile.user_relationship_level.value,
                    "sarcasm_intensity": voice_profile.sarcasm_intensity,
                    "cultural_reference_frequency": voice_profile.cultural_reference_frequency,
                    "diana_protection_intensity": voice_profile.diana_protection_intensity,
                    "interaction_history": {
                        "total_interactions": voice_profile.interaction_history.total_interactions,
                        "successful_challenges": voice_profile.interaction_history.successful_challenges,
                        "failed_evaluations": voice_profile.interaction_history.failed_evaluations,
                        "diana_encounter_requests": voice_profile.interaction_history.diana_encounter_requests,
                        "sophistication_demonstrations": voice_profile.interaction_history.sophistication_demonstrations,
                        "authentic_vulnerability_moments": voice_profile.interaction_history.authentic_vulnerability_moments,
                        "last_interaction": voice_profile.interaction_history.last_interaction,
                        "evaluation_progression": voice_profile.interaction_history.evaluation_progression
                    }
                },
                "worthiness_update": {
                    "current_worthiness_score": voice_profile.worthiness_progression.current_worthiness_score,
                    "character_assessments": voice_profile.worthiness_progression.character_assessments,
                    "behavioral_improvements": voice_profile.worthiness_progression.behavioral_improvements,
                    "sophistication_growth": voice_profile.worthiness_progression.sophistication_growth,
                    "emotional_intelligence_development": voice_profile.worthiness_progression.emotional_intelligence_development,
                    "diana_encounter_readiness": voice_profile.worthiness_progression.diana_encounter_readiness
                },
                "evaluation_focus": voice_profile.current_testing_focus,
                "pending_challenges": voice_profile.pending_challenges
            }

            # Update assessment history if provided
            if voice_profile.behavioral_assessment_history:
                context_updates["behavioral_assessment_history_update"] = [
                    {
                        "assessment_id": assessment.assessment_id,
                        "timestamp": assessment.timestamp,
                        "behavior_observed": assessment.behavior_observed,
                        "lucien_evaluation": assessment.lucien_evaluation,
                        "sophistication_impact": assessment.sophistication_impact,
                        "worthiness_impact": assessment.worthiness_impact,
                        "archetype_confirmation": assessment.archetype_confirmation,
                        "diana_protection_factor": assessment.diana_protection_factor
                    }
                    for assessment in voice_profile.behavioral_assessment_history
                ]

            # Update the interaction context
            success = await self.update_lucien_interaction_context(user_id, context_updates)

            if success:
                logger.info("Successfully saved Lucien voice profile for user: %s", user_id)
            else:
                logger.error("Failed to save Lucien voice profile for user: %s", user_id)

            return success

        except Exception as e:
            logger.error("Error saving Lucien voice profile for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to save Lucien voice profile: {str(e)}")

    async def get_lucien_relationship_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve comprehensive Lucien relationship state for user interface and experience management.

        This method implements Requirement 1.2 by providing complete relationship state information
        that enables the UX Enhanced Interface to present appropriate Lucien interactions,
        evaluation levels, and Diana encounter opportunities based on the user's current
        relationship development with Lucien's sophisticated evaluation system.

        Args:
            user_id (str): User ID

        Returns:
            Optional[Dict[str, Any]]: Comprehensive Lucien relationship state containing:
                - relationship_level: Current relationship stage with Lucien
                - evaluation_progress: User's progression through Lucien's assessment system
                - interaction_quality: Quality metrics of user-Lucien interactions
                - archetype_classification: User's behavioral archetype as assessed by Lucien
                - worthiness_assessment: Current worthiness score and progression trends
                - diana_encounter_readiness: Eligibility and readiness for Diana interactions
                - sophisticated_interaction_context: Context for generating appropriate responses
                - next_development_targets: Areas Lucien is focusing on for user growth
                - relationship_milestones: Achieved and upcoming relationship milestones
                - personalization_data: Archetype-specific interaction preferences
                Or None if user not found or no relationship data exists

        Raises:
            UserServiceError: If error occurs during retrieval

        Example:
            >>> user_service = UserService(db_manager, event_bus)
            >>> relationship_state = await user_service.get_lucien_relationship_state("user123")
            >>> print(relationship_state["relationship_level"])
            "reluctant_appreciator"
            >>> print(relationship_state["diana_encounter_readiness"]["eligible"])
            False
        """
        logger.debug("Retrieving Lucien relationship state for user: %s", user_id)

        try:
            # Get comprehensive Lucien interaction context
            lucien_context = await self.get_lucien_interaction_context(user_id)
            if lucien_context is None:
                logger.warning("No Lucien interaction context found for user: %s", user_id)
                return None

            # Get additional user context for complete assessment
            user_context = await self.get_user_context(user_id)
            if user_context is None:
                logger.warning("No user context found for relationship state assessment: %s", user_id)
                return None

            # Extract key relationship components
            relationship_with_lucien = lucien_context.get("relationship_with_lucien", RelationshipLevel.FORMAL_EXAMINER.value)
            worthiness_progression = lucien_context.get("worthiness_progression", {})
            archetype_assessment = lucien_context.get("user_archetype_assessment", {})
            voice_profile = lucien_context.get("lucien_voice_profile", {})
            interaction_history = voice_profile.get("interaction_history", {})

            # Calculate relationship progression metrics
            current_worthiness = worthiness_progression.get("current_worthiness_score", 0.0)
            total_interactions = interaction_history.get("total_interactions", 0)
            successful_challenges = interaction_history.get("successful_challenges", 0)
            sophistication_score = lucien_context.get("sophistication_level", {}).get("current_score", 0.0)

            # Determine relationship quality and progression trends
            if total_interactions > 0:
                success_rate = successful_challenges / total_interactions
                interaction_quality_score = min(1.0, (success_rate * 0.4) + (current_worthiness * 0.6))
            else:
                success_rate = 0.0
                interaction_quality_score = 0.0

            # Assess Diana encounter readiness
            diana_encounters_earned = lucien_context.get("diana_encounters_earned", 0)
            last_diana_encounter = lucien_context.get("last_diana_encounter")
            next_diana_opportunity = lucien_context.get("next_diana_opportunity")

            # Diana readiness calculation based on multiple factors
            diana_readiness_factors = {
                "worthiness_threshold": current_worthiness >= 0.6,
                "sophistication_threshold": sophistication_score >= 0.5,
                "interaction_quality": interaction_quality_score >= 0.5,
                "successful_challenges": successful_challenges >= 3,
                "has_archetype": archetype_assessment.get("detected_archetype") is not None,
                "evaluation_level": lucien_context.get("current_evaluation_level", 1) >= 3
            }

            diana_readiness_score = sum(diana_readiness_factors.values()) / len(diana_readiness_factors)
            diana_encounter_eligible = diana_readiness_score >= 0.7

            # Determine relationship development stage
            relationship_stages = {
                RelationshipLevel.FORMAL_EXAMINER.value: {
                    "stage_name": "Initial Evaluation",
                    "description": "Lucien is conducting initial assessment and establishing baseline",
                    "next_milestone": "Demonstrate consistent sophistication and respect",
                    "characteristic_behavior": "Formal distance with evaluative observation"
                },
                RelationshipLevel.RELUCTANT_APPRECIATOR.value: {
                    "stage_name": "Growing Recognition",
                    "description": "Lucien has observed noteworthy development and growing potential",
                    "next_milestone": "Achieve deeper emotional intelligence and authentic vulnerability",
                    "characteristic_behavior": "Grudging acknowledgment with increased engagement"
                },
                RelationshipLevel.TRUSTED_CONFIDANT.value: {
                    "stage_name": "Earned Collaboration",
                    "description": "Lucien has recognized exceptional growth and offers partnership",
                    "next_milestone": "Maintain sophisticated collaboration and guide others",
                    "characteristic_behavior": "Collaborative respect with genuine appreciation"
                }
            }

            current_stage = relationship_stages.get(relationship_with_lucien, relationship_stages[RelationshipLevel.FORMAL_EXAMINER.value])

            # Analyze interaction patterns and development targets
            behavioral_assessments = lucien_context.get("behavioral_assessment_history", [])
            recent_assessments = sorted(behavioral_assessments, key=lambda x: x.get("timestamp", datetime.min))[-5:] if behavioral_assessments else []

            # Identify development focus areas
            development_targets = []
            if current_worthiness < 0.3:
                development_targets.append("Basic sophistication and respectful interaction")
            elif current_worthiness < 0.6:
                development_targets.append("Emotional depth and authentic expression")
            else:
                development_targets.append("Collaborative intelligence and leadership potential")

            if sophistication_score < 0.4:
                development_targets.append("Cultural awareness and refined communication")
            if success_rate < 0.6:
                development_targets.append("Consistent performance in evaluative challenges")
            if not archetype_assessment.get("detected_archetype"):
                development_targets.append("Clear behavioral pattern expression for archetype classification")

            # Calculate relationship progression velocity
            progression_velocity = "slow"
            if total_interactions >= 10:
                recent_worthiness_changes = [assessment.get("worthiness_impact", 0.0) for assessment in recent_assessments]
                if recent_worthiness_changes:
                    avg_recent_progress = sum(recent_worthiness_changes) / len(recent_worthiness_changes)
                    if avg_recent_progress > 0.05:
                        progression_velocity = "accelerating"
                    elif avg_recent_progress > 0.02:
                        progression_velocity = "steady"

            # Compile comprehensive relationship state
            relationship_state = {
                # Core relationship information
                "relationship_level": relationship_with_lucien,
                "relationship_stage": current_stage,
                "relationship_progression_velocity": progression_velocity,

                # Evaluation and progress metrics
                "evaluation_progress": {
                    "current_evaluation_level": lucien_context.get("current_evaluation_level", 1),
                    "worthiness_score": current_worthiness,
                    "sophistication_score": sophistication_score,
                    "interaction_quality_score": interaction_quality_score,
                    "success_rate": success_rate,
                    "total_interactions": total_interactions,
                    "successful_challenges": successful_challenges
                },

                # Archetype and personalization data
                "archetype_classification": {
                    "detected_archetype": archetype_assessment.get("detected_archetype"),
                    "confidence_score": archetype_assessment.get("confidence_score", 0.0),
                    "behavioral_indicators": archetype_assessment.get("behavioral_indicators", []),
                    "assessment_date": archetype_assessment.get("assessment_date"),
                    "previous_archetype": archetype_assessment.get("previous_archetype")
                },

                # Diana encounter readiness and history
                "diana_encounter_readiness": {
                    "eligible": diana_encounter_eligible,
                    "readiness_score": diana_readiness_score,
                    "readiness_factors": diana_readiness_factors,
                    "encounters_earned": diana_encounters_earned,
                    "last_encounter": last_diana_encounter,
                    "next_opportunity": next_diana_opportunity,
                    "estimated_next_encounter": self._estimate_next_diana_opportunity(diana_readiness_score, diana_encounters_earned)
                },

                # Sophisticated interaction context
                "sophisticated_interaction_context": {
                    "formality_level": voice_profile.get("formality_level", FormalityLevel.DISTANT_FORMAL.value),
                    "evaluation_mode": voice_profile.get("evaluation_mode", EvaluationMode.SKEPTICAL_OBSERVER.value),
                    "protective_stance": voice_profile.get("protective_stance", ProtectiveStance.ABSOLUTE_GATEKEEPER.value),
                    "sophistication_display": voice_profile.get("sophistication_display", SophisticationDisplay.BASIC_ELEGANCE.value),
                    "sarcasm_intensity": voice_profile.get("sarcasm_intensity", 0.3),
                    "cultural_reference_frequency": voice_profile.get("cultural_reference_frequency", 0.2),
                    "diana_protection_intensity": voice_profile.get("diana_protection_intensity", 1.0)
                },

                # Development and growth tracking
                "development_assessment": {
                    "current_focus_areas": development_targets,
                    "recent_behavioral_patterns": [
                        {
                            "behavior": assessment.get("behavior_observed", ""),
                            "lucien_evaluation": assessment.get("lucien_evaluation", ""),
                            "impact": assessment.get("worthiness_impact", 0.0),
                            "date": assessment.get("timestamp")
                        }
                        for assessment in recent_assessments
                    ],
                    "growth_trajectory": self._analyze_growth_trajectory(worthiness_progression),
                    "next_milestone_requirements": self._determine_next_milestone_requirements(relationship_with_lucien, current_worthiness)
                },

                # Personalization preferences
                "personalization_data": {
                    "preferred_interaction_style": self._determine_preferred_interaction_style(archetype_assessment, relationship_with_lucien),
                    "response_adaptation_level": self._calculate_response_adaptation_level(sophistication_score, success_rate),
                    "challenge_complexity_preference": self._determine_challenge_complexity(current_worthiness, successful_challenges),
                    "cultural_sophistication_level": lucien_context.get("sophistication_level", {}).get("cultural_sophistication", 0.0)
                },

                # Metadata and tracking
                "relationship_metadata": {
                    "relationship_initiated": lucien_context.get("created_at"),
                    "last_interaction": interaction_history.get("last_interaction"),
                    "last_evaluation": lucien_context.get("last_evaluation_timestamp"),
                    "relationship_duration_days": self._calculate_relationship_duration(lucien_context.get("created_at")),
                    "interaction_frequency": self._calculate_interaction_frequency(total_interactions, lucien_context.get("created_at")),
                    "evolution_timeline": interaction_history.get("evaluation_progression", [])
                }
            }

            logger.debug("Successfully compiled Lucien relationship state for user: %s", user_id)
            return relationship_state

        except UserNotFoundError:
            logger.warning("User not found for Lucien relationship state retrieval: %s", user_id)
            return None
        except Exception as e:
            logger.error("Error retrieving Lucien relationship state for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to retrieve Lucien relationship state: {str(e)}")

    def _estimate_next_diana_opportunity(self, readiness_score: float, encounters_earned: int) -> Optional[str]:
        """Estimate when the next Diana encounter opportunity might arise."""
        if readiness_score >= 0.7:
            return "Ready now - awaiting appropriate moment"
        elif readiness_score >= 0.5:
            return "Soon - continue current development path"
        elif readiness_score >= 0.3:
            return "Developing - focus on sophistication growth"
        else:
            return "Early stages - establish relationship with Lucien first"

    def _analyze_growth_trajectory(self, worthiness_progression: Dict[str, Any]) -> str:
        """Analyze user's growth trajectory based on worthiness progression data."""
        current_score = worthiness_progression.get("current_worthiness_score", 0.0)
        character_assessments = worthiness_progression.get("character_assessments", [])

        if not character_assessments:
            return "insufficient_data"

        # Analyze recent assessment trends
        if len(character_assessments) >= 3:
            recent_assessments = character_assessments[-3:]
            # This would be more sophisticated in a real implementation
            return "steady_growth" if current_score > 0.4 else "early_development"
        else:
            return "establishing_baseline"

    def _determine_next_milestone_requirements(self, relationship_level: str, worthiness_score: float) -> List[str]:
        """Determine what user needs to achieve for next relationship milestone."""
        if relationship_level == RelationshipLevel.FORMAL_EXAMINER.value:
            return [
                "Demonstrate consistent sophisticated communication",
                "Complete at least 3 successful challenges",
                "Show authentic emotional engagement",
                "Achieve worthiness score of 0.5+"
            ]
        elif relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR.value:
            return [
                "Maintain sophisticated interaction patterns",
                "Show depth in emotional intelligence",
                "Demonstrate vulnerability and authenticity",
                "Achieve worthiness score of 0.8+"
            ]
        else:  # TRUSTED_CONFIDANT
            return [
                "Maintain collaborative excellence",
                "Guide and mentor other users",
                "Demonstrate leadership in sophisticated discourse",
                "Continue personal growth and self-reflection"
            ]

    def _determine_preferred_interaction_style(self, archetype_assessment: Dict[str, Any], relationship_level: str) -> str:
        """Determine user's preferred interaction style based on archetype and relationship."""
        archetype = archetype_assessment.get("detected_archetype")

        style_mappings = {
            "explorer": "challenge_focused",
            "direct": "straightforward_appreciative",
            "analytical": "intellectually_sophisticated",
            "patient": "contemplative_building",
            "persistent": "steady_recognition"
        }

        base_style = style_mappings.get(archetype, "adaptive_evaluative")

        # Modify based on relationship level
        if relationship_level == RelationshipLevel.TRUSTED_CONFIDANT.value:
            return f"collaborative_{base_style}"
        elif relationship_level == RelationshipLevel.RELUCTANT_APPRECIATOR.value:
            return f"appreciative_{base_style}"
        else:
            return f"evaluative_{base_style}"

    def _calculate_response_adaptation_level(self, sophistication_score: float, success_rate: float) -> float:
        """Calculate how much to adapt responses to user level."""
        # Higher scores mean user can handle more sophisticated responses
        base_adaptation = (sophistication_score * 0.6) + (success_rate * 0.4)
        return min(1.0, max(0.1, base_adaptation))

    def _determine_challenge_complexity(self, worthiness_score: float, successful_challenges: int) -> str:
        """Determine appropriate challenge complexity level."""
        if worthiness_score >= 0.7 and successful_challenges >= 5:
            return "advanced_sophisticated"
        elif worthiness_score >= 0.4 and successful_challenges >= 3:
            return "intermediate_nuanced"
        else:
            return "foundational_clear"

    def _calculate_relationship_duration(self, created_at: Optional[datetime]) -> Optional[int]:
        """Calculate how many days the relationship with Lucien has existed."""
        if not created_at:
            return None

        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                return None

        return (datetime.utcnow() - created_at).days

    def _calculate_interaction_frequency(self, total_interactions: int, created_at: Optional[datetime]) -> Optional[float]:
        """Calculate average interactions per day."""
        duration_days = self._calculate_relationship_duration(created_at)
        if not duration_days or duration_days == 0:
            return None

        return total_interactions / duration_days

    async def add_behavioral_assessment(self, user_id: str, assessment_data: Dict[str, Any]) -> bool:
        """Add a new behavioral assessment to user's tracking history.

        This method implements Requirement 2.2 by providing comprehensive behavioral assessment
        tracking that feeds into Lucien's sophisticated evaluation system and Diana encounter
        eligibility calculations.

        Args:
            user_id (str): User ID
            assessment_data (Dict[str, Any]): Assessment data containing:
                - behavior_observed: Description of the observed behavior
                - assessment_context: Context in which behavior was observed
                - sophistication_indicators: List of sophistication markers detected
                - authenticity_markers: Signs of authentic vs calculated responses
                - emotional_depth_signals: Indicators of emotional intelligence
                - archetype_confirmation: Behavior that confirms or challenges archetype
                - lucien_evaluation_notes: Lucien's specific observations
                - worthiness_impact: Impact on overall worthiness score (-1.0 to 1.0)
                - interaction_quality_score: Quality assessment of this interaction (0.0 to 1.0)
                - response_time_analysis: Analysis of response timing patterns
                - cultural_sophistication_displayed: Evidence of cultural awareness

        Returns:
            bool: True if assessment was successfully added, False otherwise

        Raises:
            UserServiceError: If error occurs during assessment addition

        Example:
            >>> assessment = {
            ...     "behavior_observed": "User demonstrated patience during complex narrative choice",
            ...     "assessment_context": "Diana Level 3 vulnerability mapping",
            ...     "sophistication_indicators": ["thoughtful response", "emotional nuance"],
            ...     "authenticity_markers": ["genuine vulnerability", "consistent pattern"],
            ...     "worthiness_impact": 0.15,
            ...     "interaction_quality_score": 0.8
            ... }
            >>> success = await user_service.add_behavioral_assessment("user123", assessment)
        """
        logger.debug("Adding behavioral assessment for user: %s", user_id)

        try:
            # Get current Lucien interaction context
            lucien_context = await self.get_lucien_interaction_context(user_id)
            if lucien_context is None:
                logger.warning("Could not get Lucien interaction context for behavioral assessment: %s", user_id)
                return False

            # Prepare timestamp
            timestamp = datetime.utcnow()

            # Create comprehensive behavioral assessment record
            assessment_record = {
                "assessment_id": str(uuid.uuid4()),
                "timestamp": timestamp,
                "behavior_observed": assessment_data.get("behavior_observed", ""),
                "assessment_context": assessment_data.get("assessment_context", ""),
                "sophistication_indicators": assessment_data.get("sophistication_indicators", []),
                "authenticity_markers": assessment_data.get("authenticity_markers", []),
                "emotional_depth_signals": assessment_data.get("emotional_depth_signals", []),
                "archetype_confirmation": assessment_data.get("archetype_confirmation"),
                "lucien_evaluation_notes": assessment_data.get("lucien_evaluation_notes", ""),
                "worthiness_impact": assessment_data.get("worthiness_impact", 0.0),
                "interaction_quality_score": assessment_data.get("interaction_quality_score", 0.0),
                "response_time_analysis": assessment_data.get("response_time_analysis", {}),
                "cultural_sophistication_displayed": assessment_data.get("cultural_sophistication_displayed", []),
                "session_context": {
                    "session_id": assessment_data.get("session_id"),
                    "interaction_sequence": assessment_data.get("interaction_sequence", 1),
                    "previous_assessments_count": len(lucien_context.get("behavioral_assessment_history", [])),
                    "relationship_level_at_time": lucien_context.get("relationship_with_lucien"),
                    "evaluation_level_at_time": lucien_context.get("current_evaluation_level", 1)
                },
                "impact_metrics": {
                    "sophistication_growth": assessment_data.get("sophistication_growth", 0.0),
                    "emotional_intelligence_development": assessment_data.get("emotional_intelligence_development", 0.0),
                    "diana_encounter_readiness_change": assessment_data.get("diana_encounter_readiness_change", 0.0),
                    "relationship_progression_contribution": assessment_data.get("relationship_progression_contribution", 0.0)
                }
            }

            # Update Lucien interaction context with new assessment
            context_updates = {
                "behavioral_assessment": assessment_record,
                "interaction_metadata": {
                    "assessment_added": True,
                    "sophistication_demonstrated": len(assessment_data.get("sophistication_indicators", [])) > 0,
                    "authenticity_detected": len(assessment_data.get("authenticity_markers", [])) > 0,
                    "evaluation_progression": "behavioral_assessment_recorded"
                }
            }

            # If worthiness impact is significant, also update worthiness progression
            worthiness_impact = assessment_data.get("worthiness_impact", 0.0)
            if abs(worthiness_impact) > 0.01:  # Only update for meaningful changes
                context_updates["worthiness_update"] = {
                    "worthiness_change": worthiness_impact,
                    "character_assessment": assessment_data.get("lucien_evaluation_notes", "Behavioral assessment update"),
                    "assessment_context": assessment_data.get("assessment_context", "general_interaction"),
                    "sophistication_growth": assessment_data.get("sophistication_growth", 0.0),
                    "emotional_intelligence_development": assessment_data.get("emotional_intelligence_development", 0.0)
                }

            # Update the interaction context
            success = await self.update_lucien_interaction_context(user_id, context_updates)

            if success:
                logger.info("Successfully added behavioral assessment for user: %s", user_id)

                # Publish behavioral assessment event for cross-module coordination
                try:
                    event = create_event(
                        "behavioral_assessment_added",
                        user_id=user_id,
                        assessment_id=assessment_record["assessment_id"],
                        behavior_observed=assessment_record["behavior_observed"],
                        worthiness_impact=worthiness_impact,
                        interaction_quality_score=assessment_record["interaction_quality_score"],
                        metadata={
                            "assessment_context": assessment_record["assessment_context"],
                            "sophistication_indicators": assessment_record["sophistication_indicators"],
                            "authenticity_markers": assessment_record["authenticity_markers"],
                            "timestamp": timestamp.isoformat(),
                            "relationship_level": lucien_context.get("relationship_with_lucien"),
                            "evaluation_level": lucien_context.get("current_evaluation_level", 1)
                        }
                    )
                    await self.event_bus.publish("behavioral_assessment_added", event.dict())
                    logger.debug("Published behavioral_assessment_added event for user: %s", user_id)
                except Exception as e:
                    logger.warning("Failed to publish behavioral_assessment_added event: %s", str(e))

            else:
                logger.error("Failed to update Lucien interaction context with behavioral assessment: %s", user_id)

            return success

        except Exception as e:
            logger.error("Error adding behavioral assessment for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to add behavioral assessment: {str(e)}")

    async def get_behavioral_assessment_history(self, user_id: str, limit: Optional[int] = 50, assessment_context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve user's behavioral assessment history with filtering options.

        This method provides access to the complete behavioral assessment tracking history
        that supports Lucien's evaluation system and Diana encounter management.

        Args:
            user_id (str): User ID
            limit (Optional[int]): Maximum number of assessments to return (default: 50)
            assessment_context (Optional[str]): Filter by specific assessment context

        Returns:
            List[Dict[str, Any]]: List of behavioral assessments sorted by timestamp (newest first)

        Raises:
            UserServiceError: If error occurs during retrieval

        Example:
            >>> assessments = await user_service.get_behavioral_assessment_history("user123", limit=10)
            >>> recent_narrative_assessments = await user_service.get_behavioral_assessment_history(
            ...     "user123", assessment_context="narrative_interaction"
            ... )
        """
        logger.debug("Retrieving behavioral assessment history for user: %s", user_id)

        try:
            # Get Lucien interaction context which contains assessment history
            lucien_context = await self.get_lucien_interaction_context(user_id)
            if lucien_context is None:
                logger.warning("No Lucien interaction context found for assessment history: %s", user_id)
                return []

            # Extract assessment history
            assessment_history = lucien_context.get("behavioral_assessment_history", [])

            # Filter by context if specified
            if assessment_context:
                assessment_history = [
                    assessment for assessment in assessment_history
                    if assessment.get("assessment_context") == assessment_context
                ]

            # Sort by timestamp (newest first)
            assessment_history.sort(
                key=lambda x: x.get("timestamp", datetime.min),
                reverse=True
            )

            # Apply limit
            if limit:
                assessment_history = assessment_history[:limit]

            logger.debug("Retrieved %d behavioral assessments for user: %s", len(assessment_history), user_id)
            return assessment_history

        except Exception as e:
            logger.error("Error retrieving behavioral assessment history for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to retrieve behavioral assessment history: {str(e)}")

    # --- Menu Context Management Methods (Task 25 Enhancement) ---

    async def get_user_menu_context(self, user_id: str) -> Dict[str, Any]:
        """Retrieve user's current menu context for menu navigation and state management.

        This method implements REQ-MENU-003 requirements by providing role-based access
        control context and user state information needed for menu generation.

        Args:
            user_id (str): User ID

        Returns:
            Dict[str, Any]: User menu context containing:
                - current_menu_id: Currently active menu
                - navigation_path: User's navigation history
                - menu_preferences: User's menu display preferences
                - session_data: Temporary menu-related session data
                - role: User's role for access control
                - has_vip: VIP status for premium feature access
                - narrative_level: Current narrative progression level
                - worthiness_score: Lucien's evaluation score
                - besitos_balance: Current virtual currency balance
                - archetype: User's behavioral archetype
        """
        logger.debug("Retrieving menu context for user: %s", user_id)

        try:
            # Get complete user context
            user_context = await self.get_user_context(user_id)
            if not user_context:
                logger.warning("No user context found for menu context retrieval: %s", user_id)
                return self._get_default_menu_context()

            # Extract user state
            user_state = user_context.get("state", {})
            
            # Get current menu context from user state
            menu_context = user_state.get("current_state", {}).get("menu_context", "main_menu")
            
            # Get navigation path
            navigation_path = user_state.get("current_state", {}).get("navigation_path", [])
            
            # Get session data
            session_data = user_state.get("current_state", {}).get("session_data", {})
            
            # Get user profile for role information
            user_profile = user_context.get("profile", {})
            
            # Get emotional journey for narrative level
            emotional_journey = user_state.get("emotional_journey", {})
            
            # Get Lucien interaction context for worthiness score
            lucien_context = user_state.get("lucien_interaction_context", {})
            worthiness_progression = lucien_context.get("worthiness_progression", {})
            
            # Get besitos balance
            besitos_balance = user_state.get("besitos", 0)
            
            # Get archetype from Lucien context
            archetype_assessment = lucien_context.get("user_archetype_assessment", {})
            
            # Compile comprehensive menu context
            compiled_context = {
                "user_id": user_id,
                "current_menu_id": menu_context,
                "navigation_path": navigation_path,
                "menu_preferences": user_state.get("preferences", {}),
                "session_data": session_data,
                "role": user_profile.get("role", "free_user"),
                "has_vip": user_profile.get("has_vip", False),
                "narrative_level": emotional_journey.get("current_level", 1),
                "worthiness_score": worthiness_progression.get("current_worthiness_score", 0.0),
                "besitos_balance": besitos_balance,
                "archetype": archetype_assessment.get("detected_archetype"),
                "updated_at": user_state.get("updated_at")
            }

            logger.debug("Successfully retrieved menu context for user: %s", user_id)
            return compiled_context

        except Exception as e:
            logger.error("Error retrieving menu context for user %s: %s", user_id, str(e))
            # Return default context as fallback
            return self._get_default_menu_context()

    def _get_default_menu_context(self) -> Dict[str, Any]:
        """Get default menu context for new or error cases."""
        return {
            "user_id": "unknown",
            "current_menu_id": "main_menu",
            "navigation_path": [],
            "menu_preferences": {
                "language": "es",
                "theme": "default"
            },
            "session_data": {},
            "role": "free_user",
            "has_vip": False,
            "narrative_level": 1,
            "worthiness_score": 0.0,
            "besitos_balance": 0,
            "archetype": None,
            "updated_at": datetime.utcnow().isoformat()
        }

    async def update_user_menu_context(self, user_id: str, menu_context_updates: Dict[str, Any]) -> bool:
        """Update user's menu context with new navigation state and preferences.

        This method implements REQ-MENU-003 requirements by managing user menu state
        and navigation context for role-based access control.

        Args:
            user_id (str): User ID
            menu_context_updates (Dict[str, Any]): Menu context updates containing:
                - current_menu_id: New active menu (optional)
                - navigation_path: Updated navigation path (optional)
                - menu_preferences: Updated preferences (optional)
                - session_data: Updated session data (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Updating menu context for user: %s", user_id)

        try:
            # Prepare state updates for MongoDB
            state_updates = {}
            
            # Update current menu context if provided
            if "current_menu_id" in menu_context_updates:
                if "current_state" not in state_updates:
                    state_updates["current_state"] = {}
                state_updates["current_state"]["menu_context"] = menu_context_updates["current_menu_id"]
            
            # Update navigation path if provided
            if "navigation_path" in menu_context_updates:
                if "current_state" not in state_updates:
                    state_updates["current_state"] = {}
                state_updates["current_state"]["navigation_path"] = menu_context_updates["navigation_path"]
            
            # Update session data if provided
            if "session_data" in menu_context_updates:
                if "current_state" not in state_updates:
                    state_updates["current_state"] = {}
                state_updates["current_state"]["session_data"] = menu_context_updates["session_data"]
            
            # Update menu preferences if provided
            if "menu_preferences" in menu_context_updates:
                state_updates["preferences"] = menu_context_updates["menu_preferences"]
            
            # Update user state
            if state_updates:
                success = await self.update_user_state(user_id, state_updates)
                if success:
                    logger.info("Successfully updated menu context for user: %s", user_id)
                else:
                    logger.warning("Failed to update menu context for user: %s", user_id)
                return success
            else:
                logger.debug("No menu context updates provided for user: %s", user_id)
                return True

        except Exception as e:
            logger.error("Error updating menu context for user %s: %s", user_id, str(e))
            return False

    async def push_menu_navigation(self, user_id: str, menu_id: str) -> bool:
        """Push a new menu to the user's navigation path.

        This method manages the user's navigation history for back navigation support.

        Args:
            user_id (str): User ID
            menu_id (str): Menu ID to push to navigation path

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Pushing menu '%s' to navigation path for user: %s", menu_id, user_id)

        try:
            # Get current menu context
            current_context = await self.get_user_menu_context(user_id)
            
            # Get current navigation path
            navigation_path = current_context.get("navigation_path", [])
            
            # Add current menu to navigation path (avoid duplicates)
            if navigation_path and navigation_path[-1] != menu_id:
                navigation_path.append(menu_id)
            elif not navigation_path:
                navigation_path.append(menu_id)
            
            # Limit navigation path to reasonable size (prevent memory issues)
            if len(navigation_path) > 10:
                navigation_path = navigation_path[-10:]
            
            # Update menu context with new navigation path
            updates = {"navigation_path": navigation_path}
            return await self.update_user_menu_context(user_id, updates)

        except Exception as e:
            logger.error("Error pushing menu to navigation path for user %s: %s", user_id, str(e))
            return False

    async def pop_menu_navigation(self, user_id: str) -> Optional[str]:
        """Pop the last menu from the user's navigation path and return the previous menu.

        This method supports back navigation functionality.

        Args:
            user_id (str): User ID

        Returns:
            Optional[str]: Previous menu ID or None if navigation path is empty
        """
        logger.debug("Popping menu from navigation path for user: %s", user_id)

        try:
            # Get current menu context
            current_context = await self.get_user_menu_context(user_id)
            
            # Get current navigation path
            navigation_path = current_context.get("navigation_path", [])
            
            # Pop last menu from navigation path
            if navigation_path:
                previous_menu = navigation_path.pop()
                
                # Update menu context with new navigation path
                updates = {"navigation_path": navigation_path}
                success = await self.update_user_menu_context(user_id, updates)
                
                if success:
                    logger.debug("Successfully popped menu '%s' from navigation path for user: %s", previous_menu, user_id)
                    return previous_menu
                else:
                    logger.warning("Failed to update navigation path after pop for user: %s", user_id)
                    return None
            else:
                logger.debug("Navigation path is empty for user: %s", user_id)
                return None

        except Exception as e:
            logger.error("Error popping menu from navigation path for user %s: %s", user_id, str(e))
            return None

    async def clear_menu_navigation(self, user_id: str) -> bool:
        """Clear the user's menu navigation path.

        This method is useful when starting a new navigation session or resetting state.

        Args:
            user_id (str): User ID

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Clearing navigation path for user: %s", user_id)
        
        try:
            # Update menu context with empty navigation path
            updates = {"navigation_path": []}
            return await self.update_user_menu_context(user_id, updates)
            
        except Exception as e:
            logger.error("Error clearing navigation path for user %s: %s", user_id, str(e))
            return False

    async def update_menu_session_data(self, user_id: str, session_data_updates: Dict[str, Any]) -> bool:
        """Update user's menu session data with new values.

        This method manages temporary menu-related session data that persists during
        a user's interaction session.

        Args:
            user_id (str): User ID
            session_data_updates (Dict[str, Any]): Session data updates to apply

        Returns:
            bool: True if successful, False otherwise
        """
        logger.debug("Updating menu session data for user: %s", user_id)

        try:
            # Get current menu context
            current_context = await self.get_user_menu_context(user_id)
            
            # Get current session data
            current_session_data = current_context.get("session_data", {})
            
            # Merge updates with current session data
            updated_session_data = {**current_session_data, **session_data_updates}
            
            # Update menu context with new session data
            updates = {"session_data": updated_session_data}
            return await self.update_user_menu_context(user_id, updates)

        except Exception as e:
            logger.error("Error updating menu session data for user %s: %s", user_id, str(e))
            return False

    async def analyze_behavioral_patterns(self, user_id: str, analysis_window_days: int = 30) -> Dict[str, Any]:
        """Analyze user's behavioral patterns over a specified time window.

        This method implements sophisticated behavioral pattern analysis that feeds into
        Lucien's evaluation system and supports archetype classification and relationship
        development tracking.

        Args:
            user_id (str): User ID
            analysis_window_days (int): Number of days to analyze (default: 30)

        Returns:
            Dict[str, Any]: Comprehensive behavioral pattern analysis containing:
                - pattern_summary: High-level pattern description
                - sophistication_trends: Sophistication development over time
                - authenticity_patterns: Authenticity vs calculated behavior analysis
                - interaction_quality_trends: Quality progression analysis
                - archetype_consistency: Consistency with detected archetype
                - emotional_intelligence_development: Emotional growth indicators
                - lucien_relationship_evolution: Relationship development patterns
                - behavioral_insights: Key insights and recommendations
                - assessment_frequency: Interaction frequency analysis

        Raises:
            UserServiceError: If error occurs during analysis

        Example:
            >>> analysis = await user_service.analyze_behavioral_patterns("user123", 14)
            >>> print(analysis["sophistication_trends"]["average_growth_rate"])
            0.05
        """
        logger.debug("Analyzing behavioral patterns for user: %s over %d days", user_id, analysis_window_days)

        try:
            # Get recent assessment history
            all_assessments = await self.get_behavioral_assessment_history(user_id, limit=200)

            # Filter assessments within the analysis window
            cutoff_date = datetime.utcnow() - timedelta(days=analysis_window_days)
            recent_assessments = [
                assessment for assessment in all_assessments
                if assessment.get("timestamp", datetime.min) >= cutoff_date
            ]

            if not recent_assessments:
                logger.warning("No recent assessments found for behavioral pattern analysis: %s", user_id)
                return {
                    "pattern_summary": "insufficient_data",
                    "analysis_window_days": analysis_window_days,
                    "assessments_analyzed": 0,
                    "insights": ["Need more interaction history for meaningful analysis"]
                }

            # Get current relationship state for context
            relationship_state = await self.get_lucien_relationship_state(user_id)

            # Analyze sophistication trends
            sophistication_scores = [
                assessment.get("interaction_quality_score", 0.0)
                for assessment in recent_assessments
                if assessment.get("interaction_quality_score") is not None
            ]

            sophistication_indicators_count = sum(
                len(assessment.get("sophistication_indicators", []))
                for assessment in recent_assessments
            )

            # Analyze authenticity patterns
            authenticity_markers_count = sum(
                len(assessment.get("authenticity_markers", []))
                for assessment in recent_assessments
            )

            # Calculate worthiness impact distribution
            worthiness_impacts = [
                assessment.get("worthiness_impact", 0.0)
                for assessment in recent_assessments
                if assessment.get("worthiness_impact") is not None
            ]

            # Analyze interaction contexts
            context_distribution = {}
            for assessment in recent_assessments:
                context = assessment.get("assessment_context", "unknown")
                context_distribution[context] = context_distribution.get(context, 0) + 1

            # Calculate trends
            if sophistication_scores:
                avg_sophistication = sum(sophistication_scores) / len(sophistication_scores)
                sophistication_trend = "improving" if len(sophistication_scores) > 1 and sophistication_scores[0] > sophistication_scores[-1] else "stable"
            else:
                avg_sophistication = 0.0
                sophistication_trend = "insufficient_data"

            if worthiness_impacts:
                avg_worthiness_impact = sum(worthiness_impacts) / len(worthiness_impacts)
                positive_impacts = sum(1 for impact in worthiness_impacts if impact > 0)
                negative_impacts = sum(1 for impact in worthiness_impacts if impact < 0)
            else:
                avg_worthiness_impact = 0.0
                positive_impacts = 0
                negative_impacts = 0

            # Determine archetype consistency
            archetype_confirmations = [
                assessment.get("archetype_confirmation")
                for assessment in recent_assessments
                if assessment.get("archetype_confirmation")
            ]

            most_common_archetype = None
            if archetype_confirmations:
                archetype_counts = {}
                for archetype in archetype_confirmations:
                    archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1
                most_common_archetype = max(archetype_counts, key=archetype_counts.get)

            # Generate insights
            insights = []
            if avg_sophistication > 0.7:
                insights.append("Demonstrates consistently high sophistication levels")
            elif avg_sophistication < 0.3:
                insights.append("Opportunity for sophistication development")

            if avg_worthiness_impact > 0.05:
                insights.append("Shows positive progression in Lucien's evaluation")
            elif avg_worthiness_impact < -0.05:
                insights.append("Recent interactions have challenged worthiness assessment")

            if authenticity_markers_count > sophistication_indicators_count * 0.5:
                insights.append("Strong authenticity patterns detected")

            if len(context_distribution) > 5:
                insights.append("Engages across diverse interaction contexts")

            # Compile comprehensive analysis
            analysis_result = {
                "pattern_summary": self._determine_pattern_summary(
                    avg_sophistication, avg_worthiness_impact, len(recent_assessments)
                ),
                "analysis_window_days": analysis_window_days,
                "assessments_analyzed": len(recent_assessments),
                "time_range": {
                    "earliest_assessment": recent_assessments[-1].get("timestamp") if recent_assessments else None,
                    "latest_assessment": recent_assessments[0].get("timestamp") if recent_assessments else None
                },
                "sophistication_trends": {
                    "average_score": avg_sophistication,
                    "trend_direction": sophistication_trend,
                    "indicators_detected": sophistication_indicators_count,
                    "quality_consistency": self._calculate_consistency(sophistication_scores)
                },
                "authenticity_patterns": {
                    "authenticity_markers_count": authenticity_markers_count,
                    "authenticity_ratio": authenticity_markers_count / max(len(recent_assessments), 1),
                    "authentic_vs_calculated_balance": "authentic_dominant" if authenticity_markers_count > len(recent_assessments) * 0.6 else "balanced"
                },
                "interaction_quality_trends": {
                    "average_quality_score": avg_sophistication,
                    "positive_interactions_percentage": (positive_impacts / max(len(worthiness_impacts), 1)) * 100,
                    "negative_interactions_percentage": (negative_impacts / max(len(worthiness_impacts), 1)) * 100,
                    "overall_impact_trend": "positive" if avg_worthiness_impact > 0 else "neutral" if avg_worthiness_impact == 0 else "challenging"
                },
                "archetype_consistency": {
                    "most_common_archetype": most_common_archetype,
                    "consistency_score": (archetype_counts.get(most_common_archetype, 0) / max(len(archetype_confirmations), 1)) if most_common_archetype else 0,
                    "archetype_distribution": dict(archetype_counts) if 'archetype_counts' in locals() else {}
                },
                "emotional_intelligence_development": {
                    "emotional_depth_signals_detected": sum(
                        len(assessment.get("emotional_depth_signals", []))
                        for assessment in recent_assessments
                    ),
                    "vulnerability_demonstrations": sum(
                        1 for assessment in recent_assessments
                        if "vulnerability" in str(assessment.get("behavior_observed", "")).lower()
                    ),
                    "empathy_indicators": sum(
                        1 for assessment in recent_assessments
                        if "empathy" in str(assessment.get("sophistication_indicators", [])).lower()
                    )
                },
                "lucien_relationship_evolution": {
                    "current_relationship_level": relationship_state.get("relationship_level") if relationship_state else "unknown",
                    "relationship_progression_velocity": relationship_state.get("relationship_progression_velocity") if relationship_state else "unknown",
                    "worthiness_score_change": sum(worthiness_impacts),
                    "evaluation_level_progression": len(set(
                        assessment.get("session_context", {}).get("evaluation_level_at_time")
                        for assessment in recent_assessments
                        if assessment.get("session_context", {}).get("evaluation_level_at_time")
                    ))
                },
                "behavioral_insights": insights,
                "assessment_frequency": {
                    "total_assessments": len(recent_assessments),
                    "assessments_per_day": len(recent_assessments) / analysis_window_days,
                    "context_distribution": context_distribution,
                    "most_active_context": max(context_distribution, key=context_distribution.get) if context_distribution else None
                },
                "recommendations": self._generate_behavioral_recommendations(
                    avg_sophistication, avg_worthiness_impact, most_common_archetype, insights
                )
            }

            logger.debug("Completed behavioral pattern analysis for user: %s", user_id)
            return analysis_result

        except Exception as e:
            logger.error("Error analyzing behavioral patterns for user %s: %s", user_id, str(e))
            raise UserServiceError(f"Failed to analyze behavioral patterns: {str(e)}")

    def _determine_pattern_summary(self, avg_sophistication: float, avg_worthiness_impact: float, assessment_count: int) -> str:
        """Determine overall pattern summary based on key metrics."""
        if assessment_count < 5:
            return "early_interaction_phase"
        elif avg_sophistication > 0.7 and avg_worthiness_impact > 0.05:
            return "sophisticated_positive_progression"
        elif avg_sophistication > 0.5 and avg_worthiness_impact > 0:
            return "steady_development"
        elif avg_sophistication < 0.3 or avg_worthiness_impact < -0.05:
            return "developmental_challenges"
        else:
            return "stable_baseline_interaction"

    def _calculate_consistency(self, scores: List[float]) -> float:
        """Calculate consistency score for a list of numeric values."""
        if len(scores) < 2:
            return 1.0

        # Calculate coefficient of variation (lower = more consistent)
        mean_score = sum(scores) / len(scores)
        if mean_score == 0:
            return 1.0

        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5
        cv = std_dev / mean_score

        # Convert to consistency score (higher = more consistent)
        return max(0.0, 1.0 - min(cv, 1.0))

    def _generate_behavioral_recommendations(self, avg_sophistication: float, avg_worthiness_impact: float,
                                           most_common_archetype: Optional[str], insights: List[str]) -> List[str]:
        """Generate behavioral development recommendations."""
        recommendations = []

        if avg_sophistication < 0.4:
            recommendations.append("Focus on demonstrating cultural awareness and refined communication")
        if avg_worthiness_impact < 0:
            recommendations.append("Work on consistency and authentic engagement patterns")
        if most_common_archetype:
            recommendations.append(f"Continue developing {most_common_archetype} archetype characteristics")
        if "authenticity" not in str(insights).lower():
            recommendations.append("Increase authentic vulnerability and genuine emotional expression")

        # Add general growth recommendations
        recommendations.append("Continue engaging across diverse interaction contexts")
        recommendations.append("Maintain consistent sophisticated interaction patterns")

        return recommendations


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
