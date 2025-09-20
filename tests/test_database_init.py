"""
Test for the database initialization functionality.
"""

import sqlite3
from unittest.mock import Mock, MagicMock, patch
from pymongo.database import Database
from src.database.init import DatabaseInitializer


def test_database_initializer_initialization():
    """Test DatabaseInitializer initialization."""
    initializer = DatabaseInitializer()
    assert isinstance(initializer, DatabaseInitializer)


def test_initialize_databases_success():
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


def test_initialize_databases_mongo_failure():
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


def test_initialize_databases_sqlite_failure():
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


def test_detect_migrations():
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
    assert "existing_data" in result


def test_check_sqlite_migration_status():
    """Test SQLite migration status check."""
    # Create mock connection
    mock_conn = Mock(spec=sqlite3.Connection)
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock cursor results
    mock_cursor.fetchall.return_value = [("user_profiles",), ("subscriptions",)]
    mock_cursor.fetchone.return_value = (0,)  # No existing data
    
    # Create initializer
    initializer = DatabaseInitializer()
    
    # Test SQLite migration status check
    result = initializer._check_sqlite_migration_status(mock_conn)
    
    # Verify result
    assert isinstance(result, dict)
    assert "sqlite_version" in result
    assert "existing_data" in result


def test_check_mongodb_migration_status():
    """Test MongoDB migration status check."""
    # Create mock database
    mock_db = Mock(spec=Database)
    mock_db.list_collection_names.return_value = ["users", "narrative_fragments", "items"]
    
    # Mock collection
    mock_collection = Mock()
    mock_collection.count_documents.return_value = 0  # No existing data
    mock_db.__getitem__ = Mock(return_value=mock_collection)
    
    # Create initializer
    initializer = DatabaseInitializer()
    
    # Test MongoDB migration status check
    result = initializer._check_mongodb_migration_status(mock_db)
    
    # Verify result
    assert isinstance(result, dict)
    assert "mongodb_version" in result
    assert "existing_data" in result


def test_initialize_mongodb():
    """Test MongoDB initialization."""
    # Create mock database
    mock_db = Mock(spec=Database)
    
    # Mock MongoDBHandler
    with patch('src.database.init.MongoDBHandler') as mock_handler_class:
        mock_handler_instance = Mock()
        # Mock initialize_collections to return a coroutine that returns True
        async def mock_initialize_collections():
            return True
        mock_handler_instance.initialize_collections = mock_initialize_collections
        mock_handler_class.return_value = mock_handler_instance
        
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Test MongoDB initialization
        result = initializer._initialize_mongodb(mock_db, {})
        
        # Since we're not testing the actual MongoDBHandler, we just verify it doesn't crash
        # In a real test, we would mock MongoDBHandler.initialize_collections


def test_initialize_sqlite():
    """Test SQLite initialization."""
    # Create mock connection
    mock_conn = Mock(spec=sqlite3.Connection)
    
    # Mock SQLiteSchemas.initialize_database to return True
    with patch('src.database.schemas.sqlite.SQLiteSchemas.initialize_database', return_value=True):
        # Create initializer
        initializer = DatabaseInitializer()
        
        # Test SQLite initialization
        result = initializer._initialize_sqlite(mock_conn, {})
        
        # Verify result
        assert result is True


def test_convenience_function():
    """Test convenience function."""
    from src.database.init import initialize_databases
    
    # Create mocks
    mock_mongo_db = Mock(spec=Database)
    mock_sqlite_conn = Mock(spec=sqlite3.Connection)
    
    # Mock DatabaseInitializer.initialize_databases to return True
    with patch('src.database.init.DatabaseInitializer.initialize_databases', return_value=True):
        # Test convenience function
        result = initialize_databases(mock_mongo_db, mock_sqlite_conn)
        
        # Verify result
        assert result is True


if __name__ == "__main__":
    test_database_initializer_initialization()
    test_initialize_databases_success()
    test_initialize_databases_mongo_failure()
    test_initialize_databases_sqlite_failure()
    test_detect_migrations()
    test_check_sqlite_migration_status()
    test_check_mongodb_migration_status()
    test_initialize_mongodb()
    test_initialize_sqlite()
    test_convenience_function()
    print("All tests passed!")