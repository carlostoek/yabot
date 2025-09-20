"""
Tests for the event bus test utilities.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from tests.utils.events import (
    MockEventBus, 
    EventTestConfig, 
    EventTestDataFactory, 
    EventTestHelpers,
    EventTestContext
)
from src.events.bus import EventBus
from src.events.models import BaseEvent
from src.config.manager import ConfigManager


class TestMockEventBus:
    """Test cases for the MockEventBus class."""
    
    def test_init(self):
        """Test MockEventBus initialization."""
        mock_event_bus = MockEventBus()
        assert mock_event_bus.is_connected is False
        assert len(mock_event_bus.published_events) == 0
        assert len(mock_event_bus.method_calls) == 0
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connect method."""
        mock_event_bus = MockEventBus()
        result = await mock_event_bus.connect()
        assert result is True
        assert mock_event_bus.is_connected is True
        assert "connect" in mock_event_bus.method_calls
    
    @pytest.mark.asyncio
    async def test_publish(self):
        """Test publish method."""
        mock_event_bus = MockEventBus()
        mock_event_bus._is_connected = True
        
        payload = {"test": "data"}
        result = await mock_event_bus.publish("test_event", payload)
        
        assert result is True
        assert len(mock_event_bus.published_events) == 1
        assert mock_event_bus.published_events[0]["event_name"] == "test_event"
        assert mock_event_bus.published_events[0]["payload"] == payload
        assert ("publish", "test_event") in mock_event_bus.method_calls
    
    @pytest.mark.asyncio
    async def test_publish_failure(self):
        """Test publish method with failure."""
        mock_event_bus = MockEventBus()
        mock_event_bus.set_publish_failure(True)
        
        with pytest.raises(Exception) as exc_info:
            await mock_event_bus.publish("test_event", {"test": "data"})
        
        assert "Mock publish failure" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_subscribe(self):
        """Test subscribe method."""
        mock_event_bus = MockEventBus()
        mock_event_bus._is_connected = True
        
        handler = AsyncMock()
        result = await mock_event_bus.subscribe("test_event", handler)
        
        assert result is True
        assert "test_event" in mock_event_bus._subscribers
        assert handler in mock_event_bus._subscribers["test_event"]
        assert ("subscribe", "test_event") in mock_event_bus.method_calls
    
    @pytest.mark.asyncio
    async def test_subscribe_failure(self):
        """Test subscribe method with failure."""
        mock_event_bus = MockEventBus()
        mock_event_bus.set_subscribe_failure(True)
        
        handler = AsyncMock()
        with pytest.raises(Exception) as exc_info:
            await mock_event_bus.subscribe("test_event", handler)
        
        assert "Mock subscribe failure" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health_check method."""
        mock_event_bus = MockEventBus()
        result = await mock_event_bus.health_check()
        
        assert isinstance(result, dict)
        assert "connected" in result
        assert "local_queue_size" in result
        assert "subscribers_count" in result
        assert "health_check" in mock_event_bus.method_calls
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        mock_event_bus = MockEventBus()
        mock_event_bus._is_connected = True
        
        await mock_event_bus.close()
        assert mock_event_bus.is_connected is False
        assert "close" in mock_event_bus.method_calls
    
    def test_reset(self):
        """Test reset method."""
        mock_event_bus = MockEventBus()
        mock_event_bus._is_connected = True
        
        # Add some data
        mock_event_bus._published_events.append({"test": "event"})
        mock_event_bus._method_calls.append("test_call")
        mock_event_bus._should_fail_publish = True
        
        # Reset
        mock_event_bus.reset()
        
        assert len(mock_event_bus.published_events) == 0
        assert len(mock_event_bus.method_calls) == 0
        assert mock_event_bus._should_fail_publish is False


class TestEventTestConfig:
    """Test cases for the EventTestConfig class."""
    
    def test_create_test_config_manager(self):
        """Test create_test_config_manager method."""
        import os
        
        # Store original values if they exist
        original_redis_url = os.environ.get("REDIS_URL")
        original_redis_password = os.environ.get("REDIS_PASSWORD")
        
        config_manager = EventTestConfig.create_test_config_manager()
        
        # Verify it's a mock with the expected method
        redis_config = config_manager.get_redis_config()
        assert redis_config.redis_url == "redis://localhost:6379"
        assert redis_config.redis_password is None
        
        # Restore original values
        if original_redis_url:
            os.environ["REDIS_URL"] = original_redis_url
        elif "REDIS_URL" in os.environ:
            del os.environ["REDIS_URL"]
            
        if original_redis_password:
            os.environ["REDIS_PASSWORD"] = original_redis_password
        elif "REDIS_PASSWORD" in os.environ:
            del os.environ["REDIS_PASSWORD"]
    
    def test_set_test_env_vars(self):
        """Test set_test_env_vars method."""
        import os
        
        # Store original values if they exist
        original_redis_url = os.environ.get("REDIS_URL")
        original_redis_password = os.environ.get("REDIS_PASSWORD")
        
        # Set test values
        original_vars = EventTestConfig.set_test_env_vars(
            redis_url="test_redis_url",
            redis_password="test_password"
        )
        
        # Verify environment variables are set
        assert os.environ["REDIS_URL"] == "test_redis_url"
        assert os.environ["REDIS_PASSWORD"] == "test_password"
        
        # Restore original values
        EventTestConfig.restore_env_vars(original_vars)
        
        # Verify they're restored
        if original_redis_url:
            assert os.environ["REDIS_URL"] == original_redis_url
        elif "REDIS_URL" in os.environ:
            del os.environ["REDIS_URL"]
            
        if original_redis_password:
            assert os.environ["REDIS_PASSWORD"] == original_redis_password
        elif "REDIS_PASSWORD" in os.environ:
            del os.environ["REDIS_PASSWORD"]


class TestEventTestDataFactory:
    """Test cases for the EventTestDataFactory class."""
    
    def test_create_base_event(self):
        """Test create_base_event method."""
        # Test with a supported event type that has required fields
        event = EventTestDataFactory.create_user_interaction_event(
            user_id="test_user",
            action="start"
        )
        
        assert isinstance(event, BaseEvent)
        assert event.event_type == "user_interaction"
        assert event.user_id == "test_user"
        assert event.action == "start"
    
    def test_create_user_interaction_event(self):
        """Test create_user_interaction_event method."""
        event = EventTestDataFactory.create_user_interaction_event(
            user_id="test_user",
            action="start"
        )
        
        assert event.event_type == "user_interaction"
        assert event.user_id == "test_user"
        assert event.action == "start"
    
    def test_create_reaction_detected_event(self):
        """Test create_reaction_detected_event method."""
        event = EventTestDataFactory.create_reaction_detected_event(
            user_id="test_user",
            content_id="content_001",
            reaction_type="like"
        )
        
        assert event.event_type == "reaction_detected"
        assert event.user_id == "test_user"
        assert event.content_id == "content_001"
        assert event.reaction_type == "like"
    
    def test_create_decision_made_event(self):
        """Test create_decision_made_event method."""
        event = EventTestDataFactory.create_decision_made_event(
            user_id="test_user",
            choice_id="choice_a"
        )
        
        assert event.event_type == "decision_made"
        assert event.user_id == "test_user"
        assert event.choice_id == "choice_a"
    
    def test_create_subscription_updated_event(self):
        """Test create_subscription_updated_event method."""
        event = EventTestDataFactory.create_subscription_updated_event(
            user_id="test_user",
            plan_type="premium",
            status="active"
        )
        
        assert event.event_type == "subscription_updated"
        assert event.user_id == "test_user"
        assert event.plan_type == "premium"
        assert event.status == "active"
    
    def test_create_test_event_payload(self):
        """Test create_test_event_payload method."""
        payload = EventTestDataFactory.create_test_event_payload("test_event")
        
        assert isinstance(payload, dict)
        assert "event_id" in payload
        assert "event_type" in payload
        assert "timestamp" in payload
        assert "correlation_id" in payload
        assert "user_id" in payload
        assert "payload" in payload
        assert payload["event_type"] == "test_event"


class TestEventTestHelpers:
    """Test cases for the EventTestHelpers class."""
    
    def test_create_async_mock_handler(self):
        """Test create_async_mock_handler method."""
        handler = EventTestHelpers.create_async_mock_handler()
        assert callable(handler)
    
    def test_capture_event_payloads(self):
        """Test capture_event_payloads method."""
        mock_event_bus = MockEventBus()
        mock_event_bus._published_events = [
            {"event_name": "test1", "payload": {"data": "value1"}},
            {"event_name": "test2", "payload": {"data": "value2"}}
        ]
        
        payloads = EventTestHelpers.capture_event_payloads(mock_event_bus)
        assert len(payloads) == 2
        assert payloads[0]["data"] == "value1"
        assert payloads[1]["data"] == "value2"


class TestEventTestContext:
    """Test cases for the EventTestContext class."""
    
    def test_context_manager(self):
        """Test EventTestContext as a context manager."""
        import os
        
        # Store original values if they exist
        original_redis_url = os.environ.get("REDIS_URL")
        original_redis_password = os.environ.get("REDIS_PASSWORD")
        
        # Test the context manager
        with EventTestContext():
            # Verify environment variables are set
            assert os.environ["REDIS_URL"] == "redis://localhost:6379"
        
        # Verify environment variables are restored
        if original_redis_url:
            assert os.environ["REDIS_URL"] == original_redis_url
        else:
            assert "REDIS_URL" not in os.environ
            
        if original_redis_password:
            assert os.environ["REDIS_PASSWORD"] == original_redis_password
        else:
            assert "REDIS_PASSWORD" not in os.environ


# Test the pytest fixtures
def test_mock_event_bus_fixture(mock_event_bus):
    """Test the mock_event_bus fixture."""
    assert isinstance(mock_event_bus, MockEventBus)


def test_event_test_config_fixture(event_test_config):
    """Test the event_test_config fixture."""
    assert isinstance(event_test_config, type(EventTestConfig))


def test_event_test_data_factory_fixture(event_test_data_factory):
    """Test the event_test_data_factory fixture."""
    assert isinstance(event_test_data_factory, EventTestDataFactory)


def test_event_test_helpers_fixture(event_test_helpers):
    """Test the event_test_helpers fixture."""
    assert isinstance(event_test_helpers, EventTestHelpers)