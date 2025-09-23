"""
Tests for the database test utilities.
"""

import os
import pytest
from unittest.mock import Mock

from tests.utils.database import (
    MockDatabaseManager, 
    DatabaseTestConfig, 
    DatabaseTestDataFactory, 
    DatabaseTestHelpers,
    DatabaseTestContext
)
from src.database.manager import DatabaseManager
from src.config.manager import ConfigManager


class TestMockDatabaseManager:
    """Test cases for the MockDatabaseManager class."""
    
    def test_init(self):
        """Test MockDatabaseManager initialization."""
        mock_db = MockDatabaseManager()
        assert mock_db.is_connected is False
        assert len(mock_db.method_calls) == 0
    
    @pytest.mark.asyncio
    async def test_connect_all(self):
        """Test connect_all method."""
        mock_db = MockDatabaseManager()
        result = await mock_db.connect_all()
        assert result is True
        assert mock_db.is_connected is True
        assert "connect_all" in mock_db.method_calls
    
    def test_get_mongo_db_when_connected(self):
        """Test get_mongo_db when connected."""
        mock_db = MockDatabaseManager()
        mock_db._is_connected = True
        
        mongo_db = mock_db.get_mongo_db()
        assert mongo_db is not None
        assert "get_mongo_db" in mock_db.method_calls
    
    def test_get_mongo_db_when_not_connected(self):
        """Test get_mongo_db when not connected."""
        mock_db = MockDatabaseManager()
        
        with pytest.raises(ValueError, match="MongoDB is not connected"):
            mock_db.get_mongo_db()
    
    def test_get_sqlite_conn_when_connected(self):
        """Test get_sqlite_conn when connected."""
        mock_db = MockDatabaseManager()
        mock_db._is_connected = True
        
        sqlite_conn = mock_db.get_sqlite_conn()
        assert sqlite_conn is not None
        assert "get_sqlite_conn" in mock_db.method_calls
    
    def test_get_sqlite_conn_when_not_connected(self):
        """Test get_sqlite_conn when not connected."""
        mock_db = MockDatabaseManager()
        
        with pytest.raises(ValueError, match="SQLite is not connected"):
            mock_db.get_sqlite_conn()
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health_check method."""
        mock_db = MockDatabaseManager()
        result = await mock_db.health_check()
        
        assert isinstance(result, dict)
        assert result["mongodb"] is True
        assert result["sqlite"] is True
        assert "health_check" in mock_db.method_calls
    
    @pytest.mark.asyncio
    async def test_close_all(self):
        """Test close_all method."""
        mock_db = MockDatabaseManager()
        mock_db._is_connected = True
        
        await mock_db.close_all()
        assert mock_db.is_connected is False
        assert "close_all" in mock_db.method_calls


class TestDatabaseTestConfig:
    """Test cases for the DatabaseTestConfig class."""
    
    def test_create_test_config_manager(self):
        """Test create_test_config_manager method."""
        config_manager = DatabaseTestConfig.create_test_config_manager()
        
        # Verify it's a mock with the expected method
        db_config = config_manager.get_database_config()
        assert db_config.mongodb_uri == "mongodb://localhost:27017"
        assert db_config.mongodb_database == "test_db"
        assert db_config.sqlite_database_path == ":memory:"
    
    def test_set_test_env_vars(self):
        """Test set_test_env_vars method."""
        # Store original values if they exist
        original_mongo_uri = os.environ.get("MONGODB_URI")
        original_mongo_db = os.environ.get("MONGODB_DATABASE")
        original_sqlite_path = os.environ.get("SQLITE_DATABASE_PATH")
        
        # Set test values
        original_vars = DatabaseTestConfig.set_test_env_vars(
            mongodb_uri="test_mongo_uri",
            mongodb_database="test_mongo_db",
            sqlite_database_path="test_sqlite_path"
        )
        
        # Verify environment variables are set
        assert os.environ["MONGODB_URI"] == "test_mongo_uri"
        assert os.environ["MONGODB_DATABASE"] == "test_mongo_db"
        assert os.environ["SQLITE_DATABASE_PATH"] == "test_sqlite_path"
        
        # Restore original values
        DatabaseTestConfig.restore_env_vars(original_vars)
        
        # Verify they're restored
        if original_mongo_uri:
            assert os.environ["MONGODB_URI"] == original_mongo_uri
        elif "MONGODB_URI" in os.environ:
            del os.environ["MONGODB_URI"]
            
        if original_mongo_db:
            assert os.environ["MONGODB_DATABASE"] == original_mongo_db
        elif "MONGODB_DATABASE" in os.environ:
            del os.environ["MONGODB_DATABASE"]
            
        if original_sqlite_path:
            assert os.environ["SQLITE_DATABASE_PATH"] == original_sqlite_path
        elif "SQLITE_DATABASE_PATH" in os.environ:
            del os.environ["SQLITE_DATABASE_PATH"]
    
    def test_restore_env_vars(self):
        """Test restore_env_vars method."""
        # Set some test values
        os.environ["MONGODB_URI"] = "test_value"
        os.environ["MONGODB_DATABASE"] = "test_value"
        os.environ["SQLITE_DATABASE_PATH"] = "test_value"
        
        # Restore empty dict (should clear test values)
        DatabaseTestConfig.restore_env_vars({})
        
        # Values should be removed
        assert "MONGODB_URI" not in os.environ
        assert "MONGODB_DATABASE" not in os.environ
        assert "SQLITE_DATABASE_PATH" not in os.environ


class TestDatabaseTestDataFactory:
    """Test cases for the DatabaseTestDataFactory class."""
    
    def test_create_test_user_data(self):
        """Test create_test_user_data method."""
        user_data = DatabaseTestDataFactory.create_test_user_data()
        
        assert user_data["user_id"] == "test_user_123"
        assert user_data["telegram_user_id"] == 123456789
        assert user_data["username"] == "testuser"
        assert user_data["first_name"] == "Test"
        assert user_data["last_name"] == "User"
        assert "preferences" in user_data
        assert "current_state" in user_data
    
    def test_create_test_subscription_data(self):
        """Test create_test_subscription_data method."""
        subscription_data = DatabaseTestDataFactory.create_test_subscription_data()
        
        assert subscription_data["user_id"] == "test_user_123"
        assert subscription_data["plan_type"] == "premium"
        assert subscription_data["status"] == "active"
    
    def test_create_test_narrative_fragment(self):
        """Test create_test_narrative_fragment method."""
        fragment_data = DatabaseTestDataFactory.create_test_narrative_fragment()
        
        assert fragment_data["fragment_id"] == "fragment_001"
        assert fragment_data["title"] == "Test Fragment"
        assert fragment_data["content"] == "This is a test narrative fragment."
        assert "choices" in fragment_data
        assert "metadata" in fragment_data


class TestDatabaseTestHelpers:
    """Test cases for the DatabaseTestHelpers class."""
    
    def test_create_temp_database_path(self):
        """Test create_temp_database_path method."""
        db_path = DatabaseTestHelpers.create_temp_database_path()
        assert isinstance(db_path, str)
        assert len(db_path) > 0
        # Clean up the temporary directory
        import os
        import shutil
        temp_dir = os.path.dirname(db_path)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


class TestDatabaseTestContext:
    """Test cases for the DatabaseTestContext class."""
    
    def test_context_manager(self):
        """Test DatabaseTestContext as a context manager."""
        # Store original values if they exist
        original_mongo_uri = os.environ.get("MONGODB_URI")
        original_mongo_db = os.environ.get("MONGODB_DATABASE")
        original_sqlite_path = os.environ.get("SQLITE_DATABASE_PATH")
        
        # Test the context manager
        with DatabaseTestContext() as ctx:
            # Verify environment variables are set
            assert os.environ["MONGODB_URI"] == "mongodb://localhost:27017"
            assert os.environ["MONGODB_DATABASE"] == "test_db"
            assert os.environ["SQLITE_DATABASE_PATH"] == ctx.temp_db_path
        
        # Verify environment variables are restored
        if original_mongo_uri:
            assert os.environ["MONGODB_URI"] == original_mongo_uri
        else:
            assert "MONGODB_URI" not in os.environ
            
        if original_mongo_db:
            assert os.environ["MONGODB_DATABASE"] == original_mongo_db
        else:
            assert "MONGODB_DATABASE" not in os.environ
            
        if original_sqlite_path:
            assert os.environ["SQLITE_DATABASE_PATH"] == original_sqlite_path
        else:
            assert "SQLITE_DATABASE_PATH" not in os.environ


# Test the pytest fixtures
def test_mock_database_manager_fixture(mock_database_manager):
    """Test the mock_database_manager fixture."""
    assert isinstance(mock_database_manager, MockDatabaseManager)


def test_database_test_config_fixture(database_test_config):
    """Test the database_test_config fixture."""
    assert isinstance(database_test_config, type(DatabaseTestConfig))


def test_database_test_data_factory_fixture(database_test_data_factory):
    """Test the database_test_data_factory fixture."""
    assert isinstance(database_test_data_factory, DatabaseTestDataFactory)


def test_database_test_helpers_fixture(database_test_helpers):
    """Test the database_test_helpers fixture."""
    assert isinstance(database_test_helpers, DatabaseTestHelpers)


def test_temp_database_path_fixture(temp_database_path):
    """Test the temp_database_path fixture."""
    assert isinstance(temp_database_path, str)
    assert len(temp_database_path) > 0