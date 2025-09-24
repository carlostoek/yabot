"""
Core Bot Framework - Error Handling Utilities

This module provides comprehensive error handling for the application
with user-friendly messages and proper logging.
"""
from typing import Any, Dict, Optional
import traceback
import logging
from src.utils.logger import get_logger


# Custom exception classes
class BotError(Exception):
    """
    Base exception class for bot-related errors
    """
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = self._get_timestamp()
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context,
            'timestamp': self.timestamp
        }


class ConfigurationError(BotError):
    """
    Exception raised for configuration-related errors
    """
    pass


class ValidationError(BotError):
    """
    Exception raised for validation errors
    """
    pass


class TelegramAPIError(BotError):
    """
    Exception raised for Telegram API-related errors
    """
    pass


class MessageProcessingError(BotError):
    """
    Exception raised for message processing errors
    """
    pass


class WebhookError(BotError):
    """
    Exception raised for webhook-related errors
    """
    pass


class DatabaseError(BotError):
    """
    Exception raised for database-related errors
    """
    pass


class NetworkError(BotError):
    """
    Exception raised for network-related errors
    """
    pass


def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Handle an error by logging it and returning a structured error response
    
    Args:
        error: The exception that occurred
        context: Additional context information about the error
    
    Returns:
        A dictionary with error information
    """
    logger = get_logger(__name__)
    
    # Create a comprehensive error context
    error_context = context or {}
    error_context.update({
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc()
    })
    
    # Log the error with context
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=error_context
    )
    
    # Create the error response
    error_response = {
        'success': False,
        'error_type': type(error).__name__,
        'error_message': get_user_friendly_message(error),
        'timestamp': error_context.get('timestamp', '')
    }
    
    return error_response


def get_user_friendly_message(error: Exception) -> str:
    """
    Generate a user-friendly error message based on the exception type
    
    Args:
        error: The exception to generate a message for
    
    Returns:
        A user-friendly error message
    """
    error_type = type(error).__name__
    
    # Map exception types to user-friendly messages
    error_messages = {
        'ConfigurationError': 'Configuration error occurred. Please check the bot settings.',
        'ValidationError': 'Invalid input provided. Please check your input and try again.',
        'TelegramAPIError': 'Telegram API error occurred. Please try again later.',
        'MessageProcessingError': 'Error processing your message. Please try again.',
        'WebhookError': 'Webhook configuration error. Please contact the administrator.',
        'DatabaseError': 'Database error occurred. Please try again later.',
        'NetworkError': 'Network error occurred. Please check your connection.',
    }
    
    # Return specific message if available, otherwise generic message
    if error_type in error_messages:
        return error_messages[error_type]
    else:
        # For security, don't expose system details to users
        return 'An error occurred while processing your request. Please try again later.'


def log_error(error: Exception, context: Dict[str, Any]) -> None:
    """
    Log an error with context information
    
    Args:
        error: The exception to log
        context: Context information about where the error occurred
    """
    logger = get_logger(__name__)
    
    # Add error details to the context
    context['error_type'] = type(error).__name__
    context['error_message'] = str(error)
    context['traceback'] = traceback.format_exc()
    
    logger.error("System error", **context)


def create_error_response(error: Exception, user_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized error response for API endpoints
    
    Args:
        error: The exception that occurred
        user_message: Optional custom user message
    
    Returns:
        A dictionary with error information formatted for API responses
    """
    if user_message is None:
        user_message = get_user_friendly_message(error)
    
    return {
        'success': False,
        'error': {
            'type': type(error).__name__,
            'message': user_message,
            'code': getattr(error, 'error_code', 'UNKNOWN_ERROR')
        }
    }


def safe_execute(func, *args, **kwargs) -> Any:
    """
    Safely execute a function, catching and handling any exceptions
    
    Args:
        func: The function to execute
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        The result of the function, or None if an exception occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_error(e, {
            'function': func.__name__ if hasattr(func, '__name__') else str(func),
            'args': str(args),
            'kwargs': str(kwargs)
        })
        return None


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to retry a function on failure
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
    """
    import asyncio
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:  # Don't sleep on the last attempt
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    continue
            
            # If all attempts failed, log the error and raise the exception
            logger = get_logger(__name__)
            logger.error(
                f"Function {func.__name__} failed after {max_attempts} attempts",
                error=str(last_exception),
                function=func.__name__
            )
            raise last_exception
        
        return wrapper
    return decorator


class ErrorHandler:
    """
    Centralized error handler class for consistent error handling
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle an error using the centralized error handling logic
        
        Args:
            error: The exception that occurred
            context: Additional context information about the error
        
        Returns:
            A dictionary with error information
        """
        return handle_error(error, context)
    
    def log(self, error: Exception, context: Dict[str, Any]) -> None:
        """
        Log an error with context information
        
        Args:
            error: The exception to log
            context: Context information about where the error occurred
        """
        log_error(error, context)
    
    def get_user_message(self, error: Exception) -> str:
        """
        Get a user-friendly error message
        
        Args:
            error: The exception to generate a message for
        
        Returns:
            A user-friendly error message
        """
        return get_user_friendly_message(error)
    
    def create_response(self, error: Exception, user_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a standardized error response
        
        Args:
            error: The exception that occurred
            user_message: Optional custom user message
        
        Returns:
            A dictionary with error information formatted for API responses
        """
        return create_error_response(error, user_message)


# Global error handler instance
error_handler = ErrorHandler()