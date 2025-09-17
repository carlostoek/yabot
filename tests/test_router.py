"""
Tests for the router.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.core.router import Router


class TestRouter:
    """Test cases for the Router class."""
    
    @pytest.fixture
    def router(self):
        """Create a router instance for testing."""
        return Router()
    
    @pytest.fixture
    def mock_handler(self):
        """Create a mock handler for testing."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock update for testing."""
        update = Mock()
        update.message = Mock()
        update.message.text = "/start"
        return update
    
    def test_init(self, router):
        """Test Router initialization."""
        assert router is not None
        assert router._command_handlers == {}
        assert router._message_handlers == []
        assert router._default_handler is None
    
    def test_register_command_handler(self, router, mock_handler):
        """Test registering a command handler."""
        router.register_command_handler("start", mock_handler)
        
        assert "start" in router._command_handlers
        assert router._command_handlers["start"] == mock_handler
    
    def test_register_command_handler_invalid_handler(self, router):
        """Test registering an invalid command handler."""
        with pytest.raises(TypeError, match="Handler must be callable"):
            router.register_command_handler("start", "not_a_function")
    
    def test_register_message_handler(self, router, mock_handler):
        """Test registering a message handler."""
        mock_filter = Mock()
        router.register_message_handler(mock_filter, mock_handler)
        
        assert len(router._message_handlers) == 1
        assert router._message_handlers[0] == (mock_filter, mock_handler)
    
    def test_register_message_handler_invalid_handler(self, router):
        """Test registering an invalid message handler."""
        mock_filter = Mock()
        with pytest.raises(TypeError, match="Handler must be callable"):
            router.register_message_handler(mock_filter, "not_a_function")
    
    def test_set_default_handler(self, router, mock_handler):
        """Test setting a default handler."""
        router.set_default_handler(mock_handler)
        
        assert router._default_handler == mock_handler
    
    def test_set_default_handler_invalid_handler(self, router):
        """Test setting an invalid default handler."""
        with pytest.raises(TypeError, match="Handler must be callable"):
            router.set_default_handler("not_a_function")
    
    @pytest.mark.asyncio
    async def test_route_update_command(self, router, mock_handler, mock_update):
        """Test routing an update with a command."""
        # Register the handler
        router.register_command_handler("start", mock_handler)
        
        # Route the update
        result = await router.route_update(mock_update)
        
        # Verify the handler was called
        mock_handler.assert_called_once_with(mock_update)
        assert result == mock_handler.return_value
    
    @pytest.mark.asyncio
    async def test_route_update_command_no_handler(self, router, mock_update):
        """Test routing an update with a command but no handler."""
        # Route the update (no handler registered)
        result = await router.route_update(mock_update)
        
        # Should return None since no handler is registered
        assert result is None
    
    @pytest.mark.asyncio
    async def test_route_update_message(self, router, mock_handler):
        """Test routing an update with a message."""
        # Create a message update (not a command)
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "Hello, bot!"
        
        # Register a message handler
        mock_filter = Mock()
        router.register_message_handler(mock_filter, mock_handler)
        
        # Route the update
        result = await router.route_update(mock_update)
        
        # Verify the handler was called
        mock_handler.assert_called_once_with(mock_update)
        assert result == mock_handler.return_value
    
    @pytest.mark.asyncio
    async def test_route_update_default_handler(self, router, mock_handler):
        """Test routing an update with a default handler."""
        # Set up a default handler
        router.set_default_handler(mock_handler)
        
        # Create an update that doesn't match any handlers
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "Some random message"
        
        # Route the update
        result = await router.route_update(mock_update)
        
        # Verify the default handler was called
        mock_handler.assert_called_once_with(mock_update)
        assert result == mock_handler.return_value
    
    @pytest.mark.asyncio
    async def test_route_update_no_handlers(self, router):
        """Test routing an update with no handlers at all."""
        # Create an update
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "Some random message"
        
        # Route the update
        result = await router.route_update(mock_update)
        
        # Should return None since no handlers are registered
        assert result is None
    
    def test_extract_command(self, router):
        """Test extracting command from an update."""
        # Test with a command message
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "/start"
        
        command = router._extract_command(mock_update)
        assert command == "start"
        
        # Test with a command with arguments
        mock_update.message.text = "/start arg1 arg2"
        command = router._extract_command(mock_update)
        assert command == "start"
        
        # Test with a non-command message
        mock_update.message.text = "Hello, bot!"
        command = router._extract_command(mock_update)
        assert command is None
        
        # Test with no message
        mock_update = Mock()
        mock_update.message = None
        command = router._extract_command(mock_update)
        assert command is None
    
    @pytest.mark.asyncio
    async def test_matches_filter(self, router):
        """Test matching filters."""
        mock_update = Mock()
        mock_filter = Mock()
        
        # In our implementation, _matches_filter always returns True
        result = await router._matches_filter(mock_update, mock_filter)
        assert result is True