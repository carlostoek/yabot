
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from src.modules.emotional.memory_service import EmotionalMemoryService
from src.database.schemas.emotional import MemoryFragment

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
    interaction_data = {
        "memory_id": "test_mem_id",
        "user_id": user_id,
        "interaction_context": {"text": "I've never told anyone this before..."},
        "emotional_significance": 0.9,
        "memory_type": "vulnerability_moment",
        "content_summary": "User shared a secret.",
        "diana_response_context": "Responded with empathy.",
        "relationship_stage": 2,
    }
    
    with patch.object(emotional_memory_service.collection, 'insert_one', new_callable=AsyncMock) as mock_insert:
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
    
    mock_cursor = AsyncMock()
    mock_cursor.__aiter__.return_value = iter([
        {"memory_id": "mem1", "content_summary": "Talked about family", "user_id": user_id, "interaction_context": {}, "emotional_significance": 0.8, "memory_type": "sharing", "diana_response_context": "", "relationship_stage": 1}
    ])
    
    with patch.object(emotional_memory_service.collection, 'find') as mock_find:
        mock_find.return_value.sort.return_value.limit.return_value = mock_cursor
        # Act
        memories = await emotional_memory_service.retrieve_relevant_memories(user_id, current_context)

        # Assert
        assert memories is not None
        assert len(memories) > 0
        assert memories[0].content_summary == "Talked about family"

@pytest.mark.asyncio
async def test_generate_natural_callbacks(emotional_memory_service):
    """
    Given: A list of memory fragments and a context
    When: generate_natural_callbacks is called
    Then: A list of natural-sounding callback strings is returned.
    """
    # Arrange
    mock_fragment = MagicMock(spec=MemoryFragment)
    mock_fragment.content_summary = "You mentioned your dog, Sparky."
    mock_fragment.emotional_significance = 0.9
    mock_fragment.memory_id = "mem123"

    memory_fragments = [mock_fragment]
    context = {"current_topic": "pets"}

    # Act
    callbacks = await emotional_memory_service.generate_natural_callbacks(memory_fragments, context)

    # Assert
    assert callbacks is not None
    assert len(callbacks) > 0
    assert "Sparky" in callbacks[0].callback_text
