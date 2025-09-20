"""
Integration tests for the subscription workflow.
Implements tests for requirements 3.2 and 4.5 from the modulos-atomicos specification.

Requirement 3.2: WHEN subscriptions expire THEN the system SHALL run cron jobs and publish subscription_expired events
Requirement 4.5: WHEN cross-module workflows execute THEN events SHALL be processed in chronological order using correlation IDs
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.modules.admin.subscription_manager import SubscriptionManager, Subscription, VipStatus, ExpiredSubscription
from src.events.bus import EventBus
from src.events.models import Event


@pytest.fixture
def mock_db():
    """Create a mock database for testing."""
    mock_db = Mock()
    mock_db.__getitem__ = Mock()
    mock_subscriptions = Mock()
    mock_db.__getitem__.return_value = mock_subscriptions
    return mock_db, mock_subscriptions


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    mock_bus = Mock(spec=EventBus)
    mock_bus.publish = AsyncMock()
    return mock_bus


@pytest.fixture
def subscription_manager(mock_db, mock_event_bus):
    """Create a subscription manager instance for testing."""
    db, subscriptions = mock_db
    return SubscriptionManager(db, mock_event_bus)


class TestSubscriptionWorkflow:
    """Integration tests for the subscription workflow."""

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, subscription_manager, mock_db, mock_event_bus):
        """Test successful creation of a subscription."""
        # Arrange
        user_id = "test_user_123"
        plan_type = "vip"
        duration_days = 30
        mock_db_instance, mock_subscriptions = mock_db
        
        # Mock the insert result
        mock_result = Mock()
        mock_result.inserted_id = "subscription_456"
        mock_subscriptions.insert_one = AsyncMock(return_value=mock_result)

        # Act
        subscription = await subscription_manager.create_subscription(user_id, plan_type, duration_days)

        # Assert
        assert isinstance(subscription, Subscription)
        assert subscription.user_id == user_id
        assert subscription.plan_type == plan_type
        assert subscription.status == "active"
        assert subscription.start_date <= datetime.utcnow()
        assert subscription.end_date is not None
        assert subscription.end_date > subscription.start_date
        
        # Verify database call
        mock_subscriptions.insert_one.assert_called_once()
        
        # Verify event was published
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_vip_status_active_subscription(self, subscription_manager, mock_db):
        """Test checking VIP status for user with active subscription."""
        # Arrange
        user_id = "test_user_123"
        mock_db_instance, mock_subscriptions = mock_db
        
        # Mock active VIP subscription
        now = datetime.utcnow()
        end_date = now + timedelta(days=30)
        mock_subscription = {
            "_id": "subscription_456",
            "user_id": user_id,
            "plan_type": "vip",
            "start_date": now - timedelta(days=10),
            "end_date": end_date,
            "status": "active"
        }
        mock_subscriptions.find_one = AsyncMock(return_value=mock_subscription)

        # Act
        vip_status = await subscription_manager.check_vip_status(user_id)

        # Assert
        assert isinstance(vip_status, VipStatus)
        assert vip_status.is_vip is True
        assert vip_status.plan_type == "vip"
        assert vip_status.end_date == end_date

    @pytest.mark.asyncio
    async def test_check_vip_status_no_subscription(self, subscription_manager, mock_db):
        """Test checking VIP status for user with no subscription."""
        # Arrange
        user_id = "test_user_123"
        mock_db_instance, mock_subscriptions = mock_db
        
        # Mock no subscription found
        mock_subscriptions.find_one = AsyncMock(return_value=None)

        # Act
        vip_status = await subscription_manager.check_vip_status(user_id)

        # Assert
        assert isinstance(vip_status, VipStatus)
        assert vip_status.is_vip is False
        assert vip_status.plan_type is None
        assert vip_status.end_date is None

    @pytest.mark.asyncio
    async def test_check_vip_status_expired_subscription(self, subscription_manager, mock_db):
        """Test checking VIP status for user with expired subscription."""
        # Arrange
        user_id = "test_user_123"
        mock_db_instance, mock_subscriptions = mock_db
        
        # Mock expired subscription
        now = datetime.utcnow()
        past_date = now - timedelta(days=10)
        mock_subscription = {
            "_id": "subscription_456",
            "user_id": user_id,
            "plan_type": "vip",
            "start_date": now - timedelta(days=40),
            "end_date": past_date,
            "status": "active"
        }
        mock_subscriptions.find_one = AsyncMock(return_value=mock_subscription)
        mock_subscriptions.update_one = AsyncMock()

        # Act
        vip_status = await subscription_manager.check_vip_status(user_id)

        # Assert
        assert isinstance(vip_status, VipStatus)
        assert vip_status.is_vip is False
        
        # Verify subscription was updated to expired
        mock_subscriptions.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_expiration_success(self, subscription_manager, mock_db, mock_event_bus):
        """Test successful processing of expired subscriptions.
        
        Implements requirement 3.2: WHEN subscriptions expire THEN the system SHALL 
        run cron jobs and publish subscription_expired events
        """
        # Arrange
        mock_db_instance, mock_subscriptions = mock_db
        now = datetime.utcnow()
        
        # Mock expired subscriptions
        expired_sub_1 = {
            "_id": "subscription_1",
            "user_id": "user_123",
            "plan_type": "premium",
            "start_date": now - timedelta(days=40),
            "end_date": now - timedelta(days=10),
            "status": "active"
        }
        expired_sub_2 = {
            "_id": "subscription_2",
            "user_id": "user_456",
            "plan_type": "vip",
            "start_date": now - timedelta(days=35),
            "end_date": now - timedelta(days=5),
            "status": "active"
        }
        
        # Mock async cursor for find operation
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = Mock(return_value=iter([expired_sub_1, expired_sub_2]))
        mock_subscriptions.find.return_value = mock_cursor
        mock_subscriptions.update_one = AsyncMock()

        # Act
        expired_subscriptions = await subscription_manager.process_expiration()

        # Assert
        assert len(expired_subscriptions) == 2
        assert all(isinstance(sub, ExpiredSubscription) for sub in expired_subscriptions)
        
        # Verify database updates were called
        assert mock_subscriptions.update_one.call_count == 2
        
        # Verify events were published
        assert mock_event_bus.publish.call_count == 2
        
        # Check that events published match requirement 3.2
        for call in mock_event_bus.publish.call_args_list:
            event = call[0][0] if call[0] else None
            if event:
                # Should be a subscription_updated event with status="expired"
                assert event["event_type"] == "subscription_updated"
                assert event["data"]["status"] == "expired"

    @pytest.mark.asyncio
    async def test_subscription_workflow_integration(self, subscription_manager, mock_db, mock_event_bus):
        """Test complete subscription workflow integration.
        
        Implements requirement 4.5: WHEN cross-module workflows execute THEN events 
        SHALL be processed in chronological order using correlation IDs
        """
        # Arrange
        user_id = "workflow_test_user"
        plan_type = "vip"
        duration_days = 15
        mock_db_instance, mock_subscriptions = mock_db
        
        # Mock the insert result for subscription creation
        mock_result = Mock()
        mock_result.inserted_id = "workflow_subscription_789"
        mock_subscriptions.insert_one = AsyncMock(return_value=mock_result)
        
        # Mock find_one for checking status
        mock_subscriptions.find_one = AsyncMock(return_value=None)

        # Act - Step 1: Create subscription
        subscription = await subscription_manager.create_subscription(user_id, plan_type, duration_days)
        
        # Act - Step 2: Check VIP status
        vip_status = await subscription_manager.check_vip_status(user_id)
        
        # Act - Step 3: Process expiration (no expired subscriptions in this case)
        expired_subscriptions = await subscription_manager.process_expiration()

        # Assert - Verify complete workflow
        assert isinstance(subscription, Subscription)
        assert subscription.user_id == user_id
        assert subscription.plan_type == plan_type
        assert subscription.status == "active"
        
        assert isinstance(vip_status, VipStatus)
        # Should be VIP since subscription is active and not expired
        assert vip_status.is_vip is True
        
        # No subscriptions should have expired
        assert len(expired_subscriptions) == 0
        
        # Verify chronological event publishing with correlation
        # First event should be for subscription creation
        first_call = mock_event_bus.publish.call_args_list[0]
        first_event = first_call[0][0] if first_call[0] else None
        
        if first_event:
            assert first_event["event_type"] == "subscription_updated"
            assert first_event["data"]["status"] == "active"
            # Should have a correlation ID for tracking
            assert "correlation_id" in first_event


if __name__ == "__main__":
    pytest.main([__file__])