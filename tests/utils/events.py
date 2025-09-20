"""
Event bus test utilities for the YABOT system.

This module provides utilities for testing event bus-related functionality,
including mock event buses, test event factories, and helper functions
for event testing as required by the fase1 specification testing strategy.
"""

import asyncio
import json
import pytest
import uuid
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime

from src.events.bus import EventBus, EventBusError, EventPublishError, EventSubscribeError
from src.events.models import BaseEvent, create_event, EVENT_MODELS
from src.config.manager import ConfigManager


class MockEventBus:
    """Mock event bus for testing event-related functionality."""
    
    def __init__(self):
        """Initialize the mock event bus."""
        self._is_connected = False
        self._published_events = []
        self._subscribers = {}
        self._local_queue = []
        self._method_calls = []
        self._should_fail_publish = False
        self._should_fail_subscribe = False
    
    async def connect(self) -> bool:
        """Mock connect to event bus.
        
        Returns:
            bool: True indicating successful connection
        """
        self._method_calls.append("connect")
        self._is_connected = True
        return True
    
    async def publish(self, event_name: str, payload: Dict[str, Any]) -> bool:
        """Mock publish an event.
        
        Args:
            event_name (str): Name of the event
            payload (Dict[str, Any]): Event payload
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            EventPublishError: If publishing should fail
        """
        self._method_calls.append(("publish", event_name))
        
        if self._should_fail_publish:
            raise EventPublishError("Mock publish failure")
        
        # Store the published event for verification
        event_data = {
            "event_name": event_name,
            "payload": payload,
            "timestamp": datetime.utcnow()
        }
        self._published_events.append(event_data)
        return True
    
    async def subscribe(self, event_name: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> bool:
        """Mock subscribe to an event.
        
        Args:
            event_name (str): Name of the event to subscribe to
            handler (Callable): Handler function to call when event is published
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            EventSubscribeError: If subscription should fail
        """
        self._method_calls.append(("subscribe", event_name))
        
        if self._should_fail_subscribe:
            raise EventSubscribeError("Mock subscribe failure")
        
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(handler)
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock event bus health check.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        self._method_calls.append("health_check")
        return {
            "connected": self._is_connected,
            "local_queue_size": len(self._local_queue),
            "subscribers_count": sum(len(handlers) for handlers in self._subscribers.values())
        }
    
    async def close(self) -> None:
        """Mock close event bus connections."""
        self._method_calls.append("close")
        self._is_connected = False
    
    def set_publish_failure(self, should_fail: bool = True) -> None:
        """Set whether publish operations should fail.
        
        Args:
            should_fail (bool): Whether publish operations should fail
        """
        self._should_fail_publish = should_fail
    
    def set_subscribe_failure(self, should_fail: bool = True) -> None:
        """Set whether subscribe operations should fail.
        
        Args:
            should_fail (bool): Whether subscribe operations should fail
        """
        self._should_fail_subscribe = should_fail
    
    @property
    def is_connected(self) -> bool:
        """Check if event bus is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self._is_connected
    
    @property
    def published_events(self) -> List[Dict[str, Any]]:
        """Get list of published events.
        
        Returns:
            List[Dict[str, Any]]: List of published events
        """
        return self._published_events.copy()
    
    @property
    def method_calls(self) -> List:
        """Get list of method calls made on this mock.
        
        Returns:
            List: List of method calls
        """
        return self._method_calls.copy()
    
    def reset(self) -> None:
        """Reset the mock event bus state."""
        self._published_events.clear()
        self._subscribers.clear()
        self._local_queue.clear()
        self._method_calls.clear()
        self._should_fail_publish = False
        self._should_fail_subscribe = False


class EventTestConfig:
    """Configuration utilities for event testing."""
    
    @staticmethod
    def create_test_config_manager(
        redis_url: str = "redis://localhost:6379",
        redis_password: Optional[str] = None
    ) -> ConfigManager:
        """Create a test configuration manager with Redis settings.
        
        Args:
            redis_url (str): Redis connection URL
            redis_password (str, optional): Redis password
            
        Returns:
            ConfigManager: Test configuration manager
        """
        # Create a mock config manager
        mock_config = Mock(spec=ConfigManager)
        
        # Mock the get_redis_config method
        def mock_get_redis_config():
            mock_redis_config = Mock()
            mock_redis_config.redis_url = redis_url
            mock_redis_config.redis_password = redis_password
            return mock_redis_config
        
        mock_config.get_redis_config = mock_get_redis_config
        return mock_config
    
    @staticmethod
    def set_test_env_vars(
        redis_url: str = "redis://localhost:6379",
        redis_password: Optional[str] = None
    ) -> Dict[str, str]:
        """Set environment variables for event testing.
        
        Args:
            redis_url (str): Redis connection URL
            redis_password (str, optional): Redis password
            
        Returns:
            Dict[str, str]: Original environment variables that were overridden
        """
        import os
        
        original_vars = {}
        
        # Store original values
        if "REDIS_URL" in os.environ:
            original_vars["REDIS_URL"] = os.environ["REDIS_URL"]
        if "REDIS_PASSWORD" in os.environ:
            original_vars["REDIS_PASSWORD"] = os.environ["REDIS_PASSWORD"]
        
        # Set test values
        os.environ["REDIS_URL"] = redis_url
        if redis_password:
            os.environ["REDIS_PASSWORD"] = redis_password
        elif "REDIS_PASSWORD" in os.environ:
            del os.environ["REDIS_PASSWORD"]
        
        return original_vars
    
    @staticmethod
    def restore_env_vars(original_vars: Dict[str, str]) -> None:
        """Restore original environment variables.
        
        Args:
            original_vars (Dict[str, str]): Original environment variables
        """
        import os
        
        # Remove test values first
        for var in ["REDIS_URL", "REDIS_PASSWORD"]:
            if var in os.environ:
                del os.environ[var]
        
        # Restore original values
        for var, value in original_vars.items():
            os.environ[var] = value


class EventTestDataFactory:
    """Factory for creating event test data."""
    
    @staticmethod
    def create_base_event(
        event_type: str = "test_event",
        event_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> BaseEvent:
        """Create a base event for testing.
        
        Args:
            event_type (str): Type of event
            event_id (str, optional): Event ID
            user_id (str, optional): User ID
            correlation_id (str, optional): Correlation ID
            payload (Dict[str, Any], optional): Event payload
            
        Returns:
            BaseEvent: Created event
        """
        return create_event(
            event_type=event_type,
            event_id=event_id or str(uuid.uuid4()),
            user_id=user_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            payload=payload or {}
        )
    
    @staticmethod
    def create_user_interaction_event(
        user_id: str = "test_user_123",
        action: str = "start",
        context: Optional[Dict[str, Any]] = None
    ) -> BaseEvent:
        """Create a user interaction event for testing.
        
        Args:
            user_id (str): User ID
            action (str): User action
            context (Dict[str, Any], optional): Interaction context
            
        Returns:
            BaseEvent: Created user interaction event
        """
        return create_event(
            event_type="user_interaction",
            user_id=user_id,
            action=action,
            context=context or {"source": "test"}
        )
    
    @staticmethod
    def create_reaction_detected_event(
        user_id: str = "test_user_123",
        content_id: str = "content_001",
        reaction_type: str = "like",
        metadata: Optional[Dict[str, Any]] = None
    ) -> BaseEvent:
        """Create a reaction detected event for testing.
        
        Args:
            user_id (str): User ID
            content_id (str): Content ID
            reaction_type (str): Reaction type
            metadata (Dict[str, Any], optional): Additional metadata
            
        Returns:
            BaseEvent: Created reaction detected event
        """
        return create_event(
            event_type="reaction_detected",
            user_id=user_id,
            content_id=content_id,
            reaction_type=reaction_type,
            metadata=metadata or {"source": "test"}
        )
    
    @staticmethod
    def create_decision_made_event(
        user_id: str = "test_user_123",
        choice_id: str = "choice_a",
        context: Optional[Dict[str, Any]] = None
    ) -> BaseEvent:
        """Create a decision made event for testing.
        
        Args:
            user_id (str): User ID
            choice_id (str): Choice ID
            context (Dict[str, Any], optional): Decision context
            
        Returns:
            BaseEvent: Created decision made event
        """
        return create_event(
            event_type="decision_made",
            user_id=user_id,
            choice_id=choice_id,
            context=context or {"fragment_id": "fragment_001"}
        )
    
    @staticmethod
    def create_subscription_updated_event(
        user_id: str = "test_user_123",
        plan_type: str = "premium",
        status: str = "active",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BaseEvent:
        """Create a subscription updated event for testing.
        
        Args:
            user_id (str): User ID
            plan_type (str): Plan type
            status (str): Subscription status
            start_date (datetime, optional): Start date
            end_date (datetime, optional): End date
            
        Returns:
            BaseEvent: Created subscription updated event
        """
        now = datetime.utcnow()
        return create_event(
            event_type="subscription_updated",
            user_id=user_id,
            plan_type=plan_type,
            status=status,
            start_date=start_date or now,
            end_date=end_date
        )
    
    @staticmethod
    def create_test_event_payload(event_name: str = "test_event") -> Dict[str, Any]:
        """Create a test event payload.
        
        Args:
            event_name (str): Event name
            
        Returns:
            Dict[str, Any]: Event payload
        """
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": event_name,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": str(uuid.uuid4()),
            "user_id": "test_user_123",
            "payload": {
                "test_data": "test_value"
            }
        }


class EventTestHelpers:
    """Helper functions for event testing."""
    
    @staticmethod
    async def create_test_event_bus(
        config_manager: Optional[ConfigManager] = None
    ) -> EventBus:
        """Create an event bus for testing.
        
        Args:
            config_manager (ConfigManager, optional): Configuration manager
            
        Returns:
            EventBus: Event bus instance
        """
        event_bus = EventBus(config_manager)
        return event_bus
    
    @staticmethod
    def create_async_mock_handler() -> AsyncMock:
        """Create an async mock handler for event subscription testing.
        
        Returns:
            AsyncMock: Async mock handler
        """
        return AsyncMock()
    
    @staticmethod
    async def wait_for_handler_call(handler: AsyncMock, timeout: float = 1.0) -> bool:
        """Wait for a handler to be called.
        
        Args:
            handler (AsyncMock): Handler to wait for
            timeout (float): Timeout in seconds
            
        Returns:
            bool: True if handler was called, False if timeout
        """
        try:
            await asyncio.wait_for(handler.call_count, timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
    
    @staticmethod
    def capture_event_payloads(event_bus: MockEventBus) -> List[Dict[str, Any]]:
        """Capture event payloads from a mock event bus.
        
        Args:
            event_bus (MockEventBus): Mock event bus
            
        Returns:
            List[Dict[str, Any]]: List of event payloads
        """
        return [event["payload"] for event in event_bus.published_events]


# Pytest fixtures for event testing
@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing.
    
    Returns:
        MockEventBus: Mock event bus
    """
    return MockEventBus()


@pytest.fixture
def event_test_config():
    """Create event test configuration utilities.
    
    Returns:
        EventTestConfig: Event test configuration utilities
    """
    return EventTestConfig()


@pytest.fixture
def event_test_data_factory():
    """Create event test data factory.
    
    Returns:
        EventTestDataFactory: Event test data factory
    """
    return EventTestDataFactory()


@pytest.fixture
def event_test_helpers():
    """Create event test helpers.
    
    Returns:
        EventTestHelpers: Event test helpers
    """
    return EventTestHelpers()


# Context manager for event testing
class EventTestContext:
    """Context manager for event testing with proper setup and teardown."""
    
    def __init__(self):
        """Initialize the event test context."""
        self.original_env_vars = {}
    
    def __enter__(self):
        """Enter the event test context."""
        # Set test environment variables
        self.original_env_vars = EventTestConfig.set_test_env_vars(
            redis_url="redis://localhost:6379"
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the event test context."""
        # Restore original environment variables
        EventTestConfig.restore_env_vars(self.original_env_vars)