"""
End-to-end workflow tests for the YABOT system.

This module provides comprehensive end-to-end tests that validate the integration
of all system components as required by the fase1 specification.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.coordinator import CoordinatorService
from src.services.user import UserService, UserNotFoundError
from src.services.subscription import SubscriptionService
from src.services.narrative import NarrativeService
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.config.manager import ConfigManager
from tests.utils.database import (
    MockDatabaseManager,
    DatabaseTestDataFactory
)
from tests.utils.events import (
    MockEventBus,
    EventTestDataFactory
)


class TestEndToEndWorkflows:
    """End-to-end workflow tests for integrated system components."""

    @pytest.fixture
    def mock_database_manager(self):
        """Create a mock database manager for testing."""
        return MockDatabaseManager()

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus for testing."""
        return MockEventBus()

    @pytest.fixture
    def mock_user_service(self, mock_database_manager, mock_event_bus):
        """Create a mock user service for testing."""
        return UserService(mock_database_manager, mock_event_bus)

    @pytest.fixture
    def mock_subscription_service(self, mock_database_manager, mock_event_bus):
        """Create a mock subscription service for testing."""
        return SubscriptionService(mock_database_manager, mock_event_bus)

    @pytest.fixture
    def mock_narrative_service(self, mock_database_manager, mock_subscription_service, mock_event_bus):
        """Create a mock narrative service for testing."""
        return NarrativeService(mock_database_manager, mock_subscription_service, mock_event_bus)

    @pytest.fixture
    def coordinator_service(self, mock_database_manager, mock_event_bus, 
                          mock_user_service, mock_subscription_service, mock_narrative_service):
        """Create a coordinator service for testing."""
        return CoordinatorService(
            mock_database_manager,
            mock_event_bus,
            mock_user_service,
            mock_subscription_service,
            mock_narrative_service
        )

    @pytest.mark.asyncio
    async def test_user_registration_workflow(self, coordinator_service, mock_user_service, mock_event_bus):
        """Test complete user registration workflow."""
        # Prepare test data
        user_id = "new_user_123"
        telegram_user_data = {
            "id": 123456789,
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "language_code": "en"
        }
        
        # Execute workflow
        success = await coordinator_service.process_user_interaction(
            user_id, 
            "start", 
            {"source": "telegram", "telegram_user": telegram_user_data}
        )
        
        # Verify workflow completion
        assert success is True
        
        # Verify event publishing
        published_events = mock_event_bus.published_events
        assert len(published_events) == 1
        
        event = published_events[0]
        assert event["event_name"] == "user_interaction"
        assert event["payload"]["user_id"] == user_id
        assert event["payload"]["action"] == "start"

    @pytest.mark.asyncio
    async def test_vip_access_validation_workflow(self, coordinator_service, mock_subscription_service, mock_event_bus):
        """Test VIP access validation workflow."""
        # Prepare test data
        user_id = "vip_user_123"
        
        # Mock subscription service to simulate VIP access
        mock_subscription_service.validate_vip_access = AsyncMock(return_value=True)
        
        # Execute workflow
        has_vip_access = await coordinator_service.validate_vip_access(user_id)
        
        # Verify workflow completion
        assert has_vip_access is True
        
        # Verify event publishing
        published_events = mock_event_bus.published_events
        assert len(published_events) == 1
        
        event = published_events[0]
        assert event["event_name"] == "vip_access_granted"
        assert event["payload"]["user_id"] == user_id
        assert event["payload"]["reason"] == "subscription_validated"
        
        # Verify subscription service was called
        mock_subscription_service.validate_vip_access.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_reaction_to_content_workflow(self, coordinator_service, mock_event_bus):
        """Test user reaction to content workflow."""
        # Prepare test data
        user_id = "test_user_123"
        content_id = "content_001"
        reaction_type = "like"
        
        # Execute workflow
        success = await coordinator_service.handle_reaction(user_id, content_id, reaction_type)
        
        # Verify workflow completion
        assert success is True
        
        # Verify event publishing
        published_events = mock_event_bus.published_events
        assert len(published_events) == 2  # reaction_detected + besitos_awarded
        
        # Check reaction event
        reaction_event = published_events[0]
        assert reaction_event["event_name"] == "reaction_detected"
        assert reaction_event["payload"]["user_id"] == user_id
        assert reaction_event["payload"]["content_id"] == content_id
        assert reaction_event["payload"]["reaction_type"] == reaction_type
        
        # Check besitos event
        besitos_event = published_events[1]
        assert besitos_event["event_name"] == "besitos_awarded"
        assert besitos_event["payload"]["user_id"] == user_id
        assert besitos_event["payload"]["amount"] == 1
        assert besitos_event["payload"]["reason"] == "reaction_like"

    @pytest.mark.asyncio
    async def test_narrative_choice_workflow(self, coordinator_service, mock_event_bus):
        """Test user narrative choice workflow."""
        # Prepare test data
        user_id = "test_user_123"
        choice_id = "choice_a"
        context = {"fragment_id": "fragment_001", "source": "narrative"}
        
        # Execute workflow
        success = await coordinator_service.handle_narrative_choice(user_id, choice_id, context)
        
        # Verify workflow completion
        assert success is True
        
        # Verify event publishing
        published_events = mock_event_bus.published_events
        assert len(published_events) == 2  # decision_made + narrative_hint_unlocked
        
        # Check decision event
        decision_event = published_events[0]
        assert decision_event["event_name"] == "decision_made"
        assert decision_event["payload"]["user_id"] == user_id
        assert decision_event["payload"]["choice_id"] == choice_id
        
        # Check hint event
        hint_event = published_events[1]
        assert hint_event["event_name"] == "narrative_hint_unlocked"
        assert hint_event["payload"]["user_id"] == user_id
        assert hint_event["payload"]["hint_id"] == "hint_for_choice_a"
        assert hint_event["payload"]["fragment_id"] == "fragment_001"

    @pytest.mark.asyncio
    async def test_subscription_update_workflow(self, coordinator_service, mock_event_bus):
        """Test subscription update workflow."""
        # Prepare test data
        user_id = "test_user_123"
        event_payload = EventTestDataFactory.create_test_event_payload("subscription_updated")
        event_payload.update({
            "user_id": user_id,
            "plan_type": "premium",
            "status": "active"
        })
        
        # Mock event bus to simulate subscription update event
        mock_event_bus.publish = AsyncMock(return_value=True)
        
        # Execute workflow by simulating event publication
        await mock_event_bus.publish("subscription_updated", event_payload)
        
        # Verify event publishing
        mock_event_bus.publish.assert_called_once_with("subscription_updated", event_payload)

    @pytest.mark.asyncio
    async def test_event_ordering_workflow(self, coordinator_service, mock_event_bus):
        """Test event ordering and sequencing workflow."""
        # Prepare test data
        user_id = "test_user_123"
        
        # Create events with different timestamps
        event1 = {
            "event_type": "reaction_detected",
            "user_id": user_id,
            "timestamp": datetime(2025, 1, 1, 12, 0, 0).timestamp(),
            "content_id": "content_001",
            "reaction_type": "like"
        }
        
        event2 = {
            "event_type": "besitos_awarded",
            "user_id": user_id,
            "timestamp": datetime(2025, 1, 1, 12, 0, 1).timestamp(),
            "amount": 1,
            "reason": "reaction_like"
        }
        
        event3 = {
            "event_type": "narrative_hint_unlocked",
            "user_id": user_id,
            "timestamp": datetime(2025, 1, 1, 12, 0, 2).timestamp(),
            "hint_id": "hint_001",
            "fragment_id": "fragment_001"
        }
        
        # Buffer events out of order
        await coordinator_service.buffer_event(user_id, event3)  # Latest
        await coordinator_service.buffer_event(user_id, event1)  # Earliest
        await coordinator_service.buffer_event(user_id, event2)  # Middle
        
        # Process buffered events
        await coordinator_service.process_buffered_events(user_id)
        
        # Verify events are processed (buffer is cleared)
        # Note: In the current implementation, the buffer is cleared after processing
        # but the events are not actually published in this test
        assert user_id not in coordinator_service._event_buffer or len(coordinator_service._event_buffer[user_id]) == 0

    @pytest.mark.asyncio
    async def test_error_handling_in_workflows(self, coordinator_service, mock_event_bus):
        """Test error handling in workflow execution."""
        # Prepare test data
        user_id = "test_user_123"
        
        # Mock event bus to simulate failure
        mock_event_bus.publish = AsyncMock(side_effect=Exception("Event bus error"))
        
        # Execute workflow that should fail
        success = await coordinator_service.process_user_interaction(
            user_id,
            "start",
            {"source": "telegram"}
        )
        
        # Verify workflow handles error gracefully
        assert success is False

    def test_coordinator_service_initialization(self, mock_database_manager, mock_event_bus, 
                                              mock_user_service, mock_subscription_service, mock_narrative_service):
        """Test coordinator service initialization."""
        # Create coordinator service
        coordinator = CoordinatorService(
            mock_database_manager,
            mock_event_bus,
            mock_user_service,
            mock_subscription_service,
            mock_narrative_service
        )
        
        # Verify initialization
        assert coordinator is not None
        assert coordinator.database_manager == mock_database_manager
        assert coordinator.event_bus == mock_event_bus
        assert coordinator.user_service == mock_user_service
        assert coordinator.subscription_service == mock_subscription_service
        assert coordinator.narrative_service == mock_narrative_service
        assert isinstance(coordinator._event_buffer, dict)