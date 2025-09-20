"""
Test Router database context functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.core.router import Router
from src.services.user import UserService
from src.events.bus import EventBus
from src.database.manager import DatabaseManager


class TestRouterDatabaseContext:
    """Test router database context functionality."""

    @pytest.mark.asyncio
    async def test_router_initialization_with_database_context(self):
        """Test router initialization with database context."""
        # Create mock services
        mock_user_service = Mock(spec=UserService)
        mock_event_bus = Mock(spec=EventBus)
        mock_database_manager = Mock(spec=DatabaseManager)
        
        # Initialize router with database context
        router = Router(
            user_service=mock_user_service,
            event_bus=mock_event_bus,
            database_manager=mock_database_manager
        )
        
        # Verify context is set correctly
        assert router.user_service == mock_user_service
        assert router.event_bus == mock_event_bus
        assert router.database_manager == mock_database_manager
        assert router.has_database_context is True
        assert router.has_event_context is True

    @pytest.mark.asyncio
    async def test_router_initialization_without_database_context(self):
        """Test router initialization without database context."""
        # Initialize router without database context
        router = Router()
        
        # Verify context is None
        assert router.user_service is None
        assert router.event_bus is None
        assert router.database_manager is None
        assert router.has_database_context is False
        assert router.has_event_context is False

    @pytest.mark.asyncio
    async def test_router_passes_context_to_handler_with_router_parameter(self):
        """Test that router passes context to handlers that accept router parameter."""
        # Create mock services
        mock_user_service = Mock(spec=UserService)
        mock_event_bus = Mock(spec=EventBus)
        mock_database_manager = Mock(spec=DatabaseManager)
        
        # Initialize router with database context
        router = Router(
            user_service=mock_user_service,
            event_bus=mock_event_bus,
            database_manager=mock_database_manager
        )
        
        # Create a mock handler that accepts router parameter
        async def mock_handler_with_router(update, router=None):
            # Verify router context is passed
            assert router is not None
            assert router.user_service == mock_user_service
            assert router.event_bus == mock_event_bus
            assert router.database_manager == mock_database_manager
            return "handler_with_router_result"
        
        # Register the handler
        router.register_command_handler("test", mock_handler_with_router)
        
        # Create a mock update
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "/test"
        
        # Route the update
        result = await router.route_update(mock_update)
        
        # Verify the handler was called and returned the expected result
        assert result == "handler_with_router_result"

    @pytest.mark.asyncio
    async def test_router_calls_handler_without_router_parameter(self):
        """Test that router calls handlers that don't accept router parameter."""
        # Initialize router without database context
        router = Router()
        
        # Create a mock handler that doesn't accept router parameter
        async def mock_handler_without_router(update):
            return "handler_without_router_result"
        
        # Register the handler
        router.register_command_handler("test", mock_handler_without_router)
        
        # Create a mock update
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "/test"
        
        # Route the update
        result = await router.route_update(mock_update)
        
        # Verify the handler was called and returned the expected result
        assert result == "handler_without_router_result"

    @pytest.mark.asyncio
    async def test_router_calls_default_handler_with_context(self):
        """Test that router passes context to default handler."""
        # Create mock services
        mock_user_service = Mock(spec=UserService)
        mock_event_bus = Mock(spec=EventBus)
        mock_database_manager = Mock(spec=DatabaseManager)
        
        # Initialize router with database context
        router = Router(
            user_service=mock_user_service,
            event_bus=mock_event_bus,
            database_manager=mock_database_manager
        )
        
        # Create a mock default handler that accepts router parameter
        async def mock_default_handler(update, router=None):
            # Verify router context is passed
            assert router is not None
            assert router.user_service == mock_user_service
            assert router.event_bus == mock_event_bus
            assert router.database_manager == mock_database_manager
            return "default_handler_result"
        
        # Set the default handler
        router.set_default_handler(mock_default_handler)
        
        # Create a mock update that won't match any registered handlers
        mock_update = Mock()
        mock_update.message = Mock()
        mock_update.message.text = "/unknown"
        
        # Route the update
        result = await router.route_update(mock_update)
        
        # Verify the default handler was called and returned the expected result
        assert result == "default_handler_result"