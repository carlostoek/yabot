"""
Unit tests for DatabaseManager focusing on recent fixes and dual database operations.

Key areas tested:
1. MongoDB boolean check fixes (using `is None`)
2. Dual database atomic operations
3. Connection pooling and health checks
4. Error handling and recovery
5. Collection and table initialization
"""
import pytest
import asyncio
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.database.manager import DatabaseManager, get_database_manager, reset_database_manager
from src.core.models import DatabaseConfig


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    @pytest.fixture(autouse=True)
    async def cleanup(self):
        """Cleanup after each test."""
        yield
        await reset_database_manager()

    async def test_database_manager_initialization_with_config_dict(self, test_database_config):
        """Test DatabaseManager initialization with config dictionary."""
        db_manager = DatabaseManager(config=test_database_config)

        # Verify configuration was properly set
        assert db_manager.database_config.mongodb_uri == test_database_config['mongodb_uri']
        assert db_manager.database_config.sqlite_database_path == test_database_config['sqlite_database_path']
        assert db_manager.database_config.pool_size == test_database_config['pool_size']

    async def test_database_manager_initialization_without_config(self):
        """Test DatabaseManager initialization without config (uses config manager)."""
        with patch('src.config.manager.get_config_manager') as mock_config_mgr:
            mock_config = MagicMock()
            mock_config.get_database_config.return_value = MagicMock()
            mock_config_mgr.return_value = mock_config

            db_manager = DatabaseManager()
            assert db_manager.config_manager == mock_config

    async def test_mongodb_connection_with_boolean_checks(self, test_database_config):
        """Test MongoDB connection with proper boolean checks (recent fix)."""
        db_manager = DatabaseManager(config=test_database_config)

        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command = AsyncMock()
            mock_client.__getitem__.return_value = MagicMock()
            mock_client_class.return_value = mock_client

            # Test successful connection
            result = await db_manager.connect_all()
            assert result is True
            assert db_manager._mongo_connected is True

            # Test the specific pattern that was fixed: proper boolean checks
            mongo_db = db_manager.get_mongo_db()
            assert (mongo_db is None) is False  # Using `is None` pattern from the fix

            # Test disconnected state
            db_manager._mongo_connected = False
            mongo_db = db_manager.get_mongo_db()
            assert mongo_db is None  # Should return None when not connected

    async def test_mongodb_connection_failure_handling(self, test_database_config):
        """Test MongoDB connection failure handling."""
        db_manager = DatabaseManager(config=test_database_config)

        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command = AsyncMock(side_effect=ConnectionError("MongoDB unavailable"))
            mock_client_class.return_value = mock_client

            # Test connection failure
            result = await db_manager.connect_all()
            assert result is False
            assert db_manager._mongo_connected is False

    async def test_sqlite_connection_with_real_database(self, real_sqlite_db):
        """Test SQLite connection with real database."""
        # Test that real_sqlite_db fixture works
        assert real_sqlite_db is not None
        assert real_sqlite_db._sqlite_connected is False  # Not connected yet in fixture

        # Test SQLite engine creation
        with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_engine:
            mock_engine_instance = MagicMock()
            mock_connection = MagicMock()
            mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
            mock_connection.__aexit__ = AsyncMock()
            mock_connection.execute = AsyncMock()
            mock_engine_instance.connect.return_value = mock_connection
            mock_engine.return_value = mock_engine_instance

            result = await real_sqlite_db.connect_all()
            assert mock_engine.called

    async def test_atomic_user_creation_success(self, mock_database_manager):
        """Test successful atomic user creation in both databases."""
        user_id = "test_user_123"
        mongo_doc = {
            "user_id": user_id,
            "current_state": {"menu": "main"},
            "created_at": datetime.utcnow()
        }
        sqlite_profile = {
            "user_id": user_id,
            "telegram_user_id": 123456789,
            "username": "test_user",
            "first_name": "Test",
            "is_active": True
        }

        # Test atomic creation
        result = await mock_database_manager.create_user_atomic(user_id, mongo_doc, sqlite_profile)
        assert result is True

    async def test_atomic_user_creation_rollback(self, test_database_config):
        """Test atomic user creation rollback on failure."""
        db_manager = DatabaseManager(config=test_database_config)

        user_id = "test_user_123"
        mongo_doc = {"user_id": user_id}
        sqlite_profile = {"user_id": user_id}

        # Mock MongoDB success, SQLite failure
        with patch.object(db_manager, 'get_mongo_db') as mock_get_mongo:
            with patch.object(db_manager, 'get_sqlite_engine') as mock_get_sqlite:
                mock_mongo_db = MagicMock()
                mock_mongo_db.users.insert_one = AsyncMock()
                mock_mongo_db.users.delete_one = AsyncMock()
                mock_get_mongo.return_value = mock_mongo_db

                mock_get_sqlite.return_value = None  # Simulate SQLite unavailable

                result = await db_manager.create_user_atomic(user_id, mongo_doc, sqlite_profile)
                assert result is False

                # Verify rollback occurred
                mock_mongo_db.users.delete_one.assert_called_once_with({"user_id": user_id})

    async def test_user_retrieval_from_mongodb(self, mock_database_manager):
        """Test user retrieval from MongoDB with ObjectId conversion."""
        user_id = "test_user_123"

        # Test successful retrieval
        result = await mock_database_manager.get_user_from_mongo(user_id)
        assert result is not None
        assert result['user_id'] == '123'

        # Test user not found
        mock_database_manager.get_user_from_mongo.return_value = None
        result = await mock_database_manager.get_user_from_mongo("nonexistent_user")
        assert result is None

    async def test_user_profile_retrieval_from_sqlite(self, mock_database_manager):
        """Test user profile retrieval from SQLite."""
        user_id = "test_user_123"

        # Test successful retrieval
        result = await mock_database_manager.get_user_profile_from_sqlite(user_id)
        assert result is not None
        assert 'user_id' in result

    async def test_user_update_operations(self, mock_database_manager):
        """Test user update operations in both databases."""
        user_id = "test_user_123"

        # Test MongoDB update
        update_data = {"$set": {"last_activity": datetime.utcnow()}}
        result = await mock_database_manager.update_user_in_mongo(user_id, update_data)
        assert result is True

        # Test SQLite update
        profile_updates = {"last_login": datetime.utcnow(), "is_active": True}
        result = await mock_database_manager.update_user_profile_in_sqlite(user_id, profile_updates)
        assert result is True

    async def test_user_deletion_operations(self, mock_database_manager):
        """Test user deletion operations in both databases."""
        user_id = "test_user_123"

        # Test MongoDB deletion
        result = await mock_database_manager.delete_user_from_mongo(user_id)
        assert result is True

        # Test SQLite deletion
        result = await mock_database_manager.delete_user_profile_from_sqlite(user_id)
        assert result is True

    async def test_subscription_operations(self, mock_database_manager):
        """Test subscription-related operations in SQLite."""
        user_id = "test_user_123"

        # Test subscription creation
        subscription_data = {
            "user_id": user_id,
            "plan_type": "premium",
            "status": "active",
            "start_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        with patch.object(mock_database_manager, 'create_subscription', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = True
            result = await mock_database_manager.create_subscription(subscription_data)
            assert result is True

        # Test subscription retrieval
        with patch.object(mock_database_manager, 'get_subscription_from_sqlite', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"status": "active", "plan_type": "premium"}
            subscription = await mock_database_manager.get_subscription_from_sqlite(user_id)
            assert subscription["status"] == "active"

    async def test_narrative_operations(self, mock_database_manager):
        """Test narrative fragment operations in MongoDB."""
        fragment_id = "fragment_123"

        # Test narrative retrieval
        with patch.object(mock_database_manager, 'get_narrative_from_mongo', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "fragment_id": fragment_id,
                "content": "Test narrative content",
                "_id": "object_id_string"
            }
            narrative = await mock_database_manager.get_narrative_from_mongo(fragment_id)
            assert narrative["fragment_id"] == fragment_id

        # Test related narratives retrieval
        with patch.object(mock_database_manager, 'get_related_narratives', new_callable=AsyncMock) as mock_related:
            mock_related.return_value = [
                {"fragment_id": "related_1", "_id": "id1"},
                {"fragment_id": "related_2", "_id": "id2"}
            ]
            related = await mock_database_manager.get_related_narratives(fragment_id, ["adventure"])
            assert len(related) == 2

    async def test_health_check_comprehensive(self, test_database_config):
        """Test comprehensive health check functionality."""
        db_manager = DatabaseManager(config=test_database_config)

        # Mock both databases as healthy
        with patch.object(db_manager, '_mongo_connected', True):
            with patch.object(db_manager, '_sqlite_connected', True):
                with patch.object(db_manager, '_mongo_client') as mock_mongo:
                    with patch.object(db_manager, '_sqlite_engine') as mock_sqlite:
                        # Mock successful pings
                        mock_mongo.admin.command = AsyncMock()

                        mock_connection = MagicMock()
                        mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
                        mock_connection.__aexit__ = AsyncMock()
                        mock_connection.execute = AsyncMock()
                        mock_sqlite.connect.return_value = mock_connection

                        health = await db_manager.health_check()

                        assert health['mongo_connected'] is True
                        assert health['sqlite_connected'] is True
                        assert health['overall_healthy'] is True
                        assert 'mongo_ping' in health
                        assert 'sqlite_ping' in health

    async def test_health_check_with_failures(self, test_database_config):
        """Test health check with database failures."""
        db_manager = DatabaseManager(config=test_database_config)

        # Test MongoDB failure
        with patch.object(db_manager, '_mongo_connected', True):
            with patch.object(db_manager, '_sqlite_connected', False):
                with patch.object(db_manager, '_mongo_client') as mock_mongo:
                    mock_mongo.admin.command = AsyncMock(side_effect=ConnectionError("MongoDB ping failed"))

                    health = await db_manager.health_check()
                    assert health['mongo_ping'] is False
                    assert 'mongo_error' in health

    async def test_collection_initialization(self, test_database_config):
        """Test MongoDB collection initialization."""
        db_manager = DatabaseManager(config=test_database_config)

        with patch.object(db_manager, 'get_mongo_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.list_collection_names = AsyncMock(return_value=['existing_collection'])
            mock_db.create_collection = AsyncMock()

            # Mock index creation
            mock_users = MagicMock()
            mock_users.create_index = AsyncMock()
            mock_db.users = mock_users

            mock_narratives = MagicMock()
            mock_narratives.create_index = AsyncMock()
            mock_db.narrative_fragments = mock_narratives

            mock_items = MagicMock()
            mock_items.create_index = AsyncMock()
            mock_db.items = mock_items

            mock_get_db.return_value = mock_db

            result = await db_manager.ensure_collections()
            assert result is True

            # Verify collections were created
            assert mock_db.create_collection.call_count >= 2  # At least missing collections

            # Verify indexes were created
            mock_users.create_index.assert_called()
            mock_narratives.create_index.assert_called()
            mock_items.create_index.assert_called()

    async def test_table_initialization(self, test_database_config):
        """Test SQLite table initialization."""
        db_manager = DatabaseManager(config=test_database_config)

        with patch.object(db_manager, 'get_sqlite_engine') as mock_get_engine:
            mock_engine = MagicMock()
            mock_connection = MagicMock()
            mock_connection.__aenter__ = AsyncMock(return_value=mock_connection)
            mock_connection.__aexit__ = AsyncMock()
            mock_connection.execute = AsyncMock()
            mock_connection.commit = AsyncMock()
            mock_engine.connect.return_value = mock_connection
            mock_get_engine.return_value = mock_engine

            result = await db_manager.ensure_tables()
            assert result is True

            # Verify SQL was executed
            assert mock_connection.execute.call_count >= 2  # user_profiles and subscriptions
            mock_connection.commit.assert_called()

    async def test_connection_cleanup(self, test_database_config):
        """Test connection cleanup functionality."""
        db_manager = DatabaseManager(config=test_database_config)

        # Set up mock connections
        mock_mongo_client = MagicMock()
        mock_mongo_client.close = MagicMock()
        db_manager._mongo_client = mock_mongo_client

        mock_sqlite_engine = MagicMock()
        mock_sqlite_engine.dispose = AsyncMock()
        db_manager._sqlite_engine = mock_sqlite_engine

        # Test cleanup
        await db_manager.close_connections()

        # Verify cleanup was called
        mock_mongo_client.close.assert_called_once()
        mock_sqlite_engine.dispose.assert_called_once()

        # Verify state was updated
        assert db_manager._mongo_connected is False
        assert db_manager._sqlite_connected is False
        assert db_manager._connected is False

    async def test_rollback_user_creation(self, test_database_config):
        """Test user creation rollback functionality."""
        db_manager = DatabaseManager(config=test_database_config)
        user_id = "test_user_123"

        # Mock successful rollback
        with patch.object(db_manager, 'get_mongo_db') as mock_get_mongo:
            with patch.object(db_manager, 'delete_user_profile_from_sqlite') as mock_delete_sqlite:
                mock_mongo_db = MagicMock()
                mock_mongo_db.users.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
                mock_get_mongo.return_value = mock_mongo_db

                mock_delete_sqlite.return_value = True

                db_manager._mongo_connected = True
                db_manager._sqlite_connected = True

                result = await db_manager.rollback_user_creation(user_id)
                assert result is True

                # Verify both deletions were attempted
                mock_mongo_db.users.delete_one.assert_called_once_with({"user_id": user_id})
                mock_delete_sqlite.assert_called_once_with(user_id)

    async def test_database_initialization_complete_flow(self, test_database_config):
        """Test complete database initialization flow."""
        db_manager = DatabaseManager(config=test_database_config)

        with patch.object(db_manager, 'connect_all') as mock_connect:
            with patch.object(db_manager, 'ensure_collections') as mock_collections:
                with patch.object(db_manager, 'ensure_tables') as mock_tables:
                    mock_connect.return_value = True
                    mock_collections.return_value = True
                    mock_tables.return_value = True

                    result = await db_manager.initialize_databases()
                    assert result is True

                    # Verify all steps were called
                    mock_connect.assert_called_once()
                    mock_collections.assert_called_once()
                    mock_tables.assert_called_once()

    async def test_global_database_manager_singleton(self):
        """Test global database manager singleton pattern."""
        db_manager1 = get_database_manager()
        db_manager2 = get_database_manager()
        assert db_manager1 is db_manager2

        # Test reset
        await reset_database_manager()
        db_manager3 = get_database_manager()
        assert db_manager3 is not db_manager1

    async def test_configuration_edge_cases(self, temp_db_file):
        """Test configuration edge cases and fallbacks."""
        # Test with minimal config
        minimal_config = {
            'mongodb_uri': 'mongodb://localhost:27017',
            'mongodb_database': 'test',
            'sqlite_database_path': temp_db_file
        }

        db_manager = DatabaseManager(config=minimal_config)
        assert db_manager.database_config.pool_size == 20  # Default fallback

        # Test with nested config structure (legacy format)
        nested_config = {
            'mongodb_uri': 'mongodb://localhost:27017',
            'mongodb_database': 'test',
            'sqlite_database_path': temp_db_file,
            'sqlite_config': {
                'pool_size': 15,
                'max_overflow': 25
            },
            'mongodb_config': {
                'min_pool_size': 3,
                'max_pool_size': 20
            }
        }

        db_manager2 = DatabaseManager(config=nested_config)
        assert db_manager2.database_config.pool_size == 15
        assert db_manager2.database_config.mongodb_min_pool_size == 3