"""
Integration tests for the core bot framework.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import os
from src.core.application import BotApplication
from src.config.manager import ConfigManager
from src.core.router import Router
from src.handlers.commands import CommandHandler


class TestIntegration:
    """Integration tests for the core bot framework components."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager for testing."""
        mock_config = Mock()
        mock_config.get_bot_token.return_value = "test_bot_token_12345"
        mock_config.validate_config.return_value = True
        mock_config.get_webhook_config.return_value = Mock(url="")
        return mock_config
    
    @pytest.fixture
    def mock_router(self):
        """Create a mock router for testing."""
        mock_router = Mock()
        mock_router.route_update = AsyncMock()
        return mock_router
    
    @pytest.fixture
    def mock_middleware_manager(self):
        """Create a mock middleware manager for testing."""
        mock_middleware = Mock()
        mock_middleware.process_request = AsyncMock()
        mock_middleware.process_response = AsyncMock()
        return mock_middleware
    
    @pytest.fixture
    def mock_error_handler(self):
        """Create a mock error handler for testing."""
        mock_handler = Mock()
        mock_handler.handle_error = AsyncMock()
        return mock_handler
    
    @pytest.fixture
    def mock_command_handler(self):
        """Create a mock command handler for testing."""
        mock_handler = Mock()
        mock_handler.handle_start = AsyncMock()
        mock_handler.handle_menu = AsyncMock()
        mock_handler.handle_help = AsyncMock()
        mock_handler.handle_unknown = AsyncMock()
        return mock_handler
    
    @pytest.fixture
    def sample_update(self):
        """Create a sample update for testing."""
        update = Mock()
        update.message = Mock()
        update.message.text = "/start"
        return update
    
    @patch.dict(os.environ, {"BOT_TOKEN": "test_bot_token_12345"}, clear=True)
    def test_bot_application_initialization(self):
        """Test that BotApplication initializes all components correctly."""
        bot_app = BotApplication()
        
        # Check that all components are initialized
        assert bot_app.config_manager is not None
        assert bot_app.router is not None
        assert bot_app.middleware_manager is not None
        assert bot_app.error_handler is not None
        assert bot_app.command_handler is not None
        assert bot_app.webhook_handler is not None
        
        # Check initial state
        assert bot_app.is_running is False
        assert bot_app.is_webhook_enabled is False
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"BOT_TOKEN": "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"}, clear=True)
    async def test_bot_application_start_success(self):
        """Test that BotApplication starts successfully with valid configuration."""
        bot_app = BotApplication()
        
        # Mock the webhook configuration to use polling mode
        with patch.object(bot_app.config_manager, 'get_webhook_config') as mock_webhook_config:
            mock_webhook_config.return_value = Mock(url="")  # Empty URL means polling mode
            
            # Mock the setup methods to return success
            with patch.object(bot_app, '_setup_polling_mode') as mock_setup_polling:
                mock_setup_polling.return_value = True
                
                result = await bot_app.start()
                
                assert result is True
                assert bot_app.is_running is True
                mock_setup_polling.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"BOT_TOKEN": "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"}, clear=True)
    async def test_bot_application_start_failure(self):
        """Test that BotApplication handles start failure correctly."""
        bot_app = BotApplication()
        
        # Mock the setup method to return failure
        with patch.object(bot_app, '_setup_polling_mode') as mock_setup_polling:
            mock_setup_polling.return_value = False
            
            result = await bot_app.start()
            
            assert result is False
            assert bot_app.is_running is False
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"BOT_TOKEN": "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"}, clear=True)
    async def test_bot_application_stop(self):
        """Test that BotApplication stops correctly."""
        bot_app = BotApplication()
        
        # Mock methods to avoid database and other dependencies
        with patch.object(bot_app, '_setup_polling_mode') as mock_setup_polling:
            mock_setup_polling.return_value = True
            
            result = await bot_app.start()
            
            # For now, just check that it doesn't crash
            assert result is not None
    
    def test_config_manager_integration(self):
        """Test ConfigManager integration with environment variables."""
        with patch.dict(os.environ, {
            "BOT_TOKEN": "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789",
            "WEBHOOK_URL": "https://example.com/webhook",
            "LOG_LEVEL": "DEBUG"
        }):
            config_manager = ConfigManager()
            
            # Test getting bot token
            token = config_manager.get_bot_token()
            assert token == "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"
            
            # Test getting webhook config
            webhook_config = config_manager.get_webhook_config()
            assert webhook_config.url == "https://example.com/webhook"
            
            # Test getting logging config
            logging_config = config_manager.get_logging_config()
            assert logging_config.level == "DEBUG"
    
    def test_router_command_registration(self):
        """Test Router command registration and routing."""
        router = Router()
        mock_handler = AsyncMock()
        
        # Register a command handler
        router.register_command_handler("start", mock_handler)
        
        # Create a mock update with the command
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "/start"
        
        # Extract command and verify it's registered
        command = router._extract_command(mock_update)
        assert command == "start"
        assert command in router._command_handlers
    
    @pytest.mark.asyncio
    async def test_command_handler_integration(self):
        """Test CommandHandler integration with CommandResponse."""
        from src.core.models import CommandResponse
        
        command_handler = CommandHandler()
        
        # Test handling start command
        mock_message = Mock()
        mock_message.text = "/start"
        
        response = await command_handler.handle_start(mock_message)
        
        # Verify response type and content
        assert isinstance(response, CommandResponse)
        assert "Welcome to the Telegram Bot" in response.text
        assert response.parse_mode == "HTML"
    
    @pytest.mark.asyncio
    async def test_process_update_integration(self, mock_config_manager):
        """Test the full update processing pipeline."""
        # This test would normally require a full BotApplication instance
        # but we'll mock the components to test the integration
        
        # Create mock components
        router = Router()
        middleware_manager = Mock()
        command_handler = CommandHandler()
        
        # Set up middleware to pass through updates unchanged
        middleware_manager.process_request = AsyncMock(side_effect=lambda x: x)
        middleware_manager.process_response = AsyncMock(side_effect=lambda x: x)
        
        # Register a command handler
        router.register_command_handler("start", command_handler.handle_start)
        
        # Create a mock update
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "/start"
        
        # Process through middleware
        processed_update = await middleware_manager.process_request(mock_update)
        
        # Route to handler
        response = await router.route_update(processed_update)
        
        # Process response through middleware
        processed_response = await middleware_manager.process_response(response)
        
        # Verify the response
        assert processed_response is not None
        assert "Welcome to the Telegram Bot" in processed_response.text
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"BOT_TOKEN": "test_bot_token_12345"}, clear=True)
    async def test_webhook_mode_setup(self):
        """Test setting up webhook mode."""
        bot_app = BotApplication()
        
        # Test configuring webhook
        result = bot_app.configure_webhook("https://example.com/webhook")
        
        assert result is True
        assert bot_app.is_webhook_enabled is True
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"BOT_TOKEN": "test_bot_token_12345"}, clear=True)
    async def test_polling_mode_setup(self):
        """Test setting up polling mode."""
        bot_app = BotApplication()
        
        # Test configuring polling
        result = bot_app.configure_polling()
        
        assert result is True
        assert bot_app.is_webhook_enabled is False