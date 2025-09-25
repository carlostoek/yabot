"""
Test configuration for the comprehensive bot framework test suite.

This module contains shared fixtures and configuration for all tests,
including comprehensive mocking for recent fixes and infrastructure components.
"""
import os
import pytest
import asyncio
import tempfile
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Generator, Dict, Any, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field

# Set comprehensive test environment variables
os.environ.setdefault('BOT_TOKEN', '123456789:AAG-w_1234567890abcdefghijklmnopqrstuvwxyz')
os.environ.setdefault('WEBHOOK_URL', 'https://test.example.com/webhook')
os.environ.setdefault('WEBHOOK_SECRET', 'test_webhook_secret_for_testing')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')
os.environ.setdefault('MONGODB_URI', 'mongodb://localhost:27017')
os.environ.setdefault('MONGODB_DATABASE', 'yabot_test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('API_HOST', 'localhost')
os.environ.setdefault('API_PORT', '8001')
os.environ.setdefault('POLLING_ENABLED', 'true')
os.environ.setdefault('PYTEST_RUNNING', 'true')

# Imports from old events/conftest.py
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError
from src.events.bus import EventBus, LocalEventQueue, EventBusException, EventProcessingError
from src.events.models import (
    BaseEvent, EventStatus, UserInteractionEvent, UserRegistrationEvent,
    ReactionDetectedEvent, DecisionMadeEvent, SubscriptionUpdatedEvent,
    ContentViewedEvent, HintUnlockedEvent, SystemHealthEvent, SystemNotificationEvent
)
from src.utils.logger import get_logger
from src.core.models import RedisConfig


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
    from src.core.models import BotConfig, WebhookConfig, DatabaseConfig, APIConfig, LoggingConfig

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
    redis_config = test_redis_config

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

# Content from tests/utils/conftest.py
@dataclass
class EventTestScenario:
    """Defines a test scenario for event bus testing"""
    name: str
    events: List[BaseEvent] = field(default_factory=list)
    expected_outcomes: Dict[str, Any] = field(default_factory=dict)
    error_conditions: List[str] = field(default_factory=list)
    performance_requirements: Dict[str, float] = field(default_factory=dict)


class MockRedisClient:
    """
    Mock Redis client for event bus testing

    Provides a controlled Redis environment for testing event publishing,
    subscription, and failure scenarios.
    """

    def __init__(self, fail_on_connect: bool = False, fail_on_publish: bool = False):
        self.fail_on_connect = fail_on_connect
        self.fail_on_publish = fail_on_publish
        self.connected = False
        self.published_messages = []
        self.subscribers = {}
        self._closed = False

    async def ping(self):
        """Mock ping method"""
        if self.fail_on_connect or self._closed:
            raise ConnectionError("Mock Redis connection failed")
        self.connected = True
        return True

    async def publish(self, channel: str, data: str) -> int:
        """Mock publish method"""
        if self.fail_on_publish or self._closed:
            raise ConnectionError("Mock Redis publish failed")

        self.published_messages.append({
            'channel': channel,
            'data': data,
            'timestamp': datetime.utcnow()
        })

        # Notify subscribers if any
        if channel in self.subscribers:
            for callback in self.subscribers[channel]:
                try:
                    callback(data)
                except Exception as e:
                    pass

        return 1

    def pubsub(self):
        """Mock pubsub method"""
        return MockPubSub(self)

    async def close(self):
        """Mock close method"""
        self._closed = True
        self.connected = False

    def reset(self):
        """Reset mock state"""
        self.published_messages.clear()
        self.subscribers.clear()
        self.connected = False
        self._closed = False
        self.fail_on_connect = False
        self.fail_on_publish = False


class MockPubSub:
    """Mock Redis PubSub for subscription testing"""

    def __init__(self, redis_client: MockRedisClient):
        self.redis_client = redis_client
        self.subscribed_channels = set()

    async def subscribe(self, channel: str):
        """Mock subscribe method"""
        self.subscribed_channels.add(channel)
        if channel not in self.redis_client.subscribers:
            self.redis_client.subscribers[channel] = []

    async def listen(self):
        """Mock listen method for async iteration"""
        # Yield subscription confirmation
        for channel in self.subscribed_channels:
            yield {
                'type': 'subscribe',
                'pattern': None,
                'channel': channel.encode(),
                'data': 1
            }

        # Then simulate waiting for messages
        while not self.redis_client._closed:
            await asyncio.sleep(0.1)
            # This would normally yield messages from the queue
            yield {
                'type': 'message',
                'pattern': None,
                'channel': 'test',
                'data': b'{"event_type": "test", "data": "mock"}'
            }

    async def close(self):
        """Mock close method"""
        pass


class TestEventBusManager:
    """
    Test event bus manager that provides isolated test event bus instances

    This class manages test event bus instances with mocked Redis connections
    to ensure test isolation and prevent interference with production systems.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._temp_persistence_files = []
        self._event_buses = []
        self._mock_redis_clients = []

    async def create_test_event_bus(self,
                                   redis_fail_on_connect: bool = False,
                                   redis_fail_on_publish: bool = False,
                                   use_real_redis: bool = False) -> EventBus:
        """
        Create a test event bus instance

        Args:
            redis_fail_on_connect: Whether Redis connection should fail
            redis_fail_on_publish: Whether Redis publish should fail
            use_real_redis: Whether to use real Redis (for integration tests)

        Returns:
            Configured test event bus instance
        """
        # Create temporary persistence file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pkl', prefix='test_event_queue_')
        os.close(temp_fd)
        self._temp_persistence_files.append(temp_path)

        # Create test Redis config
        test_config = RedisConfig(
            url='redis://localhost:6379/15',  # Use test database
            max_connections=5,
            retry_on_timeout=True,
            socket_connect_timeout=2,
            socket_timeout=5,
            local_queue_max_size=100,
            local_queue_persistence_file=temp_path
        )

        # Create event bus
        event_bus = EventBus(test_config)

        if not use_real_redis:
            # Mock Redis client
            mock_redis = MockRedisClient(
                fail_on_connect=redis_fail_on_connect,
                fail_on_publish=redis_fail_on_publish
            )

            # Patch Redis client creation
            with patch.object(redis, 'ConnectionPool'):
                with patch.object(redis, 'Redis', return_value=mock_redis):
                    event_bus.redis_client = mock_redis
                    self._mock_redis_clients.append(mock_redis)

        self._event_buses.append(event_bus)
        return event_bus

    async def cleanup(self):
        """Clean up all test event buses and temporary files"""
        # Close all event buses
        for event_bus in self._event_buses:
            try:
                await event_bus.close()
            except Exception as e:
                self.logger.warning(f"Error closing event bus: {e}")

        # Reset mock clients
        for mock_redis in self._mock_redis_clients:
            mock_redis.reset()

        # Clean up temporary files
        for temp_path in self._temp_persistence_files:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except OSError as e:
                self.logger.warning(f"Error removing temp file {temp_path}: {e}")

        # Clear lists
        self._event_buses.clear()
        self._mock_redis_clients.clear()
        self._temp_persistence_files.clear()

        self.logger.info("Test event bus cleanup completed")


class EventTestDataGenerator:
    """
    Generator for realistic test event data

    Provides methods to generate realistic test events following the event schemas
    and patterns used in the system.
    """

    _event_counter = 0
    _user_counter = 100000

    @classmethod
    def _get_next_event_id(cls) -> str:
        """Generate unique event ID for testing"""
        cls._event_counter += 1
        return f"test_event_{cls._event_counter:06d}"

    @classmethod
    def _get_next_user_id(cls) -> str:
        """Generate unique user ID for testing"""
        cls._user_counter += 1
        return str(cls._user_counter)

    @staticmethod
    def generate_user_interaction_event(user_id: str = None, action: str = "start") -> UserInteractionEvent:
        """Generate user interaction event for testing"""
        if user_id is None:
            user_id = EventTestDataGenerator._get_next_user_id()

        return UserInteractionEvent(
            event_id=EventTestDataGenerator._get_next_event_id(),
            user_id=user_id,
            action=action,
            context={
                "menu_state": "main_menu",
                "test_scenario": True,
                "timestamp": datetime.utcnow().isoformat()
            },
            source="test_telegram"
        )

    @staticmethod
    def generate_user_registration_event(user_id: str = None) -> UserRegistrationEvent:
        """Generate user registration event for testing"""
        if user_id is None:
            user_id = EventTestDataGenerator._get_next_user_id()

        return UserRegistrationEvent(
            event_id=EventTestDataGenerator._get_next_event_id(),
            user_id=user_id,
            telegram_data={
                "id": int(user_id),
                "username": f"test_user_{user_id}",
                "first_name": "Test",
                "last_name": "User",
                "language_code": "es",
                "is_bot": False
            }
        )

    @staticmethod
    def generate_reaction_event(user_id: str = None, content_id: str = "test_content_001",
                               reaction_type: str = "besito") -> ReactionDetectedEvent:
        """Generate reaction event for testing"""
        if user_id is None:
            user_id = EventTestDataGenerator._get_next_user_id()

        return ReactionDetectedEvent(
            event_id=EventTestDataGenerator._get_next_event_id(),
            user_id=user_id,
            content_id=content_id,
            reaction_type=reaction_type,
            metadata={
                "reaction_context": "narrative_response",
                "content_type": "narrative_fragment"
            }
        )

    @staticmethod
    def generate_decision_event(user_id: str = None, fragment_id: str = "fragment_001",
                               choice_id: str = "choice_a") -> DecisionMadeEvent:
        """Generate decision event for testing"""
        if user_id is None:
            user_id = EventTestDataGenerator._get_next_user_id()

        return DecisionMadeEvent(
            event_id=EventTestDataGenerator._get_next_event_id(),
            user_id=user_id,
            choice_id=choice_id,
            fragment_id=fragment_id,
            next_fragment_id=f"next_{fragment_id}",
            context={
                "narrative_state": "in_progress",
                "choice_metadata": {"difficulty": "easy"}
            }
        )

    @staticmethod
    def generate_subscription_event(user_id: str = None, old_status: str = "inactive",
                                  new_status: str = "active", plan_type: str = "premium") -> SubscriptionUpdatedEvent:
        """Generate subscription event for testing"""
        if user_id is None:
            user_id = EventTestDataGenerator._get_next_user_id()

        return SubscriptionUpdatedEvent(
            event_id=EventTestDataGenerator._get_next_event_id(),
            user_id=user_id,
            old_status=old_status,
            new_status=new_status,
            plan_type=plan_type,
            changed_by="test_system"
        )

    @staticmethod
    def generate_system_health_event(component: str = "event_bus", status: str = "healthy") -> SystemHealthEvent:
        """Generate system health event for testing"""
        return SystemHealthEvent(
            event_id=EventTestDataGenerator._get_next_event_id(),
            component=component,
            status=status,
            details={
                "response_time_ms": 25.5,
                "memory_usage_mb": 128.7,
                "active_connections": 15
            }
        )

    @staticmethod
    def generate_event_batch(count: int = 10, event_types: List[str] = None) -> List[BaseEvent]:
        """Generate a batch of mixed test events"""
        if event_types is None:
            event_types = ["user_interaction", "reaction_detected", "decision_made", "subscription_updated"]

        events = []
        user_id = EventTestDataGenerator._get_next_user_id()

        for i in range(count):
            event_type = event_types[i % len(event_types)]

            if event_type == "user_interaction":
                event = EventTestDataGenerator.generate_user_interaction_event(user_id)
            elif event_type == "reaction_detected":
                event = EventTestDataGenerator.generate_reaction_event(user_id)
            elif event_type == "decision_made":
                event = EventTestDataGenerator.generate_decision_event(user_id)
            elif event_type == "subscription_updated":
                event = EventTestDataGenerator.generate_subscription_event(user_id)
            else:
                # Default to user interaction
                event = EventTestDataGenerator.generate_user_interaction_event(user_id)

            events.append(event)

        return events


class EventBusTestHelpers:
    """
    Helper methods for event bus testing

    Provides utility methods for common event bus testing operations,
    validation, and test scenario setup.
    """

    def __init__(self, test_bus_manager: TestEventBusManager):
        self.test_bus_manager = test_bus_manager
        self.logger = get_logger(self.__class__.__name__)
        self.captured_events = []
        self.event_handlers = {}

    async def publish_test_events(self, event_bus: EventBus, events: List[BaseEvent],
                                 channel: str = "events") -> Dict[str, Any]:
        """
        Publish a list of events and return results

        Args:
            event_bus: The event bus to publish to
            events: List of events to publish
            channel: Channel to publish to

        Returns:
            Dictionary with publication results
        """
        results = {
            'total_events': len(events),
            'successful_publishes': 0,
            'failed_publishes': 0,
            'publish_times': [],
            'errors': []
        }

        for event in events:
            try:
                start_time = asyncio.get_event_loop().time()
                success = await event_bus.publish(event, channel)
                end_time = asyncio.get_event_loop().time()

                publish_time_ms = (end_time - start_time) * 1000
                results['publish_times'].append(publish_time_ms)

                if success:
                    results['successful_publishes'] += 1
                else:
                    results['failed_publishes'] += 1

            except Exception as e:
                results['failed_publishes'] += 1
                results['errors'].append(str(e))
                self.logger.error(f"Error publishing event {event.event_id}: {e}")

        return results

    async def verify_event_reliability(self, event_bus: EventBus, event: BaseEvent,
                                     max_retries: int = 3) -> Dict[str, Any]:
        """
        Verify event publication reliability by testing retries

        Args:
            event_bus: The event bus to test
            event: Event to publish
            max_retries: Maximum number of retries to test

        Returns:
            Dictionary with reliability test results
        """
        results = {
            'event_id': event.event_id,
            'retry_attempts': 0,
            'final_success': False,
            'retry_times': [],
            'errors': []
        }

        for attempt in range(max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()
                success = await event_bus.publish(event)
                end_time = asyncio.get_event_loop().time()

                retry_time_ms = (end_time - start_time) * 1000
                results['retry_times'].append(retry_time_ms)

                if success:
                    results['final_success'] = True
                    results['retry_attempts'] = attempt
                    break
                else:
                    results['retry_attempts'] = attempt + 1

            except Exception as e:
                results['retry_attempts'] = attempt + 1
                results['errors'].append(str(e))

                # If this is the last attempt, record failure
                if attempt == max_retries:
                    results['final_success'] = False

        return results

    async def test_event_ordering(self, event_bus: EventBus, events: List[BaseEvent]) -> Dict[str, Any]:
        """
        Test event ordering by publishing events in sequence

        Args:
            event_bus: The event bus to test
            events: List of events to publish in order

        Returns:
            Dictionary with ordering test results
        """
        results = {
            'expected_order': [e.event_id for e in events],
            'actual_order': [],
            'ordering_preserved': False,
            'publish_results': []
        }

        # Capture published events
        captured_events = []

        # Mock Redis client to capture published events
        if hasattr(event_bus.redis_client, 'published_messages'):
            original_publish = event_bus.redis_client.publish

            async def capture_publish(channel, data):
                result = await original_publish(channel, data)
                event_data = json.loads(data)
                captured_events.append(event_data['event_id'])
                return result

            event_bus.redis_client.publish = capture_publish

        # Publish events
        for event in events:
            success = await event_bus.publish(event)
            results['publish_results'].append(success)

        results['actual_order'] = captured_events
        results['ordering_preserved'] = (results['expected_order'] == results['actual_order'])

        return results

    def create_event_handler(self, handler_name: str) -> Callable:
        """
        Create a test event handler that captures received events

        Args:
            handler_name: Name for the handler

        Returns:
            Event handler function
        """
        def handler(event_data: str):
            try:
                event_dict = json.loads(event_data)
                self.captured_events.append({
                    'handler': handler_name,
                    'event_data': event_dict,
                    'timestamp': datetime.utcnow()
                })
                self.logger.debug(f"Handler {handler_name} received event: {event_dict.get('event_id')}")
            except Exception as e:
                self.logger.error(f"Error in handler {handler_name}: {e}")

        self.event_handlers[handler_name] = handler
        return handler

    async def wait_for_events(self, expected_count: int, timeout: float = 5.0) -> bool:
        """
        Wait for expected number of events to be received

        Args:
            expected_count: Expected number of events
            timeout: Timeout in seconds

        Returns:
            True if expected events received, False if timeout
        """
        start_time = asyncio.get_event_loop().time()

        while len(self.captured_events) < expected_count:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                return False
            await asyncio.sleep(0.1)

        return True

    def get_captured_events(self, handler_name: str = None) -> List[Dict[str, Any]]:
        """
        Get events captured by handlers

        Args:
            handler_name: Optional filter by handler name

        Returns:
            List of captured events
        """
        if handler_name:
            return [e for e in self.captured_events if e['handler'] == handler_name]
        return self.captured_events.copy()

    def clear_captured_events(self):
        """Clear all captured events"""
        self.captured_events.clear()

    async def verify_local_queue_behavior(self, event_bus: EventBus, test_events: List[BaseEvent]) -> Dict[str, Any]:
        """
        Verify local queue behavior when Redis is unavailable

        Args:
            event_bus: The event bus to test
            test_events: Events to test with

        Returns:
            Dictionary with local queue test results
        """
        results = {
            'events_queued_locally': 0,
            'queue_size_before': await event_bus.local_queue.size(),
            'queue_size_after': 0,
            'redis_unavailable_handled': False
        }

        # Force Redis to be unavailable
        if hasattr(event_bus.redis_client, 'fail_on_publish'):
            event_bus.redis_client.fail_on_publish = True
            event_bus._connected = False

        # Publish events (should go to local queue)
        for event in test_events:
            success = await event_bus.publish(event)
            if success:
                results['events_queued_locally'] += 1

        results['queue_size_after'] = await event_bus.local_queue.size()
        results['redis_unavailable_handled'] = results['events_queued_locally'] > 0

        return results


class EventBusPerformanceTestHelper:
    """
    Helper for performance testing event bus operations

    Provides methods to measure event bus performance and validate
    against requirements from the design document.
    """

    @staticmethod
    async def measure_event_publication_latency(event_bus: EventBus, event: BaseEvent) -> float:
        """
        Measure single event publication latency

        Args:
            event_bus: The event bus to test
            event: Event to publish

        Returns:
            Publication latency in milliseconds
        """
        start_time = asyncio.get_event_loop().time()
        await event_bus.publish(event)
        end_time = asyncio.get_event_loop().time()

        return (end_time - start_time) * 1000

    @staticmethod
    async def measure_bulk_publication_performance(event_bus: EventBus, events: List[BaseEvent]) -> Dict[str, float]:
        """
        Measure bulk event publication performance

        Args:
            event_bus: The event bus to test
            events: List of events to publish

        Returns:
            Performance metrics dictionary
        """
        publication_times = []

        total_start_time = asyncio.get_event_loop().time()

        for event in events:
            start_time = asyncio.get_event_loop().time()
            await event_bus.publish(event)
            end_time = asyncio.get_event_loop().time()

            publication_time_ms = (end_time - start_time) * 1000
            publication_times.append(publication_time_ms)

        total_end_time = asyncio.get_event_loop().time()
        total_time_ms = (total_end_time - total_start_time) * 1000

        return {
            'total_time_ms': total_time_ms,
            'average_time_ms': sum(publication_times) / len(publication_times),
            'max_time_ms': max(publication_times),
            'min_time_ms': min(publication_times),
            'events_per_second': len(events) / (total_time_ms / 1000),
            'individual_times_ms': publication_times
        }

    @staticmethod
    def validate_performance_requirement(measured_time_ms: float, requirement_ms: float = 10.0) -> bool:
        """
        Validate that measured time meets performance requirement

        Args:
            measured_time_ms: Measured time in milliseconds
            requirement_ms: Required maximum time in milliseconds

        Returns:
            True if requirement is met, False otherwise
        """
        return measured_time_ms <= requirement_ms


# Pytest fixtures following patterns from conftest.py and database.py

@pytest.fixture
async def test_event_bus_manager():
    """Fixture for test event bus manager setup and cleanup"""
    manager = TestEventBusManager()
    yield manager
    await manager.cleanup()


@pytest.fixture
async def test_event_bus(test_event_bus_manager):
    """Fixture for a basic test event bus"""
    return await test_event_bus_manager.create_test_event_bus()


@pytest.fixture
async def failing_redis_event_bus(test_event_bus_manager):
    """Fixture for event bus with failing Redis connection"""
    return await test_event_bus_manager.create_test_event_bus(redis_fail_on_connect=True)


@pytest.fixture
async def unreliable_redis_event_bus(test_event_bus_manager):
    """Fixture for event bus with unreliable Redis (fails on publish)"""
    return await test_event_bus_manager.create_test_event_bus(redis_fail_on_publish=True)


@pytest.fixture
def event_test_helpers(test_event_bus_manager):
    """Fixture for event bus test helpers"""
    return EventBusTestHelpers(test_event_bus_manager)


@pytest.fixture
def event_data_generator():
    """Fixture for event test data generator"""
    return EventTestDataGenerator()


@pytest.fixture
def performance_helper():
    """Fixture for event bus performance testing"""
    return EventBusPerformanceTestHelper()


@pytest.fixture
def sample_test_events(event_data_generator):
    """Generate sample test events for testing"""
    user_id = "123456789"
    return {
        "user_interaction": event_data_generator.generate_user_interaction_event(user_id),
        "user_registration": event_data_generator.generate_user_registration_event(user_id),
        "reaction": event_data_generator.generate_reaction_event(user_id, "content_001", "besito"),
        "decision": event_data_generator.generate_decision_event(user_id, "fragment_001", "choice_a"),
        "subscription": event_data_generator.generate_subscription_event(user_id, "inactive", "active"),
        "system_health": event_data_generator.generate_system_health_event("event_bus", "healthy")
    }


@pytest.fixture
def event_batch(event_data_generator):
    """Generate batch of test events for bulk testing"""
    return event_data_generator.generate_event_batch(count=20)


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for unit testing"""
    mock_redis = MockRedisClient()
    return mock_redis


# Test scenarios for comprehensive event bus testing

@pytest.fixture
def event_test_scenarios():
    """Predefined test scenarios for event bus testing"""
    scenarios = {
        "basic_publication": EventTestScenario(
            name="Basic Event Publication",
            events=[
                EventTestDataGenerator.generate_user_interaction_event(),
                EventTestDataGenerator.generate_reaction_event()
            ],
            expected_outcomes={"published_successfully": True, "events_count": 2},
            performance_requirements={"max_publication_time_ms": 10.0}
        ),

        "redis_failure_recovery": EventTestScenario(
            name="Redis Failure and Recovery",
            events=[EventTestDataGenerator.generate_decision_event()],
            error_conditions=["redis_connection_failed"],
            expected_outcomes={"local_queue_used": True, "event_persisted": True},
            performance_requirements={"max_fallback_time_ms": 50.0}
        ),

        "high_volume_load": EventTestScenario(
            name="High Volume Event Load",
            events=EventTestDataGenerator.generate_event_batch(count=100),
            expected_outcomes={"all_events_published": True, "no_events_lost": True},
            performance_requirements={
                "max_avg_publication_time_ms": 5.0,
                "min_events_per_second": 100
            }
        ),

        "event_ordering": EventTestScenario(
            name="Event Ordering Preservation",
            events=EventTestDataGenerator.generate_event_batch(count=10),
            expected_outcomes={"order_preserved": True, "no_race_conditions": True},
            performance_requirements={"max_ordering_deviation_ms": 1.0}
        )
    }

    return scenarios


@pytest.fixture
def api_client(populated_test_database):
    """Create a test client for the API"""
    from src.api.server import create_api_server
    from fastapi.testclient import TestClient
    from src.database.manager import DatabaseManager
    from src.events.bus import EventBus

    # Create mock dependencies
    db_manager = MagicMock(spec=DatabaseManager)
    event_bus = MagicMock(spec=EventBus)

    # Setup database mocks
    db_data = populated_test_database
    test_user = db_data["users"][0] if db_data["users"] else None

    if test_user:
        db_manager.get_user_from_mongo = AsyncMock(return_value=test_user["mongo_doc"])
        db_manager.get_user_profile_from_sqlite = AsyncMock(return_value=test_user["sqlite_profile"])
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)

    # Create the API with dependencies
    app = create_api_server(database_manager=db_manager, event_bus=event_bus)

    # Create test client
    client = TestClient(app)
    return client, db_manager, None # Return None for user_service



@pytest.fixture
def populated_test_database(real_sqlite_db, sample_mongo_user, sample_sqlite_profile):
    """
    Populate the database with some initial data for integration tests.
    """
    db_manager = real_sqlite_db
    user_id = sample_sqlite_profile["user_id"]

    # Mock MongoDB methods
    db_manager.get_user_from_mongo = AsyncMock(return_value=sample_mongo_user)
    db_manager.get_user_profile_from_sqlite = AsyncMock(return_value=sample_sqlite_profile)
    db_manager.create_user_atomic = AsyncMock(return_value=True)
    db_manager.update_user_in_mongo = AsyncMock(return_value=True)
    db_manager.update_user_profile_in_sqlite = AsyncMock(return_value=True)
    db_manager.get_subscription_from_sqlite = AsyncMock(return_value=None)
    db_manager.delete_user_from_mongo = AsyncMock(return_value=True)
    db_manager.delete_user_profile_from_sqlite = AsyncMock(return_value=True)

    return {
        "database": db_manager,
        "users": [
            {
                "user_id": user_id,
                "mongo_doc": sample_mongo_user,
                "sqlite_profile": sample_sqlite_profile,
                "telegram_data": {
                    "id": int(user_id),
                    "username": "test_user",
                    "first_name": "Test",
                    "last_name": "User",
                    "language_code": "en",
                },
            }
        ],
        "helpers": None,  # No helpers for now
    }

