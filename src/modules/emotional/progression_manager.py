"""
Narrative Progression Manager for the YABOT system.

This module is responsible for managing the user's progression through the
narrative levels, as specified in REQ-2 of the emocional specification.
"""

from typing import Dict, Any
from datetime import datetime

from src.services.subscription import SubscriptionService
from src.services.user import UserService
from src.utils.logger import get_logger
from src.database.schemas.emotional import ProgressionAssessment

logger = get_logger(__name__)


class NarrativeProgressionManager:
    """Manages the user's progression through the narrative levels."""

    def __init__(
        self,
        user_service: UserService,
        subscription_service: SubscriptionService,
    ):
        """Initialize the NarrativeProgressionManager.

        Args:
            user_service (UserService): Instance for user operations.
            subscription_service (SubscriptionService): Instance for subscription operations.
        """
        self.user_service = user_service
        self.subscription_service = subscription_service
        self.level_thresholds = {
            1: {"resonance_score": 0.6, "interactions": 10}, # To level 2
            2: {"resonance_score": 0.7, "interactions": 25}, # To level 3
            3: {"resonance_score": 0.8, "vulnerability_score": 0.5}, # To level 4 (Divan)
            4: {"resonance_score": 0.85, "authenticity_score": 0.7}, # To level 5
            5: {"resonance_score": 0.9, "relationship_depth": 0.8}, # To level 6 (Circle)
        }
        logger.info("NarrativeProgressionManager initialized")

    async def evaluate_level_readiness(
        self, user_id: str, emotional_metrics: Dict[str, Any]
    ) -> ProgressionAssessment:
        """Evaluates if a user is ready to progress to the next narrative level.

        Args:
            user_id (str): The ID of the user.
            emotional_metrics (Dict[str, Any]): The user's latest emotional metrics.

        Returns:
            ProgressionAssessment: An object detailing if the user is ready to progress.
        """
        logger.debug(f"Evaluating level readiness for user {user_id}")
        user_context = await self.user_service.get_user_context(user_id)
        if not user_context:
            return ProgressionAssessment(is_ready=False, reason="User not found.")

        current_level = user_context.get("state", {}).get("emotional_journey", {}).get("current_level", 1)
        
        if current_level >= 6:
            return ProgressionAssessment(is_ready=False, reason="User is already at the highest level.")

        next_level = current_level + 1
        thresholds = self.level_thresholds.get(current_level, {})

        for metric, threshold in thresholds.items():
            if emotional_metrics.get(metric, 0.0) < threshold:
                return ProgressionAssessment(
                    is_ready=False,
                    reason=f"Emotional metric '{metric}' ({emotional_metrics.get(metric, 0.0)}) is below threshold ({threshold})."
                )

        # Check for VIP access for levels 4 and above
        if next_level >= 4:
            has_vip = await self.validate_vip_access(user_id, next_level)
            if not has_vip:
                return ProgressionAssessment(
                    is_ready=False,
                    reason="VIP access is required to proceed to Divan levels.",
                    required_vip=True
                )

        return ProgressionAssessment(
            is_ready=True,
            next_level=next_level,
            reason="All progression criteria met."
        )

    async def advance_emotional_level(
        self, user_id: str, new_level: int, milestone_data: Dict[str, Any]
    ) -> bool:
        """Advances the user to a new emotional level.

        Args:
            user_id (str): The ID of the user.
            new_level (int): The new emotional level.
            milestone_data (Dict[str, Any]): Data about the milestone that triggered the progression.

        Returns:
            bool: True if the level was advanced successfully, False otherwise.
        """
        logger.info(f"Advancing user {user_id} to emotional level {new_level}")
        try:
            update_payload = {
                "emotional_journey.current_level": new_level,
                "emotional_journey.level_entry_date": datetime.utcnow(),
                "emotional_journey.progression_history": {
                    "$push": {
                        "level": new_level,
                        "reason": milestone_data.get("reason"),
                        "timestamp": datetime.utcnow(),
                    }
                }
            }
            return await self.user_service.update_user_state(user_id, update_payload)
        except Exception as e:
            logger.error(f"Error advancing emotional level for user {user_id}: {e}")
            return False

    async def validate_vip_access(self, user_id: str, requested_level: int) -> bool:
        """Validates if a user has VIP access for a given level.

        Args:
            user_id (str): The ID of the user.
            requested_level (int): The level being accessed.

        Returns:
            bool: True if the user has access, False otherwise.
        """
        if requested_level < 4:
            return True  # No VIP required for levels below 4

        logger.debug(f"Validating VIP access for user {user_id} for level {requested_level}")
        try:
            return await self.subscription_service.validate_vip_access(user_id)
        except Exception as e:
            logger.error(f"Error validating VIP access for user {user_id}: {e}")
            return False