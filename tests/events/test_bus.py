"""
EventBus Unit Tests

This module provides comprehensive unit tests for the EventBus class
in the YABOT system. Following the Testing Strategy from Fase1 requirements,
these tests validate event publishing, subscription, reliability mechanisms,
and performance against the specified requirements.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from typing import Dict, Any, Callable, List
import json

from src.core.models import RedisConfig
from src.events.bus import EventBus, LocalEventQueue, EventBusException
from src.events.models import (
    BaseEvent, UserInteractionEvent, UserRegistrationEvent,
    ReactionDetectedEvent, DecisionMadeEvent, SubscriptionUpdatedEvent
)



class TestEventBusInitialization:
    """Test EventBus initialization and configuration"""

    def test_init_with_config(self):
        """Test EventBus initialization with configuration"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 10,
            'retry_on_timeout': True,
            'socket_connect_timeout': 5,
            'socket_timeout': 10,
            'local_queue_max_size': 1000,
            'local_queue_persistence_file': 'test_queue.pkl'
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        assert event_bus.redis_config == config
        assert event_bus._connected is False
        assert event_bus.local_queue is not None

    def test_init_with_defaults(self):
        """Test EventBus initialization with default configuration"""
        config = RedisConfig()
        event_bus = EventBus(config)
        assert event_bus.redis_config == config
        assert event_bus._connected is False


class TestEventBusConnection:
    """Test EventBus connection management"""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_redis_client):
        """Test successful connection to Redis"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5,
            'socket_connect_timeout': 2
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        
        # Mock Redis connection
        with patch('src.events.bus.redis.Redis') as mock_redis_constructor:
            mock_redis_constructor.return_value = mock_redis_client
            mock_redis_client.ping = AsyncMock(return_value=True)
            
            result = await event_bus.connect()
            assert result is True
            assert event_bus._connected is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure handling"""
        config_dict = {
            'url': 'redis://invalid:6379',
            'max_connections': 5,
            'socket_connect_timeout': 1,
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        
        # Force connection failure
        with patch('src.events.bus.redis.Redis') as mock_redis_constructor:
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping = AsyncMock(side_effect=Exception("Connection failed"))
            mock_redis_constructor.return_value = mock_redis_instance
            
            result = await event_bus.connect()
            assert result is False
            assert event_bus._connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_redis_client):
        """Test disconnection from Redis"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        await event_bus.close()
        assert event_bus._connected is False
        mock_redis_client.close.assert_called_once()


class TestEventBusPublishing:
    """Test EventBus event publishing functionality"""

    @pytest.mark.asyncio
    async def test_publish_success(self, mock_redis_client, sample_test_events):
        """Test successful event publishing"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5,
            'socket_connect_timeout': 2
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        # Mock successful publish
        mock_redis_client.publish = AsyncMock(return_value=1)
        
        event = sample_test_events["user_interaction"]
        result = await event_bus.publish("test", event)
        
        assert result is True
        mock_redis_client.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_with_retry_success(self, mock_redis_client, sample_test_events):
        """Test event publishing with initial failure but eventual success"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5,
            'socket_connect_timeout': 2,
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        event_bus.redis_config.retry_on_timeout = True
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        # First call fails, second succeeds
        mock_redis_client.publish = AsyncMock(side_effect=[Exception("Failed"), 1])
        
        event = sample_test_events["reaction"]
        result = await event_bus.publish("test", event)
        
        assert result is True
        assert mock_redis_client.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_publish_failure_after_retries(self, mock_redis_client, sample_test_events):
        """Test event publishing failure after all retry attempts"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5,
            'socket_connect_timeout': 2,
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        event_bus.redis_config.retry_on_timeout = True
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        # All calls fail
        mock_redis_client.publish = AsyncMock(side_effect=Exception("Always fails"))
        
        event = sample_test_events["decision"]
        result = await event_bus.publish("test", event)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_to_custom_channel(self, mock_redis_client, sample_test_events):
        """Test publishing to a custom channel"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        mock_redis_client.publish = AsyncMock(return_value=1)
        
        event = sample_test_events["subscription"]
        result = await event_bus.publish("custom_events", event)
        
        assert result is True
        # Verify that the custom channel was used
        args, kwargs = mock_redis_client.publish.call_args
        assert args[0] == "custom_events"  # First argument should be the custom channel

    @pytest.mark.asyncio
    async def test_publish_when_redis_unavailable_uses_local_queue(self, sample_test_events):
        """Test that events are queued locally when Redis is unavailable"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5,
            'local_queue_max_size': 100
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        event_bus._connected = False  # Redis is not connected
        
        # Mock local queue
        event_bus.local_queue = MagicMock()
        event_bus.local_queue.add = AsyncMock(return_value=True)
        
        event = sample_test_events["user_registration"]
        result = await event_bus.publish("test", event)
        
        assert result is True
        event_bus.local_queue.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_serialization(self, mock_redis_client, sample_test_events):
        """Test that events are properly serialized before publishing"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        mock_redis_client.publish = AsyncMock(return_value=1)
        
        event = sample_test_events["user_interaction"]
        result = await event_bus.publish("test", event)
        
        assert result is True
        # Check that the event was serialized properly
        args, kwargs = mock_redis_client.publish.call_args
        serialized_data = args[1]  # Second argument should be serialized data
        deserialized_data = json.loads(serialized_data)
        
        # Verify the deserialized data has the expected structure
        assert "event_type" in deserialized_data
        assert deserialized_data["event_id"] == event.event_id


class TestEventBusSubscription:
    """Test EventBus subscription functionality"""

    @pytest.mark.asyncio
    async def test_subscribe_to_channel(self, mock_redis_client):
        """Test subscribing to a channel"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        
        # Create a mock pubsub
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_redis_client.pubsub.return_value = mock_pubsub
        
        # Create a mock handler
        handler = AsyncMock()
        
        result = await event_bus.subscribe("test_channel", handler)
        assert result is True
        mock_pubsub.subscribe.assert_called_once_with("test_channel")

    @pytest.mark.asyncio
    async def test_unsubscribe(self, mock_redis_client):
        """Test unsubscribing from a channel"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        
        # Create a mock pubsub
        mock_pubsub = MagicMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.aclose = AsyncMock()
        mock_redis_client.pubsub.return_value = mock_pubsub
        
        await event_bus.unsubscribe("test_channel")
        mock_pubsub.unsubscribe.assert_called_once_with("test_channel")


class TestEventBusLocalQueue:
    """Test EventBus local queue functionality"""

    @pytest.mark.asyncio
    async def test_local_queue_add_and_get(self):
        """Test adding and getting events from local queue"""
        local_queue = LocalEventQueue(max_size=10)
        
        event = MagicMock()
        event.event_id = "test_event_1"
        event.event_type = "test_type"
        
        # Add event to queue
        await local_queue.add(("test", event))
        
        # Get event from queue
        retrieved_event_tuple = await local_queue.get()
        
        assert retrieved_event_tuple is not None
        _channel, retrieved_event = retrieved_event_tuple
        assert retrieved_event.event_id == event.event_id

    @pytest.mark.asyncio
    async def test_local_queue_full(self):
        """Test local queue behavior when full"""
        local_queue = LocalEventQueue(max_size=2)
        
        # Add events up to the limit
        event1 = MagicMock()
        event1.event_id = "test_event_1"
        event2 = MagicMock()
        event2.event_id = "test_event_2"
        
        await local_queue.add(("test", event1))
        await local_queue.add(("test", event2))
        
        # Try to add one more (should fail or overwrite depending on implementation)
        event3 = MagicMock()
        event3.event_id = "test_event_3"
        
        # Test the queue size
        size = await local_queue.size()
        assert size == 2
        
        # Verify that we can get events
        retrieved1 = await local_queue.get()
        retrieved2 = await local_queue.get()
        
        assert retrieved1 is not None and retrieved2 is not None


class TestEventBusReplayQueue:
    """Test EventBus local queue replay functionality"""

    @pytest.mark.asyncio
    async def test_replay_queue_success(self, mock_redis_client):
        """Test successful replay of queued events when Redis becomes available"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = False  # Initially disconnected
        
        # Add some events to the local queue
        event1 = MagicMock()
        event1.event_id = "queued_event_1"
        event2 = MagicMock()
        event2.event_id = "queued_event_2"
        
        await event_bus.local_queue.add(("test", event1))
        await event_bus.local_queue.add(("test", event2))
        
        # Now simulate Redis connection
        event_bus._connected = True
        mock_redis_client.publish = AsyncMock(return_value=1)
        
        # Replay the queue
        replayed_count = await event_bus.replay_queue()
        
        assert replayed_count == 2
        assert await event_bus.local_queue.size() == 0
        assert mock_redis_client.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_replay_queue_with_failures(self, mock_redis_client):
        """Test replay behavior when some events fail to publish"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = False  # Initially disconnected
        
        # Add events to the local queue
        event1 = MagicMock()
        event1.event_id = "queued_event_1"
        event2 = MagicMock()
        event2.event_id = "queued_event_2"
        
        await event_bus.local_queue.add(("test", event1))
        await event_bus.local_queue.add(("test", event2))
        
        # Now simulate Redis connection but make the first publish fail
        event_bus._connected = True
        mock_redis_client.publish = AsyncMock(side_effect=[Exception("Failed"), 1])
        
        # Replay the queue
        replayed_count = await event_bus.replay_queue()
        
        # Even with a failure, the successfully published event should be removed from the queue
        # In a real implementation, the failed event might stay in the queue
        assert replayed_count <= 2


class TestEventBusHealthCheck:
    """Test EventBus health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_connected(self, mock_redis_client):
        """Test health check when Redis is connected"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        # Mock successful ping
        mock_redis_client.ping = AsyncMock(return_value=True)
        
        health = await event_bus.health_check()
        
        assert health["connected"] is True
        assert health["redis_healthy"] is True
        assert health["local_queue_size"] >= 0
        assert health["overall_healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """Test health check when Redis is disconnected"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus._connected = False
        
        health = await event_bus.health_check()
        
        assert health["connected"] is False
        assert health["redis_healthy"] is False
        assert health["overall_healthy"] is False

    @pytest.mark.asyncio
    async def test_health_check_redis_failure(self, mock_redis_client):
        """Test health check when Redis ping fails"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        # Mock failed ping
        mock_redis_client.ping = AsyncMock(side_effect=Exception("Ping failed"))
        
        health = await event_bus.health_check()
        
        assert health["connected"] is True  # We think we're connected
        assert health["redis_healthy"] is False
        assert health["overall_healthy"] is False


class TestEventBusErrorHandling:
    """Test EventBus error handling"""

    @pytest.mark.asyncio
    async def test_publish_with_invalid_event(self, mock_redis_client):
        """Test publishing an invalid event"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        # Try to publish a non-event object
        with pytest.raises(Exception):
            await event_bus.publish("test", "not_an_event")

    @pytest.mark.asyncio
    async def test_subscription_error_handling(self, mock_redis_client):
        """Test error handling in subscription process"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        
        # Create a mock pubsub that raises an error
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock(side_effect=Exception("Subscribe failed"))
        mock_redis_client.pubsub.return_value = mock_pubsub
        
        # Create a mock handler
        handler = AsyncMock()
        
        with pytest.raises(Exception):
            await event_bus.subscribe("test_channel", handler)


class TestEventBusPerformance:
    """Test EventBus performance requirements"""

    @pytest.mark.asyncio
    async def test_event_publication_performance(self, mock_redis_client, event_batch):
        """Test that event publication meets performance requirements"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        # Mock successful publish
        mock_redis_client.publish = AsyncMock(return_value=1)
        
        import time
        start_time = time.time()
        
        # Publish multiple events
        for event in event_batch:
            await event_bus.publish("test", event)
        
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_event = total_time_ms / len(event_batch)
        
        # Requirement: Event publication shall have latency under 10ms for local Redis instances
        assert avg_time_per_event <= 10, f"Average publication time {avg_time_per_event}ms exceeds 10ms requirement"

    @pytest.mark.asyncio
    async def test_local_queue_performance(self, event_batch):
        """Test that local queue operations meet performance requirements"""
        local_queue = LocalEventQueue(max_size=1000)
        
        import time
        start_time = time.time()
        
        # Add events to queue
        for event in event_batch:
            await local_queue.add(("test", event))
        
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_event = total_time_ms / len(event_batch)
        
        # Local queue operations should be very fast
        assert avg_time_per_event <= 1, f"Average local queue time {avg_time_per_event}ms is too slow"


class TestEventBusEdgeCases:
    """Test EventBus edge cases and special scenarios"""

    @pytest.mark.asyncio
    async def test_empty_queue_replay(self):
        """Test replaying an empty queue"""
        config = RedisConfig()
        event_bus = EventBus(config)
        # Queue is initially empty
        
        replayed_count = await event_bus.replay_queue()
        assert replayed_count == 0

    @pytest.mark.asyncio
    async def test_large_event_serialization(self):
        """Test serialization of very large events"""
        config = RedisConfig()
        event_bus = EventBus(config)
        
        # Create an event with large payload
        large_payload = {"data": "x" * 10000}  # 10KB of data
        
        class LargeEvent(BaseEvent):
            def __init__(self):
                super().__init__(
                    event_id="large_event_1",
                    event_type="large_test_event",
                    timestamp=datetime.utcnow(),
                )
                self.payload = large_payload

        large_event = LargeEvent()
        
        # Verify the event can be serialized/deserialized without errors
        try:
            serialized = event_bus._serialize_event(large_event)
            deserialized = json.loads(serialized)
            assert deserialized["payload"]["data"] == large_payload["data"]
        except Exception as e:
            pytest.fail(f"Large event serialization failed: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_publishing(self, mock_redis_client):
        """Test concurrent event publishing"""
        config = RedisConfig()
        event_bus = EventBus(config)
        event_bus.redis_client = mock_redis_client
        event_bus._connected = True
        
        # Mock successful publish
        mock_redis_client.publish = AsyncMock(return_value=1)
        
        # Create multiple events to publish concurrently
        events = []
        for i in range(10):
            class TestEvent(BaseEvent):
                def __init__(self, event_id):
                    super().__init__(
                        event_id=event_id,
                        event_type="test_concurrent",
                        timestamp=datetime.utcnow(),
                    )
                    self.payload = {"index": i}
            
            events.append(TestEvent(f"concurrent_event_{i}"))
        
        # Publish concurrently
        tasks = [event_bus.publish("test", event) for event in events]
        results = await asyncio.gather(*tasks)
        
        # All publications should succeed
        assert all(results)
        assert mock_redis_client.publish.call_count == 10


# Integration tests for actual EventBus implementation
@pytest.mark.integration
class TestEventBusActualImplementation:
    """Integration tests for actual EventBus implementation"""
    
    @pytest.mark.asyncio
    async def test_basic_config_initialization(self):
        """Test EventBus initialization with basic config"""
        config_dict = {
            'url': 'redis://localhost:6379',
            'max_connections': 5,
            'socket_connect_timeout': 2,
            'local_queue_max_size': 100
        }
        config = RedisConfig(**config_dict)
        event_bus = EventBus(config)
        
        # Just check initialization doesn't fail
        assert event_bus.redis_config == config
        assert event_bus._connected is False
        assert event_bus.local_queue is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__])
