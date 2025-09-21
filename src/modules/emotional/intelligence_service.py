"""
Emotional Intelligence Service for the YABOT system.

This module is the central orchestrator for all emotional intelligence operations,
as specified in the emocional specification.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.services.user import UserService
from src.modules.emotional.behavioral_analysis import BehavioralAnalysisEngine
from src.modules.emotional.personalization_service import PersonalizationContentService
from src.modules.emotional.memory_service import EmotionalMemoryService
from src.modules.emotional.progression_manager import NarrativeProgressionManager
from src.utils.logger import get_logger
from src.database.schemas.emotional import EmotionalResponse, ProgressionAssessment

logger = get_logger(__name__)


class EmotionalIntelligenceService:
    """Orchestrates the emotional intelligence services."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        event_bus: EventBus,
        user_service: UserService,
        behavioral_analysis_engine: BehavioralAnalysisEngine,
        personalization_service: PersonalizationContentService,
        memory_service: EmotionalMemoryService,
        progression_manager: NarrativeProgressionManager,
    ):
        """Initialize the EmotionalIntelligenceService.

        Args:
            database_manager (DatabaseManager): Instance for database operations.
            event_bus (EventBus): Instance for publishing events.
            user_service (UserService): Instance for user operations.
            behavioral_analysis_engine (BehavioralAnalysisEngine): Engine for behavioral analysis.
            personalization_service (PersonalizationContentService): Service for content personalization.
            memory_service (EmotionalMemoryService): Service for memory operations.
            progression_manager (NarrativeProgressionManager): Manager for narrative progression.
        """
        self.database_manager = database_manager
        self.event_bus = event_bus
        self.user_service = user_service
        self.behavioral_analysis_engine = behavioral_analysis_engine
        self.personalization_service = personalization_service
        self.memory_service = memory_service
        self.progression_manager = progression_manager
        logger.info("EmotionalIntelligenceService initialized")

    async def analyze_interaction(
        self, user_id: str, interaction_data: Dict[str, Any]
    ) -> Optional[EmotionalResponse]:
        """Analyzes a user interaction and returns an emotional response.

        Args:
            user_id (str): The ID of the user.
            interaction_data (Dict[str, Any]): Data from the user's interaction.

        Returns:
            Optional[EmotionalResponse]: The result of the emotional analysis.
        """
        logger.debug(f"Analyzing interaction for user {user_id}")
        try:
            # 1. Analyze behavior and calculate metrics
            auth_score = await self.behavioral_analysis_engine.analyze_response_timing(interaction_data)
            interaction_data["authenticity_score"] = auth_score

            resonance_metrics = await self.behavioral_analysis_engine.calculate_emotional_resonance(interaction_data)

            # 2. Detect archetype
            archetype = await self.behavioral_analysis_engine.detect_archetype_patterns(user_id)

            # 3. Record significant moments
            significant_moment_recorded = False
            if resonance_metrics.get("resonance_score", 0.0) > 0.75: # Threshold for significance
                moment = await self.memory_service.record_significant_moment(user_id, interaction_data)
                if moment:
                    significant_moment_recorded = True

            # 4. Evaluate progression readiness
            progression_assessment = await self.progression_manager.evaluate_level_readiness(user_id, resonance_metrics)

            # 5. Advance level if ready
            if progression_assessment.is_ready:
                await self.progression_manager.advance_emotional_level(
                    user_id, progression_assessment.next_level, {"reason": "metrics_met"}
                )

            return EmotionalResponse(
                emotional_metrics=resonance_metrics,
                archetype=archetype.value if archetype else None,
                progression_assessment=progression_assessment,
                significant_moment_recorded=significant_moment_recorded,
            )

        except Exception as e:
            logger.error(f"Error analyzing interaction for user {user_id}: {e}")
            return None

    async def get_personalized_content(
        self, user_id: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate personalized content based on emotional archetype and journey stage.

        This method implements REQ-3 and REQ-4 by coordinating memory retrieval with
        content personalization and integrating with cross-module services.

        Args:
            user_id (str): The ID of the user requesting content.
            context (Dict[str, Any]): Current interaction context including fragment_id,
                                     emotional state, and conversation context.

        Returns:
            Optional[Dict[str, Any]]: Personalized content including Diana's response,
                                     memory callbacks, and personalization metadata.
                                     Returns None if content generation fails.
        """
        logger.debug(f"Generating personalized content for user {user_id}")
        try:
            # 1. Retrieve user's emotional signature and current state
            db = self.database_manager.get_mongo_db()
            users_collection = db["users"]

            user_doc = await users_collection.find_one({"user_id": user_id})
            if not user_doc:
                logger.warning(f"User {user_id} not found in database")
                return None

            emotional_signature = user_doc.get("emotional_signature", {})
            emotional_journey = user_doc.get("state", {}).get("emotional_journey", {})

            # 2. Create user context for personalization
            user_context = {
                "user_id": user_id,
                "emotional_signature": emotional_signature,
                "emotional_journey": emotional_journey,
                "profile": user_doc
            }

            # 3. Enhance context with current emotional state
            emotional_state = {
                "current_fragment_id": context.get("fragment_id"),
                "conversation_context": context.get("conversation_context", {}),
                "current_level": emotional_journey.get("current_level", 1),
                "archetype": emotional_signature.get("archetype"),
                "authenticity_score": emotional_signature.get("authenticity_score", 0.0),
                "vulnerability_level": emotional_signature.get("vulnerability_level", 0.0)
            }

            # 4. Generate personalized Diana response using PersonalizationContentService
            personalized_response = await self.personalization_service.generate_diana_response(
                user_context, emotional_state
            )

            if not personalized_response:
                logger.warning(f"Failed to generate personalized response for user {user_id}")
                return None

            # 5. Retrieve and integrate emotional memories for continuity
            relevant_memories = await self.memory_service.retrieve_relevant_memories(
                user_id, emotional_state
            )

            # 6. Generate natural memory callbacks
            memory_callbacks = await self.memory_service.generate_natural_callbacks(
                relevant_memories, emotional_state
            )

            # 7. Calculate emotional resonance for current context
            resonance_metrics = await self.behavioral_analysis_engine.calculate_emotional_resonance({
                "user_context": user_context,
                "emotional_state": emotional_state,
                "interaction_timestamp": context.get("timestamp")
            })

            # 8. Prepare comprehensive personalized content response
            personalized_content = {
                "response_text": personalized_response.response_text,
                "personalization_details": {
                    **personalized_response.personalization_details,
                    "emotional_resonance": resonance_metrics,
                    "memory_callbacks_count": len(memory_callbacks),
                    "current_level": emotional_state["current_level"],
                    "archetype": emotional_state["archetype"]
                },
                "memory_integration": {
                    "relevant_memories_found": len(relevant_memories),
                    "callbacks_generated": len(memory_callbacks),
                    "memory_fragments": [
                        {
                            "memory_id": memory.memory_id,
                            "emotional_significance": memory.emotional_significance,
                            "memory_type": memory.memory_type
                        } for memory in relevant_memories
                    ]
                },
                "emotional_context": emotional_state,
                "content_metadata": {
                    "fragment_id": context.get("fragment_id"),
                    "generation_timestamp": datetime.utcnow().isoformat(),
                    "personalization_engine": "EmotionalIntelligenceService"
                }
            }

            # 9. Publish emotional content generation event for cross-module coordination
            try:
                from src.events.models import create_event
                event = create_event(
                    "emotional_content_generated",
                    user_id=user_id,
                    archetype=emotional_state["archetype"],
                    current_level=emotional_state["current_level"],
                    emotional_resonance=resonance_metrics.get("resonance_score", 0.0),
                    memory_callbacks_count=len(memory_callbacks),
                    content_fragment_id=context.get("fragment_id")
                )
                await self.event_bus.publish("emotional_content_generated", event.dict())
                logger.debug(f"Published emotional_content_generated event for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to publish emotional content event: {e}")

            logger.info(
                f"Generated personalized content for user {user_id}: "
                f"archetype={emotional_state['archetype']}, "
                f"level={emotional_state['current_level']}, "
                f"memories={len(relevant_memories)}, "
                f"callbacks={len(memory_callbacks)}"
            )

            return personalized_content

        except Exception as e:
            logger.error(f"Error generating personalized content for user {user_id}: {e}")
            return None

    async def update_emotional_journey(
        self, user_id: str, progression_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update the user's emotional journey with new progression data.

        This method implements REQ-2 requirements for progressive narrative level management,
        handling Diana level progression through Los Kinkys (1-3) and Diván (4-6) levels.

        Args:
            user_id (str): The ID of the user whose journey is being updated.
            progression_data (Dict[str, Any]): Data containing progression updates including:
                - current_level: The new current level to set
                - progression_reason: Reason for the progression
                - emotional_metrics: Latest emotional metrics
                - milestone_data: Any milestone data associated with the progression

        Returns:
            Optional[Dict[str, Any]]: Updated journey state if successful, None if failed.
                Returns journey state including current_level, progression_history, and metrics.
        """
        logger.debug(f"Updating emotional journey for user {user_id}")
        try:
            # 1. Get current user context using UserService pattern
            user_context = await self.user_service.get_user_context(user_id)
            if not user_context:
                logger.warning(f"User {user_id} not found, cannot update emotional journey")
                return None

            current_journey = user_context.get("state", {}).get("emotional_journey", {})
            current_level = current_journey.get("current_level", 1)

            # 2. Extract progression data
            new_level = progression_data.get("current_level", current_level)
            progression_reason = progression_data.get("progression_reason", "manual_update")
            emotional_metrics = progression_data.get("emotional_metrics", {})
            milestone_data = progression_data.get("milestone_data", {})

            # 3. Validate VIP access for Diana levels 4+ (Diván levels)
            if new_level >= 4 and new_level > current_level:
                has_vip_access = await self.progression_manager.validate_vip_access(user_id, new_level)
                if not has_vip_access:
                    logger.warning(f"User {user_id} lacks VIP access for Diana level {new_level}")
                    return {
                        "success": False,
                        "error": "VIP access required for Diana levels 4+",
                        "current_level": current_level,
                        "requested_level": new_level,
                        "requires_vip": True
                    }

            # 4. Prepare emotional journey state updates following UserService patterns
            timestamp = datetime.utcnow()

            # Build the update payload using MongoDB dot notation patterns from UserService
            journey_updates = {
                "emotional_journey.current_level": new_level,
                "emotional_journey.last_updated": timestamp.isoformat(),
                "emotional_journey.emotional_metrics": emotional_metrics
            }

            # 5. Handle progression history if level changed
            if new_level != current_level:
                # Add to progression history using $push pattern from progression_manager
                progression_entry = {
                    "from_level": current_level,
                    "to_level": new_level,
                    "reason": progression_reason,
                    "timestamp": timestamp.isoformat(),
                    "milestone_data": milestone_data
                }

                # Initialize progression_history if it doesn't exist
                if "progression_history" not in current_journey:
                    journey_updates["emotional_journey.progression_history"] = []

                # Use $push to add new progression entry
                journey_updates["$push"] = {
                    "emotional_journey.progression_history": progression_entry
                }

                # Update level entry date for new level
                journey_updates["emotional_journey.level_entry_date"] = timestamp.isoformat()

            # 6. Determine Diana stage context (Los Kinkys vs Diván)
            stage_context = "los_kinkys" if new_level <= 3 else "divan"
            journey_updates["emotional_journey.stage_context"] = stage_context

            # 7. Update user state using UserService pattern for consistency
            update_success = await self.user_service.update_user_state(user_id, journey_updates)

            if not update_success:
                logger.error(f"Failed to update emotional journey state for user {user_id}")
                return None

            # 8. Prepare updated journey state response
            updated_journey = {
                "current_level": new_level,
                "stage_context": stage_context,
                "last_updated": timestamp.isoformat(),
                "emotional_metrics": emotional_metrics,
                "progression_history": current_journey.get("progression_history", [])
            }

            # Add the new progression entry to the response if level changed
            if new_level != current_level:
                updated_journey["progression_history"].append(progression_entry)

            # 9. Publish emotional journey update event for cross-module coordination
            try:
                from src.events.models import create_event
                event = create_event(
                    "emotional_journey_updated",
                    user_id=user_id,
                    current_level=new_level,
                    previous_level=current_level,
                    stage_context=stage_context,
                    progression_reason=progression_reason,
                    emotional_metrics=emotional_metrics,
                    milestone_data=milestone_data
                )
                await self.event_bus.publish("emotional_journey_updated", event.dict())
                logger.debug(f"Published emotional_journey_updated event for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to publish emotional journey update event: {e}")

            # 10. Coordinate with progression manager if level changed for additional validation
            if new_level != current_level:
                try:
                    # Use the existing advance_emotional_level method for consistency
                    progression_success = await self.progression_manager.advance_emotional_level(
                        user_id, new_level, milestone_data
                    )
                    if not progression_success:
                        logger.warning(f"Progression manager reported failure for user {user_id} level {new_level}")
                except Exception as e:
                    logger.warning(f"Error coordinating with progression manager: {e}")

            logger.info(
                f"Successfully updated emotional journey for user {user_id}: "
                f"level={current_level}->{new_level}, stage={stage_context}, "
                f"reason={progression_reason}"
            )

            return {
                "success": True,
                "journey_state": updated_journey,
                "level_changed": new_level != current_level,
                "requires_vip": new_level >= 4,
                "stage_context": stage_context
            }

        except Exception as e:
            logger.error(f"Error updating emotional journey for user {user_id}: {e}")
            return None