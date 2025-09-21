"""
Unit tests for UserService menu context methods.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.services.user import UserService, UserServiceError
from src.database.manager import DatabaseManager
from src.events.bus import EventBus


@pytest.fixture
def mock_database_manager():
    """Create a mock database manager for testing."""
    return AsyncMock(spec=DatabaseManager)


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    return AsyncMock(spec=EventBus)


@pytest.fixture
def user_service(mock_database_manager, mock_event_bus):
    """Create a UserService instance with mocked dependencies."""
    return UserService(mock_database_manager, mock_event_bus)


@pytest.mark.asyncio
async def test_get_user_menu_context_success(user_service):
    """Test successful retrieval of user menu context."""
    # Mock user context data
    mock_user_context = {
        "user_id": "test_user_123",
        "profile": {
            "role": "vip_user",
            "has_vip": True
        },
        "state": {
            "current_state": {
                "menu_context": "gamification_menu",
                "navigation_path": ["main_menu", "narrative_menu"],
                "session_data": {"last_action": "view_wallet"}
            },
            "preferences": {
                "language": "es",
                "theme": "dark"
            },
            "emotional_journey": {
                "current_level": 3
            },
            "lucien_interaction_context": {
                "worthiness_progression": {
                    "current_worthiness_score": 0.75
                },
                "user_archetype_assessment": {
                    "detected_archetype": "explorer"
                }
            },
            "besitos": 150,
            "updated_at": "2023-01-01T00:00:00Z"
        }
    }
    
    # Mock the get_user_context method
    user_service.get_user_context = AsyncMock(return_value=mock_user_context)
    
    # Call the method
    result = await user_service.get_user_menu_context("test_user_123")
    
    # Verify the result
    assert result is not None
    assert result["user_id"] == "test_user_123"
    assert result["current_menu_id"] == "gamification_menu"
    assert result["navigation_path"] == ["main_menu", "narrative_menu"]
    assert result["session_data"] == {"last_action": "view_wallet"}
    assert result["role"] == "vip_user"
    assert result["has_vip"] is True
    assert result["narrative_level"] == 3
    assert result["worthiness_score"] == 0.75
    assert result["besitos_balance"] == 150
    assert result["archetype"] == "explorer"


@pytest.mark.asyncio
async def test_get_user_menu_context_with_missing_data(user_service):
    """Test menu context retrieval with missing user data."""
    # Mock user context with missing data
    mock_user_context = {
        "user_id": "test_user_123",
        "profile": {},
        "state": {}
    }
    
    # Mock the get_user_context method
    user_service.get_user_context = AsyncMock(return_value=mock_user_context)
    
    # Call the method
    result = await user_service.get_user_menu_context("test_user_123")
    
    # Verify the result uses defaults
    assert result is not None
    assert result["user_id"] == "test_user_123"
    assert result["current_menu_id"] == "main_menu"  # Default
    assert result["role"] == "free_user"  # Default
    assert result["has_vip"] is False  # Default
    assert result["narrative_level"] == 1  # Default


@pytest.mark.asyncio
async def test_get_user_menu_context_user_not_found(user_service):
    """Test menu context retrieval when user is not found."""
    # Mock the get_user_context method to raise UserNotFoundError
    user_service.get_user_context = AsyncMock(side_effect=UserServiceError("User not found"))
    
    # Call the method
    result = await user_service.get_user_menu_context("nonexistent_user")
    
    # Verify the result uses defaults
    assert result is not None
    assert result["user_id"] == "unknown"  # Default fallback
    assert result["current_menu_id"] == "main_menu"  # Default


@pytest.mark.asyncio
async def test_update_user_menu_context_success(user_service):
    """Test successful update of user menu context."""
    # Mock the update_user_state method
    user_service.update_user_state = AsyncMock(return_value=True)
    
    # Prepare updates
    updates = {
        "current_menu_id": "new_menu",
        "navigation_path": ["main_menu", "new_menu"],
        "menu_preferences": {"theme": "light"},
        "session_data": {"temp_value": "test"}
    }
    
    # Call the method
    result = await user_service.update_user_menu_context("test_user_123", updates)
    
    # Verify the result
    assert result is True
    user_service.update_user_state.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_menu_context_no_updates(user_service):
    """Test update of user menu context with no actual updates."""
    # Mock the update_user_state method
    user_service.update_user_state = AsyncMock(return_value=True)
    
    # Call the method with empty updates
    result = await user_service.update_user_menu_context("test_user_123", {})
    
    # Verify the result
    assert result is True
    user_service.update_user_state.assert_not_called()


@pytest.mark.asyncio
async def test_push_menu_navigation(user_service):
    """Test pushing a menu to navigation path."""
    # Mock current context
    mock_context = {
        "navigation_path": ["main_menu"]
    }
    
    # Mock methods
    user_service.get_user_menu_context = AsyncMock(return_value=mock_context)
    user_service.update_user_menu_context = AsyncMock(return_value=True)
    
    # Call the method
    result = await user_service.push_menu_navigation("test_user_123", "new_menu")
    
    # Verify the result
    assert result is True
    user_service.update_user_menu_context.assert_called_once()
    
    # Verify the update contains the new navigation path
    called_args = user_service.update_user_menu_context.call_args[0]
    assert called_args[0] == "test_user_123"
    assert "navigation_path" in called_args[1]
    assert called_args[1]["navigation_path"] == ["main_menu", "new_menu"]


@pytest.mark.asyncio
async def test_pop_menu_navigation(user_service):
    """Test popping a menu from navigation path."""
    # Mock current context
    mock_context = {
        "navigation_path": ["main_menu", "previous_menu"]
    }
    
    # Mock methods
    user_service.get_user_menu_context = AsyncMock(return_value=mock_context)
    user_service.update_user_menu_context = AsyncMock(return_value=True)
    
    # Call the method
    result = await user_service.pop_menu_navigation("test_user_123")
    
    # Verify the result
    assert result == "previous_menu"
    user_service.update_user_menu_context.assert_called_once()
    
    # Verify the update contains the modified navigation path
    called_args = user_service.update_user_menu_context.call_args[0]
    assert called_args[0] == "test_user_123"
    assert "navigation_path" in called_args[1]
    assert called_args[1]["navigation_path"] == ["main_menu"]


@pytest.mark.asyncio
async def test_pop_menu_navigation_empty_path(user_service):
    """Test popping from empty navigation path."""
    # Mock current context with empty path
    mock_context = {
        "navigation_path": []
    }
    
    # Mock methods
    user_service.get_user_menu_context = AsyncMock(return_value=mock_context)
    user_service.update_user_menu_context = AsyncMock(return_value=True)
    
    # Call the method
    result = await user_service.pop_menu_navigation("test_user_123")
    
    # Verify the result
    assert result is None
    user_service.update_user_menu_context.assert_not_called()


@pytest.mark.asyncio
async def test_clear_menu_navigation(user_service):
    """Test clearing navigation path."""
    # Mock the update_user_menu_context method
    user_service.update_user_menu_context = AsyncMock(return_value=True)
    
    # Call the method
    result = await user_service.clear_menu_navigation("test_user_123")
    
    # Verify the result
    assert result is True
    user_service.update_user_menu_context.assert_called_once_with("test_user_123", {"navigation_path": []})


@pytest.mark.asyncio
async def test_update_menu_session_data(user_service):
    """Test updating menu session data."""
    # Mock current context
    mock_context = {
        "session_data": {"existing_key": "existing_value"}
    }
    
    # Mock methods
    user_service.get_user_menu_context = AsyncMock(return_value=mock_context)
    user_service.update_user_menu_context = AsyncMock(return_value=True)
    
    # Prepare updates
    updates = {"new_key": "new_value", "existing_key": "updated_value"}
    
    # Call the method
    result = await user_service.update_menu_session_data("test_user_123", updates)
    
    # Verify the result
    assert result is True
    user_service.update_user_menu_context.assert_called_once()
    
    # Verify the update contains merged session data
    called_args = user_service.update_user_menu_context.call_args[0]
    assert called_args[0] == "test_user_123"
    assert "session_data" in called_args[1]
    assert called_args[1]["session_data"] == {
        "existing_key": "updated_value",
        "new_key": "new_value"
    }