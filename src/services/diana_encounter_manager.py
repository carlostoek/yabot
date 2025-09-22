"""
Service to manage Diana's special encounters.
"""
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class EncounterTrigger(str, Enum):
    """Enum for what earned a Diana moment."""
    MILESTONE = "milestone"
    USER_REQUEST = "user_request"
    LUCIEN_GIFT = "lucien_gift"

class PersonalityLayer(str, Enum):
    """Enum for which aspect of Diana appears."""
    DIVAN = "divan"
    KINKY = "kinky"
    VULNERABLE = "vulnerable"

class PreparationLevel(str, Enum):
    """Enum for how ready the user is for the encounter."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TransitionContext(str, Enum):
    """Enum for how to return to Lucien."""
    GENTLE = "gentle"
    ABRUPT = "abrupt"
    GUIDED = "guided"

class MomentDuration(str, Enum):
    """Enum for how long Diana remains present."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

class RelationshipImpact(str, Enum):
    """Enum for how the encounter changes the relationship."""
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    TRANSFORMATIVE = "transformative"

class DianaSpecialMoment(BaseModel):
    """
    Represents a special, earned encounter with Diana.
    """
    trigger_condition: EncounterTrigger = Field(..., description="What earned this moment")
    diana_personality_layer: PersonalityLayer = Field(..., description="Which aspect of Diana appears")
    emotional_significance: float = Field(..., description="How precious this moment is")
    user_preparation_level: PreparationLevel = Field(..., description="How ready user is for this")
    lucien_transition_context: TransitionContext = Field(..., description="How to return to Lucien")
    moment_duration: MomentDuration = Field(..., description="How long Diana remains present")
    impact_on_relationship: RelationshipImpact = Field(..., description="How this changes everything")

class EncounterReadiness(BaseModel):
    """Defines if a user is ready for a Diana encounter."""
    is_ready: bool
    reason: Optional[str] = None

class UserProgress(BaseModel):
    """Represents a user's progress in the narrative."""
    narrative_level: int
    emotional_resonance: float
    last_encounter_time: Optional[datetime] = None

class DianaEncounterManager:
    """
    Orchestrates Diana's special encounters based on user progression and emotional readiness.
    """
    MIN_TIME_BETWEEN_ENCOUNTERS = timedelta(weeks=1)

    def __init__(self):
        """Initializes the DianaEncounterManager."""
        # In a real implementation, this would connect to other services
        # like the emotional intelligence service.
        pass

    def _is_frequency_ok(self, last_encounter_time: Optional[datetime]) -> tuple[bool, str]:
        """Checks if enough time has passed since the last encounter."""
        if last_encounter_time is None:
            return True, "No previous encounter recorded."
        
        time_since_last_encounter = datetime.now() - last_encounter_time
        if time_since_last_encounter < self.MIN_TIME_BETWEEN_ENCOUNTERS:
            return False, f"Not enough time has passed since the last encounter. Need to wait {self.MIN_TIME_BETWEEN_ENCOUNTERS - time_since_last_encounter}."

        return True, "Sufficient time has passed since the last encounter."

    async def evaluate_diana_encounter_readiness(
        self, user_progress: UserProgress, emotional_resonance: float
    ) -> EncounterReadiness:
        """
        Evaluates if a user is ready for a special encounter with Diana.

        This is a placeholder implementation. The logic should be based on narrative
        milestones, user's emotional state, and other factors.

        Args:
            user_progress: The user's current progress in the narrative.
            emotional_resonance: The user's current emotional resonance score.

        Returns:
            An EncounterReadiness object indicating if the user is ready.
        """
        frequency_ok, reason = self._is_frequency_ok(user_progress.last_encounter_time)
        if not frequency_ok:
            return EncounterReadiness(is_ready=False, reason=reason)

        # Placeholder logic: User is ready if narrative level is high enough
        # and emotional resonance is strong.
        if user_progress.narrative_level >= 4 and emotional_resonance > 0.75:
            return EncounterReadiness(is_ready=True, reason="User has reached a high narrative level with strong emotional resonance.")
        
        if user_progress.narrative_level < 4:
            return EncounterReadiness(is_ready=False, reason="User has not yet reached the required narrative level (El Diván).")

        if emotional_resonance <= 0.75:
            return EncounterReadiness(is_ready=False, reason="User's emotional resonance is not yet strong enough.")

        return EncounterReadiness(is_ready=False, reason="User is not yet ready for a special encounter.")
