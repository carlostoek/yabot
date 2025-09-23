
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.modules.emotional.behavioral_analysis import BehavioralAnalysisEngine, Archetype

@pytest.fixture
def mock_database_manager():
    """Fixture for a mocked DatabaseManager."""
    return Mock()

@pytest.fixture
def mock_event_bus():
    """Fixture for a mocked EventBus."""
    return Mock()

@pytest.fixture
def behavioral_analysis_engine(mock_database_manager, mock_event_bus):
    """Fixture for BehavioralAnalysisEngine with mocked dependencies."""
    return BehavioralAnalysisEngine(
        database_manager=mock_database_manager,
        event_bus=mock_event_bus
    )

@pytest.mark.asyncio
async def test_analyze_response_timing(behavioral_analysis_engine):
    """
    Given: A response with timing data
    When: analyze_response_timing is called
    Then: An authenticity score is returned.
    """
    # Arrange
    response_data = {"response_time_seconds": 5.0}

    # Act
    authenticity_score = await behavioral_analysis_engine.analyze_response_timing(response_data)

    # Assert
    assert 0.0 <= authenticity_score <= 1.0

@pytest.mark.asyncio
async def test_detect_archetype_patterns(behavioral_analysis_engine):
    """
    Given: A user ID and a mocked database returning interactions
    When: detect_archetype_patterns is called
    Then: An archetype classification is returned.
    """
    # Arrange
    user_id = "user123"
    user_interactions = [
        {"archetype_indicators": {"style": "methodical"}},
        {"archetype_indicators": {"style": "methodical"}},
        {"archetype_indicators": {"style": "direct"}},
    ]
    
    mock_cursor = AsyncMock()
    mock_cursor.to_list.return_value = user_interactions
    
    mock_db = AsyncMock()
    mock_db["emotional_interactions"].find.return_value.sort.return_value.limit.return_value = mock_cursor
    
    behavioral_analysis_engine.database_manager.get_mongo_db.return_value = mock_db

    # Act
    archetype = await behavioral_analysis_engine.detect_archetype_patterns(user_id)

    # Assert
    assert archetype == Archetype.EXPLORADOR_PROFUNDO

@pytest.mark.asyncio
async def test_calculate_emotional_resonance(behavioral_analysis_engine):
    """
    Given: Interaction data with emotional cues
    When: calculate_emotional_resonance is called
    Then: Resonance metrics are returned including a resonance_score.
    """
    # Arrange
    interaction_data = {"vulnerability_score": 0.8, "authenticity_score": 0.9, "depth_score": 0.5}

    # Act
    resonance_metrics = await behavioral_analysis_engine.calculate_emotional_resonance(interaction_data)

    # Assert
    assert resonance_metrics is not None
    assert "resonance_score" in resonance_metrics
    assert resonance_metrics["resonance_score"] > 0
