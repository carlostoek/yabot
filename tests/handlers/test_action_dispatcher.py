"""
Unit tests for the ActionDispatcher class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, ANY
from datetime import datetime

from src.handlers.action_dispatcher import ActionDispatcher, CallbackActionResult
from src.ui.menu_factory import Menu, MenuType, UserRole
from src.events.models import BaseEvent


# Mock data
USER_ID = 67890

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
def mock_user_service():
    """Create a mock user service for testing."""
    return AsyncMock()


@pytest.fixture
def action_dispatcher(mock_event_bus, mock_user_service):
    """Create an ActionDispatcher instance for testing."""
    return ActionDispatcher(event_bus=mock_event_bus, user_service=mock_user_service)


@pytest.mark.asyncio
async def test_action_dispatcher_initialization(action_dispatcher):
    """Test ActionDispatcher initialization."""
    assert action_dispatcher.event_bus is not None
    assert action_dispatcher.user_service is not None
    assert isinstance(action_dispatcher._action_handlers, dict)
    # Check that default and module handlers are registered
    assert "gamification" in action_dispatcher._action_handlers
    assert "besitos" in action_dispatcher._action_handlers
    assert "missions" in action_dispatcher._action_handlers


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

    # Verify event bus was called for menu interaction and action completion
    assert mock_event_bus.publish.call_count == 2
    mock_event_bus.publish.assert_any_call("menu_interaction", ANY)
    mock_event_bus.publish.assert_any_call("action_completed", ANY)


@pytest.mark.asyncio
async def test_action_dispatcher_dispatch_unsupported_action(action_dispatcher, mock_event_bus):
    """Test ActionDispatcher handling of unsupported actions."""
    result = await action_dispatcher.dispatch_action("unsupported_action", "test_data", USER_CONTEXT)

    # Verify the result
    assert result.success is False
    assert "not supported" in result.response_message

    # Verify event bus was called for menu interaction and unsupported action
    assert mock_event_bus.publish.call_count == 2
    mock_event_bus.publish.assert_any_call("menu_interaction", ANY)
    mock_event_bus.publish.assert_any_call("unsupported_action", ANY)


@pytest.mark.asyncio
async def test_action_dispatcher_dispatch_action_with_error(action_dispatcher, mock_event_bus):
    """Test ActionDispatcher handling of action errors."""
    # Register a handler that raises an exception
    async def error_handler(action_data: str, user_context: dict):
        raise Exception("Test error")

    action_dispatcher.register_action_handler("error_action", error_handler)

    # Dispatch an action that will error
    result = await action_dispatcher.dispatch_action("error_action", "test_data", USER_CONTEXT)

    # Verify the result
    assert result.success is False
    assert "Error processing action" in result.response_message

    # Verify event bus was called for menu interaction and action error
    assert mock_event_bus.publish.call_count == 2
    mock_event_bus.publish.assert_any_call("menu_interaction", ANY)
    mock_event_bus.publish.assert_any_call("action_error", ANY)


@pytest.mark.asyncio
async def test_action_dispatcher_process_action_result_with_context_updates(action_dispatcher, mock_user_service):
    """Test ActionDispatcher processing action results with context updates."""
    # Create a result with context updates
    result = CallbackActionResult(
        success=True,
        response_message="Test response",
        user_context_updates={"new_field": "new_value", "besitos_balance": 150}
    )

    # Process the result
    processed_result = await action_dispatcher.process_action_result(result, USER_CONTEXT)

    # Verify the result is returned unchanged
    assert processed_result.success is True
    assert processed_result.response_message == "Test response"

    # Verify user service was called to update context
    mock_user_service.update_user_context.assert_called_once_with(
        USER_ID, 
        {"new_field": "new_value", "besitos_balance": 150}
    )


@pytest.mark.asyncio
async def test_action_dispatcher_process_action_result_with_events(action_dispatcher, mock_event_bus):
    """Test ActionDispatcher processing action results with custom events."""
    # Create a result with custom events to publish
    result = CallbackActionResult(
        success=True,
        response_message="Test response",
        events_to_publish=[
            {
                "event_type": "custom_event",
                "custom_field": "custom_value",
                "user_id": USER_ID
            }
        ]
    )

    # Process the result
    processed_result = await action_dispatcher.process_action_result(result, USER_CONTEXT)

    # Verify the result is returned unchanged
    assert processed_result.success is True
    assert processed_result.response_message == "Test response"

    # Verify event bus was called to publish custom event
    mock_event_bus.publish.assert_called_once_with("custom_event", ANY)


@pytest.mark.asyncio
async def test_action_dispatcher_handle_gamification_action(action_dispatcher):
    """Test ActionDispatcher handling of gamification actions."""
    # Test show_wallet action
    result = await action_dispatcher._handle_gamification_action("show_wallet", USER_CONTEXT)
    
    # Verify the result
    assert result.success is True
    assert "besitos in your wallet" in result.response_message
    assert result.cleanup_messages is False

    # Test unknown action
    result = await action_dispatcher._handle_gamification_action("unknown_action", USER_CONTEXT)
    
    # Verify the result
    assert result.success is False
    assert "Unknown gamification action" in result.response_message


@pytest.mark.asyncio
async def test_action_dispatcher_handle_module_actions(action_dispatcher):
    """Test ActionDispatcher handling of module actions."""
    # Test besitos action
    result = await action_dispatcher._handle_besitos_action("test_besitos", USER_CONTEXT)
    assert result.success is True
    assert "besitos action: test_besitos" in result.response_message

    # Test missions action
    result = await action_dispatcher._handle_missions_action("test_missions", USER_CONTEXT)
    assert result.success is True
    assert "missions action: test_missions" in result.response_message

    # Test achievements action
    result = await action_dispatcher._handle_achievements_action("test_achievements", USER_CONTEXT)
    assert result.success is True
    assert "achievements action: test_achievements" in result.response_message

    # Test store action
    result = await action_dispatcher._handle_store_action("test_store", USER_CONTEXT)
    assert result.success is True
    assert "store action: test_store" in result.response_message

    # Test daily gift action
    result = await action_dispatcher._handle_daily_gift_action("test_daily_gift", USER_CONTEXT)
    assert result.success is True
    assert "daily gift action: test_daily_gift" in result.response_message

    # Test narrative action
    result = await action_dispatcher._handle_narrative_action("test_narrative", USER_CONTEXT)
    assert result.success is True
    assert "narrative action: test_narrative" in result.response_message

    # Test fragments action
    result = await action_dispatcher._handle_fragments_action("test_fragments", USER_CONTEXT)
    assert result.success is True
    assert "fragments action: test_fragments" in result.response_message

    # Test hints action
    result = await action_dispatcher._handle_hints_action("test_hints", USER_CONTEXT)
    assert result.success is True
    assert "hints action: test_hints" in result.response_message

    # Test admin action
    result = await action_dispatcher._handle_admin_action("test_admin", USER_CONTEXT)
    assert result.success is True
    assert "admin action: test_admin" in result.response_message

    # Test subscriptions action
    result = await action_dispatcher._handle_subscriptions_action("test_subscriptions", USER_CONTEXT)
    assert result.success is True
    assert "subscriptions action: test_subscriptions" in result.response_message

    # Test notifications action
    result = await action_dispatcher._handle_notifications_action("test_notifications", USER_CONTEXT)
    assert result.success is True
    assert "notifications action: test_notifications" in result.response_message


if __name__ == "__main__":
    pytest.main([__file__])