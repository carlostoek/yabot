"""
Behavioral Analysis Engine for the YABOT system.

This module provides the core functionality for real-time behavioral analysis,
authenticity detection, and emotional signature analysis as specified in the
emocional specification.
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from collections import Counter

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Archetype(str, Enum):
    """Enumeration for user archetypes."""
    EXPLORADOR_PROFUNDO = "Explorador Profundo"
    DIRECTO_AUTENTICO = "Directo Auténtico"
    POETA_DEL_DESEO = "Poeta del Deseo"
    ANALITICO_EMPATICO = "Analítico Empático"
    PERSISTENTE_PACIENTE = "Persistente Paciente"


class BehavioralAnalysisEngine:
    """Engine for real-time authenticity detection and emotional signature analysis."""

    def __init__(self, database_manager: DatabaseManager, event_bus: EventBus):
        """Initialize the Behavioral Analysis Engine.

        Args:
            database_manager (DatabaseManager): Database manager instance for MongoDB access.
            event_bus (EventBus): Event bus instance for publishing analysis events.
        """
        self.database_manager = database_manager
        self.event_bus = event_bus
        logger.info("BehavioralAnalysisEngine initialized")

    async def analyze_response_timing(self, response_data: Dict[str, Any]) -> float:
        """Analyzes response timing to calculate an authenticity score.

        This method implements a simplified logic for authenticity scoring based on
        response time. Spontaneous, genuine responses are expected within an ideal
        time window. Responses that are too fast may be impulsive or automated,
        while responses that are too slow may be overly calculated.

        Args:
            response_data (Dict[str, Any]): A dictionary containing timing information,
                                            expected to have a 'response_time_seconds' key.

        Returns:
            float: An authenticity score between 0.0 and 1.0, where 1.0 is most authentic.
        """
        response_time = response_data.get("response_time_seconds")

        if response_time is None:
            logger.warning("'response_time_seconds' not found in response_data.")
            return 0.5  # Return a neutral score if timing is unavailable

        # Ideal response time window (in seconds) for authentic responses.
        # These values would be tuned based on user data.
        ideal_min_time = 2.0
        ideal_max_time = 15.0
        
        # Time window for plausible, but less ideal, responses.
        plausible_max_time = 60.0

        score = 0.0
        if ideal_min_time <= response_time <= ideal_max_time:
            # Responses within the ideal window are considered most authentic.
            score = 1.0
        elif response_time < ideal_min_time:
            # Very fast responses are penalized. Score increases linearly from 0 to 1.
            score = max(0, response_time / ideal_min_time)
        elif response_time <= plausible_max_time:
            # Responses outside the ideal but within plausible range are penalized.
            # Score decreases linearly from 1 to 0.
            score = 1.0 - ((response_time - ideal_max_time) / (plausible_max_time - ideal_max_time))
        else:
            # Very slow responses are considered least authentic.
            score = 0.0
        
        logger.debug(f"Analyzed response time of {response_time}s, authenticity score: {score:.2f}")
        
        return score

    async def detect_archetype_patterns(self, user_id: str) -> Optional[Archetype]:
        """Detects user archetype patterns based on their interaction history.

        This method queries the user's interaction history from MongoDB and applies
        a simplified logic to classify them into one of the defined archetypes.
        The logic is a placeholder and would be replaced by a more sophisticated
        model in a production environment.

        Args:
            user_id (str): The ID of the user to analyze.

        Returns:
            Optional[Archetype]: The detected archetype, or None if no pattern is clear.
        """
        logger.debug(f"Detecting archetype patterns for user {user_id}")
        try:
            db = self.database_manager.get_mongo_db()
            interactions_collection = db["emotional_interactions"]

            # Fetch the last 50 interactions for the user, sorted by time.
            # In a real system, this could be a more complex aggregation.
            cursor = interactions_collection.find({"user_id": user_id}).sort("created_at", -1).limit(50)
            interactions = await cursor.to_list(length=50)

            if not interactions:
                logger.debug(f"No interactions found for user {user_id} to determine archetype.")
                return None

            # Placeholder logic: Classify based on dominant interaction style.
            # This assumes 'interaction_style' is a field in the interaction documents.
            styles = [inter.get("archetype_indicators", {}).get("style") for inter in interactions]
            style_counts = Counter(s for s in styles if s)

            if not style_counts:
                logger.debug(f"No archetype indicators found in interactions for user {user_id}.")
                return None

            dominant_style = style_counts.most_common(1)[0][0]

            # Map dominant style to archetype
            archetype_map = {
                "methodical": Archetype.EXPLORADOR_PROFUNDO,
                "direct": Archetype.DIRECTO_AUTENTICO,
                "metaphorical": Archetype.POETA_DEL_DESEO,
                "reflective": Archetype.ANALITICO_EMPATICO,
                "consistent": Archetype.PERSISTENTE_PACIENTE,
            }

            archetype = archetype_map.get(dominant_style)
            
            if archetype:
                logger.info(f"Detected archetype for user {user_id}: {archetype.value}")
            else:
                logger.debug(f"Could not map dominant style '{dominant_style}' to an archetype for user {user_id}.")

            return archetype

        except Exception as e:
            logger.error(f"Error detecting archetype patterns for user {user_id}: {e}")
            return None

    async def calculate_emotional_resonance(self, interaction_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculates emotional resonance scores based on interaction metrics.

        This method computes a resonance score by combining metrics for authenticity,
        depth, and vulnerability. Each metric is weighted to produce a final
        emotional resonance score. This logic is a placeholder and can be expanded
        with more sophisticated calculations.

        Args:
            interaction_data (Dict[str, Any]): A dictionary containing metrics from the
                                               interaction, expected to have keys like
                                               'authenticity_score', 'depth_score',
                                               and 'vulnerability_score'.

        Returns:
            Dict[str, float]: A dictionary containing the individual scores and the
                              final combined 'resonance_score'.
        """
        authenticity = interaction_data.get("authenticity_score", 0.0)
        depth = interaction_data.get("depth_score", 0.0)
        vulnerability = interaction_data.get("vulnerability_score", 0.0)

        # Define weights for each component of the resonance score.
        # These would be tuned based on the desired emotional model.
        weights = {
            "authenticity": 0.5,
            "depth": 0.3,
            "vulnerability": 0.2,
        }

        # Calculate the weighted resonance score.
        resonance_score = (
            authenticity * weights["authenticity"] +
            depth * weights["depth"] +
            vulnerability * weights["vulnerability"]
        )
        
        # Ensure the score is capped at 1.0
        resonance_score = min(resonance_score, 1.0)

        metrics = {
            "authenticity_score": authenticity,
            "depth_score": depth,
            "vulnerability_score": vulnerability,
            "resonance_score": resonance_score,
        }

        logger.debug(f"Calculated emotional resonance metrics: {metrics}")

        return metrics
