"""
Unit tests for the TelegramMenuRenderer class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, ANY
from datetime import datetime

from src.ui.telegram_menu_renderer import TelegramMenuRenderer
from src.ui.menu_factory import Menu, MenuType, MenuItem, ActionType, UserRole


# Mock data
CHAT_ID = 12345
MESSAGE_ID = 54321

TEST_MENU = Menu(
    menu_id="test_menu",
    title="Test Menu",
    description="A test menu for testing",
    menu_type=MenuType.MAIN,
    required_role=UserRole.FREE_USER,
    items=[
        MenuItem(
            id="test_item_1",
            text="Test Item 1",
            action_type=ActionType.CALLBACK,
            action_data="test_action_1",
            description="First test item"
        ),
        MenuItem(
            id="test_item_2",
            text="Test Item 2",
            action_type=ActionType.SUBMENU,
            action_data="test_submenu",
            description="Second test item"
        )
    ],
    header_text="Test Header",
    footer_text="Test Footer",
    max_columns=2
)


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    return AsyncMock()


@pytest.fixture
def telegram_menu_renderer(mock_bot):
    """Create a TelegramMenuRenderer instance for testing."""
    return TelegramMenuRenderer(bot=mock_bot)


def test_telegram_menu_renderer_initialization(telegram_menu_renderer):
    """Test TelegramMenuRenderer initialization."""
    assert telegram_menu_renderer.bot is not None


def test_telegram_menu_renderer_render_menu(telegram_menu_renderer):
    """Test TelegramMenuRenderer render_menu method."""
    # Render the menu
    keyboard = telegram_menu_renderer.render_menu(TEST_MENU)
    
    # Verify the keyboard structure
    assert keyboard is not None
    assert hasattr(keyboard, 'inline_keyboard')
    assert len(keyboard.inline_keyboard) > 0
    
    # Verify the first row has the expected buttons
    first_row = keyboard.inline_keyboard[0]
    assert len(first_row) == 2  # Two items in the first row
    
    # Verify button properties
    first_button = first_row[0]
    assert first_button.text == "Test Item 1"
    assert first_button.callback_data == "test_action_1"
    
    second_button = first_row[1]
    assert second_button.text == "Test Item 2"
    assert second_button.callback_data == "menu:test_submenu"


def test_telegram_menu_renderer_create_button_for_item(telegram_menu_renderer):
    """Test TelegramMenuRenderer _create_button_for_item method."""
    # Test callback action
    callback_item = MenuItem(
        id="callback_item",
        text="Callback Item",
        action_type=ActionType.CALLBACK,
        action_data="callback_data"
    )
    button = telegram_menu_renderer._create_button_for_item(callback_item)
    assert button is not None
    assert button.text == "Callback Item"
    assert button.callback_data == "callback_data"
    
    # Test submenu action
    submenu_item = MenuItem(
        id="submenu_item",
        text="Submenu Item",
        action_type=ActionType.SUBMENU,
        action_data="submenu_data"
    )
    button = telegram_menu_renderer._create_button_for_item(submenu_item)
    assert button is not None
    assert button.text == "Submenu Item"
    assert button.callback_data == "menu:submenu_data"
    
    # Test URL action
    url_item = MenuItem(
        id="url_item",
        text="URL Item",
        action_type=ActionType.URL,
        action_data="https://example.com"
    )
    button = telegram_menu_renderer._create_button_for_item(url_item)
    assert button is not None
    assert button.text == "URL Item"
    assert button.url == "https://example.com"
    
    # Test command action
    command_item = MenuItem(
        id="command_item",
        text="Command Item",
        action_type=ActionType.COMMAND,
        action_data="command_data"
    )
    button = telegram_menu_renderer._create_button_for_item(command_item)
    assert button is not None
    assert button.text == "Command Item"
    assert button.callback_data == "command:command_data"
    
    # Test narrative action
    narrative_item = MenuItem(
        id="narrative_item",
        text="Narrative Item",
        action_type=ActionType.NARRATIVE_ACTION,
        action_data="narrative_data"
    )
    button = telegram_menu_renderer._create_button_for_item(narrative_item)
    assert button is not None
    assert button.text == "Narrative Item"
    assert button.callback_data == "narrative:narrative_data"
    
    # Test admin action
    admin_item = MenuItem(
        id="admin_item",
        text="Admin Item",
        action_type=ActionType.ADMIN_ACTION,
        action_data="admin_data"
    )
    button = telegram_menu_renderer._create_button_for_item(admin_item)
    assert button is not None
    assert button.text == "Admin Item"
    assert button.callback_data == "admin:admin_data"


def test_telegram_menu_renderer_render_menu_response(telegram_menu_renderer):
    """Test TelegramMenuRenderer render_menu_response method."""
    # Render the menu response
    response_data = telegram_menu_renderer.render_menu_response(TEST_MENU)
    
    # Verify response structure
    assert "text" in response_data
    assert "reply_markup" in response_data
    assert len(response_data["text"]) > 0
    assert response_data["reply_markup"] is not None


def test_telegram_menu_renderer_render_menu_response_with_edit(telegram_menu_renderer):
    """Test TelegramMenuRenderer render_menu_response method with edit parameters."""
    # Render the menu response with edit parameters
    response_data = telegram_menu_renderer.render_menu_response(
        TEST_MENU,
        edit_message=True,
        chat_id=CHAT_ID,
        message_id=MESSAGE_ID
    )
    
    # Verify response structure
    assert "text" in response_data
    assert "reply_markup" in response_data
    assert "chat_id" in response_data
    assert "message_id" in response_data
    assert response_data["chat_id"] == CHAT_ID
    assert response_data["message_id"] == MESSAGE_ID


@pytest.mark.asyncio
async def test_telegram_menu_renderer_edit_existing_menu(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer edit_existing_menu method."""
    # Mock the bot's edit_message_text method
    mock_bot.edit_message_text = AsyncMock(return_value=True)
    
    # Edit the existing menu
    result = await telegram_menu_renderer.edit_existing_menu(CHAT_ID, MESSAGE_ID, TEST_MENU)
    
    # Verify the result
    assert result is True
    mock_bot.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_telegram_menu_renderer_edit_existing_menu_with_error(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer edit_existing_menu method with error."""
    # Mock the bot's edit_message_text method to raise an exception
    mock_bot.edit_message_text = AsyncMock(side_effect=Exception("Test error"))
    
    # Edit the existing menu
    result = await telegram_menu_renderer.edit_existing_menu(CHAT_ID, MESSAGE_ID, TEST_MENU)
    
    # Verify the result
    assert result is False


@pytest.mark.asyncio
async def test_telegram_menu_renderer_send_new_menu(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer send_new_menu method."""
    # Mock the bot's send_message method
    mock_message = MagicMock()
    mock_message.message_id = MESSAGE_ID
    mock_bot.send_message = AsyncMock(return_value=mock_message)
    
    # Send a new menu
    result = await telegram_menu_renderer.send_new_menu(CHAT_ID, TEST_MENU)
    
    # Verify the result
    assert result is not None
    assert result.message_id == MESSAGE_ID
    mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_telegram_menu_renderer_send_new_menu_with_error(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer send_new_menu method with error."""
    # Mock the bot's send_message method to raise an exception
    mock_bot.send_message = AsyncMock(side_effect=Exception("Test error"))
    
    # Send a new menu
    result = await telegram_menu_renderer.send_new_menu(CHAT_ID, TEST_MENU)
    
    # Verify the result
    assert result is None


@pytest.mark.asyncio
async def test_telegram_menu_renderer_edit_menu_text_only(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer edit_menu_text_only method."""
    # Mock the bot's edit_message_text method
    mock_bot.edit_message_text = AsyncMock(return_value=True)
    
    # Edit menu text only
    result = await telegram_menu_renderer.edit_menu_text_only(CHAT_ID, MESSAGE_ID, "New text")
    
    # Verify the result
    assert result is True
    mock_bot.edit_message_text.assert_called_once_with(
        chat_id=CHAT_ID,
        message_id=MESSAGE_ID,
        text="New text"
    )


@pytest.mark.asyncio
async def test_telegram_menu_renderer_edit_menu_keyboard_only(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer edit_menu_keyboard_only method."""
    # Create a mock keyboard
    mock_keyboard = MagicMock()
    
    # Mock the bot's edit_message_reply_markup method
    mock_bot.edit_message_reply_markup = AsyncMock(return_value=True)
    
    # Edit menu keyboard only
    result = await telegram_menu_renderer.edit_menu_keyboard_only(CHAT_ID, MESSAGE_ID, mock_keyboard)
    
    # Verify the result
    assert result is True
    mock_bot.edit_message_reply_markup.assert_called_once_with(
        chat_id=CHAT_ID,
        message_id=MESSAGE_ID,
        reply_markup=mock_keyboard
    )


@pytest.mark.asyncio
async def test_telegram_menu_renderer_update_menu_partially_with_menu(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer update_menu_partially method with new menu."""
    # Mock the bot's edit_message_text method
    mock_bot.edit_message_text = AsyncMock(return_value=True)
    
    # Update menu partially with new menu
    result = await telegram_menu_renderer.update_menu_partially(CHAT_ID, MESSAGE_ID, new_menu=TEST_MENU)
    
    # Verify the result
    assert result is True
    mock_bot.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_telegram_menu_renderer_update_menu_partially_with_text(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer update_menu_partially method with new text."""
    # Mock the bot's edit_message_text method
    mock_bot.edit_message_text = AsyncMock(return_value=True)
    
    # Update menu partially with new text
    result = await telegram_menu_renderer.update_menu_partially(CHAT_ID, MESSAGE_ID, new_text="New text")
    
    # Verify the result
    assert result is True
    mock_bot.edit_message_text.assert_called_once_with(
        chat_id=CHAT_ID,
        message_id=MESSAGE_ID,
        text="New text"
    )


@pytest.mark.asyncio
async def test_telegram_menu_renderer_update_menu_partially_with_keyboard(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer update_menu_partially method with new keyboard."""
    # Create a mock keyboard
    mock_keyboard = MagicMock()
    
    # Mock the bot's edit_message_reply_markup method
    mock_bot.edit_message_reply_markup = AsyncMock(return_value=True)
    
    # Update menu partially with new keyboard
    result = await telegram_menu_renderer.update_menu_partially(CHAT_ID, MESSAGE_ID, new_keyboard=mock_keyboard)
    
    # Verify the result
    assert result is True
    mock_bot.edit_message_reply_markup.assert_called_once_with(
        chat_id=CHAT_ID,
        message_id=MESSAGE_ID,
        reply_markup=mock_keyboard
    )


@pytest.mark.asyncio
async def test_telegram_menu_renderer_update_menu_partially_with_nothing(telegram_menu_renderer, mock_bot):
    """Test TelegramMenuRenderer update_menu_partially method with nothing to update."""
    # Update menu partially with no parameters
    result = await telegram_menu_renderer.update_menu_partially(CHAT_ID, MESSAGE_ID)
    
    # Verify the result
    assert result is False


if __name__ == "__main__":
    pytest.main([__file__])