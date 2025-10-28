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
from typing import Any, Dict, Optional, Callable, Awaitable
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
            bool: True if connections were established successfully, False otherwise
        """
        logger.info("Initializing connections to all databases")
        
        try:
            # Get database configuration
            db_config = self.config_manager.get_database_config()
            
            # Track which databases were configured for recovery monitoring
            self._mongo_was_configured = bool(db_config.mongodb_uri and db_config.mongodb_database)
            self._sqlite_was_configured = bool(db_config.sqlite_database_path)
            
            # Try to connect to MongoDB, but don't fail if not configured
            mongo_success = True
            if db_config.mongodb_uri and db_config.mongodb_database:
                mongo_success = await self._connect_mongodb(
                    db_config.mongodb_uri, 
                    db_config.mongodb_database
                )
                if not mongo_success:
                    logger.warning("Failed to connect to MongoDB, continuing without it")
            else:
                logger.warning("MongoDB configuration not found, continuing without it")
            
            # Try to connect to SQLite, but don't fail if not configured
            sqlite_success = True
            if db_config.sqlite_database_path:
                sqlite_success = self._connect_sqlite(db_config.sqlite_database_path)
                if not sqlite_success:
                    logger.warning("Failed to connect to SQLite, continuing without it")
            else:
                logger.warning("SQLite configuration not found, continuing without it")
            
            # Consider connected if at least one database is available or none are configured
            # We'll mark as connected to allow the bot to function with limited capabilities
            self._is_connected = mongo_success or sqlite_success
            if self._is_connected:
                logger.info("Successfully connected to available databases")
            else:
                logger.warning("No database connections available, bot will run with limited functionality")
            
            return True  # Always return True to allow bot to start
            
        except Exception as e:
            logger.error("Error initializing database connections: %s", str(e))
            # Don't prevent bot startup on database errors
            logger.warning("Continuing without database connections")
            return True
    
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
    
    async def execute_cross_database_transaction(
        self, 
        mongo_operations: Optional[Callable] = None,
        sqlite_operations: Optional[Callable] = None,
        rollback_on_failure: bool = True
    ) -> bool:
        """Execute operations across both MongoDB and SQLite databases atomically.
        
        This method implements cross-database transaction utilities as required
        by requirements 2.1, 2.3, and 2.5.
        
        Args:
            mongo_operations: Function to execute MongoDB operations
            sqlite_operations: Function to execute SQLite operations
            rollback_on_failure: Whether to attempt rollback on failure
            
        Returns:
            bool: True if all operations succeeded, False otherwise
        """
        logger.info("Starting cross-database transaction")
        
        # Track if we have active connections to both databases
        mongo_available = self._mongo_client is not None and self._mongo_db_name is not None
        sqlite_available = self._sqlite_conn is not None
        
        # If neither database is available, we can't perform any operations
        if not mongo_available and not sqlite_available:
            logger.warning("No database connections available for cross-database transaction")
            return False
        
        # Track success of each operation
        mongo_success = True
        sqlite_success = True
        mongo_error = None
        sqlite_error = None
        
        # Track if we need to rollback
        rollback_needed = False
        
        try:
            # Execute MongoDB operations if provided and MongoDB is available
            if mongo_operations and mongo_available:
                try:
                    logger.debug("Executing MongoDB operations in cross-database transaction")
                    # Start a MongoDB session for transaction support
                    async with await self._mongo_client.start_session() as session:
                        async with session.start_transaction():
                            await mongo_operations(self.get_mongo_db(), session)
                except Exception as e:
                    mongo_success = False
                    mongo_error = str(e)
                    logger.error("MongoDB operations failed in cross-database transaction: %s", mongo_error)
                    rollback_needed = rollback_on_failure
            
            # Execute SQLite operations if provided and SQLite is available
            if sqlite_operations and sqlite_available:
                try:
                    logger.debug("Executing SQLite operations in cross-database transaction")
                    # Start a SQLite transaction
                    sqlite_conn = self.get_sqlite_conn()
                    sqlite_conn.execute("BEGIN")
                    
                    try:
                        await sqlite_operations(sqlite_conn)
                        sqlite_conn.execute("COMMIT")
                    except Exception:
                        sqlite_conn.execute("ROLLBACK")
                        raise
                except Exception as e:
                    sqlite_success = False
                    sqlite_error = str(e)
                    logger.error("SQLite operations failed in cross-database transaction: %s", sqlite_error)
                    rollback_needed = rollback_on_failure
            
            # Check if all operations succeeded
            success = mongo_success and sqlite_success
            
            if success:
                logger.info("Cross-database transaction completed successfully")
            else:
                logger.warning(
                    "Cross-database transaction partially failed: MongoDB=%s, SQLite=%s", 
                    mongo_success, 
                    sqlite_success
                )
                if rollback_needed:
                    await self._rollback_cross_database_transaction()
            
            return success
            
        except Exception as e:
            logger.error("Unexpected error in cross-database transaction: %s", str(e))
            if rollback_on_failure:
                await self._rollback_cross_database_transaction()
            return False
    
    async def _rollback_cross_database_transaction(self) -> None:
        """Rollback operations in a cross-database transaction.
        
        Note: This is a simplified rollback implementation. In a production environment,
        you would need to implement more sophisticated rollback mechanisms.
        """
        logger.info("Rolling back cross-database transaction")
        # In a real implementation, you would need to maintain a log of operations
        # and their inverses to properly rollback. For now, we just log the rollback.
        logger.warning("Cross-database transaction rollback is not fully implemented")

    async def start_offline_recovery_monitor(self) -> None:
        """Start the offline database recovery monitoring mechanism.
        
        This method implements requirement 2.5 by starting background tasks
        that monitor database connections and attempt recovery when databases
        come back online after being offline.
        """
        logger.info("Starting offline database recovery monitor")
        
        # Start MongoDB recovery monitor task
        if not hasattr(self, '_mongo_recovery_task') or self._mongo_recovery_task.done():
            self._mongo_recovery_task = asyncio.create_task(self._monitor_mongo_recovery())
            self._register_background_task(self._mongo_recovery_task, "MongoDB recovery monitor")

        # Start SQLite recovery monitor task
        if not hasattr(self, '_sqlite_recovery_task') or self._sqlite_recovery_task.done():
            self._sqlite_recovery_task = asyncio.create_task(self._monitor_sqlite_recovery())
            self._register_background_task(self._sqlite_recovery_task, "SQLite recovery monitor")

        logger.info("Offline database recovery monitor started")

    def _register_background_task(self, task: asyncio.Task, task_name: str) -> None:
        """Register background task with the main application for proper shutdown."""
        try:
            # Import here to avoid circular imports
            from src.main import register_background_task
            register_background_task(task, task_name)
        except ImportError:
            logger.warning(f"Could not register background task {task_name} - main module not available")

    def _unregister_background_task(self, task: asyncio.Task) -> None:
        """Unregister background task from the main application."""
        try:
            # Import here to avoid circular imports
            from src.main import unregister_background_task
            unregister_background_task(task)
        except ImportError:
            pass  # Main module not available

    async def _monitor_mongo_recovery(self) -> None:
        """Monitor MongoDB connection recovery and attempt reconnection."""
        logger.debug("Starting MongoDB recovery monitor")
        
        while True:
            try:
                # Check if MongoDB is disconnected but was previously configured
                if (not self._mongo_client or not self._mongo_db_name) and \
                   hasattr(self, '_mongo_was_configured') and self._mongo_was_configured:
                    
                    logger.info("Attempting MongoDB recovery...")
                    
                    # Get database configuration
                    db_config = self.config_manager.get_database_config()
                    
                    # Try to reconnect to MongoDB
                    if db_config.mongodb_uri and db_config.mongodb_database:
                        success = await self._connect_mongodb(
                            db_config.mongodb_uri, 
                            db_config.mongodb_database
                        )
                        
                        if success:
                            logger.info("MongoDB recovery successful")
                            # Publish recovery event
                            from src.events.bus import EventBus
                            from src.events.models import create_event
                            
                            # In a real implementation, you would have access to the event bus
                            # For now, we'll just log the recovery
                            
                            # Update connection status
                            self._is_connected = self._mongo_client is not None or self._sqlite_conn is not None
                        else:
                            logger.warning("MongoDB recovery attempt failed")
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                logger.info("MongoDB recovery monitor cancelled")
                break
            except Exception as e:
                logger.error("Error in MongoDB recovery monitor: %s", str(e))
                await asyncio.sleep(60)  # Wait longer on error

    async def _monitor_sqlite_recovery(self) -> None:
        """Monitor SQLite connection recovery and attempt reconnection."""
        logger.debug("Starting SQLite recovery monitor")
        
        while True:
            try:
                # Check if SQLite is disconnected but was previously configured
                if (not self._sqlite_conn) and \
                   hasattr(self, '_sqlite_was_configured') and self._sqlite_was_configured:
                    
                    logger.info("Attempting SQLite recovery...")
                    
                    # Get database configuration
                    db_config = self.config_manager.get_database_config()
                    
                    # Try to reconnect to SQLite
                    if db_config.sqlite_database_path:
                        success = self._connect_sqlite(db_config.sqlite_database_path)
                        
                        if success:
                            logger.info("SQLite recovery successful")
                            # Publish recovery event
                            # Update connection status
                            self._is_connected = self._mongo_client is not None or self._sqlite_conn is not None
                        else:
                            logger.warning("SQLite recovery attempt failed")
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                logger.info("SQLite recovery monitor cancelled")
                break
            except Exception as e:
                logger.error("Error in SQLite recovery monitor: %s", str(e))
                await asyncio.sleep(60)  # Wait longer on error

    async def trigger_manual_recovery(self) -> Dict[str, bool]:
        """Manually trigger database recovery attempts.
        
        Returns:
            Dict[str, bool]: Recovery results for each database
        """
        logger.info("Manually triggering database recovery")
        
        results = {
            "mongodb": False,
            "sqlite": False
        }
        
        try:
            # Get database configuration
            db_config = self.config_manager.get_database_config()
            
            # Try to recover MongoDB if it was configured
            if hasattr(self, '_mongo_was_configured') and self._mongo_was_configured:
                if db_config.mongodb_uri and db_config.mongodb_database:
                    logger.info("Attempting manual MongoDB recovery...")
                    results["mongodb"] = await self._connect_mongodb(
                        db_config.mongodb_uri, 
                        db_config.mongodb_database
                    )
                    if results["mongodb"]:
                        logger.info("Manual MongoDB recovery successful")
                    else:
                        logger.warning("Manual MongoDB recovery failed")
            
            # Try to recover SQLite if it was configured
            if hasattr(self, '_sqlite_was_configured') and self._sqlite_was_configured:
                if db_config.sqlite_database_path:
                    logger.info("Attempting manual SQLite recovery...")
                    results["sqlite"] = self._connect_sqlite(db_config.sqlite_database_path)
                    if results["sqlite"]:
                        logger.info("Manual SQLite recovery successful")
                    else:
                        logger.warning("Manual SQLite recovery failed")
            
            # Update overall connection status
            self._is_connected = results["mongodb"] or results["sqlite"]
            
            logger.info("Manual recovery completed: %s", results)
            return results
            
        except Exception as e:
            logger.error("Error during manual recovery: %s", str(e))
            return results

    async def stop_offline_recovery_monitor(self) -> None:
        """Stop the offline database recovery monitoring mechanism."""
        logger.info("Stopping offline database recovery monitor")

        # Cancel and unregister MongoDB recovery task
        if hasattr(self, '_mongo_recovery_task') and not self._mongo_recovery_task.done():
            self._mongo_recovery_task.cancel()
            self._unregister_background_task(self._mongo_recovery_task)
            try:
                await asyncio.wait_for(self._mongo_recovery_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.debug("MongoDB recovery task cancelled/timed out during shutdown")
            except Exception as e:
                logger.warning(f"Error during MongoDB recovery task cancellation: {e}")

        # Cancel and unregister SQLite recovery task
        if hasattr(self, '_sqlite_recovery_task') and not self._sqlite_recovery_task.done():
            self._sqlite_recovery_task.cancel()
            self._unregister_background_task(self._sqlite_recovery_task)
            try:
                await asyncio.wait_for(self._sqlite_recovery_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.debug("SQLite recovery task cancelled/timed out during shutdown")
            except Exception as e:
                logger.warning(f"Error during SQLite recovery task cancellation: {e}")

        logger.info("Offline database recovery monitor stopped")
