"""
Test for the events module structure.
"""

import sys
import os

# Add the src directory to the path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.events import (
    EVENT_TYPES,
    EVENT_BUS_CONFIG,
    EventBusError,
    EventPublishError,
    EventSubscribeError,
    get_event_logger
)


def test_events_module_structure():
    """Test that the events module structure is correctly defined."""
    # Test that EVENT_TYPES is defined and has the expected values
    assert isinstance(EVENT_TYPES, list)
    assert "user_registered" in EVENT_TYPES
    assert "reaction_detected" in EVENT_TYPES
    assert "decision_made" in EVENT_TYPES
    assert "subscription_updated" in EVENT_TYPES
    
    # Test that EVENT_BUS_CONFIG is defined and has the expected structure
    assert isinstance(EVENT_BUS_CONFIG, dict)
    assert "max_retries" in EVENT_BUS_CONFIG
    assert "retry_delay" in EVENT_BUS_CONFIG
    assert "queue_max_size" in EVENT_BUS_CONFIG
    
    # Test that exception classes are defined
    assert issubclass(EventBusError, Exception)
    assert issubclass(EventPublishError, EventBusError)
    assert issubclass(EventSubscribeError, EventBusError)
    
    # Test that get_event_logger function exists and returns a logger
    logger = get_event_logger()
    assert logger is not None
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'debug')


def test_event_constants():
    """Test event constants."""
    # Check that we have the expected event types
    expected_events = [
        "user_registered",
        "user_interaction",
        "reaction_detected",
        "decision_made",
        "subscription_updated",
        "besitos_awarded",
        "narrative_hint_unlocked",
        "vip_access_granted",
        "user_deleted",
        "update_received"
    ]
    
    for event in expected_events:
        assert event in EVENT_TYPES, f"Expected event type {event} not found"


def test_event_bus_config():
    """Test event bus configuration."""
    # Check that we have the expected configuration keys
    expected_config_keys = [
        "max_retries",
        "retry_delay",
        "queue_max_size",
        "batch_size",
        "flush_interval"
    ]
    
    for key in expected_config_keys:
        assert key in EVENT_BUS_CONFIG, f"Expected config key {key} not found"


if __name__ == "__main__":
    test_events_module_structure()
    test_event_constants()
    test_event_bus_config()
    print("All tests passed!")