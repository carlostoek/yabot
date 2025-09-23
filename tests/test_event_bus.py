"""
Test for the event bus implementation.
"""

import asyncio
import json
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from src.events.bus import EventBus, EventPublishError, EventSubscribeError
from src.config.manager import ConfigManager


def test_event_bus_initialization():
    """Test EventBus initialization."""
    # Test with default config manager
    event_bus = EventBus()
    assert hasattr(event_bus, '_redis_client')
    assert hasattr(event_bus, '_is_connected')
    assert hasattr(event_bus, '_local_queue')
    assert hasattr(event_bus, '_subscribers')
    
    # Test with custom config manager
    mock_config = Mock(spec=ConfigManager)
    event_bus = EventBus(config_manager=mock_config)
    assert event_bus.config_manager == mock_config


async def test_event_bus_connect_success():
    """Test successful EventBus connection."""
    with patch('src.events.bus.ConfigManager') as mock_config_class:
        mock_config = Mock()
        mock_config.get_redis_config.return_value = Mock(
            redis_url="redis://localhost:6379",
            redis_password=None
        )
        mock_config_class.return_value = mock_config
        
        with patch('src.events.bus.aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_client
            
            event_bus = EventBus()
            result = await event_bus.connect()
            
            assert result is True
            assert event_bus.is_connected is True
            mock_redis_client.ping.assert_called_once()


async def test_event_bus_connect_failure():
    """Test EventBus connection failure."""
    with patch('src.events.bus.ConfigManager') as mock_config_class:
        mock_config = Mock()
        mock_config.get_redis_config.return_value = Mock(
            redis_url="redis://localhost:6379",
            redis_password=None
        )
        mock_config_class.return_value = mock_config
        
        with patch('src.events.bus.aioredis.from_url') as mock_redis:
            mock_redis.side_effect = Exception("Connection failed")
            
            event_bus = EventBus()
            result = await event_bus.connect()
            
            assert result is False
            assert event_bus.is_connected is False


async def test_publish_success():
    """Test successful event publishing."""
    with patch('src.events.bus.ConfigManager') as mock_config_class:
        mock_config = Mock()
        mock_config.get_redis_config.return_value = Mock(
            redis_url="redis://localhost:6379",
            redis_password=None
        )
        mock_config_class.return_value = mock_config
        
        with patch('src.events.bus.aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis_client.publish = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_client
            
            event_bus = EventBus()
            await event_bus.connect()
            
            # Test publishing an event
            payload = {"user_id": "12345", "action": "test"}
            result = await event_bus.publish("test_event", payload)
            
            assert result is True
            mock_redis_client.publish.assert_called_once()


async def test_publish_redis_failure_queue_locally():
    """Test publishing with Redis failure that queues locally."""
    with patch('src.events.bus.ConfigManager') as mock_config_class:
        mock_config = Mock()
        mock_config.get_redis_config.return_value = Mock(
            redis_url="redis://localhost:6379",
            redis_password=None
        )
        mock_config_class.return_value = mock_config
        
        with patch('src.events.bus.aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis_client.publish = AsyncMock(side_effect=Exception("Redis error"))
            mock_redis.return_value = mock_redis_client
            
            # Mock the persistence methods
            with patch.object(EventBus, '_persist_events') as mock_persist:
                event_bus = EventBus()
                await event_bus.connect()
                
                # Test publishing an event
                payload = {"user_id": "12345", "action": "test"}
                result = await event_bus.publish("test_event", payload)
                
                assert result is True  # Should still succeed as it's queued locally
                assert len(event_bus._local_queue) == 1
                mock_persist.assert_called_once()


async def test_subscribe():
    """Test event subscription."""
    event_bus = EventBus()
    
    async def test_handler(payload):
        pass
    
    result = await event_bus.subscribe("test_event", test_handler)
    assert result is True
    assert "test_event" in event_bus._subscribers
    assert test_handler in event_bus._subscribers["test_event"]


async def test_health_check():
    """Test health check functionality."""
    with patch('src.events.bus.ConfigManager') as mock_config_class:
        mock_config = Mock()
        mock_config.get_redis_config.return_value = Mock(
            redis_url="redis://localhost:6379",
            redis_password=None
        )
        mock_config_class.return_value = mock_config
        
        with patch('src.events.bus.aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_client
            
            event_bus = EventBus()
            await event_bus.connect()
            
            # Test health check
            health = await event_bus.health_check()
            
            assert isinstance(health, dict)
            assert "connected" in health
            assert "local_queue_size" in health
            assert "subscribers_count" in health
            assert health["connected"] is True


async def test_close():
    """Test closing the event bus."""
    with patch('src.events.bus.ConfigManager') as mock_config_class:
        mock_config = Mock()
        mock_config.get_redis_config.return_value = Mock(
            redis_url="redis://localhost:6379",
            redis_password=None
        )
        mock_config_class.return_value = mock_config
        
        with patch('src.events.bus.aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis_client.close = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            event_bus = EventBus()
            await event_bus.connect()
            
            # Test closing
            await event_bus.close()
            
            assert event_bus.is_connected is False
            mock_redis_client.close.assert_called_once()


async def test_queue_locally():
    """Test local queue functionality."""
    event_bus = EventBus()
    
    # Mock the persistence method
    with patch.object(EventBus, '_persist_events') as mock_persist:
        payload = {"user_id": "12345", "action": "test"}
        result = await event_bus._queue_locally("test_event", payload)
        
        assert result is True
        assert len(event_bus._local_queue) == 1
        assert event_bus._local_queue[0]["event_name"] == "test_event"
        assert event_bus._local_queue[0]["payload"] == payload
        mock_persist.assert_called_once()


async def test_process_local_queue():
    """Test processing local queue."""
    with patch('src.events.bus.ConfigManager') as mock_config_class:
        mock_config = Mock()
        mock_config.get_redis_config.return_value = Mock(
            redis_url="redis://localhost:6379",
            redis_password=None
        )
        mock_config_class.return_value = mock_config
        
        with patch('src.events.bus.aioredis.from_url') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis_client.publish = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_client
            
            # Mock the persistence method
            with patch.object(EventBus, '_persist_events') as mock_persist:
                event_bus = EventBus()
                await event_bus.connect()
                
                # Add some events to the queue
                payload1 = {"user_id": "12345", "action": "test1"}
                payload2 = {"user_id": "67890", "action": "test2"}
                await event_bus._queue_locally("test_event1", payload1)
                await event_bus._queue_locally("test_event2", payload2)
                
                # Process the queue
                await event_bus._process_local_queue()
                
                # Verify events were published
                assert mock_redis_client.publish.call_count == 2
                assert len(event_bus._local_queue) == 0
                assert mock_persist.call_count == 3  # Once for queueing each event, once for processing


if __name__ == "__main__":
    # Run async tests
    async def run_tests():
        test_event_bus_initialization()
        await test_event_bus_connect_success()
        await test_event_bus_connect_failure()
        await test_publish_success()
        await test_publish_redis_failure_queue_locally()
        await test_subscribe()
        await test_health_check()
        await test_close()
        await test_queue_locally()
        await test_process_local_queue()
        print("All tests passed!")
    
    asyncio.run(run_tests())