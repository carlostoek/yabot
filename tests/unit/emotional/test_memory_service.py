
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from src.modules.emotional.memory_service import EmotionalMemoryService

@pytest.fixture
def mock_database_manager():
    """Fixture for a mocked DatabaseManager."""
    mock_manager = Mock()
    mock_db = MagicMock()
    mock_manager.get_mongo_db.return_value = mock_db
    return mock_manager

@pytest.fixture
def mock_event_bus():
    """Fixture for a mocked EventBus."""
    return Mock()

@pytest.fixture
def emotional_memory_service(mock_database_manager, mock_event_bus):
    """Fixture for EmotionalMemoryService with mocked dependencies."""
    return EmotionalMemoryService(
        database_manager=mock_database_manager,
        event_bus=mock_event_bus
    )

@pytest.mark.asyncio
async def test_record_significant_moment(emotional_memory_service):
    """
    Given: A user ID and interaction data for a significant moment
    When: record_significant_moment is called
    Then: A memory fragment is created and stored.
    """
    # Arrange
    user_id = "user123"
    interaction_data = {"text": "I've never told anyone this before..."}
    
    with patch.object(emotional_memory_service.db_manager.get_collection("memory_fragments"), 'insert_one') as mock_insert:
        # Act
        memory_fragment = await emotional_memory_service.record_significant_moment(user_id, interaction_data)

        # Assert
        assert memory_fragment is not None
        assert memory_fragment.user_id == user_id
        mock_insert.assert_called_once()

@pytest.mark.asyncio
async def test_retrieve_relevant_memories(emotional_memory_service):
    """
    Given: A user ID and a current interaction context
    When: retrieve_relevant_memories is called
    Then: A list of relevant memory fragments is returned.
    """
    # Arrange
    user_id = "user123"
    current_context = {"topic": "family"}
    
    with patch.object(emotional_memory_service.db_manager.get_collection("memory_fragments"), 'find') as mock_find:
        mock_find.return_value.to_list.return_value = [
            {"memory_id": "mem1", "content_summary": "Talked about family"}
        ]
        # Act
        memories = await emotional_memory_service.retrieve_relevant_memories(user_id, current_context)

        # Assert
        assert memories is not None
        assert len(memories) > 0
        assert memories[0]["content_summary"] == "Talked about family"

@pytest.mark.asyncio
async def test_update_relationship_evolution(emotional_memory_service):
    """
    Given: A user ID and milestone data
    When: update_relationship_evolution is called
    Then: The relationship status is updated in the database.
    """
    # Arrange
    user_id = "user123"
    milestone_data = {"milestone": "trust_established"}
    
    with patch.object(emotional_memory_service.db_manager.get_collection("users"), 'update_one') as mock_update:
        # Act
        status = await emotional_memory_service.update_relationship_evolution(user_id, milestone_data)

        # Assert
        assert status is not None
        mock_update.assert_called_once()

@pytest.mark.asyncio
async def test_generate_natural_callbacks(emotional_memory_service):
    """
    Given: A list of memory fragments and a context
    When: generate_natural_callbacks is called
    Then: A list of natural-sounding callback strings is returned.
    """
    # Arrange
    memory_fragments = [
        {"content_summary": "You mentioned your dog, Sparky."}
    ]
    context = {"current_topic": "pets"}

    # Act
    callbacks = await emotional_memory_service.generate_natural_callbacks(memory_fragments, context)

    # Assert
    assert callbacks is not None
    assert len(callbacks) > 0
    assert "Sparky" in callbacks[0]
