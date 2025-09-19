"""
Tests for the enhanced ErrorHandler with infrastructure errors.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.core.error_handler import ErrorHandler
from src.events.bus import EventBusError, EventPublishError, EventSubscribeError
from src.services.user import UserServiceError
from src.services.subscription import SubscriptionServiceError
from src.services.narrative import NarrativeServiceError
from src.services.coordinator import CoordinatorServiceError
import jwt


class TestErrorHandler:
    """Test cases for the enhanced ErrorHandler."""
    
    @pytest.fixture
    def error_handler(self):
        """Create an ErrorHandler instance."""
        return ErrorHandler()
    
    def test_handle_event_publish_error(self, error_handler):
        """Test handling of EventPublishError."""
        error = EventPublishError("Test event publish error")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "Event processing error. The system is experiencing temporary issues."
    
    def test_handle_event_subscribe_error(self, error_handler):
        """Test handling of EventSubscribeError."""
        error = EventSubscribeError("Test event subscribe error")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "Event processing error. The system is experiencing temporary issues."
    
    def test_handle_event_bus_error(self, error_handler):
        """Test handling of EventBusError."""
        error = EventBusError("Test event bus error")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "System communication error. Please try again in a moment."
    
    def test_handle_user_service_error(self, error_handler):
        """Test handling of UserServiceError."""
        error = UserServiceError("Test user service error")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "User data processing error. Please try again."
    
    def test_handle_subscription_service_error(self, error_handler):
        """Test handling of SubscriptionServiceError."""
        error = SubscriptionServiceError("Test subscription service error")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "Subscription processing error. Please contact support if this continues."
    
    def test_handle_narrative_service_error(self, error_handler):
        """Test handling of NarrativeServiceError."""
        error = NarrativeServiceError("Test narrative service error")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "Story content error. Please try a different option."
    
    def test_handle_coordinator_service_error(self, error_handler):
        """Test handling of CoordinatorServiceError."""
        error = CoordinatorServiceError("Test coordinator service error")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "System coordination error. Please try your request again."
    
    def test_handle_jwt_expired_signature_error(self, error_handler):
        """Test handling of jwt.ExpiredSignatureError."""
        error = jwt.ExpiredSignatureError("Token has expired")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "Authentication expired. Please refresh the page or log in again."
    
    def test_handle_jwt_invalid_token_error(self, error_handler):
        """Test handling of jwt.InvalidTokenError."""
        error = jwt.InvalidTokenError("Invalid token")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        assert message == "Invalid authentication. Please log in again."
    
    def test_handle_unknown_error_fallback(self, error_handler):
        """Test that unknown errors fall back to existing error handling."""
        error = Exception("Unknown error")
        context = {"component": "test", "operation": "test_operation"}
        
        message = error_handler.get_user_message(error)
        # Should fall back to generic message from utils.errors
        assert message == "An unexpected error occurred. Please try again or contact support."
    
    @pytest.mark.asyncio
    async def test_handle_error_method(self, error_handler):
        """Test the main handle_error method."""
        error = UserServiceError("Test user service error")
        context = {"component": "test", "operation": "test_operation"}
        
        # Mock the log_error method to avoid actual logging
        with patch.object(error_handler, 'log_error'):
            message = await error_handler.handle_error(error, context)
            assert message == "User data processing error. Please try again."