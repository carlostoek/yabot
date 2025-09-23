"""
Unit tests for the UserService class.

This module provides comprehensive unit tests for the UserService class,
implementing the testing requirements specified in fase1 specification section 1.3.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from src.services.user import (
    UserService, 
    UserServiceError, 
    UserCreationError, 
    UserNotFoundError
)
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.events.models import BaseEvent


class TestUserService:
    """Test cases for the UserService class."""
    
    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock database manager for testing."""
        mock_db_manager = Mock(spec=DatabaseManager)
        
        # Mock SQLite connection
        mock_sqlite_conn = Mock()
        mock_sqlite_cursor = Mock()
        mock_sqlite_conn.cursor.return_value = mock_sqlite_cursor
        mock_db_manager.get_sqlite_conn.return_value = mock_sqlite_conn
        
        # Mock MongoDB connection
        mock_mongo_db = Mock()
        mock_users_collection = Mock()
        mock_mongo_db.__getitem__ = Mock(return_value=mock_users_collection)
        mock_db_manager.get_mongo_db.return_value = mock_mongo_db
        
        return mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus for testing."""
        mock_event_bus = Mock(spec=EventBus)
        mock_event_bus.publish = AsyncMock()
        return mock_event_bus
    
    @pytest.fixture
    def user_service(self, mock_database_manager, mock_event_bus):
        """Create a UserService instance with mocked dependencies."""
        mock_db_manager, _, _, _, _ = mock_database_manager
        return UserService(mock_db_manager, mock_event_bus)
    
    def test_init(self, mock_database_manager, mock_event_bus):
        """Test UserService initialization."""
        mock_db_manager, _, _, _, _ = mock_database_manager
        user_service = UserService(mock_db_manager, mock_event_bus)
        
        assert user_service.database_manager == mock_db_manager
        assert user_service.event_bus == mock_event_bus
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_database_manager, mock_event_bus):
        """Test successful user creation."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock successful operations
        mock_sqlite_cursor.execute.return_value = None
        mock_sqlite_conn.commit.return_value = None
        mock_insert_result = Mock()
        mock_insert_result.acknowledged = True
        mock_users_collection.insert_one.return_value = mock_insert_result
        mock_event_bus.publish.return_value = None
        
        # Test data
        telegram_user = {
            "id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en"
        }
        
        # Call the method
        result = await user_service.create_user(telegram_user)
        
        # Verify SQLite operations
        assert mock_sqlite_cursor.execute.call_count >= 1
        assert mock_sqlite_conn.commit.call_count == 1
        
        # Verify MongoDB operations
        assert mock_users_collection.insert_one.call_count == 1
        
        # Verify event publishing
        assert mock_event_bus.publish.call_count == 1
        args, kwargs = mock_event_bus.publish.call_args
        assert args[0] == "user_registered"
        
        # Verify result
        assert isinstance(result, dict)
        assert "user_id" in result
        assert "telegram_user" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert result["telegram_user"] == telegram_user
    
    @pytest.mark.asyncio
    async def test_create_user_sqlite_failure(self, user_service, mock_database_manager, mock_event_bus):
        """Test user creation failure when SQLite operation fails."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock SQLite failure
        mock_sqlite_cursor.execute.side_effect = Exception("SQLite error")
        
        # Test data
        telegram_user = {
            "id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en"
        }
        
        # Call the method and expect failure
        with pytest.raises(UserCreationError):
            await user_service.create_user(telegram_user)
        
        # Verify rollback was attempted
        assert mock_event_bus.publish.call_count == 0
    
    @pytest.mark.asyncio
    async def test_create_user_mongo_failure(self, user_service, mock_database_manager, mock_event_bus):
        """Test user creation failure when MongoDB operation fails."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock successful SQLite but failed MongoDB
        mock_sqlite_cursor.execute.return_value = None
        mock_sqlite_conn.commit.return_value = None
        mock_users_collection.insert_one.side_effect = Exception("MongoDB error")
        
        # Test data
        telegram_user = {
            "id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "language_code": "en"
        }
        
        # Call the method and expect failure
        with pytest.raises(UserCreationError):
            await user_service.create_user(telegram_user)
        
        # Verify rollback was attempted
        assert mock_event_bus.publish.call_count == 0
    
    @pytest.mark.asyncio
    async def test_get_user_context_success(self, user_service, mock_database_manager):
        """Test successful user context retrieval."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock successful data retrieval
        mock_sqlite_cursor.fetchone.return_value = (
            "test_user_123", 123456789, "testuser", "Test", "User", "en", 
            datetime.utcnow(), datetime.utcnow(), 1
        )
        mock_cursor_desc = [("user_id",), ("telegram_user_id",), ("username",), 
                           ("first_name",), ("last_name",), ("language_code",), 
                           ("registration_date",), ("last_login",), ("is_active",)]
        mock_sqlite_cursor.description = mock_cursor_desc
        
        mock_users_collection.find_one.return_value = {
            "_id": "some_mongo_id",
            "user_id": "test_user_123",
            "current_state": {
                "menu_context": "main_menu",
                "narrative_progress": {
                    "current_fragment": "fragment_001",
                    "completed_fragments": [],
                    "choices_made": []
                },
                "session_data": {
                    "last_activity": datetime.utcnow().isoformat()
                }
            },
            "preferences": {
                "language": "en",
                "notifications_enabled": True,
                "theme": "default"
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Call the method
        result = await user_service.get_user_context("test_user_123")
        
        # Verify SQLite query
        assert mock_sqlite_cursor.execute.call_count == 1
        args, kwargs = mock_sqlite_cursor.execute.call_args
        assert "SELECT * FROM user_profiles WHERE user_id = ?" in args[0]
        
        # Verify MongoDB query
        assert mock_users_collection.find_one.call_count == 1
        args, kwargs = mock_users_collection.find_one.call_args
        assert args[0]["user_id"] == "test_user_123"
        
        # Verify result
        assert isinstance(result, dict)
        assert "user_id" in result
        assert "profile" in result
        assert "state" in result
        assert result["user_id"] == "test_user_123"
    
    @pytest.mark.asyncio
    async def test_get_user_context_not_found(self, user_service, mock_database_manager):
        """Test user context retrieval when user is not found."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock user not found
        mock_sqlite_cursor.fetchone.return_value = None
        
        # Call the method and expect failure
        with pytest.raises(UserNotFoundError):
            await user_service.get_user_context("nonexistent_user")
    
    @pytest.mark.asyncio
    async def test_update_user_state_success(self, user_service, mock_database_manager):
        """Test successful user state update."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock successful update
        mock_update_result = Mock()
        mock_update_result.modified_count = 1
        mock_users_collection.update_one.return_value = mock_update_result
        
        # Test data
        state_updates = {
            "current_state": {
                "menu_context": "settings_menu"
            }
        }
        
        # Call the method
        result = await user_service.update_user_state("test_user_123", state_updates)
        
        # Verify MongoDB update
        assert mock_users_collection.update_one.call_count == 1
        args, kwargs = mock_users_collection.update_one.call_args
        assert args[0]["user_id"] == "test_user_123"
        assert "$set" in args[1]
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_user_state_no_changes(self, user_service, mock_database_manager):
        """Test user state update when no changes are made."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock update with no changes
        mock_update_result = Mock()
        mock_update_result.modified_count = 0
        mock_users_collection.update_one.return_value = mock_update_result
        
        # Test data
        state_updates = {
            "current_state": {
                "menu_context": "same_menu"
            }
        }
        
        # Call the method
        result = await user_service.update_user_state("test_user_123", state_updates)
        
        # Verify result
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service, mock_database_manager):
        """Test successful user profile update."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock successful update
        mock_sqlite_cursor.rowcount = 1
        mock_sqlite_conn.commit.return_value = None
        
        # Test data
        profile_updates = {
            "username": "newusername",
            "first_name": "NewFirst"
        }
        
        # Call the method
        result = await user_service.update_user_profile("test_user_123", profile_updates)
        
        # Verify SQLite update
        assert mock_sqlite_cursor.execute.call_count == 1
        args, kwargs = mock_sqlite_cursor.execute.call_args
        assert "UPDATE user_profiles SET" in args[0]
        assert "username = ?" in args[0]
        assert "first_name = ?" in args[0]
        assert args[0].endswith("WHERE user_id = ?")
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_database_manager, mock_event_bus):
        """Test successful user deletion."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock successful deletions
        mock_sqlite_cursor.rowcount = 1
        mock_sqlite_conn.commit.return_value = None
        mock_delete_result = Mock()
        mock_delete_result.deleted_count = 1
        mock_users_collection.delete_one.return_value = mock_delete_result
        
        # Call the method
        result = await user_service.delete_user("test_user_123", "test_reason")
        
        # Verify SQLite deletion
        assert mock_sqlite_cursor.execute.call_count == 1
        args, kwargs = mock_sqlite_cursor.execute.call_args
        assert "DELETE FROM user_profiles WHERE user_id = ?" in args[0]
        
        # Verify MongoDB deletion
        assert mock_users_collection.delete_one.call_count == 1
        args, kwargs = mock_users_collection.delete_one.call_args
        assert args[0]["user_id"] == "test_user_123"
        
        # Verify event publishing
        assert mock_event_bus.publish.call_count == 1
        args, kwargs = mock_event_bus.publish.call_args
        assert args[0] == "user_deleted"
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_user_failure(self, user_service, mock_database_manager, mock_event_bus):
        """Test user deletion failure."""
        mock_db_manager, mock_sqlite_conn, mock_sqlite_cursor, mock_mongo_db, mock_users_collection = mock_database_manager
        
        # Mock SQLite success but MongoDB failure
        mock_sqlite_cursor.rowcount = 1
        mock_sqlite_conn.commit.return_value = None
        mock_delete_result = Mock()
        mock_delete_result.deleted_count = 0  # Indicates failure
        mock_users_collection.delete_one.return_value = mock_delete_result
        
        # Call the method
        result = await user_service.delete_user("test_user_123", "test_reason")
        
        # Verify result is False due to MongoDB failure
        assert result is False


# Test convenience function
@pytest.mark.asyncio
async def test_create_user_service():
    """Test the create_user_service convenience function."""
    mock_database_manager = Mock(spec=DatabaseManager)
    mock_event_bus = Mock(spec=EventBus)
    
    # Import inside test to avoid circular imports
    from src.services.user import create_user_service
    
    user_service = await create_user_service(mock_database_manager, mock_event_bus)
    
    assert isinstance(user_service, UserService)
    assert user_service.database_manager == mock_database_manager
    assert user_service.event_bus == mock_event_bus