"""
Core Bot Framework - Bot Application

This module serves as the main application orchestrator that initializes and coordinates 
all components of the bot. It implements the BotApplication component from the design document.
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import FastAPI

from src.core.router import setup_routers
from src.handlers.webhook import get_webhook_handler, WebhookHandler
from src.utils.logger import get_logger
from src.core.error_handler import ErrorHandler

# Delay import of config manager to avoid circular import
# It will be imported inside the methods where it's used


class BotApplication:
    """
    Main application orchestrator that initializes and coordinates all components.
    
    Implements the BotApplication component from the design document with interfaces:
    - start(): Initialize bot and start receiving updates
    - stop(): Graceful shutdown with cleanup
    - configure_webhook(url: str): Set up webhook mode
    - configure_polling(): Set up polling mode
    """
    
    def __init__(self):
        # Import here to avoid circular import
        from src.config.manager import get_config_manager
        self.config_manager = get_config_manager()
        self.logger = get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler()
        
        # Initialize bot components
        self.bot: Optional[Bot] = None
        self.dispatcher: Optional[Dispatcher] = None
        self.webhook_handler: Optional[WebhookHandler] = None
        self.fastapi_app: Optional[FastAPI] = None
        
        # Application state
        self.is_running = False
        
        # Validate configuration on initialization (Requirement 1.4)
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """
        Validate all required configuration parameters before beginning operation.
        
        Implements requirement 1.4: WHEN the bot starts THEN the system 
        SHALL validate all required configuration parameters before beginning operation
        """
        try:
            # Import config manager to avoid circular import
            from src.config.manager import get_config_manager
            config_manager = get_config_manager()
            config_valid = config_manager.validate_config()
            if not config_valid:
                raise ValueError("Configuration validation failed")
            
            self.logger.info("Configuration validated successfully")
            
        except Exception as e:
            self.logger.error(
                "Configuration validation failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def initialize(self) -> None:
        """
        Initialize the bot and all its components.
        
        Implements requirement 1.1: WHEN the bot is initialized THEN the system 
        SHALL establish a connection with Telegram API using a valid bot token
        """
        try:
            # Import config manager to avoid circular import
            from src.config.manager import get_config_manager
            config_manager = get_config_manager()
            
            # Initialize bot with token
            self.bot = Bot(
                token=config_manager.get_bot_token(),
                session=AiohttpSession()
            )
            
            # Initialize dispatcher
            self.dispatcher = Dispatcher()
            
            # Setup routers (command and message handlers)
            setup_routers(self.dispatcher)
            
            # Initialize webhook handler if needed
            if config_manager.get_webhook_config():
                self.webhook_handler = get_webhook_handler(self.bot, self.dispatcher)
            
            self.logger.info("Bot application initialized successfully")
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize bot application",
                error=str(e),
                error_type=type(e).__name__
            )
            # Requirement 1.2: log appropriate error and fail gracefully
            raise
    
    async def configure_webhook(self, url: Optional[str] = None) -> bool:
        """
        Configure webhook mode for receiving updates.
        
        Implements requirement 3.3: WHEN webhook configuration fails THEN the system 
        SHALL fallback to polling mode and log the webhook error
        
        Args:
            url: Optional URL for the webhook; if not provided, uses config value
            
        Returns:
            True if webhook was configured successfully, False otherwise
        """
        if not self.bot or not self.dispatcher:
            raise RuntimeError("Bot application not initialized")
        
        try:
            # Import config manager to avoid circular import
            from src.config.manager import get_config_manager
            config_manager = get_config_manager()
            
            webhook_config = config_manager.get_webhook_config()
            if not webhook_config or not url:
                # If no webhook config or URL provided, use default config
                if not url:
                    url = webhook_config.url if webhook_config else None
                if not url:
                    self.logger.warning("No webhook URL provided or configured")
                    return False
            
            # Use the webhook handler to set up the webhook
            if not self.webhook_handler:
                self.webhook_handler = get_webhook_handler(self.bot, self.dispatcher)
            
            success = await self.webhook_handler.setup_webhook(url, webhook_config.certificate if webhook_config else None)
            
            if success:
                self.logger.info(f"Webhook configured successfully for URL: {url}")
                return True
            else:
                # Requirement 3.3: fallback to polling mode
                self.logger.warning("Webhook configuration failed, will use polling mode")
                return False
                
        except Exception as e:
            self.logger.error(
                "Failed to configure webhook",
                error=str(e),
                error_type=type(e).__name__,
                url=url
            )
            # Requirement 3.3: fallback to polling mode and log error
            self.logger.warning("Webhook configuration failed, will use polling mode")
            return False
    
    async def configure_polling(self) -> bool:
        """
        Configure polling mode for receiving updates.
        
        Requirement 1.3: the bot SHALL support both polling and webhook modes
        """
        try:
            self.logger.info("Polling mode configured")
            return True
        except Exception as e:
            self.logger.error(
                "Failed to configure polling mode",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def start(self) -> None:
        """
        Start the bot application.
        
        Implements requirement 1.3: WHEN the bot is configured THEN the system 
        SHALL support both polling and webhook modes for receiving updates
        """
        if self.is_running:
            self.logger.warning("Bot application is already running")
            return
        
        if not self.bot or not self.dispatcher:
            raise RuntimeError("Bot application not initialized")
        
        try:
            # Import config manager to avoid circular import
            from src.config.manager import get_config_manager
            config_manager = get_config_manager()
            
            # Determine which mode to use based on configuration
            if config_manager.is_webhook_mode():
                # Try to configure webhook first
                webhook_config = config_manager.get_webhook_config()
                webhook_url = webhook_config.url if webhook_config else None
                webhook_success = await self.configure_webhook(webhook_url)
                
                if not webhook_success:
                    # Fallback to polling mode
                    await self.configure_polling()
                    self.logger.info("Starting bot in polling mode (webhook failed)")
                    await self._start_polling()
                else:
                    # Webhook configured, need to set up FastAPI to serve webhook
                    self.logger.info("Webhook configured, starting FastAPI server")
                    await self._start_webhook_server()
            else:
                # Use polling mode
                await self.configure_polling()
                self.logger.info("Starting bot in polling mode")
                await self._start_polling()
            
            self.is_running = True
            self.logger.info("Bot application started successfully")
            
        except Exception as e:
            self.logger.error(
                "Failed to start bot application",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def _start_polling(self) -> None:
        """
        Internal method to start polling mode.
        """
        try:
            # Start polling to receive updates
            await self.dispatcher.start_polling(self.bot)
        except Exception as e:
            self.logger.error(
                "Error during polling",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        finally:
            await self._cleanup()
    
    async def _start_webhook_server(self) -> None:
        """
        Internal method to start webhook server using FastAPI.
        """
        from fastapi import Request
        import uvicorn
        
        # Create FastAPI app
        self.fastapi_app = FastAPI(
            title="YABot Webhook",
            description="Webhook endpoint for YABot Telegram bot",
            version="1.0.0"
        )
        
        # Add webhook route
        @self.fastapi_app.post("/webhook")
        async def webhook_handler(request: Request):
            if not self.webhook_handler:
                return {"error": "Webhook handler not initialized"}
            
            return await self.webhook_handler.handle_webhook_request(request)
        
        # Add health check endpoint
        @self.fastapi_app.get("/health")
        async def health_check():
            return {"status": "healthy", "component": "bot"}
        
        # Start the server
        # In a real implementation, this would be handled by an external process
        # For now, we'll create a separate task to handle this
        config = uvicorn.Config(
            self.fastapi_app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        except Exception as e:
            self.logger.error(
                "Error in webhook server",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        finally:
            await self._cleanup()
    
    async def stop(self) -> None:
        """
        Stop the bot application and perform cleanup.
        
        Implements graceful shutdown with cleanup
        """
        if not self.is_running:
            self.logger.info("Bot application is not running")
            return
        
        try:
            await self._cleanup()
            self.is_running = False
            self.logger.info("Bot application stopped successfully")
        except Exception as e:
            self.logger.error(
                "Error during bot shutdown",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def _cleanup(self) -> None:
        """
        Perform cleanup operations.
        """
        # Close bot session
        if self.bot:
            await self.bot.session.close()
            self.bot = None
        
        # Perform any other cleanup operations
        self.logger.info("Cleanup completed")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the application.
        
        Returns:
            Dictionary with application status information
        """
        # Import config manager to avoid circular import
        from src.config.manager import get_config_manager
        config_manager = get_config_manager()
        
        return {
            "is_running": self.is_running,
            "bot_initialized": self.bot is not None,
            "webhook_configured": self.webhook_handler is not None,
            "mode": config_manager.get_mode(),
            "timestamp": self._get_current_timestamp()
        }
    
    def _get_current_timestamp(self) -> str:
        """
        Get current timestamp for logging purposes.
        """
        import datetime
        return datetime.datetime.now().isoformat()


# Global application instance
_bot_app = None


def get_bot_application() -> BotApplication:
    """
    Get or create the global bot application instance.
    
    Returns:
        BotApplication instance
    """
    global _bot_app
    if _bot_app is None:
        _bot_app = BotApplication()
    return _bot_app


def reset_bot_application():
    """
    Reset the global bot application instance (useful for testing).
    """
    global _bot_app
    _bot_app = None