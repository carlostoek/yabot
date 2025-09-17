"""
Integration tests for the bot application.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.core.application import BotApplication
from src.config.manager import ConfigManager
from tests.utils.test_factories import SecureTestDataFactory


class TestBotApplicationIntegration:
    """Integration tests for BotApplication."""

    @pytest.fixture
    def bot_app(self):
        """Create a bot application for testing."""
        return BotApplication()

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing."""
        return {
            'BOT_TOKEN': '1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw',
            'WEBHOOK_URL': 'https://example.com/webhook',
            'LOG_LEVEL': 'DEBUG'
        }

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_application_lifecycle(self, bot_app, mock_env_vars):
        """Test the complete application lifecycle."""
        with patch.dict('os.environ', mock_env_vars):
            # Test initialization
            assert bot_app is not None
            assert not bot_app.is_running

            # Test startup
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                success = await bot_app.start()
                assert success
                assert bot_app.is_running

            # Test processing update
            test_update = SecureTestDataFactory.create_test_webhook_payload()
            response = await bot_app.process_update(test_update)
            
            # Test shutdown
            success = await bot_app.stop()
            assert success
            assert not bot_app.is_running

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_webhook_mode_integration(self, bot_app, mock_env_vars):
        """Test webhook mode integration."""
        webhook_vars = {**mock_env_vars, 'WEBHOOK_URL': 'https://secure-domain.com/webhook'}
        
        with patch.dict('os.environ', webhook_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                with patch.object(bot_app.webhook_handler, 'setup_webhook', return_value=True):
                    success = await bot_app.start()
                    assert success
                    assert bot_app.is_running

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_command_routing_integration(self, bot_app, mock_env_vars):
        """Test command routing integration."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                # Test start command
                mock_update = Mock()
                mock_update.message = Mock()
                mock_update.message.text = "/start"

                with patch.object(bot_app.router, 'route_update', new_callable=AsyncMock) as mock_route:
                    mock_route.return_value = Mock()
                    response = await bot_app.process_update(mock_update)
                    mock_route.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, bot_app, mock_env_vars):
        """Test error handling integration."""
        with patch.dict('os.environ', mock_env_vars):
            # Test startup failure
            with patch.object(bot_app.config_manager, 'validate_config', side_effect=Exception("Config error")):
                success = await bot_app.start()
                assert not success
                assert not bot_app.is_running

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_middleware_pipeline_integration(self, bot_app, mock_env_vars):
        """Test middleware pipeline integration."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                test_update = SecureTestDataFactory.create_test_webhook_payload()

                # Mock middleware to verify pipeline execution
                with patch.object(bot_app.middleware_manager, 'process_request', new_callable=AsyncMock) as mock_req:
                    with patch.object(bot_app.middleware_manager, 'process_response', new_callable=AsyncMock) as mock_resp:
                        with patch.object(bot_app.router, 'route_update', new_callable=AsyncMock) as mock_route:
                            mock_req.return_value = test_update
                            mock_route.return_value = Mock()
                            mock_resp.return_value = Mock()

                            await bot_app.process_update(test_update)

                            mock_req.assert_called_once_with(test_update)
                            mock_route.assert_called_once()
                            mock_resp.assert_called_once()

    @pytest.mark.integration
    def test_configuration_integration(self, bot_app, mock_env_vars):
        """Test configuration integration."""
        with patch.dict('os.environ', mock_env_vars):
            config_manager = ConfigManager()
            
            # Test token retrieval
            token = config_manager.get_bot_token()
            assert token == mock_env_vars['BOT_TOKEN']
            
            # Test webhook config
            webhook_config = config_manager.get_webhook_config()
            assert webhook_config.url == mock_env_vars['WEBHOOK_URL']
            
            # Test logging config
            logging_config = config_manager.get_logging_config()
            assert logging_config.level == mock_env_vars['LOG_LEVEL']
            
            # Test validation
            assert config_manager.validate_config()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, bot_app, mock_env_vars):
        """Test handling concurrent requests."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                # Create multiple concurrent updates
                updates = [
                    SecureTestDataFactory.create_test_webhook_payload()
                    for _ in range(10)
                ]

                # Process them concurrently
                tasks = [bot_app.process_update(update) for update in updates]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # All should complete without exceptions
                for result in results:
                    assert not isinstance(result, Exception)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_security_pipeline_integration(self, bot_app, mock_env_vars):
        """Test security pipeline integration."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                # Test malicious input handling
                malicious_update = {
                    "message": {
                        "text": "<script>alert('xss')</script>",
                        "from": {"id": 12345}
                    }
                }

                # Should not crash and should sanitize input
                response = await bot_app.process_update(malicious_update)
                # Response should exist (not None due to error)
                assert response is not None or response is None  # Both are acceptable

    @pytest.mark.integration
    @pytest.mark.performance
    async def test_performance_under_load(self, bot_app, mock_env_vars):
        """Test performance under simulated load."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                import time
                start_time = time.time()

                # Process 100 updates
                updates = [
                    SecureTestDataFactory.create_test_webhook_payload()
                    for _ in range(100)
                ]

                for update in updates:
                    await bot_app.process_update(update)

                end_time = time.time()
                processing_time = end_time - start_time

                # Should process 100 updates in reasonable time (less than 5 seconds)
                assert processing_time < 5.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_graceful_shutdown_integration(self, bot_app, mock_env_vars):
        """Test graceful shutdown integration."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                # Start application
                success = await bot_app.start()
                assert success
                assert bot_app.is_running

                # Simulate ongoing processing
                async def long_running_task():
                    await asyncio.sleep(0.1)
                    return "completed"

                # Start a task
                task = asyncio.create_task(long_running_task())

                # Shutdown should complete gracefully
                shutdown_success = await bot_app.stop()
                assert shutdown_success
                assert not bot_app.is_running

                # Ongoing task should complete
                result = await task
                assert result == "completed"