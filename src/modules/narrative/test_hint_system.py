"""
Unit tests for the Hint System in the Narrative Module

Tests the hint system functionality including:
- Unlocking hints for users
- Retrieving user's hints
- Hint combination logic
- Cross-module API patterns simulation
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from src.modules.narrative.hint_system import HintSystem, Hint
from src.events.models import HintUnlockedEvent


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing"""
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def hint_system(mock_event_bus):
    """Create a HintSystem instance with mocked dependencies"""
    # Create the hint system with a mock database handler
    mock_db_handler = AsyncMock()
    hs = HintSystem(event_bus=mock_event_bus, db_handler=mock_db_handler)
    hs.db = mock_db_handler  # Set the db handler directly
    
    return hs


@pytest.mark.asyncio
async def test_unlock_hint_success(hint_system, mock_event_bus):
    """Test successful hint unlock"""
    # Arrange
    user_id = "test_user_123"
    hint_id = "test_hint_456"
    
    mock_hint = {
        "hint_id": hint_id,
        "title": "Test Hint",
        "content": "This is a test hint",
        "hint_type": "narrative",
        "created_at": datetime.utcnow()
    }
    
    # Mock the database calls
    hint_system.db.find_narrative_fragments_by_criteria.return_value = [mock_hint]
    hint_system.db.get_user.return_value = {
        "user_id": user_id,
        "narrative_progress": {"unlocked_hints": []},
        "inventory": []
    }
    hint_system.db.update_user.return_value = True  # Simulate successful update
    
    # Act
    result = await hint_system.unlock_hint(user_id, hint_id)
    
    # Assert
    assert result is True
    mock_event_bus.publish.assert_called_once()
    args, kwargs = mock_event_bus.publish.call_args
    assert isinstance(args[0], HintUnlockedEvent)
    assert args[0].user_id == user_id
    assert args[0].hint_id == hint_id


@pytest.mark.asyncio
async def test_unlock_hint_already_unlocked(hint_system):
    """Test unlocking a hint that's already unlocked"""
    # Arrange
    user_id = "test_user_123"
    hint_id = "test_hint_456"
    
    mock_hint = {
        "hint_id": hint_id,
        "title": "Test Hint",
        "content": "This is a test hint",
        "hint_type": "narrative",
        "created_at": datetime.utcnow()
    }
    
    # Mock the database calls
    hint_system.db.find_narrative_fragments_by_criteria.return_value = [mock_hint]
    hint_system.db.get_user.return_value = {
        "user_id": user_id,
        "narrative_progress": {"unlocked_hints": [hint_id]},  # Hint already unlocked
        "inventory": []
    }
    
    # Act
    result = await hint_system.unlock_hint(user_id, hint_id)
    
    # Assert
    assert result is True  # Already unlocked, so return True


@pytest.mark.asyncio
async def test_unlock_hint_not_found(hint_system):
    """Test unlocking a hint that doesn't exist"""
    # Arrange
    user_id = "test_user_123"
    hint_id = "nonexistent_hint"
    
    hint_system.db.find_narrative_fragments_by_criteria.return_value = []
    
    # Act
    result = await hint_system.unlock_hint(user_id, hint_id)
    
    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_unlock_hint_user_not_found(hint_system):
    """Test unlocking a hint for a user that doesn't exist"""
    # Arrange
    user_id = "nonexistent_user"
    hint_id = "test_hint_456"
    
    mock_hint = {
        "hint_id": hint_id,
        "title": "Test Hint",
        "content": "This is a test hint",
        "hint_type": "narrative",
        "created_at": datetime.utcnow()
    }
    
    hint_system.db.find_narrative_fragments_by_criteria.return_value = [mock_hint]
    hint_system.db.get_user.return_value = None  # User not found
    
    # Act
    result = await hint_system.unlock_hint(user_id, hint_id)
    
    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_get_user_hints_success(hint_system):
    """Test retrieving user's hints successfully"""
    # Arrange
    user_id = "test_user_123"
    hint_ids = ["hint_1", "hint_2", "hint_3"]
    
    hint_system.db.get_user.return_value = {
        "user_id": user_id,
        "narrative_progress": {"unlocked_hints": hint_ids}
    }
    
    # Mock the database calls for each hint
    hint_system.db.find_narrative_fragments_by_criteria.side_effect = [
        [{  # For hint_1
            "hint_id": "hint_1",
            "title": "Hint 1",
            "content": "First hint",
            "hint_type": "narrative",
            "created_at": datetime.utcnow()
        }],
        [{  # For hint_2
            "hint_id": "hint_2", 
            "title": "Hint 2",
            "content": "Second hint",
            "hint_type": "narrative", 
            "created_at": datetime.utcnow()
        }],
        [{  # For hint_3
            "hint_id": "hint_3", 
            "title": "Hint 3",
            "content": "Third hint",
            "hint_type": "narrative", 
            "created_at": datetime.utcnow()
        }]
    ]
    
    # Act
    result = await hint_system.get_user_hints(user_id)
    
    # Assert
    assert len(result) == 3  # Should now get all 3 hints
    assert all(isinstance(hint, Hint) for hint in result)
    assert result[0].hint_id == "hint_1"
    assert result[1].hint_id == "hint_2"
    assert result[2].hint_id == "hint_3"


@pytest.mark.asyncio
async def test_get_user_hints_no_hints(hint_system):
    """Test retrieving hints for a user with no hints"""
    # Arrange
    user_id = "test_user_123"
    
    hint_system.db.get_user.return_value = {
        "user_id": user_id,
        "narrative_progress": {"unlocked_hints": []}  # No hints
    }
    
    # Act
    result = await hint_system.get_user_hints(user_id)
    
    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_get_hint_by_id_success(hint_system):
    """Test retrieving a specific hint by ID"""
    # Arrange
    hint_id = "test_hint_456"
    mock_hint_doc = {
        "hint_id": hint_id,
        "title": "Test Hint",
        "content": "This is a test hint",
        "hint_type": "narrative",
        "created_at": datetime.utcnow()
    }
    
    hint_system.db.find_narrative_fragments_by_criteria.return_value = [mock_hint_doc]
    
    # Act
    result = await hint_system.get_hint_by_id(hint_id)
    
    # Assert
    assert isinstance(result, Hint)
    assert result.hint_id == hint_id
    assert result.title == "Test Hint"


@pytest.mark.asyncio
async def test_get_hint_by_id_not_found(hint_system):
    """Test retrieving a hint that doesn't exist"""
    # Arrange
    hint_id = "nonexistent_hint"
    hint_system.db.find_narrative_fragments_by_criteria.return_value = []
    
    # Act
    result = await hint_system.get_hint_by_id(hint_id)
    
    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_lock_hint_success(hint_system):
    """Test successfully locking a hint"""
    # Arrange
    user_id = "test_user_123"
    hint_id = "test_hint_456"
    
    # Mock user data that has the hint unlocked and in inventory
    hint_system.db.get_user.return_value = {
        "user_id": user_id,
        "narrative_progress": {"unlocked_hints": [hint_id]},
        "inventory": [{"item_id": f"hint_{hint_id}", "name": "Test Hint"}]
    }
    hint_system.db.update_user.return_value = True  # Simulate successful update
    
    # Act
    result = await hint_system.lock_hint(user_id, hint_id)
    
    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_combine_hints_success(hint_system):
    """Test successful hint combination"""
    # Arrange
    user_id = "test_user_123"
    hint_ids = ["hint_1", "hint_2"]
    
    hint_system.db.get_user.return_value = {
        "user_id": user_id,
        "narrative_progress": {"unlocked_hints": ["hint_1", "hint_2", "hint_3"]}  # User has all required hints
    }
    
    # Act
    result = await hint_system.combine_hints(user_id, hint_ids)
    
    # Assert
    assert result is not None
    assert result["success"] is True
    assert result["combined_hints"] == hint_ids


@pytest.mark.asyncio
async def test_combine_hints_missing_hint(hint_system):
    """Test hint combination when user is missing a hint"""
    # Arrange
    user_id = "test_user_123"
    hint_ids = ["hint_1", "hint_4"]  # User doesn't have hint_4
    
    hint_system.db.get_user.return_value = {
        "user_id": user_id,
        "narrative_progress": {"unlocked_hints": ["hint_1", "hint_2", "hint_3"]}  # Missing hint_4
    }
    
    # Act
    result = await hint_system.combine_hints(user_id, hint_ids)
    
    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_combine_hints_user_not_found(hint_system):
    """Test hint combination for a user that doesn't exist"""
    # Arrange
    user_id = "nonexistent_user"
    hint_ids = ["hint_1", "hint_2"]
    
    hint_system.db.get_user.return_value = None
    
    # Act
    result = await hint_system.combine_hints(user_id, hint_ids)
    
    # Assert
    assert result is None