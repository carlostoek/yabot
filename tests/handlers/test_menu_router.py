"""
Unit tests for the MenuIntegrationRouter.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

from aiogram.types import Message, CallbackQuery, User, Chat

from src.handlers.menu_router import MenuIntegrationRouter
from src.core.middleware import Middleware


class TestMenuIntegrationRouter:
    """Test cases for the MenuIntegrationRouter class."""

    @pytest.fixture
    def menu_router(self):
        """Create a MenuIntegrationRouter instance for testing."""
        return MenuIntegrationRouter()

    @pytest.fixture
    def mock_handler(self):
        """Create a mock async handler for testing."""
        return AsyncMock()

    @pytest.fixture
    def mock_message(self):
        """Create a mock Aiogram Message object."""
        message = MagicMock(spec=Message)
        message.text = "/start"
        message.from_user = MagicMock(spec=User)
        message.chat = MagicMock(spec=Chat)
        return message

    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock Aiogram CallbackQuery object."""
        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.data = "menu:main"
        callback_query.from_user = MagicMock(spec=User)
        callback_query.message = MagicMock(spec=Message)
        return callback_query

    def test_initialization(self, menu_router):
        """Test that the MenuIntegrationRouter initializes correctly."""
        assert isinstance(menu_router, MenuIntegrationRouter)
        assert hasattr(menu_router, 'middleware_manager')
        assert menu_router._callback_handlers == {}

    def test_add_middleware(self, menu_router):
        """Test that middleware can be added."""
        mock_middleware = Mock(spec=Middleware)
        menu_router.add_middleware(mock_middleware)
        assert mock_middleware in menu_router.middleware_manager._middlewares

    def test_register_callback_handler(self, menu_router, mock_handler):
        """Test registering a callback handler."""
        menu_router.register_callback_handler("menu:", mock_handler)
        assert "menu:" in menu_router._callback_handlers
        assert menu_router._callback_handlers["menu:"] == mock_handler

    def test_register_callback_handler_invalid(self, menu_router):
        """Test that registering a non-callable handler raises TypeError."""
        with pytest.raises(TypeError, match="Handler must be callable"):
            menu_router.register_callback_handler("prefix", "not_a_callable")

    @pytest.mark.asyncio
    async def test_route_message_calls_route_update(self, menu_router, mock_message):
        """Test that route_message correctly calls the base route_update."""
        menu_router.route_update = AsyncMock()
        await menu_router.route_message(mock_message)
        menu_router.route_update.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    async def test_route_update_with_middleware(self, menu_router, mock_message, mock_handler):
        """Test that route_update processes through middleware."""
        # Setup middleware
        mock_middleware = Mock(spec=Middleware)
        mock_middleware.process_request = AsyncMock(return_value=mock_message)
        mock_middleware.process_response = AsyncMock(return_value="processed_response")
        menu_router.add_middleware(mock_middleware)

        # Setup handler
        menu_router.register_command_handler("start", mock_handler)
        mock_handler.return_value = "original_response"

        # Route
        result = await menu_router.route_update(mock_message)

        # Assert
        mock_middleware.process_request.assert_called_once_with(mock_message)
        mock_handler.assert_called_once()
        mock_middleware.process_response.assert_called_once_with("original_response")
        assert result == "processed_response"

    @pytest.mark.asyncio
    async def test_route_callback_specific_handler(self, menu_router, mock_callback_query, mock_handler):
        """Test routing a callback to a specific, registered handler."""
        menu_router.register_callback_handler("menu:", mock_handler)
        menu_router.middleware_manager.process_request = AsyncMock(side_effect=lambda x: x)
        menu_router.middleware_manager.process_response = AsyncMock(side_effect=lambda x: x)

        await menu_router.route_callback(mock_callback_query)

        mock_handler.assert_called_once_with(mock_callback_query)
        menu_router.middleware_manager.process_request.assert_called_once()
        menu_router.middleware_manager.process_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_callback_fallback_to_default(self, menu_router, mock_callback_query, mock_handler):
        """Test that a callback falls back to the default handler if no specific one is found."""
        # No specific callback handler, but a default message handler
        menu_router.set_default_handler(mock_handler)
        menu_router.route_update = AsyncMock(wraps=menu_router.route_update)

        await menu_router.route_callback(mock_callback_query)

        # It should call the generic route_update, which then calls the default handler
        menu_router.route_update.assert_called_once_with(mock_callback_query)
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_inherited_command_routing(self, menu_router, mock_message, mock_handler):
        """Test that the router can still route commands like its parent."""
        menu_router.register_command_handler("start", mock_handler)

        await menu_router.route_message(mock_message)

        mock_handler.assert_called_once_with(mock_message)
