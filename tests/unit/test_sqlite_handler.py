"""
Unit tests for the SQLiteHandler class.
"""

import sqlite3
import pytest
from unittest.mock import Mock, MagicMock
from src.database.sqlite import SQLiteHandler


class TestSQLiteHandler:
    """Test cases for the SQLiteHandler class."""

    def test_init(self):
        """Test SQLiteHandler initialization."""
        mock_conn = Mock(spec=sqlite3.Connection)
        handler = SQLiteHandler(mock_conn)
        assert handler._conn == mock_conn

    def test_get_user_profiles_table(self):
        """Test getting UserProfiles table name."""
        mock_conn = Mock(spec=sqlite3.Connection)
        handler = SQLiteHandler(mock_conn)
        table_name = handler.get_user_profiles_table()
        assert table_name == "user_profiles"

    def test_get_subscriptions_table(self):
        """Test getting Subscriptions table name."""
        mock_conn = Mock(spec=sqlite3.Connection)
        handler = SQLiteHandler(mock_conn)
        table_name = handler.get_subscriptions_table()
        assert table_name == "subscriptions"

    def test_initialize_tables_success(self):
        """Test successful table initialization."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        handler = SQLiteHandler(mock_conn)
        result = handler.initialize_tables()
        
        assert result is True
        assert mock_conn.cursor.call_count == 2  # Called twice, once for each table
        assert mock_conn.commit.call_count == 2  # Called twice, once for each table
        assert mock_cursor.execute.call_count >= 2  # At least 2 calls per table (CREATE TABLE + indexes)

    def test_initialize_tables_error(self):
        """Test table initialization with error."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_conn.cursor.side_effect = Exception("Test error")
        
        handler = SQLiteHandler(mock_conn)
        result = handler.initialize_tables()
        
        assert result is False

    def test_execute_query(self):
        """Test query execution."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock cursor description and fetchall
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "test"), (2, "example")]
        
        handler = SQLiteHandler(mock_conn)
        results = handler.execute_query("SELECT * FROM test_table")
        
        assert len(results) == 2
        assert results[0] == {"id": 1, "name": "test"}
        assert results[1] == {"id": 2, "name": "example"}

    def test_execute_query_with_params(self):
        """Test query execution with parameters."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock cursor description and fetchall
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "test")]
        
        handler = SQLiteHandler(mock_conn)
        results = handler.execute_query("SELECT * FROM test_table WHERE id = ?", (1,))
        
        mock_cursor.execute.assert_called_with("SELECT * FROM test_table WHERE id = ?", (1,))
        assert len(results) == 1
        assert results[0] == {"id": 1, "name": "test"}

    def test_execute_update(self):
        """Test update execution."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        handler = SQLiteHandler(mock_conn)
        affected_rows = handler.execute_update("UPDATE test_table SET name = 'test'")
        
        assert affected_rows == 1
        mock_conn.commit.assert_called_once()

    def test_execute_update_with_params(self):
        """Test update execution with parameters."""
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        
        handler = SQLiteHandler(mock_conn)
        affected_rows = handler.execute_update("UPDATE test_table SET name = ? WHERE id = ?", ("test", 1))
        
        mock_cursor.execute.assert_called_with("UPDATE test_table SET name = ? WHERE id = ?", ("test", 1))
        assert affected_rows == 1
        mock_conn.commit.assert_called_once()