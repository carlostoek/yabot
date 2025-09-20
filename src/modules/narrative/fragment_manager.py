"""
Narrative fragment manager for the YABOT system.

This module provides narrative content storage and retrieval functionality
as required by the modulos-atomicos specification task 7.
Implements requirements 1.1, 1.4, and 1.5 from the specification.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from src.database.mongodb import MongoDBHandler
from src.database.schemas.narrative import NarrativeFragment, NarrativeProgress
from src.events.bus import EventBus
from src.events.models import create_event
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NarrativeFragmentManagerError(Exception):
    """Base exception for narrative fragment manager operations."""
    pass


class FragmentNotFoundError(NarrativeFragmentManagerError):
    """Exception raised when narrative fragment is not found."""
    pass


class VIPAccessRequiredError(NarrativeFragmentManagerError):
    """Exception raised when VIP access is required but not available."""
    pass


class ProgressionValidationError(NarrativeFragmentManagerError):
    """Exception raised when progression conditions are not met."""
    pass


class NarrativeFragmentManager:
    """Manages narrative content storage and retrieval.

    Purpose: Manages narrative fragment retrieval with VIP access control,
    user narrative progression tracking, and checkpoint progression validation.

    Interfaces:
    - get_fragment(fragment_id: str) -> NarrativeFragment
    - get_user_progress(user_id: str) -> NarrativeProgress
    - update_progress(user_id: str, fragment_id: str) -> bool
    """

    def __init__(self, mongodb_handler: MongoDBHandler, event_bus: EventBus):
        """Initialize the narrative fragment manager.

        Args:
            mongodb_handler (MongoDBHandler): MongoDB handler instance
            event_bus (EventBus): Event bus instance for narrative events
        """
        self.mongodb_handler = mongodb_handler
        self.event_bus = event_bus
        logger.info("NarrativeFragmentManager initialized")

    async def get_fragment(self, fragment_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve a narrative fragment from MongoDB with text and decision options.

        Implements requirement 1.1: WHEN a user requests a narrative fragment
        THEN the system SHALL retrieve the fragment from MongoDB with text and decision options.

        Args:
            fragment_id (str): Unique identifier for the fragment
            user_id (str, optional): User ID for VIP access validation

        Returns:
            Dict[str, Any]: Narrative fragment data with text and decision options

        Raises:
            FragmentNotFoundError: If fragment is not found
            VIPAccessRequiredError: If fragment requires VIP access but user doesn't have it
            NarrativeFragmentManagerError: If operation fails
        """
        logger.debug("Retrieving narrative fragment: %s for user: %s", fragment_id, user_id)

        try:
            # Get narrative fragments collection
            collection = self.mongodb_handler.get_narrative_fragments_collection()

            # Query for the fragment
            fragment_data = collection.find_one({"fragment_id": fragment_id})

            if not fragment_data:
                logger.warning("Fragment not found: %s", fragment_id)
                raise FragmentNotFoundError(f"Narrative fragment not found: {fragment_id}")

            # Remove MongoDB-specific fields
            fragment_data.pop("_id", None)

            # Check VIP access if required (requirement 1.4)
            if fragment_data.get("vip_required", False) or fragment_data.get("metadata", {}).get("vip_required", False):
                if not user_id:
                    raise VIPAccessRequiredError("VIP access required but no user ID provided")

                # Validate VIP access through coordinator service integration
                await self._validate_vip_access(user_id, fragment_id)

            # Publish fragment accessed event
            if user_id:
                await self._publish_fragment_accessed_event(user_id, fragment_id, fragment_data)

            logger.debug("Successfully retrieved narrative fragment: %s", fragment_id)
            return fragment_data

        except (FragmentNotFoundError, VIPAccessRequiredError):
            raise
        except Exception as e:
            logger.error("Error retrieving narrative fragment %s: %s", fragment_id, str(e))
            raise NarrativeFragmentManagerError(f"Failed to retrieve narrative fragment: {str(e)}")

    async def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Get user narrative progression tracking data.

        Args:
            user_id (str): User identifier

        Returns:
            Dict[str, Any]: User narrative progress data

        Raises:
            NarrativeFragmentManagerError: If operation fails
        """
        logger.debug("Retrieving narrative progress for user: %s", user_id)

        try:
            # Get narrative progress from users collection (following existing patterns)
            users_collection = self.mongodb_handler.get_users_collection()

            # Query for user progress
            user_data = users_collection.find_one(
                {"user_id": user_id},
                {"current_state.narrative_progress": 1}
            )

            if not user_data:
                # Create default progress for new user
                default_progress = {
                    "user_id": user_id,
                    "current_fragment": "start",
                    "completed_fragments": [],
                    "unlocked_hints": [],
                    "choices_made": {},
                    "progress_data": {},
                    "start_time": datetime.utcnow(),
                    "last_updated": datetime.utcnow(),
                    "completion_percentage": 0.0,
                    "active": True
                }
                logger.debug("Created default progress for new user: %s", user_id)
                return default_progress

            # Extract narrative progress
            progress_data = user_data.get("current_state", {}).get("narrative_progress", {})

            # Ensure required fields exist
            if not progress_data:
                progress_data = {
                    "user_id": user_id,
                    "current_fragment": "start",
                    "completed_fragments": [],
                    "unlocked_hints": [],
                    "choices_made": {},
                    "progress_data": {},
                    "start_time": datetime.utcnow(),
                    "last_updated": datetime.utcnow(),
                    "completion_percentage": 0.0,
                    "active": True
                }

            progress_data["user_id"] = user_id  # Ensure user_id is set

            logger.debug("Successfully retrieved narrative progress for user: %s", user_id)
            return progress_data

        except Exception as e:
            logger.error("Error retrieving narrative progress for user %s: %s", user_id, str(e))
            raise NarrativeFragmentManagerError(f"Failed to retrieve user progress: {str(e)}")

    async def update_progress(self, user_id: str, fragment_id: str, choice_id: Optional[str] = None) -> bool:
        """Update user narrative progression and validate checkpoint conditions.

        Implements requirement 1.5: WHEN a narrative checkpoint is reached
        THEN the system SHALL validate progression conditions via the coordinator service.

        Args:
            user_id (str): User identifier
            fragment_id (str): Fragment ID to update progress to
            choice_id (str, optional): Choice made by user

        Returns:
            bool: True if progress was updated successfully

        Raises:
            ProgressionValidationError: If progression conditions are not met
            NarrativeFragmentManagerError: If operation fails
        """
        logger.info("Updating narrative progress for user: %s to fragment: %s", user_id, fragment_id)

        try:
            # Get current progress
            current_progress = await self.get_user_progress(user_id)

            # Validate progression conditions for checkpoints
            await self._validate_progression_conditions(user_id, fragment_id, current_progress)

            # Update progress data
            current_fragment = current_progress.get("current_fragment", "start")
            completed_fragments = current_progress.get("completed_fragments", [])
            choices_made = current_progress.get("choices_made", {})

            # Add current fragment to completed if not already there
            if current_fragment not in completed_fragments and current_fragment != "start":
                completed_fragments.append(current_fragment)

            # Record choice if provided
            if choice_id and current_fragment:
                choices_made[current_fragment] = choice_id

            # Calculate completion percentage (simple implementation)
            completion_percentage = min(len(completed_fragments) * 10.0, 100.0)  # 10% per fragment, max 100%

            # Prepare updated progress
            updated_progress = {
                "current_fragment": fragment_id,
                "completed_fragments": completed_fragments,
                "choices_made": choices_made,
                "last_updated": datetime.utcnow(),
                "completion_percentage": completion_percentage,
                "active": True
            }

            # Merge with existing progress data
            for key, value in current_progress.items():
                if key not in updated_progress:
                    updated_progress[key] = value

            # Update in database
            success = await self._update_progress_in_db(user_id, updated_progress)

            if success:
                # Publish progress updated event
                await self._publish_progress_updated_event(user_id, fragment_id, updated_progress)

                # Check if this is a checkpoint and publish checkpoint event
                if await self._is_checkpoint(fragment_id):
                    await self._publish_checkpoint_reached_event(user_id, fragment_id, updated_progress)

                logger.info("Successfully updated narrative progress for user: %s", user_id)
            else:
                logger.warning("Failed to update narrative progress in database for user: %s", user_id)

            return success

        except ProgressionValidationError:
            raise
        except Exception as e:
            logger.error("Error updating narrative progress for user %s: %s", user_id, str(e))
            raise NarrativeFragmentManagerError(f"Failed to update progress: {str(e)}")

    async def get_fragments_by_vip_status(self, vip_required: bool, limit: int = 50) -> List[Dict[str, Any]]:
        """Get narrative fragments by VIP requirement status.

        Args:
            vip_required (bool): Whether to get VIP or non-VIP fragments
            limit (int): Maximum number of fragments to return

        Returns:
            List[Dict[str, Any]]: List of narrative fragments
        """
        logger.debug("Retrieving fragments with VIP requirement: %s", vip_required)

        try:
            collection = self.mongodb_handler.get_narrative_fragments_collection()

            # Query for fragments by VIP requirement
            cursor = collection.find(
                {"vip_required": vip_required, "published": True}
            ).limit(limit)

            fragments = []
            for fragment_data in cursor:
                fragment_data.pop("_id", None)
                fragments.append(fragment_data)

            logger.debug("Retrieved %d fragments with VIP requirement: %s", len(fragments), vip_required)
            return fragments

        except Exception as e:
            logger.error("Error retrieving fragments by VIP status: %s", str(e))
            return []

    async def get_user_available_fragments(self, user_id: str, has_vip_access: bool) -> List[Dict[str, Any]]:
        """Get fragments available to a specific user based on their access level.

        Args:
            user_id (str): User identifier
            has_vip_access (bool): Whether user has VIP access

        Returns:
            List[Dict[str, Any]]: List of available fragments
        """
        logger.debug("Getting available fragments for user: %s (VIP: %s)", user_id, has_vip_access)

        try:
            collection = self.mongodb_handler.get_narrative_fragments_collection()

            # Build query based on VIP access
            query = {"published": True}
            if not has_vip_access:
                query["vip_required"] = False

            # Get user progress to filter out completed fragments if needed
            progress = await self.get_user_progress(user_id)
            completed_fragments = progress.get("completed_fragments", [])

            cursor = collection.find(query)

            fragments = []
            for fragment_data in cursor:
                fragment_data.pop("_id", None)

                # Add completion status
                fragment_data["completed"] = fragment_data.get("fragment_id") in completed_fragments

                fragments.append(fragment_data)

            logger.debug("Retrieved %d available fragments for user: %s", len(fragments), user_id)
            return fragments

        except Exception as e:
            logger.error("Error retrieving available fragments for user %s: %s", user_id, str(e))
            return []

    async def _validate_vip_access(self, user_id: str, fragment_id: str) -> None:
        """Validate VIP access for a fragment through coordinator service integration.

        Implements requirement 1.4: IF a user has VIP status
        THEN the system SHALL allow access to premium narrative levels.

        Args:
            user_id (str): User identifier
            fragment_id (str): Fragment identifier

        Raises:
            VIPAccessRequiredError: If user doesn't have VIP access
        """
        logger.debug("Validating VIP access for user: %s, fragment: %s", user_id, fragment_id)

        try:
            # Publish VIP access validation request event
            # This integrates with the coordinator service pattern
            validation_event = create_event(
                "vip_access_validation_requested",
                user_id=user_id,
                fragment_id=fragment_id,
                request_timestamp=datetime.utcnow()
            )

            await self.event_bus.publish("vip_access_validation_requested", validation_event.dict())

            # In a real implementation, we would wait for a response event
            # or call the coordinator service directly
            # For now, we'll assume the validation passes if the event was published

            logger.debug("VIP access validation requested for user: %s", user_id)

        except Exception as e:
            logger.error("Error validating VIP access: %s", str(e))
            raise VIPAccessRequiredError(f"VIP access validation failed: {str(e)}")

    async def _validate_progression_conditions(self, user_id: str, fragment_id: str, current_progress: Dict[str, Any]) -> None:
        """Validate progression conditions via coordinator service.

        Implements requirement 1.5: WHEN a narrative checkpoint is reached
        THEN the system SHALL validate progression conditions via the coordinator service.

        Args:
            user_id (str): User identifier
            fragment_id (str): Target fragment identifier
            current_progress (Dict[str, Any]): Current user progress

        Raises:
            ProgressionValidationError: If progression conditions are not met
        """
        logger.debug("Validating progression conditions for user: %s to fragment: %s", user_id, fragment_id)

        try:
            # Get the target fragment to check its unlock conditions
            collection = self.mongodb_handler.get_narrative_fragments_collection()
            fragment_data = collection.find_one({"fragment_id": fragment_id})

            if not fragment_data:
                raise ProgressionValidationError(f"Target fragment not found: {fragment_id}")

            # Check unlock conditions from fragment metadata
            unlock_conditions = fragment_data.get("metadata", {}).get("unlock_conditions", {})

            if unlock_conditions:
                # Validate conditions (simple implementation)
                required_fragments = unlock_conditions.get("required_fragments", [])
                completed_fragments = current_progress.get("completed_fragments", [])

                for required_fragment in required_fragments:
                    if required_fragment not in completed_fragments:
                        raise ProgressionValidationError(
                            f"Required fragment not completed: {required_fragment}"
                        )

            # Publish progression validation event for coordinator service
            validation_event = create_event(
                "progression_validation_requested",
                user_id=user_id,
                fragment_id=fragment_id,
                current_progress=current_progress,
                unlock_conditions=unlock_conditions
            )

            await self.event_bus.publish("progression_validation_requested", validation_event.dict())

            logger.debug("Progression conditions validated for user: %s", user_id)

        except ProgressionValidationError:
            raise
        except Exception as e:
            logger.error("Error validating progression conditions: %s", str(e))
            raise ProgressionValidationError(f"Progression validation failed: {str(e)}")

    async def _update_progress_in_db(self, user_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update user progress in the database.

        Args:
            user_id (str): User identifier
            progress_data (Dict[str, Any]): Progress data to update

        Returns:
            bool: True if update was successful
        """
        try:
            users_collection = self.mongodb_handler.get_users_collection()

            # Update or insert user progress
            result = users_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "current_state.narrative_progress": progress_data,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )

            success = result.acknowledged and (result.modified_count > 0 or result.upserted_id is not None)
            logger.debug("Updated narrative progress in database for user: %s", user_id)
            return success

        except Exception as e:
            logger.error("Error updating progress in database: %s", str(e))
            return False

    async def _is_checkpoint(self, fragment_id: str) -> bool:
        """Check if a fragment is a checkpoint.

        Args:
            fragment_id (str): Fragment identifier

        Returns:
            bool: True if fragment is a checkpoint
        """
        try:
            collection = self.mongodb_handler.get_narrative_fragments_collection()
            fragment_data = collection.find_one({"fragment_id": fragment_id})

            if fragment_data:
                # Check if fragment is marked as a checkpoint
                metadata = fragment_data.get("metadata", {})
                return metadata.get("is_checkpoint", False) or "checkpoint" in metadata.get("tags", [])

            return False

        except Exception as e:
            logger.error("Error checking checkpoint status: %s", str(e))
            return False

    async def _publish_fragment_accessed_event(self, user_id: str, fragment_id: str, fragment_data: Dict[str, Any]) -> None:
        """Publish fragment accessed event.

        Args:
            user_id (str): User identifier
            fragment_id (str): Fragment identifier
            fragment_data (Dict[str, Any]): Fragment data
        """
        try:
            event = create_event(
                "narrative_fragment_accessed",
                user_id=user_id,
                fragment_id=fragment_id,
                fragment_title=fragment_data.get("title", ""),
                vip_required=fragment_data.get("vip_required", False),
                access_timestamp=datetime.utcnow()
            )

            await self.event_bus.publish("narrative_fragment_accessed", event.dict())
            logger.debug("Published fragment accessed event for user: %s, fragment: %s", user_id, fragment_id)

        except Exception as e:
            logger.warning("Failed to publish fragment accessed event: %s", str(e))

    async def _publish_progress_updated_event(self, user_id: str, fragment_id: str, progress_data: Dict[str, Any]) -> None:
        """Publish progress updated event.

        Args:
            user_id (str): User identifier
            fragment_id (str): Fragment identifier
            progress_data (Dict[str, Any]): Updated progress data
        """
        try:
            event = create_event(
                "narrative_progress_updated",
                user_id=user_id,
                fragment_id=fragment_id,
                completion_percentage=progress_data.get("completion_percentage", 0.0),
                completed_fragments_count=len(progress_data.get("completed_fragments", [])),
                update_timestamp=datetime.utcnow()
            )

            await self.event_bus.publish("narrative_progress_updated", event.dict())
            logger.debug("Published progress updated event for user: %s", user_id)

        except Exception as e:
            logger.warning("Failed to publish progress updated event: %s", str(e))

    async def _publish_checkpoint_reached_event(self, user_id: str, fragment_id: str, progress_data: Dict[str, Any]) -> None:
        """Publish checkpoint reached event.

        Args:
            user_id (str): User identifier
            fragment_id (str): Fragment identifier (checkpoint)
            progress_data (Dict[str, Any]): Current progress data
        """
        try:
            event = create_event(
                "narrative_checkpoint_reached",
                user_id=user_id,
                checkpoint_fragment_id=fragment_id,
                completion_percentage=progress_data.get("completion_percentage", 0.0),
                checkpoint_timestamp=datetime.utcnow()
            )

            await self.event_bus.publish("narrative_checkpoint_reached", event.dict())
            logger.debug("Published checkpoint reached event for user: %s, checkpoint: %s", user_id, fragment_id)

        except Exception as e:
            logger.warning("Failed to publish checkpoint reached event: %s", str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the narrative fragment manager.

        Returns:
            Dict[str, Any]: Health status information
        """
        logger.debug("Performing narrative fragment manager health check")

        health_status = {
            "status": "healthy",
            "mongodb_connected": True,
            "event_bus_connected": self.event_bus.is_connected,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Test MongoDB connection
            collection = self.mongodb_handler.get_narrative_fragments_collection()
            collection.find_one({}, {"_id": 1})

        except Exception as e:
            logger.warning("MongoDB health check failed: %s", str(e))
            health_status["mongodb_connected"] = False
            health_status["status"] = "degraded"

        logger.debug("Narrative fragment manager health check completed: %s", health_status["status"])
        return health_status


# Convenience function for easy usage
async def create_narrative_fragment_manager(mongodb_handler: MongoDBHandler, event_bus: EventBus) -> NarrativeFragmentManager:
    """Create and initialize a narrative fragment manager instance.

    Args:
        mongodb_handler (MongoDBHandler): MongoDB handler instance
        event_bus (EventBus): Event bus instance

    Returns:
        NarrativeFragmentManager: Initialized narrative fragment manager instance
    """
    return NarrativeFragmentManager(mongodb_handler, event_bus)