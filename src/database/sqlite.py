"""
SQLite handler for the YABOT system.

This module provides table operations for SQLite tables as required by the fase1 specification.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import logging
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SQLiteHandler:
    """Handler for SQLite tables and operations."""
    
    def __init__(self, connection: sqlite3.Connection):
        """Initialize the SQLite handler.
        
        Args:
            connection (sqlite3.Connection): SQLite database connection
        """
        self._conn = connection
        logger.info("SQLiteHandler initialized")
    
    def get_user_profiles_table(self) -> str:
        """Get the name of the UserProfiles table.
        
        Returns:
            str: Name of the UserProfiles table
        """
        logger.debug("Accessing UserProfiles table")
        return "user_profiles"
    
    def get_subscriptions_table(self) -> str:
        """Get the name of the Subscriptions table.
        
        Returns:
            str: Name of the Subscriptions table
        """
        logger.debug("Accessing Subscriptions table")
        return "subscriptions"
    
    def initialize_tables(self) -> bool:
        """Initialize and verify SQLite tables.
        
        Creates tables and indexes if they don't exist.
        
        Returns:
            bool: True if all tables were initialized successfully, False otherwise
        """
        try:
            logger.info("Initializing SQLite tables")
            
            # Initialize UserProfiles table
            self._initialize_user_profiles_table()
            
            # Initialize Subscriptions table
            self._initialize_subscriptions_table()
            
            logger.info("All SQLite tables initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Error initializing SQLite tables: %s", str(e))
            return False
    
    def _initialize_user_profiles_table(self) -> None:
        """Initialize the UserProfiles table with required schema."""
        logger.debug("Initializing UserProfiles table")
        
        # Create UserProfiles table
        create_table_sql = """
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
        
        cursor = self._conn.cursor()
        cursor.execute(create_table_sql)
        
        # Create indexes for common query patterns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_telegram_id ON user_profiles(telegram_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_active ON user_profiles(is_active)")
        
        self._conn.commit()
        logger.debug("UserProfiles table initialized")
    
    def _initialize_subscriptions_table(self) -> None:
        """Initialize the Subscriptions table with required schema."""
        logger.debug("Initializing Subscriptions table")
        
        # Create Subscriptions table
        create_table_sql = """
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
        
        cursor = self._conn.cursor()
        cursor.execute(create_table_sql)
        
        # Create indexes for common query patterns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_plan_type ON subscriptions(plan_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_dates ON subscriptions(start_date, end_date)")
        
        self._conn.commit()
        logger.debug("Subscriptions table initialized")
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as a list of dictionaries.
        
        Args:
            query (str): SQL query to execute
            params (Tuple, optional): Query parameters
            
        Returns:
            List[Dict[str, Any]]: Query results as list of dictionaries
        """
        logger.debug("Executing query: %s", query)
        
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Convert rows to dictionaries
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        logger.debug("Query returned %d results", len(results))
        return results
    
    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query (str): SQL query to execute
            params (Tuple, optional): Query parameters
            
        Returns:
            int: Number of affected rows
        """
        logger.debug("Executing update: %s", query)
        
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        self._conn.commit()
        affected_rows = cursor.rowcount
        logger.debug("Update affected %d rows", affected_rows)
        return affected_rows