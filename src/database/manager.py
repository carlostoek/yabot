"""
Database connection manager for the YABOT system.

This module provides a unified interface for managing connections to both
MongoDB and SQLite databases, implementing connection pooling, health checks,
and reconnection logic as required by the fase1 specification.
"""

import asyncio
import logging
import sqlite3
import time
from typing import Any, Dict, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from src.config.manager import ConfigManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Unified database manager for MongoDB and SQLite connections."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the database manager.
        
        Args:
            config_manager (ConfigManager, optional): Configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self._mongo_client: Optional[MongoClient] = None
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._mongo_db_name: Optional[str] = None
        self._is_connected = False
        
        logger.info("DatabaseManager initialized")
    
    async def connect_all(self) -> bool:
        """Initialize connections to all configured databases.
        
        Returns:
            bool: True if all connections were established successfully, False otherwise
        """
        logger.info("Initializing connections to all databases")
        
        try:
            # Get database configuration
            db_config = self.config_manager.get_database_config()
            
            # Connect to MongoDB with retry logic
            mongo_success = await self._connect_mongodb(
                db_config.mongodb_uri, 
                db_config.mongodb_database
            )
            
            if not mongo_success:
                logger.error("Failed to connect to MongoDB")
                return False
            
            # Connect to SQLite
            sqlite_success = self._connect_sqlite(db_config.sqlite_database_path)
            
            if not sqlite_success:
                logger.error("Failed to connect to SQLite")
                return False
            
            self._is_connected = True
            logger.info("Successfully connected to all databases")
            return True
            
        except Exception as e:
            logger.error("Error initializing database connections: %s", str(e))
            return False
    
    async def _connect_mongodb(self, uri: str, database: str) -> bool:
        """Connect to MongoDB with exponential backoff retry logic.
        
        Args:
            uri (str): MongoDB connection URI
            database (str): Database name
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        logger.info("Connecting to MongoDB at %s", uri)
        
        max_retries = 5
        retry_delay = 1  # Start with 1 second delay
        
        for attempt in range(max_retries):
            try:
                # Create MongoDB client with connection pooling
                self._mongo_client = MongoClient(
                    uri,
                    connectTimeoutMS=5000,
                    serverSelectionTimeoutMS=5000,
                    maxPoolSize=50,
                    minPoolSize=5
                )
                
                # Test connection
                self._mongo_client.admin.command('ping')
                self._mongo_db_name = database
                
                logger.info("Successfully connected to MongoDB")
                return True
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.warning(
                    "MongoDB connection attempt %d failed: %s", 
                    attempt + 1, 
                    str(e)
                )
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    logger.info("Retrying in %d seconds...", retry_delay)
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Double the delay for next attempt
                else:
                    logger.error("Max retries exceeded for MongoDB connection")
                    return False
                    
            except Exception as e:
                logger.error("Unexpected error connecting to MongoDB: %s", str(e))
                return False
        
        return False
    
    def _connect_sqlite(self, database_path: str) -> bool:
        """Connect to SQLite database.
        
        Args:
            database_path (str): Path to SQLite database file
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        logger.info("Connecting to SQLite database at %s", database_path)
        
        try:
            # Create SQLite connection with connection pooling-like behavior
            self._sqlite_conn = sqlite3.connect(
                database_path,
                check_same_thread=False,  # Allow sharing across threads
                timeout=30.0
            )
            
            # Enable WAL mode for better concurrency
            self._sqlite_conn.execute("PRAGMA journal_mode=WAL")
            
            # Test connection
            self._sqlite_conn.execute("SELECT 1")
            
            logger.info("Successfully connected to SQLite database")
            return True
            
        except Exception as e:
            logger.error("Error connecting to SQLite database: %s", str(e))
            return False
    
    def get_mongo_db(self):
        """Get MongoDB database instance.
        
        Returns:
            pymongo.database.Database: MongoDB database instance
            
        Raises:
            ValueError: If MongoDB is not connected
        """
        if not self._mongo_client or not self._mongo_db_name:
            raise ValueError("MongoDB is not connected")
        
        return self._mongo_client[self._mongo_db_name]
    
    def get_sqlite_conn(self) -> sqlite3.Connection:
        """Get SQLite database connection.
        
        Returns:
            sqlite3.Connection: SQLite database connection
            
        Raises:
            ValueError: If SQLite is not connected
        """
        if not self._sqlite_conn:
            raise ValueError("SQLite is not connected")
        
        return self._sqlite_conn
    
    async def health_check(self) -> Dict[str, bool]:
        """Check the health of all database connections.
        
        Returns:
            Dict[str, bool]: Health status for each database
        """
        logger.debug("Performing database health check")
        
        health_status = {
            "mongodb": False,
            "sqlite": False
        }
        
        # Check MongoDB health
        if self._mongo_client:
            try:
                self._mongo_client.admin.command('ping')
                health_status["mongodb"] = True
            except Exception as e:
                logger.warning("MongoDB health check failed: %s", str(e))
        
        # Check SQLite health
        if self._sqlite_conn:
            try:
                self._sqlite_conn.execute("SELECT 1")
                health_status["sqlite"] = True
            except Exception as e:
                logger.warning("SQLite health check failed: %s", str(e))
        
        logger.debug("Database health check results: %s", health_status)
        return health_status
    
    async def close_all(self) -> None:
        """Close all database connections."""
        logger.info("Closing all database connections")
        
        # Close MongoDB connection
        if self._mongo_client:
            try:
                self._mongo_client.close()
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error("Error closing MongoDB connection: %s", str(e))
        
        # Close SQLite connection
        if self._sqlite_conn:
            try:
                self._sqlite_conn.close()
                logger.info("SQLite connection closed")
            except Exception as e:
                logger.error("Error closing SQLite connection: %s", str(e))
        
        self._is_connected = False
        logger.info("All database connections closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if all databases are connected.
        
        Returns:
            bool: True if all databases are connected, False otherwise
        """
        return self._is_connected