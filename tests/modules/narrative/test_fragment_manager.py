"""
Unit tests for the narrative fragment manager.
Implements tests for requirements 1.1, 1.4, and 1.5 from the modulos-atomicos specification.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.modules.narrative.fragment_manager import (
    NarrativeFragmentManager,
    FragmentNotFoundError,
    VIPAccessRequiredError,
    ProgressionValidationError
)
from src.database.mongodb import MongoDBHandler
from src.events.bus import EventBus


@pytest.fixture
def mock_mongodb_handler():
    """Create a mock MongoDB handler for testing."""
    mock_handler = Mock(spec=MongoDBHandler)
    mock_handler.get_narrative_fragments_collection.return_value = Mock()
    mock_handler.get_users_collection.return_value = Mock()
    return mock_handler


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    mock_bus = Mock(spec=EventBus)
    mock_bus.publish = AsyncMock()
    mock_bus.is_connected = True
    return mock_bus


@pytest.fixture
def fragment_manager(mock_mongodb_handler, mock_event_bus):
    """Create a narrative fragment manager instance for testing."""
    return NarrativeFragmentManager(mock_mongodb_handler, mock_event_bus)


@pytest.fixture
def sample_fragment():
    """Create a sample narrative fragment for testing."""
    return {
        "fragment_id": "test_fragment_1",
        "title": "Test Fragment",
        "content": "This is a test narrative fragment.",
        "choices": [
            {
                "choice_id": "choice_1",
                "text": "First choice",
                "next_fragment_id": "test_fragment_2"
            },
            {
                "choice_id": "choice_2",
                "text": "Second choice",
                "next_fragment_id": "test_fragment_3"
            }
        ],
        "vip_required": False,
        "published": True,
        "metadata": {
            "tags": ["test"],
            "is_checkpoint": False
        }
    }


@pytest.fixture
def sample_vip_fragment():
    """Create a sample VIP narrative fragment for testing."""
    return {
        "fragment_id": "vip_fragment_1",
        "title": "VIP Fragment",
        "content": "This is a VIP narrative fragment.",
        "choices": [
            {
                "choice_id": "choice_1",
                "text": "First choice",
                "next_fragment_id": "vip_fragment_2"
            }
        ],
        "vip_required": True,
        "published": True,
        "metadata": {
            "tags": ["vip"],
            "is_checkpoint": False
        }
    }


@pytest.fixture
def sample_user_progress():
    """Create sample user progress data for testing."""
    return {
        "user_id": "test_user_123",
        "current_fragment": "start",
        "completed_fragments": ["intro_1", "intro_2"],
        "unlocked_hints": [],
        "choices_made": {
            "intro_1": "choice_a",
            "intro_2": "choice_b"
        },
        "progress_data": {},
        "start_time": datetime.utcnow(),
        "last_updated": datetime.utcnow(),
        "completion_percentage": 20.0,
        "active": True
    }


class TestNarrativeFragmentManager:
    """Test suite for the NarrativeFragmentManager class."""

    # Test requirement 1.1: WHEN a user requests a narrative fragment
    # THEN the system SHALL retrieve the fragment from MongoDB with text and decision options
    def test_get_fragment_success(self, fragment_manager, mock_mongodb_handler, sample_fragment):
        """Test successful retrieval of a narrative fragment."""
        # Arrange
        mock_collection = mock_mongodb_handler.get_narrative_fragments_collection.return_value
        mock_collection.find_one.return_value = sample_fragment
        fragment_id = "test_fragment_1"
        user_id = "test_user_123"

        # Act
        result = asyncio.run(fragment_manager.get_fragment(fragment_id, user_id))

        # Assert
        assert result == sample_fragment
        mock_collection.find_one.assert_called_once_with({"fragment_id": fragment_id})
        mock_mongodb_handler.get_narrative_fragments_collection.assert_called_once()

    def test_get_fragment_not_found(self, fragment_manager, mock_mongodb_handler):
        """Test behavior when fragment is not found."""
        # Arrange
        mock_collection = mock_mongodb_handler.get_narrative_fragments_collection.return_value
        mock_collection.find_one.return_value = None
        fragment_id = "nonexistent_fragment"

        # Act & Assert
        with pytest.raises(FragmentNotFoundError):
            asyncio.run(fragment_manager.get_fragment(fragment_id))

    # Test requirement 1.4: IF a user has VIP status
    # THEN the system SHALL allow access to premium narrative levels
    def test_get_vip_fragment_without_user_id(self, fragment_manager, mock_mongodb_handler, sample_vip_fragment):
        """Test that VIP fragment requires user ID."""
        # Arrange
        mock_collection = mock_mongodb_handler.get_narrative_fragments_collection.return_value
        mock_collection.find_one.return_value = sample_vip_fragment
        fragment_id = "vip_fragment_1"

        # Act & Assert
        with pytest.raises(VIPAccessRequiredError):
            asyncio.run(fragment_manager.get_fragment(fragment_id))

    def test_get_vip_fragment_with_user_id(self, fragment_manager, mock_mongodb_handler, mock_event_bus, sample_vip_fragment):
        """Test successful retrieval of VIP fragment with user ID."""
        # Arrange
        mock_collection = mock_mongodb_handler.get_narrative_fragments_collection.return_value
        mock_collection.find_one.return_value = sample_vip_fragment
        fragment_id = "vip_fragment_1"
        user_id = "test_user_123"

        # Act
        result = asyncio.run(fragment_manager.get_fragment(fragment_id, user_id))

        # Assert
        assert result == sample_vip_fragment
        # Check that VIP validation event was published
        mock_event_bus.publish.assert_called()

    # Test requirement 1.5: WHEN a narrative checkpoint is reached
    # THEN the system SHALL validate progression conditions via the coordinator service
    def test_update_progress_success(self, fragment_manager, mock_mongodb_handler, mock_event_bus, sample_user_progress):
        """Test successful progress update."""
        # Arrange
        user_id = "test_user_123"
        fragment_id = "test_fragment_1"
        choice_id = "choice_1"

        # Mock get_user_progress to return sample data
        with patch.object(fragment_manager, 'get_user_progress', AsyncMock(return_value=sample_user_progress)):
            # Mock _update_progress_in_db to return success
            with patch.object(fragment_manager, '_update_progress_in_db', AsyncMock(return_value=True)):
                # Mock _is_checkpoint to return False for simplicity
                with patch.object(fragment_manager, '_is_checkpoint', AsyncMock(return_value=False)):
                    # Act
                    result = asyncio.run(fragment_manager.update_progress(user_id, fragment_id, choice_id))

                    # Assert
                    assert result is True
                    fragment_manager._update_progress_in_db.assert_called_once()
                    mock_event_bus.publish.assert_called()

    def test_update_progress_validation_error(self, fragment_manager, mock_mongodb_handler, sample_user_progress):
        """Test progress update with validation error."""
        # Arrange
        user_id = "test_user_123"
        fragment_id = "restricted_fragment_1"

        # Mock get_user_progress to return sample data
        with patch.object(fragment_manager, 'get_user_progress', AsyncMock(return_value=sample_user_progress)):
            # Mock _validate_progression_conditions to raise an error
            with patch.object(fragment_manager, '_validate_progression_conditions', AsyncMock(side_effect=ProgressionValidationError("Progression conditions not met"))):
                # Act & Assert
                with pytest.raises(ProgressionValidationError):
                    asyncio.run(fragment_manager.update_progress(user_id, fragment_id))

    def test_get_user_progress_new_user(self, fragment_manager, mock_mongodb_handler):
        """Test getting progress for a new user."""
        # Arrange
        user_id = "new_user_456"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        mock_users_collection.find_one.return_value = None  # User not found

        # Act
        result = asyncio.run(fragment_manager.get_user_progress(user_id))

        # Assert
        assert result["user_id"] == user_id
        assert result["current_fragment"] == "start"
        assert result["completed_fragments"] == []
        assert "start_time" in result
        assert "last_updated" in result

    def test_get_user_progress_existing_user(self, fragment_manager, mock_mongodb_handler, sample_user_progress):
        """Test getting progress for an existing user."""
        # Arrange
        user_id = "test_user_123"
        mock_users_collection = mock_mongodb_handler.get_users_collection.return_value
        mock_users_collection.find_one.return_value = {
            "current_state": {
                "narrative_progress": sample_user_progress
            }
        }

        # Act
        result = asyncio.run(fragment_manager.get_user_progress(user_id))

        # Assert
        assert result == sample_user_progress
        assert result["user_id"] == user_id
        assert result["completed_fragments"] == ["intro_1", "intro_2"]

    def test_health_check(self, fragment_manager, mock_mongodb_handler, mock_event_bus):
        """Test health check functionality."""
        # Arrange
        mock_collection = mock_mongodb_handler.get_narrative_fragments_collection.return_value
        mock_collection.find_one.return_value = {"_id": "test"}

        # Act
        result = asyncio.run(fragment_manager.health_check())

        # Assert
        assert result["status"] == "healthy"
        assert result["mongodb_connected"] is True
        assert result["event_bus_connected"] is True
        assert "timestamp" in result


if __name__ == "__main__":
    pytest.main([__file__])