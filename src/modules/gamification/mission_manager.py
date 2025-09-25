"""
Mission Manager - Gamification Missions System

This module implements the mission system for the YABOT gamification module
with mission assignment, progress tracking, and automatic event handling.
Implements requirements 2.3, 2.4, 4.4: mission system, progress tracking,
and event-driven automation.

The mission manager handles:
- Mission assignment and status management
- Progress tracking and updates
- Event subscription for automatic mission triggering
- Reward distribution upon mission completion
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field
import uuid

from motor.motor_asyncio import AsyncIOMotorClient
from src.events.models import BaseEvent
from src.events.bus import EventBus
from src.utils.logger import get_logger
from .besitos_wallet import BesitosWallet, BesitosTransactionType
from src.database.schemas.gamification import MissionMongoSchema


class MissionStatus(str, Enum):
    """
    Enumeration for mission statuses
    """
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class MissionType(str, Enum):
    """
    Enumeration for mission types
    """
    ENGAGEMENT = "engagement"  # React to posts, participate in decisions
    NARRATIVE = "narrative"     # Complete narrative fragments
    REACTION = "reaction"       # React to specific content
    TRIVIA = "trivia"           # Participate in trivia events
    DAILY = "daily"             # Daily challenges
    ACHIEVEMENT = "achievement" # Milestone-based missions
    SOCIAL = "social"           # Share, invite, social actions


class Mission(BaseModel):
    """
    Mission data model representing a user's assigned mission
    """
    mission_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    mission_type: MissionType
    title: str
    description: str
    objectives: List[Dict[str, Any]]  # List of objectives to complete
    progress: Dict[str, Any] = Field(default_factory=dict)  # Current progress per objective
    reward: Dict[str, Any]  # Reward upon completion (besitos, items, etc.)
    status: MissionStatus = MissionStatus.ASSIGNED
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MissionManager:
    """
    Mission manager implementation with assignment, progress tracking,
    and event subscription functionality.

    Implements requirements 2.3, 2.4, 4.4:
    - 2.3: Mission system with assignment and completion
    - 2.4: Mission progress tracking
    - 4.4: Event-driven automation for mission updates
    """

    def __init__(self, db_client: AsyncIOMotorClient, event_bus: EventBus, besitos_wallet: BesitosWallet):
        """
        Initialize the mission manager with database and event bus connections

        Args:
            db_client: MongoDB client for database operations
            event_bus: Event bus for publishing mission events
            besitos_wallet: Besitos wallet for reward distribution
        """
        self.db = db_client.get_database()
        self.event_bus = event_bus
        self.besitos_wallet = besitos_wallet
        self.logger = get_logger(self.__class__.__name__)

        # Collection references
        self.missions_collection = self.db.missions
        self.users_collection = self.db.users

        # Mission type to event mapping for automatic progress tracking
        self.event_handlers = {
            "reaction_detected": self._handle_reaction_event,
            "decision_made": self._handle_decision_event,
            "content_viewed": self._handle_content_viewed_event,
            "besitos_earned": self._handle_besitos_event,
            "subscription_updated": self._handle_subscription_event,
        }

        # Register event subscriptions
        self._register_event_subscriptions()

    async def _register_event_subscriptions(self):
        """
        Register event subscriptions for automatic mission progress updates
        """
        try:
            for event_type, handler in self.event_handlers.items():
                # Subscribe to events with the handler function
                await self.event_bus.subscribe(event_type, self._create_event_handler(event_type, handler))
            self.logger.info("Mission manager event subscriptions registered")
        except Exception as e:
            self.logger.error(
                "Error registering mission manager event subscriptions",
                error=str(e),
                error_type=type(e).__name__
            )

    def _create_event_handler(self, event_type: str, handler: Callable) -> Callable:
        """
        Create an event handler wrapper that can process event data

        Args:
            event_type: The type of event to handle
            handler: The specific handler function

        Returns:
            Callable wrapper for the event handler
        """
        async def wrapper(event_data: str):
            try:
                import json
                parsed_event = json.loads(event_data)
                # Call the specific handler with the parsed event data
                await handler(parsed_event)
            except Exception as e:
                self.logger.error(
                    "Error in mission manager event handler",
                    event_type=event_type,
                    error=str(e),
                    error_type=type(e).__name__
                )

        return wrapper

    async def assign_mission(self, user_id: str, mission_type: MissionType, 
                           title: str, description: str, 
                           objectives: List[Dict[str, Any]], 
                           reward: Dict[str, Any],
                           expires_in_days: Optional[int] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Optional[Mission]:
        """
        Assign a new mission to a user

        Args:
            user_id: User identifier
            mission_type: Type of mission to assign
            title: Mission title
            description: Mission description
            objectives: List of objectives to complete
            reward: Reward upon completion
            expires_in_days: Number of days until mission expires (optional)
            metadata: Additional metadata for the mission

        Returns:
            Mission object if successfully created, None otherwise
        """
        try:
            # Calculate expiration date if provided
            expires_at = None
            if expires_in_days:
                from datetime import timedelta
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            # Create mission object
            mission = Mission(
                user_id=user_id,
                mission_type=mission_type,
                title=title,
                description=description,
                objectives=objectives,
                reward=reward,
                status=MissionStatus.ASSIGNED,
                expires_at=expires_at,
                metadata=metadata or {}
            )

            # Insert mission document
            mission_doc = mission.dict()
            result = await self.missions_collection.insert_one(mission_doc)

            if result.inserted_id:
                self.logger.info(
                    "Mission assigned successfully",
                    mission_id=mission.mission_id,
                    user_id=user_id,
                    mission_type=mission_type.value
                )

                # Publish mission assigned event
                await self._publish_mission_event(
                    user_id=user_id,
                    mission_id=mission.mission_id,
                    event_type="mission_assigned",
                    mission_data=mission.dict()
                )

                return mission
            else:
                self.logger.error(
                    "Failed to assign mission - database insert failed",
                    user_id=user_id,
                    mission_type=mission_type.value
                )
                return None

        except Exception as e:
            self.logger.error(
                "Error assigning mission",
                user_id=user_id,
                mission_type=mission_type.value,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def get_user_missions(self, user_id: str, status_filter: Optional[MissionStatus] = None) -> List[Mission]:
        """
        Get all missions for a user with optional status filter

        Args:
            user_id: User identifier
            status_filter: Optional status to filter missions by

        Returns:
            List of Mission objects
        """
        try:
            query = {"user_id": user_id}
            if status_filter:
                query["status"] = status_filter.value

            cursor = self.missions_collection.find(query).sort("assigned_at", -1)
            missions = []

            async for doc in cursor:
                # Convert document to Mission object
                mission = Mission(**doc)
                missions.append(mission)

            return missions

        except Exception as e:
            self.logger.error(
                "Error getting user missions",
                user_id=user_id,
                status_filter=status_filter,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def get_active_missions(self, user_id: str) -> List[Mission]:
        """
        Get all active missions for a user (assigned or in progress)

        Args:
            user_id: User identifier

        Returns:
            List of active Mission objects
        """
        try:
            active_statuses = [MissionStatus.ASSIGNED, MissionStatus.IN_PROGRESS]
            query = {
                "user_id": user_id,
                "status": {"$in": [s.value for s in active_statuses]}
            }

            # Check for expired missions and update their status
            await self._check_expired_missions(user_id)

            cursor = self.missions_collection.find(query).sort("assigned_at", -1)
            missions = []

            async for doc in cursor:
                mission = Mission(**doc)
                missions.append(mission)

            return missions

        except Exception as e:
            self.logger.error(
                "Error getting active user missions",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return []

    async def update_progress(self, user_id: str, mission_id: str, 
                             objective_id: str, progress_data: Dict[str, Any]) -> bool:
        """
        Update progress for a specific mission objective

        Args:
            user_id: User identifier
            mission_id: Mission identifier
            objective_id: Objective identifier to update
            progress_data: Progress data to update the objective with

        Returns:
            True if progress was updated successfully, False otherwise
        """
        try:
            # Get the mission to verify it exists and belongs to user
            mission_doc = await self.missions_collection.find_one({
                "mission_id": mission_id,
                "user_id": user_id
            })

            if not mission_doc:
                self.logger.warning(
                    "Mission not found or doesn't belong to user",
                    mission_id=mission_id,
                    user_id=user_id
                )
                return False

            mission = Mission(**mission_doc)

            # Update progress dictionary with the new objective data
            current_progress = mission.progress.copy()
            current_progress[objective_id] = progress_data

            # Update the mission document with new progress
            result = await self.missions_collection.update_one(
                {"mission_id": mission_id, "user_id": user_id},
                {
                    "$set": {
                        "progress": current_progress,
                        "status": MissionStatus.IN_PROGRESS,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                self.logger.info(
                    "Mission progress updated",
                    mission_id=mission_id,
                    user_id=user_id,
                    objective_id=objective_id
                )

                # Check if mission is completed after progress update
                await self._check_mission_completion(user_id, mission_id)

                # Publish progress update event
                await self._publish_mission_event(
                    user_id=user_id,
                    mission_id=mission_id,
                    event_type="mission_progress_updated",
                    mission_data={
                        "objective_id": objective_id,
                        "progress_data": progress_data,
                        "total_progress": current_progress
                    }
                )

                return True
            else:
                self.logger.warning(
                    "No mission document was modified",
                    mission_id=mission_id,
                    user_id=user_id
                )
                return False

        except Exception as e:
            self.logger.error(
                "Error updating mission progress",
                mission_id=mission_id,
                user_id=user_id,
                objective_id=objective_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def complete_mission(self, user_id: str, mission_id: str) -> Optional[Dict[str, Any]]:
        """
        Complete a mission and distribute rewards

        Args:
            user_id: User identifier
            mission_id: Mission identifier

        Returns:
            Dict with completion result and reward information, None if failed
        """
        try:
            # Get the mission to verify it exists and belongs to user
            mission_doc = await self.missions_collection.find_one({
                "mission_id": mission_id,
                "user_id": user_id,
                "status": {"$in": [s.value for s in [MissionStatus.ASSIGNED, MissionStatus.IN_PROGRESS]]}
            })

            if not mission_doc:
                self.logger.warning(
                    "Mission not found, already completed, or doesn't belong to user",
                    mission_id=mission_id,
                    user_id=user_id
                )
                return None

            mission = Mission(**mission_doc)

            # Update mission status to completed
            result = await self.missions_collection.update_one(
                {"mission_id": mission_id, "user_id": user_id},
                {
                    "$set": {
                        "status": MissionStatus.COMPLETED,
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            if result.modified_count > 0:
                self.logger.info(
                    "Mission completed successfully",
                    mission_id=mission_id,
                    user_id=user_id
                )

                # Distribute rewards
                reward_result = await self._distribute_rewards(user_id, mission.reward)

                completion_result = {
                    "success": True,
                    "mission_id": mission_id,
                    "reward": mission.reward,
                    "reward_distributed": reward_result
                }

                # Publish mission completed event
                await self._publish_mission_event(
                    user_id=user_id,
                    mission_id=mission_id,
                    event_type="mission_completed",
                    mission_data=completion_result
                )

                return completion_result
            else:
                self.logger.warning(
                    "No mission document was modified during completion",
                    mission_id=mission_id,
                    user_id=user_id
                )
                return None

        except Exception as e:
            self.logger.error(
                "Error completing mission",
                mission_id=mission_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    async def _check_mission_completion(self, user_id: str, mission_id: str) -> bool:
        """
        Check if a mission is completed based on progress objectives

        Args:
            user_id: User identifier
            mission_id: Mission identifier

        Returns:
            True if mission was completed, False otherwise
        """
        try:
            # Get the mission document
            mission_doc = await self.missions_collection.find_one({
                "mission_id": mission_id,
                "user_id": user_id
            })

            if not mission_doc:
                return False

            mission = Mission(**mission_doc)

            # Check if all objectives are completed
            objectives_completed = True
            for objective in mission.objectives:
                objective_id = objective.get("id")
                if objective_id and objective_id in mission.progress:
                    progress = mission.progress[objective_id]
                    # Check if the objective is marked as completed
                    if not progress.get("completed", False):
                        objectives_completed = False
                        break
                else:
                    objectives_completed = False
                    break

            # If all objectives are completed, complete the mission
            if objectives_completed:
                return await self.complete_mission(user_id, mission_id) is not None

            return False

        except Exception as e:
            self.logger.error(
                "Error checking mission completion",
                mission_id=mission_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    async def _distribute_rewards(self, user_id: str, reward: Dict[str, Any]) -> Dict[str, Any]:
        """
        Distribute rewards for completed mission

        Args:
            user_id: User identifier
            reward: Reward specification dictionary

        Returns:
            Dict with reward distribution results
        """
        results = {
            "besitos_added": 0,
            "items_awarded": [],
            "other_rewards": {}
        }

        try:
            # Handle besitos reward
            if "besitos" in reward:
                besitos_amount = reward["besitos"]
                if besitos_amount > 0:
                    transaction_result = await self.besitos_wallet.add_besitos(
                        user_id=user_id,
                        amount=besitos_amount,
                        transaction_type=BesitosTransactionType.MISSION_COMPLETE,
                        description=f"Completed mission reward: {reward.get('description', 'Mission Completion')}",
                        reference_data={
                            "reference_type": "mission",
                            "reference_id": reward.get("mission_id", "unknown")
                        }
                    )
                    
                    if transaction_result.success:
                        results["besitos_added"] = besitos_amount
                        self.logger.info(
                            "Mission besitos reward distributed",
                            user_id=user_id,
                            besitos_amount=besitos_amount
                        )
                    else:
                        self.logger.error(
                            "Failed to distribute mission besitos reward",
                            user_id=user_id,
                            besitos_amount=besitos_amount,
                            error=transaction_result.error_message
                        )

            # Handle item rewards (placeholder - would connect to item manager)
            if "items" in reward:
                item_ids = reward["items"]
                results["items_awarded"] = item_ids
                # In a real implementation, this would connect to the item manager
                self.logger.info(
                    "Mission item rewards processed",
                    user_id=user_id,
                    item_ids=item_ids
                )

            # Handle other reward types
            for key, value in reward.items():
                if key not in ["besitos", "items", "description"]:
                    results["other_rewards"][key] = value

            return results

        except Exception as e:
            self.logger.error(
                "Error distributing mission rewards",
                user_id=user_id,
                reward=reward,
                error=str(e),
                error_type=type(e).__name__
            )
            return results

    async def _check_expired_missions(self, user_id: str) -> int:
        """
        Check for and update status of expired missions

        Args:
            user_id: User identifier

        Returns:
            Number of missions updated to expired status
        """
        try:
            now = datetime.utcnow()
            result = await self.missions_collection.update_many(
                {
                    "user_id": user_id,
                    "expires_at": {"$lt": now},
                    "status": {"$in": [MissionStatus.ASSIGNED.value, MissionStatus.IN_PROGRESS.value]}
                },
                {
                    "$set": {
                        "status": MissionStatus.EXPIRED,
                        "updated_at": now
                    }
                }
            )

            expired_count = result.modified_count
            if expired_count > 0:
                self.logger.info(
                    "Expired missions updated",
                    user_id=user_id,
                    expired_count=expired_count
                )

            return expired_count

        except Exception as e:
            self.logger.error(
                "Error checking expired missions",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return 0

    # Event handlers for automatic mission progress
    async def _handle_reaction_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle reaction detected events for mission progress

        Args:
            event_data: Event data from reaction event
        """
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                return

            # Look for missions that require reactions
            missions = await self.get_active_missions(user_id)
            for mission in missions:
                if mission.mission_type == MissionType.REACTION:
                    # Find objectives related to reactions
                    for objective in mission.objectives:
                        if objective.get("type") == "reaction_count":
                            # Update progress for reaction count objective
                            current_count = mission.progress.get("reaction_count", {}).get("count", 0)
                            new_count = current_count + 1

                            await self.update_progress(
                                user_id=user_id,
                                mission_id=mission.mission_id,
                                objective_id="reaction_count",
                                progress_data={
                                    "count": new_count,
                                    "completed": new_count >= objective.get("target", 1)
                                }
                            )

        except Exception as e:
            self.logger.error(
                "Error handling reaction event for missions",
                error=str(e),
                error_type=type(e).__name__
            )

    async def _handle_decision_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle decision made events for mission progress

        Args:
            event_data: Event data from decision event
        """
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                return

            # Look for missions that require narrative decisions
            missions = await self.get_active_missions(user_id)
            for mission in missions:
                if mission.mission_type == MissionType.NARRATIVE or mission.mission_type == MissionType.ENGAGEMENT:
                    # Find objectives related to decisions
                    for objective in mission.objectives:
                        if objective.get("type") == "decision_count":
                            # Update progress for decision count objective
                            current_count = mission.progress.get("decision_count", {}).get("count", 0)
                            new_count = current_count + 1

                            await self.update_progress(
                                user_id=user_id,
                                mission_id=mission.mission_id,
                                objective_id="decision_count",
                                progress_data={
                                    "count": new_count,
                                    "completed": new_count >= objective.get("target", 1)
                                }
                            )

        except Exception as e:
            self.logger.error(
                "Error handling decision event for missions",
                error=str(e),
                error_type=type(e).__name__
            )

    async def _handle_content_viewed_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle content viewed events for mission progress

        Args:
            event_data: Event data from content viewed event
        """
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                return

            # Look for missions that require content viewing
            missions = await self.get_active_missions(user_id)
            for mission in missions:
                if mission.mission_type == MissionType.NARRATIVE:
                    # Find objectives related to content viewing
                    for objective in mission.objectives:
                        if objective.get("type") == "content_view_count":
                            # Update progress for content view count objective
                            current_count = mission.progress.get("content_view_count", {}).get("count", 0)
                            new_count = current_count + 1

                            await self.update_progress(
                                user_id=user_id,
                                mission_id=mission.mission_id,
                                objective_id="content_view_count",
                                progress_data={
                                    "count": new_count,
                                    "completed": new_count >= objective.get("target", 1)
                                }
                            )

        except Exception as e:
            self.logger.error(
                "Error handling content viewed event for missions",
                error=str(e),
                error_type=type(e).__name__
            )

    async def _handle_besitos_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle besitos earned events for mission progress

        Args:
            event_data: Event data from besitos event
        """
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                return

            # Look for missions that require earning besitos
            missions = await self.get_active_missions(user_id)
            for mission in missions:
                if mission.mission_type == MissionType.ACHIEVEMENT:
                    # Find objectives related to besitos earning
                    for objective in mission.objectives:
                        if objective.get("type") == "besitos_earned":
                            current_amount = mission.progress.get("besitos_earned", {}).get("amount", 0)
                            earned_amount = event_data.get("amount", 0)
                            new_amount = current_amount + earned_amount

                            await self.update_progress(
                                user_id=user_id,
                                mission_id=mission.mission_id,
                                objective_id="besitos_earned",
                                progress_data={
                                    "amount": new_amount,
                                    "completed": new_amount >= objective.get("target", 10)
                                }
                            )

        except Exception as e:
            self.logger.error(
                "Error handling besitos event for missions",
                error=str(e),
                error_type=type(e).__name__
            )

    async def _handle_subscription_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle subscription updated events for mission progress

        Args:
            event_data: Event data from subscription event
        """
        try:
            user_id = event_data.get("user_id")
            if not user_id:
                return

            # Look for missions that require subscription status
            missions = await self.get_active_missions(user_id)
            for mission in missions:
                if mission.mission_type == MissionType.ACHIEVEMENT:
                    # Find objectives related to subscription status
                    for objective in mission.objectives:
                        if objective.get("type") == "subscription_status":
                            new_status = event_data.get("new_status")
                            target_status = objective.get("target_status", "active")

                            await self.update_progress(
                                user_id=user_id,
                                mission_id=mission.mission_id,
                                objective_id="subscription_status",
                                progress_data={
                                    "status": new_status,
                                    "completed": new_status == target_status
                                }
                            )

        except Exception as e:
            self.logger.error(
                "Error handling subscription event for missions",
                error=str(e),
                error_type=type(e).__name__
            )

    async def _publish_mission_event(self, user_id: str, mission_id: str, 
                                   event_type: str, mission_data: Dict[str, Any]) -> None:
        """
        Publish an event about mission activities

        Args:
            user_id: User ID
            mission_id: Mission identifier
            event_type: Type of mission event
            mission_data: Additional mission data to include in event
        """
        try:
            event_payload = {
                "user_id": user_id,
                "mission_id": mission_id,
                "event_type": event_type,
                "mission_data": mission_data,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Using BaseEvent with a generic payload since specific event models
            # may not be defined yet for mission events
            event = BaseEvent(
                event_type=f"mission_{event_type}",
                user_id=user_id,
                payload=event_payload
            )

            await self.event_bus.publish(f"mission_{event_type}", event_payload)
            self.logger.debug(
                "Mission event published",
                event_type=event_type,
                user_id=user_id,
                mission_id=mission_id
            )

        except Exception as e:
            self.logger.error(
                "Error publishing mission event",
                user_id=user_id,
                mission_id=mission_id,
                event_type=event_type,
                error=str(e),
                error_type=type(e).__name__
            )