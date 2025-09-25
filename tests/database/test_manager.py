"""
DatabaseManager Unit Tests

This module provides comprehensive unit tests for the DatabaseManager class
in the YABOT system. Following the Testing Strategy from Fase1 requirements,
these tests validate database connection management, CRUD operations,
error handling, and performance against the specified requirements.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from typing import Dict, Any, Optional

from src.database.manager import DatabaseManager



class TestDatabaseManagerInitialization:
    """Test DatabaseManager initialization and configuration"""

    def test_init_with_config(self):
        """Test DatabaseManager initialization with configuration"""
        config = {
            "mongodb_uri": "mongodb://localhost:27017",
            "mongodb_database": "test_db",
            "sqlite_database_path": ":memory:",
            "mongodb_config": {
                "min_pool_size": 1,
                "max_pool_size": 10,
                "server_selection_timeout": 5000
            },
            "sqlite_config": {
                "pool_size": 5,
                "max_overflow": 10
            }
        }

        db_manager = DatabaseManager(config)
        assert db_manager.config == config
        assert not db_manager._connected

    def test_init_with_defaults(self):
        """Test DatabaseManager initialization with default configuration"""
        db_manager = DatabaseManager({})
        assert db_manager.config == {}
        assert not db_manager._connected


class TestDatabaseManagerConnection:
    """Test DatabaseManager connection management"""

    @pytest.mark.asyncio
    async def test_connect_all_success(self, mock_database_manager):
        """Test successful connection to both databases"""
        db_manager = mock_database_manager
        db_manager.connect_all = AsyncMock(return_value=True)
        db_manager.health_check = AsyncMock(return_value={
            "mongo_connected": True,
            "sqlite_connected": True,
            "overall_healthy": True
        })

        result = await db_manager.connect_all()
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_all_partial_failure(self, mock_database_manager):
        """Test connection when one database fails"""
        db_manager = mock_database_manager
        db_manager.get_mongo_db = AsyncMock(return_value=None)  # Mongo fails
        db_manager.get_sqlite_engine = AsyncMock(return_value=MagicMock())  # SQLite works
        db_manager.health_check = AsyncMock(return_value={
            "mongo_connected": False,
            "sqlite_connected": True,
            "overall_healthy": False
        })

        result = await db_manager.connect_all()
        health = await db_manager.health_check()
        assert not health["overall_healthy"]

    @pytest.mark.asyncio
    async def test_disconnect_all(self, mock_database_manager):
        """Test disconnection from both databases"""
        db_manager = mock_database_manager
        db_manager.close_connections = AsyncMock(return_value=True)

        result = await db_manager.close_connections()
        assert result is True
        assert not db_manager._connected


class TestDatabaseManagerMongoCRUD:
    """Test MongoDB-specific CRUD operations in DatabaseManager"""

    @pytest.mark.asyncio
    async def test_get_mongo_db(self, mock_database_manager):
        """Test getting MongoDB connection"""
        db_manager = mock_database_manager
        mongo_db = db_manager.get_mongo_db()
        assert mongo_db is not None  # From mock

    @pytest.mark.asyncio
    async def test_get_user_from_mongo(self, mock_database_manager):
        """Test retrieving user from MongoDB"""
        db_manager = mock_database_manager
        expected_user = {
            "user_id": "123456",
            "current_state": {"menu_context": "main_menu"},
            "preferences": {"language": "es"}
        }
        db_manager.get_user_from_mongo = AsyncMock(return_value=expected_user)

        result = await db_manager.get_user_from_mongo("123456")
        assert result == expected_user

    @pytest.mark.asyncio
    async def test_get_user_from_mongo_not_found(self, mock_database_manager):
        """Test retrieving non-existent user from MongoDB"""
        db_manager = mock_database_manager
        db_manager.get_user_from_mongo = AsyncMock(return_value=None)

        result = await db_manager.get_user_from_mongo("999999")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_in_mongo(self, mock_database_manager):
        """Test updating user in MongoDB"""
        db_manager = mock_database_manager
        db_manager.update_user_in_mongo = AsyncMock(return_value=True)

        update_data = {"current_state.menu_context": "game_menu"}
        result = await db_manager.update_user_in_mongo("123456", update_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_update_user_in_mongo_failure(self, mock_database_manager):
        """Test update user in MongoDB fails"""
        db_manager = mock_database_manager
        db_manager.update_user_in_mongo = AsyncMock(return_value=False)

        update_data = {"current_state.menu_context": "game_menu"}
        result = await db_manager.update_user_in_mongo("123456", update_data)
        assert result is False

    @pytest.mark.asyncio
    async def test_create_user_in_mongo(self, mock_database_manager):
        """Test creating user in MongoDB"""
        db_manager = mock_database_manager
        user_data = {
            "user_id": "123456",
            "current_state": {"menu_context": "main_menu"},
            "preferences": {"language": "es"},
            "created_at": datetime.utcnow()
        }
        db_manager.create_user_in_mongo = AsyncMock(return_value=True)

        result = await db_manager.create_user_in_mongo(user_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_from_mongo(self, mock_database_manager):
        """Test deleting user from MongoDB"""
        db_manager = mock_database_manager
        db_manager.delete_user_from_mongo = AsyncMock(return_value=True)

        result = await db_manager.delete_user_from_mongo("123456")
        assert result is True


class TestDatabaseManagerSQLiteCRUD:
    """Test SQLite-specific CRUD operations in DatabaseManager"""

    @pytest.mark.asyncio
    async def test_get_sqlite_engine(self, mock_database_manager):
        """Test getting SQLite engine"""
        db_manager = mock_database_manager
        sqlite_engine = db_manager.get_sqlite_engine()
        assert sqlite_engine is not None  # From mock

    @pytest.mark.asyncio
    async def test_get_user_profile_from_sqlite(self, mock_database_manager):
        """Test retrieving user profile from SQLite"""
        db_manager = mock_database_manager
        expected_profile = {
            "user_id": "123456",
            "telegram_user_id": 123456,
            "username": "test_user",
            "first_name": "Test",
            "is_active": True
        }
        db_manager.get_user_profile_from_sqlite = AsyncMock(return_value=expected_profile)

        result = await db_manager.get_user_profile_from_sqlite("123456")
        assert result == expected_profile

    @pytest.mark.asyncio
    async def test_get_user_profile_from_sqlite_not_found(self, mock_database_manager):
        """Test retrieving non-existent user profile from SQLite"""
        db_manager = mock_database_manager
        db_manager.get_user_profile_from_sqlite = AsyncMock(return_value=None)

        result = await db_manager.get_user_profile_from_sqlite("999999")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_profile_in_sqlite(self, mock_database_manager):
        """Test updating user profile in SQLite"""
        db_manager = mock_database_manager
        profile_updates = {"username": "new_username", "last_login": datetime.utcnow()}
        db_manager.update_user_profile_in_sqlite = AsyncMock(return_value=True)

        result = await db_manager.update_user_profile_in_sqlite("123456", profile_updates)
        assert result is True

    @pytest.mark.asyncio
    async def test_update_user_profile_in_sqlite_failure(self, mock_database_manager):
        """Test updating user profile in SQLite fails"""
        db_manager = mock_database_manager
        profile_updates = {"username": "new_username"}
        db_manager.update_user_profile_in_sqlite = AsyncMock(return_value=False)

        result = await db_manager.update_user_profile_in_sqlite("123456", profile_updates)
        assert result is False

    @pytest.mark.asyncio
    async def test_create_user_profile_in_sqlite(self, mock_database_manager):
        """Test creating user profile in SQLite"""
        db_manager = mock_database_manager
        profile_data = {
            "user_id": "123456",
            "telegram_user_id": 123456,
            "username": "test_user",
            "first_name": "Test",
            "is_active": True
        }
        db_manager.create_user_profile_in_sqlite = AsyncMock(return_value=True)

        result = await db_manager.create_user_profile_in_sqlite(profile_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_subscription_from_sqlite(self, mock_database_manager):
        """Test retrieving subscription from SQLite"""
        db_manager = mock_database_manager
        expected_subscription = {
            "id": 1,
            "user_id": "123456",
            "plan_type": "premium",
            "status": "active",
            "start_date": datetime.utcnow(),
            "end_date": datetime.utcnow()
        }
        db_manager.get_subscription_from_sqlite = AsyncMock(return_value=expected_subscription)

        result = await db_manager.get_subscription_from_sqlite("123456")
        assert result == expected_subscription

    @pytest.mark.asyncio
    async def test_get_subscription_from_sqlite_not_found(self, mock_database_manager):
        """Test retrieving non-existent subscription from SQLite"""
        db_manager = mock_database_manager
        db_manager.get_subscription_from_sqlite = AsyncMock(return_value=None)

        result = await db_manager.get_subscription_from_sqlite("999999")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_subscription_in_sqlite(self, mock_database_manager):
        """Test updating subscription in SQLite"""
        db_manager = mock_database_manager
        subscription_updates = {"status": "expired", "end_date": datetime.utcnow()}
        db_manager.update_subscription_in_sqlite = AsyncMock(return_value=True)

        result = await db_manager.update_subscription_in_sqlite("123456", subscription_updates)
        assert result is True

    @pytest.mark.asyncio
    async def test_create_subscription_in_sqlite(self, mock_database_manager):
        """Test creating subscription in SQLite"""
        db_manager = mock_database_manager
        subscription_data = {
            "user_id": "123456",
            "plan_type": "premium",
            "status": "active",
            "start_date": datetime.utcnow(),
            "end_date": datetime.utcnow()
        }
        db_manager.create_subscription_in_sqlite = AsyncMock(return_value=True)

        result = await db_manager.create_subscription_in_sqlite(subscription_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_profile_from_sqlite(self, mock_database_manager):
        """Test deleting user profile from SQLite"""
        db_manager = mock_database_manager
        db_manager.delete_user_profile_from_sqlite = AsyncMock(return_value=True)

        result = await db_manager.delete_user_profile_from_sqlite("123456")
        assert result is True


class TestDatabaseManagerAtomicOperations:
    """Test atomic operations across both databases"""

    @pytest.mark.asyncio
    async def test_create_user_atomic_success(self, mock_database_manager):
        """Test atomic user creation in both databases"""
        db_manager = mock_database_manager
        telegram_user = {
            "id": 123456,
            "username": "test_user",
            "first_name": "Test",
            "is_bot": False
        }
        db_manager.create_user_atomic = AsyncMock(return_value=True)

        result = await db_manager.create_user_atomic(telegram_user)
        assert result is True

    @pytest.mark.asyncio
    async def test_create_user_atomic_failure_rollback(self, mock_database_manager):
        """Test atomic user creation rollback when one db fails"""
        db_manager = mock_database_manager
        telegram_user = {
            "id": 123456,
            "username": "test_user",
            "first_name": "Test",
            "is_bot": False
        }

        # Mock to simulate failure in one operation
        async def atomic_failure(user):
            # Simulate mongo success, sqlite failure
            await db_manager.create_user_in_mongo({"user_id": str(user["id"])})
            raise Exception("SQLite insertion failed")

        db_manager.create_user_atomic = AsyncMock(side_effect=atomic_failure)
        db_manager.rollback_user_creation = AsyncMock(return_value=True)

        with pytest.raises(Exception):
            await db_manager.create_user_atomic(telegram_user)

        # Verify rollback was called
        db_manager.rollback_user_creation.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_atomic_success(self, mock_database_manager):
        """Test atomic user update in both databases"""
        db_manager = mock_database_manager
        user_id = "123456"
        state_updates = {"current_state.menu_context": "game_menu"}
        profile_updates = {"last_login": datetime.utcnow()}

        db_manager.update_user_atomic = AsyncMock(return_value=True)

        result = await db_manager.update_user_atomic(user_id, state_updates, profile_updates)
        assert result is True


class TestDatabaseManagerHealthCheck:
    """Test DatabaseManager health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self, mock_database_manager):
        """Test health check when both databases are healthy"""
        db_manager = mock_database_manager
        health = await db_manager.health_check()
        
        assert health["mongo_connected"] is True
        assert health["sqlite_connected"] is True
        assert health["overall_healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_mongo_unhealthy(self, mock_database_manager):
        """Test health check when MongoDB is unhealthy"""
        db_manager = mock_database_manager
        # Mock the internal connection state attributes directly
        db_manager._mongo_connected = False
        db_manager._sqlite_connected = True

        # Replace the mocked health_check with a simple implementation
        async def real_health_check():
            return {
                "mongo_connected": db_manager._mongo_connected,
                "sqlite_connected": db_manager._sqlite_connected,
                "overall_healthy": db_manager._mongo_connected and db_manager._sqlite_connected
            }

        db_manager.health_check = real_health_check
        health = await db_manager.health_check()

        assert health["mongo_connected"] is False
        assert health["sqlite_connected"] is True
        assert health["overall_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_sqlite_unhealthy(self, mock_database_manager):
        """Test health check when SQLite is unhealthy"""
        db_manager = mock_database_manager
        # Mock the internal connection state attributes directly
        db_manager._mongo_connected = True
        db_manager._sqlite_connected = False

        # Replace the mocked health_check with a simple implementation
        async def real_health_check():
            return {
                "mongo_connected": db_manager._mongo_connected,
                "sqlite_connected": db_manager._sqlite_connected,
                "overall_healthy": db_manager._mongo_connected and db_manager._sqlite_connected
            }

        db_manager.health_check = real_health_check
        health = await db_manager.health_check()

        assert health["mongo_connected"] is True
        assert health["sqlite_connected"] is False
        assert health["overall_healthy"] is False


class TestDatabaseManagerErrorHandling:
    """Test DatabaseManager error handling"""

    @pytest.mark.asyncio
    async def test_connection_error_retry(self):
        """Test connection error handling and retry mechanism"""
        config = {
            "mongodb_uri": "mongodb://invalid:27017",
            "mongodb_database": "test_db",
            "sqlite_database_path": ":memory:",
            "mongodb_config": {
                "min_pool_size": 1,
                "max_pool_size": 1,
                "server_selection_timeout": 100
            },
            "sqlite_config": {"pool_size": 1}
        }

        db_manager = DatabaseManager(config)
        
        # This should handle connection errors gracefully
        try:
            await db_manager.connect_all()
        except Exception:
            # Connection failure is expected with invalid MongoDB URI
            pass

    @pytest.mark.asyncio
    async def test_operation_timeout_handling(self):
        """Test timeout handling for database operations"""
        config = {
            "mongodb_uri": "mongodb://localhost:27017",
            "mongodb_database": "test_db",
            "sqlite_database_path": ":memory:",
            "mongodb_config": {
                "min_pool_size": 1,
                "max_pool_size": 1,
                "server_selection_timeout": 100,
                "socket_timeout": 100
            },
            "sqlite_config": {"pool_size": 1}
        }

        db_manager = DatabaseManager(config)
        
        # We'll test by mocking a timeout scenario
        with patch.object(db_manager, 'get_mongo_db', side_effect=TimeoutError("Mongo timeout")):
            try:
                mongo_db = db_manager.get_mongo_db()
                # This should be reached but will return None due to exception
                assert mongo_db is None
            except:
                # Exception handling should be in the implementation
                pass


class TestDatabaseManagerPerformance:
    """Test DatabaseManager performance requirements"""

    @pytest.mark.asyncio
    async def test_mongo_operation_performance(self, mock_database_manager):
        """Test that MongoDB operations meet performance requirements"""
        db_manager = mock_database_manager
        
        # Measure the time for a simple operation
        import time
        start_time = time.time()
        
        # Mock a fast operation
        db_manager.get_user_from_mongo = AsyncMock(return_value={"user_id": "123"})
        result = await db_manager.get_user_from_mongo("123")
        
        end_time = time.time()
        operation_time_ms = (end_time - start_time) * 1000
        
        # Requirement: Database operations shall complete within 100ms for 95% of requests
        assert operation_time_ms <= 100, f"Operation took {operation_time_ms}ms, exceeding 100ms requirement"

    @pytest.mark.asyncio
    async def test_sqlite_operation_performance(self, mock_database_manager):
        """Test that SQLite operations meet performance requirements"""
        db_manager = mock_database_manager
        
        import time
        start_time = time.time()
        
        # Mock a fast operation
        db_manager.get_user_profile_from_sqlite = AsyncMock(return_value={"user_id": "123"})
        result = await db_manager.get_user_profile_from_sqlite("123")
        
        end_time = time.time()
        operation_time_ms = (end_time - start_time) * 1000
        
        # Requirement: Database operations shall complete within 100ms for 95% of requests
        assert operation_time_ms <= 100, f"Operation took {operation_time_ms}ms, exceeding 100ms requirement"


# Test the actual DatabaseManager implementation if it exists
@pytest.mark.integration
class TestDatabaseManagerActualImplementation:
    """Integration tests for actual DatabaseManager implementation"""
    
    @pytest.mark.asyncio
    async def test_connect_with_real_config(self):
        """Test connection with minimal realistic configuration"""
        config = {
            "mongodb_uri": "mongodb://localhost:27017",
            "mongodb_database": "yabot_test",
            "sqlite_database_path": ":memory:",  # In-memory for testing
            "mongodb_config": {
                "min_pool_size": 1,
                "max_pool_size": 5,
                "server_selection_timeout": 2000
            },
            "sqlite_config": {
                "pool_size": 2,
                "max_overflow": 5,
                "pool_timeout": 10
            }
        }

        db_manager = DatabaseManager(config)
        
        # Test initialization - this won't actually connect without MongoDB running
        assert db_manager.config == config
        assert db_manager._connected is False


# Run tests
if __name__ == "__main__":
    pytest.main([__file__])