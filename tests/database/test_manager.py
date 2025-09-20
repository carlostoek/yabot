"""
Unit tests for the DatabaseManager class.

This module provides comprehensive unit tests for the DatabaseManager class,
implementing the testing requirements specified in fase1 specification section 1.1.
"""

import asyncio
import os
import tempfile
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import sqlite3

from src.database.manager import DatabaseManager
from src.config.manager import ConfigManager
from src.core.models import DatabaseConfig


class TestDatabaseManager:
    """Test cases for the DatabaseManager class."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager for testing."""
        mock_config = Mock(spec=ConfigManager)
        
        # Create a mock database config
        mock_db_config = Mock(spec=DatabaseConfig)
        mock_db_config.mongodb_uri = "mongodb://localhost:27017"
        mock_db_config.mongodb_database = "test_db"
        mock_db_config.sqlite_database_path = ":memory:"
        
        mock_config.get_database_config.return_value = mock_db_config
        return mock_config
    
    @pytest.fixture
    def database_manager(self, mock_config_manager):
        """Create a DatabaseManager instance with mocked configuration."""
        return DatabaseManager(config_manager=mock_config_manager)
    
    def test_init(self, mock_config_manager):
        """Test DatabaseManager initialization."""
        # Test with default config manager
        db_manager = DatabaseManager()
        assert hasattr(db_manager, '_mongo_client')
        assert hasattr(db_manager, '_sqlite_conn')
        assert hasattr(db_manager, '_mongo_db_name')
        assert hasattr(db_manager, '_is_connected')
        assert db_manager._is_connected is False
        assert isinstance(db_manager.config_manager, ConfigManager)
        
        # Test with custom config manager
        db_manager = DatabaseManager(config_manager=mock_config_manager)
        assert db_manager.config_manager == mock_config_manager
    
    def test_is_connected_property(self):
        """Test the is_connected property."""
        db_manager = DatabaseManager()
        assert db_manager.is_connected is False
        
        # Manually set the connected flag
        db_manager._is_connected = True
        assert db_manager.is_connected is True
    
    @pytest.mark.asyncio
    async def test_connect_all_success(self, database_manager, mock_config_manager):
        """Test successful connection to all databases."""
        # Mock the database config
        mock_db_config = Mock()
        mock_db_config.mongodb_uri = "mongodb://localhost:27017"
        mock_db_config.mongodb_database = "test_db"
        mock_db_config.sqlite_database_path = ":memory:"
        mock_config_manager.get_database_config.return_value = mock_db_config
        
        # Mock MongoDB connection
        with patch('src.database.manager.MongoClient') as mock_mongo_client, \
             patch('src.database.manager.sqlite3.connect') as mock_sqlite_connect:
            
            # Mock MongoDB client
            mock_mongo_instance = Mock()
            mock_mongo_instance.admin.command.return_value = True
            mock_mongo_client.return_value = mock_mongo_instance
            
            # Mock SQLite connection
            mock_sqlite_instance = Mock()
            mock_sqlite_instance.execute.return_value = None
            mock_sqlite_connect.return_value = mock_sqlite_instance
            
            # Test connection
            result = await database_manager.connect_all()
            
            # Verify MongoDB connection
            assert mock_mongo_client.called
            assert mock_mongo_instance.admin.command.called
            assert mock_mongo_instance.admin.command.call_args[0][0] == 'ping'
            
            # Verify SQLite connection
            assert mock_sqlite_connect.called
            assert mock_sqlite_instance.execute.called
            
            # Verify result
            assert result is True
            assert database_manager._is_connected is True
            assert database_manager._mongo_db_name == "test_db"
    
    @pytest.mark.asyncio
    async def test_connect_all_mongo_failure(self, database_manager, mock_config_manager):
        """Test connection failure when MongoDB connection fails."""
        # Mock the database config
        mock_db_config = Mock()
        mock_db_config.mongodb_uri = "mongodb://localhost:27017"
        mock_db_config.mongodb_database = "test_db"
        mock_db_config.sqlite_database_path = ":memory:"
        mock_config_manager.get_database_config.return_value = mock_db_config
        
        # Mock MongoDB connection failure
        with patch('src.database.manager.MongoClient') as mock_mongo_client, \
             patch('src.database.manager.sqlite3.connect') as mock_sqlite_connect:
            
            # Mock MongoDB client to raise connection failure
            mock_mongo_client.side_effect = ConnectionFailure("Connection failed")
            
            # Mock SQLite connection (should not be called due to early return)
            mock_sqlite_instance = Mock()
            mock_sqlite_connect.return_value = mock_sqlite_instance
            
            # Test connection
            result = await database_manager.connect_all()
            
            # Verify MongoDB connection was attempted
            assert mock_mongo_client.called
            
            # Verify SQLite connection was not attempted
            assert not mock_sqlite_connect.called
            
            # Verify result
            assert result is False
            assert database_manager._is_connected is False
    
    @pytest.mark.asyncio
    async def test_connect_all_sqlite_failure(self, database_manager, mock_config_manager):
        """Test connection failure when SQLite connection fails."""
        # Mock the database config
        mock_db_config = Mock()
        mock_db_config.mongodb_uri = "mongodb://localhost:27017"
        mock_db_config.mongodb_database = "test_db"
        mock_db_config.sqlite_database_path = ":memory:"
        mock_config_manager.get_database_config.return_value = mock_db_config
        
        # Mock MongoDB connection success but SQLite failure
        with patch('src.database.manager.MongoClient') as mock_mongo_client, \
             patch('src.database.manager.sqlite3.connect') as mock_sqlite_connect:
            
            # Mock successful MongoDB connection
            mock_mongo_instance = Mock()
            mock_mongo_instance.admin.command.return_value = True
            mock_mongo_client.return_value = mock_mongo_instance
            
            # Mock SQLite connection failure
            mock_sqlite_connect.side_effect = sqlite3.Error("SQLite connection failed")
            
            # Test connection
            result = await database_manager.connect_all()
            
            # Verify MongoDB connection was attempted
            assert mock_mongo_client.called
            assert mock_mongo_instance.admin.command.called
            
            # Verify SQLite connection was attempted
            assert mock_sqlite_connect.called
            
            # Verify result
            assert result is False
            assert database_manager._is_connected is False
    
    @pytest.mark.asyncio
    async def test_connect_mongodb_success(self, database_manager):
        """Test successful MongoDB connection."""
        with patch('src.database.manager.MongoClient') as mock_mongo_client:
            # Mock MongoDB client
            mock_mongo_instance = Mock()
            mock_mongo_instance.admin.command.return_value = True
            mock_mongo_client.return_value = mock_mongo_instance
            
            # Test connection
            result = await database_manager._connect_mongodb(
                "mongodb://localhost:27017", "test_db"
            )
            
            # Verify connection
            assert result is True
            assert mock_mongo_client.called
            assert mock_mongo_instance.admin.command.called
            assert mock_mongo_instance.admin.command.call_args[0][0] == 'ping'
    
    @pytest.mark.asyncio
    async def test_connect_mongodb_retry_success(self, database_manager):
        """Test MongoDB connection with retry that eventually succeeds."""
        with patch('src.database.manager.MongoClient') as mock_mongo_client, \
             patch('src.database.manager.asyncio.sleep') as mock_sleep:
            
            # Mock MongoDB client to fail first, then succeed
            mock_mongo_instance_fail = Mock()
            mock_mongo_instance_fail.admin.command.side_effect = ServerSelectionTimeoutError("Timeout")
            
            mock_mongo_instance_success = Mock()
            mock_mongo_instance_success.admin.command.return_value = True
            
            mock_mongo_client.side_effect = [
                mock_mongo_instance_fail,  # First attempt fails
                mock_mongo_instance_success  # Second attempt succeeds
            ]
            
            # Mock sleep to avoid actual delays
            mock_sleep.return_value = None
            
            # Test connection
            result = await database_manager._connect_mongodb(
                "mongodb://localhost:27017", "test_db"
            )
            
            # Verify connection
            assert result is True
            assert mock_mongo_client.call_count == 2  # Two attempts
            assert mock_sleep.called  # Should have slept between retries
    
    @pytest.mark.asyncio
    async def test_connect_mongodb_retry_failure(self, database_manager):
        """Test MongoDB connection with retry that eventually fails."""
        with patch('src.database.manager.MongoClient') as mock_mongo_client, \
             patch('src.database.manager.asyncio.sleep') as mock_sleep:
            
            # Mock MongoDB client to always fail
            mock_mongo_instance = Mock()
            mock_mongo_instance.admin.command.side_effect = ServerSelectionTimeoutError("Timeout")
            mock_mongo_client.return_value = mock_mongo_instance
            
            # Mock sleep to avoid actual delays
            mock_sleep.return_value = None
            
            # Test connection
            result = await database_manager._connect_mongodb(
                "mongodb://localhost:27017", "test_db"
            )
            
            # Verify connection
            assert result is False
            assert mock_mongo_client.call_count == 5  # Max retries (5 attempts)
            assert mock_sleep.call_count == 4  # Slept between each retry
    
    def test_connect_sqlite_success(self, database_manager):
        """Test successful SQLite connection."""
        with patch('src.database.manager.sqlite3.connect') as mock_sqlite_connect:
            # Mock SQLite connection
            mock_sqlite_instance = Mock()
            mock_sqlite_instance.execute.return_value = None
            mock_sqlite_connect.return_value = mock_sqlite_instance
            
            # Test connection
            result = database_manager._connect_sqlite(":memory:")
            
            # Verify connection
            assert result is True
            assert mock_sqlite_connect.called
            assert mock_sqlite_instance.execute.called
    
    def test_connect_sqlite_failure(self, database_manager):
        """Test SQLite connection failure."""
        with patch('src.database.manager.sqlite3.connect') as mock_sqlite_connect:
            # Mock SQLite connection failure
            mock_sqlite_connect.side_effect = sqlite3.Error("Connection failed")
            
            # Test connection
            result = database_manager._connect_sqlite("invalid_path")
            
            # Verify connection
            assert result is False
            assert mock_sqlite_connect.called
    
    def test_get_mongo_db_success(self, database_manager):
        """Test successful MongoDB database retrieval."""
        # Set up mock MongoDB client
        mock_mongo_client = Mock()
        mock_mongo_db = Mock()
        mock_mongo_client.__getitem__.return_value = mock_mongo_db
        database_manager._mongo_client = mock_mongo_client
        database_manager._mongo_db_name = "test_db"
        
        # Test retrieval
        result = database_manager.get_mongo_db()
        
        # Verify result
        assert result == mock_mongo_db
        assert mock_mongo_client.__getitem__.called
        assert mock_mongo_client.__getitem__.call_args[0][0] == "test_db"
    
    def test_get_mongo_db_not_connected(self, database_manager):
        """Test MongoDB database retrieval when not connected."""
        # Ensure MongoDB is not connected
        database_manager._mongo_client = None
        database_manager._mongo_db_name = None
        
        # Test retrieval
        with pytest.raises(ValueError, match="MongoDB is not connected"):
            database_manager.get_mongo_db()
    
    def test_get_sqlite_conn_success(self, database_manager):
        """Test successful SQLite connection retrieval."""
        # Set up mock SQLite connection
        mock_sqlite_conn = Mock()
        database_manager._sqlite_conn = mock_sqlite_conn
        
        # Test retrieval
        result = database_manager.get_sqlite_conn()
        
        # Verify result
        assert result == mock_sqlite_conn
    
    def test_get_sqlite_conn_not_connected(self, database_manager):
        """Test SQLite connection retrieval when not connected."""
        # Ensure SQLite is not connected
        database_manager._sqlite_conn = None
        
        # Test retrieval
        with pytest.raises(ValueError, match="SQLite is not connected"):
            database_manager.get_sqlite_conn()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, database_manager):
        """Test successful health check."""
        # Set up mock MongoDB client
        mock_mongo_client = Mock()
        mock_mongo_client.admin.command.return_value = True
        database_manager._mongo_client = mock_mongo_client
        
        # Set up mock SQLite connection
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.execute.return_value = None
        database_manager._sqlite_conn = mock_sqlite_conn
        
        # Test health check
        result = await database_manager.health_check()
        
        # Verify result
        assert isinstance(result, dict)
        assert "mongodb" in result
        assert "sqlite" in result
        assert result["mongodb"] is True
        assert result["sqlite"] is True
        
        # Verify MongoDB health check
        assert mock_mongo_client.admin.command.called
        assert mock_mongo_client.admin.command.call_args[0][0] == 'ping'
        
        # Verify SQLite health check
        assert mock_sqlite_conn.execute.called
        assert mock_sqlite_conn.execute.call_args[0][0] == "SELECT 1"
    
    @pytest.mark.asyncio
    async def test_health_check_mongo_failure(self, database_manager):
        """Test health check with MongoDB failure."""
        # Set up mock MongoDB client that fails
        mock_mongo_client = Mock()
        mock_mongo_client.admin.command.side_effect = Exception("MongoDB error")
        database_manager._mongo_client = mock_mongo_client
        
        # Set up mock SQLite connection that succeeds
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.execute.return_value = None
        database_manager._sqlite_conn = mock_sqlite_conn
        
        # Test health check
        result = await database_manager.health_check()
        
        # Verify result
        assert isinstance(result, dict)
        assert "mongodb" in result
        assert "sqlite" in result
        assert result["mongodb"] is False
        assert result["sqlite"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_sqlite_failure(self, database_manager):
        """Test health check with SQLite failure."""
        # Set up mock MongoDB client that succeeds
        mock_mongo_client = Mock()
        mock_mongo_client.admin.command.return_value = True
        database_manager._mongo_client = mock_mongo_client
        
        # Set up mock SQLite connection that fails
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.execute.side_effect = Exception("SQLite error")
        database_manager._sqlite_conn = mock_sqlite_conn
        
        # Test health check
        result = await database_manager.health_check()
        
        # Verify result
        assert isinstance(result, dict)
        assert "mongodb" in result
        assert "sqlite" in result
        assert result["mongodb"] is True
        assert result["sqlite"] is False
    
    @pytest.mark.asyncio
    async def test_close_all_success(self, database_manager):
        """Test successful closure of all database connections."""
        # Set up mock MongoDB client
        mock_mongo_client = Mock()
        mock_mongo_client.close.return_value = None
        database_manager._mongo_client = mock_mongo_client
        
        # Set up mock SQLite connection
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.close.return_value = None
        database_manager._sqlite_conn = mock_sqlite_conn
        
        # Test closure
        await database_manager.close_all()
        
        # Verify MongoDB closure
        assert mock_mongo_client.close.called
        
        # Verify SQLite closure
        assert mock_sqlite_conn.close.called
        
        # Verify connected flag is reset
        assert database_manager._is_connected is False
    
    @pytest.mark.asyncio
    async def test_close_all_mongo_failure(self, database_manager):
        """Test closure with MongoDB failure."""
        # Set up mock MongoDB client that fails
        mock_mongo_client = Mock()
        mock_mongo_client.close.side_effect = Exception("MongoDB error")
        database_manager._mongo_client = mock_mongo_client
        
        # Set up mock SQLite connection that succeeds
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.close.return_value = None
        database_manager._sqlite_conn = mock_sqlite_conn
        
        # Test closure (should not raise exception even with MongoDB failure)
        await database_manager.close_all()
        
        # Verify MongoDB closure was attempted
        assert mock_mongo_client.close.called
        
        # Verify SQLite closure was attempted
        assert mock_sqlite_conn.close.called
        
        # Verify connected flag is reset
        assert database_manager._is_connected is False
    
    @pytest.mark.asyncio
    async def test_close_all_sqlite_failure(self, database_manager):
        """Test closure with SQLite failure."""
        # Set up mock MongoDB client that succeeds
        mock_mongo_client = Mock()
        mock_mongo_client.close.return_value = None
        database_manager._mongo_client = mock_mongo_client
        
        # Set up mock SQLite connection that fails
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.close.side_effect = Exception("SQLite error")
        database_manager._sqlite_conn = mock_sqlite_conn
        
        # Test closure (should not raise exception even with SQLite failure)
        await database_manager.close_all()
        
        # Verify MongoDB closure was attempted
        assert mock_mongo_client.close.called
        
        # Verify SQLite closure was attempted
        assert mock_sqlite_conn.close.called
        
        # Verify connected flag is reset
        assert database_manager._is_connected is False


# Integration tests with temporary databases
class TestDatabaseManagerIntegration:
    """Integration tests for the DatabaseManager class."""
    
    @pytest.fixture
    def temp_database_manager(self):
        """Create a DatabaseManager with temporary database files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = os.path.join(temp_dir, "test.db")
            
            # Set environment variables for testing
            os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
            os.environ["MONGODB_DATABASE"] = "test_db"
            os.environ["SQLITE_DATABASE_PATH"] = sqlite_path
            
            # Create database manager
            db_manager = DatabaseManager()
            yield db_manager
            
            # Clean up environment variables
            if "MONGODB_URI" in os.environ:
                del os.environ["MONGODB_URI"]
            if "MONGODB_DATABASE" in os.environ:
                del os.environ["MONGODB_DATABASE"]
            if "SQLITE_DATABASE_PATH" in os.environ:
                del os.environ["SQLITE_DATABASE_PATH"]
    
    def test_database_manager_properties(self, temp_database_manager):
        """Test that DatabaseManager has all required properties."""
        db_manager = temp_database_manager
        
        # Test that all required attributes exist
        assert hasattr(db_manager, '_mongo_client')
        assert hasattr(db_manager, '_sqlite_conn')
        assert hasattr(db_manager, '_mongo_db_name')
        assert hasattr(db_manager, '_is_connected')
        assert hasattr(db_manager, 'config_manager')
        
        # Test that all required methods exist
        assert hasattr(db_manager, 'connect_all')
        assert hasattr(db_manager, 'get_mongo_db')
        assert hasattr(db_manager, 'get_sqlite_conn')
        assert hasattr(db_manager, 'health_check')
        assert hasattr(db_manager, 'close_all')
        assert hasattr(db_manager, 'is_connected')


# Test with actual configuration
@pytest.mark.asyncio
async def test_database_manager_with_real_config():
    """Test DatabaseManager with real configuration."""
    # Set up environment variables
    original_mongo_uri = os.environ.get("MONGODB_URI")
    original_mongo_db = os.environ.get("MONGODB_DATABASE")
    original_sqlite_path = os.environ.get("SQLITE_DATABASE_PATH")
    
    try:
        # Set test environment variables
        os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
        os.environ["MONGODB_DATABASE"] = "test_db"
        os.environ["SQLITE_DATABASE_PATH"] = ":memory:"
        
        # Create database manager with real config
        config_manager = ConfigManager()
        db_manager = DatabaseManager(config_manager=config_manager)
        
        # Test initialization
        assert isinstance(db_manager.config_manager, ConfigManager)
        assert db_manager._is_connected is False
        
    finally:
        # Restore original environment variables
        if original_mongo_uri:
            os.environ["MONGODB_URI"] = original_mongo_uri
        elif "MONGODB_URI" in os.environ:
            del os.environ["MONGODB_URI"]
            
        if original_mongo_db:
            os.environ["MONGODB_DATABASE"] = original_mongo_db
        elif "MONGODB_DATABASE" in os.environ:
            del os.environ["MONGODB_DATABASE"]
            
        if original_sqlite_path:
            os.environ["SQLITE_DATABASE_PATH"] = original_sqlite_path
        elif "SQLITE_DATABASE_PATH" in os.environ:
            del os.environ["SQLITE_DATABASE_PATH"]