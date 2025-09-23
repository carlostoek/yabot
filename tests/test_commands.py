"""
Tests for the command handlers.
"""

import pytest
from unittest.mock import Mock
from src.handlers.telegram_commands import CommandHandler
from src.core.models import CommandResponse


class TestCommandHandler:
    """Test cases for the CommandHandler class."""
    
    @pytest.fixture
    def command_handler(self):
        """Create a command handler instance for testing."""
        return CommandHandler()
    
    @pytest.fixture
    def mock_message(self):
        """Create a mock message for testing."""
        message = Mock()
        message.text = "Test message"
        return message
    
    def test_init(self, command_handler):
        """Test CommandHandler initialization."""
        assert command_handler is not None
        # The handle method should be abstract, so we can't call it directly
        # but we can test the other methods
    
    @pytest.mark.asyncio
    async def test_handle_start(self, command_handler, mock_message):
        """Test handling the /start command."""
        response = await command_handler.handle_start(mock_message)
        
        assert isinstance(response, CommandResponse)
        assert "Welcome to the Telegram Bot" in response.text
        assert "start" in response.text.lower()
        assert "menu" in response.text.lower()
        assert "help" in response.text.lower()
        assert response.parse_mode == "HTML"
    
    @pytest.mark.asyncio
    async def test_handle_menu(self, command_handler, mock_message):
        """Test handling the /menu command."""
        response = await command_handler.handle_menu(mock_message)
        
        assert isinstance(response, CommandResponse)
        assert "Main Menu" in response.text
        assert "Option 1" in response.text
        assert "Option 2" in response.text
        assert "Option 3" in response.text
        assert response.parse_mode == "HTML"
    
    @pytest.mark.asyncio
    async def test_handle_help(self, command_handler, mock_message):
        """Test handling the /help command."""
        response = await command_handler.handle_help(mock_message)
        
        assert isinstance(response, CommandResponse)
        assert "Help Information" in response.text
        assert "start" in response.text.lower()
        assert "menu" in response.text.lower()
        assert "help" in response.text.lower()
        assert response.parse_mode == "HTML"
    
    @pytest.mark.asyncio
    async def test_handle_unknown(self, command_handler, mock_message):
        """Test handling unknown commands."""
        response = await command_handler.handle_unknown(mock_message)
        
        assert isinstance(response, CommandResponse)
        assert "Unknown command" in response.text
        assert "start" in response.text.lower()
        assert "menu" in response.text.lower()
        assert "help" in response.text.lower()
        assert response.parse_mode == "HTML"
    
    @pytest.mark.asyncio
    async def test_create_response(self, command_handler):
        """Test creating a response."""
        text = "Test response text"
        response = await command_handler._create_response(text)
        
        assert isinstance(response, CommandResponse)
        assert response.text == text
        assert response.parse_mode == "HTML"
        assert response.reply_markup is None
        assert response.disable_notification is False
    
    @pytest.mark.asyncio
    async def test_create_response_with_custom_params(self, command_handler):
        """Test creating a response with custom parameters."""
        text = "Test response text"
        parse_mode = "Markdown"
        reply_markup = {"inline_keyboard": []}
        disable_notification = True
        
        response = await command_handler._create_response(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_notification=disable_notification
        )
        
        assert isinstance(response, CommandResponse)
        assert response.text == text
        assert response.parse_mode == parse_mode
        assert response.reply_markup == reply_markup
        assert response.disable_notification == disable_notification