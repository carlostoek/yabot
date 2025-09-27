"""
Core Bot Framework - Data Models

This module contains all the Pydantic data models used throughout the application.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class BotConfig(BaseModel):
    """
    Configuration model for the Telegram bot
    """
    bot_token: str
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    polling_enabled: bool = True
    max_connections: int = 100
    request_timeout: int = 30


class WebhookConfig(BaseModel):
    """
    Configuration model for webhook settings
    """
    url: str
    secret_token: Optional[str] = None
    certificate: Optional[str] = None
    ip_address: Optional[str] = None
    max_connections: int = 40
    allowed_updates: List[str] = Field(default_factory=list)


class LoggingConfig(BaseModel):
    """
    Configuration model for logging settings
    """
    level: str = "INFO"
    format: str = "json"
    file_path: Optional[str] = None
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5


class DatabaseConfig(BaseModel):
    """
    Configuration model for database connections
    """
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "yabot"
    sqlite_database_path: str = "./yabot.db"
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 10
    pool_recycle: int = 3600  # 1 hour
    # MongoDB specific configuration
    mongodb_min_pool_size: int = 5
    mongodb_max_pool_size: int = 50
    mongodb_max_idle_time: int = 30000  # 30 seconds
    mongodb_server_selection_timeout: int = 5000  # 5 seconds
    mongodb_socket_timeout: int = 10000  # 10 seconds


class RedisConfig(BaseModel):
    """
    Configuration model for Redis connection
    """
    url: str = "redis://localhost:6379"
    password: Optional[str] = None
    max_connections: int = 50
    retry_on_timeout: bool = True
    socket_connect_timeout: int = 5
    socket_timeout: int = 10
    local_queue_max_size: int = 1000
    local_queue_persistence_file: str = "event_queue.pkl"


class APIConfig(BaseModel):
    """
    Configuration model for internal API server
    """
    host: str = "localhost"
    port: int = 8001
    workers: int = 1
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


class ChannelConfig(BaseModel):
    """
    Configuration model for channel interactions
    """
    main_channel: str = "@yabot_canal"
    required_reaction_emoji: str = "❤️"
    channel_post_timeout: int = 300  # 5 minutes
    reaction_detection_timeout: int = 5  # 5 seconds


class CommandResponse(BaseModel):
    """
    Model for command responses
    """
    text: str
    parse_mode: Optional[str] = "HTML"
    reply_markup: Optional[dict] = None
    disable_notification: bool = False


class UserSession(BaseModel):
    """
    Model to track user session state
    """
    user_id: int
    current_state: str = "initial"
    context: dict = Field(default_factory=dict)
    created_at: Optional[str] = None
    last_activity: Optional[str] = None


class MessageContext(BaseModel):
    """
    Model for message processing context
    """
    message_id: int
    chat_id: int
    user_id: int
    message_type: str
    content: str
    timestamp: str
    metadata: dict = Field(default_factory=dict)


class BotCommand(BaseModel):
    """
    Model for bot commands
    """
    command: str
    description: str
    handler: str
    parameters: List[str] = Field(default_factory=list)
    requires_auth: bool = False


class WebhookUpdate(BaseModel):
    """
    Model for incoming webhook updates
    """
    update_id: int
    message: Optional[dict] = None
    edited_message: Optional[dict] = None
    channel_post: Optional[dict] = None
    edited_channel_post: Optional[dict] = None
    inline_query: Optional[dict] = None
    chosen_inline_result: Optional[dict] = None
    callback_query: Optional[dict] = None
    shipping_query: Optional[dict] = None
    pre_checkout_query: Optional[dict] = None
    poll: Optional[dict] = None
    poll_answer: Optional[dict] = None
    my_chat_member: Optional[dict] = None
    chat_member: Optional[dict] = None
    chat_join_request: Optional[dict] = None