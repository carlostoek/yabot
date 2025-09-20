"""
Event bus module for the YABOT system.

This module provides the foundation for event-driven communication as required by the fase1 specification.
"""

# Event bus module structure
# This file makes the events directory a Python package and defines the public interface

from typing import Any, Dict, List, Optional, Callable, Awaitable
import asyncio
import logging
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Event bus component imports (to be implemented in future tasks)
# from .bus import EventBus
# from .processor import EventProcessor
# from .schemas import BaseEvent

# Event type definitions
EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]
EventHandler = Callable[[Dict[str, Any]], None]

# Event constants
EVENT_TYPES = [
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

# Event bus configuration
EVENT_BUS_CONFIG = {
    "max_retries": 3,
    "retry_delay": 1.0,  # seconds
    "queue_max_size": 1000,
    "batch_size": 10,
    "flush_interval": 5.0  # seconds
}


class EventBusError(Exception):
    """Base exception for event bus operations."""
    pass


class EventPublishError(EventBusError):
    """Exception raised when event publishing fails."""
    pass


class EventSubscribeError(EventBusError):
    """Exception raised when event subscription fails."""
    pass


def get_event_logger() -> logging.Logger:
    """Get a logger instance for event operations.
    
    Returns:
        logging.Logger: Logger instance for event operations
    """
    return get_logger("events")


# Module initialization
logger.info("Event bus module initialized")

__all__ = [
    "EventCallback",
    "EventHandler",
    "EVENT_TYPES",
    "EVENT_BUS_CONFIG",
    "EventBusError",
    "EventPublishError",
    "EventSubscribeError",
    "get_event_logger"
]