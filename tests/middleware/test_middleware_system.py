"""
Tests for middleware system focusing on Aiogram 3 fixes and database injection.

Key areas tested:
1. Aiogram 3 middleware registration fixes
2. DatabaseMiddleware dependency injection
3. Middleware chain execution order
4. Error handling middleware
5. User context middleware
6. Throttling middleware
7. Configuration validation middleware
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from src.core.middleware import (
    MiddlewareManager,
    DatabaseMiddleware,
    LoggingMiddleware,
    ConfigurationValidationMiddleware,
    ErrorHandlerMiddleware,
    UserContextMiddleware,
    ThrottlingMiddleware,
    setup_default_middlewares
)
from src.services.user import UserService


class TestDatabaseMiddleware:
    """Test DatabaseMiddleware functionality and Aiogram 3 integration."""

    async def test_database_middleware_initialization(
        self,
        mock_database_manager,
        mock_event_bus
    ):
        """Test DatabaseMiddleware initialization with dependencies."""
        middleware = DatabaseMiddleware(mock_database_manager, mock_event_bus)

        assert middleware.database_manager == mock_database_manager
        assert middleware.event_bus == mock_event_bus

    async def test_database_middleware_dependency_injection(
        self,
        mock_database_manager,
        mock_event_bus,
        mock_update
    ):
        """Test dependency injection into handler data."""
        middleware = DatabaseMiddleware(mock_database_manager, mock_event_bus)

        # Mock handler
        mock_handler = AsyncMock(return_value="handler_result")

        # Mock event data
        event_data = {"test_key": "test_value"}

        # Call middleware
        result = await middleware.__call__(mock_handler, mock_update, event_data)

        # Verify dependencies were injected
        assert "database_manager" in event_data
        assert "user_service" in event_data
        assert event_data["database_manager"] == mock_database_manager

        # Verify user service was created with correct dependencies
        user_service = event_data["user_service"]
        assert isinstance(user_service, UserService)

        # Verify handler was called
        mock_handler.assert_called_once_with(mock_update, event_data)
        assert result == "handler_result"

    async def test_database_middleware_without_event_bus(
        self,
        mock_database_manager,
        mock_update
    ):
        """Test DatabaseMiddleware without event_bus parameter."""
        middleware = DatabaseMiddleware(mock_database_manager, event_bus=None)

        mock_handler = AsyncMock(return_value="handler_result")
        event_data = {}

        result = await middleware.__call__(mock_handler, mock_update, event_data)

        # Verify database_manager was injected
        assert "database_manager" in event_data
        assert event_data["database_manager"] == mock_database_manager

        # Verify user_service was NOT created without event_bus
        assert "user_service" not in event_data

        mock_handler.assert_called_once_with(mock_update, event_data)

    async def test_database_middleware_aiogram3_signature(
        self,
        mock_database_manager,
        mock_event_bus,
        mock_message
    ):
        """Test middleware signature compatibility with Aiogram 3."""
        middleware = DatabaseMiddleware(mock_database_manager, mock_event_bus)

        # Test with different Aiogram 3 event types
        from aiogram.types import Message, CallbackQuery, InlineQuery

        mock_callback = MagicMock(spec=CallbackQuery)
        mock_inline = MagicMock(spec=InlineQuery)

        mock_handler = AsyncMock(return_value="test_result")

        # Test with Message
        event_data = {}
        await middleware.__call__(mock_handler, mock_message, event_data)
        assert "database_manager" in event_data

        # Test with CallbackQuery
        event_data = {}
        await middleware.__call__(mock_handler, mock_callback, event_data)
        assert "database_manager" in event_data

        # Test with InlineQuery
        event_data = {}
        await middleware.__call__(mock_handler, mock_inline, event_data)
        assert "database_manager" in event_data


class TestLoggingMiddleware:
    """Test LoggingMiddleware functionality."""

    async def test_logging_middleware_successful_processing(
        self,
        mock_update
    ):
        """Test logging middleware with successful update processing."""
        middleware = LoggingMiddleware()

        mock_handler = AsyncMock(return_value="success_result")
        event_data = {}

        with patch.object(middleware.logger, 'info') as mock_info:
            result = await middleware.__call__(mock_handler, mock_update, event_data)

            # Verify logging calls
            assert mock_info.call_count == 2  # Incoming and processed
            assert result == "success_result"

    async def test_logging_middleware_error_handling(
        self,
        mock_update
    ):
        """Test logging middleware with handler error."""
        middleware = LoggingMiddleware()

        test_error = ValueError("Test error")
        mock_handler = AsyncMock(side_effect=test_error)
        event_data = {}

        with patch.object(middleware.logger, 'info'), \
             patch.object(middleware.logger, 'error') as mock_error:
            with pytest.raises(ValueError):
                await middleware.__call__(mock_handler, mock_update, event_data)

            # Verify error was logged
            mock_error.assert_called_once()

    async def test_logging_middleware_update_extraction(
        self,
        mock_message
    ):
        """Test logging middleware update information extraction."""
        middleware = LoggingMiddleware()

        mock_handler = AsyncMock(return_value="result")
        event_data = {}

        with patch.object(middleware.logger, 'info') as mock_info:
            await middleware.__call__(mock_handler, mock_message, event_data)

            # Verify logged information includes update details
            calls = mock_info.call_args_list
            assert len(calls) >= 1

            # Check that user_id and chat_id were extracted correctly
            first_call_kwargs = calls[0][1]
            assert 'user_id' in first_call_kwargs
            assert 'chat_id' in first_call_kwargs


class TestConfigurationValidationMiddleware:
    """Test ConfigurationValidationMiddleware functionality."""

    async def test_configuration_validation_success(
        self,
        mock_update
    ):
        """Test middleware with valid configuration."""
        middleware = ConfigurationValidationMiddleware()

        mock_handler = AsyncMock(return_value="success")
        event_data = {}

        # Mock successful validation
        with patch.object(middleware.config_manager, 'validate_config', return_value=True):
            result = await middleware.__call__(mock_handler, mock_update, event_data)

            assert result == "success"
            mock_handler.assert_called_once()

    async def test_configuration_validation_failure(
        self,
        mock_update
    ):
        """Test middleware with invalid configuration."""
        middleware = ConfigurationValidationMiddleware()

        mock_handler = AsyncMock(return_value="should_not_be_called")
        event_data = {}

        # Mock validation failure
        validation_error = ValueError("Invalid configuration")
        with patch.object(middleware.config_manager, 'validate_config', side_effect=validation_error):
            with patch.object(middleware.logger, 'error'):
                result = await middleware.__call__(mock_handler, mock_update, event_data)

                # Should return None without calling handler
                assert result is None
                mock_handler.assert_not_called()


class TestErrorHandlerMiddleware:
    """Test ErrorHandlerMiddleware functionality."""

    async def test_error_handler_middleware_success(
        self,
        mock_update
    ):
        """Test error handler middleware with successful processing."""
        middleware = ErrorHandlerMiddleware()

        mock_handler = AsyncMock(return_value="success_result")
        event_data = {}

        result = await middleware.__call__(mock_handler, mock_update, event_data)
        assert result == "success_result"

    async def test_error_handler_middleware_with_error(
        self,
        mock_update
    ):
        """Test error handler middleware processing an error."""
        middleware = ErrorHandlerMiddleware()

        test_error = RuntimeError("Test runtime error")
        mock_handler = AsyncMock(side_effect=test_error)
        event_data = {}

        with patch('src.utils.errors.error_handler') as mock_global_handler:
            mock_global_handler.handle.return_value = {
                'error_handled': True,
                'user_message': 'Error handled'
            }

            with patch.object(middleware.logger, 'error'):
                # Should re-raise the error after handling
                with pytest.raises(RuntimeError):
                    await middleware.__call__(mock_handler, mock_update, event_data)

                # Verify error handler was called
                mock_global_handler.handle.assert_called_once()


class TestUserContextMiddleware:
    """Test UserContextMiddleware functionality."""

    async def test_user_context_middleware_new_user(
        self,
        mock_update
    ):
        """Test user context middleware with new user."""
        middleware = UserContextMiddleware()

        mock_handler = AsyncMock(return_value="result")
        event_data = {}

        result = await middleware.__call__(mock_handler, mock_update, event_data)

        # Verify user context was added
        assert "user_context" in event_data
        user_context = event_data["user_context"]
        assert user_context["user_id"] == 123456789
        assert user_context["current_state"] == "start"
        assert "session_data" in user_context

    async def test_user_context_middleware_existing_user(
        self,
        mock_update
    ):
        """Test user context middleware with existing user."""
        middleware = UserContextMiddleware()

        # Pre-populate user contexts
        user_id = mock_update.message.from_user.id
        existing_context = {
            "user_id": user_id,
            "current_state": "menu",
            "session_data": {"key": "value"}
        }
        middleware.user_contexts[user_id] = existing_context

        mock_handler = AsyncMock(return_value="result")
        event_data = {}

        await middleware.__call__(mock_handler, mock_update, event_data)

        # Verify existing context was used
        assert event_data["user_context"] == existing_context

    async def test_user_context_middleware_without_user(
        self,
        mock_update
    ):
        """Test user context middleware without user information."""
        middleware = UserContextMiddleware()

        # Remove user from update
        mock_update.message.from_user = None

        mock_handler = AsyncMock(return_value="result")
        event_data = {}

        await middleware.__call__(mock_handler, mock_update, event_data)

        # Verify no user context was added
        assert "user_context" not in event_data


class TestThrottlingMiddleware:
    """Test ThrottlingMiddleware functionality."""

    async def test_throttling_middleware_within_limits(
        self,
        mock_update
    ):
        """Test throttling middleware within rate limits."""
        middleware = ThrottlingMiddleware(threshold=5, time_window=60)

        mock_handler = AsyncMock(return_value="result")
        event_data = {}

        # First request should pass
        result = await middleware.__call__(mock_handler, mock_update, event_data)
        assert result == "result"
        mock_handler.assert_called_once()

    async def test_throttling_middleware_exceeding_limits(
        self,
        mock_update
    ):
        """Test throttling middleware exceeding rate limits."""
        middleware = ThrottlingMiddleware(threshold=2, time_window=60)

        user_id = mock_update.message.from_user.id
        current_time = datetime.now().isoformat()

        # Pre-populate requests to exceed threshold
        middleware.requests[user_id] = [current_time, current_time]

        mock_handler = AsyncMock(return_value="should_not_be_called")
        event_data = {}

        with patch.object(middleware.logger, 'warning'):
            result = await middleware.__call__(mock_handler, mock_update, event_data)

            # Should return None without calling handler
            assert result is None
            mock_handler.assert_not_called()

    async def test_throttling_middleware_time_window_cleanup(
        self,
        mock_update
    ):
        """Test throttling middleware time window cleanup."""
        middleware = ThrottlingMiddleware(threshold=2, time_window=1)  # 1 second window

        user_id = mock_update.message.from_user.id
        old_time = (datetime.now() - timedelta(seconds=2)).isoformat()

        # Pre-populate with old requests
        middleware.requests[user_id] = [old_time, old_time]

        mock_handler = AsyncMock(return_value="result")
        event_data = {}

        # Should pass because old requests are outside time window
        result = await middleware.__call__(mock_handler, mock_update, event_data)
        assert result == "result"

    async def test_throttling_middleware_without_user(
        self,
        mock_update
    ):
        """Test throttling middleware without user information."""
        middleware = ThrottlingMiddleware(threshold=1, time_window=60)

        # Remove user from update
        mock_update.message.from_user = None

        mock_handler = AsyncMock(return_value="result")
        event_data = {}

        # Should pass without throttling
        result = await middleware.__call__(mock_handler, mock_update, event_data)
        assert result == "result"


class TestMiddlewareManager:
    """Test MiddlewareManager functionality."""

    def test_middleware_manager_initialization(self):
        """Test MiddlewareManager initialization."""
        manager = MiddlewareManager()
        assert len(manager.middlewares) == 0

    def test_middleware_manager_add_middleware(self):
        """Test adding middleware to manager."""
        manager = MiddlewareManager()
        middleware1 = LoggingMiddleware()
        middleware2 = ErrorHandlerMiddleware()

        manager.add_middleware(middleware1)
        manager.add_middleware(middleware2)

        middlewares = manager.get_middlewares()
        assert len(middlewares) == 2
        assert middleware1 in middlewares
        assert middleware2 in middlewares

    def test_setup_default_middlewares(self):
        """Test setup of default middlewares."""
        manager = setup_default_middlewares()

        middlewares = manager.get_middlewares()
        assert len(middlewares) == 5

        # Check that all default middlewares are present
        middleware_types = [type(m).__name__ for m in middlewares]
        expected_types = [
            'LoggingMiddleware',
            'ConfigurationValidationMiddleware',
            'UserContextMiddleware',
            'ThrottlingMiddleware',
            'ErrorHandlerMiddleware'
        ]

        for expected_type in expected_types:
            assert expected_type in middleware_types


class TestMiddlewareChainExecution:
    """Test middleware chain execution order and integration."""

    async def test_middleware_chain_execution_order(
        self,
        mock_database_manager,
        mock_event_bus,
        mock_update
    ):
        """Test middleware chain execution order."""
        execution_order = []

        class TestMiddleware1(DatabaseMiddleware):
            async def __call__(self, handler, event, data):
                execution_order.append("middleware1_start")
                result = await super().__call__(handler, event, data)
                execution_order.append("middleware1_end")
                return result

        class TestMiddleware2(LoggingMiddleware):
            async def __call__(self, handler, event, data):
                execution_order.append("middleware2_start")
                result = await super().__call__(handler, event, data)
                execution_order.append("middleware2_end")
                return result

        async def test_handler(event, data):
            execution_order.append("handler")
            return "handler_result"

        middleware1 = TestMiddleware1(mock_database_manager, mock_event_bus)
        middleware2 = TestMiddleware2()

        # Simulate middleware chain: middleware1 -> middleware2 -> handler
        async def wrapped_handler(event, data):
            return await middleware2(test_handler, event, data)

        result = await middleware1(wrapped_handler, mock_update, {})

        # Verify execution order
        expected_order = [
            "middleware1_start",
            "middleware2_start",
            "handler",
            "middleware2_end",
            "middleware1_end"
        ]
        assert execution_order == expected_order
        assert result == "handler_result"

    async def test_middleware_error_propagation(
        self,
        mock_database_manager,
        mock_event_bus,
        mock_update
    ):
        """Test error propagation through middleware chain."""
        middleware1 = DatabaseMiddleware(mock_database_manager, mock_event_bus)
        middleware2 = ErrorHandlerMiddleware()

        test_error = ValueError("Test chain error")

        async def error_handler(event, data):
            raise test_error

        with patch('src.utils.errors.error_handler') as mock_global_handler:
            mock_global_handler.handle.return_value = {'error_handled': True}

            with patch.object(middleware2.logger, 'error'):
                # Chain: middleware1 -> middleware2 -> error_handler
                async def wrapped_handler(event, data):
                    return await middleware2(error_handler, event, data)

                with pytest.raises(ValueError):
                    await middleware1(wrapped_handler, mock_update, {})

    async def test_middleware_data_flow(
        self,
        mock_database_manager,
        mock_event_bus,
        mock_update
    ):
        """Test data flow through middleware chain."""
        middleware1 = DatabaseMiddleware(mock_database_manager, mock_event_bus)
        middleware2 = UserContextMiddleware()

        async def data_inspector_handler(event, data):
            return {
                'has_database_manager': 'database_manager' in data,
                'has_user_service': 'user_service' in data,
                'has_user_context': 'user_context' in data,
                'data_keys': list(data.keys())
            }

        # Chain: middleware1 -> middleware2 -> data_inspector_handler
        async def wrapped_handler(event, data):
            return await middleware2(data_inspector_handler, event, data)

        result = await middleware1(wrapped_handler, mock_update, {})

        # Verify all middleware injected their data
        assert result['has_database_manager'] is True
        assert result['has_user_service'] is True
        assert result['has_user_context'] is True

    async def test_performance_with_multiple_middlewares(
        self,
        performance_monitor,
        mock_database_manager,
        mock_event_bus,
        mock_update
    ):
        """Test performance impact of multiple middlewares."""
        middlewares = [
            DatabaseMiddleware(mock_database_manager, mock_event_bus),
            LoggingMiddleware(),
            UserContextMiddleware(),
            ThrottlingMiddleware(),
        ]

        async def simple_handler(event, data):
            return "result"

        performance_monitor.start()

        # Simulate processing 100 updates through middleware chain
        for _ in range(100):
            current_handler = simple_handler

            # Apply middlewares in reverse order to create chain
            for middleware in reversed(middlewares):
                next_handler = current_handler

                async def make_wrapped_handler(mw, nh):
                    async def wrapped(event, data):
                        with patch.object(mw.logger if hasattr(mw, 'logger') else MagicMock(), 'info'), \
                             patch.object(mw.logger if hasattr(mw, 'logger') else MagicMock(), 'error'):
                            return await mw(nh, event, data)
                    return wrapped

                current_handler = await make_wrapped_handler(middleware, next_handler)

            await current_handler(mock_update, {})

        metrics = performance_monitor.stop()

        # Assert reasonable performance (should handle 100 updates quickly)
        assert metrics['duration'] < 5.0  # Should complete in under 5 seconds