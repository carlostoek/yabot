"""
Test configuration for the Telegram bot framework.
"""

import os
import sys
import pytest
from unittest.mock import Mock, AsyncMock
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load environment variables
load_dotenv()


@pytest.fixture
def mock_config_manager():
    """Create a mock configuration manager for testing."""
    mock_config = Mock()
    mock_config.get_bot_token.return_value = "test_bot_token"
    mock_config.validate_config.return_value = True
    return mock_config


@pytest.fixture
def mock_router():
    """Create a mock router for testing."""
    mock_router = Mock()
    mock_router.route_update = AsyncMock()
    return mock_router


@pytest.fixture
def mock_middleware_manager():
    """Create a mock middleware manager for testing."""
    mock_middleware = Mock()
    mock_middleware.process_request = AsyncMock()
    mock_middleware.process_response = AsyncMock()
    return mock_middleware


@pytest.fixture
def mock_error_handler():
    """Create a mock error handler for testing."""
    mock_handler = Mock()
    mock_handler.handle_error = AsyncMock()
    return mock_handler


@pytest.fixture
def mock_command_handler():
    """Create a mock command handler for testing."""
    mock_handler = Mock()
    mock_handler.handle_start = AsyncMock()
    mock_handler.handle_menu = AsyncMock()
    mock_handler.handle_help = AsyncMock()
    mock_handler.handle_unknown = AsyncMock()
    return mock_handler


@pytest.fixture
def mock_webhook_handler():
    """Create a mock webhook handler for testing."""
    mock_handler = Mock()
    mock_handler.setup_webhook.return_value = True
    mock_handler.validate_request.return_value = True
    mock_handler.process_update = AsyncMock()
    return mock_handler


@pytest.fixture
def mock_database_manager():
    """Create a mock database manager for testing."""
    from tests.utils.database import MockDatabaseManager
    return MockDatabaseManager()


@pytest.fixture
def database_test_config():
    """Create a database test configuration for testing."""
    from tests.utils.database import DatabaseTestConfig
    return DatabaseTestConfig


@pytest.fixture
def database_test_data_factory():
    """Create a database test data factory for testing."""
    from tests.utils.database import DatabaseTestDataFactory
    return DatabaseTestDataFactory()


@pytest.fixture
def database_test_helpers():
    """Create database test helpers for testing."""
    from tests.utils.database import DatabaseTestHelpers
    return DatabaseTestHelpers()


@pytest.fixture
def temp_database_path(tmp_path):
    """Create a temporary database path for testing."""
    return str(tmp_path / "test_database.db")


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    from tests.utils.events import MockEventBus
    return MockEventBus()


@pytest.fixture
def event_test_config():
    """Create an event test configuration for testing."""
    from tests.utils.events import EventTestConfig
    return EventTestConfig


@pytest.fixture
def event_test_data_factory():
    """Create an event test data factory for testing."""
    from tests.utils.events import EventTestDataFactory
    return EventTestDataFactory()


@pytest.fixture
def event_test_helpers():
    """Create event test helpers for testing."""
    from tests.utils.events import EventTestHelpers
    return EventTestHelpers()


@pytest.fixture
def sample_update():
    """Create a sample update for testing."""
    update = Mock()
    update.message = Mock()
    update.message.text = "/start"
    return update


@pytest.fixture
def sample_message():
    """Create a sample message for testing."""
    message = Mock()
    message.text = "Hello, bot!"
    return message


@pytest.fixture
def sample_command_response():
    """Create a sample command response for testing."""
    from src.core.models import CommandResponse
    return CommandResponse(
        text="Test response",
        parse_mode="HTML"
    )