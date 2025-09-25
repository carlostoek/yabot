"""
Unit tests for ConfigManager with comprehensive configuration scenarios.

Key areas tested:
1. Environment variable loading and validation
2. Redis configuration access fixes
3. Configuration validation with all edge cases
4. Pydantic model validation
5. Boolean configuration handling
6. Missing configuration handling and defaults
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from src.config.manager import ConfigManager, get_config_manager
from src.core.models import BotConfig, WebhookConfig, DatabaseConfig, RedisConfig, APIConfig, LoggingConfig


class TestConfigManager:
    """Test ConfigManager functionality."""

    @pytest.fixture(autouse=True)
    def clean_environment(self):
        """Clean environment variables before each test."""
        # Store original values
        original_env = {}
        env_vars = [
            'BOT_TOKEN', 'WEBHOOK_URL', 'WEBHOOK_SECRET', 'LOG_LEVEL',
            'MONGODB_URI', 'MONGODB_DATABASE', 'REDIS_URL', 'REDIS_PASSWORD',
            'API_HOST', 'API_PORT', 'POLLING_ENABLED'
        ]

        for var in env_vars:
            original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

        yield

        # Restore original values
        for var, value in original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

    def test_config_manager_initialization_with_all_defaults(self):
        """Test ConfigManager initialization with minimal environment variables."""
        # Set only required variables
        os.environ['BOT_TOKEN'] = 'test_token'

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            # Test that defaults were applied
            assert config_manager.bot_config.bot_token == 'test_token'
            assert config_manager.bot_config.polling_enabled is True  # Default
            assert config_manager.bot_config.max_connections == 100  # Default
            assert config_manager.webhook_config is None  # No webhook URL provided

    def test_config_manager_initialization_with_comprehensive_config(self):
        """Test ConfigManager initialization with all configuration options."""
        # Set all environment variables
        env_vars = {
            'BOT_TOKEN': 'test_bot_token_123:ABC-DEF',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'WEBHOOK_SECRET': 'webhook_secret',
            'WEBHOOK_CERTIFICATE': '/path/to/cert.pem',
            'WEBHOOK_IP_ADDRESS': '192.168.1.100',
            'WEBHOOK_MAX_CONNECTIONS': '50',
            'WEBHOOK_ALLOWED_UPDATES': 'message,callback_query',
            'POLLING_ENABLED': 'false',
            'MAX_CONNECTIONS': '200',
            'REQUEST_TIMEOUT': '45',
            'LOG_LEVEL': 'INFO',
            'LOG_FORMAT': 'text',
            'LOG_FILE_PATH': '/var/log/yabot.log',
            'LOG_MAX_FILE_SIZE': '20971520',  # 20MB
            'LOG_BACKUP_COUNT': '10',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'yabot_prod',
            'SQLITE_DATABASE_PATH': '/data/yabot.db',
            'SQLITE_POOL_SIZE': '25',
            'SQLITE_MAX_OVERFLOW': '40',
            'SQLITE_POOL_TIMEOUT': '15',
            'SQLITE_POOL_RECYCLE': '7200',
            'MONGODB_MIN_POOL_SIZE': '8',
            'MONGODB_MAX_POOL_SIZE': '100',
            'MONGODB_MAX_IDLE_TIME': '60000',
            'MONGODB_SERVER_SELECTION_TIMEOUT': '10000',
            'MONGODB_SOCKET_TIMEOUT': '20000',
            'REDIS_URL': 'redis://redis-server:6379',
            'REDIS_PASSWORD': 'redis_password',
            'REDIS_MAX_CONNECTIONS': '75',
            'REDIS_RETRY_ON_TIMEOUT': 'false',
            'REDIS_SOCKET_CONNECT_TIMEOUT': '3',
            'REDIS_SOCKET_TIMEOUT': '8',
            'REDIS_LOCAL_QUEUE_MAX_SIZE': '500',
            'REDIS_LOCAL_QUEUE_PERSISTENCE_FILE': '/tmp/events.pkl',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8080',
            'API_WORKERS': '4',
            'API_SSL_CERT': '/path/to/ssl.crt',
            'API_SSL_KEY': '/path/to/ssl.key',
            'API_ACCESS_TOKEN_EXPIRE_MINUTES': '30',
            'API_REFRESH_TOKEN_EXPIRE_DAYS': '14'
        }

        for key, value in env_vars.items():
            os.environ[key] = value

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            # Verify bot config
            assert config_manager.bot_config.bot_token == 'test_bot_token_123:ABC-DEF'
            assert config_manager.bot_config.polling_enabled is False
            assert config_manager.bot_config.max_connections == 200
            assert config_manager.bot_config.request_timeout == 45

            # Verify webhook config
            assert config_manager.webhook_config is not None
            assert config_manager.webhook_config.url == 'https://example.com/webhook'
            assert config_manager.webhook_config.secret_token == 'webhook_secret'
            assert config_manager.webhook_config.certificate == '/path/to/cert.pem'
            assert config_manager.webhook_config.ip_address == '192.168.1.100'
            assert config_manager.webhook_config.max_connections == 50
            assert config_manager.webhook_config.allowed_updates == ['message', 'callback_query']

            # Verify database config
            assert config_manager.database_config.mongodb_uri == 'mongodb://localhost:27017'
            assert config_manager.database_config.mongodb_database == 'yabot_prod'
            assert config_manager.database_config.sqlite_database_path == '/data/yabot.db'
            assert config_manager.database_config.pool_size == 25
            assert config_manager.database_config.mongodb_min_pool_size == 8

            # Verify Redis config (test recent Redis configuration access fixes)
            assert config_manager.redis_config.url == 'redis://redis-server:6379'
            assert config_manager.redis_config.password == 'redis_password'
            assert config_manager.redis_config.max_connections == 75
            assert config_manager.redis_config.retry_on_timeout is False
            assert config_manager.redis_config.local_queue_max_size == 500

    def test_redis_configuration_access_patterns(self):
        """Test Redis configuration access patterns that had recent fixes."""
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'REDIS_URL': 'redis://localhost:6379',
            'REDIS_PASSWORD': 'test_password',
            'REDIS_MAX_CONNECTIONS': '20'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            # Test the specific access patterns that were fixed
            redis_config = config_manager.get_redis_config()
            assert redis_config is not None

            # Test attribute access patterns
            assert hasattr(redis_config, 'url')
            assert hasattr(redis_config, 'password')
            assert hasattr(redis_config, 'max_connections')

            # Test the values
            assert redis_config.url == 'redis://localhost:6379'
            assert redis_config.password == 'test_password'
            assert redis_config.max_connections == 20

            # Test has_redis_config method
            assert config_manager.has_redis_config() is True

    def test_boolean_configuration_handling(self):
        """Test boolean configuration handling patterns."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
            ('', False),  # Empty string
            ('invalid', False)  # Invalid value
        ]

        for value, expected in test_cases:
            os.environ.clear()
            os.environ['BOT_TOKEN'] = 'test_token'
            os.environ['POLLING_ENABLED'] = value
            os.environ['REDIS_RETRY_ON_TIMEOUT'] = value

            with patch('src.utils.logger.setup_basic_logging'), \
                 patch('src.utils.logger.setup_logging_with_config'):
                config_manager = ConfigManager()

                assert config_manager.bot_config.polling_enabled == expected
                assert config_manager.redis_config.retry_on_timeout == expected

    def test_configuration_validation_success(self):
        """Test successful configuration validation."""
        os.environ.update({
            'BOT_TOKEN': 'valid_bot_token',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'yabot',
            'SQLITE_DATABASE_PATH': './yabot.db',
            'REDIS_URL': 'redis://localhost:6379'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()
            result = config_manager.validate_config()
            assert result is True

    def test_configuration_validation_failures(self):
        """Test configuration validation failures."""
        # Test missing bot token
        os.environ.clear()

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            with pytest.raises(ValueError, match="Configuration validation failed"):
                ConfigManager()

    def test_configuration_validation_missing_webhook_url(self):
        """Test validation failure for webhook configuration without URL."""
        os.environ.update({
            'BOT_TOKEN': 'valid_bot_token',
            'WEBHOOK_SECRET': 'secret',  # Webhook secret without URL
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'yabot',
            'SQLITE_DATABASE_PATH': './yabot.db',
            'REDIS_URL': 'redis://localhost:6379'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            # This should work because webhook_config will be None when no URL is provided
            config_manager = ConfigManager()
            assert config_manager.webhook_config is None

    def test_webhook_mode_detection(self):
        """Test webhook mode detection logic."""
        # Test polling mode (default)
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'POLLING_ENABLED': 'true'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()
            assert config_manager.is_webhook_mode() is False
            assert config_manager.get_mode() == 'polling'

        # Test webhook mode
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'POLLING_ENABLED': 'false'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()
            assert config_manager.is_webhook_mode() is True
            assert config_manager.get_mode() == 'webhook'

    def test_database_configuration_availability_checks(self):
        """Test database configuration availability checks."""
        # Test with complete database config
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'yabot',
            'SQLITE_DATABASE_PATH': './yabot.db'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()
            assert config_manager.has_database_config() is True

        # Test with missing database config
        os.environ.clear()
        os.environ['BOT_TOKEN'] = 'test_token'

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            with pytest.raises(ValueError, match="MONGODB_URI is required"):
                ConfigManager()

    def test_redis_configuration_availability_checks(self):
        """Test Redis configuration availability checks."""
        # Test with Redis config
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'REDIS_URL': 'redis://localhost:6379'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()
            assert config_manager.has_redis_config() is True

        # Test without Redis URL (should still pass as it has default)
        os.environ.clear()
        os.environ['BOT_TOKEN'] = 'test_token'

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            with pytest.raises(ValueError):  # Will fail on other required configs first
                ConfigManager()

    def test_pydantic_validation_errors(self):
        """Test Pydantic validation errors for invalid configurations."""
        # Test invalid port number
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'API_PORT': 'invalid_port_number'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            with pytest.raises((ValueError, ValidationError)):
                ConfigManager()

        # Test negative timeout values
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'REQUEST_TIMEOUT': '-10'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            with pytest.raises((ValueError, ValidationError)):
                ConfigManager()

    def test_environment_variable_precedence(self):
        """Test environment variable precedence over defaults."""
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'MAX_CONNECTIONS': '150',  # Override default of 100
            'LOG_LEVEL': 'WARNING',    # Override default of INFO
            'SQLITE_POOL_SIZE': '30'   # Override default of 20
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            assert config_manager.bot_config.max_connections == 150
            assert config_manager.logging_config.level == 'WARNING'
            assert config_manager.database_config.pool_size == 30

    def test_configuration_getter_methods(self):
        """Test all configuration getter methods."""
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'yabot',
            'SQLITE_DATABASE_PATH': './yabot.db',
            'REDIS_URL': 'redis://localhost:6379'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            # Test all getter methods
            assert config_manager.get_bot_token() == 'test_token'
            assert config_manager.get_webhook_config() is not None
            assert config_manager.get_logging_config() is not None
            assert config_manager.get_database_config() is not None
            assert config_manager.get_redis_config() is not None
            assert config_manager.get_api_config() is not None

    def test_webhook_allowed_updates_parsing(self):
        """Test webhook allowed updates parsing."""
        # Test with comma-separated values
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'WEBHOOK_ALLOWED_UPDATES': 'message,callback_query,inline_query'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            assert config_manager.webhook_config.allowed_updates == [
                'message', 'callback_query', 'inline_query'
            ]

        # Test with empty string
        os.environ['WEBHOOK_ALLOWED_UPDATES'] = ''

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            assert config_manager.webhook_config.allowed_updates == []

    def test_logging_configuration_edge_cases(self):
        """Test logging configuration edge cases."""
        # Test with file logging
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'LOG_FILE_PATH': '/var/log/yabot.log',
            'LOG_MAX_FILE_SIZE': '50000000',  # 50MB
            'LOG_BACKUP_COUNT': '15'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            assert config_manager.logging_config.file_path == '/var/log/yabot.log'
            assert config_manager.logging_config.max_file_size == 50000000
            assert config_manager.logging_config.backup_count == 15

    def test_global_config_manager_singleton(self):
        """Test global config manager singleton pattern."""
        os.environ['BOT_TOKEN'] = 'test_token'

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config1 = get_config_manager()
            config2 = get_config_manager()

            assert config1 is config2

    def test_configuration_with_ssl_settings(self):
        """Test configuration with SSL settings."""
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'API_SSL_CERT': '/path/to/cert.pem',
            'API_SSL_KEY': '/path/to/key.pem',
            'API_HOST': '0.0.0.0',
            'API_PORT': '443'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            api_config = config_manager.get_api_config()
            assert api_config.ssl_cert == '/path/to/cert.pem'
            assert api_config.ssl_key == '/path/to/key.pem'
            assert api_config.host == '0.0.0.0'
            assert api_config.port == 443

    def test_configuration_error_handling_in_loading(self):
        """Test error handling during configuration loading."""
        os.environ['BOT_TOKEN'] = 'test_token'

        # Test Pydantic validation error handling
        with patch('src.core.models.BotConfig') as mock_bot_config:
            mock_bot_config.side_effect = ValidationError([], BotConfig)

            with patch('src.utils.logger.setup_basic_logging'), \
                 patch('src.utils.logger.setup_logging_with_config'):
                with pytest.raises(ValidationError):
                    ConfigManager()

    def test_complex_mongodb_configuration(self):
        """Test complex MongoDB configuration scenarios."""
        os.environ.update({
            'BOT_TOKEN': 'test_token',
            'MONGODB_URI': 'mongodb://user:pass@host1:27017,host2:27017/yabot?replicaSet=rs0',
            'MONGODB_DATABASE': 'yabot_production',
            'MONGODB_MIN_POOL_SIZE': '10',
            'MONGODB_MAX_POOL_SIZE': '200',
            'MONGODB_MAX_IDLE_TIME': '120000',
            'MONGODB_SERVER_SELECTION_TIMEOUT': '15000',
            'MONGODB_SOCKET_TIMEOUT': '30000'
        })

        with patch('src.utils.logger.setup_basic_logging'), \
             patch('src.utils.logger.setup_logging_with_config'):
            config_manager = ConfigManager()

            db_config = config_manager.get_database_config()
            assert 'replicaSet=rs0' in db_config.mongodb_uri
            assert db_config.mongodb_database == 'yabot_production'
            assert db_config.mongodb_min_pool_size == 10
            assert db_config.mongodb_max_pool_size == 200
            assert db_config.mongodb_max_idle_time == 120000