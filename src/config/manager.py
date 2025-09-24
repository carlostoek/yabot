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
from src.core.models import BotConfig, WebhookConfig, LoggingConfig


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
            logging_config = LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "json"),
                file_path=os.getenv("LOG_FILE_PATH"),
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