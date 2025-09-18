"""
Unit tests for the event processor implementation.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.events.processor import EventProcessor, EventProcessorError, EventProcessingError
from src.events.bus import EventBus
from src.events.models import BaseEvent, create_event
from src.config.manager import ConfigManager


class TestEventProcessor:
    """Test cases for EventProcessor class."""

    def test_init(self):
        """Test EventProcessor initialization."""
        # Test with default config manager
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        assert event_processor.event_bus == mock_event_bus
        assert event_processor.config_manager is not None
        assert event_processor._handlers == {}
        assert event_processor._is_processing is False
        assert event_processor._dead_letter_queue == []

        # Test with custom config manager
        mock_event_bus = Mock(spec=EventBus)
        mock_config = Mock(spec=ConfigManager)
        event_processor = EventProcessor(mock_event_bus, mock_config)
        assert event_processor.config_manager == mock_config

    @pytest.mark.asyncio
    async def test_start_processing(self):
        """Test starting event processing."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Mock the register default handlers method
        with patch.object(EventProcessor, '_register_default_handlers') as mock_register:
            mock_register.return_value = None
            
            result = await event_processor.start_processing()
            assert result is True
            assert event_processor.is_processing is True
            mock_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_processing(self):
        """Test stopping event processing."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Start processing first
        with patch.object(EventProcessor, '_register_default_handlers'):
            await event_processor.start_processing()
            assert event_processor.is_processing is True
            
            # Stop processing
            result = await event_processor.stop_processing()
            assert result is True
            assert event_processor.is_processing is False

    @pytest.mark.asyncio
    async def test_stop_processing_with_task(self):
        """Test stopping event processing with running task."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Start processing first
        with patch.object(EventProcessor, '_register_default_handlers'):
            await event_processor.start_processing()
            assert event_processor.is_processing is True
            
            # Create a mock processing task
            mock_task = AsyncMock()
            mock_task.done.return_value = False
            mock_task.cancel = Mock()
            event_processor._processing_task = mock_task
            
            # Stop processing
            result = await event_processor.stop_processing()
            assert result is True
            assert event_processor.is_processing is False
            mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_handler(self):
        """Test registering event handlers."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        async def test_handler(event):
            pass
        
        result = await event_processor.register_handler("test_event", test_handler)
        assert result is True
        assert "test_event" in event_processor._handlers
        assert test_handler in event_processor._handlers["test_event"]

    @pytest.mark.asyncio
    async def test_register_handler_exception(self):
        """Test registering event handlers with exception."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Mock an exception during handler registration
        with patch.object(event_processor._handlers, '__setitem__', side_effect=Exception("Test error")):
            async def test_handler(event):
                pass
            
            result = await event_processor.register_handler("test_event", test_handler)
            assert result is False

    @pytest.mark.asyncio
    async def test_handle_subscription_updated(self):
        """Test handling subscription updated events."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        # Mock the process subscription update method
        with patch.object(EventProcessor, '_process_subscription_update') as mock_process:
            mock_process.return_value = None
            
            await event_processor._handle_subscription_updated(event)
            mock_process.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_user_registered(self):
        """Test handling user registered events."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "user_registered",
            user_id="12345",
            telegram_user_id=12345,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # Mock the process user registration method
        with patch.object(EventProcessor, '_process_user_registration') as mock_process:
            mock_process.return_value = None
            
            await event_processor._handle_user_registered(event)
            mock_process.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_user_deleted(self):
        """Test handling user deleted events."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "user_deleted",
            user_id="12345",
            deletion_reason="user_request"
        )
        
        # Mock the process user deletion method
        with patch.object(EventProcessor, '_process_user_deletion') as mock_process:
            mock_process.return_value = None
            
            await event_processor._handle_user_deleted(event)
            mock_process.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_besitos_awarded(self):
        """Test handling besitos awarded events."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "besitos_awarded",
            user_id="12345",
            amount=10,
            reason="reaction_reward"
        )
        
        # Mock the process besitos award method
        with patch.object(EventProcessor, '_process_besitos_award') as mock_process:
            mock_process.return_value = None
            
            await event_processor._handle_besitos_awarded(event)
            mock_process.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_vip_access_granted(self):
        """Test handling VIP access granted events."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "vip_access_granted",
            user_id="12345",
            reason="subscription_upgrade"
        )
        
        # Mock the process VIP access grant method
        with patch.object(EventProcessor, '_process_vip_access_grant') as mock_process:
            mock_process.return_value = None
            
            await event_processor._handle_vip_access_granted(event)
            mock_process.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_process_subscription_update(self):
        """Test processing subscription update."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        # This should not raise an exception
        await event_processor._process_subscription_update(event)

    @pytest.mark.asyncio
    async def test_process_user_registration(self):
        """Test processing user registration."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "user_registered",
            user_id="12345",
            telegram_user_id=12345,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # This should not raise an exception
        await event_processor._process_user_registration(event)

    @pytest.mark.asyncio
    async def test_process_user_deletion(self):
        """Test processing user deletion."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "user_deleted",
            user_id="12345",
            deletion_reason="user_request"
        )
        
        # This should not raise an exception
        await event_processor._process_user_deletion(event)

    @pytest.mark.asyncio
    async def test_process_besitos_award(self):
        """Test processing besitos award."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "besitos_awarded",
            user_id="12345",
            amount=10,
            reason="reaction_reward"
        )
        
        # This should not raise an exception
        await event_processor._process_besitos_award(event)

    @pytest.mark.asyncio
    async def test_process_vip_access_grant(self):
        """Test processing VIP access grant."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "vip_access_granted",
            user_id="12345",
            reason="subscription_upgrade"
        )
        
        # This should not raise an exception
        await event_processor._process_vip_access_grant(event)

    @pytest.mark.asyncio
    async def test_add_to_dead_letter_queue(self):
        """Test adding events to dead letter queue."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        # Test adding to queue
        await event_processor._add_to_dead_letter_queue(event, Exception("Test error"))
        assert len(event_processor._dead_letter_queue) == 1
        assert event_processor._dead_letter_queue[0]["event"]["event_id"] == event.event_id
        assert event_processor._dead_letter_queue[0]["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_add_to_dead_letter_queue_full(self):
        """Test adding events to full dead letter queue."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        event_processor._max_dead_letter_queue_size = 2
        
        # Fill the queue
        for i in range(3):
            event = create_event(
                f"test_event_{i}",
                user_id="12345"
            )
            event_processor._dead_letter_queue.append({
                "event": event.dict(),
                "error": f"Test error {i}",
                "timestamp": event.timestamp,
                "retry_count": 0
            })
        
        # Test adding to full queue
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        await event_processor._add_to_dead_letter_queue(event, Exception("Test error"))
        assert len(event_processor._dead_letter_queue) == 2  # Should still be at max size
        # The oldest event should have been removed
        assert event_processor._dead_letter_queue[0]["event"]["event_type"] == "test_event_1"
        assert event_processor._dead_letter_queue[1]["event"]["event_type"] == "subscription_updated"

    @pytest.mark.asyncio
    async def test_handle_processing_failure(self):
        """Test handling processing failure."""
        mock_event_bus = Mock(spec=EventBus)
        mock_event_bus.publish = AsyncMock()
        mock_event_bus.is_connected = True
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        # Mock the add to dead letter queue method
        with patch.object(EventProcessor, '_add_to_dead_letter_queue') as mock_add_dlq:
            mock_add_dlq.return_value = None
            
            await event_processor._handle_processing_failure(event, Exception("Test error"))
            mock_add_dlq.assert_called_once_with(event, Exception("Test error"))
            mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_processing_failure_publish_exception(self):
        """Test handling processing failure with publish exception."""
        mock_event_bus = Mock(spec=EventBus)
        mock_event_bus.publish = AsyncMock(side_effect=Exception("Publish error"))
        mock_event_bus.is_connected = True
        event_processor = EventProcessor(mock_event_bus)
        
        # Create a test event
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        # Mock the add to dead letter queue method
        with patch.object(EventProcessor, '_add_to_dead_letter_queue') as mock_add_dlq:
            mock_add_dlq.return_value = None
            
            await event_processor._handle_processing_failure(event, Exception("Test error"))
            mock_add_dlq.assert_called_once_with(event, Exception("Test error"))
            mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        mock_event_bus = Mock(spec=EventBus)
        mock_event_bus.is_connected = True
        event_processor = EventProcessor(mock_event_bus)
        
        # Start processing
        with patch.object(EventProcessor, '_register_default_handlers'):
            await event_processor.start_processing()
        
        # Test health check
        health = await event_processor.health_check()
        assert isinstance(health, dict)
        assert "is_processing" in health
        assert "handler_count" in health
        assert "dead_letter_queue_size" in health
        assert "event_bus_connected" in health
        assert health["is_processing"] is True
        assert health["event_bus_connected"] is True

    @pytest.mark.asyncio
    async def test_is_processing_property(self):
        """Test the is_processing property."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        assert event_processor.is_processing is False
        
        # Start processing
        with patch.object(EventProcessor, '_register_default_handlers'):
            await event_processor.start_processing()
            assert event_processor.is_processing is True

    @pytest.mark.asyncio
    async def test_retry_dead_letter_queue_empty(self):
        """Test retrying dead letter queue when empty."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Test retrying empty queue
        await event_processor.retry_dead_letter_queue()
        assert len(event_processor._dead_letter_queue) == 0

    @pytest.mark.asyncio
    async def test_retry_dead_letter_queue(self):
        """Test retrying dead letter queue."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Add an event to the dead letter queue
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        event_processor._dead_letter_queue.append({
            "event": event.dict(),
            "error": "Test error",
            "timestamp": event.timestamp,
            "retry_count": 0
        })
        
        # Mock the handlers
        async def test_handler(event):
            pass
        
        event_processor._handlers["subscription_updated"] = [test_handler]
        
        # Test retrying queue
        await event_processor.retry_dead_letter_queue()
        # The event should have been removed from the queue
        assert len(event_processor._dead_letter_queue) == 0

    @pytest.mark.asyncio
    async def test_retry_dead_letter_queue_max_retries(self):
        """Test retrying dead letter queue with max retries exceeded."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Add an event to the dead letter queue with max retries exceeded
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        event_processor._dead_letter_queue.append({
            "event": event.dict(),
            "error": "Test error",
            "timestamp": event.timestamp,
            "retry_count": 3  # Max retries exceeded
        })
        
        # Test retrying queue
        await event_processor.retry_dead_letter_queue()
        # The event should still be in the queue with incremented retry count
        assert len(event_processor._dead_letter_queue) == 1
        assert event_processor._dead_letter_queue[0]["retry_count"] == 4

    @pytest.mark.asyncio
    async def test_retry_dead_letter_queue_no_handler(self):
        """Test retrying dead letter queue with no handler."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Add an event to the dead letter queue
        event = create_event(
            "unknown_event_type",
            user_id="12345"
        )
        
        event_processor._dead_letter_queue.append({
            "event": event.dict(),
            "error": "Test error",
            "timestamp": event.timestamp,
            "retry_count": 0
        })
        
        # Test retrying queue
        await event_processor.retry_dead_letter_queue()
        # The event should still be in the queue
        assert len(event_processor._dead_letter_queue) == 1

    @pytest.mark.asyncio
    async def test_retry_dead_letter_queue_handler_exception(self):
        """Test retrying dead letter queue with handler exception."""
        mock_event_bus = Mock(spec=EventBus)
        event_processor = EventProcessor(mock_event_bus)
        
        # Add an event to the dead letter queue
        event = create_event(
            "subscription_updated",
            user_id="12345",
            plan_type="premium",
            status="active",
            start_date="2025-01-15T00:00:00Z"
        )
        
        event_processor._dead_letter_queue.append({
            "event": event.dict(),
            "error": "Test error",
            "timestamp": event.timestamp,
            "retry_count": 0
        })
        
        # Mock the handlers to raise an exception
        async def test_handler(event):
            raise Exception("Handler error")
        
        event_processor._handlers["subscription_updated"] = [test_handler]
        
        # Test retrying queue
        await event_processor.retry_dead_letter_queue()
        # The event should still be in the queue with incremented retry count
        assert len(event_processor._dead_letter_queue) == 1
        assert event_processor._dead_letter_queue[0]["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_create_event_processor(self):
        """Test the create_event_processor convenience function."""
        mock_event_bus = Mock(spec=EventBus)
        
        # Mock the EventProcessor constructor and start_processing method
        with patch('src.events.processor.EventProcessor') as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.start_processing = AsyncMock(return_value=None)
            mock_processor_class.return_value = mock_processor
            
            from src.events.processor import create_event_processor
            result = await create_event_processor(mock_event_bus)
            
            assert result == mock_processor
            mock_processor.start_processing.assert_called_once()