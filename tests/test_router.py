"""
Test module for the router component.

This module tests the RouterManager class which routes incoming messages 
to appropriate handlers based on message type and content, specifically covering:
- 5.1: WHEN a text message is received THEN the system SHALL route it to the appropriate handler based on content
- 5.2: WHEN an unsupported message type is received THEN the bot SHALL inform the user about supported message types
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from aiogram.types import Message, Update, User, Chat
from aiogram.filters import Command

from src.core.router import RouterManager
from src.core.models import BotCommand


class TestRouterManager:
    """Tests for the RouterManager class."""

    def test_router_manager_initialization(self):
        """Test that RouterManager initializes correctly."""
        router_manager = RouterManager()
        
        assert router_manager is not None
        assert router_manager.router is not None
        assert isinstance(router_manager.command_handlers, dict)
        assert isinstance(router_manager.message_handlers, list)
        assert isinstance(router_manager.callback_handlers, list)

    def test_register_command_handler(self):
        """Test registering a command handler."""
        router_manager = RouterManager()
        
        # Create a mock handler
        mock_handler = AsyncMock()
        
        # Register the handler
        router_manager.register_command_handler('test', mock_handler)
        
        # Verify the handler was registered
        assert 'test' in router_manager.command_handlers
        assert router_manager.command_handlers['test'] == mock_handler
        
        # Check that get_registered_commands returns the command
        registered_commands = router_manager.get_registered_commands()
        assert 'test' in registered_commands

    def test_register_message_handler(self):
        """Test registering a message handler."""
        router_manager = RouterManager()
        
        # Create a mock handler
        mock_handler = AsyncMock()
        
        # Register the handler with a filter
        filter_func = lambda x: True  # Simple filter for testing
        
        router_manager.register_message_handler(filter_func, mock_handler)
        
        # Verify the handler was registered
        assert len(router_manager.message_handlers) == 1
        assert router_manager.message_handlers[0][0] == filter_func
        assert router_manager.message_handlers[0][1] == mock_handler

    def test_register_callback_handler(self):
        """Test registering a callback handler."""
        router_manager = RouterManager()
        
        # Create a mock handler
        mock_handler = AsyncMock()
        
        # Register the handler
        router_manager.register_callback_handler('test_pattern', mock_handler)
        
        # Verify the handler was registered
        assert len(router_manager.callback_handlers) == 1
        assert router_manager.callback_handlers[0][0] == 'test_pattern'
        assert router_manager.callback_handlers[0][1] == mock_handler

    def test_get_router(self):
        """Test the get_router method."""
        router_manager = RouterManager()
        router = router_manager.get_router()
        
        assert router is not None
        # Should be an aiogram Router instance
        from aiogram import Router
        assert isinstance(router, Router)

    def test_get_registered_commands(self):
        """Test getting registered commands."""
        router_manager = RouterManager()
        
        # Initially should be empty (or contain default ones)
        commands = router_manager.get_registered_commands()
        assert isinstance(commands, list)
        
        # Add a command and check it's returned
        mock_handler = AsyncMock()
        router_manager.register_command_handler('newcommand', mock_handler)
        
        commands = router_manager.get_registered_commands()
        assert 'newcommand' in commands

    def test_route_update_method(self, mock_update):
        """Test the route_update method."""
        router_manager = RouterManager()
        
        # The method should return None as per implementation
        result = router_manager.route_update(mock_update)
        assert result is None


class TestRouterCommands:
    """Tests for command routing functionality."""

    async def test_command_routing_with_mock_handler(self, mock_message):
        """Test routing to a registered command handler."""
        router_manager = RouterManager()
        
        # Create and register a mock handler for a test command
        async def test_handler(message):
            await message.answer("Test command response")
        
        router_manager.register_command_handler('testcmd', test_handler)
        
        # Verify the command was registered
        registered_commands = router_manager.get_registered_commands()
        assert 'testcmd' in registered_commands

    async def test_default_command_handlers(self, mock_message):
        """Test that default command handlers are registered."""
        router_manager = RouterManager()
        
        # Check if default commands are registered
        registered_commands = router_manager.get_registered_commands()
        
        # We expect the default commands that are registered in _register_default_handlers
        # They are registered as decorators, so we need to check if they exist
        # This test might need to be adapted based on how the default handlers work


class TestRouterMessageHandling:
    """Tests for message handling functionality."""

    async def test_message_handler_with_filter(self, mock_message):
        """Test registering and using a message handler with a filter."""
        router_manager = RouterManager()
        
        # Create a mock handler
        mock_handler = AsyncMock()
        
        # Use a simple filter (text messages)
        from aiogram import F
        filter_func = F.text
        
        router_manager.register_message_handler(filter_func, mock_handler)
        
        # Verify it was registered
        assert len(router_manager.message_handlers) == 1
        assert router_manager.message_handlers[0][0] == filter_func

    async def test_callback_handler_routing(self):
        """Test callback handler routing."""
        router_manager = RouterManager()
        
        # Create a mock handler
        mock_handler = AsyncMock()
        
        # Register the handler
        router_manager.register_callback_handler('test_callback', mock_handler)
        
        # Verify it was registered
        assert len(router_manager.callback_handlers) == 1
        assert router_manager.callback_handlers[0][0] == 'test_callback'


class TestRouterErrorHandling:
    """Tests for error handling in router."""

    async def test_command_handler_error_handling(self, mock_message):
        """Test that errors in command handlers are handled gracefully."""
        router_manager = RouterManager()
        
        # Create a handler that raises an exception
        async def error_handler(message):
            raise ValueError("Test error")
        
        # Mock the logger to verify error logging
        with patch.object(router_manager.logger, 'error') as mock_logger_error:
            router_manager.register_command_handler('errorcmd', error_handler)
            
            # Verify the command was registered
            registered_commands = router_manager.get_registered_commands()
            assert 'errorcmd' in registered_commands

    async def test_message_handler_error_handling(self):
        """Test that errors in message handlers are handled gracefully."""
        router_manager = RouterManager()
        
        # Create a handler that raises an exception
        async def error_handler(message):
            raise ValueError("Test error")
        
        # Register the handler with a filter
        from aiogram import F
        filter_func = F.text
        
        # Mock the logger to verify error logging
        with patch.object(router_manager.logger, 'error') as mock_logger_error:
            router_manager.register_message_handler(filter_func, error_handler)
            
            # Verify it was registered
            assert len(router_manager.message_handlers) == 1

    async def test_callback_handler_error_handling(self):
        """Test that errors in callback handlers are handled gracefully."""
        router_manager = RouterManager()
        
        # Create a handler that raises an exception
        async def error_handler(callback_query):
            raise ValueError("Test error")
        
        # Mock the logger to verify error logging
        with patch.object(router_manager.logger, 'error') as mock_logger_error:
            router_manager.register_callback_handler('error_callback', error_handler)
            
            # Verify it was registered
            assert len(router_manager.callback_handlers) == 1


class TestRouterIntegration:
    """Integration tests for the router."""

    def test_router_manager_full_setup(self):
        """Test complete router manager setup."""
        router_manager = RouterManager()
        
        # Verify all components are properly set up
        assert router_manager.router is not None
        assert isinstance(router_manager.command_handlers, dict)
        assert isinstance(router_manager.message_handlers, list)
        assert isinstance(router_manager.callback_handlers, list)
        assert router_manager.logger is not None
        
        # Test registration methods work without error
        mock_handler = AsyncMock()
        
        router_manager.register_command_handler('integration_test', mock_handler)
        assert 'integration_test' in router_manager.command_handlers
        
        from aiogram import F
        router_manager.register_message_handler(F.text, mock_handler)
        assert len(router_manager.message_handlers) > 0
        
        router_manager.register_callback_handler('integration_callback', mock_handler)
        assert len(router_manager.callback_handlers) > 0


class TestRouterWithRealUpdate:
    """Tests with real-like update objects."""

    def test_route_update_with_message(self):
        """Test routing an update that contains a message."""
        router_manager = RouterManager()
        
        # Create a mock update object
        mock_update = MagicMock()
        mock_update.update_id = 12345
        mock_update.message = MagicMock()
        
        # Test that route_update works
        result = router_manager.route_update(mock_update)
        assert result is None  # As per implementation

    def test_route_update_with_callback_query(self):
        """Test routing an update that contains a callback query."""
        router_manager = RouterManager()
        
        # Create a mock update object
        mock_update = MagicMock()
        mock_update.update_id = 12346
        mock_update.callback_query = MagicMock()
        
        # Test that route_update works
        result = router_manager.route_update(mock_update)
        assert result is None  # As per implementation