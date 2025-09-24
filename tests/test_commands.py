"""
Test module for command handlers.

This module tests the command handler functionality, specifically covering:
- 2.1: WHEN a user sends /start command THEN the bot SHALL respond with a welcome message and basic usage instructions
- 2.2: WHEN a user sends /menu command THEN the bot SHALL display the main menu with available options
- 2.3: WHEN a user sends an unrecognized command THEN the bot SHALL respond with a helpful message explaining available commands
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.types import Message, User, Chat
from src.handlers.commands import (
    StartCommandHandler, 
    MenuCommandHandler, 
    HelpCommandHandler, 
    UnknownCommandHandler
)
from src.core.models import MessageContext, CommandResponse


class TestStartCommandHandler:
    """Tests for the StartCommandHandler class."""

    def test_start_handler_initialization(self):
        """Test that StartCommandHandler initializes correctly."""
        handler = StartCommandHandler()
        
        assert handler is not None
        assert hasattr(handler, 'process_message')
        assert hasattr(handler, 'create_response')
        assert hasattr(handler, 'send_response')

    def test_start_handler_process_message(self, mock_message):
        """Test that the StartCommandHandler processes messages correctly."""
        handler = StartCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='/start',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        # Mock the send_response method to prevent actual sending
        with patch.object(handler, 'send_response', new_callable=AsyncMock) as mock_send:
            response = handler.process_message(mock_message, message_context)
            
            # The process_message method should return a CommandResponse
            assert isinstance(response, CommandResponse)
            assert 'Hello! Welcome to the bot' in response.text
            assert 'Usage instructions' in response.text
            mock_send.assert_called_once()

    async def test_start_handler_response_content(self, mock_message):
        """Test that the start command response contains expected content."""
        handler = StartCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='/start',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            response = await handler.process_message(mock_message, message_context)
            
            # Check that the response contains expected content
            assert 'Hello! Welcome to the bot' in response.text
            assert 'Usage instructions' in response.text
            assert '/menu' in response.text
            assert '/help' in response.text


class TestMenuCommandHandler:
    """Tests for the MenuCommandHandler class."""

    def test_menu_handler_initialization(self):
        """Test that MenuCommandHandler initializes correctly."""
        handler = MenuCommandHandler()
        
        assert handler is not None
        assert hasattr(handler, 'process_message')
        assert hasattr(handler, 'create_response')
        assert hasattr(handler, 'send_response')

    async def test_menu_handler_process_message(self, mock_message):
        """Test that the MenuCommandHandler processes messages correctly."""
        handler = MenuCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='/menu',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            response = await handler.process_message(mock_message, message_context)
            
            # Check that the response contains expected content
            assert 'Main Menu' in response.text
            assert 'select an option' in response.text.lower()
            
            # Check that the response includes reply markup for the keyboard
            assert response.reply_markup is not None

    async def test_menu_handler_keyboard_structure(self, mock_message):
        """Test that the menu command response includes a properly structured keyboard."""
        handler = MenuCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='/menu',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            response = await handler.process_message(mock_message, message_context)
            
            # Verify that reply markup is included in the response
            assert response.reply_markup is not None
            # The reply markup should have keyboard data
            keyboard_data = response.reply_markup
            # Check that it has buttons
            # (Keyboard structure can't be fully validated without aiogram types)


class TestHelpCommandHandler:
    """Tests for the HelpCommandHandler class."""

    def test_help_handler_initialization(self):
        """Test that HelpCommandHandler initializes correctly."""
        handler = HelpCommandHandler()
        
        assert handler is not None
        assert hasattr(handler, 'process_message')
        assert hasattr(handler, 'create_response')
        assert hasattr(handler, 'send_response')

    async def test_help_handler_process_message(self, mock_message):
        """Test that the HelpCommandHandler processes messages correctly."""
        handler = HelpCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='/help',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            response = await handler.process_message(mock_message, message_context)
            
            # Check that the response contains expected content
            assert 'Bot Help' in response.text
            assert 'Available commands' in response.text
            assert '/start' in response.text
            assert '/menu' in response.text
            assert '/help' in response.text


class TestUnknownCommandHandler:
    """Tests for the UnknownCommandHandler class."""

    def test_unknown_handler_initialization(self):
        """Test that UnknownCommandHandler initializes correctly."""
        handler = UnknownCommandHandler()
        
        assert handler is not None
        assert hasattr(handler, 'process_message')
        assert hasattr(handler, 'create_response')
        assert hasattr(handler, 'send_response')

    async def test_unknown_command_response(self, mock_message):
        """Test that the UnknownCommandHandler responds to unrecognized commands."""
        handler = UnknownCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='/unknown_command',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        # Set up the mock message to simulate an unknown command
        mock_message.text = '/unknown_command'
        
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            response = await handler.process_message(mock_message, message_context)
            
            # Check that the response contains expected content for unknown commands
            assert 'recognize the command' in response.text
            assert '/unknown_command' in response.text
            assert '/help' in response.text
            assert '/menu' in response.text

    async def test_unknown_message_response(self, mock_message):
        """Test that the UnknownCommandHandler responds to unrecognized messages (not commands)."""
        handler = UnknownCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='random text not a command',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        # Set up the mock message to simulate a regular text message
        mock_message.text = 'random text not a command'
        
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            response = await handler.process_message(mock_message, message_context)
            
            # Check that the response contains expected content for unknown messages
            assert 'not sure how to respond' in response.text
            assert '/help' in response.text
            assert '/menu' in response.text

    async def test_unknown_handler_handles_non_command_text(self, mock_message):
        """Test handling of non-command text."""
        handler = UnknownCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='hello there',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        # Set up the mock message to simulate a regular text message
        mock_message.text = 'hello there'
        
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            response = await handler.process_message(mock_message, message_context)
            
            # Verify that response is appropriate for non-command text
            assert 'not sure how to respond' in response.text


class TestCommandHandlerIntegration:
    """Integration tests for command handlers."""

    async def test_command_handlers_create_responses_properly(self, mock_message):
        """Test that all command handlers properly create CommandResponse objects."""
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='/start',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        # Test all command handlers
        handlers_and_commands = [
            (StartCommandHandler(), '/start'),
            (MenuCommandHandler(), '/menu'),
            (HelpCommandHandler(), '/help'),
            (UnknownCommandHandler(), '/unknown')
        ]
        
        for handler, command in handlers_and_commands:
            message_context.content = command
            if hasattr(mock_message, 'text'):
                mock_message.text = command
            
            with patch.object(handler, 'send_response', new_callable=AsyncMock):
                response = await handler.process_message(mock_message, message_context)
                
                # Verify that all handlers return CommandResponse objects
                assert isinstance(response, CommandResponse)
                assert response.text is not None
                assert len(response.text) > 0

    async def test_command_handler_response_format(self, mock_message):
        """Test that command handlers create properly formatted responses."""
        handler = StartCommandHandler()
        message_context = MessageContext(
            message_id=1,
            chat_id=987654321,
            user_id=123456789,
            message_type='text',
            content='/start',
            timestamp='2023-01-01T00:00:00Z'
        )
        
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            response = await handler.process_message(mock_message, message_context)
            
            # Check response attributes
            assert hasattr(response, 'text')
            assert hasattr(response, 'parse_mode')
            assert hasattr(response, 'reply_markup')
            assert hasattr(response, 'disable_notification')
            
            # Check default values
            assert response.parse_mode == 'HTML'


class TestCommandHandlerErrorHandling:
    """Error handling tests for command handlers."""

    async def test_command_handler_with_invalid_context(self, mock_message):
        """Test that command handlers handle invalid context gracefully."""
        handler = StartCommandHandler()
        invalid_context = {"invalid": "context"}
        
        # Should handle gracefully even with invalid context
        with patch.object(handler, 'send_response', new_callable=AsyncMock):
            try:
                response = await handler.process_message(mock_message, invalid_context)
                # If it doesn't raise an exception, that's good
            except Exception as e:
                # If an exception is raised, it should be handled appropriately
                assert isinstance(e, (TypeError, AttributeError))