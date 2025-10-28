"""
Achievement system module for the YABOT system.

This module provides achievement tracking and unlocking functionality,
implementing requirement 2.10 from the modulos-atomicos specification.
Enhanced with Lucien's sophisticated recognition as per
ux-enhanced specification task 21.
"""

import uuid
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from pymongo.collection import Collection
from pymongo.client_session import ClientSession
from pymongo.errors import PyMongoError

from src.database.mongodb import MongoDBHandler
from src.database.schemas.gamification import (
    UserAchievement, AchievementType, AchievementTier, AchievementProgress,
    AchievementUnlockedEvent
)
from src.events.bus import EventBus
from src.utils.logger import get_logger
from src.ui.lucien_voice_generator import (
    LucienVoiceProfile,
    generate_lucien_response,
    RelationshipLevel,
    LucienCelebration
)

logger = get_logger(__name__)


class AchievementSystemError(Exception):
    """Base exception for achievement system operations."""
    pass


class AchievementNotFoundError(AchievementSystemError):
    """Exception raised when achievement is not found."""
    pass


class InvalidAchievementError(AchievementSystemError):
    """Exception raised when achievement data is invalid."""
    pass


class Achievement:
    """Represents an achievement definition."""

    def __init__(self, achievement_id: str, title: str, description: str,
                 achievement_type: AchievementType, tier: AchievementTier,
                 target_value: int, reward_besitos: int = 0,
                 reward_items: List[str] = None, icon: str = None,
                 secret: bool = False, metadata: Dict[str, Any] = None):
        self.achievement_id = achievement_id
        self.title = title
        self.description = description
        self.type = achievement_type
        self.tier = tier
        self.target_value = target_value
        self.reward_besitos = reward_besitos
        self.reward_items = reward_items or []
        self.icon = icon
        self.secret = secret
        self.metadata = metadata or {}


class AchievementSystem:
    """Achievement system for tracking and unlocking user achievements (logros).

    This system tracks user achievements based on various actions and events,
    implementing requirement 2.10: WHEN logros (achievements) are unlocked THEN
    the system SHALL trigger database events and publish badge_unlocked events.
    """

    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus):
        """Initialize the achievement system.

        Args:
            mongodb_handler: MongoDB handler for database operations
            event_bus: Event bus for publishing achievement events
        """
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        self.user_achievements_collection: Collection = mongodb_handler.get_user_achievements_collection()
        self.users_collection: Collection = mongodb_handler.get_users_collection()

        # Define achievement templates
        self.achievement_definitions = {
            # Mission-based achievements
            "first_mission": Achievement(
                achievement_id="first_mission",
                title="Primer Paso",
                description="Completa tu primera misión",
                achievement_type=AchievementType.MILESTONE,
                tier=AchievementTier.BRONZE,
                target_value=1,
                reward_besitos=50,
                icon="🎯",
                metadata={"trigger_event": "mission_completed", "field": "missions_completed"}
            ),
            "mission_explorer": Achievement(
                achievement_id="mission_explorer",
                title="Explorador de Misiones",
                description="Completa 10 misiones",
                achievement_type=AchievementType.PROGRESS,
                tier=AchievementTier.SILVER,
                target_value=10,
                reward_besitos=200,
                icon="🗺️",
                metadata={"trigger_event": "mission_completed", "field": "missions_completed"}
            ),
            "mission_master": Achievement(
                achievement_id="mission_master",
                title="Maestro de Misiones",
                description="Completa 50 misiones",
                achievement_type=AchievementType.PROGRESS,
                tier=AchievementTier.GOLD,
                target_value=50,
                reward_besitos=1000,
                icon="👑",
                metadata={"trigger_event": "mission_completed", "field": "missions_completed"}
            ),

            # Besitos-based achievements
            "first_besitos": Achievement(
                achievement_id="first_besitos",
                title="Primeros Besitos",
                description="Gana tus primeros 100 besitos",
                achievement_type=AchievementType.MILESTONE,
                tier=AchievementTier.BRONZE,
                target_value=100,
                reward_besitos=25,
                icon="💰",
                metadata={"trigger_event": "besitos_added", "field": "total_besitos_earned"}
            ),
            "besitos_collector": Achievement(
                achievement_id="besitos_collector",
                title="Coleccionista de Besitos",
                description="Acumula 1000 besitos en total",
                achievement_type=AchievementType.PROGRESS,
                tier=AchievementTier.SILVER,
                target_value=1000,
                reward_besitos=100,
                icon="💎",
                metadata={"trigger_event": "besitos_added", "field": "total_besitos_earned"}
            ),
            "besitos_magnate": Achievement(
                achievement_id="besitos_magnate",
                title="Magnate de Besitos",
                description="Acumula 10000 besitos en total",
                achievement_type=AchievementType.PROGRESS,
                tier=AchievementTier.GOLD,
                target_value=10000,
                reward_besitos=500,
                icon="💸",
                metadata={"trigger_event": "besitos_added", "field": "total_besitos_earned"}
            ),

            # Reaction-based achievements
            "first_reaction": Achievement(
                achievement_id="first_reaction",
                title="Primera Reacción",
                description="Reacciona por primera vez al contenido",
                achievement_type=AchievementType.MILESTONE,
                tier=AchievementTier.BRONZE,
                target_value=1,
                reward_besitos=10,
                icon="❤️",
                metadata={"trigger_event": "reaction_detected", "field": "total_reactions"}
            ),
            "reaction_enthusiast": Achievement(
                achievement_id="reaction_enthusiast",
                title="Entusiasta de Reacciones",
                description="Reacciona 25 veces al contenido",
                achievement_type=AchievementType.PROGRESS,
                tier=AchievementTier.SILVER,
                target_value=25,
                reward_besitos=75,
                icon="😍",
                metadata={"trigger_event": "reaction_detected", "field": "total_reactions"}
            ),

            # Decision-based achievements
            "first_choice": Achievement(
                achievement_id="first_choice",
                title="Primera Decisión",
                description="Toma tu primera decisión narrativa",
                achievement_type=AchievementType.MILESTONE,
                tier=AchievementTier.BRONZE,
                target_value=1,
                reward_besitos=20,
                icon="🤔",
                metadata={"trigger_event": "decision_made", "field": "total_decisions"}
            ),
            "story_shaper": Achievement(
                achievement_id="story_shaper",
                title="Forjador de Historias",
                description="Toma 50 decisiones narrativas",
                achievement_type=AchievementType.PROGRESS,
                tier=AchievementTier.GOLD,
                target_value=50,
                reward_besitos=300,
                icon="📖",
                metadata={"trigger_event": "decision_made", "field": "total_decisions"}
            ),

            # Collection-based achievements
            "item_collector": Achievement(
                achievement_id="item_collector",
                title="Coleccionista de Objetos",
                description="Posee 5 objetos diferentes",
                achievement_type=AchievementType.COLLECTION,
                tier=AchievementTier.SILVER,
                target_value=5,
                reward_besitos=150,
                icon="🎒",
                metadata={"trigger_event": "item_acquired", "field": "unique_items_owned"}
            ),

            # Social achievements
            "trivia_participant": Achievement(
                achievement_id="trivia_participant",
                title="Participante de Trivia",
                description="Participa en tu primera trivia",
                achievement_type=AchievementType.MILESTONE,
                tier=AchievementTier.BRONZE,
                target_value=1,
                reward_besitos=30,
                icon="🧠",
                metadata={"trigger_event": "trivia_answered", "field": "trivias_participated"}
            ),

            # Special achievements
            "early_adopter": Achievement(
                achievement_id="early_adopter",
                title="Adoptante Temprano",
                description="Únete durante la fase beta",
                achievement_type=AchievementType.SPECIAL,
                tier=AchievementTier.PLATINUM,
                target_value=1,
                reward_besitos=500,
                reward_items=["beta_badge"],
                icon="🌟",
                secret=True,
                metadata={"trigger_event": "user_registered", "field": "early_adopter_status"}
            )
        }

        logger.info("AchievementSystem initialized with %d achievement definitions",
                   len(self.achievement_definitions))

    async def initialize(self) -> bool:
        """Initialize the achievement system and subscribe to events.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Subscribe to events that can trigger achievement progress
            await self.event_bus.subscribe("mission_completed", self._handle_mission_completed)
            await self.event_bus.subscribe("besitos_added", self._handle_besitos_added)
            await self.event_bus.subscribe("reaction_detected", self._handle_reaction_detected)
            await self.event_bus.subscribe("decision_made", self._handle_decision_made)
            await self.event_bus.subscribe("trivia_answered", self._handle_trivia_answered)
            await self.event_bus.subscribe("item_acquired", self._handle_item_acquired)
            await self.event_bus.subscribe("user_registered", self._handle_user_registered)

            logger.info("AchievementSystem initialized and subscribed to events")
            return True

        except Exception as e:
            logger.error("Error initializing achievement system: %s", str(e))
            return False

    async def check_achievements(self, user_id: str, action: str) -> List[Achievement]:
        """Check for achievement unlocks based on user action.

        Args:
            user_id: User ID to check achievements for
            action: Action that triggered the check

        Returns:
            List of newly unlocked achievements
        """
        logger.debug("Checking achievements for user %s on action %s", user_id, action)

        try:
            unlocked_achievements = []

            # Get relevant achievement definitions for this action
            relevant_achievements = [
                achievement for achievement in self.achievement_definitions.values()
                if achievement.metadata.get("trigger_event") == action
            ]

            if not relevant_achievements:
                logger.debug("No relevant achievements found for action: %s", action)
                return []

            # Check each relevant achievement
            for achievement_def in relevant_achievements:
                unlocked = await self._check_individual_achievement(user_id, achievement_def)
                if unlocked:
                    unlocked_achievements.append(unlocked)

            logger.debug("Found %d newly unlocked achievements for user %s",
                        len(unlocked_achievements), user_id)
            return unlocked_achievements

        except Exception as e:
            logger.error("Error checking achievements for user %s: %s", user_id, str(e))
            return []

    async def _generate_lucien_achievement_recognition(self, user_id: str, achievement: Achievement) -> LucienCelebration:
        """Generate Lucien's sophisticated recognition for an unlocked achievement.
        
        Args:
            user_id: User ID who unlocked the achievement
            achievement: Achievement that was unlocked
            
        Returns:
            LucienCelebration: Lucien's sophisticated recognition of the achievement
        """
        try:
            # For now, we'll create a basic Lucien voice profile
            # In a full implementation, this would be based on user's actual relationship with Lucien
            lucien_profile = LucienVoiceProfile()
            
            # Generate context for the achievement recognition
            lucien_context = {
                "achievement_title": achievement.title,
                "achievement_description": achievement.description,
                "achievement_tier": achievement.tier.value,
                "reward_besitos": achievement.reward_besitos,
                "user_id": user_id
            }
            
            # Generate Lucien's response
            lucien_response = generate_lucien_response(lucien_profile, "achievement_unlocked", lucien_context)
            
            # Create LucienCelebration instance
            celebration = LucienCelebration(
                achievement_id=achievement.achievement_id,
                lucien_recognition=lucien_response.response_text if lucien_response and lucien_response.response_text else 
                                 f"Su logro '{achievement.title}' ha sido registrado apropiadamente.",
                celebration_style="formal_appreciation"
            )
            
            return celebration
            
        except Exception as e:
            logger.warning("Failed to generate Lucien achievement recognition: %s", str(e))
            # Fallback to basic recognition
            return LucienCelebration(
                achievement_id=achievement.achievement_id,
                lucien_recognition=f"Su logro '{achievement.title}' ha sido registrado apropiadamente.",
                celebration_style="formal_appreciation"
            )

    async def unlock_achievement(self, user_id: str, achievement_id: str) -> bool:
        """Manually unlock an achievement for a user.

        Args:
            user_id: User ID to unlock achievement for
            achievement_id: Achievement ID to unlock

        Returns:
            bool: True if achievement was unlocked successfully
        """
        logger.info("Manually unlocking achievement %s for user %s", achievement_id, user_id)

        try:
            achievement_def = self.achievement_definitions.get(achievement_id)
            if not achievement_def:
                logger.error("Achievement definition not found: %s", achievement_id)
                raise AchievementNotFoundError(f"Achievement {achievement_id} not found")

            # Check if user already has this achievement
            existing_achievement = await self.user_achievements_collection.find_one({
                "user_id": user_id,
                "achievement_id": achievement_id
            })

            if existing_achievement and existing_achievement.get("completed", False):
                logger.warning("User %s already has achievement %s", user_id, achievement_id)
                return False

            # Create or update user achievement
            user_achievement_id = str(uuid.uuid4())
            current_time = datetime.utcnow()

            user_achievement = UserAchievement(
                user_achievement_id=user_achievement_id,
                user_id=user_id,
                achievement_id=achievement_id,
                title=achievement_def.title,
                description=achievement_def.description,
                type=achievement_def.type,
                tier=achievement_def.tier,
                progress=AchievementProgress(
                    current_value=achievement_def.target_value,
                    target_value=achievement_def.target_value,
                    percentage=100.0
                ),
                completed=True,
                reward_besitos=achievement_def.reward_besitos,
                reward_items=achievement_def.reward_items,
                icon=achievement_def.icon,
                secret=achievement_def.secret,
                completed_at=current_time,
                metadata=achievement_def.metadata
            )

            # Insert or update achievement
            await self.user_achievements_collection.update_one(
                {"user_id": user_id, "achievement_id": achievement_id},
                {"$set": user_achievement.dict()},
                upsert=True
            )

            # Generate Lucien's sophisticated achievement recognition
            lucien_recognition = await self._generate_lucien_achievement_recognition(user_id, achievement_def)
            logger.info("Lucien achievement recognition: %s", lucien_recognition.lucien_recognition)

            # Award besitos if specified
            if achievement_def.reward_besitos > 0:
                await self._award_achievement_reward(user_id, achievement_def)

            # Publish badge_unlocked event (requirement 2.10)
            await self._publish_badge_unlocked_event(user_id, achievement_def)

            logger.info("Achievement %s unlocked for user %s", achievement_id, user_id)
            return True

        except Exception as e:
            logger.error("Error unlocking achievement %s for user %s: %s",
                        achievement_id, user_id, str(e))
            return False

    async def get_user_achievements(self, user_id: str) -> List[UserAchievement]:
        """Get all achievements for a user.

        Args:
            user_id: User ID to get achievements for

        Returns:
            List of user achievements
        """
        logger.debug("Getting achievements for user %s", user_id)

        try:
            cursor = self.user_achievements_collection.find(
                {"user_id": user_id},
                {"_id": 0}  # Exclude MongoDB ObjectId
            ).sort("completed_at", -1)

            achievements = []
            async for doc in cursor:
                try:
                    achievement = UserAchievement(**doc)
                    achievements.append(achievement)
                except Exception as e:
                    logger.warning("Invalid achievement document for user %s: %s", user_id, str(e))

            logger.debug("Retrieved %d achievements for user %s", len(achievements), user_id)
            return achievements

        except PyMongoError as e:
            logger.error("Database error getting achievements for user %s: %s", user_id, str(e))
            raise AchievementSystemError(f"Failed to get achievements: {str(e)}")

    async def get_available_achievements(self, user_id: str) -> List[Achievement]:
        """Get available achievements that the user hasn't unlocked yet.

        Args:
            user_id: User ID to get available achievements for

        Returns:
            List of available achievement definitions
        """
        logger.debug("Getting available achievements for user %s", user_id)

        try:
            # Get user's current achievements
            user_achievements = await self.user_achievements_collection.find(
                {"user_id": user_id, "completed": True},
                {"achievement_id": 1}
            ).to_list(length=None)

            completed_achievement_ids = {ach["achievement_id"] for ach in user_achievements}

            # Filter out completed achievements and secret achievements
            available_achievements = [
                achievement for achievement_id, achievement in self.achievement_definitions.items()
                if achievement_id not in completed_achievement_ids and not achievement.secret
            ]

            logger.debug("Found %d available achievements for user %s",
                        len(available_achievements), user_id)
            return available_achievements

        except Exception as e:
            logger.error("Error getting available achievements for user %s: %s", user_id, str(e))
            return []

    async def _check_individual_achievement(self, user_id: str, achievement_def: Achievement) -> Optional[Achievement]:
        """Check if a specific achievement should be unlocked for a user.

        Args:
            user_id: User ID to check
            achievement_def: Achievement definition to check

        Returns:
            Achievement if unlocked, None otherwise
        """
        try:
            # Check if user already has this achievement
            existing_achievement = await self.user_achievements_collection.find_one({
                "user_id": user_id,
                "achievement_id": achievement_def.achievement_id
            })

            if existing_achievement and existing_achievement.get("completed", False):
                return None  # Already unlocked

            # Get user's current progress value for this achievement
            current_value = await self._get_user_progress_value(user_id, achievement_def)

            # Check if target value is reached
            if current_value >= achievement_def.target_value:
                # Unlock the achievement
                success = await self.unlock_achievement(user_id, achievement_def.achievement_id)
                if success:
                    return achievement_def

            else:
                # Update progress if achievement exists but not completed
                if existing_achievement:
                    await self._update_achievement_progress(user_id, achievement_def, current_value)

            return None

        except Exception as e:
            logger.error("Error checking individual achievement %s for user %s: %s",
                        achievement_def.achievement_id, user_id, str(e))
            return None

    async def _get_user_progress_value(self, user_id: str, achievement_def: Achievement) -> int:
        """Get the current progress value for a user's achievement.

        Args:
            user_id: User ID
            achievement_def: Achievement definition

        Returns:
            Current progress value
        """
        field = achievement_def.metadata.get("field")
        if not field:
            return 0

        try:
            user_doc = await self.users_collection.find_one(
                {"user_id": user_id},
                {f"stats.{field}": 1}
            )

            if not user_doc:
                return 0

            return user_doc.get("stats", {}).get(field, 0)

        except Exception as e:
            logger.error("Error getting progress value for user %s field %s: %s",
                        user_id, field, str(e))
            return 0

    async def _update_achievement_progress(self, user_id: str, achievement_def: Achievement, current_value: int) -> None:
        """Update achievement progress without unlocking.

        Args:
            user_id: User ID
            achievement_def: Achievement definition
            current_value: Current progress value
        """
        try:
            percentage = min(100.0, (current_value / achievement_def.target_value) * 100)

            progress = AchievementProgress(
                current_value=current_value,
                target_value=achievement_def.target_value,
                percentage=percentage
            )

            await self.user_achievements_collection.update_one(
                {"user_id": user_id, "achievement_id": achievement_def.achievement_id},
                {
                    "$set": {
                        "progress": progress.dict(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            logger.debug("Updated progress for achievement %s (user %s): %d/%d (%.1f%%)",
                        achievement_def.achievement_id, user_id, current_value,
                        achievement_def.target_value, percentage)

        except Exception as e:
            logger.error("Error updating achievement progress: %s", str(e))

    async def _award_achievement_reward(self, user_id: str, achievement_def: Achievement) -> None:
        """Award besitos reward for achievement unlock.

        Args:
            user_id: User ID
            achievement_def: Achievement definition
        """
        try:
            if achievement_def.reward_besitos > 0:
                # Import besitos wallet to award reward
                from src.modules.gamification.besitos_wallet import create_besitos_wallet

                besitos_wallet = await create_besitos_wallet(self.mongodb_handler, self.event_bus)
                await besitos_wallet.add_besitos(
                    user_id=user_id,
                    amount=achievement_def.reward_besitos,
                    reason=f"Achievement unlocked: {achievement_def.title}",
                    source="achievement",
                    reference_id=achievement_def.achievement_id
                )

                logger.info("Awarded %d besitos to user %s for achievement %s",
                           achievement_def.reward_besitos, user_id, achievement_def.achievement_id)

        except Exception as e:
            logger.error("Error awarding achievement reward: %s", str(e))

    async def _publish_badge_unlocked_event(self, user_id: str, achievement_def: Achievement) -> None:
        """Publish badge_unlocked event when achievement is unlocked (requirement 2.10).

        Args:
            user_id: User ID
            achievement_def: Achievement definition
        """
        try:
            from src.events.models import create_event

            event = create_event(
                "badge_unlocked",
                user_id=user_id,
                achievement_id=achievement_def.achievement_id,
                achievement_title=achievement_def.title,
                tier=achievement_def.tier,
                reward_besitos=achievement_def.reward_besitos,
                metadata={
                    "achievement_type": achievement_def.type,
                    "icon": achievement_def.icon,
                    "secret": achievement_def.secret
                }
            )

            await self.event_bus.publish("badge_unlocked", event.dict())
            logger.debug("Published badge_unlocked event for user %s achievement %s",
                        user_id, achievement_def.achievement_id)

        except Exception as e:
            # Don't fail the achievement unlock for event publishing errors
            logger.warning("Failed to publish badge_unlocked event for user %s: %s", user_id, str(e))

    # Event handlers for automatic achievement checking
    async def _handle_mission_completed(self, event_data: Dict[str, Any]) -> None:
        """Handle mission_completed event for achievement checking."""
        try:
            user_id = event_data.get("user_id")
            if user_id:
                await self._update_user_stat(user_id, "missions_completed", 1)
                await self.check_achievements(user_id, "mission_completed")
        except Exception as e:
            logger.error("Error handling mission_completed event: %s", str(e))

    async def _handle_besitos_added(self, event_data: Dict[str, Any]) -> None:
        """Handle besitos_added event for achievement checking."""
        try:
            user_id = event_data.get("user_id")
            amount = event_data.get("amount", 0)
            if user_id and amount > 0:
                await self._update_user_stat(user_id, "total_besitos_earned", amount)
                await self.check_achievements(user_id, "besitos_added")
        except Exception as e:
            logger.error("Error handling besitos_added event: %s", str(e))

    async def _handle_reaction_detected(self, event_data: Dict[str, Any]) -> None:
        """Handle reaction_detected event for achievement checking."""
        try:
            user_id = event_data.get("user_id")
            if user_id:
                await self._update_user_stat(user_id, "total_reactions", 1)
                await self.check_achievements(user_id, "reaction_detected")
        except Exception as e:
            logger.error("Error handling reaction_detected event: %s", str(e))

    async def _handle_decision_made(self, event_data: Dict[str, Any]) -> None:
        """Handle decision_made event for achievement checking."""
        try:
            user_id = event_data.get("user_id")
            if user_id:
                await self._update_user_stat(user_id, "total_decisions", 1)
                await self.check_achievements(user_id, "decision_made")
        except Exception as e:
            logger.error("Error handling decision_made event: %s", str(e))

    async def _handle_trivia_answered(self, event_data: Dict[str, Any]) -> None:
        """Handle trivia_answered event for achievement checking."""
        try:
            user_id = event_data.get("user_id")
            if user_id:
                await self._update_user_stat(user_id, "trivias_participated", 1)
                await self.check_achievements(user_id, "trivia_answered")
        except Exception as e:
            logger.error("Error handling trivia_answered event: %s", str(e))

    async def _handle_item_acquired(self, event_data: Dict[str, Any]) -> None:
        """Handle item_acquired event for achievement checking."""
        try:
            user_id = event_data.get("user_id")
            if user_id:
                # Count unique items owned
                await self._update_unique_items_count(user_id)
                await self.check_achievements(user_id, "item_acquired")
        except Exception as e:
            logger.error("Error handling item_acquired event: %s", str(e))

    async def _handle_user_registered(self, event_data: Dict[str, Any]) -> None:
        """Handle user_registered event for achievement checking."""
        try:
            user_id = event_data.get("user_id")
            if user_id:
                # Check for early adopter status (simplified for demo)
                await self._update_user_stat(user_id, "early_adopter_status", 1)
                await self.check_achievements(user_id, "user_registered")
        except Exception as e:
            logger.error("Error handling user_registered event: %s", str(e))

    async def _update_user_stat(self, user_id: str, stat_field: str, increment: int) -> None:
        """Update a user statistic field.

        Args:
            user_id: User ID
            stat_field: Statistics field to update
            increment: Value to increment by
        """
        try:
            await self.users_collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {f"stats.{stat_field}": increment},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                upsert=True
            )
        except Exception as e:
            logger.error("Error updating user stat %s for user %s: %s", stat_field, user_id, str(e))

    async def _update_unique_items_count(self, user_id: str) -> None:
        """Update the count of unique items owned by user.

        Args:
            user_id: User ID
        """
        try:
            # Count distinct item_ids for this user
            user_items_collection = self.mongodb_handler.get_user_items_collection()
            distinct_items = await user_items_collection.distinct("item_id", {"user_id": user_id})
            unique_count = len(distinct_items)

            await self.users_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "stats.unique_items_owned": unique_count,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error("Error updating unique items count for user %s: %s", user_id, str(e))


# Factory function for dependency injection consistency with other modules
async def create_achievement_system(mongodb_handler: MongoDBHandler, event_bus: EventBus) -> AchievementSystem:
    """Factory function to create an AchievementSystem instance.

    Args:
        mongodb_handler: MongoDB handler instance
        event_bus: Event bus instance

    Returns:
        AchievementSystem: Initialized achievement system instance
    """
    achievement_system = AchievementSystem(mongodb_handler, event_bus)
    await achievement_system.initialize()
    return achievement_system