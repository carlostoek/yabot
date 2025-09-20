"""
Test for the event processor implementation.
"""

import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from src.events.processor import EventProcessor, EventProcessorError, EventProcessingError
from src.events.bus import EventBus
from src.events.models import BaseEvent, create_event
from src.config.manager import ConfigManager


def test_event_processor_initialization():
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


async def test_event_processor_start_processing():
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


async def test_event_processor_stop_processing():
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


async def test_register_handler():
    """Test registering event handlers."""
    mock_event_bus = Mock(spec=EventBus)
    event_processor = EventProcessor(mock_event_bus)
    
    async def test_handler(event):
        pass
    
    result = await event_processor.register_handler("test_event", test_handler)
    assert result is True
    assert "test_event" in event_processor._handlers
    assert test_handler in event_processor._handlers["test_event"]


async def test_handle_subscription_updated():
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


async def test_handle_user_registered():
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


async def test_handle_user_deleted():
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


async def test_handle_besitos_awarded():
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


async def test_handle_vip_access_granted():
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


async def test_process_subscription_update():
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


async def test_process_user_registration():
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


async def test_process_user_deletion():
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


async def test_process_besitos_award():
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


async def test_process_vip_access_grant():
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


async def test_add_to_dead_letter_queue():
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


async def test_handle_processing_failure():
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
        mock_add_dlq.assert_called_once()
        mock_event_bus.publish.assert_called_once()


async def test_health_check():
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


async def test_create_event_processor():
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


if __name__ == "__main__":
    # Run async tests
    async def run_tests():
        test_event_processor_initialization()
        await test_event_processor_start_processing()
        await test_event_processor_stop_processing()
        await test_register_handler()
        await test_handle_subscription_updated()
        await test_handle_user_registered()
        await test_handle_user_deleted()
        await test_handle_besitos_awarded()
        await test_handle_vip_access_granted()
        await test_process_subscription_update()
        await test_process_user_registration()
        await test_process_user_deletion()
        await test_process_besitos_award()
        await test_process_vip_access_grant()
        await test_add_to_dead_letter_queue()
        await test_handle_processing_failure()
        await test_health_check()
        await test_create_event_processor()
        print("All tests passed!")
    
    asyncio.run(run_tests())