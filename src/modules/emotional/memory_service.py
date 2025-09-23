"""
Emotional Memory Service for the YABOT system.

This module is responsible for creating, storing, and retrieving memory fragments
to maintain relationship continuity, as specified in REQ-4 of the emocional
specification.
"""
import uuid
import random
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.utils.logger import get_logger
from src.database.schemas.emotional import MemoryFragment, MemoryCallback
from src.events.models import create_event

logger = get_logger(__name__)

class EmotionalMemoryServiceError(Exception):
    """Base exception for emotional memory service operations."""
    pass

class EmotionalMemoryService:
    """Manages the creation, storage, and retrieval of emotional memory fragments."""

    def __init__(self, database_manager: DatabaseManager, event_bus: EventBus):
        """Initialize the EmotionalMemoryService.

        Args:
            database_manager (DatabaseManager): Instance for database operations.
            event_bus (EventBus): Instance for publishing events.
        """
        self.database_manager = database_manager
        self.event_bus = event_bus
        self.collection = self.database_manager.get_mongo_db()["memory_fragments"]
        logger.info("EmotionalMemoryService initialized")

    async def record_significant_moment(
        self, user_id: str, interaction_data: Dict[str, Any]
    ) -> Optional[MemoryFragment]:
        """Records a significant emotional moment as a memory fragment.

        This method creates and stores a new MemoryFragment document in MongoDB
        and publishes an event to the event bus.

        Args:
            user_id (str): The ID of the user experiencing the moment.
            interaction_data (Dict[str, Any]): Data describing the interaction.

        Returns:
            Optional[MemoryFragment]: The created memory fragment, or None on failure.
        """
        logger.debug(f"Recording significant moment for user {user_id}")
        try:
            fragment_data = interaction_data.copy()
            fragment_data["user_id"] = user_id

            # Create a MemoryFragment instance to validate data
            memory_fragment = MemoryFragment(**fragment_data)

            # Insert the validated data into the collection
            result = await self.collection.insert_one(memory_fragment.dict())

            if not result.acknowledged:
                raise EmotionalMemoryServiceError("Failed to insert memory fragment into database.")

            logger.info(f"Successfully recorded memory fragment {memory_fragment.memory_id} for user {user_id}")

            # Publish an event about the new memory fragment
            event = create_event(
                "memory_fragment_created",
                user_id=user_id,
                memory_id=memory_fragment.memory_id,
                memory_type=memory_fragment.memory_type,
                emotional_significance=memory_fragment.emotional_significance,
            )
            await self.event_bus.publish("memory_fragment_created", event.dict())

            return memory_fragment

        except Exception as e:
            logger.error(f"Error recording significant moment for user {user_id}: {e}")
            return None

    async def retrieve_relevant_memories(
        self, user_id: str, current_context: Dict[str, Any], limit: int = 5
    ) -> List[MemoryFragment]:
        """Retrieves relevant memory fragments based on the current context.

        Args:
            user_id (str): The ID of the user.
            current_context (Dict[str, Any]): The current interaction context, which may
                                             contain keywords for recall.
            limit (int): The maximum number of memories to retrieve.

        Returns:
            List[MemoryFragment]: A list of relevant memory fragments.
        """
        logger.debug(f"Retrieving relevant memories for user {user_id}")
        try:
            query = {"user_id": user_id}

            # Use keywords from the context to find relevant memories
            keywords = current_context.get("keywords", [])
            if keywords:
                query["recall_triggers"] = {"$in": keywords}

            # Sort by significance and recency
            sort_order = [("emotional_significance", -1), ("created_at", -1)]

            cursor = self.collection.find(query).sort(sort_order).limit(limit)

            memories = []
            async for doc in cursor:
                memories.append(MemoryFragment(**doc))

            logger.info(f"Retrieved {len(memories)} relevant memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Error retrieving relevant memories for user {user_id}: {e}")
            return []

    async def generate_natural_callbacks(
        self, memory_fragments: List[MemoryFragment], context: Dict[str, Any]
    ) -> List[MemoryCallback]:
        """Generates natural-sounding callbacks from a list of memory fragments.

        Args:
            memory_fragments (List[MemoryFragment]): A list of memories to generate callbacks from.
            context (Dict[str, Any]): The current interaction context.

        Returns:
            List[MemoryCallback]: A list of generated callback objects.
        """
        if not memory_fragments:
            return []

        logger.debug(f"Generating natural callbacks from {len(memory_fragments)} memories.")
        callbacks = []

        # For simplicity, we'll generate a callback for the most significant memory.
        # A more complex implementation could select memories based on context.
        most_significant_memory = max(memory_fragments, key=lambda m: m.emotional_significance)

        # Simple template-based callback generation
        templates = [
            "Recuerdo que hablamos sobre {summary}. ¿Cómo te sientes al respecto ahora?",
            "Pensaba en lo que mencionaste sobre {summary}. Me hizo reflexionar.",
            "La última vez que conversamos sobre {summary}, sentí una conexión especial.",
            "A propósito de esto, me viene a la mente cuando dijiste '{summary}'."
        ]

        template = random.choice(templates)
        callback_text = template.format(summary=most_significant_memory.content_summary)

        callback = MemoryCallback(
            callback_text=callback_text,
            source_memory_id=most_significant_memory.memory_id,
            relevance_score=most_significant_memory.emotional_significance
        )

        callbacks.append(callback)
        logger.info(f"Generated 1 natural callback from memory {most_significant_memory.memory_id}")

        return callbacks