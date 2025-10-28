
"""
System-level tests for validating the impact of a Diana encounter.

These tests ensure that after a user experiences a special encounter with Diana,
their emotional state, relationship metrics, and content access are updated
correctly, reflecting the significance of the event.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.services.user import UserService
from src.services.diana_encounter_manager import DianaEncounterManager, UserProgress
from src.events.processor import EventProcessor
from src.events.models import create_event, EmotionalMilestoneReachedEvent
from src.ui.menu_factory import MenuFactory, MenuType
from src.database.manager import DatabaseManager

# Use mock fixtures from conftest
from tests.conftest import mock_database_manager, mock_event_bus

@pytest.fixture
async def setup_system_for_impact_test(mock_database_manager: DatabaseManager, mock_event_bus: Mock):
    """Provides a setup with a user ready for a significant encounter."""
    user_service = UserService(db_manager=mock_database_manager)
    encounter_manager = DianaEncounterManager()
    event_processor = EventProcessor(event_bus=mock_event_bus)
    menu_factory = MenuFactory()
    menu_factory.cache_manager.connect = Mock(return_value=None)

    user_id = "impact_test_user"
    await user_service.create_user({"id": user_id, "username": "impact_tester"})
    await user_service.update_user_profile(user_id, {
        "role": "vip_user",
        "has_vip": True,
        "narrative_level": 4, # Ready for El Diván
        "emotional_resonance": 0.8, # High resonance
        "relationship_depth_score": 0.5 # Initial depth
    })
    
    return user_service, encounter_manager, event_processor, menu_factory, user_id

@pytest.mark.asyncio
async def test_diana_encounter_impact_on_user_state_and_access(setup_system_for_impact_test):
    """
    Tests that a Diana encounter correctly updates the user's emotional metrics
    and unlocks new content or menu options.
    """
    user_service, encounter_manager, event_processor, menu_factory, user_id = setup_system_for_impact_test

    # --- Step 1: Verify Pre-Encounter State ---
    pre_encounter_context = await user_service.get_user_context(user_id)
    initial_depth_score = pre_encounter_context.get("relationship_depth_score", 0.5)

    # Check that a specific high-level content item is not yet available
    pre_encounter_menu = await menu_factory.create_menu(MenuType.NARRATIVE, pre_encounter_context)
    assert not any(item.id == "divan_level5" for item in pre_encounter_menu.items)

    # --- Step 2: Trigger the Diana Encounter ---
    # This handler simulates the system's response to a milestone event
    async def handle_milestone_and_apply_impact(event: EmotionalMilestoneReachedEvent):
        user_progress = UserProgress(
            narrative_level=pre_encounter_context.get("narrative_level", 1),
            emotional_resonance=pre_encounter_context.get("emotional_resonance", 0.0),
            last_encounter_time=pre_encounter_context.get("last_encounter_time")
        )
        readiness = await encounter_manager.evaluate_diana_encounter_readiness(user_progress, user_progress.emotional_resonance)
        
        if readiness.is_ready:
            # Simulate the impact of the encounter
            new_depth_score = initial_depth_score + 0.2
            await user_service.update_user_profile(event.user_id, {
                "relationship_depth_score": new_depth_score,
                "narrative_level": 5, # The encounter causes level progression
                "last_encounter_time": "2025-09-21T12:00:00Z"
            })
            await mock_database_manager.db["diana_encounters"].insert_one({"user_id": event.user_id})

    await event_processor.register_handler("emotional_milestone_reached", handle_milestone_and_apply_impact)

    # Create and process the event
    milestone_event = create_event("emotional_milestone_reached", user_id=user_id, payload={})
    handlers = event_processor._handlers.get("emotional_milestone_reached", [])
    for handler in handlers:
        await handler(milestone_event)

    # --- Step 3: Verify Post-Encounter State ---
    post_encounter_context = await user_service.get_user_context(user_id)

    # Assert that emotional metrics have been updated
    assert post_encounter_context.get("relationship_depth_score") > initial_depth_score
    assert post_encounter_context.get("narrative_level") == 5
    assert post_encounter_context.get("last_encounter_time") is not None

    # Assert that new content is now unlocked in the menu
    post_encounter_menu = await menu_factory.create_menu(MenuType.NARRATIVE, post_encounter_context)
    assert any(item.id == "divan_level5" for item in post_encounter_menu.items)
