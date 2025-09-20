"""
Core data models for the Telegram bot framework.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class BotConfig(BaseModel):
    """Configuration model for the Telegram bot."""
    bot_token: str
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    polling_enabled: bool = True
    max_connections: int = 100
    request_timeout: int = 30


class WebhookConfig(BaseModel):
    """Configuration model for webhook settings."""
    url: str
    secret_token: Optional[str] = None
    certificate: Optional[str] = None
    ip_address: Optional[str] = None
    max_connections: int = 40
    allowed_updates: List[str] = Field(default_factory=list)


class LoggingConfig(BaseModel):
    """Configuration model for logging settings."""
    level: str = "INFO"
    format: str = "json"
    file_path: Optional[str] = None
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5


class CommandResponse(BaseModel):
    """Response model for command handlers."""
    text: str
    parse_mode: Optional[str] = "HTML"
    reply_markup: Optional[dict] = None
    disable_notification: bool = False


class DatabaseConfig(BaseModel):
    """Configuration model for database connections."""
    mongodb_uri: str
    mongodb_database: str
    sqlite_database_path: str


class RedisConfig(BaseModel):
    """Configuration model for Redis connection."""
    redis_url: str
    redis_password: Optional[str] = None