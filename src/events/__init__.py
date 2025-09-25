"""
Event Bus Module - Core Infrastructure

This module provides the foundational event bus infrastructure for the YABOT system,
enabling asynchronous communication between different system components.
"""
from typing import TYPE_CHECKING

# Import core components
if TYPE_CHECKING:
    from .bus import EventBus
    from .processor import EventProcessor
    from .models import BaseEvent, UserInteractionEvent, ReactionDetectedEvent

# Import main classes from submodules
from .bus import EventBus
from .processor import EventProcessor
from .models import (
    BaseEvent, 
    UserInteractionEvent, 
    ReactionDetectedEvent,
    EventStatus
)

# Import configuration and utility functions
from .config import get_redis_config
from .exceptions import EventBusException, EventProcessingError

# Define the public API
__all__ = [
    # Core components
    'EventBus',
    'EventProcessor',
    
    # Base event models
    'BaseEvent',
    'UserInteractionEvent', 
    'ReactionDetectedEvent',
    'EventStatus',
    
    # Configuration
    'get_redis_config',
    
    # Exceptions
    'EventBusException',
    'EventProcessingError'
]

# Convenience functions for initialization
async def create_event_bus(redis_config: dict = None) -> 'EventBus':
    """
    Create and configure an event bus instance
    
    Args:
        redis_config: Optional Redis configuration dictionary
        
    Returns:
        Configured EventBus instance
    """
    from .bus import EventBus
    return EventBus(redis_config=redis_config)

async def create_event_processor(subscriptions: dict = None) -> 'EventProcessor':
    """
    Create and configure an event processor instance
    
    Args:
        subscriptions: Optional dictionary mapping event types to handler functions
        
    Returns:
        Configured EventProcessor instance
    """
    from .processor import EventProcessor
    return EventProcessor(subscriptions=subscriptions)

# Global instance for easy access (singleton pattern)
_event_bus_instance = None
_event_processor_instance = None


async def get_event_bus() -> 'EventBus':
    """
    Get the global event bus instance, creating it if needed
    
    Returns:
        EventBus instance
    """
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = await create_event_bus()
    return _event_bus_instance


async def get_event_processor() -> 'EventProcessor':
    """
    Get the global event processor instance, creating it if needed
    
    Returns:
        EventProcessor instance
    """
    global _event_processor_instance
    if _event_processor_instance is None:
        _event_processor_instance = await create_event_processor()
    return _event_processor_instance


async def initialize_event_system(redis_config: dict = None, subscriptions: dict = None):
    """
    Initialize the complete event system with both bus and processor
    
    Args:
        redis_config: Optional Redis configuration
        subscriptions: Optional event subscriptions
    """
    global _event_bus_instance, _event_processor_instance
    
    # Create event bus
    _event_bus_instance = await create_event_bus(redis_config)
    
    # Create event processor
    _event_processor_instance = await create_event_processor(subscriptions)
    
    # Return both instances
    return _event_bus_instance, _event_processor_instance


async def shutdown_event_system():
    """
    Shutdown the event system and clean up resources
    """
    global _event_bus_instance, _event_processor_instance
    
    # Shutdown event bus if it exists
    if _event_bus_instance:
        await _event_bus_instance.close()
        _event_bus_instance = None
    
    # Shutdown event processor if it exists
    if _event_processor_instance:
        await _event_processor_instance.shutdown()
        _event_processor_instance = None


# Convenience imports for common event types
from .models import (
    # User interaction events
    UserInteractionEvent,
    UserRegistrationEvent,
    DecisionMadeEvent,
    SubscriptionUpdatedEvent,
    
    # Content interaction events
    ReactionDetectedEvent,
    ContentViewedEvent,
    HintUnlockedEvent,
    
    # System events
    SystemHealthEvent,
    SystemNotificationEvent
)

__all__.extend([
    'UserRegistrationEvent',
    'DecisionMadeEvent', 
    'SubscriptionUpdatedEvent',
    'ContentViewedEvent',
    'HintUnlockedEvent',
    'SystemHealthEvent',
    'SystemNotificationEvent',
    # Functions
    'create_event_bus',
    'create_event_processor',
    'get_event_bus',
    'get_event_processor',
    'initialize_event_system',
    'shutdown_event_system'
])