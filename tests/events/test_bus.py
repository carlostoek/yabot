"""
Unit tests for the EventBus class.

This module provides comprehensive unit tests for the EventBus class,
implementing the testing requirements specified in fase1 specification sections 2.1 and 2.2.
"""

import asyncio
import json
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any
from redis import asyncio as aioredis

from src.events.bus import EventBus, EventBusError, EventPublishError, EventSubscribeError
from src.events.models import BaseEvent, create_event
from src.config.manager import ConfigManager
from src.core.models import RedisConfig


class TestEventBus:
    """Test cases for the EventBus class."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager for testing."""
        mock_config = Mock(spec=ConfigManager)
        
        # Create a mock Redis config
        mock_redis_config = Mock(spec=RedisConfig)
        mock_redis_config.redis_url = "redis://localhost:6379"
        mock_redis_config.redis_password = None
        
        mock_config.get_redis_config.return_value = mock_redis_config
        return mock_config
    
    @pytest.fixture
    def event_bus(self, mock_config_manager):
        """Create an EventBus instance with mocked configuration."""
        event_bus = EventBus(config_manager=mock_config_manager)
        yield event_bus
        
        # Clean up
        if hasattr(event_bus, '_flush_task') and event_bus._flush_task:
            event_bus._flush_task.cancel()
            try:
                # Note: We don't await this in a fixture because fixtures can't be async
                pass
            except asyncio.CancelledError:
                pass
    
    def test_init(self, mock_config_manager):
        """Test EventBus initialization."""
        # Test with default config manager
        event_bus = EventBus()
        assert hasattr(event_bus, '_redis_client')
        assert hasattr(event_bus, '_is_connected')
        assert hasattr(event_bus, '_local_queue')
        assert hasattr(event_bus, '_subscribers')
        assert hasattr(event_bus, '_max_queue_size')
        assert hasattr(event_bus, '_persistence_file')
        assert hasattr(event_bus, '_flush_interval')
        assert event_bus._is_connected is False
        assert event_bus._local_queue == []
        assert event_bus._subscribers == {}
        assert isinstance(event_bus.config_manager, ConfigManager)
        
        # Test with custom config manager
        event_bus = EventBus(config_manager=mock_config_manager)
        assert event_bus.config_manager == mock_config_manager
    
    @pytest.mark.asyncio
    async def test_connect_success(self, mock_config_manager):
        """Test successful connection to Redis."""
        # Create an EventBus instance
        event_bus = EventBus(config_manager=mock_config_manager)
        
        # Mock Redis configuration
        mock_redis_config = Mock()
        mock_redis_config.redis_url = "redis://localhost:6379"
        mock_redis_config.redis_password = None
        mock_config_manager.get_redis_config.return_value = mock_redis_config
        
        # Mock Redis client
        with patch('src.events.bus.aioredis.from_url') as mock_redis_client, \
             patch('src.events.bus.open', side_effect=FileNotFoundError()), \
             patch('src.events.bus.EventBus._start_flush_task') as mock_start_flush:
            
            # Mock successful Redis connection
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock(return_value=True)
            mock_redis_client.return_value = mock_redis_instance
            
            # Test connection
            result = await event_bus.connect()
            
            # Verify Redis connection
            assert mock_redis_client.called
            assert mock_redis_instance.ping.called
            
            # Verify result
            assert result is True
            assert event_bus.is_connected is True
            
            # Verify flush task was started
            assert mock_start_flush.called
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, event_bus, mock_config_manager):
        """Test failed connection to Redis."""
        # Mock Redis configuration
        mock_redis_config = Mock()
        mock_redis_config.redis_url = "redis://localhost:6379"
        mock_redis_config.redis_password = None
        mock_config_manager.get_redis_config.return_value = mock_redis_config
        
        # Mock Redis client failure
        with patch('src.events.bus.aioredis.from_url') as mock_redis_client, \
             patch('src.events.bus.EventBus._start_flush_task') as mock_start_flush:
            
            # Mock Redis connection failure
            mock_redis_client.side_effect = Exception("Connection failed")
            
            # Test connection
            result = await event_bus.connect()
            
            # Verify Redis connection was attempted
            assert mock_redis_client.called
            
            # Verify result
            assert result is False
            assert event_bus.is_connected is False
            
            # Verify flush task was still started
            assert mock_start_flush.called
    
    @pytest.mark.asyncio
    async def test_connect_with_retry(self, event_bus, mock_config_manager):
        """Test connection with retry logic."""
        # Mock Redis configuration
        mock_redis_config = Mock()
        mock_redis_config.redis_url = "redis://localhost:6379"
        mock_redis_config.redis_password = None
        mock_config_manager.get_redis_config.return_value = mock_redis_config
        
        # Mock Redis client with retry behavior
        with patch('src.events.bus.aioredis.from_url') as mock_redis_client, \
             patch('src.events.bus.asyncio.sleep') as mock_sleep, \
             patch('src.events.bus.open', side_effect=FileNotFoundError()), \
             patch('src.events.bus.EventBus._start_flush_task'):
            
            # Mock Redis connection to fail first, then succeed
            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock(return_value=True)
            
            mock_redis_client.side_effect = [
                Exception("Connection failed"),  # First attempt fails
                mock_redis_instance  # Second attempt succeeds
            ]
            
            # Mock sleep to avoid delays
            mock_sleep.return_value = None
            
            # Test connection
            result = await event_bus.connect()
            
            # Verify Redis client was called twice (retry)
            assert mock_redis_client.call_count == 2
            
            # Verify sleep was called for retry delay
            assert mock_sleep.called
            
            # Verify result
            assert result is True
            assert event_bus.is_connected is True
    
    @pytest.mark.asyncio
    async def test_publish_success_with_redis(self, mock_config_manager):
        """Test successful event publishing with Redis connection."""
        # Create an EventBus instance
        event_bus = EventBus(config_manager=mock_config_manager)
        
        # Set up mock Redis connection
        mock_redis_client = AsyncMock()
        mock_redis_client.publish = AsyncMock(return_value=True)
        event_bus._redis_client = mock_redis_client
        event_bus._is_connected = True
        
        # Test event payload
        event_payload = {
            "user_id": "test_user_123",
            "content_id": "content_001",
            "reaction_type": "like"
        }
        
        # Test publishing
        result = await event_bus.publish("reaction_detected", event_payload)
        
        # Verify Redis publish was called
        assert mock_redis_client.publish.called
        args, kwargs = mock_redis_client.publish.call_args
        assert args[0] == "reaction_detected"
        assert "user_id" in json.loads(args[1])
        assert "content_id" in json.loads(args[1])
        assert "reaction_type" in json.loads(args[1])
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_publish_success_with_local_queue(self, event_bus):
        """Test successful event publishing with local queue fallback."""
        # Ensure Redis is not connected
        event_bus._redis_client = None
        event_bus._is_connected = False
        
        # Test event payload
        event_payload = {
            "user_id": "test_user_123",
            "content_id": "content_001",
            "reaction_type": "like"
        }
        
        # Test publishing
        result = await event_bus.publish("reaction_detected", event_payload)
        
        # Verify event was queued locally
        assert len(event_bus._local_queue) == 1
        queued_event = event_bus._local_queue[0]
        assert queued_event["event_name"] == "reaction_detected"
        assert "user_id" in queued_event["payload"]
        assert "content_id" in queued_event["payload"]
        assert "reaction_type" in queued_event["payload"]
        assert "timestamp" in queued_event["payload"]
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_publish_redis_failure_fallback_to_local_queue(self, event_bus):
        """Test event publishing when Redis fails, fallback to local queue."""
        # Set up mock Redis connection that fails
        mock_redis_client = AsyncMock()
        mock_redis_client.publish = AsyncMock(side_effect=Exception("Redis error"))
        event_bus._redis_client = mock_redis_client
        event_bus._is_connected = True
        
        # Test event payload
        event_payload = {
            "user_id": "test_user_123",
            "content_id": "content_001",
            "reaction_type": "like"
        }
        
        # Test publishing
        result = await event_bus.publish("reaction_detected", event_payload)
        
        # Verify Redis publish was attempted
        assert mock_redis_client.publish.called
        
        # Verify event was queued locally as fallback
        assert len(event_bus._local_queue) == 1
        queued_event = event_bus._local_queue[0]
        assert queued_event["event_name"] == "reaction_detected"
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_publish_local_queue_full(self, event_bus):
        """Test event publishing when local queue is full."""
        # Ensure Redis is not connected
        event_bus._redis_client = None
        event_bus._is_connected = False
        
        # Fill the local queue to maximum capacity
        event_bus._max_queue_size = 3
        for i in range(3):
            event_bus._local_queue.append({
                "event_name": f"test_event_{i}",
                "payload": {"test": f"data_{i}"},
                "timestamp": 1234567890.0 + i
            })
        
        # Test event payload
        event_payload = {
            "user_id": "test_user_123",
            "content_id": "content_001",
            "reaction_type": "like"
        }
        
        # Test publishing
        result = await event_bus.publish("reaction_detected", event_payload)
        
        # Verify oldest event was dropped
        assert len(event_bus._local_queue) == 3  # Still 3, but oldest was dropped
        assert event_bus._local_queue[0]["event_name"] == "test_event_1"  # Oldest dropped
        assert event_bus._local_queue[-1]["event_name"] == "reaction_detected"  # Newest added
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_subscribe_success(self, mock_config_manager):
        """Test successful event subscription."""
        # Create an EventBus instance
        event_bus = EventBus(config_manager=mock_config_manager)
        
        # Test handler function
        mock_handler = AsyncMock()
        
        # Test subscription
        result = await event_bus.subscribe("reaction_detected", mock_handler)
        
        # Verify subscription was added
        assert "reaction_detected" in event_bus._subscribers
        assert mock_handler in event_bus._subscribers["reaction_detected"]
        
        # Verify result
        assert result is True
    
    @pytest.mark.asyncio
    async def test_subscribe_multiple_handlers(self, event_bus):
        """Test subscription with multiple handlers for the same event."""
        # Test handler functions
        mock_handler1 = AsyncMock()
        mock_handler2 = AsyncMock()
        
        # Test subscriptions
        result1 = await event_bus.subscribe("reaction_detected", mock_handler1)
        result2 = await event_bus.subscribe("reaction_detected", mock_handler2)
        
        # Verify both handlers were added
        assert "reaction_detected" in event_bus._subscribers
        assert len(event_bus._subscribers["reaction_detected"]) == 2
        assert mock_handler1 in event_bus._subscribers["reaction_detected"]
        assert mock_handler2 in event_bus._subscribers["reaction_detected"]
        
        # Verify results
        assert result1 is True
        assert result2 is True
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, event_bus):
        """Test successful health check."""
        # Set up mock Redis connection
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        event_bus._redis_client = mock_redis_client
        event_bus._is_connected = True
        
        # Add some test data
        event_bus._local_queue = [{"test": "event"}]
        event_bus._subscribers = {"reaction_detected": [AsyncMock()]}
        
        # Test health check
        result = await event_bus.health_check()
        
        # Verify result
        assert isinstance(result, dict)
        assert "connected" in result
        assert "local_queue_size" in result
        assert "subscribers_count" in result
        assert result["connected"] is True
        assert result["local_queue_size"] == 1
        assert result["subscribers_count"] == 1
        assert "redis_healthy" in result
        assert result["redis_healthy"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_redis_failure(self, event_bus):
        """Test health check when Redis is connected but unhealthy."""
        # Set up mock Redis connection that fails health check
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(side_effect=Exception("Redis error"))
        event_bus._redis_client = mock_redis_client
        event_bus._is_connected = True
        
        # Test health check
        result = await event_bus.health_check()
        
        # Verify result
        assert isinstance(result, dict)
        assert "connected" in result
        assert "local_queue_size" in result
        assert "subscribers_count" in result
        assert "redis_healthy" in result
        assert result["connected"] is True
        assert result["redis_healthy"] is False
    
    @pytest.mark.asyncio
    async def test_close_success(self, event_bus):
        """Test successful closure of event bus connections."""
        # Set up mock Redis connection
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock()
        event_bus._redis_client = mock_redis_client
        
        # Set up mock flush task
        mock_flush_task = AsyncMock()
        mock_flush_task.done.return_value = False
        event_bus._flush_task = mock_flush_task
        
        # Add some test data to queue
        event_bus._local_queue = [{"test": "event"}]
        
        # Test closure with mock file persistence
        with patch('src.events.bus.open') as mock_open, \
             patch('src.events.bus.pickle.dump') as mock_pickle_dump:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Test closure
            await event_bus.close()
            
            # Verify Redis connection was closed
            assert mock_redis_client.close.called
            
            # Verify flush task was cancelled
            assert mock_flush_task.cancel.called
            
            # Verify events were persisted
            assert mock_open.called
            assert mock_pickle_dump.called
            
            # Verify connected flag is reset
            assert event_bus._is_connected is False
    
    @pytest.mark.asyncio
    async def test_close_redis_failure(self, event_bus):
        """Test closure when Redis connection fails."""
        # Set up mock Redis connection that fails to close
        mock_redis_client = AsyncMock()
        mock_redis_client.close = AsyncMock(side_effect=Exception("Redis close error"))
        event_bus._redis_client = mock_redis_client
        
        # Set up mock flush task
        mock_flush_task = AsyncMock()
        mock_flush_task.done.return_value = False
        event_bus._flush_task = mock_flush_task
        
        # Test closure (should not raise exception even with Redis failure)
        with patch('src.events.bus.open'), patch('src.events.bus.pickle.dump'):
            await event_bus.close()
        
        # Verify Redis close was attempted
        assert mock_redis_client.close.called
        
        # Verify flush task was cancelled
        assert mock_flush_task.cancel.called
        
        # Verify connected flag is reset
        assert event_bus._is_connected is False
    
    @pytest.mark.asyncio
    async def test_process_local_queue_success(self, event_bus):
        """Test successful processing of local queue."""
        # Set up mock Redis connection
        mock_redis_client = AsyncMock()
        mock_redis_client.publish = AsyncMock(return_value=True)
        event_bus._redis_client = mock_redis_client
        event_bus._is_connected = True
        
        # Add test events to queue
        event_bus._local_queue = [
            {
                "event_name": "reaction_detected",
                "payload": {"user_id": "test_user_1", "content_id": "content_1"},
                "timestamp": 1234567890.0
            },
            {
                "event_name": "decision_made",
                "payload": {"user_id": "test_user_2", "choice_id": "choice_a"},
                "timestamp": 1234567891.0
            }
        ]
        
        # Test processing
        await event_bus._process_local_queue()
        
        # Verify Redis publish was called for both events
        assert mock_redis_client.publish.call_count == 2
        
        # Verify queue is now empty
        assert len(event_bus._local_queue) == 0
    
    @pytest.mark.asyncio
    async def test_process_local_queue_partial_failure(self, event_bus):
        """Test processing of local queue with partial failure."""
        # Set up mock Redis connection with partial failure
        mock_redis_client = AsyncMock()
        mock_redis_client.publish = AsyncMock(side_effect=[
            True,  # First event succeeds
            Exception("Redis error")  # Second event fails
        ])
        event_bus._redis_client = mock_redis_client
        event_bus._is_connected = True
        
        # Add test events to queue
        event_bus._local_queue = [
            {
                "event_name": "reaction_detected",
                "payload": {"user_id": "test_user_1", "content_id": "content_1"},
                "timestamp": 1234567890.0
            },
            {
                "event_name": "decision_made",
                "payload": {"user_id": "test_user_2", "choice_id": "choice_a"},
                "timestamp": 1234567891.0
            }
        ]
        
        # Test processing
        await event_bus._process_local_queue()
        
        # Verify Redis publish was called for both events
        assert mock_redis_client.publish.call_count == 2
        
        # Verify first event was removed from queue, second was kept
        assert len(event_bus._local_queue) == 1
        assert event_bus._local_queue[0]["event_name"] == "decision_made"
    
    @pytest.mark.asyncio
    async def test_queue_locally_persistence(self, event_bus):
        """Test local queuing with persistence."""
        # Ensure Redis is not connected
        event_bus._redis_client = None
        event_bus._is_connected = False
        
        # Test event payload
        event_payload = {
            "user_id": "test_user_123",
            "content_id": "content_001",
            "reaction_type": "like"
        }
        
        # Test queuing with mock file persistence
        with patch('src.events.bus.open') as mock_open, \
             patch('src.events.bus.pickle.dump') as mock_pickle_dump:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # Test queuing
            result = await event_bus._queue_locally("reaction_detected", event_payload)
            
            # Verify event was queued
            assert len(event_bus._local_queue) == 1
            assert event_bus._local_queue[0]["event_name"] == "reaction_detected"
            
            # Verify persistence was attempted
            assert mock_open.called
            assert mock_pickle_dump.called
            
            # Verify result
            assert result is True


# Integration tests with temporary files
class TestEventBusIntegration:
    """Integration tests for the EventBus class."""
    
    @pytest.fixture
    async def temp_event_bus(self):
        """Create an EventBus with temporary persistence file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up temporary persistence file
            persistence_file = os.path.join(temp_dir, "event_queue.pkl")
            
            # Create event bus with temporary file
            event_bus = EventBus()
            event_bus._persistence_file = persistence_file
            
            yield event_bus
            
            # Clean up
            if hasattr(event_bus, '_flush_task') and event_bus._flush_task:
                event_bus._flush_task.cancel()
                try:
                    await event_bus._flush_task
                except asyncio.CancelledError:
                    pass
    
    def test_event_bus_properties(self, temp_event_bus):
        """Test that EventBus has all required properties."""
        event_bus = temp_event_bus
        
        # Test that all required attributes exist
        assert hasattr(event_bus, '_redis_client')
        assert hasattr(event_bus, '_is_connected')
        assert hasattr(event_bus, '_local_queue')
        assert hasattr(event_bus, '_subscribers')
        assert hasattr(event_bus, '_max_queue_size')
        assert hasattr(event_bus, '_persistence_file')
        assert hasattr(event_bus, '_flush_interval')
        assert hasattr(event_bus, 'config_manager')
        
        # Test that all required methods exist
        assert hasattr(event_bus, 'connect')
        assert hasattr(event_bus, 'publish')
        assert hasattr(event_bus, 'subscribe')
        assert hasattr(event_bus, 'health_check')
        assert hasattr(event_bus, 'close')
        assert hasattr(event_bus, 'is_connected')


# Test with actual configuration
@pytest.mark.asyncio
async def test_event_bus_with_real_config():
    """Test EventBus with real configuration."""
    # Set up environment variables
    original_redis_url = os.environ.get("REDIS_URL")
    original_redis_password = os.environ.get("REDIS_PASSWORD")
    
    try:
        # Set test environment variables
        os.environ["REDIS_URL"] = "redis://localhost:6379"
        os.environ["REDIS_PASSWORD"] = ""
        
        # Create event bus with real config
        config_manager = ConfigManager()
        event_bus = EventBus(config_manager=config_manager)
        
        # Test initialization
        assert isinstance(event_bus.config_manager, ConfigManager)
        assert event_bus._is_connected is False
        
    finally:
        # Restore original environment variables
        if original_redis_url:
            os.environ["REDIS_URL"] = original_redis_url
        elif "REDIS_URL" in os.environ:
            del os.environ["REDIS_URL"]
            
        if original_redis_password:
            os.environ["REDIS_PASSWORD"] = original_redis_password
        elif "REDIS_PASSWORD" in os.environ:
            del os.environ["REDIS_PASSWORD"]


# Test convenience function
@pytest.mark.asyncio
async def test_create_event_bus():
    """Test the create_event_bus convenience function."""
    # Test with default config manager
    with patch('src.events.bus.EventBus.connect') as mock_connect:
        mock_connect.return_value = True
        
        from src.events.bus import create_event_bus
        event_bus = await create_event_bus()
        
        assert isinstance(event_bus, EventBus)
        assert mock_connect.called


# Test event models integration
def test_event_bus_with_event_models():
    """Test EventBus integration with event models."""
    # Create an event using the event models
    event = create_event(
        "user_interaction",
        user_id="test_user_123",
        action="start",
        context={"source": "test"}
    )
    
    # Verify event was created correctly
    assert isinstance(event, BaseEvent)
    assert event.event_type == "user_interaction"
    assert event.user_id == "test_user_123"
    assert event.action == "start"
    assert "context" in event.payload
    assert event.payload["context"]["source"] == "test"