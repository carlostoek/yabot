"""
Bot application for the Telegram bot framework.
"""

import asyncio
from typing import Any, Optional
from src.config.manager import ConfigManager
from src.core.router import Router
from src.core.middleware import MiddlewareManager
from src.core.error_handler import ErrorHandler
from src.handlers.commands import CommandHandler
from src.handlers.webhook import WebhookHandler
from src.utils.logger import get_logger, configure_logging

logger = get_logger(__name__)


class BotApplication:
    """Main application orchestrator that initializes and coordinates all components."""
    
    def __init__(self):
        """Initialize the bot application."""
        logger.info("Initializing bot application")
        
        # Initialize core components
        self.config_manager = ConfigManager()
        self.router = Router()
        self.middleware_manager = MiddlewareManager()
        self.error_handler = ErrorHandler()
        self.command_handler = CommandHandler()
        self.webhook_handler = WebhookHandler()
        
        # State tracking
        self._is_running = False
        self._is_webhook_enabled = False
        
        # Configure logging
        configure_logging(self.config_manager)
        
        logger.info("Bot application initialized successfully")
    
    async def start(self) -> bool:
        """Initialize bot and start receiving updates.
        
        Returns:
            bool: True if bot started successfully, False otherwise
        """
        logger.info("Starting bot application")
        
        try:
            # Validate configuration
            if not self.config_manager.validate_config():
                logger.error("Configuration validation failed")
                return False
            
            # Set up command handlers
            self._setup_command_handlers()
            
            # Configure update receiving mode (webhook or polling)
            if self._should_use_webhook():
                success = await self._setup_webhook_mode()
            else:
                success = await self._setup_polling_mode()
            
            if not success:
                logger.error("Failed to set up update receiving mode")
                return False
            
            self._is_running = True
            logger.info("Bot application started successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "start",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Failed to start bot application: %s", user_message)
            return False
    
    async def stop(self) -> bool:
        """Graceful shutdown with cleanup.
        
        Returns:
            bool: True if bot stopped successfully, False otherwise
        """
        logger.info("Stopping bot application")
        
        try:
            # Perform cleanup operations
            self._is_running = False
            
            # In a real implementation, we would:
            # 1. Stop receiving updates
            # 2. Close any open connections
            # 3. Save any pending state
            # 4. Clean up resources
            
            logger.info("Bot application stopped successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "stop",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error during bot shutdown: %s", user_message)
            return False
    
    def configure_webhook(self, url: str) -> bool:
        """Set up webhook mode.
        
        Args:
            url (str): The webhook URL
            
        Returns:
            bool: True if webhook configuration was successful, False otherwise
        """
        logger.info("Configuring webhook mode with URL: %s", url)
        
        try:
            # Get webhook configuration
            webhook_config = self.config_manager.get_webhook_config()
            
            # Set up the webhook
            success = self.webhook_handler.setup_webhook(
                url=url,
                certificate=webhook_config.certificate
            )
            
            if success:
                self._is_webhook_enabled = True
                logger.info("Webhook mode configured successfully")
            
            return success
            
        except Exception as e:
            error_context = {
                "operation": "configure_webhook",
                "component": "BotApplication",
                "url": url
            }
            user_message = self.error_handler.handle_error(e, error_context)
            logger.error("Failed to configure webhook: %s", user_message)
            return False
    
    def configure_polling(self) -> bool:
        """Set up polling mode.
        
        Returns:
            bool: True if polling configuration was successful, False otherwise
        """
        logger.info("Configuring polling mode")
        
        try:
            # In a real implementation, this would configure the bot
            # to use polling instead of webhooks
            
            self._is_webhook_enabled = False
            logger.info("Polling mode configured successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "configure_polling",
                "component": "BotApplication"
            }
            user_message = self.error_handler.handle_error(e, error_context)
            logger.error("Failed to configure polling: %s", user_message)
            return False
    
    def _setup_command_handlers(self) -> None:
        """Set up the command handlers with the router."""
        logger.debug("Setting up command handlers")
        
        # Register command handlers
        self.router.register_command_handler("start", self.command_handler.handle_start)
        self.router.register_command_handler("menu", self.command_handler.handle_menu)
        self.router.register_command_handler("help", self.command_handler.handle_help)
        self.router.set_default_handler(self.command_handler.handle_unknown)
        
        logger.debug("Command handlers set up successfully")
    
    def _should_use_webhook(self) -> bool:
        """Determine if webhook mode should be used.
        
        Returns:
            bool: True if webhook mode should be used, False for polling
        """
        # Check configuration
        webhook_config = self.config_manager.get_webhook_config()
        return bool(webhook_config.url)
    
    async def _setup_webhook_mode(self) -> bool:
        """Set up the bot to receive updates via webhook.
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        logger.info("Setting up webhook mode")
        
        try:
            # Get webhook configuration
            webhook_config = self.config_manager.get_webhook_config()
            
            # Configure webhook
            success = self.configure_webhook(webhook_config.url)
            
            if not success:
                logger.warning("Webhook setup failed, falling back to polling mode")
                return await self._setup_polling_mode()
            
            logger.info("Webhook mode set up successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "setup_webhook_mode",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up webhook mode: %s", user_message)
            # Fall back to polling mode
            logger.info("Falling back to polling mode")
            return await self._setup_polling_mode()
    
    async def _setup_polling_mode(self) -> bool:
        """Set up the bot to receive updates via polling.
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        logger.info("Setting up polling mode")
        
        try:
            # Configure polling
            success = self.configure_polling()
            
            if not success:
                logger.error("Failed to set up polling mode")
                return False
            
            logger.info("Polling mode set up successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "setup_polling_mode",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up polling mode: %s", user_message)
            return False
    
    async def process_update(self, update: Any) -> Optional[Any]:
        """Process an incoming update through the middleware and routing pipeline.
        
        Args:
            update (Any): The incoming update
            
        Returns:
            Optional[Any]: The response to the update
        """
        logger.debug("Processing incoming update")
        
        try:
            # Process through middleware
            processed_update = await self.middleware_manager.process_request(update)
            
            # Route to appropriate handler
            response = await self.router.route_update(processed_update)
            
            # Process response through middleware
            processed_response = await self.middleware_manager.process_response(response)
            
            logger.debug("Update processed successfully")
            return processed_response
            
        except Exception as e:
            error_context = {
                "operation": "process_update",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error processing update: %s", user_message)
            return None
    
    @property
    def is_running(self) -> bool:
        """Check if the bot is currently running.
        
        Returns:
            bool: True if the bot is running, False otherwise
        """
        return self._is_running
    
    @property
    def is_webhook_enabled(self) -> bool:
        """Check if webhook mode is enabled.
        
        Returns:
            bool: True if webhook mode is enabled, False otherwise
        """
        return self._is_webhook_enabled