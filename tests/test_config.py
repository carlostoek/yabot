"""
Tests for the configuration manager.
"""

import os
import pytest
from unittest.mock import patch
from src.config.manager import ConfigManager
from src.core.models import WebhookConfig, LoggingConfig, DatabaseConfig, RedisConfig


class TestConfigManager:
    """Test cases for the ConfigManager class."""
    
    def test_init(self):
        """Test ConfigManager initialization."""
        config_manager = ConfigManager()
        assert config_manager is not None
        assert config_manager._bot_config is None
        assert config_manager._webhook_config is None
        assert config_manager._logging_config is None
        assert config_manager._database_config is None
        assert config_manager._redis_config is None
    
    @patch.dict(os.environ, {"BOT_TOKEN": "test_token_12345"})
    def test_get_bot_token(self):
        """Test getting bot token from environment variables."""
        config_manager = ConfigManager()
        token = config_manager.get_bot_token()
        assert token == "test_token_12345"
    
    @patch.dict(os.environ, {"BOT_TOKEN": ""})
    def test_get_bot_token_missing(self):
        """Test getting bot token when it's missing."""
        config_manager = ConfigManager()
        with pytest.raises(ValueError, match="BOT_TOKEN environment variable is required but not set"):
            config_manager.get_bot_token()
    
    @patch.dict(os.environ, {
        "WEBHOOK_URL": "https://example.com/webhook",
        "WEBHOOK_SECRET": "test_secret",
        "WEBHOOK_MAX_CONNECTIONS": "50"
    })
    def test_get_webhook_config(self):
        """Test getting webhook configuration."""
        config_manager = ConfigManager()
        webhook_config = config_manager.get_webhook_config()
        
        assert isinstance(webhook_config, WebhookConfig)
        assert webhook_config.url == "https://example.com/webhook"
        assert webhook_config.secret_token == "test_secret"
        assert webhook_config.max_connections == 50
    
    @patch.dict(os.environ, {
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "text",
        "LOG_MAX_FILE_SIZE": "5242880",
        "LOG_BACKUP_COUNT": "3"
    })
    def test_get_logging_config(self):
        """Test getting logging configuration."""
        config_manager = ConfigManager()
        logging_config = config_manager.get_logging_config()
        
        assert isinstance(logging_config, LoggingConfig)
        assert logging_config.level == "DEBUG"
        assert logging_config.format == "text"
        assert logging_config.max_file_size == 5242880
        assert logging_config.backup_count == 3
    
    @patch.dict(os.environ, {"BOT_TOKEN": "valid_bot_token_12345"})
    def test_validate_config_valid_token(self):
        """Test validating configuration with valid bot token."""
        config_manager = ConfigManager()
        result = config_manager.validate_config()
        assert result is True
    
    @patch.dict(os.environ, {"BOT_TOKEN": "short"})
    def test_validate_config_invalid_token(self):
        """Test validating configuration with invalid bot token."""
        config_manager = ConfigManager()
        with pytest.raises(ValueError, match="Invalid bot token: Token is required and must be at least 10 characters"):
            config_manager.validate_config()
    
    @patch.dict(os.environ, {"BOT_TOKEN": "valid_bot_token_12345"}, clear=True)
    def test_validate_config_missing_token(self):
        """Test validating configuration with missing bot token."""
        config_manager = ConfigManager()
        # This should work since we're setting a valid token
        result = config_manager.validate_config()
        assert result is True
    
    @patch.dict(os.environ, {
        "BOT_TOKEN": "valid_bot_token_12345",
        "WEBHOOK_URL": "https://example.com/webhook"
    })
    def test_validate_config_valid_webhook(self):
        """Test validating configuration with valid webhook URL."""
        config_manager = ConfigManager()
        result = config_manager.validate_config()
        assert result is True
    
    @patch.dict(os.environ, {
        "BOT_TOKEN": "valid_bot_token_12345",
        "WEBHOOK_URL": "http://example.com/webhook"
    })
    def test_validate_config_invalid_webhook_url(self):
        """Test validating configuration with invalid webhook URL (not HTTPS)."""
        config_manager = ConfigManager()
        with pytest.raises(ValueError, match="Invalid webhook URL: Must use HTTPS protocol"):
            config_manager.validate_config()
    
    def test_config_caching(self):
        """Test that configuration objects are cached."""
        config_manager = ConfigManager()
        
        # Get webhook config twice
        webhook_config1 = config_manager.get_webhook_config()
        webhook_config2 = config_manager.get_webhook_config()
        
        # Should be the same object
        assert webhook_config1 is webhook_config2
        
        # Get logging config twice
        logging_config1 = config_manager.get_logging_config()
        logging_config2 = config_manager.get_logging_config()
        
        # Should be the same object
        assert logging_config1 is logging_config2
        
        # Get database config twice
        with patch.dict(os.environ, {
            "MONGODB_URI": "mongodb://localhost:27017/test",
            "MONGODB_DATABASE": "test_db",
            "SQLITE_DATABASE_PATH": "/tmp/test.db"
        }):
            database_config1 = config_manager.get_database_config()
            database_config2 = config_manager.get_database_config()
            
            # Should be the same object
            assert database_config1 is database_config2
            
            # Get Redis config twice
            with patch.dict(os.environ, {
                "REDIS_URL": "redis://localhost:6379/0",
                "REDIS_PASSWORD": "test_password"
            }):
                redis_config1 = config_manager.get_redis_config()
                redis_config2 = config_manager.get_redis_config()
                
                # Should be the same object
                assert redis_config1 is redis_config2
    
    @patch.dict(os.environ, {
        "MONGODB_URI": "mongodb://localhost:27017/test",
        "MONGODB_DATABASE": "test_db",
        "SQLITE_DATABASE_PATH": "/tmp/test.db"
    })
    def test_get_database_config(self):
        """Test getting database configuration."""
        config_manager = ConfigManager()
        database_config = config_manager.get_database_config()
        
        assert isinstance(database_config, DatabaseConfig)
        assert database_config.mongodb_uri == "mongodb://localhost:27017/test"
        assert database_config.mongodb_database == "test_db"
        assert database_config.sqlite_database_path == "/tmp/test.db"
    
    @patch.dict(os.environ, {
        "MONGODB_URI": "mongodb://localhost:27017/test"
    })
    def test_get_database_config_with_defaults(self):
        """Test getting database configuration with default values."""
        config_manager = ConfigManager()
        database_config = config_manager.get_database_config()
        
        assert isinstance(database_config, DatabaseConfig)
        assert database_config.mongodb_uri == "mongodb://localhost:27017/test"
        assert database_config.mongodb_database == "yabot"  # Default value
        assert database_config.sqlite_database_path == "yabot.db"  # Default value
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_database_config_missing_uri(self):
        """Test getting database configuration when MongoDB URI is missing."""
        config_manager = ConfigManager()
        with pytest.raises(ValueError, match="MONGODB_URI environment variable is required but not set"):
            config_manager.get_database_config()
    
    @patch.dict(os.environ, {
        "REDIS_URL": "redis://localhost:6379/0",
        "REDIS_PASSWORD": "test_password"
    })
    def test_get_redis_config(self):
        """Test getting Redis configuration."""
        config_manager = ConfigManager()
        redis_config = config_manager.get_redis_config()
        
        assert isinstance(redis_config, RedisConfig)
        assert redis_config.redis_url == "redis://localhost:6379/0"
        assert redis_config.redis_password == "test_password"
    
    @patch.dict(os.environ, {
        "REDIS_URL": "redis://localhost:6379/0"
    })
    def test_get_redis_config_without_password(self):
        """Test getting Redis configuration without password."""
        config_manager = ConfigManager()
        redis_config = config_manager.get_redis_config()
        
        assert isinstance(redis_config, RedisConfig)
        assert redis_config.redis_url == "redis://localhost:6379/0"
        assert redis_config.redis_password is None
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_redis_config_missing_url(self):
        """Test getting Redis configuration when Redis URL is missing."""
        config_manager = ConfigManager()
        with pytest.raises(ValueError, match="REDIS_URL environment variable is required but not set"):
            config_manager.get_redis_config()