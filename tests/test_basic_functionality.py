"""
Basic functionality test for the core bot framework.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

# Set a test token to bypass configuration validation
os.environ['BOT_TOKEN'] = 'test_token'

from src.core.application import BotApplication
from src.config.manager import get_config_manager
from src.handlers.base import BaseHandler
from src.utils.logger import get_logger


class TestBotApplication:
    """Tests for the BotApplication class."""
    
    def test_bot_application_initialization(self):
        """Test that BotApplication initializes correctly."""
        app = BotApplication()
        assert app.config_manager is not None
        assert app.bot is None  # Bot is not initialized until initialize() is called
        assert app.dispatcher is None  # Dispatcher is not initialized until initialize() is called
        assert app.is_running is False
    
    def test_bot_application_config_access(self):
        """Test that the application can access configuration."""
        app = BotApplication()
        config_manager = get_config_manager()
        
        # Verify that we can get the bot token
        bot_token = config_manager.get_bot_token()
        assert bot_token == 'test_token'
    
    def test_bot_application_modes(self):
        """Test that the application can determine its operation mode."""
        app = BotApplication()
        
        # With default test configuration, should be in polling mode
        mode = app.config_manager.get_mode()
        assert mode in ['polling', 'webhook']  # Should be one of these modes


from src.handlers.commands import StartCommandHandler

class TestCommandHandler:
    """Tests for concrete handler implementations."""
    
    def test_command_handler_initialization(self):
        """Test that a concrete handler (like StartCommandHandler) initializes with required components."""
        handler = StartCommandHandler()
        
        # Check that logger is available
        assert handler.logger is not None
        
        # Check that error handler is available
        assert handler.error_handler is not None


def test_logger_functionality():
    """Test that logging functionality works."""
    logger = get_logger("test_logger")
    assert logger is not None


if __name__ == "__main__":
    pytest.main([__file__])