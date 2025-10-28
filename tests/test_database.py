"""
Tests for the database connection manager.
"""

import os
import pytest
import asyncio
from unittest.mock import Mock, patch
from src.database import DatabaseManager
from src.config.manager import ConfigManager


class TestDatabaseManager:
    """Test cases for the DatabaseManager class."""
    
    def test_init(self):
        """Test DatabaseManager initialization."""
        # Test with default config manager
        db_manager = DatabaseManager()
        assert db_manager is not None
        assert db_manager.config_manager is not None
        assert db_manager._mongo_client is None
        assert db_manager._sqlite_conn is None
        assert db_manager._mongo_db_name is None
        assert db_manager._is_connected is False
        
        # Test with custom config manager
        mock_config = Mock()
        db_manager = DatabaseManager(config_manager=mock_config)
        assert db_manager.config_manager == mock_config
    
    @patch('src.database.manager.MongoClient')
    @patch('src.database.manager.sqlite3')
    def test_connect_all_success(self, mock_sqlite, mock_mongo_client):
        """Test successful connection to all databases."""
        # Setup mocks
        mock_mongo_instance = Mock()
        mock_mongo_instance.admin.command.return_value = True
        mock_mongo_client.return_value = mock_mongo_instance
        
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.execute.return_value = True
        mock_sqlite.connect.return_value = mock_sqlite_conn
        
        # Setup config manager mock
        mock_config_manager = Mock()
        mock_config_manager.get_database_config.return_value = Mock(
            mongodb_uri="mongodb://localhost:27017/test",
            mongodb_database="test",
            sqlite_database_path="/tmp/test.db"
        )
        
        # Create database manager and connect
        db_manager = DatabaseManager(config_manager=mock_config_manager)
        result = asyncio.run(db_manager.connect_all())
        
        # Verify results
        assert result is True
        assert db_manager._is_connected is True
        mock_mongo_client.assert_called_once()
        mock_sqlite.connect.assert_called_once()
    
    @patch('src.database.manager.MongoClient')
    @patch('src.database.manager.sqlite3')
    def test_connect_all_mongo_failure(self, mock_sqlite, mock_mongo_client):
        """Test connection failure with MongoDB."""
        # Setup mocks to simulate MongoDB connection failure
        mock_mongo_client.side_effect = Exception("Connection failed")
        
        # Setup config manager mock
        mock_config_manager = Mock()
        mock_config_manager.get_database_config.return_value = Mock(
            mongodb_uri="mongodb://localhost:27017/test",
            mongodb_database="test",
            sqlite_database_path="/tmp/test.db"
        )
        
        # Create database manager and connect
        db_manager = DatabaseManager(config_manager=mock_config_manager)
        result = asyncio.run(db_manager.connect_all())
        
        # Verify results - connect_all always returns True to allow bot to start
        assert result is True
        assert db_manager._is_connected is True  # SQLite connection should still work
        mock_mongo_client.assert_called_once()
        mock_sqlite.connect.assert_called_once()
    
    @patch('src.database.manager.MongoClient')
    @patch('src.database.manager.sqlite3')
    def test_connect_all_sqlite_failure(self, mock_sqlite, mock_mongo_client):
        """Test connection failure with SQLite."""
        # Setup MongoDB mock to succeed
        mock_mongo_instance = Mock()
        mock_mongo_instance.admin.command.return_value = True
        mock_mongo_client.return_value = mock_mongo_instance
        
        # Setup SQLite mock to fail
        mock_sqlite.connect.side_effect = Exception("Connection failed")
        
        # Setup config manager mock
        mock_config_manager = Mock()
        mock_config_manager.get_database_config.return_value = Mock(
            mongodb_uri="mongodb://localhost:27017/test",
            mongodb_database="test",
            sqlite_database_path="/tmp/test.db"
        )
        
        # Create database manager and connect
        db_manager = DatabaseManager(config_manager=mock_config_manager)
        result = asyncio.run(db_manager.connect_all())
        
        # Verify results - connect_all always returns True to allow bot to start
        assert result is True
        assert db_manager._is_connected is True  # MongoDB connection should still work
        mock_mongo_client.assert_called_once()
        mock_sqlite.connect.assert_called_once()
    
    @patch('src.database.manager.MongoClient')
    def test_get_mongo_db(self, mock_mongo_client):
        """Test getting MongoDB database instance."""
        # Setup mock
        mock_mongo_instance = Mock()
        mock_mongo_client.return_value = mock_mongo_instance
        # Configure the mock to return a database when accessed with []
        mock_database = Mock()
        mock_mongo_instance.__getitem__ = Mock(return_value=mock_database)
        
        # Setup config manager mock
        mock_config_manager = Mock()
        mock_config_manager.get_database_config.return_value = Mock(
            mongodb_uri="mongodb://localhost:27017/test",
            mongodb_database="test",
            sqlite_database_path="/tmp/test.db"
        )
        
        # Create database manager and connect
        db_manager = DatabaseManager(config_manager=mock_config_manager)
        asyncio.run(db_manager.connect_all())
        
        # Test getting MongoDB database
        mongo_db = db_manager.get_mongo_db()
        assert mongo_db is not None
        mock_mongo_instance.__getitem__.assert_called_with("test")
    
    def test_get_mongo_db_not_connected(self):
        """Test getting MongoDB database when not connected."""
        db_manager = DatabaseManager()
        with pytest.raises(ValueError, match="MongoDB is not connected"):
            db_manager.get_mongo_db()
    
    @patch('src.database.manager.sqlite3')
    def test_get_sqlite_conn(self, mock_sqlite):
        """Test getting SQLite connection."""
        # Setup mock
        mock_sqlite_conn = Mock()
        mock_sqlite.connect.return_value = mock_sqlite_conn
        
        # Setup config manager mock
        mock_config_manager = Mock()
        mock_config_manager.get_database_config.return_value = Mock(
            mongodb_uri="mongodb://localhost:27017/test",
            mongodb_database="test",
            sqlite_database_path="/tmp/test.db"
        )
        
        # Create database manager and connect
        db_manager = DatabaseManager(config_manager=mock_config_manager)
        asyncio.run(db_manager.connect_all())
        
        # Test getting SQLite connection
        sqlite_conn = db_manager.get_sqlite_conn()
        assert sqlite_conn is not None
        assert sqlite_conn == mock_sqlite_conn
    
    def test_get_sqlite_conn_not_connected(self):
        """Test getting SQLite connection when not connected."""
        db_manager = DatabaseManager()
        with pytest.raises(ValueError, match="SQLite is not connected"):
            db_manager.get_sqlite_conn()
    
    @patch('src.database.manager.MongoClient')
    @patch('src.database.manager.sqlite3')
    def test_health_check(self, mock_sqlite, mock_mongo_client):
        """Test database health check."""
        # Setup mocks
        mock_mongo_instance = Mock()
        mock_mongo_instance.admin.command.return_value = True
        mock_mongo_client.return_value = mock_mongo_instance
        
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.execute.return_value = True
        mock_sqlite.connect.return_value = mock_sqlite_conn
        
        # Setup config manager mock
        mock_config_manager = Mock()
        mock_config_manager.get_database_config.return_value = Mock(
            mongodb_uri="mongodb://localhost:27017/test",
            mongodb_database="test",
            sqlite_database_path="/tmp/test.db"
        )
        
        # Create database manager and connect
        db_manager = DatabaseManager(config_manager=mock_config_manager)
        asyncio.run(db_manager.connect_all())
        
        # Test health check
        health_status = asyncio.run(db_manager.health_check())
        assert health_status["mongodb"] is True
        assert health_status["sqlite"] is True
    
    @patch('src.database.manager.MongoClient')
    @patch('src.database.manager.sqlite3')
    async def test_close_all(self, mock_sqlite, mock_mongo_client):
        """Test closing all database connections."""
        # Setup mocks
        mock_mongo_instance = Mock()
        mock_mongo_instance.close = Mock()
        mock_mongo_client.return_value = mock_mongo_instance
        
        mock_sqlite_conn = Mock()
        mock_sqlite_conn.close = Mock()
        mock_sqlite.connect.return_value = mock_sqlite_conn
        
        # Setup config manager mock
        mock_config_manager = Mock()
        mock_config_manager.get_database_config.return_value = Mock(
            mongodb_uri="mongodb://localhost:27017/test",
            mongodb_database="test",
            sqlite_database_path="/tmp/test.db"
        )
        
        # Create database manager and connect
        db_manager = DatabaseManager(config_manager=mock_config_manager)
        await db_manager.connect_all()
        
        # Test closing connections
        await db_manager.close_all()
        assert db_manager._is_connected is False
        mock_mongo_instance.close.assert_called_once()
        mock_sqlite_conn.close.assert_called_once()