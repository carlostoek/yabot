"""
Core Bot Framework - Webhook Handler

This module handles webhook endpoint for receiving Telegram updates with security validation.
It implements requirements 3.1, 3.2, 3.4, and 3.5 related to webhook integration.
"""
import hashlib
import hmac
import asyncio
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from aiogram import Bot, Dispatcher
from aiogram.types import Update
import logging

from src.utils.logger import get_logger
from src.core.models import WebhookUpdate
from src.core.error_handler import ErrorHandler


class WebhookHandler:
    """
    Handles webhook endpoint for receiving Telegram updates with security validation.
    
    Implements the WebhookHandler component from the design document with interfaces:
    - setup_webhook(url: str, certificate: Optional[str]): Configure webhook
    - validate_request(request: Request) -> bool: Validate incoming webhook requests
    - process_update(update: Update): Process received updates
    """
    
    def __init__(self, bot: Bot, dispatcher: Dispatcher):
        self.bot = bot
        self.dispatcher = dispatcher
        # Import config manager here to avoid circular import
        from src.config.manager import get_config_manager
        self.config_manager = get_config_manager()
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler()
        
        # Get webhook configuration
        self.webhook_config = self.config_manager.get_webhook_config()
        
    async def setup_webhook(self, url: str, certificate: Optional[str] = None) -> bool:
        """
        Configure webhook with Telegram API.
        
        Implements requirement 3.1: WHEN webhook mode is enabled THEN the system 
        SHALL configure a secure HTTPS endpoint for receiving Telegram updates
        
        Args:
            url: The webhook URL to register with Telegram
            certificate: Optional certificate file path for self-signed certificates
            
        Returns:
            True if webhook was set successfully, False otherwise
        """
        try:
            # Set webhook with Telegram API
            await self.bot.set_webhook(
                url=url,
                certificate=open(certificate, 'rb') if certificate else None,
                max_connections=self.webhook_config.max_connections if self.webhook_config else 40,
                allowed_updates=self.webhook_config.allowed_updates if self.webhook_config else []
            )
            
            self.logger.info(f"Webhook set successfully for URL: {url}")
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to set webhook",
                error=str(e),
                error_type=type(e).__name__,
                url=url
            )
            # Requirement 3.3: WHEN webhook configuration fails THEN the system 
            # SHALL fallback to polling mode and log the webhook error
            self.logger.warning("Webhook configuration failed, falling back to polling mode")
            return False
    
    async def validate_request(self, request: Request) -> bool:
        """
        Validate incoming webhook requests for security.
        
        Implements requirement 3.4: WHEN the webhook endpoint receives invalid 
        requests THEN the system SHALL reject them and log security warnings
        
        Args:
            request: The incoming webhook request
            
        Returns:
            True if request is valid, False otherwise
        """
        try:
            # Get content and headers
            body = await request.body()
            
            # Verify if we have a secret token configured
            if self.webhook_config and self.webhook_config.secret_token:
                # Use secret token for validation if available
                secret_token = self.webhook_config.secret_token
                expected_signature = hmac.new(
                    secret_token.encode(),
                    body,
                    hashlib.sha256
                ).hexdigest()
                
                actual_signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
                
                if not actual_signature or not hmac.compare_digest(expected_signature, actual_signature):
                    self.logger.warning(
                        "Webhook request validation failed: invalid signature",
                        remote_addr=request.client.host if request.client else "unknown"
                    )
                    return False
            else:
                # If no secret token, at least check that the request is coming with proper headers
                content_type = request.headers.get('content-type')
                if content_type != 'application/json':
                    self.logger.warning(
                        "Webhook request validation failed: invalid content type",
                        content_type=content_type
                    )
                    return False
            
            # Additional security checks can be added here
            # For example, IP address validation if IP restriction is configured
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Error during webhook request validation",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def process_update(self, raw_update: Dict[str, Any]) -> bool:
        """
        Process received updates asynchronously without blocking other requests.
        
        Implements requirement 3.2: WHEN a webhook receives an update THEN the system 
        SHALL process it asynchronously without blocking other requests
        
        Args:
            raw_update: The raw update dictionary from Telegram
            
        Returns:
            True if update was processed successfully, False otherwise
        """
        try:
            # Create an Update object from the raw data
            update = Update(**raw_update)
            
            # Log the update for monitoring
            self.logger.debug(
                "Processing webhook update",
                update_id=update.update_id,
                update_type=self._get_update_type(update)
            )
            
            # Process the update through the dispatcher asynchronously
            # This allows for parallel processing of updates
            await self.dispatcher.feed_update(self.bot, update)
            
            self.logger.debug(
                "Successfully processed webhook update",
                update_id=update.update_id
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Error processing webhook update",
                error=str(e),
                error_type=type(e).__name__,
                raw_update=str(raw_update)[:500]  # Log first 500 chars of raw update
            )
            
            # Handle the error appropriately
            self.error_handler.handle_error(e, {
                'update': raw_update,
                'error': str(e),
                'error_type': type(e).__name__
            })
            
            return False
    
    def _get_update_type(self, update: Update) -> str:
        """
        Determine the type of update for logging purposes.
        
        Args:
            update: The update object
            
        Returns:
            String representing the update type
        """
        if update.message:
            return "message"
        elif update.edited_message:
            return "edited_message"
        elif update.channel_post:
            return "channel_post"
        elif update.edited_channel_post:
            return "edited_channel_post"
        elif update.inline_query:
            return "inline_query"
        elif update.chosen_inline_result:
            return "chosen_inline_result"
        elif update.callback_query:
            return "callback_query"
        elif update.shipping_query:
            return "shipping_query"
        elif update.pre_checkout_query:
            return "pre_checkout_query"
        elif update.poll:
            return "poll"
        elif update.poll_answer:
            return "poll_answer"
        elif update.my_chat_member:
            return "my_chat_member"
        elif update.chat_member:
            return "chat_member"
        elif update.chat_join_request:
            return "chat_join_request"
        else:
            return "unknown"
    
    async def handle_webhook_request(self, request: Request) -> Dict[str, Any]:
        """
        Complete handler for webhook requests - validates and processes updates.
        
        Args:
            request: The incoming webhook request from FastAPI
            
        Returns:
            Response dictionary indicating success or failure
        """
        # Validate the request
        if not await self.validate_request(request):
            # Requirement 3.4: log security warnings for invalid requests
            self.logger.warning(
                "Invalid webhook request rejected",
                remote_addr=request.client.host if request.client else "unknown"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Request validation failed"
            )
        
        try:
            # Read the request body
            body = await request.body()
            # Parse the JSON update data
            import json
            raw_update = json.loads(body.decode('utf-8'))
            
            # Process the update asynchronously
            success = await self.process_update(raw_update)
            
            if success:
                self.logger.info(
                    "Webhook update processed successfully",
                    update_id=raw_update.get('update_id', 'unknown')
                )
                return {"status": "success", "processed": True}
            else:
                self.logger.warning(
                    "Webhook update processing failed",
                    update_id=raw_update.get('update_id', 'unknown')
                )
                return {"status": "error", "processed": False}
                
        except json.JSONDecodeError as e:
            self.logger.error(
                "Invalid JSON in webhook request",
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Invalid JSON"
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error in webhook handler",
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error"
            )


# Global webhook handler instance
_webhook_handler = None


def get_webhook_handler(bot: Bot, dispatcher: Dispatcher) -> WebhookHandler:
    """
    Get or create the global webhook handler instance.
    
    Args:
        bot: The aiogram Bot instance
        dispatcher: The aiogram Dispatcher instance
        
    Returns:
        WebhookHandler instance
    """
    global _webhook_handler
    if _webhook_handler is None:
        _webhook_handler = WebhookHandler(bot, dispatcher)
    return _webhook_handler


def reset_webhook_handler():
    """
    Reset the global webhook handler instance (useful for testing).
    """
    global _webhook_handler
    _webhook_handler = None