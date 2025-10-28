"""
Test for the SQLite schema definitions.
"""

import sqlite3
import tempfile
import os
from src.database.schemas.sqlite import SQLiteSchemas


def test_get_user_profiles_schema():
    """Test getting UserProfiles schema."""
    schema = SQLiteSchemas.get_user_profiles_schema()
    assert "CREATE TABLE IF NOT EXISTS user_profiles" in schema
    assert "user_id TEXT PRIMARY KEY" in schema
    assert "telegram_user_id INTEGER UNIQUE NOT NULL" in schema


def test_get_subscriptions_schema():
    """Test getting Subscriptions schema."""
    schema = SQLiteSchemas.get_subscriptions_schema()
    assert "CREATE TABLE IF NOT EXISTS subscriptions" in schema
    assert "user_id TEXT NOT NULL" in schema
    assert "plan_type TEXT NOT NULL CHECK (plan_type IN ('free', 'premium', 'vip'))" in schema
    assert "status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'cancelled', 'expired'))" in schema
    assert "FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)" in schema


def test_get_user_profiles_indexes():
    """Test getting UserProfiles indexes."""
    indexes = SQLiteSchemas.get_user_profiles_indexes()
    assert len(indexes) == 3
    assert "idx_user_profiles_telegram_id" in indexes[0]
    assert "idx_user_profiles_username" in indexes[1]
    assert "idx_user_profiles_active" in indexes[2]


def test_get_subscriptions_indexes():
    """Test getting Subscriptions indexes."""
    indexes = SQLiteSchemas.get_subscriptions_indexes()
    assert len(indexes) == 4
    assert "idx_subscriptions_user_id" in indexes[0]
    assert "idx_subscriptions_plan_type" in indexes[1]
    assert "idx_subscriptions_status" in indexes[2]
    assert "idx_subscriptions_dates" in indexes[3]


def test_initialize_database():
    """Test database initialization."""
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
    
    assert "idx_user_profiles_telegram_id" in indexes
    assert "idx_user_profiles_username" in indexes
    assert "idx_user_profiles_active" in indexes
    assert "idx_subscriptions_user_id" in indexes
    assert "idx_subscriptions_plan_type" in indexes
    assert "idx_subscriptions_status" in indexes
    assert "idx_subscriptions_dates" in indexes


def test_constants():
    """Test schema constants."""
    from src.database.schemas.sqlite import USER_PROFILES_TABLE, SUBSCRIPTIONS_TABLE
    from src.database.schemas.sqlite import USER_PROFILES_COLUMNS, SUBSCRIPTIONS_COLUMNS
    
    assert USER_PROFILES_TABLE == "user_profiles"
    assert SUBSCRIPTIONS_TABLE == "subscriptions"
    
    assert "user_id" in USER_PROFILES_COLUMNS
    assert "telegram_user_id" in USER_PROFILES_COLUMNS
    assert "username" in USER_PROFILES_COLUMNS
    
    assert "id" in SUBSCRIPTIONS_COLUMNS
    assert "user_id" in SUBSCRIPTIONS_COLUMNS
    assert "plan_type" in SUBSCRIPTIONS_COLUMNS
    assert "status" in SUBSCRIPTIONS_COLUMNS


if __name__ == "__main__":
    test_get_user_profiles_schema()
    test_get_subscriptions_schema()
    test_get_user_profiles_indexes()
    test_get_subscriptions_indexes()
    test_initialize_database()
    test_constants()
    print("All tests passed!")