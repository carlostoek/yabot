"""
Unit tests for the SQLite schema definitions.
"""

import sqlite3
import pytest
from unittest.mock import Mock, patch
from src.database.schemas.sqlite import SQLiteSchemas


class TestSQLiteSchemas:
    """Test cases for SQLite schema definitions."""

    def test_get_user_profiles_schema(self):
        """Test getting UserProfiles schema."""
        schema = SQLiteSchemas.get_user_profiles_schema()
        assert "CREATE TABLE IF NOT EXISTS user_profiles" in schema
        assert "user_id TEXT PRIMARY KEY" in schema
        assert "telegram_user_id INTEGER UNIQUE NOT NULL" in schema
        assert "username TEXT" in schema
        assert "first_name TEXT" in schema
        assert "last_name TEXT" in schema
        assert "language_code TEXT" in schema
        assert "registration_date DATETIME DEFAULT CURRENT_TIMESTAMP" in schema
        assert "last_login DATETIME" in schema
        assert "is_active BOOLEAN DEFAULT 1" in schema

    def test_get_subscriptions_schema(self):
        """Test getting Subscriptions schema."""
        schema = SQLiteSchemas.get_subscriptions_schema()
        assert "CREATE TABLE IF NOT EXISTS subscriptions" in schema
        assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in schema
        assert "user_id TEXT NOT NULL" in schema
        assert "plan_type TEXT NOT NULL CHECK (plan_type IN ('free', 'premium', 'vip'))" in schema
        assert "status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'cancelled', 'expired'))" in schema
        assert "start_date DATETIME NOT NULL" in schema
        assert "end_date DATETIME" in schema
        assert "created_at DATETIME DEFAULT CURRENT_TIMESTAMP" in schema
        assert "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP" in schema
        assert "FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)" in schema

    def test_get_user_profiles_indexes(self):
        """Test getting UserProfiles indexes."""
        indexes = SQLiteSchemas.get_user_profiles_indexes()
        assert isinstance(indexes, list)
        assert len(indexes) == 3
        
        # Check that each index creation statement is present
        index_sql_statements = [stmt for stmt in indexes]
        assert any("idx_user_profiles_telegram_id" in stmt for stmt in index_sql_statements)
        assert any("idx_user_profiles_username" in stmt for stmt in index_sql_statements)
        assert any("idx_user_profiles_active" in stmt for stmt in index_sql_statements)

    def test_get_subscriptions_indexes(self):
        """Test getting Subscriptions indexes."""
        indexes = SQLiteSchemas.get_subscriptions_indexes()
        assert isinstance(indexes, list)
        assert len(indexes) == 4
        
        # Check that each index creation statement is present
        index_sql_statements = [stmt for stmt in indexes]
        assert any("idx_subscriptions_user_id" in stmt for stmt in index_sql_statements)
        assert any("idx_subscriptions_plan_type" in stmt for stmt in index_sql_statements)
        assert any("idx_subscriptions_status" in stmt for stmt in index_sql_statements)
        assert any("idx_subscriptions_dates" in stmt for stmt in index_sql_statements)

    def test_initialize_database_success(self):
        """Test successful database initialization."""
        # Create an in-memory SQLite database for testing
        conn = sqlite3.connect(":memory:")
        
        # Test initialization
        result = SQLiteSchemas.initialize_database(conn)
        
        # Verify success
        assert result is True
        
        # Verify that tables were created
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "user_profiles" in tables
        assert "subscriptions" in tables
        
        # Verify that indexes were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        expected_indexes = [
            "idx_user_profiles_telegram_id",
            "idx_user_profiles_username",
            "idx_user_profiles_active",
            "idx_subscriptions_user_id",
            "idx_subscriptions_plan_type",
            "idx_subscriptions_status",
            "idx_subscriptions_dates"
        ]
        
        for index in expected_indexes:
            assert index in indexes

    def test_initialize_database_error(self):
        """Test database initialization with error."""
        # Create a mock connection that raises an exception
        mock_conn = Mock(spec=sqlite3.Connection)
        mock_conn.cursor.side_effect = Exception("Test error")
        
        # Test initialization
        result = SQLiteSchemas.initialize_database(mock_conn)
        
        # Verify failure
        assert result is False