"""
Unit tests for the event bus implementation.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.events.bus import EventBus, EventPublishError, EventSubscribeError
from src.config.manager import ConfigManager


class TestEventBus:
    """Test cases for EventBus class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Cancel any existing flush tasks to prevent interference between tests
        pass

    def teardown_method(self):
        """Tear down test fixtures."""
        # Clean up any running tasks
        pass

    def test_init(self):
        """Test EventBus initialization."""
        # Test with default config manager
        event_bus = EventBus()
        assert event_bus.config_manager is not None
        assert event_bus._redis_client is None
        assert event_bus._is_connected is False
        assert event_bus._local_queue == []
        assert event_bus._subscribers == {}
        assert hasattr(event_bus, '_max_queue_size')
        assert hasattr(event_bus, '_persistence_file')
        assert hasattr(event_bus, '_flush_interval')

    def test_init_with_config(self):
        """Test EventBus initialization with custom config."""
        mock_config = Mock(spec=ConfigManager)
        event_bus = EventBus(config_manager=mock_config)
        assert event_bus.config_manager == mock_config

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to Redis."""
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

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test failed connection to Redis."""
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

    @pytest.mark.asyncio
    async def test_connect_with_retry(self):
        """Test connection with retry logic."""
        with patch('src.events.bus.ConfigManager') as mock_config_class:
            mock_config = Mock()
            mock_config.get_redis_config.return_value = Mock(
                redis_url="redis://localhost:6379",
                redis_password=None
            )
            mock_config_class.return_value = mock_config
            
            with patch('src.events.bus.aioredis.from_url') as mock_redis:
                # Create a list of side effects
                side_effects = [
                    Exception("Connection failed"),
                    Exception("Connection failed"),
                    AsyncMock()
                ]
                
                # Mock the Redis client's ping method for the successful connection
                mock_redis_client = AsyncMock()
                mock_redis_client.ping = AsyncMock(return_value=True)
                side_effects[2] = mock_redis_client
                
                mock_redis.side_effect = side_effects
                
                event_bus = EventBus()
                result = await event_bus.connect()
                
                assert result is True
                assert event_bus.is_connected is True
                assert mock_redis.call_count == 3

    @pytest.mark.asyncio
    async def test_publish_success(self):
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

    @pytest.mark.asyncio
    async def test_publish_redis_failure_queue_locally(self):
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

    @pytest.mark.asyncio
    async def test_subscribe(self):
        """Test event subscription."""
        event_bus = EventBus()
        
        async def test_handler(payload):
            pass
        
        result = await event_bus.subscribe("test_event", test_handler)
        assert result is True
        assert "test_event" in event_bus._subscribers
        assert test_handler in event_bus._subscribers["test_event"]

    @pytest.mark.asyncio
    async def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers to the same event."""
        event_bus = EventBus()
        
        async def handler1(payload):
            pass
        
        async def handler2(payload):
            pass
        
        result1 = await event_bus.subscribe("test_event", handler1)
        result2 = await event_bus.subscribe("test_event", handler2)
        
        assert result1 is True
        assert result2 is True
        assert len(event_bus._subscribers["test_event"]) == 2
        assert handler1 in event_bus._subscribers["test_event"]
        assert handler2 in event_bus._subscribers["test_event"]

    @pytest.mark.asyncio
    async def test_health_check(self):
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

    @pytest.mark.asyncio
    async def test_close(self):
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

    @pytest.mark.asyncio
    async def test_queue_locally(self):
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

    @pytest.mark.asyncio
    async def test_queue_locally_full_queue(self):
        """Test local queue functionality when queue is full."""
        event_bus = EventBus()
        event_bus._max_queue_size = 2
        
        # Add events to fill the queue (this will actually add 3 events, but the queue should only keep 2)
        # because we're setting up the initial state, not testing the queueing logic yet
        for i in range(2):
            event_bus._local_queue.append({
                "event_name": f"event_{i}",
                "payload": {"data": i},
                "timestamp": i
            })
        
        # Mock the persistence method
        with patch.object(EventBus, '_persist_events') as mock_persist:
            payload = {"user_id": "12345", "action": "test"}
            result = await event_bus._queue_locally("test_event", payload)
            
            assert result is True
            assert len(event_bus._local_queue) == 2  # Should still be at max size
            # The oldest event (event_0) should have been removed, and the new event added
            assert event_bus._local_queue[0]["event_name"] == "event_1"
            assert event_bus._local_queue[1]["event_name"] == "test_event"
            mock_persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_local_queue(self):
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
                    # Called once for each queue operation and once for processing
                    assert mock_persist.call_count == 3

    def test_is_connected_property(self):
        """Test the is_connected property."""
        event_bus = EventBus()
        assert event_bus.is_connected is False
        
        event_bus._is_connected = True
        assert event_bus.is_connected is True

    @pytest.mark.asyncio
    async def test_create_event_bus(self):
        """Test the create_event_bus convenience function."""
        with patch('src.events.bus.EventBus') as mock_event_bus_class:
            mock_event_bus = AsyncMock()
            mock_event_bus.connect = AsyncMock()
            mock_event_bus_class.return_value = mock_event_bus
            
            from src.events.bus import create_event_bus
            result = await create_event_bus()
            
            assert result == mock_event_bus
            mock_event_bus.connect.assert_called_once()