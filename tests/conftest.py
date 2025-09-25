"""
Test configuration for the comprehensive bot framework test suite.

This module contains shared fixtures and configuration for all tests,
including comprehensive mocking for recent fixes and infrastructure components.
"""# Pytest plugins
pytest_plugins = ["tests.utils.events"]

import os
import pytest
import asyncio
import tempfile
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Generator, Dict, Any

# Set comprehensive test environment variables
os.environ.setdefault('BOT_TOKEN', 'test_bot_token_123:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')
os.environ.setdefault('WEBHOOK_URL', 'https://test.example.com/webhook')
os.environ.setdefault('WEBHOOK_SECRET', 'test_webhook_secret_for_testing')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')
os.environ.setdefault('MONGODB_URI', 'mongodb://localhost:27017')
os.environ.setdefault('MONGODB_DATABASE', 'yabot_test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('API_HOST', 'localhost')
os.environ.setdefault('API_PORT', '8001')
os.environ.setdefault('POLLING_ENABLED', 'true')


@pytest.fixture
def mock_aiogram_bot():
    """Mock aiogram Bot instance for testing."""
    with patch('aiogram.Bot') as mock_bot:
        mock_bot_instance = MagicMock()
        mock_bot_instance.session = MagicMock()
        mock_bot_instance.session.close = AsyncMock()
        mock_bot_instance.get_me = AsyncMock(return_value=MagicMock(
            id=123456789,
            is_bot=True,
            first_name='Test Bot',
            username='test_bot'
        ))
        mock_bot.return_value = mock_bot_instance
        yield mock_bot_instance


@pytest.fixture
def mock_aiogram_dispatcher():
    """Mock aiogram Dispatcher instance for testing."""
    with patch('aiogram.Dispatcher') as mock_dispatcher:
        mock_dispatcher_instance = MagicMock()
        mock_dispatcher_instance.start_polling = AsyncMock()
        mock_dispatcher_instance.stop_polling = AsyncMock()

        # Mock middleware registration
        mock_dispatcher_instance.message = MagicMock()
        mock_dispatcher_instance.message.middleware = MagicMock()
        mock_dispatcher_instance.callback_query = MagicMock()
        mock_dispatcher_instance.callback_query.middleware = MagicMock()
        mock_dispatcher_instance.inline_query = MagicMock()
        mock_dispatcher_instance.inline_query.middleware = MagicMock()
        mock_dispatcher_instance.chosen_inline_result = MagicMock()
        mock_dispatcher_instance.chosen_inline_result.middleware = MagicMock()

        # Mock router registration
        mock_dispatcher_instance.include_router = MagicMock()

        # Mock error handling
        mock_dispatcher_instance.errors = MagicMock()
        mock_dispatcher_instance.errors.register = MagicMock()

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
    mock_user.language_code = 'en'

    mock_chat.id = 987654321
    mock_chat.type = 'private'

    # Link message to user and chat
    mock_message.from_user = mock_user
    mock_message.chat = mock_chat
    mock_message.text = '/start'
    mock_message.message_id = 1
    mock_message.date = datetime.now()
    mock_message.answer = AsyncMock()
    mock_message.reply = AsyncMock()

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
    mock_user.language_code = 'en'

    mock_chat.id = 987654321
    mock_chat.type = 'private'

    # Link message to user and chat
    mock_message.from_user = mock_user
    mock_message.chat = mock_chat
    mock_message.text = 'test message'
    mock_message.message_id = 1
    mock_message.date = datetime.now()
    mock_message.answer = AsyncMock()
    mock_message.reply = AsyncMock()

    return mock_message


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager for testing."""
    from src.config.manager import ConfigManager

    with patch.object(ConfigManager, '__new__') as mock_new:
        mock_config_instance = MagicMock(spec=ConfigManager)
        mock_new.return_value = mock_config_instance

        # Set default return values for common config methods
        mock_config_instance.get_bot_token.return_value = 'test_bot_token_123:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
        mock_config_instance.get_webhook_url.return_value = 'https://test.example.com/webhook'
        mock_config_instance.get_webhook_secret.return_value = 'test_webhook_secret'
        mock_config_instance.get_mode.return_value = 'polling'  # Default to polling in tests
        mock_config_instance.validate_config.return_value = True

        yield mock_config_instance


@pytest.fixture
def enhanced_mock_config_manager(test_database_config, test_redis_config):
    """Enhanced mock ConfigManager with comprehensive configuration."""
    from src.config.manager import ConfigManager
    from src.core.models import BotConfig, WebhookConfig, DatabaseConfig, RedisConfig, APIConfig, LoggingConfig

    mock_config = MagicMock(spec=ConfigManager)

    # Create mock config objects
    bot_config = BotConfig(
        bot_token='test_bot_token_123:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
        webhook_url='https://test.example.com/webhook',
        webhook_secret='test_webhook_secret',
        polling_enabled=True,
        max_connections=100,
        request_timeout=30
    )

    webhook_config = WebhookConfig(
        url='https://test.example.com/webhook',
        secret_token='test_webhook_secret',
        certificate=None,
        ip_address=None,
        max_connections=40,
        allowed_updates=[]
    )

    database_config = DatabaseConfig(**test_database_config)
    redis_config = RedisConfig(**test_redis_config)

    api_config = APIConfig(
        host='localhost',
        port=8001,
        workers=1,
        ssl_cert=None,
        ssl_key=None,
        access_token_expire_minutes=15,
        refresh_token_expire_days=7
    )

    logging_config = LoggingConfig(
        level='DEBUG',
        format='json',
        file_path=None,
        max_file_size=10485760,
        backup_count=5
    )

    # Set up mock return values
    mock_config.bot_config = bot_config
    mock_config.webhook_config = webhook_config
    mock_config.database_config = database_config
    mock_config.redis_config = redis_config
    mock_config.api_config = api_config
    mock_config.logging_config = logging_config

    # Method return values
    mock_config.get_bot_token.return_value = bot_config.bot_token
    mock_config.get_webhook_config.return_value = webhook_config
    mock_config.get_database_config.return_value = database_config
    mock_config.get_redis_config.return_value = redis_config
    mock_config.get_api_config.return_value = api_config
    mock_config.get_logging_config.return_value = logging_config

    mock_config.validate_config.return_value = True
    mock_config.is_webhook_mode.return_value = False
    mock_config.get_mode.return_value = 'polling'
    mock_config.has_database_config.return_value = True
    mock_config.has_redis_config.return_value = True

    return mock_config


@pytest.fixture
def test_bot_token():
    """Provide a test bot token for testing."""
    return os.environ.get('BOT_TOKEN', 'test_bot_token_123:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')


@pytest.fixture
def temp_db_file():
    """Provide a temporary SQLite database file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
        temp_file.close()
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except FileNotFoundError:
            pass


@pytest.fixture
def temp_event_queue_file():
    """Provide a temporary file for event queue persistence."""
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as temp_file:
        temp_file.close()
        yield temp_file.name
        try:
            os.unlink(temp_file.name)
        except FileNotFoundError:
            pass


@pytest.fixture
def test_database_config(temp_db_file):
    """Provide test database configuration."""
    return {
        'mongodb_uri': 'mongodb://localhost:27017',
        'mongodb_database': 'yabot_test',
        'sqlite_database_path': temp_db_file,
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 5,
        'pool_recycle': 1800,
        'mongodb_min_pool_size': 2,
        'mongodb_max_pool_size': 10,
        'mongodb_max_idle_time': 10000,
        'mongodb_server_selection_timeout': 2000,
        'mongodb_socket_timeout': 5000
    }


@pytest.fixture
def test_redis_config(temp_event_queue_file):
    """Provide test Redis configuration."""
    from src.core.models import RedisConfig
    return RedisConfig(
        url='redis://localhost:6379',
        password=None,
        max_connections=10,
        retry_on_timeout=True,
        socket_connect_timeout=2,
        socket_timeout=5,
        local_queue_max_size=100,
        local_queue_persistence_file=temp_event_queue_file
    )


@pytest.fixture
def mock_database_manager():
    """Mock DatabaseManager with all methods."""
    from src.database.manager import DatabaseManager

    mock_db = MagicMock(spec=DatabaseManager)

    # Mock database connections
    mock_db._mongo_connected = True
    mock_db._sqlite_connected = True
    mock_db._connected = True

    # Mock database instances
    mock_mongo_db = MagicMock()
    mock_sqlite_engine = MagicMock()

    mock_db.get_mongo_db.return_value = mock_mongo_db
    mock_db.get_sqlite_engine.return_value = mock_sqlite_engine

    # Mock connection methods
    mock_db.connect_all = AsyncMock(return_value=True)
    mock_db.initialize_databases = AsyncMock(return_value=True)
    mock_db.ensure_collections = AsyncMock(return_value=True)
    mock_db.ensure_tables = AsyncMock(return_value=True)
    mock_db.close_connections = AsyncMock()

    # Mock user methods
    mock_db.create_user_atomic = AsyncMock(return_value=True)
    mock_db.get_user_from_mongo = AsyncMock(return_value={'user_id': '123', 'current_state': {}})
    mock_db.get_user_profile_from_sqlite = AsyncMock(return_value={'user_id': '123', 'username': 'test'})
    mock_db.update_user_in_mongo = AsyncMock(return_value=True)
    mock_db.update_user_profile_in_sqlite = AsyncMock(return_value=True)
    mock_db.delete_user_from_mongo = AsyncMock(return_value=True)
    mock_db.delete_user_profile_from_sqlite = AsyncMock(return_value=True)

    # Mock health check
    mock_db.health_check = AsyncMock(return_value={
        'mongo_connected': True,
        'sqlite_connected': True,
        'overall_healthy': True,
        'mongo_ping': True,
        'sqlite_ping': True
    })

    return mock_db


@pytest.fixture
def mock_event_bus():
    """Mock EventBus with all methods."""
    from src.events.bus import EventBus

    mock_bus = MagicMock(spec=EventBus)

    # Mock connection status
    mock_bus._connected = True

    # Mock methods
    mock_bus.connect = AsyncMock()
    mock_bus.close = AsyncMock()
    mock_bus.publish = AsyncMock(return_value=True)
    mock_bus.subscribe = AsyncMock()

    # Mock health check
    mock_bus.health_check = AsyncMock(return_value={
        'redis_connected': True,
        'local_queue_size': 0,
        'connected': True,
        'redis_healthy': True,
        'overall_healthy': True
    })

    # Mock queue operations
    mock_bus.clear_local_queue = AsyncMock()
    mock_bus.replay_queue = AsyncMock(return_value=0)
    mock_bus.get_stats = AsyncMock(return_value={
        'published_events': 0,
        'failed_events': 0,
        'retried_events': 0,
        'local_queue_size': 0
    })

    return mock_bus


@pytest.fixture
def mock_user_service(mock_database_manager, mock_event_bus):
    """Mock UserService with dependencies."""
    from src.services.user import UserService

    mock_service = MagicMock(spec=UserService)
    mock_service.db_manager = mock_database_manager
    mock_service.event_bus = mock_event_bus

    # Mock user operations
    mock_service.create_user = AsyncMock(return_value={
        'user_id': '123',
        'mongo_created': True,
        'sqlite_created': True,
        'profile': {'user_id': '123', 'username': 'test'}
    })
    mock_service.get_user_context = AsyncMock(return_value={
        'user_id': '123',
        'mongo_data': {'user_id': '123', 'current_state': {}},
        'profile_data': {'user_id': '123', 'username': 'test'},
        'combined_context': {}
    })
    mock_service.update_user_state = AsyncMock(return_value=True)
    mock_service.update_user_profile = AsyncMock(return_value=True)
    mock_service.get_user_subscription_status = AsyncMock(return_value='active')
    mock_service.delete_user = AsyncMock(return_value=True)

    return mock_service


@pytest.fixture
def mock_bot_application():
    """Mock BotApplication with all components."""
    from src.core.application import BotApplication

    mock_app = MagicMock(spec=BotApplication)

    # Mock application state
    mock_app.is_running = False
    mock_app.bot = None
    mock_app.dispatcher = None
    mock_app.webhook_handler = None
    mock_app.fastapi_app = None

    # Mock lifecycle methods
    mock_app.initialize = AsyncMock()
    mock_app.start = AsyncMock()
    mock_app.stop = AsyncMock()
    mock_app.configure_webhook = AsyncMock(return_value=True)
    mock_app.configure_polling = AsyncMock(return_value=True)

    # Mock status
    mock_app.get_status.return_value = {
        'is_running': False,
        'bot_initialized': False,
        'webhook_configured': False,
        'mode': 'polling',
        'timestamp': datetime.now().isoformat()
    }

    return mock_app


@pytest.fixture
def mock_error_handler():
    """Mock ErrorHandler for testing."""
    from src.core.error_handler import ErrorHandler

    mock_handler = MagicMock(spec=ErrorHandler)

    mock_handler.handle_error = AsyncMock(return_value={
        'error_handled': True,
        'user_message': 'Test error message',
        'error_type': 'TestError',
        'critical': False,
        'timestamp': datetime.now().isoformat()
    })
    mock_handler.log_error = AsyncMock()
    mock_handler.get_user_message = AsyncMock(return_value='Test error message')
    mock_handler.handle_update_error = AsyncMock(return_value=True)

    return mock_handler


@pytest.fixture
def telegram_user_data():
    """Sample Telegram user data for testing."""
    return {
        'id': 123456789,
        'username': 'test_user',
        'first_name': 'Test',
        'last_name': 'User',
        'language_code': 'en'
    }


@pytest.fixture
def sample_mongo_user(telegram_user_data):
    """Sample MongoDB user document for testing."""
    return {
        'user_id': str(telegram_user_data['id']),
        'current_state': {
            'menu_context': 'main_menu',
            'narrative_progress': {
                'current_fragment': None,
                'completed_fragments': [],
                'choices_made': []
            }
        },
        'preferences': {
            'language': 'en',
            'notifications_enabled': True,
            'theme': 'default'
        },
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }


@pytest.fixture
def sample_sqlite_profile(telegram_user_data):
    """Sample SQLite user profile for testing."""
    return {
        'user_id': str(telegram_user_data['id']),
        'telegram_user_id': telegram_user_data['id'],
        'username': telegram_user_data.get('username'),
        'first_name': telegram_user_data.get('first_name'),
        'last_name': telegram_user_data.get('last_name'),
        'language_code': telegram_user_data.get('language_code'),
        'registration_date': datetime.utcnow(),
        'last_login': datetime.utcnow(),
        'is_active': True
    }


@pytest.fixture
async def real_sqlite_db(temp_db_file):
    """Create a real SQLite database for integration testing."""
    from src.database.manager import DatabaseManager

    # Create database with real SQLite connection
    config = {
        'mongodb_uri': 'mongodb://localhost:27017',
        'mongodb_database': 'yabot_test',
        'sqlite_database_path': temp_db_file,
        'pool_size': 1,
        'max_overflow': 0,
        'pool_timeout': 5,
        'pool_recycle': 1800
    }

    db_manager = DatabaseManager(config)

    # Initialize SQLite tables only
    try:
        # Use direct SQLite connection for setup
        conn = sqlite3.connect(temp_db_file)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                telegram_user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                plan_type TEXT NOT NULL CHECK (plan_type IN ('free', 'premium', 'vip')),
                status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'cancelled', 'expired')),
                start_date DATETIME NOT NULL,
                end_date DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)

        conn.commit()
        conn.close()

        yield db_manager

    finally:
        await db_manager.close_connections()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_redis = MagicMock()
    mock_redis.ping = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)
    mock_redis.close = AsyncMock()

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.listen = AsyncMock()
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub

    return mock_redis


@pytest.fixture
def mock_fastapi_app():
    """Mock FastAPI application for testing."""
    from fastapi import FastAPI

    mock_app = MagicMock(spec=FastAPI)
    mock_app.post = MagicMock()
    mock_app.get = MagicMock()

    return mock_app


@pytest.fixture
async def cleanup_global_singletons():
    """Cleanup global singleton instances after each test."""
    yield

    # Reset global instances
    from src.core.application import reset_bot_application
    from src.database.manager import reset_database_manager

    reset_bot_application()
    await reset_database_manager()


@pytest.fixture
def event_loop():
    """Create an event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Error simulation fixtures
@pytest.fixture
def network_error():
    """Network error for testing error handling."""
    from src.utils.errors import NetworkError
    return NetworkError("Test network error")


@pytest.fixture
def database_error():
    """Database error for testing error handling."""
    from src.utils.errors import DatabaseError
    return DatabaseError("Test database error")


@pytest.fixture
def configuration_error():
    """Configuration error for testing error handling."""
    from src.utils.errors import ConfigurationError
    return ConfigurationError("Test configuration error")


@pytest.fixture
def telegram_api_error():
    """Telegram API error for testing error handling."""
    from aiogram.exceptions import TelegramAPIError
    return TelegramAPIError(method='test', message='Test Telegram API error')


# Performance testing fixtures
@pytest.fixture
def performance_monitor():
    """Monitor for performance testing."""
    import time
    import psutil
    import os

    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_time = None
            self.start_memory = None

        def start(self):
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss

        def stop(self):
            end_time = time.time()
            end_memory = self.process.memory_info().rss

            return {
                'duration': end_time - self.start_time,
                'memory_delta': end_memory - self.start_memory,
                'memory_peak': self.process.memory_info().rss
            }

    return PerformanceMonitor()