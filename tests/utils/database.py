"""
Database Test Utilities

This module provides comprehensive utilities for testing database operations in the YABOT system.
Following the Testing Strategy from Fase1 requirements, these utilities provide fixtures
and helper functions for both MongoDB and SQLite database testing with proper isolation,
cleanup, and realistic test data generation.
"""
import asyncio
import tempfile
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

from src.database.manager import DatabaseManager
from src.events.models import (
    UserInteractionEvent, UserRegistrationEvent, ReactionDetectedEvent,
    DecisionMadeEvent, SubscriptionUpdatedEvent, EventStatus
)
from src.utils.logger import get_logger


class DatabaseTestConfig:
    """Test configuration for database connections"""

    def __init__(self):
        self.mongodb_uri = "mongodb://localhost:27017"
        self.mongodb_database = f"yabot_test_{uuid.uuid4().hex[:8]}"
        self.sqlite_database_path = None  # Will be set to temp file
        self.mongodb_min_pool_size = 1
        self.mongodb_max_pool_size = 5
        self.mongodb_max_idle_time = 10000
        self.mongodb_server_selection_timeout = 2000
        self.mongodb_socket_timeout = 5000
        self.pool_size = 5
        self.max_overflow = 10
        self.pool_timeout = 5
        self.pool_recycle = 1800


class TestDatabaseManager:
    """
    Test database manager that provides isolated test databases

    This class provides separate test databases for MongoDB and SQLite
    to ensure test isolation and prevent interference with production data.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.config = DatabaseTestConfig()

        # Create temporary SQLite database
        self._temp_db_fd, self.config.sqlite_database_path = tempfile.mkstemp(suffix='.db')

        self._mongo_client: Optional[AsyncIOMotorClient] = None
        self._mongo_db = None
        self._sqlite_engine: Optional[AsyncEngine] = None

        self._mongo_connected = False
        self._sqlite_connected = False

        # Track created test data for cleanup
        self.created_users = set()
        self.created_fragments = set()
        self.created_subscriptions = set()

    async def setup(self) -> bool:
        """
        Set up test databases

        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Connect to MongoDB test database
            self._mongo_client = AsyncIOMotorClient(
                self.config.mongodb_uri,
                minPoolSize=self.config.mongodb_min_pool_size,
                maxPoolSize=self.config.mongodb_max_pool_size,
                serverSelectionTimeoutMS=self.config.mongodb_server_selection_timeout
            )

            # Test MongoDB connection
            await self._mongo_client.admin.command('ping')
            self._mongo_db = self._mongo_client[self.config.mongodb_database]
            self._mongo_connected = True

            # Setup SQLite engine
            sqlite_url = f"sqlite+aiosqlite:///{self.config.sqlite_database_path}"
            self._sqlite_engine = create_async_engine(
                sqlite_url,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                echo=False
            )

            # Test SQLite connection
            async with self._sqlite_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            self._sqlite_connected = True

            # Create collections and tables
            await self._create_test_collections()
            await self._create_test_tables()

            self.logger.info("Test databases set up successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to setup test databases: {str(e)}")
            return False

    async def cleanup(self):
        """Clean up test databases and connections"""
        try:
            # Clean up MongoDB test database
            if self._mongo_client and self._mongo_connected:
                await self._mongo_client.drop_database(self.config.mongodb_database)
                self._mongo_client.close()
                self._mongo_connected = False

            # Clean up SQLite database
            if self._sqlite_engine and self._sqlite_connected:
                await self._sqlite_engine.dispose()
                self._sqlite_connected = False

            # Remove temporary SQLite file
            try:
                os.close(self._temp_db_fd)
                os.unlink(self.config.sqlite_database_path)
            except (OSError, FileNotFoundError):
                pass

            self.logger.info("Test databases cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    async def _create_test_collections(self):
        """Create test MongoDB collections with indexes"""
        if not self._mongo_db:
            return

        collections = ["users", "narrative_fragments", "items"]

        for collection_name in collections:
            await self._mongo_db.create_collection(collection_name)

        # Create indexes
        await self._mongo_db.users.create_index("user_id", unique=True)
        await self._mongo_db.users.create_index("created_at")
        await self._mongo_db.narrative_fragments.create_index("fragment_id", unique=True)
        await self._mongo_db.narrative_fragments.create_index("metadata.tags")
        await self._mongo_db.items.create_index("item_id", unique=True)

    async def _create_test_tables(self):
        """Create test SQLite tables"""
        if not self._sqlite_engine:
            return

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

        async with self._sqlite_engine.connect() as conn:
            await conn.execute(text(create_user_profiles_sql))
            await conn.execute(text(create_subscriptions_sql))
            await conn.commit()

    def get_mongo_db(self):
        """Get test MongoDB database"""
        return self._mongo_db if self._mongo_connected else None

    def get_sqlite_engine(self) -> Optional[AsyncEngine]:
        """Get test SQLite engine"""
        return self._sqlite_engine if self._sqlite_connected else None

    async def reset_data(self):
        """Reset all test data while keeping schema"""
        if self._mongo_db:
            collections = await self._mongo_db.list_collection_names()
            for collection in collections:
                await self._mongo_db[collection].delete_many({})

        if self._sqlite_engine:
            async with self._sqlite_engine.connect() as conn:
                await conn.execute(text("DELETE FROM subscriptions"))
                await conn.execute(text("DELETE FROM user_profiles"))
                await conn.commit()

        # Reset tracking sets
        self.created_users.clear()
        self.created_fragments.clear()
        self.created_subscriptions.clear()


class TestDataGenerator:
    """
    Generator for realistic test data

    Provides methods to generate realistic test data for users, narratives,
    subscriptions, and events following the data schemas from the design document.
    """

    @staticmethod
    def generate_telegram_user(user_id: int = None) -> Dict[str, Any]:
        """Generate realistic Telegram user data"""
        if user_id is None:
            user_id = 123456789 + len(TestDataGenerator._used_ids) if hasattr(TestDataGenerator, '_used_ids') else 123456789

        if not hasattr(TestDataGenerator, '_used_ids'):
            TestDataGenerator._used_ids = set()
        TestDataGenerator._used_ids.add(user_id)

        return {
            "id": user_id,
            "username": f"test_user_{user_id}",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "es",
            "is_bot": False
        }

    @staticmethod
    def generate_user_mongo_doc(user_id: str) -> Dict[str, Any]:
        """Generate MongoDB user document"""
        return {
            "user_id": user_id,
            "current_state": {
                "menu_context": "main_menu",
                "narrative_progress": {
                    "current_fragment": None,
                    "completed_fragments": [],
                    "choices_made": []
                },
                "session_data": {"last_activity": datetime.utcnow().isoformat()}
            },
            "preferences": {
                "language": "es",
                "notifications_enabled": True,
                "theme": "default"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

    @staticmethod
    def generate_user_sqlite_profile(user_id: str, telegram_user: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SQLite user profile"""
        return {
            "user_id": user_id,
            "telegram_user_id": telegram_user["id"],
            "username": telegram_user.get("username"),
            "first_name": telegram_user.get("first_name"),
            "last_name": telegram_user.get("last_name"),
            "language_code": telegram_user.get("language_code"),
            "registration_date": datetime.utcnow(),
            "last_login": datetime.utcnow(),
            "is_active": True
        }

    @staticmethod
    def generate_narrative_fragment(fragment_id: str = None) -> Dict[str, Any]:
        """Generate narrative fragment document"""
        if fragment_id is None:
            fragment_id = f"fragment_{uuid.uuid4().hex[:8]}"

        return {
            "fragment_id": fragment_id,
            "title": f"Test Fragment {fragment_id}",
            "content": "Esta es una aventura de prueba...",
            "choices": [
                {"id": "choice_a", "text": "Explorar", "next_fragment": "next_001"},
                {"id": "choice_b", "text": "Esperar", "next_fragment": "next_002"}
            ],
            "metadata": {
                "difficulty": "easy",
                "tags": ["test", "adventure"],
                "vip_required": False
            },
            "created_at": datetime.utcnow()
        }

    @staticmethod
    def generate_subscription_data(user_id: str, plan_type: str = "free", status: str = "active") -> Dict[str, Any]:
        """Generate subscription data"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30) if plan_type != "free" else None

        return {
            "user_id": user_id,
            "plan_type": plan_type,
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

    @staticmethod
    def generate_user_interaction_event(user_id: str, action: str = "start") -> UserInteractionEvent:
        """Generate user interaction event"""
        return UserInteractionEvent(
            user_id=user_id,
            action=action,
            context={"test": True},
            source="test"
        )

    @staticmethod
    def generate_user_registration_event(user_id: str, telegram_data: Dict[str, Any]) -> UserRegistrationEvent:
        """Generate user registration event"""
        return UserRegistrationEvent(
            user_id=user_id,
            telegram_data=telegram_data
        )

    @staticmethod
    def generate_reaction_event(user_id: str, content_id: str, reaction_type: str = "like") -> ReactionDetectedEvent:
        """Generate reaction event"""
        return ReactionDetectedEvent(
            user_id=user_id,
            content_id=content_id,
            reaction_type=reaction_type
        )

    @staticmethod
    def generate_decision_event(user_id: str, fragment_id: str, choice_id: str) -> DecisionMadeEvent:
        """Generate decision event"""
        return DecisionMadeEvent(
            user_id=user_id,
            choice_id=choice_id,
            fragment_id=fragment_id,
            next_fragment_id="next_fragment_001"
        )

    @staticmethod
    def generate_subscription_event(user_id: str, old_status: str, new_status: str, plan_type: str = "premium") -> SubscriptionUpdatedEvent:
        """Generate subscription event"""
        return SubscriptionUpdatedEvent(
            user_id=user_id,
            old_status=old_status,
            new_status=new_status,
            plan_type=plan_type
        )


class DatabaseTestHelpers:
    """
    Helper methods for database testing

    Provides utility methods for common database testing operations,
    data validation, and test scenario setup.
    """

    def __init__(self, test_db: TestDatabaseManager):
        self.test_db = test_db
        self.logger = get_logger(self.__class__.__name__)

    async def create_test_user(self, user_id: str = None, telegram_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a complete test user in both databases"""
        if not telegram_data:
            telegram_data = TestDataGenerator.generate_telegram_user()

        if not user_id:
            user_id = str(telegram_data["id"])

        mongo_doc = TestDataGenerator.generate_user_mongo_doc(user_id)
        sqlite_profile = TestDataGenerator.generate_user_sqlite_profile(user_id, telegram_data)

        # Insert into MongoDB
        mongo_db = self.test_db.get_mongo_db()
        if mongo_db:
            await mongo_db.users.insert_one(mongo_doc)
            self.test_db.created_users.add(user_id)

        # Insert into SQLite
        sqlite_engine = self.test_db.get_sqlite_engine()
        if sqlite_engine:
            async with sqlite_engine.connect() as conn:
                await conn.execute(
                    text("""INSERT INTO user_profiles
                           (user_id, telegram_user_id, username, first_name, last_name,
                            language_code, registration_date, last_login, is_active)
                           VALUES (:user_id, :telegram_user_id, :username, :first_name, :last_name,
                                  :language_code, :registration_date, :last_login, :is_active)"""),
                    sqlite_profile
                )
                await conn.commit()

        return {
            "user_id": user_id,
            "telegram_data": telegram_data,
            "mongo_doc": mongo_doc,
            "sqlite_profile": sqlite_profile
        }

    async def create_test_narrative(self, fragment_id: str = None) -> Dict[str, Any]:
        """Create a test narrative fragment"""
        fragment = TestDataGenerator.generate_narrative_fragment(fragment_id)

        mongo_db = self.test_db.get_mongo_db()
        if mongo_db:
            await mongo_db.narrative_fragments.insert_one(fragment)
            self.test_db.created_fragments.add(fragment["fragment_id"])

        return fragment

    async def create_test_subscription(self, user_id: str, plan_type: str = "premium", status: str = "active") -> Dict[str, Any]:
        """Create a test subscription"""
        subscription = TestDataGenerator.generate_subscription_data(user_id, plan_type, status)

        sqlite_engine = self.test_db.get_sqlite_engine()
        if sqlite_engine:
            async with sqlite_engine.connect() as conn:
                await conn.execute(
                    text("""INSERT INTO subscriptions
                           (user_id, plan_type, status, start_date, end_date, created_at, updated_at)
                           VALUES (:user_id, :plan_type, :status, :start_date, :end_date, :created_at, :updated_at)"""),
                    subscription
                )
                await conn.commit()
                self.test_db.created_subscriptions.add(user_id)

        return subscription

    async def verify_user_exists(self, user_id: str) -> Dict[str, bool]:
        """Verify user exists in both databases"""
        results = {"mongo": False, "sqlite": False}

        # Check MongoDB
        mongo_db = self.test_db.get_mongo_db()
        if mongo_db:
            user_doc = await mongo_db.users.find_one({"user_id": user_id})
            results["mongo"] = user_doc is not None

        # Check SQLite
        sqlite_engine = self.test_db.get_sqlite_engine()
        if sqlite_engine:
            async with sqlite_engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT user_id FROM user_profiles WHERE user_id = :user_id"),
                    {"user_id": user_id}
                )
                row = await result.fetchone()
                results["sqlite"] = row is not None

        return results

    async def verify_subscription_exists(self, user_id: str) -> bool:
        """Verify subscription exists for user"""
        sqlite_engine = self.test_db.get_sqlite_engine()
        if sqlite_engine:
            async with sqlite_engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT id FROM subscriptions WHERE user_id = :user_id"),
                    {"user_id": user_id}
                )
                row = await result.fetchone()
                return row is not None
        return False

    async def count_users(self) -> Dict[str, int]:
        """Count users in both databases"""
        counts = {"mongo": 0, "sqlite": 0}

        # Count MongoDB users
        mongo_db = self.test_db.get_mongo_db()
        if mongo_db:
            counts["mongo"] = await mongo_db.users.count_documents({})

        # Count SQLite users
        sqlite_engine = self.test_db.get_sqlite_engine()
        if sqlite_engine:
            async with sqlite_engine.connect() as conn:
                result = await conn.execute(text("SELECT COUNT(*) FROM user_profiles"))
                row = await result.fetchone()
                counts["sqlite"] = row[0] if row else 0

        return counts

    async def get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user state from MongoDB"""
        mongo_db = self.test_db.get_mongo_db()
        if mongo_db:
            user_doc = await mongo_db.users.find_one({"user_id": user_id})
            return user_doc.get("current_state") if user_doc else None
        return None

    async def update_user_state(self, user_id: str, new_state: Dict[str, Any]) -> bool:
        """Update user state in MongoDB"""
        mongo_db = self.test_db.get_mongo_db()
        if mongo_db:
            result = await mongo_db.users.update_one(
                {"user_id": user_id},
                {"$set": {"current_state": new_state, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        return False


# Test fixtures following pytest patterns from conftest.py

@pytest.fixture
async def test_database():
    """Fixture for test database setup and cleanup"""
    test_db = TestDatabaseManager()

    # Setup test databases
    setup_success = await test_db.setup()
    if not setup_success:
        pytest.skip("Could not connect to test databases")

    yield test_db

    # Cleanup
    await test_db.cleanup()


@pytest.fixture
async def test_db_helpers(test_database):
    """Fixture for database test helpers"""
    return DatabaseTestHelpers(test_database)


@pytest.fixture
def mock_database_manager():
    """Mock DatabaseManager for unit testing"""
    mock_db = MagicMock(spec=DatabaseManager)

    # Setup default return values
    mock_db.get_mongo_db.return_value = MagicMock()
    mock_db.get_sqlite_engine.return_value = MagicMock()
    mock_db.health_check.return_value = {
        "mongo_connected": True,
        "sqlite_connected": True,
        "overall_healthy": True
    }

    # Mock CRUD operations
    mock_db.create_user_atomic = AsyncMock(return_value=True)
    mock_db.get_user_from_mongo = AsyncMock(return_value=None)
    mock_db.get_user_profile_from_sqlite = AsyncMock(return_value=None)
    mock_db.update_user_in_mongo = AsyncMock(return_value=True)
    mock_db.update_user_profile_in_sqlite = AsyncMock(return_value=True)
    mock_db.get_subscription_from_sqlite = AsyncMock(return_value=None)
    mock_db.delete_user_from_mongo = AsyncMock(return_value=True)
    mock_db.delete_user_profile_from_sqlite = AsyncMock(return_value=True)

    return mock_db


@pytest.fixture
def sample_telegram_user():
    """Generate sample Telegram user data"""
    return TestDataGenerator.generate_telegram_user()


@pytest.fixture
def sample_user_events():
    """Generate sample user events for testing"""
    user_id = "123456789"
    return {
        "interaction": TestDataGenerator.generate_user_interaction_event(user_id),
        "registration": TestDataGenerator.generate_user_registration_event(
            user_id, TestDataGenerator.generate_telegram_user()
        ),
        "reaction": TestDataGenerator.generate_reaction_event(user_id, "content_001"),
        "decision": TestDataGenerator.generate_decision_event(user_id, "fragment_001", "choice_a"),
        "subscription": TestDataGenerator.generate_subscription_event(user_id, "inactive", "active")
    }


@pytest.fixture
async def populated_test_database(test_database, test_db_helpers):
    """Fixture that provides a database populated with test data"""
    # Create multiple test users
    users = []
    for i in range(3):
        user = await test_db_helpers.create_test_user()
        users.append(user)

    # Create some narrative fragments
    fragments = []
    for i in range(2):
        fragment = await test_db_helpers.create_test_narrative()
        fragments.append(fragment)

    # Create some subscriptions
    for user in users[:2]:  # Only first two users get subscriptions
        await test_db_helpers.create_test_subscription(
            user["user_id"],
            plan_type="premium" if users.index(user) == 0 else "vip"
        )

    return {
        "database": test_database,
        "helpers": test_db_helpers,
        "users": users,
        "fragments": fragments
    }


# Performance testing utilities
class DatabasePerformanceTestHelper:
    """
    Helper for performance testing database operations

    Provides methods to measure operation latency and validate
    performance requirements from the design document.
    """

    @staticmethod
    async def time_operation(operation_coro):
        """Time an async operation"""
        import time
        start_time = time.time()
        result = await operation_coro
        end_time = time.time()
        return result, (end_time - start_time) * 1000  # Return result and time in milliseconds

    @staticmethod
    def validate_performance_requirement(operation_time_ms: float, requirement_ms: float = 100) -> bool:
        """Validate that operation meets performance requirement"""
        return operation_time_ms <= requirement_ms

    @staticmethod
    async def measure_concurrent_operations(operations: List, max_concurrent: int = 10):
        """Measure performance of concurrent operations"""
        import time
        from asyncio import gather, Semaphore

        semaphore = Semaphore(max_concurrent)

        async def timed_operation(op):
            async with semaphore:
                start_time = time.time()
                result = await op
                end_time = time.time()
                return result, (end_time - start_time) * 1000

        start_time = time.time()
        results = await gather(*[timed_operation(op) for op in operations])
        total_time = (time.time() - start_time) * 1000

        return {
            "total_time_ms": total_time,
            "operation_results": results,
            "average_time_ms": sum(r[1] for r in results) / len(results),
            "max_time_ms": max(r[1] for r in results),
            "min_time_ms": min(r[1] for r in results)
        }


@pytest.fixture
def performance_helper():
    """Fixture for database performance testing"""
    return DatabasePerformanceTestHelper()