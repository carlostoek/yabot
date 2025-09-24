"""
Test module for the configuration manager.

This module tests the ConfigManager class which handles bot configuration,
including requirements:
- 1.1: WHEN the bot is initialized THEN the system SHALL establish a connection with Telegram API using a valid bot token
- 1.2: WHEN the bot token is invalid THEN the system SHALL log an appropriate error and fail gracefully
- 1.4: WHEN the bot starts THEN the system SHALL validate all required configuration parameters before beginning operation
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from src.config.manager import ConfigManager, get_config_manager
from src.core.models import BotConfig, WebhookConfig, LoggingConfig


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_config_manager_initialization(self):
        """Test that ConfigManager initializes correctly with default values."""
        # Ensure we have a clean environment for this test
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'WEBHOOK_SECRET': 'test_secret'
        }):
            config_manager = ConfigManager()
            
            assert config_manager is not None
            assert config_manager.bot_config is not None
            assert config_manager.webhook_config is not None
            assert config_manager.logging_config is not None

    def test_get_bot_token(self):
        """Test that ConfigManager can retrieve the bot token."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI'
        }):
            config_manager = ConfigManager()
            bot_token = config_manager.get_bot_token()
            
            assert bot_token == 'test_token_123:ABCdefGHI'

    def test_get_bot_token_from_environment(self, test_bot_token):
        """Test that ConfigManager retrieves bot token from test environment."""
        config_manager = ConfigManager()
        bot_token = config_manager.get_bot_token()
        
        assert bot_token == test_bot_token

    def test_webhook_config_creation(self):
        """Test that webhook configuration is properly created from environment."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'WEBHOOK_SECRET': 'test_secret',
            'WEBHOOK_MAX_CONNECTIONS': '50',
            'WEBHOOK_ALLOWED_UPDATES': 'message,callback_query'
        }):
            config_manager = ConfigManager()
            webhook_config = config_manager.get_webhook_config()
            
            assert webhook_config is not None
            assert webhook_config.url == 'https://example.com/webhook'
            assert webhook_config.secret_token == 'test_secret'
            assert webhook_config.max_connections == 50
            assert 'message' in webhook_config.allowed_updates
            assert 'callback_query' in webhook_config.allowed_updates

    def test_logging_config_creation(self):
        """Test that logging configuration is properly created from environment."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI',
            'LOG_LEVEL': 'DEBUG',
            'LOG_FORMAT': 'json',
            'LOG_MAX_FILE_SIZE': '20971520',  # 20MB
            'LOG_BACKUP_COUNT': '10'
        }):
            config_manager = ConfigManager()
            logging_config = config_manager.get_logging_config()
            
            assert logging_config is not None
            assert logging_config.level == 'DEBUG'
            assert logging_config.format == 'json'
            assert logging_config.max_file_size == 20971520
            assert logging_config.backup_count == 10

    def test_validate_config_with_valid_settings(self):
        """Test that config validation passes with valid settings."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI'
        }):
            config_manager = ConfigManager()
            is_valid = config_manager.validate_config()
            
            assert is_valid is True

    def test_validate_config_fails_without_bot_token(self):
        """Test that config validation fails when bot token is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Add minimal required env vars except bot token
            os.environ['BOT_TOKEN'] = ''  # Empty token should cause validation to fail
            
            with pytest.raises(ValueError, match="Configuration validation failed: BOT_TOKEN is required"):
                ConfigManager()

    def test_get_mode_polling_by_default(self):
        """Test that the bot operates in polling mode by default."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI',
            'POLLING_ENABLED': 'true'
        }):
            config_manager = ConfigManager()
            mode = config_manager.get_mode()
            
            assert mode == 'polling'

    def test_get_mode_webhook_when_configured(self):
        """Test that the bot operates in webhook mode when configured."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'POLLING_ENABLED': 'false'
        }):
            config_manager = ConfigManager()
            mode = config_manager.get_mode()
            
            assert mode == 'webhook'

    def test_is_webhook_mode(self):
        """Test the is_webhook_mode method."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'POLLING_ENABLED': 'false'
        }):
            config_manager = ConfigManager()
            
            assert config_manager.is_webhook_mode() is True

    def test_is_webhook_mode_false_when_polling_enabled(self):
        """Test that is_webhook_mode returns False when polling is enabled."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'POLLING_ENABLED': 'true'
        }):
            config_manager = ConfigManager()
            
            assert config_manager.is_webhook_mode() is False


class TestConfigManagerSingleton:
    """Tests for the ConfigManager singleton pattern."""
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns the same instance each time."""
        config1 = get_config_manager()
        config2 = get_config_manager()
        
        assert config1 is config2

    def test_config_manager_properties(self):
        """Test that the singleton instance has the expected properties."""
        with patch.dict(os.environ, {
            'BOT_TOKEN': 'test_token_123:ABCdefGHI'
        }):
            config_manager = get_config_manager()
            
            assert hasattr(config_manager, 'get_bot_token')
            assert hasattr(config_manager, 'get_webhook_config')
            assert hasattr(config_manager, 'get_logging_config')
            assert hasattr(config_manager, 'validate_config')
            assert hasattr(config_manager, 'get_mode')


class TestBotConfigModel:
    """Tests for the BotConfig Pydantic model."""
    
    def test_bot_config_creation(self):
        """Test creating a BotConfig instance."""
        config = BotConfig(
            bot_token='test_token_123:ABCdefGHI',
            webhook_url='https://example.com/webhook',
            max_connections=50,
            request_timeout=45
        )
        
        assert config.bot_token == 'test_token_123:ABCdefGHI'
        assert config.webhook_url == 'https://example.com/webhook'
        assert config.max_connections == 50
        assert config.request_timeout == 45

    def test_bot_config_validation_fails_without_token(self):
        """Test that BotConfig validation fails without a token."""
        with pytest.raises(ValidationError):
            BotConfig(bot_token='')


class TestWebhookConfigModel:
    """Tests for the WebhookConfig Pydantic model."""
    
    def test_webhook_config_creation(self):
        """Test creating a WebhookConfig instance."""
        config = WebhookConfig(
            url='https://example.com/webhook',
            secret_token='test_secret',
            max_connections=60,
            allowed_updates=['message', 'callback_query']
        )
        
        assert config.url == 'https://example.com/webhook'
        assert config.secret_token == 'test_secret'
        assert config.max_connections == 60
        assert 'message' in config.allowed_updates
        assert 'callback_query' in config.allowed_updates


class TestLoggingConfigModel:
    """Tests for the LoggingConfig Pydantic model."""
    
    def test_logging_config_creation(self):
        """Test creating a LoggingConfig instance."""
        config = LoggingConfig(
            level='DEBUG',
            format='json',
            max_file_size=20971520,
            backup_count=10
        )
        
        assert config.level == 'DEBUG'
        assert config.format == 'json'
        assert config.max_file_size == 20971520
        assert config.backup_count == 10