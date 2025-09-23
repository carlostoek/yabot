"""
Emotional intelligence module initialization and event handler registration.
"""

from src.events.bus import EventBus
from src.services.cross_module import CrossModuleService
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def register_emotional_event_handlers(event_bus: EventBus, cross_module_service: CrossModuleService):
    """Register all emotional intelligence event handlers."""

    # Register emotional signature update handler
    await event_bus.subscribe(
        "emotional_signature_updated",
        lambda event_data: cross_module_service.handle_emotional_signature_update(event_data)
    )

    # Register Diana level progression handler
    await event_bus.subscribe(
        "diana_level_progression",
        lambda event_data: cross_module_service.handle_diana_level_progression(event_data)
    )

    # Register emotional milestone handler
    await event_bus.subscribe(
        "emotional_milestone_reached",
        lambda event_data: cross_module_service.handle_emotional_milestone(event_data)
    )

    # Register content personalization handler
    await event_bus.subscribe(
        "content_personalized",
        lambda event_data: cross_module_service.handle_content_personalization(event_data)
    )

    # Register emotional interaction handler
    await event_bus.subscribe(
        "emotional_interaction_recorded",
        lambda event_data: cross_module_service.handle_emotional_interaction(event_data)
    )

    logger.info("Emotional intelligence event handlers registered successfully")