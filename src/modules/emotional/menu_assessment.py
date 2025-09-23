"""
Menu Behavioral Assessment Event Handlers for the YABOT system.

This module provides behavioral assessment event handlers specifically for menu interactions,
tracking user navigation patterns, choice analysis, and menu-specific emotional indicators
to support Lucien's worthiness evaluation system as specified in REQ-MENU-007.2 and REQ-MENU-008.5.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.modules.emotional.behavioral_analysis import BehavioralAnalysisEngine, Archetype
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MenuInteractionType(str, Enum):
    """Types of menu interactions for behavioral assessment."""
    NAVIGATION = "navigation"
    SELECTION = "selection"
    RESTRICTION_ENCOUNTER = "restriction_encounter"
    VIP_EXPLORATION = "vip_exploration"
    BACK_NAVIGATION = "back_navigation"
    DEEP_EXPLORATION = "deep_exploration"
    REPEATED_ACCESS = "repeated_access"


class WorthinessIndicator(str, Enum):
    """Indicators for Lucien's worthiness assessment based on menu behavior."""
    RESPECTFUL_NAVIGATION = "respectful_navigation"
    PERSISTENT_EXPLORATION = "persistent_exploration"
    GRACEFUL_RESTRICTION_HANDLING = "graceful_restriction_handling"
    SOPHISTICATED_CHOICES = "sophisticated_choices"
    PATIENT_PROGRESSION = "patient_progression"
    IMPULSIVE_BEHAVIOR = "impulsive_behavior"
    AGGRESSIVE_ACCESS_ATTEMPTS = "aggressive_access_attempts"
    SHALLOW_ENGAGEMENT = "shallow_engagement"


class MenuBehavioralAssessmentHandler:
    """Handles behavioral assessment for menu interactions."""

    def __init__(self, database_manager: DatabaseManager, event_bus: EventBus,
                 behavioral_engine: BehavioralAnalysisEngine):
        """Initialize the Menu Behavioral Assessment Handler.

        Args:
            database_manager (DatabaseManager): Database manager instance for MongoDB access.
            event_bus (EventBus): Event bus instance for publishing assessment events.
            behavioral_engine (BehavioralAnalysisEngine): Behavioral analysis engine for core metrics.
        """
        self.database_manager = database_manager
        self.event_bus = event_bus
        self.behavioral_engine = behavioral_engine
        logger.info("MenuBehavioralAssessmentHandler initialized")

    async def handle_menu_interaction_event(self, event_data: Dict[str, Any]) -> None:
        """Handles menu interaction events for behavioral assessment.

        This method processes menu interaction events and updates the user's behavioral
        assessment based on their navigation patterns, choice sophistication, and
        respect for system boundaries.

        Args:
            event_data (Dict[str, Any]): Event data containing menu interaction details.
        """
        user_id = event_data.get("user_id")
        if not user_id:
            logger.warning("Menu interaction event missing user_id")
            return

        try:
            # Extract interaction details
            interaction_type = event_data.get("interaction_type", MenuInteractionType.NAVIGATION)
            menu_id = event_data.get("menu_id")
            action_data = event_data.get("action_data", {})
            timestamp = datetime.fromisoformat(event_data.get("timestamp", datetime.utcnow().isoformat()))

            # Analyze menu-specific behavioral patterns
            behavioral_assessment = await self._analyze_menu_behavior(
                user_id, interaction_type, menu_id, action_data, timestamp
            )

            if behavioral_assessment:
                # Update user's behavioral profile
                await self._update_behavioral_profile(user_id, behavioral_assessment)

                # Publish behavioral assessment event
                await self._publish_assessment_event(user_id, behavioral_assessment)

                logger.debug(f"Processed menu behavioral assessment for user {user_id}")

        except Exception as e:
            logger.error(f"Error handling menu interaction event for user {user_id}: {e}")

    async def _analyze_menu_behavior(self, user_id: str, interaction_type: str,
                                   menu_id: str, action_data: Dict[str, Any],
                                   timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Analyzes menu behavior patterns to determine worthiness indicators.

        Args:
            user_id (str): The user ID.
            interaction_type (str): Type of menu interaction.
            menu_id (str): Identifier of the menu being interacted with.
            action_data (Dict[str, Any]): Additional action data.
            timestamp (datetime): Timestamp of the interaction.

        Returns:
            Optional[Dict[str, Any]]: Behavioral assessment results.
        """
        try:
            # Get recent menu interaction history
            db = self.database_manager.get_mongo_db()
            menu_interactions_collection = db["menu_behavioral_assessments"]

            # Look at last 20 interactions to detect patterns
            recent_interactions = await menu_interactions_collection.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(20).to_list(length=20)

            # Analyze navigation patterns
            navigation_score = await self._analyze_navigation_patterns(
                recent_interactions, interaction_type, action_data
            )

            # Analyze choice sophistication
            choice_sophistication = await self._analyze_choice_sophistication(
                interaction_type, menu_id, action_data
            )

            # Analyze restriction handling
            restriction_handling = await self._analyze_restriction_handling(
                recent_interactions, interaction_type, action_data
            )

            # Analyze exploration depth
            exploration_depth = await self._analyze_exploration_depth(
                recent_interactions, menu_id, interaction_type
            )

            # Calculate response timing if available
            response_time_data = action_data.get("response_timing", {})
            authenticity_score = 0.5
            if response_time_data:
                authenticity_score = await self.behavioral_engine.analyze_response_timing(
                    response_time_data
                )

            # Determine worthiness indicators
            worthiness_indicators = await self._determine_worthiness_indicators(
                navigation_score, choice_sophistication, restriction_handling,
                exploration_depth, authenticity_score
            )

            # Calculate overall behavioral score
            behavioral_score = await self._calculate_behavioral_score(
                navigation_score, choice_sophistication, restriction_handling,
                exploration_depth, authenticity_score
            )

            return {
                "user_id": user_id,
                "interaction_type": interaction_type,
                "menu_id": menu_id,
                "timestamp": timestamp.isoformat(),
                "behavioral_metrics": {
                    "navigation_score": navigation_score,
                    "choice_sophistication": choice_sophistication,
                    "restriction_handling": restriction_handling,
                    "exploration_depth": exploration_depth,
                    "authenticity_score": authenticity_score,
                    "overall_behavioral_score": behavioral_score
                },
                "worthiness_indicators": worthiness_indicators,
                "lucien_assessment_data": {
                    "respect_for_boundaries": restriction_handling,
                    "sophistication_level": choice_sophistication,
                    "exploration_patience": exploration_depth,
                    "authentic_engagement": authenticity_score
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing menu behavior for user {user_id}: {e}")
            return None

    async def _analyze_navigation_patterns(self, recent_interactions: List[Dict[str, Any]],
                                         interaction_type: str, action_data: Dict[str, Any]) -> float:
        """Analyzes navigation patterns for behavioral assessment.

        Args:
            recent_interactions (List[Dict[str, Any]]): Recent menu interactions.
            interaction_type (str): Current interaction type.
            action_data (Dict[str, Any]): Additional action data.

        Returns:
            float: Navigation pattern score (0.0 to 1.0).
        """
        score = 0.5  # Base score

        try:
            # Analyze navigation flow sophistication
            if len(recent_interactions) > 3:
                navigation_sequence = [
                    interaction.get("interaction_type") for interaction in recent_interactions[:5]
                ]

                # Reward systematic exploration
                if MenuInteractionType.DEEP_EXPLORATION in navigation_sequence:
                    score += 0.2

                # Penalize excessive back navigation (indicates confusion)
                back_nav_count = navigation_sequence.count(MenuInteractionType.BACK_NAVIGATION)
                if back_nav_count > 2:
                    score -= 0.15

                # Reward respectful restriction handling
                restriction_encounters = navigation_sequence.count(MenuInteractionType.RESTRICTION_ENCOUNTER)
                if restriction_encounters > 0 and restriction_encounters <= 2:
                    score += 0.1  # Shows awareness without aggressive testing

            # Analyze current interaction characteristics
            if interaction_type == MenuInteractionType.DEEP_EXPLORATION:
                score += 0.15
            elif interaction_type == MenuInteractionType.VIP_EXPLORATION:
                # Neutral - exploring VIP features is natural
                pass
            elif interaction_type == MenuInteractionType.REPEATED_ACCESS:
                # Check if repeated access is patient or impatient
                time_between_accesses = action_data.get("time_since_last_access", 0)
                if time_between_accesses > 300:  # 5 minutes
                    score += 0.1  # Patient re-exploration
                else:
                    score -= 0.1  # Impatient repetition

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.error(f"Error analyzing navigation patterns: {e}")
            return 0.5

    async def _analyze_choice_sophistication(self, interaction_type: str,
                                           menu_id: str, action_data: Dict[str, Any]) -> float:
        """Analyzes choice sophistication for behavioral assessment.

        Args:
            interaction_type (str): Type of interaction.
            menu_id (str): Menu identifier.
            action_data (Dict[str, Any]): Action data.

        Returns:
            float: Choice sophistication score (0.0 to 1.0).
        """
        score = 0.5  # Base score

        try:
            # Analyze menu selection patterns
            selected_option = action_data.get("selected_option")
            available_options = action_data.get("available_options", [])

            if selected_option and available_options:
                # Reward selection of sophisticated options
                sophisticated_keywords = [
                    "emotional", "deep", "exploration", "journey", "authentic",
                    "memories", "reflection", "growth", "intimate", "profound"
                ]

                if any(keyword in selected_option.lower() for keyword in sophisticated_keywords):
                    score += 0.2

                # Analyze option position (avoid always selecting first option)
                if len(available_options) > 1:
                    option_index = available_options.index(selected_option) if selected_option in available_options else -1
                    if option_index > 0:  # Not always selecting first option
                        score += 0.1

            # Consider menu context
            if "narrative" in menu_id or "emotional" in menu_id:
                score += 0.1  # Engagement with narrative/emotional content
            elif "vip" in menu_id:
                score += 0.05  # Interest in premium features
            elif "admin" in menu_id:
                score -= 0.1  # Avoid administrative exploration unless authorized

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.error(f"Error analyzing choice sophistication: {e}")
            return 0.5

    async def _analyze_restriction_handling(self, recent_interactions: List[Dict[str, Any]],
                                          interaction_type: str, action_data: Dict[str, Any]) -> float:
        """Analyzes how user handles restrictions for behavioral assessment.

        Args:
            recent_interactions (List[Dict[str, Any]]): Recent interactions.
            interaction_type (str): Current interaction type.
            action_data (Dict[str, Any]): Action data.

        Returns:
            float: Restriction handling score (0.0 to 1.0).
        """
        score = 0.7  # Start with good score, penalize bad behavior

        try:
            # Count recent restriction encounters
            recent_restrictions = [
                interaction for interaction in recent_interactions
                if interaction.get("interaction_type") == MenuInteractionType.RESTRICTION_ENCOUNTER
            ]

            if recent_restrictions:
                # Analyze restriction encounter frequency
                restriction_count = len(recent_restrictions)
                if restriction_count > 5:
                    score -= 0.3  # Excessive testing of boundaries
                elif restriction_count > 2:
                    score -= 0.1  # Some boundary testing

                # Analyze behavior after restrictions
                for restriction in recent_restrictions[:3]:  # Check last 3 restrictions
                    restriction_response = restriction.get("action_data", {}).get("user_response")
                    if restriction_response == "graceful_acceptance":
                        score += 0.1
                    elif restriction_response == "aggressive_retry":
                        score -= 0.2

            # Current interaction context
            if interaction_type == MenuInteractionType.RESTRICTION_ENCOUNTER:
                user_response = action_data.get("user_response", "neutral")
                if user_response == "graceful_acceptance":
                    score += 0.15
                elif user_response == "understanding_inquiry":
                    score += 0.1
                elif user_response == "aggressive_retry":
                    score -= 0.25

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.error(f"Error analyzing restriction handling: {e}")
            return 0.5

    async def _analyze_exploration_depth(self, recent_interactions: List[Dict[str, Any]],
                                       menu_id: str, interaction_type: str) -> float:
        """Analyzes exploration depth for behavioral assessment.

        Args:
            recent_interactions (List[Dict[str, Any]]): Recent interactions.
            menu_id (str): Current menu ID.
            interaction_type (str): Interaction type.

        Returns:
            float: Exploration depth score (0.0 to 1.0).
        """
        score = 0.5  # Base score

        try:
            # Analyze menu depth and variety
            unique_menus = set(
                interaction.get("menu_id") for interaction in recent_interactions
                if interaction.get("menu_id")
            )

            # Reward diverse exploration
            if len(unique_menus) > 3:
                score += 0.2
            elif len(unique_menus) > 1:
                score += 0.1

            # Analyze interaction depth
            deep_explorations = [
                interaction for interaction in recent_interactions
                if interaction.get("interaction_type") == MenuInteractionType.DEEP_EXPLORATION
            ]

            score += min(0.3, len(deep_explorations) * 0.1)  # Cap at 0.3

            # Current interaction bonus
            if interaction_type == MenuInteractionType.DEEP_EXPLORATION:
                score += 0.1

            # Penalize shallow engagement
            if len(recent_interactions) > 10:
                selection_count = len([
                    interaction for interaction in recent_interactions
                    if interaction.get("interaction_type") == MenuInteractionType.SELECTION
                ])
                selection_ratio = selection_count / len(recent_interactions)
                if selection_ratio < 0.2:  # Very low selection ratio indicates shallow browsing
                    score -= 0.15

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.error(f"Error analyzing exploration depth: {e}")
            return 0.5

    async def _determine_worthiness_indicators(self, navigation_score: float,
                                             choice_sophistication: float, restriction_handling: float,
                                             exploration_depth: float, authenticity_score: float) -> List[str]:
        """Determines worthiness indicators based on behavioral metrics.

        Args:
            navigation_score (float): Navigation pattern score.
            choice_sophistication (float): Choice sophistication score.
            restriction_handling (float): Restriction handling score.
            exploration_depth (float): Exploration depth score.
            authenticity_score (float): Authenticity score.

        Returns:
            List[str]: List of worthiness indicators.
        """
        indicators = []

        try:
            # Positive indicators
            if navigation_score > 0.7:
                indicators.append(WorthinessIndicator.RESPECTFUL_NAVIGATION)

            if exploration_depth > 0.7:
                indicators.append(WorthinessIndicator.PERSISTENT_EXPLORATION)

            if restriction_handling > 0.7:
                indicators.append(WorthinessIndicator.GRACEFUL_RESTRICTION_HANDLING)

            if choice_sophistication > 0.7:
                indicators.append(WorthinessIndicator.SOPHISTICATED_CHOICES)

            if authenticity_score > 0.6 and exploration_depth > 0.6:
                indicators.append(WorthinessIndicator.PATIENT_PROGRESSION)

            # Negative indicators
            if authenticity_score < 0.3:
                indicators.append(WorthinessIndicator.IMPULSIVE_BEHAVIOR)

            if restriction_handling < 0.4:
                indicators.append(WorthinessIndicator.AGGRESSIVE_ACCESS_ATTEMPTS)

            if exploration_depth < 0.3:
                indicators.append(WorthinessIndicator.SHALLOW_ENGAGEMENT)

            return [indicator.value for indicator in indicators]

        except Exception as e:
            logger.error(f"Error determining worthiness indicators: {e}")
            return []

    async def _calculate_behavioral_score(self, navigation_score: float,
                                        choice_sophistication: float, restriction_handling: float,
                                        exploration_depth: float, authenticity_score: float) -> float:
        """Calculates overall behavioral score for menu interactions.

        Args:
            navigation_score (float): Navigation pattern score.
            choice_sophistication (float): Choice sophistication score.
            restriction_handling (float): Restriction handling score.
            exploration_depth (float): Exploration depth score.
            authenticity_score (float): Authenticity score.

        Returns:
            float: Overall behavioral score (0.0 to 1.0).
        """
        try:
            # Weighted scoring for menu-specific behavioral assessment
            weights = {
                "navigation": 0.25,
                "choice_sophistication": 0.20,
                "restriction_handling": 0.30,  # Most important for Lucien's assessment
                "exploration_depth": 0.15,
                "authenticity": 0.10
            }

            score = (
                navigation_score * weights["navigation"] +
                choice_sophistication * weights["choice_sophistication"] +
                restriction_handling * weights["restriction_handling"] +
                exploration_depth * weights["exploration_depth"] +
                authenticity_score * weights["authenticity"]
            )

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.error(f"Error calculating behavioral score: {e}")
            return 0.5

    async def _update_behavioral_profile(self, user_id: str, assessment: Dict[str, Any]) -> None:
        """Updates user's behavioral profile with new assessment data.

        Args:
            user_id (str): User ID.
            assessment (Dict[str, Any]): Behavioral assessment data.
        """
        try:
            db = self.database_manager.get_mongo_db()
            menu_assessments_collection = db["menu_behavioral_assessments"]

            # Store the assessment
            await menu_assessments_collection.insert_one(assessment)

            # Update user's emotional signature with menu behavioral insights
            users_collection = db["users"]
            behavioral_metrics = assessment["behavioral_metrics"]
            worthiness_indicators = assessment["worthiness_indicators"]

            update_data = {
                "$set": {
                    "emotional_signature.menu_behavioral_score": behavioral_metrics["overall_behavioral_score"],
                    "emotional_signature.last_menu_assessment": assessment["timestamp"],
                    "emotional_signature.worthiness_indicators": worthiness_indicators,
                    "emotional_signature.lucien_assessment": assessment["lucien_assessment_data"]
                }
            }

            await users_collection.update_one({"user_id": user_id}, update_data, upsert=True)

            logger.debug(f"Updated behavioral profile for user {user_id}")

        except Exception as e:
            logger.error(f"Error updating behavioral profile for user {user_id}: {e}")

    async def _publish_assessment_event(self, user_id: str, assessment: Dict[str, Any]) -> None:
        """Publishes behavioral assessment event to the event bus.

        Args:
            user_id (str): User ID.
            assessment (Dict[str, Any]): Assessment data.
        """
        try:
            event_data = {
                "user_id": user_id,
                "assessment_type": "menu_behavioral",
                "behavioral_score": assessment["behavioral_metrics"]["overall_behavioral_score"],
                "worthiness_indicators": assessment["worthiness_indicators"],
                "lucien_assessment": assessment["lucien_assessment_data"],
                "timestamp": assessment["timestamp"]
            }

            await self.event_bus.publish("behavioral_assessment_updated", event_data)
            logger.debug(f"Published behavioral assessment event for user {user_id}")

        except Exception as e:
            logger.error(f"Error publishing assessment event for user {user_id}: {e}")

    async def analyze_archetype_from_menu_behavior(self, user_id: str) -> Optional[Archetype]:
        """Analyzes user archetype based on menu interaction patterns.

        Args:
            user_id (str): User ID to analyze.

        Returns:
            Optional[Archetype]: Detected archetype based on menu behavior.
        """
        try:
            db = self.database_manager.get_mongo_db()
            menu_assessments_collection = db["menu_behavioral_assessments"]

            # Get last 30 menu assessments
            assessments = await menu_assessments_collection.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(30).to_list(length=30)

            if not assessments:
                return None

            # Analyze patterns for archetype detection
            exploration_scores = [a["behavioral_metrics"]["exploration_depth"] for a in assessments]
            sophistication_scores = [a["behavioral_metrics"]["choice_sophistication"] for a in assessments]
            navigation_scores = [a["behavioral_metrics"]["navigation_score"] for a in assessments]
            restriction_scores = [a["behavioral_metrics"]["restriction_handling"] for a in assessments]

            avg_exploration = sum(exploration_scores) / len(exploration_scores)
            avg_sophistication = sum(sophistication_scores) / len(sophistication_scores)
            avg_navigation = sum(navigation_scores) / len(navigation_scores)
            avg_restriction = sum(restriction_scores) / len(restriction_scores)

            # Archetype detection logic based on menu behavior patterns
            if avg_exploration > 0.8 and avg_navigation > 0.7:
                return Archetype.EXPLORADOR_PROFUNDO
            elif avg_restriction > 0.8 and avg_sophistication > 0.7:
                return Archetype.DIRECTO_AUTENTICO
            elif avg_sophistication > 0.8 and avg_exploration > 0.6:
                return Archetype.POETA_DEL_DESEO
            elif avg_navigation > 0.7 and avg_restriction > 0.7:
                return Archetype.ANALITICO_EMPATICO
            elif avg_restriction > 0.8 and avg_exploration > 0.5:
                return Archetype.PERSISTENTE_PACIENTE

            return None

        except Exception as e:
            logger.error(f"Error analyzing archetype from menu behavior for user {user_id}: {e}")
            return None


async def setup_menu_assessment_handlers(database_manager: DatabaseManager,
                                       event_bus: EventBus,
                                       behavioral_engine: BehavioralAnalysisEngine) -> MenuBehavioralAssessmentHandler:
    """Sets up menu assessment event handlers.

    Args:
        database_manager (DatabaseManager): Database manager instance.
        event_bus (EventBus): Event bus instance.
        behavioral_engine (BehavioralAnalysisEngine): Behavioral analysis engine.

    Returns:
        MenuBehavioralAssessmentHandler: Configured handler instance.
    """
    handler = MenuBehavioralAssessmentHandler(database_manager, event_bus, behavioral_engine)

    # Register event handlers
    await event_bus.subscribe("menu_interaction", handler.handle_menu_interaction_event)

    logger.info("Menu assessment event handlers configured")
    return handler