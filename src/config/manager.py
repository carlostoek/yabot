"""
Core Bot Framework - Configuration Manager

This module provides centralized configuration management with validation 
and environment-based configuration support.
"""
import os
import logging
from typing import Optional
from pydantic import ValidationError
from dotenv import load_dotenv

# Import the models from the core module
from src.core.models import BotConfig, WebhookConfig, LoggingConfig, DatabaseConfig, RedisConfig, APIConfig, ChannelConfig


class ConfigManager:
    """
    Centralized configuration management with validation and environment support
    """
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Initialize logging with basic configuration to avoid circular imports
        from src.utils.logger import setup_basic_logging
        setup_basic_logging()
        
        # Initialize configuration objects
        self.bot_config = self._load_bot_config()
        self.webhook_config = self._load_webhook_config()
        self.logging_config = self._load_logging_config()
        self.database_config = self._load_database_config()
        self.redis_config = self._load_redis_config()
        self.api_config = self._load_api_config()
        self.channel_config = self._load_channel_config()
        
        # Validate all configurations
        self.validate_config()
        
        # Now that configuration is loaded, setup full logging
        from src.utils.logger import setup_logging_with_config
        setup_logging_with_config(self.logging_config)
    
    def _load_bot_config(self) -> BotConfig:
        """
        Load bot configuration from environment variables
        """
        try:
            bot_config = BotConfig(
                bot_token=os.getenv("BOT_TOKEN", ""),
                webhook_url=os.getenv("WEBHOOK_URL"),
                webhook_secret=os.getenv("WEBHOOK_SECRET"),
                polling_enabled=os.getenv("POLLING_ENABLED", "true").lower() in ("true", "1", "yes"),
                max_connections=int(os.getenv("MAX_CONNECTIONS", "100")),
                request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30"))
            )
            return bot_config
        except ValidationError as e:
            logging.error(f"Error validating bot configuration: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading bot configuration: {e}")
            raise
    
    def _load_webhook_config(self) -> Optional[WebhookConfig]:
        """
        Load webhook configuration from environment variables
        """
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            return None
        
        try:
            webhook_config = WebhookConfig(
                url=webhook_url,
                secret_token=os.getenv("WEBHOOK_SECRET"),
                certificate=os.getenv("WEBHOOK_CERTIFICATE"),
                ip_address=os.getenv("WEBHOOK_IP_ADDRESS"),
                max_connections=int(os.getenv("WEBHOOK_MAX_CONNECTIONS", "40")),
                allowed_updates=os.getenv("WEBHOOK_ALLOWED_UPDATES", "").split(",") if os.getenv("WEBHOOK_ALLOWED_UPDATES") else []
            )
            return webhook_config
        except ValidationError as e:
            logging.error(f"Error validating webhook configuration: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading webhook configuration: {e}")
            raise
    
    def _load_logging_config(self) -> LoggingConfig:
        """
        Load logging configuration from environment variables
        """
        try:
            file_path = os.getenv("LOG_FILE_PATH")
            if os.getenv("PYTEST_RUNNING"):
                file_path = None

            logging_config = LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "json"),
                file_path=file_path,
                max_file_size=int(os.getenv("LOG_MAX_FILE_SIZE", "10485760")),  # 10MB
                backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))
            )
            return logging_config
        except ValidationError as e:
            logging.error(f"Error validating logging configuration: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading logging configuration: {e}")
            raise
    
    def _load_database_config(self) -> DatabaseConfig:
        """
        Load database configuration from environment variables
        """
        try:
            database_config = DatabaseConfig(
                mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
                mongodb_database=os.getenv("MONGODB_DATABASE", "yabot"),
                sqlite_database_path=os.getenv("SQLITE_DATABASE_PATH", "./yabot.db"),
                pool_size=int(os.getenv("SQLITE_POOL_SIZE", "20")),
                max_overflow=int(os.getenv("SQLITE_MAX_OVERFLOW", "30")),
                pool_timeout=int(os.getenv("SQLITE_POOL_TIMEOUT", "10")),
                pool_recycle=int(os.getenv("SQLITE_POOL_RECYCLE", "3600")),  # 1 hour
                mongodb_min_pool_size=int(os.getenv("MONGODB_MIN_POOL_SIZE", "5")),
                mongodb_max_pool_size=int(os.getenv("MONGODB_MAX_POOL_SIZE", "50")),
                mongodb_max_idle_time=int(os.getenv("MONGODB_MAX_IDLE_TIME", "30000")),  # 30 seconds
                mongodb_server_selection_timeout=int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT", "5000")),  # 5 seconds
                mongodb_socket_timeout=int(os.getenv("MONGODB_SOCKET_TIMEOUT", "10000"))  # 10 seconds
            )
            return database_config
        except ValidationError as e:
            logging.error(f"Error validating database configuration: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading database configuration: {e}")
            raise
    
    def _load_redis_config(self) -> RedisConfig:
        """
        Load Redis configuration from environment variables
        """
        try:
            redis_config = RedisConfig(
                url=os.getenv("REDIS_URL", "redis://localhost:6379"),
                password=os.getenv("REDIS_PASSWORD"),
                max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
                retry_on_timeout=os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() in ("true", "1", "yes"),
                socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
                socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "10")),
                local_queue_max_size=int(os.getenv("REDIS_LOCAL_QUEUE_MAX_SIZE", "1000")),
                local_queue_persistence_file=os.getenv("REDIS_LOCAL_QUEUE_PERSISTENCE_FILE", "event_queue.pkl")
            )
            return redis_config
        except ValidationError as e:
            logging.error(f"Error validating Redis configuration: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading Redis configuration: {e}")
            raise
    
    def _load_api_config(self) -> APIConfig:
        """
        Load internal API configuration from environment variables
        """
        try:
            api_config = APIConfig(
                host=os.getenv("API_HOST", "localhost"),
                port=int(os.getenv("API_PORT", "8001")),
                workers=int(os.getenv("API_WORKERS", "1")),
                ssl_cert=os.getenv("API_SSL_CERT"),
                ssl_key=os.getenv("API_SSL_KEY"),
                access_token_expire_minutes=int(os.getenv("API_ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
                refresh_token_expire_days=int(os.getenv("API_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
            )
            return api_config
        except ValidationError as e:
            logging.error(f"Error validating API configuration: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading API configuration: {e}")
            raise

    def _load_channel_config(self) -> 'ChannelConfig':
        """
        Load channel configuration from environment variables
        """
        from src.core.models import ChannelConfig
        
        try:
            channel_config = ChannelConfig(
                main_channel=os.getenv("MAIN_CHANNEL", "@yabot_canal"),
                required_reaction_emoji=os.getenv("REQUIRED_REACTION_EMOJI", "❤️"),
                channel_post_timeout=int(os.getenv("CHANNEL_POST_TIMEOUT", "300")),
                reaction_detection_timeout=int(os.getenv("REACTION_DETECTION_TIMEOUT", "5"))
            )
            return channel_config
        except ValidationError as e:
            logging.error(f"Error validating channel configuration: {e}")
            raise
        except Exception as e:
            logging.error(f"Error loading channel configuration: {e}")
            raise
    
    def get_bot_token(self) -> str:
        """
        Retrieve validated bot token
        """
        return self.bot_config.bot_token
    
    def get_webhook_config(self) -> Optional[WebhookConfig]:
        """
        Get webhook settings
        """
        return self.webhook_config
    
    def get_logging_config(self) -> LoggingConfig:
        """
        Get logging configuration
        """
        return self.logging_config
    
    def get_database_config(self) -> DatabaseConfig:
        """
        Get database configuration
        """
        return self.database_config
    
    def get_redis_config(self) -> RedisConfig:
        """
        Get Redis configuration
        """
        return self.redis_config
    
    def get_api_config(self) -> APIConfig:
        """
        Get internal API configuration
        """
        return self.api_config

    def get_channel_config(self) -> 'ChannelConfig':
        """
        Get channel configuration
        """
        return self.channel_config
    
    def validate_config(self) -> bool:
        """
        Validate all configuration parameters
        """
        errors = []
        
        # Validate bot token
        if not self.bot_config.bot_token:
            errors.append("BOT_TOKEN is required")
        
        # Validate webhook configuration if webhook is enabled
        if self.webhook_config:
            if not self.webhook_config.url:
                errors.append("WEBHOOK_URL is required when webhook is enabled")
        
        # Validate database configuration
        if not self.database_config.mongodb_uri:
            errors.append("MONGODB_URI is required")
        if not self.database_config.mongodb_database:
            errors.append("MONGODB_DATABASE is required")
        if not self.database_config.sqlite_database_path:
            errors.append("SQLITE_DATABASE_PATH is required")
        
        # Validate Redis configuration
        if not self.redis_config.url:
            errors.append("REDIS_URL is required")
        
        # Validate channel configuration
        if not self.channel_config.main_channel:
            errors.append("MAIN_CHANNEL is required")
        if not self.channel_config.required_reaction_emoji:
            errors.append("REQUIRED_REACTION_EMOJI is required")
        
        # Log any validation errors
        if errors:
            for error in errors:
                logging.error(error)
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
        
        return True
    
    def is_webhook_mode(self) -> bool:
        """
        Check if the bot is configured to use webhook mode
        """
        return bool(self.webhook_config and self.bot_config.polling_enabled is False)
    
    def get_mode(self) -> str:
        """
        Get the current operation mode (polling or webhook)
        """
        return "webhook" if self.is_webhook_mode() else "polling"
    
    def has_database_config(self) -> bool:
        """
        Check if database configuration is available
        """
        return (
            bool(self.database_config.mongodb_uri) and 
            bool(self.database_config.mongodb_database) and 
            bool(self.database_config.sqlite_database_path)
        )
    
    def has_redis_config(self) -> bool:
        """
        Check if Redis configuration is available
        """
        return bool(self.redis_config.url)


# Singleton instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager