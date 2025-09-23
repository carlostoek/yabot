"""
Database initialization module for the YABOT system.

This module provides functionality for initializing databases with migration detection
as required by the fase1 specification.
"""

from typing import Dict, Any, Optional
import sqlite3
from pymongo.database import Database
from src.database.schemas.sqlite import SQLiteSchemas
from src.database.mongodb import MongoDBHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseInitializer:
    """Handles database initialization with migration detection."""
    
    def __init__(self):
        """Initialize the database initializer."""
        logger.info("DatabaseInitializer initialized")
    
    def initialize_databases(self, mongo_db: Database, sqlite_conn: sqlite3.Connection) -> bool:
        """Initialize both MongoDB and SQLite databases with migration detection.
        
        Args:
            mongo_db (Database): MongoDB database instance
            sqlite_conn (sqlite3.Connection): SQLite database connection
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Starting database initialization with migration detection")
            
            # Check for existing migrations
            migration_status = self._detect_migrations(sqlite_conn, mongo_db)
            
            # Initialize MongoDB
            mongo_success = self._initialize_mongodb(mongo_db, migration_status)
            if not mongo_success:
                logger.error("Failed to initialize MongoDB")
                return False
            
            # Initialize SQLite
            sqlite_success = self._initialize_sqlite(sqlite_conn, migration_status)
            if not sqlite_success:
                logger.error("Failed to initialize SQLite")
                return False
            
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error("Error during database initialization: %s", str(e))
            return False
    
    def _detect_migrations(self, sqlite_conn: sqlite3.Connection, mongo_db: Database) -> Dict[str, Any]:
        """Detect existing migrations and schema versions.
        
        Args:
            sqlite_conn (sqlite3.Connection): SQLite database connection
            mongo_db (Database): MongoDB database instance
            
        Returns:
            Dict[str, Any]: Migration status information
        """
        logger.info("Detecting existing migrations")
        
        migration_status = {
            "sqlite_version": None,
            "mongodb_version": None,
            "requires_migration": False,
            "existing_data": False
        }
        
        try:
            # Check SQLite for existing tables and data
            sqlite_status = self._check_sqlite_migration_status(sqlite_conn)
            migration_status.update(sqlite_status)
            
            # Check MongoDB for existing collections and data
            mongo_status = self._check_mongodb_migration_status(mongo_db)
            migration_status.update(mongo_status)
            
            # Determine if migration is needed
            migration_status["requires_migration"] = (
                sqlite_status["existing_data"] or mongo_status["existing_data"]
            )
            
            logger.info("Migration detection completed: %s", migration_status)
            return migration_status
            
        except Exception as e:
            logger.warning("Error during migration detection: %s", str(e))
            # Continue with initialization even if migration detection fails
            return migration_status
    
    def _check_sqlite_migration_status(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Check SQLite database migration status.
        
        Args:
            conn (sqlite3.Connection): SQLite database connection
            
        Returns:
            Dict[str, Any]: SQLite migration status
        """
        logger.debug("Checking SQLite migration status")
        
        try:
            cursor = conn.cursor()
            
            # Check if tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('user_profiles', 'subscriptions')")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Check for existing data
            existing_data = False
            if "user_profiles" in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM user_profiles")
                count = cursor.fetchone()[0]
                existing_data = count > 0
            
            status = {
                "sqlite_version": "1.0",  # Default version
                "existing_data": existing_data
            }
            
            logger.debug("SQLite migration status: %s", status)
            return status
            
        except Exception as e:
            logger.warning("Error checking SQLite migration status: %s", str(e))
            return {
                "sqlite_version": None,
                "existing_data": False
            }
    
    def _check_mongodb_migration_status(self, db: Database) -> Dict[str, Any]:
        """Check MongoDB migration status.
        
        Args:
            db (Database): MongoDB database instance
            
        Returns:
            Dict[str, Any]: MongoDB migration status
        """
        logger.debug("Checking MongoDB migration status")
        
        try:
            # Get collection names
            collections = db.list_collection_names()
            
            # Check for required collections
            required_collections = ["users", "narrative_fragments", "items"]
            existing_collections = [col for col in required_collections if col in collections]
            
            # Check for existing data
            existing_data = False
            if "users" in existing_collections:
                count = db["users"].count_documents({})
                existing_data = count > 0
            
            status = {
                "mongodb_version": "1.0",  # Default version
                "existing_data": existing_data
            }
            
            logger.debug("MongoDB migration status: %s", status)
            return status
            
        except Exception as e:
            logger.warning("Error checking MongoDB migration status: %s", str(e))
            return {
                "mongodb_version": None,
                "existing_data": False
            }
    
    def _initialize_mongodb(self, db: Database, migration_status: Dict[str, Any]) -> bool:
        """Initialize MongoDB collections.
        
        Args:
            db (Database): MongoDB database instance
            migration_status (Dict[str, Any]): Migration status information
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        logger.info("Initializing MongoDB collections")
        
        try:
            # Create MongoDB handler
            mongo_handler = MongoDBHandler(db)
            
            # Initialize collections
            success = mongo_handler.initialize_collections()
            
            if success:
                logger.info("MongoDB collections initialized successfully")
            else:
                logger.error("Failed to initialize MongoDB collections")
            
            return success
            
        except Exception as e:
            logger.error("Error initializing MongoDB: %s", str(e))
            return False
    
    def _initialize_sqlite(self, conn: sqlite3.Connection, migration_status: Dict[str, Any]) -> bool:
        """Initialize SQLite tables.
        
        Args:
            conn (sqlite3.Connection): SQLite database connection
            migration_status (Dict[str, Any]): Migration status information
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        logger.info("Initializing SQLite tables")
        
        try:
            # Initialize database with schemas
            success = SQLiteSchemas.initialize_database(conn)
            
            if success:
                logger.info("SQLite tables initialized successfully")
            else:
                logger.error("Failed to initialize SQLite tables")
            
            return success
            
        except Exception as e:
            logger.error("Error initializing SQLite: %s", str(e))
            return False


# Convenience function for easy initialization
def initialize_databases(mongo_db: Database, sqlite_conn: sqlite3.Connection) -> bool:
    """Convenience function to initialize databases.
    
    Args:
        mongo_db (Database): MongoDB database instance
        sqlite_conn (sqlite3.Connection): SQLite database connection
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    initializer = DatabaseInitializer()
    return initializer.initialize_databases(mongo_db, sqlite_conn)