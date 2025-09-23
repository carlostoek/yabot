
"""
Unit tests for the MenuHandlerSystem class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, ANY

from src.handlers.menu_handler import MenuHandlerSystem
from src.ui.menu_factory import Menu, MenuType

# Mock data
CHAT_ID = 12345
USER_ID = 67890
MESSAGE_ID = 54321

@pytest.fixture
def mock_user_service():
    return AsyncMock()

@pytest.fixture
def mock_event_bus():
    return AsyncMock()

@pytest.fixture
def mock_menu_factory():
    # Create a mock for the MenuFactory
    factory = AsyncMock()
    # Mock the create_menu method to return a mock Menu object
    mock_menu = Menu(
        menu_id='main_menu', 
        title='Main Menu', 
        description='Welcome', 
        menu_type=MenuType.MAIN, 
        required_role='free_user',
        items=[],
        max_columns=2
    )
    factory.create_menu.return_value = mock_menu
    return factory

@pytest.fixture
def mock_message_manager():
    manager = AsyncMock()
    manager.bot = AsyncMock()
    # Mock the bot's send_message to return a mock message object with an ID
    sent_message_mock = MagicMock()
    sent_message_mock.message_id = MESSAGE_ID + 1
    sent_message_mock.chat.id = CHAT_ID
    manager.bot.send_message.return_value = sent_message_mock
    manager.bot.edit_message_text.return_value = True
    return manager

@pytest.fixture
def menu_handler(mock_user_service, mock_event_bus, mock_menu_factory, mock_message_manager):
    """Provides a MenuHandlerSystem instance with mocked dependencies."""
    handler = MenuHandlerSystem(
        user_service=mock_user_service,
        event_bus=mock_event_bus,
        menu_factory=mock_menu_factory,
        message_manager=mock_message_manager
    )
    # Also mock the internal evaluation tracker to isolate the handler logic
    handler._track_lucien_evaluation = AsyncMock()
    return handler

@pytest.fixture
def mock_message():
    """Provides a mock aiogram Message object."""
    user = MagicMock()
    user.id = USER_ID
    user.model_dump.return_value = {'id': USER_ID, 'username': 'test'}

    chat = MagicMock()
    chat.id = CHAT_ID

    message = MagicMock()
    message.from_user = user
    message.chat = chat
    message.text = "/start"
    return message

@pytest.fixture
def mock_callback_query():
    """Provides a mock aiogram CallbackQuery object."""
    user = MagicMock()
    user.id = USER_ID

    chat = MagicMock()
    chat.id = CHAT_ID

    message = MagicMock()
    message.chat = chat
    message.message_id = MESSAGE_ID

    query = AsyncMock()
    query.from_user = user
    query.message = message
    query.data = "menu:main_menu"
    return query


@pytest.mark.asyncio
async def test_handle_command_success(menu_handler, mock_message, mock_message_manager, mock_user_service, mock_menu_factory, mock_event_bus):
    """Test the successful handling of a command."""
    await menu_handler.handle_command(mock_message)

    # 1. Cleanup was called
    mock_message_manager.delete_old_messages.assert_awaited_once_with(CHAT_ID)

    # 2. User context was retrieved
    mock_user_service.get_or_create_user_context.assert_awaited_once()

    # 3. Lucien evaluation was tracked
    menu_handler._track_lucien_evaluation.assert_awaited_once()

    # 4. Menu was created
    mock_menu_factory.create_menu.assert_awaited_once()

    # 5. Message was sent
    mock_message_manager.bot.send_message.assert_awaited_once()

    # 6. New message was tracked
    mock_message_manager.track_message.assert_awaited_once_with(
        CHAT_ID, MESSAGE_ID + 1, 'main_menu', is_main_menu=True
    )

    # 7. Event was published
    mock_event_bus.publish.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_callback_success(menu_handler, mock_callback_query, mock_message_manager, mock_user_service, mock_menu_factory, mock_event_bus):
    """Test the successful handling of a callback query."""
    await menu_handler.handle_callback(mock_callback_query)

    # 1. Callback was answered
    mock_callback_query.answer.assert_awaited_once()

    # 2. User context was retrieved
    mock_user_service.get_user_context.assert_awaited_once()

    # 3. Lucien evaluation was tracked
    menu_handler._track_lucien_evaluation.assert_awaited_once()

    # 4. Menu was created
    mock_menu_factory.create_menu.assert_awaited_once_with("main_menu", ANY)

    # 5. Message was edited
    mock_message_manager.bot.edit_message_text.assert_awaited_once()
    mock_message_manager.bot.send_message.assert_not_called()

    # 6. Event was published
    mock_event_bus.publish.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_callback_edit_failure_fallback(menu_handler, mock_callback_query, mock_message_manager):
    """Test that the handler sends a new message if editing fails."""
    # Arrange: Make editing fail
    mock_message_manager.bot.edit_message_text.side_effect = Exception("Edit failed")

    await menu_handler.handle_callback(mock_callback_query)

    # Assert that edit was attempted
    mock_message_manager.bot.edit_message_text.assert_awaited_once()

    # Assert that it fell back to sending a new message
    mock_message_manager.delete_old_messages.assert_awaited_once()
    mock_message_manager.bot.send_message.assert_awaited_once()
    mock_message_manager.track_message.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_command_user_service_failure(menu_handler, mock_message, mock_user_service, mock_message_manager):
    """Test error handling when the user service fails."""
    # Arrange: Make user service fail
    mock_user_service.get_or_create_user_context.side_effect = Exception("DB down")

    await menu_handler.handle_command(mock_message)

    # Assert an error message was sent
    mock_message_manager.bot.send_message.assert_awaited_once()
    args, kwargs = mock_message_manager.bot.send_message.call_args
    assert "Error" in args[1]

    # Assert the error message was tracked
    mock_message_manager.track_message.assert_awaited_once_with(ANY, ANY, 'error_message')
