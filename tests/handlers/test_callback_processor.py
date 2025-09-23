"""
Unit tests for the CallbackProcessor and ActionDispatcher classes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, ANY, patch
from datetime import datetime

from src.handlers.callback_processor import CallbackProcessor, ActionDispatcher, CallbackActionResult
from src.ui.menu_factory import Menu, MenuType, MenuItem, ActionType, UserRole
from src.events.models import BaseEvent


# Mock data
CHAT_ID = 12345
USER_ID = 67890
MESSAGE_ID = 54321

USER_CONTEXT = {
    "user_id": USER_ID,
    "role": "free_user",
    "besitos_balance": 100,
    "narrative_level": 3
}


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    return AsyncMock()


@pytest.fixture
def mock_menu_factory():
    """Create a mock menu factory for testing."""
    factory = AsyncMock()
    # Create a mock menu
    mock_menu = Menu(
        menu_id='test_menu',
        title='Test Menu',
        description='Test menu for testing',
        menu_type=MenuType.MAIN,
        required_role=UserRole.FREE_USER,
        items=[],
        max_columns=2
    )
    factory.create_menu.return_value = mock_menu
    return factory


@pytest.fixture
def mock_message_manager():
    """Create a mock message manager for testing."""
    return AsyncMock()


@pytest.fixture
def action_dispatcher(mock_event_bus):
    """Create an ActionDispatcher instance for testing."""
    return ActionDispatcher(event_bus=mock_event_bus)


@pytest.fixture
def callback_processor(mock_event_bus, mock_menu_factory, mock_message_manager):
    """Create a CallbackProcessor instance for testing."""
    action_dispatcher = ActionDispatcher(event_bus=mock_event_bus)
    return CallbackProcessor(
        action_dispatcher=action_dispatcher,
        message_manager=mock_message_manager,
        menu_factory=mock_menu_factory,
        event_bus=mock_event_bus
    )


@pytest.mark.asyncio
async def test_action_dispatcher_initialization(action_dispatcher):
    """Test ActionDispatcher initialization."""
    assert action_dispatcher.event_bus is not None
    assert isinstance(action_dispatcher._action_handlers, dict)


@pytest.mark.asyncio
async def test_action_dispatcher_register_handler(action_dispatcher):
    """Test registering a handler with ActionDispatcher."""
    async def test_handler(action_data: str, user_context: dict):
        return CallbackActionResult(success=True, response_message="Test response")

    action_dispatcher.register_action_handler("test_action", test_handler)
    assert "test_action" in action_dispatcher._action_handlers


@pytest.mark.asyncio
async def test_action_dispatcher_dispatch_action_with_event_bus(action_dispatcher, mock_event_bus):
    """Test ActionDispatcher dispatch_action with event bus integration."""
    # Register a test handler
    async def test_handler(action_data: str, user_context: dict):
        return CallbackActionResult(success=True, response_message="Test response")

    action_dispatcher.register_action_handler("test_action", test_handler)

    # Dispatch an action
    result = await action_dispatcher.dispatch_action("test_action", "test_data", USER_CONTEXT)

    # Verify the result
    assert result.success is True
    assert result.response_message == "Test response"

    # Verify event bus was called
    assert mock_event_bus.publish.call_count == 2  # menu_interaction and action_completed events


@pytest.mark.asyncio
async def test_action_dispatcher_dispatch_unsupported_action(action_dispatcher, mock_event_bus):
    """Test ActionDispatcher handling of unsupported actions."""
    result = await action_dispatcher.dispatch_action("unsupported_action", "test_data", USER_CONTEXT)

    # Verify the result
    assert result.success is False
    assert "not supported" in result.response_message

    # Verify event bus was called for unsupported action
    assert mock_event_bus.publish.call_count == 2  # menu_interaction and unsupported_action events


@pytest.mark.asyncio
async def test_callback_processor_initialization(callback_processor):
    """Test CallbackProcessor initialization."""
    assert callback_processor.event_bus is not None
    assert callback_processor.action_dispatcher is not None
    assert callback_processor.message_manager is not None
    assert callback_processor.menu_factory is not None


@pytest.mark.asyncio
async def test_callback_processor_process_menu_navigation(callback_processor, mock_event_bus, mock_menu_factory):
    """Test CallbackProcessor processing menu navigation."""
    # Process a menu navigation callback
    result = await callback_processor.process_callback("menu:test_menu", USER_CONTEXT, CHAT_ID)

    # Verify the result
    assert result.success is True
    assert result.new_menu is not None

    # Verify event bus was called
    assert mock_event_bus.publish.call_count == 2  # callback_received and menu_navigation events


@pytest.mark.asyncio
async def test_callback_processor_process_action(callback_processor, mock_event_bus):
    """Test CallbackProcessor processing an action."""
    # Register a test handler
    async def test_handler(action_data: str, user_context: dict):
        return CallbackActionResult(success=True, response_message="Action response")

    callback_processor.action_dispatcher.register_action_handler("test_action", test_handler)

    # Process an action callback
    result = await callback_processor.process_callback("test_action:test_data", USER_CONTEXT, CHAT_ID)

    # Verify the result
    assert result.success is True
    assert result.response_message == "Action response"

    # Verify event bus was called
    assert mock_event_bus.publish.call_count == 3  # callback_received, menu_interaction, and callback_processed events


@pytest.mark.asyncio
async def test_callback_processor_process_invalid_callback(callback_processor, mock_event_bus):
    """Test CallbackProcessor handling of invalid callback data."""
    # Process invalid callback data (too long)
    long_data = "a" * 100  # Exceeds Telegram's 64-byte limit
    result = await callback_processor.process_callback(long_data, USER_CONTEXT, CHAT_ID)

    # Verify the result
    assert result.success is False
    assert result.response_message == "Invalid action."

    # Verify event bus was called
    assert mock_event_bus.publish.call_count == 2  # callback_received and invalid_callback events


@pytest.mark.asyncio
async def test_callback_processor_cleanup_after_callback(callback_processor, mock_event_bus):
    """Test CallbackProcessor cleanup after callback processing."""
    # Call cleanup
    await callback_processor.cleanup_after_callback(CHAT_ID)

    # Verify event bus was called
    assert mock_event_bus.publish.call_count == 2  # cleanup_started and cleanup_completed events


@pytest.mark.asyncio
async def test_callback_processor_validate_callback_data():
    """Test CallbackProcessor callback data validation."""
    # Test valid callback data
    valid_data = "valid_callback_data"
    assert callback_processor.validate_callback_data(valid_data) is True

    # Test invalid callback data (too long)
    invalid_data = "a" * 100  # Exceeds Telegram's 64-byte limit
    assert callback_processor.validate_callback_data(invalid_data) is False


if __name__ == "__main__":
    pytest.main([__file__])