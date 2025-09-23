"""
Database test utilities for the YABOT system.

This module provides utilities for testing database-related functionality,
including mock database managers, test data factories, and helper functions
for database testing as required by the fase1 specification testing strategy.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Any, Dict, Optional

from src.database.manager import DatabaseManager
from src.config.manager import ConfigManager
from src.services.user import UserService
from src.services.subscription import SubscriptionService
from src.services.narrative import NarrativeService
from src.events.bus import EventBus


class MockDatabaseManager:
    """Mock database manager for testing database-related functionality."""
    
    def __init__(self):
        """Initialize the mock database manager."""
        self._is_connected = False
        self._mongo_client = None
        self._sqlite_conn = None
        self._mongo_db_name = "test_db"
        
        # Mock database collections/tables
        self._mock_mongo_collections = {}
        self._mock_sqlite_tables = {}
        
        # Track method calls for testing
        self._method_calls = []
    
    async def connect_all(self) -> bool:
        """Mock connect all databases.
        
        Returns:
            bool: True indicating successful connection
        """
        self._method_calls.append("connect_all")
        self._is_connected = True
        return True
    
    def get_mongo_db(self):
        """Mock get MongoDB database.
        
        Returns:
            dict: Mock MongoDB database
        """
        self._method_calls.append("get_mongo_db")
        if not self._is_connected:
            raise ValueError("MongoDB is not connected")
        
        # Return a mock database object
        mock_db = MagicMock()
        mock_db.name = self._mongo_db_name
        
        # Mock collection access
        def get_collection(name):
            if name not in self._mock_mongo_collections:
                self._mock_mongo_collections[name] = MagicMock()
                self._mock_mongo_collections[name].name = name
            return self._mock_mongo_collections[name]
        
        mock_db.__getitem__.side_effect = get_collection
        return mock_db
    
    def get_sqlite_conn(self):
        """Mock get SQLite connection.
        
        Returns:
            MagicMock: Mock SQLite connection
        """
        self._method_calls.append("get_sqlite_conn")
        if not self._is_connected:
            raise ValueError("SQLite is not connected")
        return MagicMock()
    
    async def health_check(self) -> Dict[str, bool]:
        """Mock database health check.
        
        Returns:
            Dict[str, bool]: Health status for each database
        """
        self._method_calls.append("health_check")
        return {
            "mongodb": True,
            "sqlite": True
        }
    
    async def close_all(self) -> None:
        """Mock close all database connections."""
        self._method_calls.append("close_all")
        self._is_connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if databases are connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self._is_connected
    
    @property
    def method_calls(self) -> list:
        """Get list of method calls made on this mock.
        
        Returns:
            list: List of method calls
        """
        return self._method_calls.copy()


class DatabaseTestConfig:
    """Configuration utilities for database testing."""
    
    @staticmethod
    def create_test_config_manager(
        mongodb_uri: str = "mongodb://localhost:27017",
        mongodb_database: str = "test_db",
        sqlite_database_path: str = ":memory:"
    ) -> ConfigManager:
        """Create a test configuration manager with database settings.
        
        Args:
            mongodb_uri (str): MongoDB connection URI
            mongodb_database (str): MongoDB database name
            sqlite_database_path (str): SQLite database path
            
        Returns:
            ConfigManager: Test configuration manager
        """
        # Create a mock config manager
        mock_config = Mock(spec=ConfigManager)
        
        # Mock the get_database_config method
        def mock_get_database_config():
            mock_db_config = Mock()
            mock_db_config.mongodb_uri = mongodb_uri
            mock_db_config.mongodb_database = mongodb_database
            mock_db_config.sqlite_database_path = sqlite_database_path
            return mock_db_config
        
        mock_config.get_database_config = mock_get_database_config
        return mock_config
    
    @staticmethod
    def set_test_env_vars(
        mongodb_uri: str = "mongodb://localhost:27017",
        mongodb_database: str = "test_db",
        sqlite_database_path: str = ":memory:"
    ) -> Dict[str, str]:
        """Set environment variables for database testing.
        
        Args:
            mongodb_uri (str): MongoDB connection URI
            mongodb_database (str): MongoDB database name
            sqlite_database_path (str): SQLite database path
            
        Returns:
            Dict[str, str]: Original environment variables that were overridden
        """
        original_vars = {}
        
        # Store original values
        if "MONGODB_URI" in os.environ:
            original_vars["MONGODB_URI"] = os.environ["MONGODB_URI"]
        if "MONGODB_DATABASE" in os.environ:
            original_vars["MONGODB_DATABASE"] = os.environ["MONGODB_DATABASE"]
        if "SQLITE_DATABASE_PATH" in os.environ:
            original_vars["SQLITE_DATABASE_PATH"] = os.environ["SQLITE_DATABASE_PATH"]
        
        # Set test values
        os.environ["MONGODB_URI"] = mongodb_uri
        os.environ["MONGODB_DATABASE"] = mongodb_database
        os.environ["SQLITE_DATABASE_PATH"] = sqlite_database_path
        
        return original_vars
    
    @staticmethod
    def restore_env_vars(original_vars: Dict[str, str]) -> None:
        """Restore original environment variables.
        
        Args:
            original_vars (Dict[str, str]): Original environment variables
        """
        # Remove test values first
        for var in ["MONGODB_URI", "MONGODB_DATABASE", "SQLITE_DATABASE_PATH"]:
            if var in os.environ:
                del os.environ[var]
        
        # Restore original values
        for var, value in original_vars.items():
            os.environ[var] = value


class DatabaseTestDataFactory:
    """Factory for creating database test data."""
    
    @staticmethod
    def create_test_user_data(
        user_id: str = "test_user_123",
        telegram_user_id: int = 123456789,
        username: str = "testuser",
        first_name: str = "Test",
        last_name: str = "User"
    ) -> Dict[str, Any]:
        """Create test user data for both MongoDB and SQLite.
        
        Args:
            user_id (str): User ID
            telegram_user_id (int): Telegram user ID
            username (str): Username
            first_name (str): First name
            last_name (str): Last name
            
        Returns:
            Dict[str, Any]: Complete user data for both databases
        """
        return {
            "user_id": user_id,
            "telegram_user_id": telegram_user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": "en",
            "registration_date": "2025-01-01T00:00:00Z",
            "last_login": "2025-01-01T00:00:00Z",
            "is_active": True,
            "preferences": {
                "language": "en",
                "notifications_enabled": True,
                "theme": "default"
            },
            "current_state": {
                "menu_context": "main_menu",
                "narrative_progress": {
                    "current_fragment": "fragment_001",
                    "completed_fragments": [],
                    "choices_made": []
                },
                "session_data": {
                    "last_activity": "2025-01-01T00:00:00Z"
                }
            }
        }
    
    @staticmethod
    def create_test_subscription_data(
        user_id: str = "test_user_123",
        plan_type: str = "premium",
        status: str = "active"
    ) -> Dict[str, Any]:
        """Create test subscription data.
        
        Args:
            user_id (str): User ID
            plan_type (str): Subscription plan type
            status (str): Subscription status
            
        Returns:
            Dict[str, Any]: Subscription data
        """
        return {
            "user_id": user_id,
            "plan_type": plan_type,
            "status": status,
            "start_date": "2025-01-01T00:00:00Z",
            "end_date": "2026-01-01T00:00:00Z",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z"
        }
    
    @staticmethod
    def create_test_narrative_fragment(
        fragment_id: str = "fragment_001",
        title: str = "Test Fragment",
        content: str = "This is a test narrative fragment."
    ) -> Dict[str, Any]:
        """Create test narrative fragment data.
        
        Args:
            fragment_id (str): Fragment ID
            title (str): Fragment title
            content (str): Fragment content
            
        Returns:
            Dict[str, Any]: Narrative fragment data
        """
        return {
            "fragment_id": fragment_id,
            "title": title,
            "content": content,
            "choices": [
                {
                    "id": "choice_a",
                    "text": "Choice A",
                    "next_fragment": "fragment_002"
                }
            ],
            "metadata": {
                "difficulty": "easy",
                "tags": ["test"],
                "vip_required": False
            },
            "created_at": "2025-01-01T00:00:00Z"
        }


class DatabaseTestHelpers:
    """Helper functions for database testing."""
    
    @staticmethod
    async def create_test_database_manager(
        config_manager: Optional[ConfigManager] = None
    ) -> DatabaseManager:
        """Create a database manager for testing.
        
        Args:
            config_manager (ConfigManager, optional): Configuration manager
            
        Returns:
            DatabaseManager: Database manager instance
        """
        db_manager = DatabaseManager(config_manager)
        return db_manager
    
    @staticmethod
    async def create_test_services(
        database_manager: DatabaseManager,
        event_bus: Optional[EventBus] = None
    ) -> tuple:
        """Create test service instances.
        
        Args:
            database_manager (DatabaseManager): Database manager
            event_bus (EventBus, optional): Event bus
            
        Returns:
            tuple: (UserService, SubscriptionService, NarrativeService)
        """
        # Create mock event bus if not provided
        if event_bus is None:
            event_bus = Mock(spec=EventBus)
            event_bus.publish = AsyncMock()
        
        # Create services
        user_service = UserService(database_manager, event_bus)
        subscription_service = SubscriptionService(database_manager)
        narrative_service = NarrativeService(database_manager, subscription_service, event_bus)
        
        return user_service, subscription_service, narrative_service
    
    @staticmethod
    def create_temp_database_path() -> str:
        """Create a temporary database path for testing.
        
        Returns:
            str: Path to temporary database file
        """
        temp_dir = tempfile.mkdtemp()
        return os.path.join(temp_dir, "test.db")


# Pytest fixtures for database testing
@pytest.fixture
def mock_database_manager():
    """Create a mock database manager for testing.
    
    Returns:
        MockDatabaseManager: Mock database manager
    """
    return MockDatabaseManager()


@pytest.fixture
def database_test_config():
    """Create database test configuration utilities.
    
    Returns:
        DatabaseTestConfig: Database test configuration utilities
    """
    return DatabaseTestConfig()


@pytest.fixture
def database_test_data_factory():
    """Create database test data factory.
    
    Returns:
        DatabaseTestDataFactory: Database test data factory
    """
    return DatabaseTestDataFactory()


@pytest.fixture
def database_test_helpers():
    """Create database test helpers.
    
    Returns:
        DatabaseTestHelpers: Database test helpers
    """
    return DatabaseTestHelpers()


@pytest.fixture
def temp_database_path():
    """Create a temporary database path for testing.
    
    Returns:
        str: Path to temporary database file
    """
    return DatabaseTestHelpers.create_temp_database_path()


# Context manager for database testing
class DatabaseTestContext:
    """Context manager for database testing with proper setup and teardown."""
    
    def __init__(self):
        """Initialize the database test context."""
        self.original_env_vars = {}
        self.temp_dir = None
        self.temp_db_path = None
    
    def __enter__(self):
        """Enter the database test context."""
        # Set up temporary database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_db_path = os.path.join(self.temp_dir.name, "test.db")
        
        # Set test environment variables
        self.original_env_vars = DatabaseTestConfig.set_test_env_vars(
            mongodb_uri="mongodb://localhost:27017",
            mongodb_database="test_db",
            sqlite_database_path=self.temp_db_path
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the database test context."""
        # Restore original environment variables
        DatabaseTestConfig.restore_env_vars(self.original_env_vars)
        
        # Clean up temporary directory
        if self.temp_dir:
            self.temp_dir.cleanup()