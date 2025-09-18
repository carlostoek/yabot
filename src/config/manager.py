"""
Configuration manager for the Telegram bot framework.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from src.core.models import BotConfig, WebhookConfig, LoggingConfig, DatabaseConfig, RedisConfig


class ConfigManager:
    """Centralized configuration management with validation and environment support."""
    
    def __init__(self):
        """Initialize the configuration manager and load environment variables."""
        load_dotenv()
        self._bot_config: Optional[BotConfig] = None
        self._webhook_config: Optional[WebhookConfig] = None
        self._logging_config: Optional[LoggingConfig] = None
        self._database_config: Optional[DatabaseConfig] = None
        self._redis_config: Optional[RedisConfig] = None
    
    def get_bot_token(self) -> str:
        """Retrieve validated bot token.
        
        Returns:
            str: The Telegram bot token
            
        Raises:
            ValueError: If BOT_TOKEN is not set in environment variables
        """
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN environment variable is required but not set")
        return bot_token
    
    def get_webhook_config(self) -> WebhookConfig:
        """Get webhook settings.
        
        Returns:
            WebhookConfig: The webhook configuration
        """
        if self._webhook_config is None:
            self._webhook_config = WebhookConfig(
                url=os.getenv("WEBHOOK_URL", ""),
                secret_token=os.getenv("WEBHOOK_SECRET"),
                certificate=None,  # Will be loaded from file if needed
                ip_address=os.getenv("WEBHOOK_IP_ADDRESS"),
                max_connections=int(os.getenv("WEBHOOK_MAX_CONNECTIONS", "40")),
                allowed_updates=[]
            )
        return self._webhook_config
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration.
        
        Returns:
            LoggingConfig: The logging configuration
        """
        if self._logging_config is None:
            self._logging_config = LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "json"),
                file_path=os.getenv("LOG_FILE_PATH"),
                max_file_size=int(os.getenv("LOG_MAX_FILE_SIZE", "10485760")),
                backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))
            )
        return self._logging_config
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration for MongoDB and SQLite.
        
        Returns:
            DatabaseConfig: The database configuration
            
        Raises:
            ValueError: If required database configuration is missing or invalid
        """
        if self._database_config is None:
            mongodb_uri = os.getenv("MONGODB_URI")
            if not mongodb_uri:
                raise ValueError("MONGODB_URI environment variable is required but not set")
            
            mongodb_database = os.getenv("MONGODB_DATABASE", "yabot")
            
            # SQLite database path with default fallback
            sqlite_database_path = os.getenv("SQLITE_DATABASE_PATH", "yabot.db")
            
            self._database_config = DatabaseConfig(
                mongodb_uri=mongodb_uri,
                mongodb_database=mongodb_database,
                sqlite_database_path=sqlite_database_path
            )
        return self._database_config
    
    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration.
        
        Returns:
            RedisConfig: The Redis configuration
            
        Raises:
            ValueError: If required Redis configuration is missing or invalid
        """
        if self._redis_config is None:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                raise ValueError("REDIS_URL environment variable is required but not set")
            
            redis_password = os.getenv("REDIS_PASSWORD")
            
            self._redis_config = RedisConfig(
                redis_url=redis_url,
                redis_password=redis_password
            )
        return self._redis_config
    
    def validate_config(self) -> bool:
        """Validate all configuration parameters.
        
        Returns:
            bool: True if all required configuration parameters are valid
            
        Raises:
            ValueError: If any required configuration parameter is invalid
        """
        # Validate bot token
        bot_token = self.get_bot_token()
        if not bot_token or len(bot_token) < 10:
            raise ValueError("Invalid bot token: Token is required and must be at least 10 characters")
        
        # Validate webhook config if webhook is enabled
        webhook_config = self.get_webhook_config()
        if webhook_config.url and not webhook_config.url.startswith("https://"):
            raise ValueError("Invalid webhook URL: Must use HTTPS protocol")
        
        return True
    
    def validate_bot_token(self) -> bool:
        """Validate bot token format."""
        try:
            token = self.get_bot_token()
            return InputValidator.validate_bot_token(token)
        except ValueError:
            return False