"
Personalization Content Service for the YABOT system.

This module is responsible for dynamic content adaptation based on user's
emotional archetype and journey stage, as specified in REQ-3 of the emocional
specification.
"

from typing import Dict, Any, Optional, List

from src.services.narrative import NarrativeService
from src.modules.emotional.memory_service import EmotionalMemoryService
from src.utils.logger import get_logger
from src.database.schemas.emotional import PersonalizedResponse, ContentVariant, MemoryCallback
from src.modules.emotional.behavioral_analysis import Archetype

logger = get_logger(__name__)


class PersonalizationContentService:
    """Manages the personalization of content for users."""

    def __init__(
        self,
        narrative_service: NarrativeService,
        memory_service: EmotionalMemoryService,
    ):
        """Initialize the PersonalizationContentService.

        Args:
            narrative_service (NarrativeService): Instance for narrative operations.
            memory_service (EmotionalMemoryService): Instance for memory operations.
        """
        self.narrative_service = narrative_service
        self.memory_service = memory_service
        logger.info("PersonalizationContentService initialized")

    async def generate_diana_response(
        self,
        user_context: Dict[str, Any],
        emotional_state: Dict[str, Any],
    ) -> Optional[PersonalizedResponse]:
        """Generates a personalized response for Diana.

        Args:
            user_context (Dict[str, Any]): The user's context, including profile.
            emotional_state (Dict[str, Any]): The user's current emotional state.

        Returns:
            Optional[PersonalizedResponse]: A personalized response object, or None.
        """
        logger.debug(f"Generating Diana response for user {user_context.get('user_id')}")
        try:
            fragment_id = emotional_state.get("current_fragment_id")
            if not fragment_id:
                logger.warning("No fragment_id in emotional_state, cannot generate response.")
                return None

            base_fragment = await self.narrative_service.get_narrative_fragment(fragment_id)
            if not base_fragment:
                logger.error(f"Could not retrieve fragment {fragment_id}")
                return None

            archetype = user_context.get("emotional_signature", {}).get("archetype")
            content_variant = await self.select_content_variant(
                base_fragment, archetype, emotional_state
            )
            response_text = content_variant.variant_text

            memories = await self.memory_service.retrieve_relevant_memories(
                user_id=user_context["user_id"],
                current_context=emotional_state,
            )

            callbacks = await self.memory_service.generate_natural_callbacks(memories, emotional_state)

            response_text, details = await self.incorporate_memory_callbacks(response_text, callbacks)

            personalization_details = {
                "callbacks_added": details,
                "archetype_variant_used": archetype.value if archetype else 'default'
            }

            logger.info(f"Generated response for user {user_context.get('user_id')} with {len(callbacks)} callbacks.")

            return PersonalizedResponse(
                response_text=response_text,
                personalization_details=personalization_details,
            )

        except Exception as e:
            logger.error(f"Error generating Diana response: {e}")
            return None

    async def select_content_variant(
        self,
        base_fragment: Dict[str, Any],
        archetype: Archetype,
        emotional_context: Dict[str, Any],
    ) -> ContentVariant:
        """Selects a content variant based on the user's archetype.

        Args:
            base_fragment (Dict[str, Any]): The base narrative fragment.
            archetype (Archetype): The user's emotional archetype.
            emotional_context (Dict[str, Any]): The user's current emotional context.

        Returns:
            ContentVariant: The selected content variant.
        """
        variants = base_fragment.get("variants", {})
        default_text = base_fragment.get("text", "")

        if archetype and archetype.value in variants:
            variant_text = variants[archetype.value]
            logger.debug(f"Selected variant for archetype {archetype.value}")
        else:
            variant_text = default_text
            logger.debug("No specific variant found for archetype, using default text.")

        return ContentVariant(variant_text=variant_text, archetype=archetype.value if archetype else "default")

    async def incorporate_memory_callbacks(
        self,
        response_text: str,
        callbacks: List[MemoryCallback],
    ) -> (str, List[str]):
        """Incorporates memory callbacks into the response text.

        Args:
            response_text (str): The base response text.
            callbacks (List[MemoryCallback]): A list of memory callbacks to incorporate.

        Returns:
            A tuple containing the modified response text and a list of incorporated callback IDs.
        """
        if not callbacks:
            return response_text, []

        incorporated_callback_ids = []
        for callback in callbacks:
            response_text += f"\n\n{callback.callback_text}"
            incorporated_callback_ids.append(callback.source_memory_id)
        
        return response_text, incorporated_callback_ids