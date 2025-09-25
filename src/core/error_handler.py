"""
Core Bot Framework - Error Handler

This module provides centralized error handling with user-friendly responses
and comprehensive logging as specified in the requirements.
"""
from typing import Optional, Dict, Any
from aiogram import Router
from aiogram.types import Update
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramRetryAfter,  # For Throttled
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError
)
from src.utils.logger import get_logger
from src.utils.errors import (
    BotError,
    ConfigurationError,
    ValidationError,
    TelegramAPIError as BotTelegramAPIError,
    MessageProcessingError,
    WebhookError,
    DatabaseError,
    NetworkError as BotNetworkError,
    error_handler as global_error_handler
)
import asyncio
import traceback

# Infrastructure-specific error types
from src.events.bus import EventBusException, EventProcessingError
import redis.exceptions


class ErrorHandler:
    """
    Centralized error handler with user-friendly responses and comprehensive logging
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.retry_attempts = 3  # Default number of retry attempts
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and respond to errors
        
        Args:
            error: The exception that occurred
            context: Context information about where the error occurred
        
        Returns:
            A dictionary with error handling results
        """
        # Log the error with context
        await self.log_error(error, context)
        
        # Determine if this is a critical error that affects bot operation
        is_critical = self._is_critical_error(error)
        
        # Generate user-friendly message
        user_message = await self.get_user_message(error)
        
        # Prepare error response
        error_response = {
            'error_handled': True,
            'user_message': user_message,
            'error_type': type(error).__name__,
            'critical': is_critical,
            'timestamp': context.get('timestamp', self._get_timestamp())
        }
        
        # Attempt graceful recovery for non-critical errors
        if not is_critical:
            await self._attempt_graceful_recovery(error, context)
        
        return error_response
    
    async def log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """
        Log error with context
        
        Args:
            error: The exception to log
            context: Context information about where the error occurred
        """
        log_context = {
            **context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'component': context.get('component', 'unknown')
        }
        
        # Determine log level based on error type
        if self._is_critical_error(error):
            self.logger.critical("Critical infrastructure error occurred", **log_context)
        elif self._is_recoverable_error(error):
            self.logger.warning("Recoverable infrastructure error occurred", **log_context)
        else:
            # Check if this might be an infrastructure error
            error_type_name = type(error).__name__
            error_module = type(error).__module__
            
            # Log infrastructure errors with more detail
            if any(infra_error in error_type_name.lower() for infra_error in 
                   ['database', 'event', 'redis', 'sqlalchemy', 'connection']):
                self.logger.warning("Infrastructure error occurred", **log_context)
            else:
                self.logger.error("Error occurred", **log_context)
    
    async def get_user_message(self, error: Exception) -> str:
        """
        Generate user-friendly error message
        
        Args:
            error: The exception to generate a message for
            
        Returns:
            User-friendly error message
        """
        # Map specific error types to user-friendly messages
        error_type = type(error).__name__
        
        user_messages = {
            # Telegram-specific errors
            'TelegramBadRequest': "Sorry, I couldn't process your request. Please try again.",
            'TelegramForbiddenError': "It seems there's an issue with access. Please try again later.",
            'TelegramRetryAfter': "Too many requests. Please wait a moment before trying again.",
            'TelegramNetworkError': "Network error occurred. Please check your connection and try again.",
            
            # Custom bot errors
            'ConfigurationError': "Configuration error occurred. Please contact the administrator.",
            'ValidationError': "Invalid input provided. Please check your input and try again.",
            'MessageProcessingError': "Error processing your message. Please try again.",
            'WebhookError': "Webhook configuration issue. Please contact the administrator.",
            'DatabaseError': "Database error occurred. Please try again later.",
            
            # Infrastructure errors
            'EventBusException': "Event bus error occurred. Please try again later.",
            'EventProcessingError': "Error processing event. Please try again later.",
            'SQLAlchemyError': "Database error occurred. Please try again later.",
            'ConnectionError': "Connection error occurred. Please check your connection and try again later.",
            'redis.exceptions.ConnectionError': "Connection to event system failed. Please try again later.",
        }
        
        # Return specific message if available, otherwise generic message
        if error_type in user_messages:
            return user_messages[error_type]
        else:
            # For security, don't expose system details to users
            return "An error occurred while processing your request. Please try again later."
    
    def _is_critical_error(self, error: Exception) -> bool:
        """
        Determine if an error is critical and affects bot operation
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error is critical, False otherwise
        """
        critical_error_types = (
            ConfigurationError,
            DatabaseError,
            WebhookError,
            EventBusException,  # Critical: event bus failures affect system communication
            EventProcessingError,  # Critical: event processing failures affect business logic
            SQLAlchemyError,  # Critical: database failures affect data persistence
        )
        
        # Also consider TelegramAPIError critical if it's a configuration issue
        if isinstance(error, TelegramAPIError) and 'token' in str(error).lower():
            return True
            
        # Consider Redis connection errors critical as they affect event system
        if isinstance(error, redis.exceptions.ConnectionError):
            return True
            
        # Consider general ConnectionError critical for infrastructure
        if isinstance(error.__class__.__name__, 'ConnectionError') and not isinstance(error, TelegramNetworkError):
            return True
            
        return isinstance(error, critical_error_types)
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """
        Determine if an error is recoverable
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error is recoverable, False otherwise
        """
        recoverable_error_types = (
            TelegramRetryAfter,
            TelegramNetworkError,
            BotNetworkError,
            redis.exceptions.ConnectionError,  # Redis connection errors may be recoverable
        )
        
        # Also consider specific infrastructure errors recoverable
        error_type_name = type(error).__name__
        if error_type_name in ['EventBusException', 'EventProcessingError']:
            # Some event bus errors may be recoverable depending on context
            return True
        
        return isinstance(error, recoverable_error_types)
    
    async def _attempt_graceful_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Attempt graceful recovery from an error
        
        Args:
            error: The exception that occurred
            context: Context information about where the error occurred
            
        Returns:
            True if recovery was successful, False otherwise
        """
        error_type = type(error).__name__
        
        # Implement specific recovery strategies based on error type
        if isinstance(error, (TelegramNetworkError, BotNetworkError)):
            # For network errors, try to reconnect
            self.logger.info("Attempting network recovery")
            # In a real implementation, this would attempt to reconnect to services
            return True
        elif isinstance(error, (redis.exceptions.ConnectionError, EventBusException)):
            # For Redis/EventBus errors, try to reconnect to the event bus
            self.logger.info("Attempting event bus recovery")
            # In a real implementation, this would attempt to reconnect to Redis
            return True
        elif isinstance(error, EventProcessingError):
            # For event processing errors, log and continue
            self.logger.info("Handling event processing error, continuing operation")
            return True
        elif isinstance(error, TelegramRetryAfter):
            # For throttling, wait before continuing
            self.logger.info("Handling throttling by waiting")
            await asyncio.sleep(2)  # Wait 2 seconds before continuing
            return True
        elif isinstance(error, TelegramBadRequest):
            # For bad requests, no recovery is possible, but bot can continue operating
            self.logger.info("Bad request handled, bot can continue operating")
            return True
        elif isinstance(error, SQLAlchemyError):
            # For database errors, log and continue
            self.logger.info("Database error handled, bot can continue operating")
            return True
        else:
            # For other errors, we can't recover but the bot can continue
            self.logger.info("Error handled, bot can continue operating")
            return True
    
    async def handle_update_error(self, update: Optional[Update], error: Exception) -> bool:
        """
        Specifically handle errors that occur during update processing
        
        Args:
            update: The update that was being processed (may be None)
            error: The exception that occurred
            
        Returns:
            True if the error was handled successfully
        """
        context = {
            'component': 'update_processor',
            'update_type': type(update).__name__ if update else 'unknown',
            'update_id': getattr(update, 'update_id', 'unknown') if update else 'unknown',
        }
        
        # Handle the error
        error_response = await self.handle_error(error, context)
        
        # If we have a valid update and it's a message, try to respond to the user
        if update and hasattr(update, 'message') and update.message:
            try:
                await update.message.answer(error_response['user_message'])
            except Exception:
                # If we can't send a message to the user, log it but continue
                self.logger.error(
                    "Could not send error message to user",
                    original_error=str(error),
                    response_error=str(error_response)
                )
        
        return True
    
    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO format
        
        Returns:
            Formatted timestamp string
        """
        from datetime import datetime
        return datetime.now().isoformat()


class AiogramErrorHandler:
    """
    Error handler specifically designed for aiogram's error handling system
    """
    
    def __init__(self):
        self.error_handler = ErrorHandler()
        self.logger = get_logger(self.__class__.__name__)
    
    async def handle(self, exception: Exception) -> None:
        """
        Handle errors in the aiogram error handling system

        Args:
            exception: The exception that occurred
        """
        try:
            # Handle the error using our centralized error handler
            # We don't have access to the update in this context, so pass None
            await self.error_handler.handle_update_error(None, exception)
        except Exception as handler_error:
            # If the error handler itself fails, log it
            self.logger.error(
                "Error in error handler",
                original_error=str(exception),
                handler_error=str(handler_error),
                traceback=traceback.format_exc()
            )


# Global error handler instance
error_handler = ErrorHandler()
aiogram_error_handler = AiogramErrorHandler()


def setup_error_handlers(dp) -> None:
    """
    Setup error handlers for the dispatcher
    
    Args:
        dp: The aiogram Dispatcher instance
    """
    # Register the global error handler
    dp.errors.register(aiogram_error_handler.handle)
    
    logger = get_logger(__name__)
    logger.info("Error handlers registered with dispatcher")


# For backward compatibility and direct usage
def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to handle errors using the global error handler
    
    Args:
        error: The exception that occurred
        context: Optional context information
        
    Returns:
        Error handling result dictionary
    """
    ctx = context or {}
    import asyncio
    
    # If we're in an event loop, run the async method directly
    try:
        loop = asyncio.get_running_loop()
        # If we're in a loop, caller needs to await this separately
        # This is a limitation of this approach - for async functions,
        # clients need to use the error_handler directly
        pass
    except RuntimeError:
        # No event loop running, we can create one
        return asyncio.run(error_handler.handle_error(error, ctx))
    
    # Return the coroutine for the caller to await
    return error_handler.handle_error(error, ctx)