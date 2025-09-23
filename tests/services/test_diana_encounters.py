
"""
Unit tests for the Diana Encounter Management Service.

These tests validate the logic that determines a user's readiness for a special
encounter with Diana, ensuring that encounters are appropriately rare and tied to
meaningful user progression, as per the design specifications.
"""

import pytest
from datetime import datetime, timedelta

from src.services.diana_encounter_manager import DianaEncounterManager, UserProgress

@pytest.mark.asyncio
async def test_user_not_ready_due_to_low_narrative_level():
    """A user with a low narrative level should not be ready for an encounter."""
    # Arrange
    manager = DianaEncounterManager()
    user_progress = UserProgress(narrative_level=3, emotional_resonance=0.8)

    # Act
    readiness = await manager.evaluate_diana_encounter_readiness(user_progress, user_progress.emotional_resonance)

    # Assert
    assert not readiness.is_ready
    assert "required narrative level" in readiness.reason

@pytest.mark.asyncio
async def test_user_not_ready_due_to_low_emotional_resonance():
    """A user with a high level but low resonance should not be ready."""
    # Arrange
    manager = DianaEncounterManager()
    user_progress = UserProgress(narrative_level=4, emotional_resonance=0.7)

    # Act
    readiness = await manager.evaluate_diana_encounter_readiness(user_progress, user_progress.emotional_resonance)

    # Assert
    assert not readiness.is_ready
    assert "emotional resonance is not yet strong enough" in readiness.reason

@pytest.mark.asyncio
async def test_user_not_ready_due_to_frequency_limit():
    """A user who had a recent encounter should not be ready for another."""
    # Arrange
    manager = DianaEncounterManager()
    last_encounter = datetime.now() - timedelta(days=3)
    user_progress = UserProgress(narrative_level=5, emotional_resonance=0.9, last_encounter_time=last_encounter)

    # Act
    readiness = await manager.evaluate_diana_encounter_readiness(user_progress, user_progress.emotional_resonance)

    # Assert
    assert not readiness.is_ready
    assert "Not enough time has passed" in readiness.reason

@pytest.mark.asyncio
async def test_user_is_ready_all_conditions_met():
    """A user who meets all criteria (level, resonance, time) should be ready."""
    # Arrange
    manager = DianaEncounterManager()
    last_encounter = datetime.now() - timedelta(days=8) # More than a week ago
    user_progress = UserProgress(narrative_level=5, emotional_resonance=0.9, last_encounter_time=last_encounter)

    # Act
    readiness = await manager.evaluate_diana_encounter_readiness(user_progress, user_progress.emotional_resonance)

    # Assert
    assert readiness.is_ready
    assert "high narrative level with strong emotional resonance" in readiness.reason

@pytest.mark.asyncio
async def test_user_is_ready_for_first_encounter():
    """A user meeting level/resonance criteria with no previous encounters should be ready."""
    # Arrange
    manager = DianaEncounterManager()
    user_progress = UserProgress(narrative_level=4, emotional_resonance=0.8, last_encounter_time=None)

    # Act
    readiness = await manager.evaluate_diana_encounter_readiness(user_progress, user_progress.emotional_resonance)

    # Assert
    assert readiness.is_ready
