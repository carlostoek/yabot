"""
Database Manager for YABOT

This module implements the DatabaseManager component that handles both MongoDB and SQLite connections.
It follows the requirements for dual database support and integrates with the existing configuration system.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text

from src.core.models import DatabaseConfig
from src.utils.logger import get_logger


class DatabaseManager:
    """
    DatabaseManager handles both MongoDB and SQLite connections with connection pooling
    and integrates with the existing configuration system.
    
    Implements requirement 1.1: Central Database System
    1. WHEN the system initializes THEN it SHALL establish connections to both MongoDB and SQLite databases
    2. WHEN storing user dynamic states THEN the system SHALL use MongoDB for flexible schema requirements
    3. WHEN storing subscription data and user profiles THEN the system SHALL use SQLite for ACID compliance
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = get_logger(self.__class__.__name__)
        
        # Use provided config if available, otherwise use config manager
        if config is not None:
            self.config = config
            # If config is provided as dict, we need to convert it to DatabaseConfig
            from src.core.models import DatabaseConfig
            try:
                self.database_config = DatabaseConfig(**config)
            except Exception:
                # Fallback: create a basic config from the provided dict
                self.database_config = DatabaseConfig(
                    mongodb_uri=config.get('mongodb_uri', 'mongodb://localhost:27017'),
                    mongodb_database=config.get('mongodb_database', 'yabot'),
                    sqlite_database_path=config.get('sqlite_database_path', './yabot.db'),
                    pool_size=config.get('sqlite_config', {}).get('pool_size', 20) if 'sqlite_config' in config else config.get('pool_size', 20),
                    max_overflow=config.get('sqlite_config', {}).get('max_overflow', 30) if 'sqlite_config' in config else config.get('max_overflow', 30),
                    pool_timeout=config.get('sqlite_config', {}).get('pool_timeout', 10) if 'sqlite_config' in config else config.get('pool_timeout', 10),
                    pool_recycle=config.get('sqlite_config', {}).get('pool_recycle', 3600) if 'sqlite_config' in config else config.get('pool_recycle', 3600),
                    mongodb_min_pool_size=config.get('mongodb_config', {}).get('min_pool_size', 5) if 'mongodb_config' in config else config.get('mongodb_min_pool_size', 5),
                    mongodb_max_pool_size=config.get('mongodb_config', {}).get('max_pool_size', 50) if 'mongodb_config' in config else config.get('mongodb_max_pool_size', 50),
                    mongodb_max_idle_time=config.get('mongodb_config', {}).get('max_idle_time', 30000) if 'mongodb_config' in config else config.get('mongodb_max_idle_time', 30000),
                    mongodb_server_selection_timeout=config.get('mongodb_config', {}).get('server_selection_timeout', 5000) if 'mongodb_config' in config else config.get('mongodb_server_selection_timeout', 5000),
                    mongodb_socket_timeout=config.get('mongodb_config', {}).get('socket_timeout', 10000) if 'mongodb_config' in config else config.get('mongodb_socket_timeout', 10000)
                )
        else:
            # Use config manager when no config is provided
            from src.config.manager import get_config_manager
            self.config_manager = get_config_manager()
            self.database_config = self.config_manager.get_database_config()
        
        # Initialize database connections
        self._mongo_client: Optional[AsyncIOMotorClient] = None
        self._mongo_db = None
        self._sqlite_engine: Optional[AsyncEngine] = None
        
        # Track connection status
        self._mongo_connected = False
        self._sqlite_connected = False
        self._connected = False  # Overall connection status
    
    async def connect_all(self) -> bool:
        """
        Initialize all database connections with connection pooling.
        
        Returns:
            True if all connections established successfully, False otherwise
        """
        success = True
        
        # Connect to MongoDB
        try:
            self.logger.info("Connecting to MongoDB", uri=self.database_config.mongodb_uri)
            self._mongo_client = AsyncIOMotorClient(
                self.database_config.mongodb_uri,
                minPoolSize=self.database_config.mongodb_min_pool_size,
                maxPoolSize=self.database_config.mongodb_max_pool_size,
                maxIdleTimeMS=self.database_config.mongodb_max_idle_time,
                serverSelectionTimeoutMS=self.database_config.mongodb_server_selection_timeout,
                socketTimeoutMS=self.database_config.mongodb_socket_timeout
            )
            # Test the MongoDB connection
            await self._mongo_client.admin.command('ping')
            self._mongo_db = self._mongo_client[self.database_config.mongodb_database]
            self._mongo_connected = True
            self.logger.info("MongoDB connection established successfully")
        except Exception as e:
            self.logger.error(
                "Failed to connect to MongoDB",
                error=str(e),
                error_type=type(e).__name__
            )
            self._mongo_connected = False
            success = False
        
        # Connect to SQLite
        try:
            self.logger.info("Connecting to SQLite", path=self.database_config.sqlite_database_path)
            # Create the async engine for SQLite with connection pooling
            sqlite_url = f"sqlite+aiosqlite:///{self.database_config.sqlite_database_path}"
            self._sqlite_engine = create_async_engine(
                sqlite_url,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=self.database_config.pool_size,
                max_overflow=self.database_config.max_overflow,
                pool_timeout=self.database_config.pool_timeout,
                pool_recycle=self.database_config.pool_recycle,
                echo=False  # Set to True for SQL debugging
            )
            # Test the SQLite connection
            async with self._sqlite_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            self._sqlite_connected = True
            self.logger.info("SQLite connection established successfully")
        except Exception as e:
            self.logger.error(
                "Failed to connect to SQLite",
                error=str(e),
                error_type=type(e).__name__,
                path=self.database_config.sqlite_database_path
            )
            self._sqlite_connected = False
            success = False
        
        # Set overall connection status
        self._connected = success
        return success
    
    def get_mongo_db(self):
        """
        Get the MongoDB database instance.
        
        Returns:
            MongoDB database instance if connected, None otherwise
        """
        if not self._mongo_connected:
            self.logger.warning("MongoDB is not connected")
            return None
        return self._mongo_db
    
    def get_mongo_client(self):
        """
        Get the MongoDB client instance.
        
        Returns:
            MongoDB client instance if connected, None otherwise
        """
        if not self._mongo_connected:
            self.logger.warning("MongoDB is not connected")
            return None
        return self._mongo_client
    
    def get_sqlite_engine(self) -> Optional[AsyncEngine]:
        """
        Get the SQLite engine instance.
        
        Returns:
            SQLite engine instance if connected, None otherwise
        """
        if not self._sqlite_connected:
            self.logger.warning("SQLite is not connected")
            return None
        return self._sqlite_engine
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check database connectivity health.
        
        Returns:
            Dictionary with health status for each database
        """
        health_status = {
            "mongo_connected": self._mongo_connected,
            "sqlite_connected": self._sqlite_connected,
            "overall_healthy": self._mongo_connected and self._sqlite_connected
        }
        
        # Additional checks for MongoDB
        if self._mongo_connected:
            try:
                await self._mongo_client.admin.command('ping')
                health_status["mongo_ping"] = True
            except Exception as e:
                health_status["mongo_ping"] = False
                health_status["mongo_error"] = str(e)
        
        # Additional checks for SQLite
        if self._sqlite_connected and self._sqlite_engine:
            try:
                async with self._sqlite_engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                health_status["sqlite_ping"] = True
            except Exception as e:
                health_status["sqlite_ping"] = False
                health_status["sqlite_error"] = str(e)
        
        return health_status
    
    async def close_connections(self):
        """
        Close all database connections gracefully.
        """
        if self._mongo_client:
            self._mongo_client.close()
            self._mongo_connected = False
            self.logger.info("MongoDB connection closed")
        
        if self._sqlite_engine:
            await self._sqlite_engine.dispose()
            self._sqlite_connected = False
            self.logger.info("SQLite engine disposed")
        
        # Update overall connection status
        self._connected = False
    
    async def ensure_collections(self) -> bool:
        """
        Ensure required MongoDB collections exist.
        
        Implements requirement 1.2: Database Collections and Tables
        1. WHEN the system starts THEN it SHALL create/verify the following MongoDB collections:
           - Users (dynamic state, preferences, current context)
           - NarrativeFragments (story content, choices, metadata)
           - Items (virtual items, gifts, achievements)
        
        Returns:
            True if all collections exist or were created successfully, False otherwise
        """
        try:
            db = self.get_mongo_db()
            if db is None:
                self.logger.error("Cannot ensure collections - MongoDB not connected")
                return False
            
            # List of required collections
            required_collections = [
                "users",
                "narrative_fragments", 
                "items"
            ]
            
            existing_collections = await db.list_collection_names()
            
            for collection_name in required_collections:
                if collection_name not in existing_collections:
                    # Create the collection
                    await db.create_collection(collection_name)
                    self.logger.info(f"Created MongoDB collection: {collection_name}")
                else:
                    self.logger.info(f"MongoDB collection exists: {collection_name}")
            
            # Create indexes for performance
            # Users collection indexes
            await db.users.create_index("user_id", unique=True)
            await db.users.create_index("created_at")
            
            # Narrative fragments indexes
            await db.narrative_fragments.create_index("fragment_id", unique=True)
            await db.narrative_fragments.create_index("metadata.tags")
            
            # Items indexes
            await db.items.create_index("item_id", unique=True)
            
            self.logger.info("MongoDB collections verified and indexes created")
            return True
            
        except Exception as e:
            self.logger.error(
                "Error ensuring MongoDB collections",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def ensure_tables(self) -> bool:
        """
        Ensure required SQLite tables exist.
        
        Implements requirement 1.2: Database Collections and Tables
        2. WHEN the system starts THEN it SHALL create/verify the following SQLite tables:
           - Subscriptions (user_id, plan, status, dates)
           - UserProfiles (user_id, telegram_data, registration_info)
        
        Returns:
            True if all tables exist or were created successfully, False otherwise
        """
        try:
            engine = self.get_sqlite_engine()
            if not engine:
                self.logger.error("Cannot ensure tables - SQLite not connected")
                return False
            
            # SQL statements to create tables
            create_user_profiles_sql = """
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
            );
            """
            
            create_subscriptions_sql = """
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
            );
            """
            
            # Execute the table creation statements
            async with engine.connect() as conn:
                await conn.execute(text(create_user_profiles_sql))
                await conn.execute(text(create_subscriptions_sql))
                await conn.commit()
            
            self.logger.info("SQLite tables verified and created if needed")
            return True
            
        except Exception as e:
            self.logger.error(
                "Error ensuring SQLite tables",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def initialize_databases(self) -> bool:
        """
        Initialize both databases by connecting and creating required collections/tables.
        
        Returns:
            True if initialization successful, False otherwise
        """
        # Connect to both databases
        if not await self.connect_all():
            self.logger.error("Failed to connect to databases")
            return False
        
        # Ensure MongoDB collections exist
        if not await self.ensure_collections():
            self.logger.error("Failed to ensure MongoDB collections")
            return False
        
        # Ensure SQLite tables exist
        if not await self.ensure_tables():
            self.logger.error("Failed to ensure SQLite tables")
            return False
        
        self.logger.info("Database initialization completed successfully")
        return True

    # User Management Methods

    async def create_user_atomic(self, user_id: str, mongo_doc: Dict[str, Any], sqlite_profile: Dict[str, Any]) -> bool:
        """
        Create user in both databases atomically

        Args:
            user_id: User ID
            mongo_doc: MongoDB user document
            sqlite_profile: SQLite user profile data

        Returns:
            True if both creations successful, False otherwise
        """
        try:
            # Insert into MongoDB
            mongo_db = self.get_mongo_db()
            if mongo_db is None:
                self.logger.error("MongoDB not available")
                return False

            await mongo_db.users.insert_one(mongo_doc)

            # Insert into SQLite
            sqlite_engine = self.get_sqlite_engine()
            if not sqlite_engine:
                self.logger.error("SQLite not available")
                # Rollback MongoDB insertion
                await mongo_db.users.delete_one({"user_id": user_id})
                return False

            async with sqlite_engine.connect() as conn:
                from sqlalchemy import text
                stmt = text("""INSERT INTO user_profiles
                       (user_id, telegram_user_id, username, first_name, last_name,
                        language_code, registration_date, last_login, is_active)
                       VALUES (:user_id, :telegram_user_id, :username, :first_name, :last_name,
                        :language_code, :registration_date, :last_login, :is_active)""")
                await conn.execute(stmt, sqlite_profile)
                await conn.commit()

            self.logger.info("User created atomically", user_id=user_id)
            return True

        except Exception as e:
            self.logger.error("Error in atomic user creation", error=str(e), user_id=user_id)
            # Attempt rollback
            try:
                mongo_db = self.get_mongo_db()
                if mongo_db:
                    await mongo_db.users.delete_one({"user_id": user_id})
            except:
                pass
            return False

    async def get_user_from_mongo(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from MongoDB

        Args:
            user_id: User ID

        Returns:
            User document or None if not found
        """
        try:
            mongo_db = self.get_mongo_db()
            if mongo_db is None:
                return None

            user_doc = await mongo_db.users.find_one({"user_id": user_id})
            if user_doc:
                # Convert ObjectId to string for JSON serialization
                user_doc["_id"] = str(user_doc["_id"])
                return user_doc
            return None

        except Exception as e:
            self.logger.error("Error getting user from MongoDB", error=str(e), user_id=user_id)
            return None

    async def get_user_profile_from_sqlite(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile from SQLite

        Args:
            user_id: User ID

        Returns:
            User profile dict or None if not found
        """
        try:
            sqlite_engine = self.get_sqlite_engine()
            if not sqlite_engine:
                return None

            async with sqlite_engine.connect() as conn:
                from sqlalchemy import text
                stmt = text("SELECT * FROM user_profiles WHERE user_id = :user_id")
                result = await conn.execute(stmt, {"user_id": user_id})
                row = await result.fetchone()
                if row:
                    # Convert row to dict
                    return dict(row._mapping)
                return None

        except Exception as e:
            self.logger.error("Error getting user profile from SQLite", error=str(e), user_id=user_id)
            return None

    async def update_user_in_mongo(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update user data in MongoDB

        Args:
            user_id: User ID
            update_data: Update operations dict

        Returns:
            True if update successful, False otherwise
        """
        try:
            mongo_db = self.get_mongo_db()
            if mongo_db is None:
                return False

            result = await mongo_db.users.update_one(
                {"user_id": user_id},
                update_data
            )

            return result.modified_count > 0

        except Exception as e:
            self.logger.error("Error updating user in MongoDB", error=str(e), user_id=user_id)
            return False

    async def update_user_profile_in_sqlite(self, user_id: str, profile_updates: Dict[str, Any]) -> bool:
        """
        Update user profile in SQLite

        Args:
            user_id: User ID
            profile_updates: Profile data to update

        Returns:
            True if update successful, False otherwise
        """
        try:
            sqlite_engine = self.get_sqlite_engine()
            if not sqlite_engine:
                return False

            # Build update statement dynamically
            set_clauses = []
            values = []

            for key, value in profile_updates.items():
                if key != 'user_id':  # Don't update user_id
                    set_clauses.append(f"{key} = ?")
                    values.append(value)

            values.append(user_id)

            if not set_clauses:
                return True  # Nothing to update

            query = f"UPDATE user_profiles SET {', '.join(set_clauses)} WHERE user_id = ?"

            async with sqlite_engine.connect() as conn:
                result = await conn.execute(query, values)
                await conn.commit()
                return result.rowcount > 0

        except Exception as e:
            self.logger.error("Error updating user profile in SQLite", error=str(e), user_id=user_id)
            return False

    async def get_subscription_from_sqlite(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription data from SQLite

        Args:
            user_id: User ID

        Returns:
            Subscription dict or None if not found
        """
        try:
            sqlite_engine = self.get_sqlite_engine()
            if not sqlite_engine:
                return None

            async with sqlite_engine.connect() as conn:
                from sqlalchemy import text
                stmt = text("""SELECT * FROM subscriptions
                       WHERE user_id = :user_id AND status IN ('active', 'pending')
                       ORDER BY created_at DESC LIMIT 1""")
                result = await conn.execute(stmt, {"user_id": user_id})
                row = await result.fetchone()
                if row:
                    return dict(row._mapping)
                return None

        except Exception as e:
            self.logger.error("Error getting subscription from SQLite", error=str(e), user_id=user_id)
            return None

    async def delete_user_from_mongo(self, user_id: str) -> bool:
        """
        Delete user from MongoDB

        Args:
            user_id: User ID

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            mongo_db = self.get_mongo_db()
            if mongo_db is None:
                return False

            result = await mongo_db.users.delete_one({"user_id": user_id})
            return result.deleted_count > 0

        except Exception as e:
            self.logger.error("Error deleting user from MongoDB", error=str(e), user_id=user_id)
            return False

    async def delete_user_profile_from_sqlite(self, user_id: str) -> bool:
        """
        Delete user profile from SQLite

        Args:
            user_id: User ID

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            sqlite_engine = self.get_sqlite_engine()
            if not sqlite_engine:
                return False

            async with sqlite_engine.connect() as conn:
                from sqlalchemy import text
                stmt = text("DELETE FROM user_profiles WHERE user_id = :user_id")
                result = await conn.execute(stmt, {"user_id": user_id})
                await conn.commit()
                return result.rowcount > 0

        except Exception as e:
            self.logger.error("Error deleting user profile from SQLite", error=str(e), user_id=user_id)
            return False

    async def rollback_user_creation(self, user_id: str) -> bool:
        """
        Rollback user creation by deleting user from both databases

        Args:
            user_id: User ID to rollback

        Returns:
            True if rollback successful, False otherwise
        """
        try:
            # Delete from MongoDB first
            mongo_success = True
            if self._mongo_connected:
                mongo_db = self.get_mongo_db()
                if mongo_db is not None:
                    result = await mongo_db.users.delete_one({"user_id": user_id})
                    mongo_success = result.deleted_count > 0

            # Delete from SQLite
            sqlite_success = True
            if self._sqlite_connected:
                sqlite_success = await self.delete_user_profile_from_sqlite(user_id)

            self.logger.info("User creation rolled back", user_id=user_id, 
                           mongo_rollback=mongo_success, sqlite_rollback=sqlite_success)
            return mongo_success and sqlite_success

        except Exception as e:
            self.logger.error("Error rolling back user creation", error=str(e), user_id=user_id)
            return False

    # Subscription Management Methods

    async def create_subscription(self, subscription_data: Dict[str, Any]) -> bool:
        """
        Create a new subscription in SQLite

        Args:
            subscription_data: Subscription data to insert

        Returns:
            True if creation successful, False otherwise
        """
        try:
            sqlite_engine = self.get_sqlite_engine()
            if not sqlite_engine:
                return False

            async with sqlite_engine.connect() as conn:
                from sqlalchemy import text
                stmt = text("""INSERT INTO subscriptions
                       (user_id, plan_type, status, start_date, end_date, created_at, updated_at)
                       VALUES (:user_id, :plan_type, :status, :start_date, :end_date, :created_at, :updated_at)""")
                await conn.execute(stmt, subscription_data)
                await conn.commit()

            self.logger.info("Subscription created", user_id=subscription_data.get('user_id'))
            return True

        except Exception as e:
            self.logger.error("Error creating subscription", error=str(e), user_id=subscription_data.get('user_id'))
            return False

    async def update_subscription(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update subscription data in SQLite

        Args:
            user_id: User ID
            update_data: Subscription data to update

        Returns:
            True if update successful, False otherwise
        """
        try:
            sqlite_engine = self.get_sqlite_engine()
            if not sqlite_engine:
                return False

            # Build update statement dynamically
            set_clauses = []
            values = []

            for key, value in update_data.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)

            values.append(user_id)

            if not set_clauses:
                return True  # Nothing to update

            query = f"UPDATE subscriptions SET {', '.join(set_clauses)} WHERE user_id = ?"

            async with sqlite_engine.connect() as conn:
                result = await conn.execute(query, values)
                await conn.commit()
                return result.rowcount > 0

        except Exception as e:
            self.logger.error("Error updating subscription", error=str(e), user_id=user_id)
            return False

    # Narrative Management Methods

    async def get_narrative_from_mongo(self, fragment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get narrative fragment from MongoDB

        Args:
            fragment_id: Fragment ID

        Returns:
            Narrative fragment document or None if not found
        """
        try:
            mongo_db = self.get_mongo_db()
            if mongo_db is None:
                return None

            fragment_doc = await mongo_db.narrative_fragments.find_one({"fragment_id": fragment_id})
            if fragment_doc:
                # Convert ObjectId to string for JSON serialization
                fragment_doc["_id"] = str(fragment_doc["_id"])
                return fragment_doc
            return None

        except Exception as e:
            self.logger.error("Error getting narrative from MongoDB", error=str(e), fragment_id=fragment_id)
            return None

    async def get_related_narratives(self, fragment_id: str, tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get related narrative fragments based on tags

        Args:
            fragment_id: Current fragment ID
            tags: Tags to search for related fragments

        Returns:
            List of related narrative fragments
        """
        try:
            mongo_db = self.get_mongo_db()
            if mongo_db is None:
                return []

            # Build query based on tags
            query = {"fragment_id": {"$ne": fragment_id}}  # Exclude current fragment

            if tags:
                query["metadata.tags"] = {"$in": tags}

            cursor = mongo_db.narrative_fragments.find(query).limit(10)  # Limit to 10 results
            related_fragments = []

            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                related_fragments.append(doc)

            return related_fragments

        except Exception as e:
            self.logger.error("Error getting related narratives", error=str(e), fragment_id=fragment_id)
            return []


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """
    Get or create the global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def reset_database_manager():
    """
    Reset the global database manager instance (useful for testing).
    """
    global _db_manager
    if _db_manager:
        await _db_manager.close_connections()
        _db_manager = None