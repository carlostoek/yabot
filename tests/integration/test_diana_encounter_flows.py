
"""
Integration tests for the Diana encounter trigger flows.

These tests verify that reaching a narrative milestone correctly triggers the
Diana encounter evaluation process and results in an encounter for an eligible user.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.services.user import UserService
from src.services.diana_encounter_manager import DianaEncounterManager, UserProgress
from src.events.processor import EventProcessor
from src.events.models import create_event, EmotionalMilestoneReachedEvent
from src.database.manager import DatabaseManager

# Use mock fixtures from conftest
from tests.conftest import mock_database_manager, mock_event_bus

@pytest.mark.asyncio
async def test_diana_encounter_triggered_by_milestone_event(mock_database_manager: DatabaseManager, mock_event_bus: Mock):
    """
    Tests that an EmotionalMilestoneReachedEvent triggers a Diana encounter
    for a user who meets all the necessary criteria.
    """
    # Arrange: Set up services and a user who is ready for an encounter
    user_service = UserService(db_manager=mock_database_manager)
    encounter_manager = DianaEncounterManager()
    event_processor = EventProcessor(event_bus=mock_event_bus)

    user_id = "eligible_user_for_diana"
    user_details = {
        "id": user_id,
        "username": "diana_fan",
        "first_name": "Eligible",
        "last_name": "User",
    }
    await user_service.create_user(user_details)
    # Set user to be VIP, high narrative level, and high resonance
    await user_service.update_user_profile(user_id, {
        "role": "vip_user",
        "has_vip": True,
        "narrative_level": 4,
        "emotional_resonance": 0.8
    })

    # This will be our mock handler, simulating a real event-driven architecture
    # It will be registered with the event processor.
    async def handle_milestone_event(event: EmotionalMilestoneReachedEvent):
        user_context = await user_service.get_user_context(event.user_id)
        user_progress = UserProgress(
            narrative_level=user_context.get("narrative_level", 1),
            emotional_resonance=user_context.get("emotional_resonance", 0.0),
            last_encounter_time=user_context.get("last_encounter_time")
        )
        
        readiness = await encounter_manager.evaluate_diana_encounter_readiness(
            user_progress, user_progress.emotional_resonance
        )
        
        if readiness.is_ready:
            # In a real system, this would trigger a new event or a direct action.
            # For this test, we'll confirm readiness and log the encounter.
            await mock_database_manager.db["diana_encounters"].insert_one({
                "user_id": event.user_id,
                "trigger_condition": f"milestone:{event.payload.get('milestone_type')}",
                "emotional_significance": 0.9, # mock value
            })

    await event_processor.register_handler("emotional_milestone_reached", handle_milestone_event)

    # Action: Simulate a narrative milestone being reached by publishing an event
    milestone_event = create_event(
        "emotional_milestone_reached",
        user_id=user_id,
        payload={
            "milestone_type": "cartografia_del_deseo_completed",
            "milestone_data": {"details": "User completed a significant chapter"}
        }
    )

    # Manually trigger the handler as the processor's listening loop isn't running
    # This simulates the event bus dispatching the event to the correct handler
    handlers = event_processor._handlers.get("emotional_milestone_reached", [])
    for handler in handlers:
        await handler(milestone_event)

    # Assert: Check that a Diana encounter was created in the database
    encounter_record = await mock_database_manager.db["diana_encounters"].find_one({"user_id": user_id})
    
    assert encounter_record is not None
    assert encounter_record["user_id"] == user_id
    assert "milestone:cartografia_del_deseo_completed" in encounter_record["trigger_condition"]
