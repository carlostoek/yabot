"""
Test for the SQLiteHandler class.
"""

import sqlite3
import tempfile
import os
from src.database.sqlite import SQLiteHandler


def test_sqlite_handler_initialization():
    """Test SQLiteHandler initialization."""
    # Create an in-memory SQLite database for testing
    conn = sqlite3.connect(":memory:")
    
    # Create handler
    handler = SQLiteHandler(conn)
    
    # Verify initialization
    assert handler._conn == conn


def test_table_access_methods():
    """Test table access methods."""
    # Create an in-memory SQLite database for testing
    conn = sqlite3.connect(":memory:")
    
    # Create handler
    handler = SQLiteHandler(conn)
    
    # Test table access methods
    assert handler.get_user_profiles_table() == "user_profiles"
    assert handler.get_subscriptions_table() == "subscriptions"


def test_initialize_tables():
    """Test table initialization."""
    # Create an in-memory SQLite database for testing
    conn = sqlite3.connect(":memory:")
    
    # Create handler
    handler = SQLiteHandler(conn)
    
    # Test initialization
    result = handler.initialize_tables()
    
    # Verify success
    assert result is True
    
    # Verify that tables were created
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "user_profiles" in tables
    assert "subscriptions" in tables


def test_execute_query():
    """Test query execution."""
    # Create an in-memory SQLite database for testing
    conn = sqlite3.connect(":memory:")
    
    # Create handler
    handler = SQLiteHandler(conn)
    
    # Initialize tables
    handler.initialize_tables()
    
    # Insert a test record
    insert_sql = """
    INSERT INTO user_profiles (user_id, telegram_user_id, username, first_name, last_name)
    VALUES (?, ?, ?, ?, ?)
    """
    handler.execute_update(insert_sql, ("user123", 12345, "testuser", "Test", "User"))
    
    # Query the record
    query_sql = "SELECT * FROM user_profiles WHERE user_id = ?"
    results = handler.execute_query(query_sql, ("user123",))
    
    # Verify results
    assert len(results) == 1
    assert results[0]["user_id"] == "user123"
    assert results[0]["telegram_user_id"] == 12345
    assert results[0]["username"] == "testuser"
    assert results[0]["first_name"] == "Test"
    assert results[0]["last_name"] == "User"


def test_execute_update():
    """Test update execution."""
    # Create an in-memory SQLite database for testing
    conn = sqlite3.connect(":memory:")
    
    # Create handler
    handler = SQLiteHandler(conn)
    
    # Initialize tables
    handler.initialize_tables()
    
    # Insert a test record
    insert_sql = """
    INSERT INTO user_profiles (user_id, telegram_user_id, username, first_name, last_name)
    VALUES (?, ?, ?, ?, ?)
    """
    affected_rows = handler.execute_update(insert_sql, ("user123", 12345, "testuser", "Test", "User"))
    
    # Verify insertion
    assert affected_rows == 1
    
    # Update the record
    update_sql = "UPDATE user_profiles SET username = ? WHERE user_id = ?"
    affected_rows = handler.execute_update(update_sql, ("updateduser", "user123"))
    
    # Verify update
    assert affected_rows == 1
    
    # Verify the update
    query_sql = "SELECT username FROM user_profiles WHERE user_id = ?"
    results = handler.execute_query(query_sql, ("user123",))
    assert results[0]["username"] == "updateduser"


if __name__ == "__main__":
    test_sqlite_handler_initialization()
    test_table_access_methods()
    test_initialize_tables()
    test_execute_query()
    test_execute_update()
    print("All tests passed!")