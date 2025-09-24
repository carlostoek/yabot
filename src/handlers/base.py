"""
Core Bot Framework - Base Handler Class

This module provides a base handler class that can be extended by specific handlers.
The base handler includes common functionality for logging, error handling, and 
response formatting that can be leveraged by command and message handlers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Awaitable, Callable
from aiogram import Router
from aiogram.types import Message, CallbackQuery, Update
from aiogram.fsm.context import FSMContext

from src.utils.logger import get_logger
from src.core.models import CommandResponse, MessageContext
from src.core.error_handler import ErrorHandler


class BaseHandler(ABC):
    """
    Base handler class that provides common functionality for all handlers.
    
    This class serves as the foundation for all specific handlers in the bot,
    providing common utilities like logging, error handling, and response formatting.
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler()
        
    async def handle_message(self, message: Message, **kwargs) -> None:
        """
        General message handling method that can be overridden by subclasses.
        
        Args:
            message: The incoming message object
            **kwargs: Additional arguments that may be passed by handlers
        """
        self.logger.debug(
            "Processing message",
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
        
        try:
            # Create message context
            message_context = MessageContext(
                message_id=message.message_id,
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                message_type=message.content_type if hasattr(message, 'content_type') else 'unknown',
                content=getattr(message, 'text', ''),
                timestamp=str(message.date)
            )
            
            # Pre-processing
            processed_context = await self.pre_process_message(message_context, message, **kwargs)
            
            # Handle the specific message in subclasses
            result = await self.process_message(message, processed_context, **kwargs)
            
            # Post-processing
            await self.post_process_message(result, message, processed_context, **kwargs)
            
        except Exception as e:
            self.logger.error(
                "Error processing message",
                error=str(e),
                error_type=type(e).__name__,
                user_id=message.from_user.id,
                chat_id=message.chat.id
            )
            await self.handle_error(e, message, **kwargs)
    
    async def handle_callback_query(self, callback_query: CallbackQuery, **kwargs) -> None:
        """
        General callback query handling method that can be overridden by subclasses.
        
        Args:
            callback_query: The incoming callback query object
            **kwargs: Additional arguments that may be passed by handlers
        """
        self.logger.debug(
            "Processing callback query",
            user_id=callback_query.from_user.id,
            data=callback_query.data
        )
        
        try:
            # Handle the specific callback in subclasses
            await self.process_callback_query(callback_query, **kwargs)
            
        except Exception as e:
            self.logger.error(
                "Error processing callback query",
                error=str(e),
                error_type=type(e).__name__,
                user_id=callback_query.from_user.id,
                data=callback_query.data
            )
            await self.handle_error(e, callback_query, **kwargs)
    
    async def pre_process_message(self, context: MessageContext, message: Message, **kwargs) -> MessageContext:
        """
        Pre-process the incoming message before handling.
        
        This method can be overridden by subclasses to implement custom preprocessing logic.
        
        Args:
            context: The message context
            message: The incoming message object
            **kwargs: Additional arguments
            
        Returns:
            Processed message context
        """
        # Default implementation returns the same context
        return context
    
    async def post_process_message(self, result: Any, message: Message, context: MessageContext, **kwargs) -> None:
        """
        Post-process the message after handling.
        
        This method can be overridden by subclasses to implement custom postprocessing logic.
        
        Args:
            result: The result from the message processing
            message: The incoming message object
            context: The message context
            **kwargs: Additional arguments
        """
        # Default implementation does nothing
        pass
    
    @abstractmethod
    async def process_message(self, message: Message, context: MessageContext, **kwargs) -> Any:
        """
        Abstract method to process an incoming message.
        
        This method must be implemented by subclasses to handle specific message types.
        
        Args:
            message: The incoming message object
            context: The message context
            **kwargs: Additional arguments
            
        Returns:
            Result of processing the message
        """
        pass
    
    async def process_callback_query(self, callback_query: CallbackQuery, **kwargs) -> None:
        """
        Process a callback query.
        
        This method can be overridden by subclasses to handle specific callback queries.
        
        Args:
            callback_query: The incoming callback query object
            **kwargs: Additional arguments
        """
        # Default implementation does nothing
        pass
    
    async def handle_error(self, error: Exception, message: Optional[Message] = None, 
                          callback_query: Optional[CallbackQuery] = None, **kwargs) -> None:
        """
        Handle an error that occurred during message processing.
        
        Args:
            error: The exception that was raised
            message: The message object, if available
            callback_query: The callback query object, if available
            **kwargs: Additional arguments
        """
        user_id = None
        chat_id = None
        
        if message:
            user_id = message.from_user.id
            chat_id = message.chat.id
        elif callback_query:
            user_id = callback_query.from_user.id
            chat_id = callback_query.message.chat.id if callback_query.message else None
        
        # Let the error handler process the error
        error_response = self.error_handler.handle_error(error, {
            'user_id': user_id,
            'chat_id': chat_id,
            'message': str(message) if message else str(callback_query),
            **kwargs
        })
        
        # Send user-friendly error message to the user if possible
        if message:
            try:
                await message.answer(error_response.get_user_message(error))
            except Exception as send_error:
                self.logger.error(
                    "Failed to send error message to user",
                    send_error=str(send_error),
                    original_error=str(error)
                )
        elif callback_query:
            try:
                await callback_query.answer(error_response.get_user_message(error), show_alert=True)
            except Exception as send_error:
                self.logger.error(
                    "Failed to send error message to user for callback",
                    send_error=str(send_error),
                    original_error=str(error)
                )
    
    async def send_response(self, message: Message, response: CommandResponse) -> None:
        """
        Send a formatted response to the user.
        
        Args:
            message: The message object to reply to
            response: The CommandResponse object containing the response data
        """
        try:
            await message.answer(
                text=response.text,
                parse_mode=response.parse_mode,
                reply_markup=response.reply_markup,
                disable_notification=response.disable_notification
            )
        except Exception as e:
            self.logger.error(
                "Failed to send response",
                error=str(e),
                error_type=type(e).__name__,
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                response_text=response.text[:100]  # Log first 100 chars of response
            )
            raise
    
    def create_response(self, text: str, parse_mode: Optional[str] = "HTML", 
                       reply_markup: Optional[dict] = None, 
                       disable_notification: bool = False) -> CommandResponse:
        """
        Create a formatted response object.
        
        Args:
            text: The response text
            parse_mode: The parse mode for formatting (HTML, Markdown, etc.)
            reply_markup: Keyboard markup for the response
            disable_notification: Whether to disable notification for this response
            
        Returns:
            A CommandResponse object with the provided data
        """
        return CommandResponse(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_notification=disable_notification
        )


class MessageHandlerMixin:
    """
    Mixin class that provides additional functionality for message handlers.
    
    This mixin can be used along with BaseHandler to provide common message handling utilities.
    """
    
    async def validate_message_content(self, message: Message) -> bool:
        """
        Validate that the message contains acceptable content.
        
        Args:
            message: The message to validate
            
        Returns:
            True if content is valid, False otherwise
        """
        # Check if message has text content
        if not hasattr(message, 'text') or not message.text:
            self.logger.warning(
                "Message has no text content",
                message_id=message.message_id,
                user_id=message.from_user.id
            )
            return False
        
        # Additional validation can be added here
        return True
    
    async def sanitize_input(self, text: str) -> str:
        """
        Sanitize user input to prevent injection attacks.
        
        Args:
            text: The input text to sanitize
            
        Returns:
            Sanitized input text
        """
        # Basic sanitization - remove potentially harmful characters
        # In a real implementation, you'd want more sophisticated sanitization
        sanitized = text.strip()
        return sanitized


class CallbackHandlerMixin:
    """
    Mixin class that provides additional functionality for callback query handlers.
    
    This mixin can be used along with BaseHandler to provide common callback handling utilities.
    """
    
    async def validate_callback_data(self, callback_query: CallbackQuery) -> bool:
        """
        Validate the callback query data.
        
        Args:
            callback_query: The callback query to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        if not callback_query.data:
            self.logger.warning(
                "Callback query has no data",
                user_id=callback_query.from_user.id
            )
            return False
        
        return True