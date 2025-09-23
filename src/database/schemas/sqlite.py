"""
SQLite schema definitions for the YABOT system.

This module provides schema definitions for SQLite tables as required by the fase1 specification.
These definitions are used for table creation and validation when working with SQLite databases.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import sqlite3
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SQLiteSchemas:
    """Schema definitions for SQLite tables."""
    
    @staticmethod
    def get_user_profiles_schema() -> str:
        """Get the CREATE TABLE statement for the UserProfiles table.
        
        Returns:
            str: SQL statement to create the UserProfiles table
        """
        logger.debug("Getting UserProfiles table schema")
        return """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            telegram_user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME,
            is_active BOOLEAN DEFAULT 1
        )
        """
    
    @staticmethod
    def get_subscriptions_schema() -> str:
        """Get the CREATE TABLE statement for the Subscriptions table.
        
        Returns:
            str: SQL statement to create the Subscriptions table
        """
        logger.debug("Getting Subscriptions table schema")
        return """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            plan_type TEXT NOT NULL CHECK (plan_type IN ('free', 'premium', 'vip')),
            status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'cancelled', 'expired')),
            start_date DATETIME NOT NULL,
            end_date DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
        )
        """
    
    @staticmethod
    def get_user_profiles_indexes() -> List[str]:
        """Get the CREATE INDEX statements for the UserProfiles table.
        
        Returns:
            List[str]: SQL statements to create indexes for the UserProfiles table
        """
        logger.debug("Getting UserProfiles table indexes")
        return [
            "CREATE INDEX IF NOT EXISTS idx_user_profiles_telegram_id ON user_profiles(telegram_user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username)",
            "CREATE INDEX IF NOT EXISTS idx_user_profiles_active ON user_profiles(is_active)"
        ]
    
    @staticmethod
    def get_subscriptions_indexes() -> List[str]:
        """Get the CREATE INDEX statements for the Subscriptions table.
        
        Returns:
            List[str]: SQL statements to create indexes for the Subscriptions table
        """
        logger.debug("Getting Subscriptions table indexes")
        return [
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_plan_type ON subscriptions(plan_type)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_dates ON subscriptions(start_date, end_date)"
        ]
    
    @classmethod
    def initialize_database(cls, connection: sqlite3.Connection) -> bool:
        """Initialize the database with all required tables and indexes.
        
        Args:
            connection (sqlite3.Connection): SQLite database connection
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing SQLite database with required tables and indexes")
            cursor = connection.cursor()
            
            # Create tables
            cursor.execute(cls.get_user_profiles_schema())
            cursor.execute(cls.get_subscriptions_schema())
            
            # Create indexes
            for index_sql in cls.get_user_profiles_indexes():
                cursor.execute(index_sql)
            
            for index_sql in cls.get_subscriptions_indexes():
                cursor.execute(index_sql)
            
            connection.commit()
            logger.info("SQLite database initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Error initializing SQLite database: %s", str(e))
            return False


# Table name constants
USER_PROFILES_TABLE = "user_profiles"
SUBSCRIPTIONS_TABLE = "subscriptions"

# Column name constants for UserProfiles table
USER_PROFILES_COLUMNS = [
    "user_id",
    "telegram_user_id",
    "username",
    "first_name",
    "last_name",
    "language_code",
    "registration_date",
    "last_login",
    "is_active"
]

# Column name constants for Subscriptions table
SUBSCRIPTIONS_COLUMNS = [
    "id",
    "user_id",
    "plan_type",
    "status",
    "start_date",
    "end_date",
    "created_at",
    "updated_at"
]