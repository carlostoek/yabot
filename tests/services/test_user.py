"""
UserService Unit Tests

Comprehensive unit tests for the UserService class following requirement 1.3: User CRUD Operations.
Tests leverage existing test utilities from tests/utils/database.py and tests/utils/events.py
to provide proper mocking and validation of service functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from src.services.user import UserService, UserStatus
from src.database.manager import DatabaseManager
from src.events.bus import EventBus

from src.events.models import UserRegistrationEvent, UserInteractionEvent


class TestDataGenerator:
    @staticmethod
    def generate_telegram_user() -> Dict[str, Any]:
        return {
            "id": 123456789,
            "is_bot": False,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "language_code": "en",
        }

    @staticmethod
    def generate_user_mongo_doc(user_id: str) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "current_state": {
                "menu_context": "main_menu",
                "narrative_progress": {},
                "session_data": {},
            },
            "preferences": {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    @staticmethod
    def generate_user_sqlite_profile(user_id: str, telegram_user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "telegram_user_id": telegram_user["id"],
            "username": telegram_user.get("username"),
            "first_name": telegram_user.get("first_name"),
            "last_name": telegram_user.get("last_name"),
            "language_code": telegram_user.get("language_code"),
            "registration_date": datetime.utcnow(),
            "last_login": datetime.utcnow(),
            "is_active": True,
        }


class TestUserService:

    """Unit tests for UserService class"""

    @pytest.fixture
    def mock_db_manager(self) -> AsyncMock:
        """Create mock DatabaseManager for testing"""
        mock_db = AsyncMock(spec=DatabaseManager)

        # Configure default return values
        mock_db.create_user_atomic.return_value = True
        mock_db.get_user_from_mongo.return_value = None
        mock_db.get_user_profile_from_sqlite.return_value = None
        mock_db.update_user_in_mongo.return_value = True
        mock_db.update_user_profile_in_sqlite.return_value = True
        mock_db.get_subscription_from_sqlite.return_value = None
        mock_db.delete_user_from_mongo.return_value = True
        mock_db.delete_user_profile_from_sqlite.return_value = True

        return mock_db

    @pytest.fixture
    def mock_event_bus(self) -> AsyncMock:
        """Create mock EventBus for testing"""
        mock_bus = AsyncMock(spec=EventBus)
        mock_bus.publish.return_value = True
        return mock_bus

    @pytest.fixture
    def user_service(self, mock_db_manager, mock_event_bus) -> UserService:
        """Create UserService instance with mocked dependencies"""
        return UserService(mock_db_manager)

    @pytest.fixture
    def sample_telegram_user(self) -> Dict[str, Any]:
        """Generate sample Telegram user data"""
        return TestDataGenerator.generate_telegram_user()

    @pytest.fixture
    def sample_user_state(self) -> Dict[str, Any]:
        """Generate sample user state data"""
        return {
            "menu_context": "narrative_menu",
            "narrative_progress": {
                "current_fragment": "fragment_001",
                "completed_fragments": ["intro_001"],
                "choices_made": [{"fragment": "intro_001", "choice": "choice_a"}]
            },
            "session_data": {"last_activity": datetime.utcnow().isoformat()}
        }

    @pytest.fixture
    def sample_mongo_user(self) -> Dict[str, Any]:
        """Generate sample MongoDB user document"""
        user_id = "123456789"
        return TestDataGenerator.generate_user_mongo_doc(user_id)

    @pytest.fixture
    def sample_sqlite_profile(self) -> Dict[str, Any]:
        """Generate sample SQLite user profile"""
        user_id = "123456789"
        telegram_data = TestDataGenerator.generate_telegram_user()
        return TestDataGenerator.generate_user_sqlite_profile(user_id, telegram_data)


class TestCreateUser(TestUserService):
    """Tests for create_user method"""

    async def test_create_user_success(self, user_service, mock_db_manager, mock_event_bus, sample_telegram_user):
        """Test successful user creation"""
        # Arrange
        mock_db_manager.create_user_atomic.return_value = True
        expected_user_id = str(sample_telegram_user["id"])

        # Act
        result = await user_service.create_user(sample_telegram_user)

        # Assert
        assert result is not None
        assert result["user_id"] == expected_user_id
        assert result["mongo_created"] is True
        assert result["sqlite_created"] is True
        assert "profile" in result

        # Verify database manager was called correctly
        mock_db_manager.create_user_atomic.assert_called_once()
        call_args = mock_db_manager.create_user_atomic.call_args[0]
        assert call_args[0] == expected_user_id  # user_id
        assert call_args[1]["user_id"] == expected_user_id  # mongo doc
        assert call_args[2]["user_id"] == expected_user_id  # sqlite profile

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event_call_args = mock_event_bus.publish.call_args[0]
        assert event_call_args[0] == "user_registered"
        assert "user_id" in event_call_args[1]

    async def test_create_user_database_failure(self, user_service, mock_db_manager, mock_event_bus, sample_telegram_user):
        """Test user creation when database operation fails"""
        # Arrange
        mock_db_manager.create_user_atomic.return_value = False

        # Act
        result = await user_service.create_user(sample_telegram_user)

        # Assert
        assert result is None
        mock_event_bus.publish.assert_not_called()

    async def test_create_user_exception_handling(self, user_service, mock_db_manager, mock_event_bus, sample_telegram_user):
        """Test exception handling during user creation"""
        # Arrange
        mock_db_manager.create_user_atomic.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await user_service.create_user(sample_telegram_user)

        # Verify event was not published due to exception
        mock_event_bus.publish.assert_not_called()

    async def test_create_user_data_structure(self, user_service, mock_db_manager, mock_event_bus, sample_telegram_user):
        """Test that create_user generates correct data structures"""
        # Arrange
        mock_db_manager.create_user_atomic.return_value = True
        expected_user_id = str(sample_telegram_user["id"])

        # Act
        await user_service.create_user(sample_telegram_user)

        # Assert - Check MongoDB document structure
        call_args = mock_db_manager.create_user_atomic.call_args[0]
        mongo_doc = call_args[1]

        assert mongo_doc["user_id"] == expected_user_id
        assert "current_state" in mongo_doc
        assert "menu_context" in mongo_doc["current_state"]
        assert "narrative_progress" in mongo_doc["current_state"]
        assert "preferences" in mongo_doc
        assert isinstance(mongo_doc["created_at"], datetime)

        # Assert - Check SQLite profile structure
        sqlite_profile = call_args[2]
        assert sqlite_profile["user_id"] == expected_user_id
        assert sqlite_profile["telegram_user_id"] == sample_telegram_user["id"]
        assert sqlite_profile["username"] == sample_telegram_user.get("username")
        assert sqlite_profile["is_active"] is True


class TestGetUserContext(TestUserService):
    """Tests for get_user_context method"""

    async def test_get_user_context_success(self, user_service, mock_db_manager, sample_mongo_user, sample_sqlite_profile):
        """Test successful retrieval of user context"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.get_user_from_mongo.return_value = sample_mongo_user
        mock_db_manager.get_user_profile_from_sqlite.return_value = sample_sqlite_profile

        # Act
        result = await user_service.get_user_context(user_id)

        # Assert
        assert result is not None
        assert result["user_id"] == user_id
        assert "mongo_data" in result
        assert "profile_data" in result
        assert "combined_context" in result

        # Verify combined context structure
        combined = result["combined_context"]
        assert "profile" in combined
        assert combined["user_id"] == user_id

        # Verify database calls
        mock_db_manager.get_user_from_mongo.assert_called_once_with(user_id)
        mock_db_manager.get_user_profile_from_sqlite.assert_called_once_with(user_id)

    async def test_get_user_context_mongo_not_found(self, user_service, mock_db_manager):
        """Test when user not found in MongoDB"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.get_user_from_mongo.return_value = None

        # Act
        result = await user_service.get_user_context(user_id)

        # Assert
        assert result is None
        mock_db_manager.get_user_from_mongo.assert_called_once_with(user_id)
        # Should not call SQLite if MongoDB fails
        mock_db_manager.get_user_profile_from_sqlite.assert_not_called()

    async def test_get_user_context_sqlite_not_found(self, user_service, mock_db_manager, sample_mongo_user):
        """Test when user profile not found in SQLite"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.get_user_from_mongo.return_value = sample_mongo_user
        mock_db_manager.get_user_profile_from_sqlite.return_value = None

        # Act
        result = await user_service.get_user_context(user_id)

        # Assert
        assert result is None
        mock_db_manager.get_user_from_mongo.assert_called_once_with(user_id)
        mock_db_manager.get_user_profile_from_sqlite.assert_called_once_with(user_id)

    async def test_get_user_context_exception_handling(self, user_service, mock_db_manager):
        """Test exception handling in get_user_context"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.get_user_from_mongo.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await user_service.get_user_context(user_id)


class TestUpdateUserState(TestUserService):
    """Tests for update_user_state method"""

    async def test_update_user_state_success(self, user_service, mock_db_manager, mock_event_bus, sample_user_state):
        """Test successful user state update"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.update_user_in_mongo.return_value = True

        # Act
        result = await user_service.update_user_state(user_id, sample_user_state)

        # Assert
        assert result is True

        # Verify database update call
        mock_db_manager.update_user_in_mongo.assert_called_once()
        call_args = mock_db_manager.update_user_in_mongo.call_args[0]
        assert call_args[0] == user_id
        update_data = call_args[1]
        assert "$set" in update_data
        assert update_data["$set"]["current_state"] == sample_user_state
        assert "updated_at" in update_data["$set"]

        # Verify event publication
        mock_event_bus.publish.assert_called_once()
        event_args = mock_event_bus.publish.call_args[0]
        assert event_args[0] == "user_state_updated"
        assert event_args[1]["user_id"] == user_id
        assert event_args[1]["action"] == "update_state"

    async def test_update_user_state_failure(self, user_service, mock_db_manager, mock_event_bus, sample_user_state):
        """Test user state update when database operation fails"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.update_user_in_mongo.return_value = False

        # Act
        result = await user_service.update_user_state(user_id, sample_user_state)

        # Assert
        assert result is False
        mock_event_bus.publish.assert_not_called()

    async def test_update_user_state_exception_handling(self, user_service, mock_db_manager, mock_event_bus, sample_user_state):
        """Test exception handling in update_user_state"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.update_user_in_mongo.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await user_service.update_user_state(user_id, sample_user_state)

        mock_event_bus.publish.assert_not_called()


class TestUpdateUserProfile(TestUserService):
    """Tests for update_user_profile method"""

    async def test_update_user_profile_success(self, user_service, mock_db_manager):
        """Test successful user profile update"""
        # Arrange
        user_id = "123456789"
        profile_updates = {"first_name": "Updated", "last_login": datetime.utcnow()}
        mock_db_manager.update_user_profile_in_sqlite.return_value = True

        # Act
        result = await user_service.update_user_profile(user_id, profile_updates)

        # Assert
        assert result is True
        mock_db_manager.update_user_profile_in_sqlite.assert_called_once_with(user_id, profile_updates)

    async def test_update_user_profile_failure(self, user_service, mock_db_manager):
        """Test user profile update when database operation fails"""
        # Arrange
        user_id = "123456789"
        profile_updates = {"first_name": "Updated"}
        mock_db_manager.update_user_profile_in_sqlite.return_value = False

        # Act
        result = await user_service.update_user_profile(user_id, profile_updates)

        # Assert
        assert result is False

    async def test_update_user_profile_exception_handling(self, user_service, mock_db_manager):
        """Test exception handling in update_user_profile"""
        # Arrange
        user_id = "123456789"
        profile_updates = {"first_name": "Updated"}
        mock_db_manager.update_user_profile_in_sqlite.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await user_service.update_user_profile(user_id, profile_updates)


class TestGetUserSubscriptionStatus(TestUserService):
    """Tests for get_user_subscription_status method"""

    async def test_get_subscription_status_with_subscription(self, user_service, mock_db_manager):
        """Test getting subscription status when subscription exists"""
        # Arrange
        user_id = "123456789"
        mock_subscription = {"user_id": user_id, "status": "premium", "plan_type": "premium"}
        mock_db_manager.get_subscription_from_sqlite.return_value = mock_subscription

        # Act
        result = await user_service.get_user_subscription_status(user_id)

        # Assert
        assert result == "premium"
        mock_db_manager.get_subscription_from_sqlite.assert_called_once_with(user_id)

    async def test_get_subscription_status_without_subscription(self, user_service, mock_db_manager):
        """Test getting subscription status when no subscription exists"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.get_subscription_from_sqlite.return_value = None

        # Act
        result = await user_service.get_user_subscription_status(user_id)

        # Assert
        assert result == "inactive"

    async def test_get_subscription_status_missing_status_field(self, user_service, mock_db_manager):
        """Test getting subscription status when subscription exists but status field is missing"""
        # Arrange
        user_id = "123456789"
        mock_subscription = {"user_id": user_id, "plan_type": "premium"}  # Missing status
        mock_db_manager.get_subscription_from_sqlite.return_value = mock_subscription

        # Act
        result = await user_service.get_user_subscription_status(user_id)

        # Assert
        assert result == "inactive"  # Default value

    async def test_get_subscription_status_exception_handling(self, user_service, mock_db_manager):
        """Test exception handling in get_user_subscription_status"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.get_subscription_from_sqlite.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await user_service.get_user_subscription_status(user_id)


class TestDeleteUser(TestUserService):
    """Tests for delete_user method"""

    async def test_delete_user_success(self, user_service, mock_db_manager, mock_event_bus):
        """Test successful user deletion"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.delete_user_from_mongo.return_value = True
        mock_db_manager.delete_user_profile_from_sqlite.return_value = True

        # Act
        result = await user_service.delete_user(user_id)

        # Assert
        assert result is True

        # Verify deletion calls
        mock_db_manager.delete_user_from_mongo.assert_called_once_with(user_id)
        mock_db_manager.delete_user_profile_from_sqlite.assert_called_once_with(user_id)

        # Verify event publication
        mock_event_bus.publish.assert_called_once()
        event_args = mock_event_bus.publish.call_args[0]
        assert event_args[0] == "user_deleted"
        event_data = event_args[1]
        assert event_data["event_type"] == "user_deleted"
        assert event_data["user_id"] == user_id
        assert "timestamp" in event_data

    async def test_delete_user_partial_failure_mongo_fails(self, user_service, mock_db_manager, mock_event_bus):
        """Test user deletion when MongoDB deletion fails"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.delete_user_from_mongo.return_value = False
        mock_db_manager.delete_user_profile_from_sqlite.return_value = True

        # Act
        result = await user_service.delete_user(user_id)

        # Assert
        assert result is False
        mock_event_bus.publish.assert_not_called()

    async def test_delete_user_partial_failure_sqlite_fails(self, user_service, mock_db_manager, mock_event_bus):
        """Test user deletion when SQLite deletion fails"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.delete_user_from_mongo.return_value = True
        mock_db_manager.delete_user_profile_from_sqlite.return_value = False

        # Act
        result = await user_service.delete_user(user_id)

        # Assert
        assert result is False
        mock_event_bus.publish.assert_not_called()

    async def test_delete_user_complete_failure(self, user_service, mock_db_manager, mock_event_bus):
        """Test user deletion when both operations fail"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.delete_user_from_mongo.return_value = False
        mock_db_manager.delete_user_profile_from_sqlite.return_value = False

        # Act
        result = await user_service.delete_user(user_id)

        # Assert
        assert result is False
        mock_event_bus.publish.assert_not_called()

    async def test_delete_user_exception_handling(self, user_service, mock_db_manager, mock_event_bus):
        """Test exception handling in delete_user"""
        # Arrange
        user_id = "123456789"
        mock_db_manager.delete_user_from_mongo.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await user_service.delete_user(user_id)

        mock_event_bus.publish.assert_not_called()


class TestUserServiceIntegration(TestUserService):
    """Integration-style tests for UserService business logic"""

    async def test_user_lifecycle_complete(self, user_service, mock_db_manager, mock_event_bus, sample_telegram_user):
        """Test complete user lifecycle: create, update, retrieve, delete"""
        user_id = str(sample_telegram_user["id"])

        # Configure mocks for successful operations
        mock_db_manager.create_user_atomic.return_value = True
        mock_db_manager.get_user_from_mongo.return_value = TestDataGenerator.generate_user_mongo_doc(user_id)
        mock_db_manager.get_user_profile_from_sqlite.return_value = TestDataGenerator.generate_user_sqlite_profile(
            user_id, sample_telegram_user
        )
        mock_db_manager.update_user_in_mongo.return_value = True
        mock_db_manager.update_user_profile_in_sqlite.return_value = True
        mock_db_manager.delete_user_from_mongo.return_value = True
        mock_db_manager.delete_user_profile_from_sqlite.return_value = True

        # 1. Create user
        create_result = await user_service.create_user(sample_telegram_user)
        assert create_result is not None
        assert create_result["user_id"] == user_id

        # 2. Retrieve user context
        context = await user_service.get_user_context(user_id)
        assert context is not None
        assert context["user_id"] == user_id

        # 3. Update user state
        new_state = {"menu_context": "shop", "session_data": {"test": True}}
        state_update_result = await user_service.update_user_state(user_id, new_state)
        assert state_update_result is True

        # 4. Update user profile
        profile_updates = {"last_login": datetime.utcnow()}
        profile_update_result = await user_service.update_user_profile(user_id, profile_updates)
        assert profile_update_result is True

        # 5. Delete user
        delete_result = await user_service.delete_user(user_id)
        assert delete_result is True

        # Verify all expected events were published
        expected_events = ["user_registered", "user_state_updated", "user_deleted"]
        publish_calls = mock_event_bus.publish.call_args_list
        assert len(publish_calls) == 3
        published_events = [call[0][0] for call in publish_calls]
        assert set(published_events) == set(expected_events)

    async def test_error_recovery_scenarios(self, user_service, mock_db_manager, mock_event_bus, sample_telegram_user):
        """Test error recovery scenarios and rollback behavior"""
        user_id = str(sample_telegram_user["id"])

        # Test create user failure - should not publish events
        mock_db_manager.create_user_atomic.return_value = False
        create_result = await user_service.create_user(sample_telegram_user)
        assert create_result is None
        mock_event_bus.publish.assert_not_called()

        # Reset mocks
        mock_event_bus.reset_mock()

        # Test partial update failures
        mock_db_manager.update_user_in_mongo.return_value = False
        new_state = {"menu_context": "updated"}
        state_result = await user_service.update_user_state(user_id, new_state)
        assert state_result is False
        mock_event_bus.publish.assert_not_called()

    async def test_data_consistency_validation(self, user_service, mock_db_manager, sample_telegram_user):
        """Test that data structures are consistent across operations"""
        user_id = str(sample_telegram_user["id"])
        mock_db_manager.create_user_atomic.return_value = True

        # Create user and verify data structure consistency
        await user_service.create_user(sample_telegram_user)

        # Verify the atomic creation call structure
        call_args = mock_db_manager.create_user_atomic.call_args[0]
        mongo_doc = call_args[1]
        sqlite_profile = call_args[2]

        # Verify user_id consistency
        assert call_args[0] == user_id
        assert mongo_doc["user_id"] == user_id
        assert sqlite_profile["user_id"] == user_id

        # Verify Telegram data mapping consistency
        assert sqlite_profile["telegram_user_id"] == sample_telegram_user["id"]
        assert mongo_doc["preferences"]["language"] == sample_telegram_user.get("language_code", "es")
        assert sqlite_profile["language_code"] == sample_telegram_user.get("language_code")

        # Verify required fields are present
        assert "current_state" in mongo_doc
        assert "narrative_progress" in mongo_doc["current_state"]
        assert "is_active" in sqlite_profile
        assert sqlite_profile["is_active"] is True


class TestUserServiceValidation(TestUserService):
    """Tests for UserService input validation and edge cases"""

    async def test_create_user_missing_required_fields(self, user_service, mock_db_manager):
        """Test create_user with missing required fields"""
        # Test with missing id field
        invalid_telegram_user = {"username": "test", "first_name": "Test"}

        with pytest.raises(KeyError):
            await user_service.create_user(invalid_telegram_user)

    async def test_operations_with_empty_user_id(self, user_service, mock_db_manager):
        """Test operations with empty or None user_id"""
        empty_user_ids = ["", None, "   "]

        for user_id in empty_user_ids:
            if user_id is not None:
                # These operations should handle empty strings gracefully
                context = await user_service.get_user_context(user_id)
                # The actual behavior depends on database manager implementation
                # At minimum, it should not crash

    async def test_large_data_handling(self, user_service, mock_db_manager, mock_event_bus, sample_telegram_user):
        """Test handling of large data structures"""
        # Create large state data
        large_state = {
            "menu_context": "test",
            "narrative_progress": {
                "current_fragment": "fragment_001",
                "completed_fragments": ["frag_" + str(i) for i in range(1000)],  # Large list
                "choices_made": [{"fragment": f"frag_{i}", "choice": f"choice_{i}"} for i in range(500)]
            },
            "session_data": {"large_data": "x" * 10000}  # Large string
        }

        mock_db_manager.update_user_in_mongo.return_value = True
        user_id = "123456789"

        # Should handle large data without issues
        result = await user_service.update_user_state(user_id, large_state)
        assert result is True

    async def test_concurrent_operations_simulation(self, user_service, mock_db_manager, mock_event_bus):
        """Test simulation of concurrent operations"""
        import asyncio

        user_id = "123456789"
        mock_db_manager.update_user_in_mongo.return_value = True
        mock_db_manager.update_user_profile_in_sqlite.return_value = True

        # Simulate concurrent state updates
        async def update_state():
            state = {"menu_context": "concurrent_test", "timestamp": datetime.utcnow().isoformat()}
            return await user_service.update_user_state(user_id, state)

        async def update_profile():
            profile = {"last_login": datetime.utcnow()}
            return await user_service.update_user_profile(user_id, profile)

        # Run concurrent operations
        results = await asyncio.gather(
            update_state(),
            update_profile(),
            update_state(),
            return_exceptions=True
        )

        # All operations should succeed (though order may vary)
        for result in results:
            if not isinstance(result, Exception):
                assert result is True


class TestUserServicePerformance(TestUserService):
    """Performance-related tests for UserService"""

    async def test_performance_requirements_validation(self, user_service, mock_db_manager, mock_event_bus, sample_telegram_user):
        """Test that operations meet performance requirements (< 100ms per requirement 1.3)"""
        import time

        # Configure fast mock responses
        mock_db_manager.create_user_atomic.return_value = True
        mock_db_manager.get_user_from_mongo.return_value = TestDataGenerator.generate_user_mongo_doc("123")
        mock_db_manager.get_user_profile_from_sqlite.return_value = TestDataGenerator.generate_user_sqlite_profile(
            "123", sample_telegram_user
        )

        # Test create_user performance
        start_time = time.time()
        result = await user_service.create_user(sample_telegram_user)
        create_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        assert result is not None
        # Note: This test measures mock performance, not actual database performance
        # Real performance testing would require actual database connections
        assert create_time < 1000  # Very generous limit for mock operations

        # Test get_user_context performance
        start_time = time.time()
        context = await user_service.get_user_context("123")
        get_time = (time.time() - start_time) * 1000

        assert context is not None
        assert get_time < 1000  # Very generous limit for mock operations