"""
Decision engine for the YABOT system.

This module provides decision processing functionality for narrative choices
as required by the modulos-atomicos specification task 8.
Implements requirements 1.2, 1.5, and 4.4 from the specification.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from src.modules.narrative.fragment_manager import NarrativeFragmentManager
from src.services.coordinator import CoordinatorService
from src.database.mongodb import MongoDBHandler
from src.database.schemas.narrative import UserChoiceLog
from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DecisionEngineError(Exception):
    """Base exception for decision engine operations."""
    pass


class InvalidChoiceError(DecisionEngineError):
    """Exception raised when choice is invalid."""
    pass


class ProgressionValidationError(DecisionEngineError):
    """Exception raised when progression validation fails."""
    pass


class DecisionResult:
    """Result of processing a narrative decision."""

    def __init__(self, success: bool, next_fragment_id: Optional[str] = None,
                 message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Initialize decision result.

        Args:
            success (bool): Whether the decision was processed successfully
            next_fragment_id (str, optional): ID of the next fragment to show
            message (str, optional): Message to display to the user
            metadata (Dict[str, Any], optional): Additional result metadata
        """
        self.success = success
        self.next_fragment_id = next_fragment_id
        self.message = message
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class DecisionEngine:
    """Processes user narrative choices and determines outcomes.

    Purpose: Processes user narrative choices with validation, updates narrative state
    in database when decisions are made, publishes decision_made events to the event bus,
    validates progression conditions through coordinator service, and supports
    cross-module interactions through event publishing.

    Interfaces:
    - process_decision(user_id: str, choice_id: str) -> DecisionResult
    - validate_choice(user_id: str, choice_id: str) -> bool
    """

    def __init__(self, fragment_manager: NarrativeFragmentManager,
                 coordinator_service: CoordinatorService, mongodb_handler: MongoDBHandler,
                 event_bus: EventBus):
        """Initialize the decision engine.

        Args:
            fragment_manager (NarrativeFragmentManager): Fragment manager instance
            coordinator_service (CoordinatorService): Coordinator service instance
            mongodb_handler (MongoDBHandler): MongoDB handler instance
            event_bus (EventBus): Event bus instance for decision events
        """
        self.fragment_manager = fragment_manager
        self.coordinator_service = coordinator_service
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        logger.info("DecisionEngine initialized")

    async def process_decision(self, user_id: str, choice_id: str,
                             context: Optional[Dict[str, Any]] = None) -> DecisionResult:
        """Process user narrative choice and determine outcomes.

        Implements requirement 1.2: WHEN a user makes a narrative decision
        THEN the system SHALL update their narrative_state in the database
        and publish a decision_made event.

        Args:
            user_id (str): User identifier
            choice_id (str): Choice identifier made by user
            context (Dict[str, Any], optional): Additional context for the decision

        Returns:
            DecisionResult: Result of processing the decision

        Raises:
            InvalidChoiceError: If choice is invalid
            ProgressionValidationError: If progression validation fails
            DecisionEngineError: If operation fails
        """
        logger.info("Processing decision for user: %s, choice: %s", user_id, choice_id)

        try:
            # Validate the choice first
            is_valid = await self.validate_choice(user_id, choice_id)
            if not is_valid:
                raise InvalidChoiceError(f"Invalid choice: {choice_id} for user: {user_id}")

            # Get current user progress and fragment context
            current_progress = await self.fragment_manager.get_user_progress(user_id)
            current_fragment_id = current_progress.get("current_fragment", "start")

            # Enrich context with current state
            enriched_context = context or {}
            enriched_context.update({
                "fragment_id": current_fragment_id,
                "user_progress": current_progress,
                "decision_timestamp": datetime.utcnow(),
                "decision_id": str(uuid.uuid4())
            })

            # Get the current fragment to understand choice consequences
            current_fragment = await self.fragment_manager.get_fragment(current_fragment_id, user_id)
            choice_data = self._find_choice_in_fragment(current_fragment, choice_id)

            if not choice_data:
                raise InvalidChoiceError(f"Choice {choice_id} not found in fragment {current_fragment_id}")

            # Determine next fragment based on choice
            next_fragment_id = choice_data.get("next_fragment_id")

            # Validate progression conditions if moving to a new fragment (requirement 1.5)
            if next_fragment_id:
                await self._validate_progression_conditions(user_id, next_fragment_id, enriched_context)

            # Log the user choice for analytics
            await self._log_user_choice(user_id, current_fragment_id, choice_id, choice_data, enriched_context)

            # Update narrative state in database (requirement 1.2)
            if next_fragment_id:
                progress_updated = await self.fragment_manager.update_progress(
                    user_id, next_fragment_id, choice_id
                )
                if not progress_updated:
                    logger.warning("Failed to update progress for user: %s", user_id)
            else:
                # Update choices made even if staying on same fragment
                current_progress["choices_made"][current_fragment_id] = choice_id
                await self.fragment_manager._update_progress_in_db(user_id, current_progress)

            # Publish decision_made event (requirement 1.2 and 4.4)
            await self._publish_decision_made_event(user_id, choice_id, enriched_context)

            # Process decision through coordinator service for cross-module interactions
            await self.coordinator_service.handle_narrative_choice(user_id, choice_id, enriched_context)

            # Create successful result
            result = DecisionResult(
                success=True,
                next_fragment_id=next_fragment_id,
                message=choice_data.get("message", "Decision processed successfully"),
                metadata={
                    "choice_text": choice_data.get("text", ""),
                    "current_fragment": current_fragment_id,
                    "progression_valid": True,
                    "context": enriched_context
                }
            )

            logger.info("Successfully processed decision for user: %s, choice: %s", user_id, choice_id)
            return result

        except (InvalidChoiceError, ProgressionValidationError):
            raise
        except Exception as e:
            logger.error("Error processing decision for user %s: %s", user_id, str(e))
            raise DecisionEngineError(f"Failed to process decision: {str(e)}")

    async def validate_choice(self, user_id: str, choice_id: str) -> bool:
        """Validate if a choice is available to the user.

        Args:
            user_id (str): User identifier
            choice_id (str): Choice identifier to validate

        Returns:
            bool: True if choice is valid, False otherwise
        """
        logger.debug("Validating choice: %s for user: %s", choice_id, user_id)

        try:
            # Get current user progress
            current_progress = await self.fragment_manager.get_user_progress(user_id)
            current_fragment_id = current_progress.get("current_fragment", "start")

            # Get the current fragment
            try:
                current_fragment = await self.fragment_manager.get_fragment(current_fragment_id, user_id)
            except Exception as e:
                logger.warning("Could not get fragment %s for user %s: %s", current_fragment_id, user_id, str(e))
                return False

            # Check if choice exists in current fragment
            choice_data = self._find_choice_in_fragment(current_fragment, choice_id)
            if not choice_data:
                logger.debug("Choice %s not found in fragment %s", choice_id, current_fragment_id)
                return False

            # Validate choice conditions
            conditions = choice_data.get("conditions", {})
            if conditions:
                conditions_met = await self._validate_choice_conditions(user_id, conditions, current_progress)
                if not conditions_met:
                    logger.debug("Choice conditions not met for choice: %s", choice_id)
                    return False

            logger.debug("Choice validation successful: %s for user: %s", choice_id, user_id)
            return True

        except Exception as e:
            logger.error("Error validating choice %s for user %s: %s", choice_id, user_id, str(e))
            return False

    async def get_available_choices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all available choices for the user's current fragment.

        Args:
            user_id (str): User identifier

        Returns:
            List[Dict[str, Any]]: List of available choices with their data
        """
        logger.debug("Getting available choices for user: %s", user_id)

        try:
            # Get current user progress
            current_progress = await self.fragment_manager.get_user_progress(user_id)
            current_fragment_id = current_progress.get("current_fragment", "start")

            # Get the current fragment
            current_fragment = await self.fragment_manager.get_fragment(current_fragment_id, user_id)

            # Filter choices based on conditions
            available_choices = []
            choices = current_fragment.get("choices", [])

            for choice in choices:
                choice_id = choice.get("choice_id")
                if choice_id and await self.validate_choice(user_id, choice_id):
                    available_choices.append(choice)

            logger.debug("Found %d available choices for user: %s", len(available_choices), user_id)
            return available_choices

        except Exception as e:
            logger.error("Error getting available choices for user %s: %s", user_id, str(e))
            return []

    async def get_choice_consequences(self, user_id: str, choice_id: str) -> Dict[str, Any]:
        """Get potential consequences of making a specific choice.

        Args:
            user_id (str): User identifier
            choice_id (str): Choice identifier

        Returns:
            Dict[str, Any]: Information about choice consequences
        """
        logger.debug("Getting choice consequences for user: %s, choice: %s", user_id, choice_id)

        try:
            # Validate choice first
            is_valid = await self.validate_choice(user_id, choice_id)
            if not is_valid:
                return {"valid": False, "reason": "Choice not available"}

            # Get current fragment and choice data
            current_progress = await self.fragment_manager.get_user_progress(user_id)
            current_fragment_id = current_progress.get("current_fragment", "start")
            current_fragment = await self.fragment_manager.get_fragment(current_fragment_id, user_id)
            choice_data = self._find_choice_in_fragment(current_fragment, choice_id)

            if not choice_data:
                return {"valid": False, "reason": "Choice not found"}

            consequences = {
                "valid": True,
                "choice_text": choice_data.get("text", ""),
                "next_fragment_id": choice_data.get("next_fragment_id"),
                "immediate_effects": choice_data.get("metadata", {}).get("effects", {}),
                "rewards": choice_data.get("metadata", {}).get("rewards", {}),
                "risks": choice_data.get("metadata", {}).get("risks", {})
            }

            # Add preview of next fragment if available
            next_fragment_id = choice_data.get("next_fragment_id")
            if next_fragment_id:
                try:
                    next_fragment = await self.fragment_manager.get_fragment(next_fragment_id, user_id)
                    consequences["next_fragment_preview"] = {
                        "title": next_fragment.get("title", ""),
                        "description": next_fragment.get("metadata", {}).get("description", "")
                    }
                except Exception:
                    # If we can't get next fragment, it's not critical
                    pass

            return consequences

        except Exception as e:
            logger.error("Error getting choice consequences: %s", str(e))
            return {"valid": False, "reason": "Internal error"}

    def _find_choice_in_fragment(self, fragment: Dict[str, Any], choice_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific choice within a fragment.

        Args:
            fragment (Dict[str, Any]): Fragment data
            choice_id (str): Choice identifier to find

        Returns:
            Optional[Dict[str, Any]]: Choice data if found, None otherwise
        """
        choices = fragment.get("choices", [])
        for choice in choices:
            if choice.get("choice_id") == choice_id:
                return choice
        return None

    async def _validate_choice_conditions(self, user_id: str, conditions: Dict[str, Any],
                                        current_progress: Dict[str, Any]) -> bool:
        """Validate if choice conditions are met.

        Args:
            user_id (str): User identifier
            conditions (Dict[str, Any]): Choice conditions to validate
            current_progress (Dict[str, Any]): Current user progress

        Returns:
            bool: True if all conditions are met
        """
        try:
            # Check required fragments completion
            required_fragments = conditions.get("required_fragments", [])
            completed_fragments = current_progress.get("completed_fragments", [])

            for required_fragment in required_fragments:
                if required_fragment not in completed_fragments:
                    logger.debug("Required fragment not completed: %s", required_fragment)
                    return False

            # Check required choices
            required_choices = conditions.get("required_choices", {})
            choices_made = current_progress.get("choices_made", {})

            for fragment_id, required_choice in required_choices.items():
                if fragment_id not in choices_made or choices_made[fragment_id] != required_choice:
                    logger.debug("Required choice not made: %s in %s", required_choice, fragment_id)
                    return False

            # Check minimum progress percentage
            min_progress = conditions.get("min_progress_percentage", 0)
            current_progress_pct = current_progress.get("completion_percentage", 0)

            if current_progress_pct < min_progress:
                logger.debug("Insufficient progress: %s < %s", current_progress_pct, min_progress)
                return False

            return True

        except Exception as e:
            logger.error("Error validating choice conditions: %s", str(e))
            return False

    async def _validate_progression_conditions(self, user_id: str, next_fragment_id: str,
                                             context: Dict[str, Any]) -> None:
        """Validate progression conditions via coordinator service.

        Implements requirement 1.5: WHEN a narrative checkpoint is reached
        THEN the system SHALL validate progression conditions via the coordinator service.

        Args:
            user_id (str): User identifier
            next_fragment_id (str): Target fragment identifier
            context (Dict[str, Any]): Decision context

        Raises:
            ProgressionValidationError: If progression conditions are not met
        """
        logger.debug("Validating progression conditions for user: %s to fragment: %s",
                    user_id, next_fragment_id)

        try:
            # Get the target fragment to check if it's a checkpoint
            target_fragment = await self.fragment_manager.get_fragment(next_fragment_id, user_id)

            # Check if this is a checkpoint
            is_checkpoint = target_fragment.get("metadata", {}).get("is_checkpoint", False)

            if is_checkpoint:
                # Use fragment manager's validation (which publishes events to coordinator)
                current_progress = context.get("user_progress", {})
                await self.fragment_manager._validate_progression_conditions(
                    user_id, next_fragment_id, current_progress
                )

                logger.debug("Checkpoint progression validation passed for user: %s", user_id)
            else:
                logger.debug("Fragment %s is not a checkpoint, no special validation needed", next_fragment_id)

        except Exception as e:
            logger.error("Progression validation failed for user %s: %s", user_id, str(e))
            raise ProgressionValidationError(f"Progression validation failed: {str(e)}")

    async def _log_user_choice(self, user_id: str, fragment_id: str, choice_id: str,
                             choice_data: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Log user choice for analytics and replay.

        Args:
            user_id (str): User identifier
            fragment_id (str): Fragment where choice was made
            choice_id (str): Choice that was selected
            choice_data (Dict[str, Any]): Choice data
            context (Dict[str, Any]): Decision context
        """
        try:
            # Create choice log entry
            choice_log = {
                "log_id": str(uuid.uuid4()),
                "user_id": user_id,
                "fragment_id": fragment_id,
                "choice_id": choice_id,
                "choice_text": choice_data.get("text", ""),
                "timestamp": datetime.utcnow(),
                "session_id": context.get("session_id"),
                "context_data": {
                    "decision_id": context.get("decision_id"),
                    "user_progress_before": context.get("user_progress"),
                    "metadata": choice_data.get("metadata", {})
                },
                "completion_time_ms": context.get("completion_time_ms")
            }

            # Store in MongoDB
            collection = self.mongodb_handler.get_user_choice_logs_collection()
            collection.insert_one(choice_log)

            logger.debug("Logged user choice: %s for user: %s", choice_id, user_id)

        except Exception as e:
            logger.warning("Failed to log user choice: %s", str(e))

    async def _publish_decision_made_event(self, user_id: str, choice_id: str,
                                         context: Dict[str, Any]) -> None:
        """Publish decision_made event to the event bus.

        Implements requirement 1.2: publish a decision_made event
        Implements requirement 4.4: WHEN a decision_made event occurs THEN gamification
        SHALL potentially assign missions AND administration SHALL potentially grant access

        Args:
            user_id (str): User identifier
            choice_id (str): Choice identifier
            context (Dict[str, Any]): Decision context
        """
        try:
            # Create decision made event
            event = create_event(
                "decision_made",
                user_id=user_id,
                choice_id=choice_id,
                context=context
            )

            # Publish to event bus
            await self.event_bus.publish("decision_made", event.dict())

            logger.debug("Published decision_made event for user: %s, choice: %s", user_id, choice_id)

        except Exception as e:
            logger.warning("Failed to publish decision_made event: %s", str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the decision engine.

        Returns:
            Dict[str, Any]: Health status information
        """
        logger.debug("Performing decision engine health check")

        health_status = {
            "status": "healthy",
            "fragment_manager_healthy": True,
            "coordinator_service_available": True,
            "mongodb_connected": True,
            "event_bus_connected": self.event_bus.is_connected,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Test fragment manager health
            fragment_health = await self.fragment_manager.health_check()
            health_status["fragment_manager_healthy"] = fragment_health.get("status") == "healthy"

        except Exception as e:
            logger.warning("Fragment manager health check failed: %s", str(e))
            health_status["fragment_manager_healthy"] = False
            health_status["status"] = "degraded"

        try:
            # Test MongoDB connection
            collection = self.mongodb_handler.get_narrative_fragments_collection()
            collection.find_one({}, {"_id": 1})

        except Exception as e:
            logger.warning("MongoDB health check failed: %s", str(e))
            health_status["mongodb_connected"] = False
            health_status["status"] = "degraded"

        logger.debug("Decision engine health check completed: %s", health_status["status"])
        return health_status


# Convenience function for easy usage
async def create_decision_engine(fragment_manager: NarrativeFragmentManager,
                               coordinator_service: CoordinatorService,
                               mongodb_handler: MongoDBHandler,
                               event_bus: EventBus) -> DecisionEngine:
    """Create and initialize a decision engine instance.

    Args:
        fragment_manager (NarrativeFragmentManager): Fragment manager instance
        coordinator_service (CoordinatorService): Coordinator service instance
        mongodb_handler (MongoDBHandler): MongoDB handler instance
        event_bus (EventBus): Event bus instance

    Returns:
        DecisionEngine: Initialized decision engine instance
    """
    return DecisionEngine(fragment_manager, coordinator_service, mongodb_handler, event_bus)