"""
Database Initialization - Migration Detection

This module handles database initialization with migration detection
to ensure proper setup of MongoDB and SQLite collections/tables.
"""
from datetime import datetime
import asyncio
from typing import List, Dict, Any, Optional

# Import database handlers
from .mongodb import MongoDBHandler
from .sqlite import SQLiteHandler
from .schemas.mongo import DatabaseMigration as MongoMigration
from .schemas.sqlite import Migration as SqlMigration
from src.utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class DatabaseInitializer:
    """
    Handles database initialization with migration detection for MongoDB and SQLite
    """
    def __init__(self, mongo_handler: MongoDBHandler, sqlite_handler: SQLiteHandler):
        self.mongo_handler = mongo_handler
        self.sqlite_handler = sqlite_handler
        self.logger = logger

    async def detect_migrations_needed(self) -> Dict[str, Any]:
        """
        Detect if any migrations are needed for the database collections/tables
        
        Returns:
            Dictionary containing migration status for each database
        """
        try:
            self.logger.info("Starting migration detection")
            
            # Check if collections/tables exist
            migrations_needed = {
                'mongodb': {
                    'users_collection_exists': await self._check_mongo_collection_exists('users'),
                    'narrative_fragments_collection_exists': await self._check_mongo_collection_exists('narrative_fragments'),
                    'items_collection_exists': await self._check_mongo_collection_exists('items'),
                    'migrations_collection_exists': await self._check_mongo_collection_exists('migrations'),
                },
                'sqlite': {
                    'user_profiles_table_exists': self._check_sqlite_table_exists('user_profiles'),
                    'subscriptions_table_exists': self._check_sqlite_table_exists('subscriptions'),
                    'migrations_table_exists': self._check_sqlite_table_exists('database_migrations'),
                }
            }
            
            # Determine if any migrations are needed
            mongodb_needs_migration = not all([
                migrations_needed['mongodb']['users_collection_exists'],
                migrations_needed['mongodb']['narrative_fragments_collection_exists'],
                migrations_needed['mongodb']['items_collection_exists']
            ])
            
            sqlite_needs_migration = not all([
                migrations_needed['sqlite']['user_profiles_table_exists'],
                migrations_needed['sqlite']['subscriptions_table_exists']
            ])
            
            migrations_needed['mongodb_needs_migration'] = mongodb_needs_migration
            migrations_needed['sqlite_needs_migration'] = sqlite_needs_migration
            migrations_needed['any_needed'] = mongodb_needs_migration or sqlite_needs_migration
            
            self.logger.info("Migration detection completed", 
                           migrations_needed=migrations_needed['any_needed'])
            
            return migrations_needed
        except Exception as e:
            self.logger.error("Error during migration detection", error=str(e))
            raise

    async def _check_mongo_collection_exists(self, collection_name: str) -> bool:
        """
        Check if a MongoDB collection exists
        
        Args:
            collection_name: Name of the collection to check
            
        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = await self.mongo_handler.db.list_collection_names()
            exists = collection_name in collections
            
            self.logger.info(f"MongoDB collection check", 
                           collection=collection_name, 
                           exists=exists)
            return exists
        except Exception as e:
            self.logger.error(f"Error checking MongoDB collection", 
                            collection=collection_name, 
                            error=str(e))
            return False

    def _check_sqlite_table_exists(self, table_name: str) -> bool:
        """
        Check if a SQLite table exists
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            from sqlalchemy import inspect
            inspector = inspect(self.sqlite_handler.engine)
            exists = inspector.has_table(table_name)
            
            self.logger.info(f"SQLite table check", 
                           table=table_name, 
                           exists=exists)
            return exists
        except Exception as e:
            self.logger.error(f"Error checking SQLite table", 
                            table=table_name, 
                            error=str(e))
            return False

    async def run_migrations(self):
        """
        Run necessary database migrations
        """
        try:
            self.logger.info("Starting database migrations")
            
            # Run MongoDB migrations
            await self._run_mongo_migrations()
            
            # Run SQLite migrations
            self._run_sqlite_migrations()
            
            self.logger.info("Database migrations completed successfully")
        except Exception as e:
            self.logger.error("Error during migration execution", error=str(e))
            raise

    async def _run_mongo_migrations(self):
        """
        Run MongoDB-specific migrations
        """
        try:
            # Ensure necessary collections exist
            collections_to_create = ['users', 'narrative_fragments', 'items']
            
            for collection_name in collections_to_create:
                if not await self._check_mongo_collection_exists(collection_name):
                    # Create the collection
                    await self.mongo_handler.db.create_collection(collection_name)
                    self.logger.info(f"Created MongoDB collection", collection=collection_name)
                    
                    # Add initial indexes if needed
                    if collection_name == 'users':
                        await self.mongo_handler.db['users'].create_index('user_id', unique=True)
                        self.logger.info(f"Created index on user_id", collection='users')
                        
                    elif collection_name == 'narrative_fragments':
                        await self.mongo_handler.db['narrative_fragments'].create_index('fragment_id', unique=True)
                        self.logger.info(f"Created index on fragment_id", collection='narrative_fragments')
                        
                    elif collection_name == 'items':
                        await self.mongo_handler.db['items'].create_index('item_id', unique=True)
                        self.logger.info(f"Created index on item_id", collection='items')
            
            # Create migration record if needed
            if not await self._check_mongo_collection_exists('migrations'):
                await self.mongo_handler.db.create_collection('migrations')
                await self.mongo_handler.db['migrations'].create_index('migration_id', unique=True)
                self.logger.info(f"Created migration tracking collection", collection='migrations')
            
            self.logger.info("MongoDB migrations completed")
        except Exception as e:
            self.logger.error("Error during MongoDB migrations", error=str(e))
            raise

    def _run_sqlite_migrations(self):
        """
        Run SQLite-specific migrations
        """
        try:
            # Import the create_all_tables function
            from .schemas.sqlite import create_all_tables
            
            # Create all tables if they don't exist
            create_all_tables(self.sqlite_handler.engine)
            
            self.logger.info("SQLite migrations completed")
        except Exception as e:
            self.logger.error("Error during SQLite migrations", error=str(e))
            raise

    async def initialize_databases(self) -> bool:
        """
        Initialize databases with migration detection and execution
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Starting database initialization")
            
            # Detect if migrations are needed
            migrations_needed = await self.detect_migrations_needed()
            
            if migrations_needed['any_needed']:
                self.logger.info("Migrations needed, running migrations")
                await self.run_migrations()
            else:
                self.logger.info("No migrations needed, databases already initialized")
            
            # Verify initialization
            verification_result = await self._verify_initialization()
            
            if verification_result:
                self.logger.info("Database initialization completed successfully")
                return True
            else:
                self.logger.warning("Database initialization completed but verification failed")
                return False
                
        except Exception as e:
            self.logger.error("Error during database initialization", error=str(e))
            return False

    async def _verify_initialization(self) -> bool:
        """
        Verify that database initialization was successful
        
        Returns:
            True if verification passed, False otherwise
        """
        try:
            # Verify MongoDB collections
            mongo_verification = all([
                await self._check_mongo_collection_exists('users'),
                await self._check_mongo_collection_exists('narrative_fragments'),
                await self._check_mongo_collection_exists('items')
            ])
            
            # Verify SQLite tables
            sqlite_verification = all([
                self._check_sqlite_table_exists('user_profiles'),
                self._check_sqlite_table_exists('subscriptions')
            ])
            
            self.logger.info("Database verification results", 
                           mongo_ok=mongo_verification,
                           sqlite_ok=sqlite_verification)
            
            return mongo_verification and sqlite_verification
        except Exception as e:
            self.logger.error("Error during database verification", error=str(e))
            return False


async def initialize_database_system(mongo_handler: MongoDBHandler, sqlite_handler: SQLiteHandler) -> bool:
    """
    Initialize the database system with migration detection and execution
    
    Args:
        mongo_handler: MongoDB handler instance
        sqlite_handler: SQLite handler instance
        
    Returns:
        True if initialization successful, False otherwise
    """
    initializer = DatabaseInitializer(mongo_handler, sqlite_handler)
    return await initializer.initialize_databases()