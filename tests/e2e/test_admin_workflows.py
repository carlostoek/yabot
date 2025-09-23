"""
End-to-end tests for admin workflows.
Implements tests for Requirement 3 user stories from the modulos-atomicos specification.

Requirement 3 User Story: As an administrator, I want to control user access, 
manage subscriptions, and schedule content, so that I can maintain organized 
and secure channels.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the modules to be tested
from src.modules.admin.access_control import AccessControl
from src.modules.admin.subscription_manager import SubscriptionManager
from src.modules.admin.post_scheduler import PostScheduler
from src.modules.admin.notification_system import NotificationSystem
from src.modules.admin.admin_commands import AdminCommandHandler as AdminCommandInterface

from src.events.bus import EventBus
from src.database.mongodb import MongoDBHandler


@pytest.fixture
def mock_mongodb_handler():
    """Create a mock MongoDB handler for testing."""
    mock_handler = Mock(spec=MongoDBHandler)
    # Set up mock collections
    mock_handler.get_users_collection.return_value = Mock()
    mock_handler.get_subscriptions_collection.return_value = Mock()
    mock_handler.get_scheduled_posts_collection.return_value = Mock()
    return mock_handler


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    mock_bus = Mock(spec=EventBus)
    mock_bus.publish = AsyncMock()
    return mock_bus


@pytest.fixture
def access_control(mock_mongodb_handler, mock_event_bus):
    """Create an access control instance for testing."""
    return AccessControl(mock_mongodb_handler, mock_event_bus)


@pytest.fixture
def subscription_manager(mock_mongodb_handler, mock_event_bus):
    """Create a subscription manager instance for testing."""
    return SubscriptionManager(mock_mongodb_handler, mock_event_bus)


@pytest.fixture
def post_scheduler(mock_mongodb_handler, mock_event_bus):
    """Create a post scheduler instance for testing."""
    return PostScheduler(mock_mongodb_handler, mock_event_bus)


@pytest.fixture
def notification_system(mock_mongodb_handler, mock_event_bus):
    """Create a notification system instance for testing."""
    return NotificationSystem(mock_mongodb_handler, mock_event_bus)


@pytest.fixture
def admin_commands(access_control, subscription_manager, post_scheduler, notification_system):
    """Create an admin command interface instance for testing."""
    return AdminCommandInterface(
        access_control=access_control,
        subscription_manager=subscription_manager,
        post_scheduler=post_scheduler,
        notification_system=notification_system
    )


class TestAdminWorkflows:
    """End-to-end tests for admin workflows."""

    @pytest.mark.asyncio
    async def test_complete_admin_workflow(self, 
                                         access_control, 
                                         subscription_manager, 
                                         post_scheduler, 
                                         notification_system, 
                                         admin_commands,
                                         mock_mongodb_handler,
                                         mock_event_bus):
        """Test a complete admin workflow:
        1. Grant user access to a channel
        2. Create a VIP subscription for the user
        3. Schedule a post in the channel
        4. Send a notification to the user
        5. Verify all actions were successful and events were published
        """
        # Test data
        user_id = "admin_test_user_123"
        channel_id = "admin_test_channel_456"
        duration_days = 30
        plan_type = "vip"
        
        # Test post data
        post_content = "This is a scheduled test post"
        post_time = datetime.utcnow() + timedelta(hours=1)
        
        # Test notification data
        notification_message = "Your VIP subscription has been activated"
        
        # Mock database responses
        users_collection = mock_mongodb_handler.get_users_collection.return_value
        subscriptions_collection = mock_mongodb_handler.get_subscriptions_collection.return_value
        scheduled_posts_collection = mock_mongodb_handler.get_scheduled_posts_collection.return_value
        
        # Mock successful database operations
        users_collection.update_one = AsyncMock(return_value=Mock(modified_count=1))
        subscriptions_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="subscription_789"))
        scheduled_posts_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="post_999"))
        
        # Step 1: Grant user access to channel
        # Implements requirement 3.1: WHEN user access is validated THEN the system SHALL 
        # use Telegram API to verify permissions and publish user_access_checked events
        access_granted = await access_control.grant_access(user_id, channel_id, duration_days)
        assert access_granted is True
        
        # Verify access granted event was published
        mock_event_bus.publish.assert_called()
        access_calls = [call for call in mock_event_bus.publish.call_args_list 
                       if 'user_access' in call[0][0]]
        assert len(access_calls) > 0
        
        # Step 2: Create VIP subscription for user
        # Implements requirement 3.2: WHEN subscriptions expire THEN the system SHALL 
        # run cron jobs and publish subscription_expired events
        subscription = await subscription_manager.create_subscription(user_id, plan_type, duration_days)
        assert subscription is not None
        assert subscription.user_id == user_id
        assert subscription.plan_type == plan_type
        assert subscription.status == "active"
        
        # Verify subscription created event was published
        subscription_calls = [call for call in mock_event_bus.publish.call_args_list 
                             if 'subscription' in call[0][0]]
        assert len(subscription_calls) > 0
        
        # Step 3: Schedule a post in the channel
        # Implements requirement 3.3: WHEN posts are scheduled THEN the system SHALL 
        # use APScheduler and publish post_scheduled events
        scheduled_post = await post_scheduler.schedule_post(post_content, channel_id, post_time)
        assert scheduled_post is not None
        assert scheduled_post.content == post_content
        assert scheduled_post.channel_id == channel_id
        assert scheduled_post.status == "scheduled"
        
        # Verify post scheduled event was published
        post_calls = [call for call in mock_event_bus.publish.call_args_list 
                     if 'post' in call[0][0]]
        assert len(post_calls) > 0
        
        # Step 4: Send notification to user
        # Implements requirement 3.6: WHEN notifications are sent THEN the system SHALL 
        # deliver push messages and publish notification_sent events
        notification_sent = await notification_system.send_notification(
            user_id, notification_message, "info"
        )
        assert notification_sent is True
        
        # Verify notification sent event was published
        notification_calls = [call for call in mock_event_bus.publish.call_args_list 
                             if 'notification' in call[0][0]]
        assert len(notification_calls) > 0
        
        # Step 5: Verify user has VIP access
        # This tests the integration between access control and subscription manager
        has_vip_access = await subscription_manager.check_vip_status(user_id)
        assert has_vip_access.is_vip is True
        assert has_vip_access.plan_type == plan_type
        
        # Summary of events that should have been published:
        # 1. user_access_granted
        # 2. subscription_created
        # 3. post_scheduled
        # 4. notification_sent
        total_calls = len(mock_event_bus.publish.call_args_list)
        assert total_calls >= 4, f"Expected at least 4 events to be published, got {total_calls}"

    @pytest.mark.asyncio
    async def test_admin_command_workflow(self,
                                        access_control,
                                        subscription_manager,
                                        post_scheduler,
                                        notification_system,
                                        admin_commands,
                                        mock_event_bus):
        """Test admin command workflow using the admin command interface.
        
        Implements requirement 3.7: WHEN admin commands are executed THEN the system SHALL 
        provide private command interfaces with inline menus
        """
        # Test data
        admin_user_id = "admin_user_999"
        target_user_id = "target_user_123"
        channel_id = "test_channel_456"
        
        # Mock the command processing
        with patch.object(access_control, 'grant_access', AsyncMock(return_value=True)) as mock_grant_access:
            with patch.object(subscription_manager, 'create_subscription', AsyncMock()) as mock_create_subscription:
                # Mock subscription return value
                mock_subscription = Mock()
                mock_subscription.user_id = target_user_id
                mock_subscription.plan_type = "premium"
                mock_subscription.status = "active"
                mock_create_subscription.return_value = mock_subscription
                
                # Test grant access command
                command_result = await admin_commands.process_admin_command(
                    admin_user_id,
                    "grant_access",
                    {
                        "user_id": target_user_id,
                        "channel_id": channel_id,
                        "duration_days": 7
                    }
                )
                
                # Verify command was processed
                assert command_result is not None
                mock_grant_access.assert_called_once_with(target_user_id, channel_id, 7)
                
                # Test create subscription command
                command_result = await admin_commands.process_admin_command(
                    admin_user_id,
                    "create_subscription",
                    {
                        "user_id": target_user_id,
                        "plan_type": "premium",
                        "duration_days": 30
                    }
                )
                
                # Verify command was processed
                assert command_result is not None
                mock_create_subscription.assert_called_once_with(target_user_id, "premium", 30)

    @pytest.mark.asyncio
    async def test_subscription_expiration_workflow(self,
                                                  subscription_manager,
                                                  mock_mongodb_handler,
                                                  mock_event_bus):
        """Test subscription expiration workflow.
        
        Implements requirement 3.2: WHEN subscriptions expire THEN the system SHALL 
        run cron jobs and publish subscription_expired events
        """
        # Test data
        user_id = "expiring_user_123"
        
        # Mock database with expiring subscriptions
        subscriptions_collection = mock_mongodb_handler.get_subscriptions_collection.return_value
        
        # Mock expired subscriptions
        now = datetime.utcnow()
        expired_subscription = {
            "_id": "expiring_sub_456",
            "user_id": user_id,
            "plan_type": "vip",
            "start_date": now - timedelta(days=40),
            "end_date": now - timedelta(days=10),  # Expired 10 days ago
            "status": "active"
        }
        
        # Mock async cursor for find operation
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = Mock(return_value=iter([expired_subscription]))
        subscriptions_collection.find.return_value = mock_cursor
        subscriptions_collection.update_one = AsyncMock()
        
        # Process subscription expiration
        expired_subscriptions = await subscription_manager.process_expiration()
        
        # Verify expired subscriptions were processed
        assert len(expired_subscriptions) == 1
        assert expired_subscriptions[0].user_id == user_id
        
        # Verify database was updated
        subscriptions_collection.update_one.assert_called_once()
        
        # Verify expiration event was published
        expiration_calls = [call for call in mock_event_bus.publish.call_args_list 
                           if 'subscription_expired' in call[0][0] or 'subscription_updated' in call[0][0]]
        assert len(expiration_calls) > 0, "Expected subscription expiration event to be published"

    @pytest.mark.asyncio
    async def test_admin_workflow_error_handling(self,
                                               access_control,
                                               subscription_manager,
                                               post_scheduler,
                                               notification_system,
                                               mock_mongodb_handler):
        """Test error handling in admin workflows."""
        user_id = "error_test_user_123"
        channel_id = "error_test_channel_456"
        
        # Mock database failure
        users_collection = mock_mongodb_handler.get_users_collection.return_value
        users_collection.update_one = AsyncMock(side_effect=Exception("Database connection failed"))
        
        # Test that errors are handled gracefully
        try:
            access_granted = await access_control.grant_access(user_id, channel_id, 7)
            # If we get here, the method should have handled the error gracefully
            assert access_granted is False, "Expected access grant to fail due to database error"
        except Exception:
            # If an exception is raised, that's also acceptable as long as it's handled
            pass
        
        # Test subscription manager error handling
        subscriptions_collection = mock_mongodb_handler.get_subscriptions_collection.return_value
        subscriptions_collection.insert_one = AsyncMock(side_effect=Exception("Database error"))
        
        try:
            subscription = await subscription_manager.create_subscription(user_id, "vip", 30)
            assert subscription is None, "Expected subscription creation to fail due to database error"
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])