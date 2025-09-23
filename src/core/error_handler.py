"""
Error handler for the Telegram bot framework.
"""

from typing import Dict, Any, Optional
from src.utils.logger import get_logger
from src.utils.errors import get_user_friendly_message, log_error

# Import infrastructure error classes
from src.database.manager import DatabaseManager
from src.events.bus import EventBusError, EventPublishError, EventSubscribeError
from src.services.user import UserServiceError
from src.services.subscription import SubscriptionServiceError
from src.services.narrative import NarrativeServiceError
from src.services.coordinator import CoordinatorServiceError
import jwt

logger = get_logger(__name__)


class ErrorHandler:
    """Centralized error handling with user-friendly responses and comprehensive logging."""
    
    def __init__(self):
        """Initialize the error handler."""
        pass
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> str:
        """Process and respond to errors.
        
        Args:
            error (Exception): The error that occurred
            context (Dict[str, Any]): Context information about when/where the error occurred
            
        Returns:
            str: A user-friendly error message
        """
        # Log the error with context
        self.log_error(error, context)
        
        # Generate user-friendly message
        user_message = self.get_user_message(error)
        
        # Additional error-specific handling could be added here
        # For example, special handling for critical errors, retries for transient errors, etc.
        
        return user_message
    
    def log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Log error with context.
        
        Args:
            error (Exception): The error to log
            context (Dict[str, Any]): Context information about when/where the error occurred
        """
        log_error(error, context)
    
    def get_user_message(self, error: Exception) -> str:
        """Generate user-friendly error message.
        
        Args:
            error (Exception): The error to generate a message for
            
        Returns:
            str: A user-friendly error message
        """
        # Handle infrastructure-specific errors
        # NOTE: Order matters! Check specific exceptions before their parent classes
        if isinstance(error, (EventPublishError, EventSubscribeError)):
            return "Event processing error. The system is experiencing temporary issues."
        elif isinstance(error, EventBusError):
            return "System communication error. Please try again in a moment."
        elif isinstance(error, UserServiceError):
            return "User data processing error. Please try again."
        elif isinstance(error, SubscriptionServiceError):
            return "Subscription processing error. Please contact support if this continues."
        elif isinstance(error, NarrativeServiceError):
            return "Story content error. Please try a different option."
        elif isinstance(error, CoordinatorServiceError):
            return "System coordination error. Please try your request again."
        elif isinstance(error, jwt.ExpiredSignatureError):
            return "Authentication expired. Please refresh the page or log in again."
        elif isinstance(error, jwt.InvalidTokenError):
            return "Invalid authentication. Please log in again."
        
        # Fall back to existing error handling
        return get_user_friendly_message(error)