"""
Error handling utilities for the Telegram bot framework.
"""

import time
import asyncio
import traceback
from typing import Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BotError(Exception):
    """Base exception class for bot-related errors."""
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ConfigurationError(BotError):
    """Exception raised for configuration-related errors."""
    pass


class NetworkError(BotError):
    """Exception raised for network-related errors."""
    pass


class ValidationError(BotError):
    """Exception raised for validation-related errors."""
    pass


class RetryableError(BotError):
    """Exception raised for errors that can be retried."""
    pass


def get_user_friendly_message(error: Exception) -> str:
    """Generate a user-friendly error message based on the exception type.
    
    Args:
        error (Exception): The exception to generate a message for
        
    Returns:
        str: A user-friendly error message
    """
    if isinstance(error, ConfigurationError):
        return "Bot configuration error. Please contact the administrator."
    elif isinstance(error, NetworkError):
        return "Network connectivity issue. Please try again in a moment."
    elif isinstance(error, ValidationError):
        return "Invalid input provided. Please check your request and try again."
    elif isinstance(error, RetryableError):
        return "Temporary issue encountered. Please try again."
    else:
        # For unknown errors, provide a generic message
        return "An unexpected error occurred. Please try again or contact support."


async def retry_with_backoff(
    func,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
):
    """Execute a function with exponential backoff retry logic.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        max_retries (int): Maximum number of retry attempts
        base_delay (float): Base delay in seconds for exponential backoff
        max_delay (float): Maximum delay in seconds between retries
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
        
    Raises:
        Exception: If all retry attempts fail, the last exception is raised
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                # Calculate delay with exponential backoff and jitter
                delay = min(base_delay * (2 ** attempt), max_delay)
                # Add jitter to prevent thundering herd
                jitter = delay * 0.1 * (2 * (hash(str(e)) % 100) / 100 - 1)
                delay = max(0, delay + jitter)
                
                logger.warning(
                    "Attempt %d failed with error: %s. Retrying in %.2f seconds...",
                    attempt + 1, str(e), delay
                )
                
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "All %d attempts failed. Last error: %s",
                    max_retries + 1, str(e)
                )
    
    # If we get here, all retries failed
    raise last_exception


def log_error(error: Exception, context: Dict[str, Any]):
    """Log an error with context information.
    
    Args:
        error (Exception): The exception to log
        context (Dict[str, Any]): Context information about when/where the error occurred
    """
    logger.error(
        "Error occurred: %s",
        str(error),
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "traceback": traceback.format_exc()
        }
    )