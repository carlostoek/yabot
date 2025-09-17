"""
Performance tests for load testing and benchmarking.
"""

import pytest
import asyncio
import time
from unittest.mock import patch
from src.core.application import BotApplication
from tests.utils.test_factories import SecureTestDataFactory


class TestLoadPerformance:
    """Load performance tests."""

    @pytest.fixture
    def bot_app(self):
        """Create a bot application for testing."""
        return BotApplication()

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing."""
        return {
            'BOT_TOKEN': '1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw',
            'LOG_LEVEL': 'WARNING'  # Reduce logging for performance tests
        }

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_message_processing_throughput(self, bot_app, mock_env_vars):
        """Test message processing throughput."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                # Generate test messages
                messages = [
                    SecureTestDataFactory.create_test_webhook_payload()
                    for _ in range(1000)
                ]

                start_time = time.time()
                
                # Process messages
                for message in messages:
                    await bot_app.process_update(message)

                end_time = time.time()
                processing_time = end_time - start_time
                
                # Calculate throughput
                throughput = len(messages) / processing_time
                
                # Should process at least 100 messages per second
                assert throughput >= 100, f"Throughput {throughput:.2f} msg/s is below expected 100 msg/s"
                
                print(f"Throughput: {throughput:.2f} messages/second")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, bot_app, mock_env_vars):
        """Test concurrent message processing performance."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                # Generate test messages
                messages = [
                    SecureTestDataFactory.create_test_webhook_payload()
                    for _ in range(100)
                ]

                start_time = time.time()
                
                # Process messages concurrently
                tasks = [bot_app.process_update(message) for message in messages]
                await asyncio.gather(*tasks)

                end_time = time.time()
                processing_time = end_time - start_time
                
                # Concurrent processing should be faster than sequential
                assert processing_time < 2.0, f"Concurrent processing took {processing_time:.2f}s, expected < 2.0s"
                
                print(f"Concurrent processing time: {processing_time:.2f} seconds")

    @pytest.mark.performance
    @pytest.mark.benchmark
    def test_config_validation_performance(self, benchmark):
        """Benchmark configuration validation performance."""
        mock_env_vars = {
            'BOT_TOKEN': '1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw',
            'WEBHOOK_URL': 'https://example.com/webhook'
        }

        def validate_config():
            with patch.dict('os.environ', mock_env_vars):
                from src.config.manager import ConfigManager
                config_manager = ConfigManager()
                return config_manager.validate_config()

        result = benchmark(validate_config)
        assert result is True

    @pytest.mark.performance
    @pytest.mark.benchmark
    def test_input_sanitization_performance(self, benchmark):
        """Benchmark input sanitization performance."""
        from src.utils.validators import InputValidator
        
        malicious_input = "<script>alert('xss')</script>" * 100  # Large input
        
        def sanitize_input():
            return InputValidator.sanitize_html_input(malicious_input)

        result = benchmark(sanitize_input)
        assert "<script>" not in result

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, bot_app, mock_env_vars):
        """Test memory usage under sustained load."""
        import psutil
        import os
        
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                process = psutil.Process(os.getpid())
                initial_memory = process.memory_info().rss

                # Process many messages
                for i in range(500):
                    message = SecureTestDataFactory.create_test_webhook_payload()
                    await bot_app.process_update(message)
                    
                    # Check memory every 100 messages
                    if i % 100 == 0:
                        current_memory = process.memory_info().rss
                        memory_growth = current_memory - initial_memory
                        
                        # Memory growth should be reasonable (less than 50MB)
                        assert memory_growth < 50 * 1024 * 1024, f"Memory growth {memory_growth} bytes is excessive"

                final_memory = process.memory_info().rss
                memory_growth = final_memory - initial_memory
                
                print(f"Memory growth: {memory_growth / 1024 / 1024:.2f} MB")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self, bot_app, mock_env_vars):
        """Test rate limiting performance impact."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                user_id = "test_user_123"
                
                # Test without rate limiting
                start_time = time.time()
                for _ in range(50):
                    message = SecureTestDataFactory.create_test_webhook_payload()
                    await bot_app.process_update(message)
                no_rate_limit_time = time.time() - start_time

                # Test with rate limiting
                start_time = time.time()
                for _ in range(50):
                    # Check rate limit first
                    await bot_app.webhook_handler.check_rate_limit(user_id)
                    message = SecureTestDataFactory.create_test_webhook_payload()
                    await bot_app.process_update(message)
                rate_limit_time = time.time() - start_time

                # Rate limiting should not significantly impact performance (< 20% overhead)
                overhead = (rate_limit_time - no_rate_limit_time) / no_rate_limit_time
                assert overhead < 0.2, f"Rate limiting overhead {overhead:.2f} is too high"
                
                print(f"Rate limiting overhead: {overhead:.2%}")

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_long_running_stability(self, bot_app, mock_env_vars):
        """Test stability under long-running conditions."""
        with patch.dict('os.environ', mock_env_vars):
            with patch.object(bot_app.config_manager, 'validate_config', return_value=True):
                await bot_app.start()

                start_time = time.time()
                processed_count = 0
                error_count = 0

                # Run for 30 seconds
                while time.time() - start_time < 30:
                    try:
                        message = SecureTestDataFactory.create_test_webhook_payload()
                        await bot_app.process_update(message)
                        processed_count += 1
                    except Exception:
                        error_count += 1
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.01)

                # Should process messages with low error rate
                error_rate = error_count / (processed_count + error_count) if (processed_count + error_count) > 0 else 1
                assert error_rate < 0.05, f"Error rate {error_rate:.2%} is too high"
                
                print(f"Processed {processed_count} messages with {error_count} errors in 30 seconds")
                print(f"Error rate: {error_rate:.2%}")

    @pytest.mark.performance
    def test_startup_time_performance(self, benchmark, mock_env_vars):
        """Benchmark application startup time."""
        async def startup_app():
            with patch.dict('os.environ', mock_env_vars):
                app = BotApplication()
                with patch.object(app.config_manager, 'validate_config', return_value=True):
                    success = await app.start()
                    await app.stop()
                    return success

        def sync_startup():
            return asyncio.run(startup_app())

        result = benchmark(sync_startup)
        assert result is True