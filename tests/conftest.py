"""
Test configuration for the core bot framework.

This module contains shared fixtures and configuration for all tests.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Generator

# Set default test environment variables
os.environ.setdefault('BOT_TOKEN', 'test_token_for_testing')
os.environ.setdefault('WEBHOOK_URL', 'https://test.example.com/webhook')
os.environ.setdefault('WEBHOOK_SECRET', 'test_webhook_secret')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')


@pytest.fixture
def mock_aiogram_bot():
    """Mock aiogram Bot instance for testing."""
    with patch('aiogram.Bot') as mock_bot:
        mock_bot_instance = MagicMock()
        mock_bot.return_value = mock_bot_instance
        yield mock_bot_instance


@pytest.fixture
def mock_aiogram_dispatcher():
    """Mock aiogram Dispatcher instance for testing."""
    with patch('aiogram.Dispatcher') as mock_dispatcher:
        mock_dispatcher_instance = MagicMock()
        mock_dispatcher.return_value = mock_dispatcher_instance
        yield mock_dispatcher_instance


@pytest.fixture
def mock_update():
    """Mock aiogram Update object for testing."""
    from aiogram.types import Update, Message, User, Chat
    
    mock_update = MagicMock(spec=Update)
    mock_message = MagicMock(spec=Message)
    mock_user = MagicMock(spec=User)
    mock_chat = MagicMock(spec=Chat)
    
    # Set up basic user and chat attributes
    mock_user.id = 123456789
    mock_user.username = 'test_user'
    mock_user.first_name = 'Test'
    mock_user.last_name = 'User'
    
    mock_chat.id = 987654321
    mock_chat.type = 'private'
    
    # Link message to user and chat
    mock_message.from_user = mock_user
    mock_message.chat = mock_chat
    mock_message.text = '/start'
    mock_message.message_id = 1
    mock_message.date = 1234567890
    
    # Link update to message
    mock_update.message = mock_message
    mock_update.callback_query = None
    mock_update.inline_query = None
    mock_update.update_id = 123456
    
    return mock_update


@pytest.fixture
def mock_message():
    """Mock aiogram Message object for testing."""
    from aiogram.types import Message, User, Chat
    
    mock_message = MagicMock(spec=Message)
    mock_user = MagicMock(spec=User)
    mock_chat = MagicMock(spec=Chat)
    
    # Set up basic attributes
    mock_user.id = 123456789
    mock_user.username = 'test_user'
    mock_user.first_name = 'Test'
    mock_user.last_name = 'Test'
    
    mock_chat.id = 987654321
    mock_chat.type = 'private'
    
    # Link message to user and chat
    mock_message.from_user = mock_user
    mock_message.chat = mock_chat
    mock_message.text = 'test message'
    mock_message.message_id = 1
    mock_message.date = 1234567890
    
    return mock_message


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager for testing."""
    from src.config.manager import ConfigManager
    
    with patch.object(ConfigManager, '__new__') as mock_new:
        mock_config = MagicMock(spec=ConfigManager)
        mock_new.return_value = mock_config
        
        # Set default return values for common config methods
        mock_config.get_bot_token.return_value = 'test_token_for_testing'
        mock_config.get_webhook_url.return_value = 'https://test.example.com/webhook'
        mock_config.get_webhook_secret.return_value = 'test_webhook_secret'
        mock_config.get_mode.return_value = 'polling'  # Default to polling in tests
        mock_config.validate_config.return_value = True
        
        yield mock_config


@pytest.fixture
def test_bot_token():
    """Provide a test bot token for testing."""
    return os.environ.get('BOT_TOKEN', 'test_token_for_testing')