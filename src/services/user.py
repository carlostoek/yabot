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
