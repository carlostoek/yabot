"""
Security tests for authentication and authorization.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.config.manager import ConfigManager
from src.handlers.webhook import WebhookHandler


class TestAuthSecurity:
    """Test authentication and authorization security."""

    @pytest.fixture
    def config_manager(self):
        """Create a config manager for testing."""
        return ConfigManager()

    @pytest.fixture
    def webhook_handler(self):
        """Create a webhook handler for testing."""
        return WebhookHandler()

    @pytest.mark.security
    def test_bot_token_not_exposed_in_logs(self, config_manager):
        """Test that bot token is not exposed in logs."""
        with patch('src.utils.logger.get_logger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            token = "fake_bot_token_123456789"
            with patch.object(config_manager, 'get_bot_token', return_value=token):
                config_manager.validate_config()
            
            # Check that token is not in any log calls
            for call in mock_log.info.call_args_list:
                assert token not in str(call)
            for call in mock_log.debug.call_args_list:
                assert token not in str(call)

    @pytest.mark.security
    def test_webhook_url_validation(self, webhook_handler):
        """Test webhook URL validation."""
        # Test invalid URLs
        invalid_urls = [
            "http://example.com",  # Not HTTPS
            "https://localhost",   # Localhost not allowed
            "https://127.0.0.1",   # Local IP not allowed
            "https://192.168.1.1", # Private IP not allowed
            "not_a_url",          # Invalid format
            "",                   # Empty string
            None,                 # None value
        ]
        
        for url in invalid_urls:
            result = webhook_handler.validate_webhook_url(url)
            assert result is False, f"URL {url} should be invalid"

    @pytest.mark.security
    def test_webhook_request_validation(self, webhook_handler):
        """Test webhook request validation."""
        # Mock request with missing token
        mock_request = Mock()
        mock_request.headers = {}
        
        result = webhook_handler.validate_request(mock_request)
        assert result is False

    @pytest.mark.security
    def test_secure_headers_present(self, webhook_handler):
        """Test that security headers are present in webhook responses."""
        mock_response = Mock()
        mock_response.headers = {}
        
        webhook_handler.add_security_headers(mock_response)
        
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]
        
        for header in expected_headers:
            assert header in mock_response.headers

    @pytest.mark.security
    async def test_rate_limiting_protection(self, webhook_handler):
        """Test rate limiting protection."""
        user_id = "test_user_123"
        
        # Simulate multiple rapid requests
        for i in range(15):  # Exceed rate limit
            result = await webhook_handler.check_rate_limit(user_id)
            if i < 10:  # First 10 should pass
                assert result is True
            else:  # Rest should be blocked
                assert result is False

    @pytest.mark.security
    def test_input_sanitization(self, webhook_handler):
        """Test input sanitization for XSS prevention."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
        ]
        
        for malicious_input in malicious_inputs:
            sanitized = webhook_handler.sanitize_input(malicious_input)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "onerror=" not in sanitized
            assert "DROP TABLE" not in sanitized
            assert "../" not in sanitized

    @pytest.mark.security
    def test_bot_token_format_validation(self, config_manager):
        """Test bot token format validation."""
        invalid_tokens = [
            "",                    # Empty
            "short",              # Too short
            "123456789",          # Numbers only
            "abcdefghij",         # Letters only
            "123:abc",            # Wrong format
            None,                 # None
        ]
        
        for token in invalid_tokens:
            with patch.dict('os.environ', {'BOT_TOKEN': str(token) if token else ''}):
                assert not config_manager.validate_bot_token()

    @pytest.mark.security
    async def test_webhook_signature_validation(self, webhook_handler):
        """Test webhook signature validation."""
        payload = b'{"test": "data"}'
        secret = "webhook_secret_key"
        
        # Generate valid signature
        valid_signature = webhook_handler.generate_signature(payload, secret)
        
        # Test valid signature
        assert webhook_handler.validate_signature(payload, valid_signature, secret)
        
        # Test invalid signature
        invalid_signature = "invalid_signature"
        assert not webhook_handler.validate_signature(payload, invalid_signature, secret)
        
        # Test tampered payload
        tampered_payload = b'{"test": "modified_data"}'
        assert not webhook_handler.validate_signature(tampered_payload, valid_signature, secret)

    @pytest.mark.security
    def test_environment_variable_exposure(self):
        """Test that environment variables are not exposed."""
        sensitive_vars = [
            'BOT_TOKEN',
            'WEBHOOK_SECRET',
            'DATABASE_URL',
            'API_KEY',
            'SECRET_KEY'
        ]
        
        # Mock a function that might accidentally expose env vars
        def potentially_unsafe_function():
            import os
            return str(os.environ)
        
        result = potentially_unsafe_function()
        
        # In a real scenario, we'd check that these aren't logged or returned
        # This is a placeholder test - in practice you'd check logs, responses, etc.
        for var in sensitive_vars:
            # This would be implemented based on your specific logging/response system
            pass

    @pytest.mark.security
    async def test_command_injection_prevention(self, webhook_handler):
        """Test prevention of command injection attacks."""
        malicious_commands = [
            "; cat /etc/passwd",
            "| whoami",
            "&& rm -rf /",
            "`id`",
            "$(uname -a)",
        ]
        
        for command in malicious_commands:
            # Test that command injection is prevented
            result = await webhook_handler.process_user_input(command)
            
            # Should not execute system commands
            assert "root:" not in str(result)  # /etc/passwd content
            assert "uid=" not in str(result)   # id command output
            assert "Linux" not in str(result)  # uname output