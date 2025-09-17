"""
Error handler for the Telegram bot framework.
"""

from typing import Dict, Any, Optional
from src.utils.logger import get_logger
from src.utils.errors import get_user_friendly_message, log_error

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
        return get_user_friendly_message(error)