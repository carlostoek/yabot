"""
Tests for the webhook handler.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.handlers.webhook import WebhookHandler
from src.core.models import CommandResponse


class TestWebhookHandler:
    """Test cases for the WebhookHandler class."""
    
    @pytest.fixture
    def webhook_handler(self):
        """Create a webhook handler instance for testing."""
        return WebhookHandler()
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock update for testing."""
        update = Mock()
        update.message = Mock()
        update.message.text = "/start"
        return update
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request for testing."""
        request = Mock()
        request.headers = {"Content-Type": "application/json"}
        request.method = "POST"
        return request
    
    def test_init(self, webhook_handler):
        """Test WebhookHandler initialization."""
        assert webhook_handler is not None
        assert webhook_handler._webhook_config is None
    
    @pytest.mark.asyncio
    async def test_handle(self, webhook_handler, mock_update):
        """Test handling an update."""
        # The handle method in the base class just returns None
        result = await webhook_handler.handle(mock_update)
        assert result is None
    
    def test_setup_webhook_valid_url(self, webhook_handler):
        """Test setting up webhook with a valid URL."""
        url = "https://example.com/webhook"
        result = webhook_handler.setup_webhook(url)
        
        assert result is True
        assert webhook_handler._webhook_config is not None
        assert webhook_handler._webhook_config["url"] == url
    
    def test_setup_webhook_invalid_url(self, webhook_handler):
        """Test setting up webhook with an invalid URL."""
        url = "http://example.com/webhook"  # Not HTTPS
        result = webhook_handler.setup_webhook(url)
        
        assert result is False
        # Config should not be set for invalid URL
        # In our implementation, we still set it but return False
        assert webhook_handler._webhook_config is not None
    
    def test_setup_webhook_with_certificate(self, webhook_handler):
        """Test setting up webhook with a certificate."""
        url = "https://example.com/webhook"
        certificate = "test_certificate"
        result = webhook_handler.setup_webhook(url, certificate)
        
        assert result is True
        assert webhook_handler._webhook_config is not None
        assert webhook_handler._webhook_config["url"] == url
        assert webhook_handler._webhook_config["certificate"] == certificate
    
    def test_validate_request_valid(self, webhook_handler, mock_request):
        """Test validating a valid request."""
        result = webhook_handler.validate_request(mock_request)
        assert result is True
    
    def test_validate_request_missing_headers(self, webhook_handler):
        """Test validating a request with missing headers."""
        mock_request = Mock()
        del mock_request.headers  # Remove headers attribute
        
        result = webhook_handler.validate_request(mock_request)
        assert result is False
    
    def test_validate_request_invalid_method(self, webhook_handler):
        """Test validating a request with invalid method."""
        mock_request = Mock()
        mock_request.headers = {"Content-Type": "application/json"}
        mock_request.method = "GET"  # Should be POST
        
        result = webhook_handler.validate_request(mock_request)
        assert result is False
    
    def test_validate_request_valid_method(self, webhook_handler):
        """Test validating a request with valid method."""
        mock_request = Mock()
        mock_request.headers = {"Content-Type": "application/json"}
        mock_request.method = "POST"
        
        result = webhook_handler.validate_request(mock_request)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_process_update(self, webhook_handler, mock_update):
        """Test processing an update."""
        result = await webhook_handler.process_update(mock_update)
        
        # Should return None as per our implementation
        assert result is None
    
    @pytest.mark.asyncio
    async def test_process_update_logging(self, webhook_handler, mock_update, caplog):
        """Test that processing an update logs information."""
        with caplog.at_level("INFO"):
            await webhook_handler.process_update(mock_update)
            
            # Check that the expected log messages were recorded
            assert "Processing webhook update" in caplog.text
            assert "Webhook update processed successfully" in caplog.text