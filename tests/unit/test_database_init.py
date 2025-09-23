"""
Unit tests for the database initialization functionality.
"""

import sqlite3
import pytest
from unittest.mock import Mock, patch, MagicMock
from pymongo.database import Database
from src.database.init import DatabaseInitializer


class TestDatabaseInitializer:
    """Test cases for DatabaseInitializer class."""

    def test_init(self):
        """Test DatabaseInitializer initialization."""
        initializer = DatabaseInitializer()
        assert isinstance(initializer, DatabaseInitializer)

    def test_initialize_databases_success(self):
        """Test successful database initialization."""
        # Create mocks
        mock_mongo_db = Mock(spec=Database)
        mock_sqlite_conn = Mock(spec=sqlite3.Connection)
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Mock internal methods to return success
        initializer._detect_migrations = Mock(return_value={
            "sqlite_version": "1.0",
            "mongodb_version": "1.0",
            "requires_migration": False,
            "existing_data": False
        })
        initializer._initialize_mongodb = Mock(return_value=True)
        initializer._initialize_sqlite = Mock(return_value=True)
        
        # Test initialization
        result = initializer.initialize_databases(mock_mongo_db, mock_sqlite_conn)
        
        # Verify success
        assert result is True
        initializer._detect_migrations.assert_called_once_with(mock_sqlite_conn, mock_mongo_db)
        initializer._initialize_mongodb.assert_called_once()
        initializer._initialize_sqlite.assert_called_once()

    def test_initialize_databases_mongo_failure(self):
        """Test database initialization with MongoDB failure."""
        # Create mocks
        mock_mongo_db = Mock(spec=Database)
        mock_sqlite_conn = Mock(spec=sqlite3.Connection)
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Mock internal methods
        initializer._detect_migrations = Mock(return_value={
            "sqlite_version": "1.0",
            "mongodb_version": "1.0",
            "requires_migration": False,
            "existing_data": False
        })
        initializer._initialize_mongodb = Mock(return_value=False)  # Fail MongoDB
        initializer._initialize_sqlite = Mock(return_value=True)
        
        # Test initialization
        result = initializer.initialize_databases(mock_mongo_db, mock_sqlite_conn)
        
        # Verify failure
        assert result is False

    def test_initialize_databases_sqlite_failure(self):
        """Test database initialization with SQLite failure."""
        # Create mocks
        mock_mongo_db = Mock(spec=Database)
        mock_sqlite_conn = Mock(spec=sqlite3.Connection)
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Mock internal methods
        initializer._detect_migrations = Mock(return_value={
            "sqlite_version": "1.0",
            "mongodb_version": "1.0",
            "requires_migration": False,
            "existing_data": False
        })
        initializer._initialize_mongodb = Mock(return_value=True)
        initializer._initialize_sqlite = Mock(return_value=False)  # Fail SQLite
        
        # Test initialization
        result = initializer.initialize_databases(mock_mongo_db, mock_sqlite_conn)
        
        # Verify failure
        assert result is False

    def test_initialize_databases_exception(self):
        """Test database initialization with exception."""
        # Create mocks
        mock_mongo_db = Mock(spec=Database)
        mock_sqlite_conn = Mock(spec=sqlite3.Connection)
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Mock to raise exception
        initializer._detect_migrations = Mock(side_effect=Exception("Test error"))
        
        # Test initialization
        result = initializer.initialize_databases(mock_mongo_db, mock_sqlite_conn)
        
        # Verify failure
        assert result is False

    def test_detect_migrations(self):
        """Test migration detection."""
        # Create mocks
        mock_mongo_db = Mock(spec=Database)
        mock_sqlite_conn = Mock(spec=sqlite3.Connection)
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Mock internal methods
        initializer._check_sqlite_migration_status = Mock(return_value={
            "sqlite_version": "1.0",
            "existing_data": False
        })
        initializer._check_mongodb_migration_status = Mock(return_value={
            "mongodb_version": "1.0",
            "existing_data": False
        })
        
        # Test migration detection
        result = initializer._detect_migrations(mock_sqlite_conn, mock_mongo_db)
        
        # Verify result
        assert isinstance(result, dict)
        assert "sqlite_version" in result
        assert "mongodb_version" in result
        assert "requires_migration" in result
        assert result["requires_migration"] is False

    def test_detect_migrations_with_existing_data(self):
        """Test migration detection with existing data."""
        # Create mocks
        mock_mongo_db = Mock(spec=Database)
        mock_sqlite_conn = Mock(spec=sqlite3.Connection)
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Mock internal methods with existing data
        initializer._check_sqlite_migration_status = Mock(return_value={
            "sqlite_version": "1.0",
            "existing_data": True  # Existing data
        })
        initializer._check_mongodb_migration_status = Mock(return_value={
            "mongodb_version": "1.0",
            "existing_data": False
        })
        
        # Test migration detection
        result = initializer._detect_migrations(mock_sqlite_conn, mock_mongo_db)
        
        # Verify result - should require migration
        assert result["requires_migration"] is True

    def test_check_sqlite_migration_status_success(self):
        """Test successful SQLite migration status check."""
        # Create mock connection
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock cursor results
        mock_cursor.fetchall.return_value = [("user_profiles",), ("subscriptions",)]
        mock_cursor.fetchone.return_value = (5,)  # 5 existing records
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Test SQLite migration status check
        result = initializer._check_sqlite_migration_status(mock_conn)
        
        # Verify result
        assert isinstance(result, dict)
        assert result["sqlite_version"] == "1.0"
        assert result["existing_data"] is True

    def test_check_sqlite_migration_status_no_data(self):
        """Test SQLite migration status check with no data."""
        # Create mock connection
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock cursor results - no tables
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = (0,)
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Test SQLite migration status check
        result = initializer._check_sqlite_migration_status(mock_conn)
        
        # Verify result
        assert isinstance(result, dict)
        assert result["sqlite_version"] == "1.0"
        assert result["existing_data"] is False

    def test_check_sqlite_migration_status_exception(self):
        """Test SQLite migration status check with exception."""
        # Create mock connection
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_conn.cursor.side_effect = Exception("Test error")
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Test SQLite migration status check
        result = initializer._check_sqlite_migration_status(mock_conn)
        
        # Verify result
        assert isinstance(result, dict)
        assert result["sqlite_version"] is None
        assert result["existing_data"] is False

    def test_check_mongodb_migration_status_success(self):
        """Test successful MongoDB migration status check."""
        # Create mock database
        mock_db = MagicMock(spec=Database)
        mock_db.list_collection_names.return_value = ["users", "narrative_fragments", "items"]
        
        # Mock collection
        mock_collection = Mock()
        mock_collection.count_documents.return_value = 3  # 3 existing documents
        mock_db.__getitem__.return_value = mock_collection
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Test MongoDB migration status check
        result = initializer._check_mongodb_migration_status(mock_db)
        
        # Verify result
        assert isinstance(result, dict)
        assert result["mongodb_version"] == "1.0"
        assert result["existing_data"] is True

    def test_check_mongodb_migration_status_no_data(self):
        """Test MongoDB migration status check with no data."""
        # Create mock database
        mock_db = MagicMock(spec=Database)
        mock_db.list_collection_names.return_value = []
        
        # Mock collection
        mock_collection = Mock()
        mock_collection.count_documents.return_value = 0
        mock_db.__getitem__.return_value = mock_collection
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Test MongoDB migration status check
        result = initializer._check_mongodb_migration_status(mock_db)
        
        # Verify result
        assert isinstance(result, dict)
        assert result["mongodb_version"] == "1.0"
        assert result["existing_data"] is False

    def test_check_mongodb_migration_status_exception(self):
        """Test MongoDB migration status check with exception."""
        # Create mock database
        mock_db = Mock(spec=Database)
        mock_db.list_collection_names.side_effect = Exception("Test error")
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Test MongoDB migration status check
        result = initializer._check_mongodb_migration_status(mock_db)
        
        # Verify result
        assert isinstance(result, dict)
        assert result["mongodb_version"] is None
        assert result["existing_data"] is False

    def test_initialize_mongodb_success(self):
        """Test successful MongoDB initialization."""
        # Create mock database
        mock_db = Mock(spec=Database)
        
        # Mock MongoDBHandler
        with patch('src.database.init.MongoDBHandler') as mock_handler_class:
            mock_handler_instance = Mock()
            mock_handler_instance.initialize_collections.return_value = True
            mock_handler_class.return_value = mock_handler_instance
            
            # Create initializer
            initializer = DatabaseInitializer()
            
            # Test MongoDB initialization
            result = initializer._initialize_mongodb(mock_db, {})
            
            # Verify result
            assert result is True
            mock_handler_class.assert_called_once_with(mock_db)
            mock_handler_instance.initialize_collections.assert_called_once()

    def test_initialize_mongodb_failure(self):
        """Test MongoDB initialization failure."""
        # Create mock database
        mock_db = Mock(spec=Database)
        
        # Mock MongoDBHandler
        with patch('src.database.init.MongoDBHandler') as mock_handler_class:
            mock_handler_instance = Mock()
            mock_handler_instance.initialize_collections.return_value = False
            mock_handler_class.return_value = mock_handler_instance
            
            # Create initializer
            initializer = DatabaseInitializer()
            
            # Test MongoDB initialization
            result = initializer._initialize_mongodb(mock_db, {})
            
            # Verify result
            assert result is False

    def test_initialize_mongodb_exception(self):
        """Test MongoDB initialization with exception."""
        # Create mock database
        mock_db = Mock(spec=Database)
        
        # Mock MongoDBHandler to raise exception
        with patch('src.database.init.MongoDBHandler') as mock_handler_class:
            mock_handler_class.side_effect = Exception("Test error")
            
            # Create initializer
            initializer = DatabaseInitializer()
            
            # Test MongoDB initialization
            result = initializer._initialize_mongodb(mock_db, {})
            
            # Verify result
            assert result is False

    def test_initialize_sqlite_success(self):
        """Test successful SQLite initialization."""
        # Create mock connection
        mock_conn = Mock(spec=sqlite3.Connection)
        
        # Mock SQLiteSchemas.initialize_database
        with patch('src.database.init.SQLiteSchemas.initialize_database', return_value=True):
            # Create initializer
            initializer = DatabaseInitializer()
            
            # Test SQLite initialization
            result = initializer._initialize_sqlite(mock_conn, {})
            
            # Verify result
            assert result is True

    def test_initialize_sqlite_failure(self):
        """Test SQLite initialization failure."""
        # Create mock connection
        mock_conn = Mock(spec=sqlite3.Connection)
        
        # Mock SQLiteSchemas.initialize_database to return False
        with patch('src.database.init.SQLiteSchemas.initialize_database', return_value=False):
            # Create initializer
            initializer = DatabaseInitializer()
            
            # Test SQLite initialization
            result = initializer._initialize_sqlite(mock_conn, {})
            
            # Verify result
            assert result is False

    def test_initialize_sqlite_exception(self):
        """Test SQLite initialization with exception."""
        # Create mock connection
        mock_conn = Mock(spec=sqlite3.Connection)
        
        # Mock SQLiteSchemas.initialize_database to raise exception
        with patch('src.database.init.SQLiteSchemas.initialize_database', side_effect=Exception("Test error")):
            # Create initializer
            initializer = DatabaseInitializer()
            
            # Test SQLite initialization
            result = initializer._initialize_sqlite(mock_conn, {})
            
            # Verify result
            assert result is False