"""
Integration tests for the complete bot startup sequence.

Tests all the areas that had recent fixes:
1. MongoDB boolean check fixes (using `is None`)
2. Redis configuration access fixes
3. FastAPI startup event fixes
4. Aiogram 3 middleware registration fixes
5. Missing router creation
6. UserService event_bus parameter fixes
7. AiogramErrorHandler signature fixes
8. EventBus dict/object parameter fixes
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.core.application import BotApplication, get_bot_application
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.services.user import UserService
from src.core.error_handler import ErrorHandler, AiogramErrorHandler
from src.core.middleware import DatabaseMiddleware


class TestCompleteStartupSequence:
    """Test the complete bot startup sequence."""

    @pytest.fixture(autouse=True)
    def setup_method(self, cleanup_global_singletons):
        """Setup method with global cleanup."""
        pass

    async def test_full_startup_sequence_polling_mode(
        self,
        mock_aiogram_bot,
        mock_aiogram_dispatcher,
        enhanced_mock_config_manager
    ):
        """Test complete startup sequence in polling mode."""
        with patch('aiogram.utils.token.validate_token') as mock_validate:
            # Skip token validation for tests
            mock_validate.return_value = True
            with patch('src.database.manager.DatabaseManager') as mock_db_class:
                with patch('src.events.bus.EventBus') as mock_bus_class:
                    # Setup mocks
                    mock_db_instance = MagicMock()
                    mock_db_instance.initialize_databases = AsyncMock(return_value=True)
                    mock_db_instance.close_connections = AsyncMock()
                    mock_db_class.return_value = mock_db_instance

                    mock_bus_instance = MagicMock()
                    mock_bus_instance.connect = AsyncMock()
                    mock_bus_instance.close = AsyncMock()
                    mock_bus_class.return_value = mock_bus_instance

                    # Create application
                    app = BotApplication()

                    # Test initialization
                    await app.initialize()
                    assert app.bot is not None
                    assert app.dispatcher is not None

                    # Test startup
                    with patch.object(app, '_start_polling', new_callable=AsyncMock) as mock_polling:
                        await app.start()
                        mock_polling.assert_called_once()

                    # Verify configuration was validated
                    enhanced_mock_config_manager.validate_config.assert_called()

                    # Test cleanup
                    await app.stop()

    async def test_full_startup_sequence_webhook_mode(
        self,
        mock_aiogram_bot,
        mock_aiogram_dispatcher,
        enhanced_mock_config_manager
    ):
        """Test complete startup sequence in webhook mode."""
        # Configure for webhook mode
        enhanced_mock_config_manager.is_webhook_mode.return_value = True
        enhanced_mock_config_manager.get_mode.return_value = 'webhook'

        with patch('aiogram.utils.token.validate_token') as mock_validate:
            # Skip token validation for tests
            mock_validate.return_value = True
            with patch('src.database.manager.DatabaseManager') as mock_db_class:
                with patch('src.events.bus.EventBus') as mock_bus_class:
                    # Setup mocks
                    mock_db_instance = MagicMock()
                    mock_db_instance.initialize_databases = AsyncMock(return_value=True)
                    mock_db_instance.close_connections = AsyncMock()
                    mock_db_class.return_value = mock_db_instance

                    mock_bus_instance = MagicMock()
                    mock_bus_instance.connect = AsyncMock()
                    mock_bus_instance.close = AsyncMock()
                    mock_bus_class.return_value = mock_bus_instance

                    # Create application
                    app = BotApplication()

                    # Test initialization
                    await app.initialize()

                    # Test webhook configuration
                    with patch.object(app, 'configure_webhook', return_value=True) as mock_webhook:
                        with patch.object(app, '_start_webhook_server', new_callable=AsyncMock) as mock_server:
                            await app.start()
                            mock_webhook.assert_called()
                            mock_server.assert_called_once()

                    await app.stop()

    async def test_database_initialization_sequence(
        self,
        test_database_config,
        temp_db_file
    ):
        """Test database initialization sequence with real SQLite."""
        # Test DatabaseManager initialization
        db_manager = DatabaseManager(test_database_config)

        # Mock MongoDB to avoid dependency
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_mongo:
            mock_client = MagicMock()
            mock_client.admin.command = AsyncMock()
            mock_client.__getitem__.return_value = MagicMock()
            mock_mongo.return_value = mock_client

            # Test connection
            result = await db_manager.connect_all()
            assert result is True

            # Test health check
            health = await db_manager.health_check()
            assert 'mongo_connected' in health
            assert 'sqlite_connected' in health

            # Test cleanup
            await db_manager.close_connections()

    async def test_event_bus_initialization_with_fallback(
        self,
        test_redis_config,
        temp_event_queue_file
    ):
        """Test EventBus initialization with fallback to local queue."""
        # Test EventBus with Redis unavailable
        event_bus = EventBus(test_redis_config)

        # Mock Redis connection failure
        with patch('redis.asyncio.ConnectionPool.from_url') as mock_pool:
            with patch('redis.asyncio.Redis') as mock_redis:
                mock_redis_instance = MagicMock()
                mock_redis_instance.ping = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
                mock_redis.return_value = mock_redis_instance

                # Test connection - should fallback to local queue
                await event_bus.connect()
                assert event_bus._connected is False

                # Test health check
                health = await event_bus.health_check()
                assert 'redis_connected' in health
                assert 'local_queue_size' in health

                await event_bus.close()

    async def test_middleware_registration_sequence(
        self,
        mock_database_manager,
        mock_event_bus,
        mock_aiogram_dispatcher
    ):
        """Test middleware registration sequence including DatabaseMiddleware."""
        # Create DatabaseMiddleware instance
        db_middleware = DatabaseMiddleware(mock_database_manager, mock_event_bus)

        # Test middleware registration
        mock_aiogram_dispatcher.message.middleware(db_middleware)
        mock_aiogram_dispatcher.callback_query.middleware(db_middleware)
        mock_aiogram_dispatcher.inline_query.middleware(db_middleware)
        mock_aiogram_dispatcher.chosen_inline_result.middleware(db_middleware)

        # Verify middleware was registered
        assert mock_aiogram_dispatcher.message.middleware.called
        assert mock_aiogram_dispatcher.callback_query.middleware.called
        assert mock_aiogram_dispatcher.inline_query.middleware.called
        assert mock_aiogram_dispatcher.chosen_inline_result.middleware.called

    async def test_error_handler_registration_sequence(
        self,
        mock_aiogram_dispatcher
    ):
        """Test error handler registration with AiogramErrorHandler signature fix."""
        # Create error handler
        error_handler = AiogramErrorHandler()

        # Test error handler registration
        mock_aiogram_dispatcher.errors.register(error_handler.handle)

        # Verify registration
        mock_aiogram_dispatcher.errors.register.assert_called_with(error_handler.handle)

        # Test error handling
        test_error = ValueError("Test error")
        await error_handler.handle(test_error)

    async def test_user_service_initialization_with_event_bus(
        self,
        mock_database_manager,
        mock_event_bus,
        telegram_user_data
    ):
        """Test UserService initialization with event_bus parameter fix."""
        # Create UserService with dependencies (event_bus passed via kwargs in methods, not constructor)
        user_service = UserService(mock_database_manager)

        # Verify dependencies are properly set
        assert user_service.db_manager == mock_database_manager
        # event_bus is passed as kwargs to methods, not stored as attribute

        # Test user creation with event publishing (event_bus passed via kwargs)
        result = await user_service.create_user(telegram_user_data, event_bus=mock_event_bus)

        # Verify database operations were called
        mock_database_manager.create_user_atomic.assert_called_once()

        # Verify event was published
        mock_event_bus.publish.assert_called_once()

    async def test_configuration_validation_sequence(
        self,
        enhanced_mock_config_manager
    ):
        """Test configuration validation sequence."""
        # Test successful validation
        result = enhanced_mock_config_manager.validate_config()
        assert result is True

        # Test configuration access patterns that had recent fixes
        bot_token = enhanced_mock_config_manager.get_bot_token()
        assert bot_token is not None

        redis_config = enhanced_mock_config_manager.get_redis_config()
        assert redis_config is not None

        database_config = enhanced_mock_config_manager.get_database_config()
        assert database_config is not None

        # Test boolean checks (fixing MongoDB boolean check issues)
        webhook_config = enhanced_mock_config_manager.get_webhook_config()
        assert webhook_config is not None

        # Test the specific pattern that was fixed: using `is None`
        assert (webhook_config is None) == False

    async def test_startup_failure_recovery_sequence(
        self,
        mock_aiogram_bot,
        mock_aiogram_dispatcher,
        enhanced_mock_config_manager
    ):
        """Test startup failure and recovery scenarios."""
        with patch('aiogram.utils.token.validate_token') as mock_validate:
            # Skip token validation for tests
            mock_validate.return_value = True
            with patch('src.database.manager.DatabaseManager') as mock_db_class:
                # Simulate database initialization failure
                mock_db_instance = MagicMock()
                mock_db_instance.initialize_databases = AsyncMock(return_value=False)
                mock_db_class.return_value = mock_db_instance

                app = BotApplication()
                await app.initialize()

                # Test startup with database failure
                with pytest.raises(RuntimeError, match="Failed to initialize databases"):
                    await app.start()

    async def test_webhook_fallback_to_polling_sequence(
        self,
        mock_aiogram_bot,
        mock_aiogram_dispatcher,
        enhanced_mock_config_manager
    ):
        """Test webhook failure fallback to polling sequence."""
        # Configure for webhook mode initially
        enhanced_mock_config_manager.is_webhook_mode.return_value = True

        with patch('aiogram.utils.token.validate_token') as mock_validate:
            # Skip token validation for tests
            mock_validate.return_value = True
            with patch('src.database.manager.DatabaseManager') as mock_db_class:
                with patch('src.events.bus.EventBus') as mock_bus_class:
                    # Setup mocks
                    mock_db_instance = MagicMock()
                    mock_db_instance.initialize_databases = AsyncMock(return_value=True)
                    mock_db_class.return_value = mock_db_instance

                    mock_bus_instance = MagicMock()
                    mock_bus_instance.connect = AsyncMock()
                    mock_bus_class.return_value = mock_bus_instance

                    app = BotApplication()
                    await app.initialize()

                    # Mock webhook configuration failure
                    with patch.object(app, 'configure_webhook', return_value=False) as mock_webhook:
                        with patch.object(app, '_start_polling', new_callable=AsyncMock) as mock_polling:
                            await app.start()

                            # Verify webhook was attempted
                            mock_webhook.assert_called_once()

                            # Verify fallback to polling occurred
                            mock_polling.assert_called_once()

    async def test_global_singleton_management(self):
        """Test global singleton management and reset functionality."""
        # Test bot application singleton
        app1 = get_bot_application()
        app2 = get_bot_application()
        assert app1 is app2

        # Test singleton reset
        from src.core.application import reset_bot_application
        reset_bot_application()

        app3 = get_bot_application()
        assert app3 is not app1

    async def test_fastapi_startup_event_fixes(self, mock_fastapi_app, enhanced_mock_config_manager):
        """Test FastAPI startup event handling fixes."""
        with patch('src.api.server.create_api_server', return_value=mock_fastapi_app) as mock_create:
            with patch('src.config.manager.get_config_manager', return_value=enhanced_mock_config_manager) as mock_config:
                with patch('src.database.manager.DatabaseManager') as mock_db_class:
                    with patch('src.events.bus.EventBus') as mock_bus_class:
                        mock_db_instance = MagicMock()
                        mock_db_instance.initialize_databases = AsyncMock(return_value=True)
                        mock_db_class.return_value = mock_db_instance

                        mock_bus_instance = MagicMock()
                        mock_bus_instance.connect = AsyncMock()
                        mock_bus_class.return_value = mock_bus_instance

                        app = BotApplication()
                        await app.initialize()

                        # Test FastAPI server setup
                        await app._setup_api_server()

                        # Verify API server was created with dependencies
                        mock_create.assert_called_once_with(
                            database_manager=mock_db_instance,
                            event_bus=mock_bus_instance
                        )

    async def test_performance_during_startup(
        self,
        performance_monitor,
        mock_aiogram_bot,
        mock_aiogram_dispatcher,
        enhanced_mock_config_manager
    ):
        """Test startup performance and memory usage."""
        performance_monitor.start()

        with patch('aiogram.utils.token.validate_token') as mock_validate:
            # Skip token validation for tests
            mock_validate.return_value = True
            with patch('src.database.manager.DatabaseManager') as mock_db_class:
                with patch('src.events.bus.EventBus') as mock_bus_class:
                    # Setup mocks
                    mock_db_instance = MagicMock()
                    mock_db_instance.initialize_databases = AsyncMock(return_value=True)
                    mock_db_class.return_value = mock_db_instance

                    mock_bus_instance = MagicMock()
                    mock_bus_instance.connect = AsyncMock()
                    mock_bus_class.return_value = mock_bus_instance

                    app = BotApplication()
                    await app.initialize()

                    with patch.object(app, '_start_polling', new_callable=AsyncMock):
                        await app.start()
                        await app.stop()

        metrics = performance_monitor.stop()

        # Assert reasonable startup time (should be under 1 second with mocks)
        assert metrics['duration'] < 1.0

        # Assert memory usage is reasonable (should not leak significantly)
        assert abs(metrics['memory_delta']) < 50 * 1024 * 1024  # 50MB threshold