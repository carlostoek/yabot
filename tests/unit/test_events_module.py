"""
Unit tests for the events module structure.
"""

import pytest
import logging
from src.events import (
    EVENT_TYPES,
    EVENT_BUS_CONFIG,
    EventBusError,
    EventPublishError,
    EventSubscribeError,
    get_event_logger
)


class TestEventsModule:
    """Test cases for the events module structure."""

    def test_event_types_defined(self):
        """Test that EVENT_TYPES is properly defined."""
        assert isinstance(EVENT_TYPES, list)
        assert len(EVENT_TYPES) > 0
        
        # Check for some expected event types
        assert "user_registered" in EVENT_TYPES
        assert "reaction_detected" in EVENT_TYPES
        assert "decision_made" in EVENT_TYPES
        assert "subscription_updated" in EVENT_TYPES

    def test_event_bus_config_defined(self):
        """Test that EVENT_BUS_CONFIG is properly defined."""
        assert isinstance(EVENT_BUS_CONFIG, dict)
        assert len(EVENT_BUS_CONFIG) > 0
        
        # Check for expected configuration keys
        assert "max_retries" in EVENT_BUS_CONFIG
        assert "retry_delay" in EVENT_BUS_CONFIG
        assert "queue_max_size" in EVENT_BUS_CONFIG
        assert "batch_size" in EVENT_BUS_CONFIG
        assert "flush_interval" in EVENT_BUS_CONFIG

    def test_event_bus_exceptions(self):
        """Test that event bus exception classes are properly defined."""
        # Test EventBusError
        assert issubclass(EventBusError, Exception)
        
        # Test EventPublishError
        assert issubclass(EventPublishError, EventBusError)
        exception = EventPublishError("Test error")
        assert str(exception) == "Test error"
        
        # Test EventSubscribeError
        assert issubclass(EventSubscribeError, EventBusError)
        exception = EventSubscribeError("Test error")
        assert str(exception) == "Test error"

    def test_get_event_logger(self):
        """Test that get_event_logger returns a valid logger."""
        logger = get_event_logger()
        assert logger is not None
        # The structlog get_logger returns a BoundLoggerLazyProxy, not a standard Logger
        # Just check that it has the basic logging methods
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')

    def test_event_constants_completeness(self):
        """Test that all expected event types are defined."""
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
            assert event in EVENT_TYPES, f"Missing expected event type: {event}"

    def test_event_bus_config_values(self):
        """Test that event bus configuration has reasonable values."""
        # Test that numeric values are present and reasonable
        assert isinstance(EVENT_BUS_CONFIG["max_retries"], int)
        assert EVENT_BUS_CONFIG["max_retries"] > 0
        
        assert isinstance(EVENT_BUS_CONFIG["retry_delay"], (int, float))
        assert EVENT_BUS_CONFIG["retry_delay"] > 0
        
        assert isinstance(EVENT_BUS_CONFIG["queue_max_size"], int)
        assert EVENT_BUS_CONFIG["queue_max_size"] > 0
        
        assert isinstance(EVENT_BUS_CONFIG["batch_size"], int)
        assert EVENT_BUS_CONFIG["batch_size"] > 0
        
        assert isinstance(EVENT_BUS_CONFIG["flush_interval"], (int, float))
        assert EVENT_BUS_CONFIG["flush_interval"] > 0