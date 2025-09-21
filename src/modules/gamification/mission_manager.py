"""
Mission manager module for the YABOT system.

This module provides mission assignment and tracking functionality,
implementing requirements 2.3, 2.4, and 4.4 from the modulos-atomicos specification.
"""

import uuid
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from pymongo.collection import Collection
from pymongo.client_session import ClientSession
from pymongo.errors import PyMongoError

from src.database.mongodb import MongoDBHandler
from src.database.schemas.gamification import (
    Mission, MissionType, MissionStatus, MissionObjective,
    BesitosTransaction, TransactionType, TransactionStatus
)
from src.events.bus import EventBus
from src.events.models import DecisionMadeEvent, MissionCompletedEvent, BesitosAwardedEvent
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MissionManagerError(Exception):
    """Base exception for mission manager operations."""
    pass


class MissionNotFoundError(MissionManagerError):
    """Exception raised when mission is not found."""
    pass


class InvalidMissionError(MissionManagerError):
    """Exception raised when mission data is invalid."""
    pass


class Reward:
    """Represents a mission completion reward."""

    def __init__(self, besitos: int = 0, items: List[str] = None):
        self.besitos = besitos
        self.items = items or []


class MissionManager:
    """MongoDB-backed mission manager for dynamic mission assignment and tracking.

    Responsibilities:
    - Assign missions to users based on events and triggers
    - Track mission progress in MongoDB database
    - Handle mission completion with reward distribution
    - Publish mission_completed events when missions are finished
    - Subscribe to decision_made events to trigger mission assignments
    - Support mission templates and dynamic mission generation
    """

    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus):
        """Initialize the mission manager.

        Args:
            mongodb_handler (MongoDBHandler): MongoDB handler instance
            event_bus (EventBus): Event bus instance for publishing/subscribing
        """
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        self.missions: Collection = mongodb_handler.get_missions_collection()
        self.transactions: Collection = mongodb_handler.get_besitos_transactions_collection()
        self.users: Collection = mongodb_handler.get_users_collection()

        # Mission templates for dynamic generation
        self.mission_templates = {
            MissionType.DAILY: [
                {
                    "title": "Explora un Fragmento",
                    "description": "Lee un fragmento narrativo nuevo",
                    "objectives": [
                        {"objective_id": "read_fragment", "description": "Leer 1 fragmento", "target_value": 1}
                    ],
                    "reward_besitos": 10,
                    "expires_hours": 24
                },
                {
                    "title": "Toma una Decisión",
                    "description": "Haz una elección narrativa",
                    "objectives": [
                        {"objective_id": "make_decision", "description": "Hacer 1 decisión", "target_value": 1}
                    ],
                    "reward_besitos": 15,
                    "expires_hours": 24
                }
            ],
            MissionType.WEEKLY: [
                {
                    "title": "Narrativa Avanzada",
                    "description": "Progresa significativamente en la historia",
                    "objectives": [
                        {"objective_id": "read_fragments", "description": "Leer 5 fragmentos", "target_value": 5},
                        {"objective_id": "make_decisions", "description": "Hacer 3 decisiones", "target_value": 3}
                    ],
                    "reward_besitos": 100,
                    "expires_hours": 168  # 7 days
                }
            ],
            MissionType.STORY: [
                {
                    "title": "Desbloqueador de Historias",
                    "description": "Desbloquea contenido VIP usando pistas",
                    "objectives": [
                        {"objective_id": "unlock_hints", "description": "Desbloquear 2 pistas", "target_value": 2}
                    ],
                    "reward_besitos": 50,
                    "reward_items": ["special_hint"]
                }
            ],
            MissionType.SPECIAL: [
                {
                    "title": "Reaccionador Entusiasta",
                    "description": "Reacciona positivamente al contenido",
                    "objectives": [
                        {"objective_id": "react_content", "description": "Reaccionar 3 veces", "target_value": 3}
                    ],
                    "reward_besitos": 25
                }
            ]
        }

        logger.info("MissionManager initialized with %d mission templates",
                   sum(len(templates) for templates in self.mission_templates.values()))

    async def initialize(self) -> bool:
        """Initialize the mission manager and subscribe to events.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Subscribe to events that can trigger mission assignments
            await self.event_bus.subscribe("decision_made", self._handle_decision_made_event)
            await self.event_bus.subscribe("reaction_detected", self._handle_reaction_event)
            await self.event_bus.subscribe("user_interaction", self._handle_interaction_event)

            logger.info("MissionManager initialized and subscribed to events")
            return True

        except Exception as e:
            logger.error("Error initializing MissionManager: %s", str(e))
            return False

    async def assign_mission(self, user_id: str, mission_type: MissionType,
                           template_override: Optional[Dict[str, Any]] = None) -> Mission:
        """Assign a mission to a user based on type and optional template override.

        Args:
            user_id (str): User ID to assign mission to
            mission_type (MissionType): Type of mission to assign
            template_override (Dict[str, Any], optional): Override mission template data

        Returns:
            Mission: Created mission instance

        Raises:
            InvalidMissionError: If mission type is invalid or template not found
        """
        try:
            logger.debug("Assigning %s mission to user %s", mission_type.value, user_id)

            # Check if user already has an active mission of this type
            existing_mission = await self._get_active_mission(user_id, mission_type)
            if existing_mission:
                logger.debug("User %s already has active %s mission", user_id, mission_type.value)
                return Mission(**existing_mission)

            # Select mission template
            template = template_override or self._select_mission_template(mission_type)
            if not template:
                raise InvalidMissionError(f"No template found for mission type: {mission_type}")

            # Create mission from template
            mission = await self._create_mission_from_template(user_id, mission_type, template)

            # Save mission to database
            mission_doc = mission.dict()
            mission_doc["_id"] = mission.mission_id  # Use mission_id as MongoDB _id

            await self.missions.insert_one(mission_doc)

            logger.info("Assigned %s mission '%s' to user %s",
                       mission_type.value, mission.title, user_id)

            return mission

        except Exception as e:
            logger.error("Error assigning mission to user %s: %s", user_id, str(e))
            raise MissionManagerError(f"Failed to assign mission: {str(e)}")

    async def update_progress(self, user_id: str, mission_id: str, progress: Dict[str, Any]) -> bool:
        """Update progress for a specific mission objective.

        Args:
            user_id (str): User ID who owns the mission
            mission_id (str): Mission ID to update
            progress (Dict[str, Any]): Progress update with objective_id and increment

        Returns:
            bool: True if progress was updated successfully, False otherwise

        Requirements 2.3: Track progress in database via API
        """
        try:
            logger.debug("Updating progress for mission %s, user %s", mission_id, user_id)

            # Get current mission
            mission_doc = await self.missions.find_one({
                "mission_id": mission_id,
                "user_id": user_id,
                "status": {"$in": [MissionStatus.AVAILABLE.value, MissionStatus.IN_PROGRESS.value]}
            })

            if not mission_doc:
                logger.warning("Mission %s not found for user %s", mission_id, user_id)
                return False

            mission = Mission(**mission_doc)

            # Update objective progress
            objective_id = progress.get("objective_id")
            increment = progress.get("increment", 1)

            updated = False
            for objective in mission.objectives:
                if objective.objective_id == objective_id:
                    objective.current_value = min(
                        objective.current_value + increment,
                        objective.target_value
                    )
                    objective.completed = objective.current_value >= objective.target_value
                    updated = True
                    break

            if not updated:
                logger.warning("Objective %s not found in mission %s", objective_id, mission_id)
                return False

            # Check if mission is completed
            all_completed = all(obj.completed for obj in mission.objectives)
            if all_completed and mission.status != MissionStatus.COMPLETED:
                mission.status = MissionStatus.COMPLETED
                mission.completed_at = datetime.utcnow()

                # Complete mission and distribute rewards
                await self._complete_mission(mission)
            elif mission.status == MissionStatus.AVAILABLE:
                mission.status = MissionStatus.IN_PROGRESS
                mission.started_at = datetime.utcnow()

            mission.updated_at = datetime.utcnow()

            # Save updated mission
            await self.missions.replace_one(
                {"mission_id": mission_id, "user_id": user_id},
                mission.dict()
            )

            logger.debug("Updated progress for mission %s: %s", mission_id, progress)
            return True

        except Exception as e:
            logger.error("Error updating mission progress: %s", str(e))
            return False

    async def complete_mission(self, user_id: str, mission_id: str) -> Reward:
        """Manually complete a mission and distribute rewards.

        Args:
            user_id (str): User ID who owns the mission
            mission_id (str): Mission ID to complete

        Returns:
            Reward: Distributed reward information

        Raises:
            MissionNotFoundError: If mission is not found or already completed
        """
        try:
            logger.debug("Manually completing mission %s for user %s", mission_id, user_id)

            # Get mission
            mission_doc = await self.missions.find_one({
                "mission_id": mission_id,
                "user_id": user_id,
                "status": {"$ne": MissionStatus.COMPLETED.value}
            })

            if not mission_doc:
                raise MissionNotFoundError(f"Mission {mission_id} not found or already completed")

            mission = Mission(**mission_doc)

            # Complete all objectives
            for objective in mission.objectives:
                objective.current_value = objective.target_value
                objective.completed = True

            mission.status = MissionStatus.COMPLETED
            mission.completed_at = datetime.utcnow()
            mission.updated_at = datetime.utcnow()

            # Save completed mission
            await self.missions.replace_one(
                {"mission_id": mission_id, "user_id": user_id},
                mission.dict()
            )

            # Distribute rewards
            reward = await self._distribute_rewards(mission)

            logger.info("Manually completed mission '%s' for user %s", mission.title, user_id)
            return reward

        except Exception as e:
            logger.error("Error manually completing mission: %s", str(e))
            raise MissionManagerError(f"Failed to complete mission: {str(e)}")

    async def get_user_missions(self, user_id: str, status: Optional[MissionStatus] = None) -> List[Mission]:
        """Get missions for a specific user, optionally filtered by status.

        Args:
            user_id (str): User ID to get missions for
            status (MissionStatus, optional): Filter by mission status

        Returns:
            List[Mission]: List of user missions
        """
        try:
            query = {"user_id": user_id}
            if status:
                query["status"] = status.value

            cursor = self.missions.find(query, {"_id": 0}).sort("created_at", -1)
            mission_docs = await cursor.to_list(length=None)

            return [Mission(**doc) for doc in mission_docs]

        except Exception as e:
            logger.error("Error getting user missions: %s", str(e))
            return []

    async def get_mission(self, mission_id: str, user_id: Optional[str] = None) -> Optional[Mission]:
        """Get a specific mission by ID.

        Args:
            mission_id (str): Mission ID to retrieve
            user_id (str, optional): User ID for additional validation

        Returns:
            Mission: Mission instance if found, None otherwise
        """
        try:
            query = {"mission_id": mission_id}
            if user_id:
                query["user_id"] = user_id

            mission_doc = await self.missions.find_one(query, {"_id": 0})
            if mission_doc:
                return Mission(**mission_doc)
            return None

        except Exception as e:
            logger.error("Error getting mission %s: %s", mission_id, str(e))
            return None

    async def expire_missions(self) -> int:
        """Expire missions that have passed their expiration time.

        Returns:
            int: Number of missions expired
        """
        try:
            current_time = datetime.utcnow()

            result = await self.missions.update_many(
                {
                    "status": {"$in": [MissionStatus.AVAILABLE.value, MissionStatus.IN_PROGRESS.value]},
                    "expires_at": {"$lt": current_time}
                },
                {
                    "$set": {
                        "status": MissionStatus.EXPIRED.value,
                        "updated_at": current_time
                    }
                }
            )

            expired_count = result.modified_count
            if expired_count > 0:
                logger.info("Expired %d missions", expired_count)

            return expired_count

        except Exception as e:
            logger.error("Error expiring missions: %s", str(e))
            return 0

    # Private methods

    async def _get_active_mission(self, user_id: str, mission_type: MissionType) -> Optional[Dict[str, Any]]:
        """Get active mission of specific type for user."""
        return await self.missions.find_one({
            "user_id": user_id,
            "type": mission_type.value,
            "status": {"$in": [MissionStatus.AVAILABLE.value, MissionStatus.IN_PROGRESS.value]}
        }, {"_id": 0})

    def _select_mission_template(self, mission_type: MissionType) -> Optional[Dict[str, Any]]:
        """Select a mission template based on type."""
        templates = self.mission_templates.get(mission_type, [])
        if not templates:
            return None

        # For now, select the first template. In future, could add randomization or user-specific logic
        return templates[0]

    async def _create_mission_from_template(self, user_id: str, mission_type: MissionType,
                                          template: Dict[str, Any]) -> Mission:
        """Create a mission instance from a template."""
        mission_id = str(uuid.uuid4())
        current_time = datetime.utcnow()

        # Create objectives from template
        objectives = []
        for obj_template in template.get("objectives", []):
            objective = MissionObjective(
                objective_id=obj_template["objective_id"],
                description=obj_template["description"],
                target_value=obj_template["target_value"],
                current_value=0,
                completed=False
            )
            objectives.append(objective)

        # Calculate expiration time
        expires_at = None
        if "expires_hours" in template:
            expires_at = current_time + timedelta(hours=template["expires_hours"])

        # Create mission
        mission = Mission(
            mission_id=mission_id,
            user_id=user_id,
            title=template["title"],
            description=template["description"],
            type=mission_type,
            status=MissionStatus.AVAILABLE,
            objectives=objectives,
            reward_besitos=template.get("reward_besitos", 0),
            reward_items=template.get("reward_items", []),
            expires_at=expires_at,
            created_at=current_time,
            updated_at=current_time
        )

        return mission

    async def _complete_mission(self, mission: Mission) -> None:
        """Complete mission and handle rewards and events."""
        try:
            # Distribute rewards
            reward = await self._distribute_rewards(mission)

            # Publish mission_completed event (Requirement 2.4)
            await self._publish_mission_completed_event(mission, reward)

            logger.info("Completed mission '%s' for user %s with %d besitos reward",
                       mission.title, mission.user_id, reward.besitos)

        except Exception as e:
            logger.error("Error completing mission %s: %s", mission.mission_id, str(e))

    async def _distribute_rewards(self, mission: Mission) -> Reward:
        """Distribute mission completion rewards."""
        reward = Reward(besitos=mission.reward_besitos, items=mission.reward_items)

        try:
            # Award besitos if specified
            if mission.reward_besitos > 0:
                await self._award_besitos(
                    mission.user_id,
                    mission.reward_besitos,
                    f"Misión completada: {mission.title}",
                    mission.mission_id
                )

            # Award items if specified
            if mission.reward_items:
                await self._award_items(mission.user_id, mission.reward_items, mission.mission_id)

            return reward

        except Exception as e:
            logger.error("Error distributing rewards for mission %s: %s", mission.mission_id, str(e))
            return Reward()  # Return empty reward on error

    async def _award_besitos(self, user_id: str, amount: int, reason: str, reference_id: str) -> None:
        """Award besitos to user for mission completion."""
        try:
            # Get current user balance
            user_doc = await self.users.find_one({"user_id": user_id}, {"besitos_balance": 1})
            current_balance = user_doc.get("besitos_balance", 0) if user_doc else 0

            # Create transaction
            transaction = BesitosTransaction(
                transaction_id=str(uuid.uuid4()),
                user_id=user_id,
                type=TransactionType.AWARDED,
                amount=amount,
                balance_before=current_balance,
                balance_after=current_balance + amount,
                status=TransactionStatus.COMPLETED,
                reason=reason,
                source="mission",
                reference_id=reference_id,
                completed_at=datetime.utcnow()
            )

            # Save transaction and update user balance atomically
            async with await self.mongodb_handler._db.start_session() as session:
                async with session.start_transaction():
                    await self.transactions.insert_one(transaction.dict(), session=session)
                    await self.users.update_one(
                        {"user_id": user_id},
                        {"$inc": {"besitos_balance": amount}},
                        session=session
                    )

            # Publish besitos awarded event
            from src.events.models import create_event
            
            event = create_event(
                "besitos_awarded",
                user_id=user_id,
                transaction_id=transaction.transaction_id,
                amount=amount,
                reason=reason,
                source="mission",
                balance_after=current_balance + amount
            )

            await self.event_bus.publish("besitos_awarded", event.dict())

            logger.debug("Awarded %d besitos to user %s for mission completion", amount, user_id)

        except Exception as e:
            logger.error("Error awarding besitos: %s", str(e))

    async def _award_items(self, user_id: str, item_ids: List[str], reference_id: str) -> None:
        """Award items to user for mission completion."""
        try:
            # Publish item award events (let item manager handle the actual awarding)
            for item_id in item_ids:
                from src.events.models import create_event
                
                event = create_event(
                    "item_awarded",
                    user_id=user_id,
                    item_id=item_id,
                    quantity=1,
                    source="mission"
                )

                await self.event_bus.publish("item_awarded", event.dict())

            logger.debug("Awarded items %s to user %s for mission completion", item_ids, user_id)

        except Exception as e:
            logger.error("Error awarding items: %s", str(e))

    async def _publish_mission_completed_event(self, mission: Mission, reward: Reward) -> None:
        """Publish mission_completed event (Requirement 2.4)."""
        try:
            from src.events.models import create_event
            
            event = create_event(
                "mission_completed",
                user_id=mission.user_id,
                mission_id=mission.mission_id,
                mission_type=mission.type.value,
                reward_besitos=reward.besitos,
                reward_items=reward.items
            )

            await self.event_bus.publish("mission_completed", event.dict())

            logger.debug("Published mission_completed event for mission %s", mission.mission_id)

        except Exception as e:
            logger.error("Error publishing mission_completed event: %s", str(e))

    # Event handlers for automatic mission assignment (Requirement 4.4)

    async def _handle_decision_made_event(self, event_data: Dict[str, Any]) -> None:
        """Handle decision_made events to potentially assign missions."""
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                return

            logger.debug("Handling decision_made event for user %s", user_id)

            # Update existing decision-related missions
            await self._update_decision_missions(user_id)

            # Potentially assign new missions based on decision patterns
            await self._maybe_assign_story_mission(user_id)

        except Exception as e:
            logger.error("Error handling decision_made event: %s", str(e))

    async def _handle_reaction_event(self, event_data: Dict[str, Any]) -> None:
        """Handle reaction_detected events to potentially assign missions."""
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                return

            logger.debug("Handling reaction_detected event for user %s", user_id)

            # Update existing reaction-related missions
            await self._update_reaction_missions(user_id)

            # Potentially assign special reaction missions
            await self._maybe_assign_special_mission(user_id)

        except Exception as e:
            logger.error("Error handling reaction_detected event: %s", str(e))

    async def _handle_interaction_event(self, event_data: Dict[str, Any]) -> None:
        """Handle user_interaction events to potentially assign missions."""
        try:
            user_id = event_data.get("user_id")
            action = event_data.get("action")

            if not user_id or not action:
                return

            logger.debug("Handling user_interaction event for user %s: %s", user_id, action)

            # Update fragment reading missions
            if action == "fragment_read":
                await self._update_fragment_missions(user_id)

            # Assign daily missions for new users
            if action == "start":
                await self._maybe_assign_daily_missions(user_id)

        except Exception as e:
            logger.error("Error handling user_interaction event: %s", str(e))

    async def _update_decision_missions(self, user_id: str) -> None:
        """Update progress for decision-related missions."""
        # Find active missions with decision objectives
        cursor = self.missions.find({
            "user_id": user_id,
            "status": {"$in": [MissionStatus.AVAILABLE.value, MissionStatus.IN_PROGRESS.value]},
            "objectives.objective_id": {"$in": ["make_decision", "make_decisions"]}
        })

        async for mission_doc in cursor:
            mission = Mission(**mission_doc)
            for objective in mission.objectives:
                if objective.objective_id in ["make_decision", "make_decisions"] and not objective.completed:
                    await self.update_progress(user_id, mission.mission_id, {
                        "objective_id": objective.objective_id,
                        "increment": 1
                    })

    async def _update_reaction_missions(self, user_id: str) -> None:
        """Update progress for reaction-related missions."""
        cursor = self.missions.find({
            "user_id": user_id,
            "status": {"$in": [MissionStatus.AVAILABLE.value, MissionStatus.IN_PROGRESS.value]},
            "objectives.objective_id": "react_content"
        })

        async for mission_doc in cursor:
            mission = Mission(**mission_doc)
            for objective in mission.objectives:
                if objective.objective_id == "react_content" and not objective.completed:
                    await self.update_progress(user_id, mission.mission_id, {
                        "objective_id": "react_content",
                        "increment": 1
                    })

    async def _update_fragment_missions(self, user_id: str) -> None:
        """Update progress for fragment reading missions."""
        cursor = self.missions.find({
            "user_id": user_id,
            "status": {"$in": [MissionStatus.AVAILABLE.value, MissionStatus.IN_PROGRESS.value]},
            "objectives.objective_id": {"$in": ["read_fragment", "read_fragments"]}
        })

        async for mission_doc in cursor:
            mission = Mission(**mission_doc)
            for objective in mission.objectives:
                if objective.objective_id in ["read_fragment", "read_fragments"] and not objective.completed:
                    await self.update_progress(user_id, mission.mission_id, {
                        "objective_id": objective.objective_id,
                        "increment": 1
                    })

    async def _maybe_assign_daily_missions(self, user_id: str) -> None:
        """Maybe assign daily missions to new users."""
        try:
            # Check if user already has daily missions
            existing = await self._get_active_mission(user_id, MissionType.DAILY)
            if existing:
                return

            # Assign a daily mission
            await self.assign_mission(user_id, MissionType.DAILY)

        except Exception as e:
            logger.error("Error assigning daily missions: %s", str(e))

    async def _maybe_assign_story_mission(self, user_id: str) -> None:
        """Maybe assign story missions based on decision patterns."""
        try:
            # Check if user already has story missions
            existing = await self._get_active_mission(user_id, MissionType.STORY)
            if existing:
                return

            # Count recent decisions to determine if story mission should be assigned
            recent_decisions = await self.missions.count_documents({
                "user_id": user_id,
                "type": MissionType.DAILY.value,
                "status": MissionStatus.COMPLETED.value,
                "completed_at": {"$gte": datetime.utcnow() - timedelta(days=3)}
            })

            # Assign story mission if user has completed enough daily missions
            if recent_decisions >= 2:
                await self.assign_mission(user_id, MissionType.STORY)

        except Exception as e:
            logger.error("Error assigning story missions: %s", str(e))

    async def _maybe_assign_special_mission(self, user_id: str) -> None:
        """Maybe assign special missions based on reaction patterns."""
        try:
            # Check if user already has special missions
            existing = await self._get_active_mission(user_id, MissionType.SPECIAL)
            if existing:
                return

            # Assign special mission if conditions are met (simplified logic)
            await self.assign_mission(user_id, MissionType.SPECIAL)

        except Exception as e:
            logger.error("Error assigning special missions: %s", str(e))


async def create_mission_manager(mongodb_handler: MongoDBHandler, event_bus: EventBus) -> MissionManager:
    """Factory function for dependency injection consistency with other modules.

    Args:
        mongodb_handler (MongoDBHandler): MongoDB handler instance
        event_bus (EventBus): Event bus instance

    Returns:
        MissionManager: Initialized mission manager instance
    """
    mission_manager = MissionManager(mongodb_handler, event_bus)
    await mission_manager.initialize()
    return mission_manager