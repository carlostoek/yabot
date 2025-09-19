"""
Bot application for the Telegram bot framework.
"""

import asyncio
from typing import Any, Optional, Dict, Callable
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from src.config.manager import ConfigManager
from src.core.router import Router
from src.core.middleware import MiddlewareManager
from src.core.error_handler import ErrorHandler
from src.handlers.commands import CommandHandler
from src.handlers.telegram_commands import CommandHandler as TelegramCommandHandler
from src.handlers.webhook import WebhookHandler
from src.utils.logger import get_logger, configure_logging
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.services.user import UserService
from src.api.server import APIServer  # Added for API server initialization

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
        
        # Initialize database and event components (will be set up during start)
        self.database_manager: Optional[DatabaseManager] = None
        self.event_bus: Optional[EventBus] = None
        self.user_service: Optional[UserService] = None
        
        # Initialize API server (will be set up during start)
        self.api_server: Optional[APIServer] = None
        
        # Initialize handlers with database context
        self.command_handler = CommandHandler()
        self.telegram_command_handler = TelegramCommandHandler()
        self.webhook_handler = WebhookHandler()
        
        # Initialize Telegram bot components
        self.bot: Optional[Bot] = None
        self.dispatcher: Optional[Dispatcher] = None
        
        # State tracking
        self._is_running = False
        self._is_webhook_enabled = False
        self._polling_task: Optional[asyncio.Task] = None
        
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
            
            # Initialize Telegram bot
            bot_token = self.config_manager.get_bot_token()
            self.bot = Bot(
                token=bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            self.dispatcher = Dispatcher()
            
            # Set up database and event components
            await self._setup_database()
            await self._setup_event_bus()
            
            # Set up user service after database and event bus
            await self._setup_user_service()
            
            # Set up API server
            await self._setup_api_server()
            
            # Set up command handlers with database context
            self._setup_command_handlers()
            
            # Set up webhook handler with event bus context
            self._setup_webhook_handler()
            
            # Register Telegram command handlers
            self._register_telegram_handlers()
            
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
            # Stop polling if it's running
            if hasattr(self, '_polling_task') and self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
            
            # Stop dispatcher polling
            if self.dispatcher:
                await self.dispatcher.stop_polling()
            
            # Close bot session
            if self.bot:
                await self.bot.session.close()
            
            # Perform cleanup operations
            self._is_running = False
            
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
        
        # In the new implementation, polling is handled by aiogram
        # This method is kept for compatibility but doesn't need to do anything
        self._is_webhook_enabled = False
        logger.info("Polling mode configured successfully")
        return True
    
    def _setup_command_handlers(self) -> None:
        """Set up the command handlers with the router."""
        logger.debug("Setting up command handlers")
        
        # Reinitialize command handler with database context if available
        if self.user_service and self.event_bus:
            self.command_handler = CommandHandler(self.user_service, self.event_bus)
            self.telegram_command_handler = TelegramCommandHandler(self.user_service, self.event_bus)
        elif self.user_service:
            self.command_handler = CommandHandler(self.user_service)
            self.telegram_command_handler = TelegramCommandHandler(self.user_service)
        elif self.event_bus:
            self.command_handler = CommandHandler(event_bus=self.event_bus)
            self.telegram_command_handler = TelegramCommandHandler(event_bus=self.event_bus)
        else:
            self.command_handler = CommandHandler()
            self.telegram_command_handler = TelegramCommandHandler()
        
        # Register command handlers
        self.router.register_command_handler("start", self.command_handler.handle_start)
        self.router.register_command_handler("menu", self.command_handler.handle_menu)
        self.router.register_command_handler("help", self.command_handler.handle_help)
        self.router.set_default_handler(self.command_handler.handle_unknown)
        
        logger.debug("Command handlers set up successfully")
    
    def _register_telegram_handlers(self) -> None:
        """Register Telegram command handlers with the dispatcher."""
        logger.debug("Registering Telegram command handlers")
        
        if not self.dispatcher:
            logger.error("Dispatcher not initialized")
            return
        
        # Register command handlers
        async def start_handler(message: Any) -> None:
            try:
                response = await self.telegram_command_handler.handle_start(message)
                if response and self.bot:
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text=response.text,
                        parse_mode=response.parse_mode,
                        reply_markup=response.reply_markup,
                        disable_notification=response.disable_notification
                    )
            except Exception as e:
                logger.error("Error handling /start command: %s", str(e))
        
        # Register /menu command handler
        async def menu_handler(message: Any) -> None:
            try:
                response = await self.telegram_command_handler.handle_menu(message)
                if response and self.bot:
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text=response.text,
                        parse_mode=response.parse_mode,
                        reply_markup=response.reply_markup,
                        disable_notification=response.disable_notification
                    )
            except Exception as e:
                logger.error("Error handling /menu command: %s", str(e))
        
        # Register /help command handler
        async def help_handler(message: Any) -> None:
            try:
                response = await self.telegram_command_handler.handle_help(message)
                if response and self.bot:
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text=response.text,
                        parse_mode=response.parse_mode,
                        reply_markup=response.reply_markup,
                        disable_notification=response.disable_notification
                    )
            except Exception as e:
                logger.error("Error handling /help command: %s", str(e))
        
        # Register handlers with dispatcher
        self.dispatcher.message.register(start_handler, Command("start"))
        self.dispatcher.message.register(menu_handler, Command("menu"))
        self.dispatcher.message.register(help_handler, Command("help"))
        
        logger.debug("Telegram command handlers registered successfully")
    
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
    
    async def _setup_database(self) -> bool:
        """Initialize database connections as required by fase1 specification.
        
        Returns:
            bool: True if database setup was successful, False otherwise
        """
        logger.info("Setting up database connections")
        
        try:
            # Initialize database manager
            self.database_manager = DatabaseManager(self.config_manager)
            
            # Connect to all databases
            success = await self.database_manager.connect_all()
            
            if not success:
                logger.error("Failed to connect to databases")
                return False
            
            logger.info("Database connections set up successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "setup_database",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up database connections: %s", user_message)
            return False
    
    async def _setup_event_bus(self) -> bool:
        """Initialize event bus as required by fase1 specification.
        
        Returns:
            bool: True if event bus setup was successful, False otherwise
        """
        logger.info("Setting up event bus")
        
        try:
            # Initialize event bus
            self.event_bus = EventBus(self.config_manager)
            
            # Connect to Redis
            success = await self.event_bus.connect()
            
            if not success:
                logger.warning("Failed to connect to Redis, events will be queued locally")
            
            logger.info("Event bus set up successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "setup_event_bus",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up event bus: %s", user_message)
            return False
    
    async def _setup_user_service(self) -> bool:
        """Initialize user service after database and event bus are set up.
        
        Returns:
            bool: True if user service setup was successful, False otherwise
        """
        logger.info("Setting up user service")
        
        try:
            # Initialize user service with database manager and event bus
            if self.database_manager:
                self.user_service = UserService(self.database_manager, self.event_bus)
                logger.info("User service set up successfully")
                return True
            else:
                logger.error("Database manager not initialized, cannot set up user service")
                return False
                
        except Exception as e:
            error_context = {
                "operation": "setup_user_service",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up user service: %s", user_message)
            return False
        """Initialize event bus as required by fase1 specification.
        
        Returns:
            bool: True if event bus setup was successful, False otherwise
        """
        logger.info("Setting up event bus")
        
        try:
            # Initialize event bus
            self.event_bus = EventBus(self.config_manager)
            
            # Connect to Redis
            success = await self.event_bus.connect()
            
            if not success:
                logger.warning("Failed to connect to Redis, events will be queued locally")
            
            logger.info("Event bus set up successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "setup_event_bus",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up event bus: %s", user_message)
            return False
    
    async def _setup_api_server(self) -> bool:
        """Initialize API server as required by fase1 specification.
        
        Returns:
            bool: True if API server setup was successful, False otherwise
        """
        logger.info("Setting up API server")
        
        try:
            # Initialize API server
            self.api_server = APIServer(self.config_manager)
            
            # Register API endpoints
            self._register_api_endpoints()
            
            # In a real implementation, we would start the server in a separate task
            # For now, we'll just set it up and log that it's ready
            logger.info("API server set up successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "setup_api_server",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up API server: %s", user_message)
            return False
    
    def _register_api_endpoints(self) -> None:
        """Register API endpoints with the API server."""
        logger.debug("Registering API endpoints")
        
        try:
            # Import endpoint routers
            from src.api.endpoints.users import router as user_router
            from src.api.endpoints.narrative import router as narrative_router
            
            # Register routers with the API server
            if self.api_server:
                self.api_server.app.include_router(user_router)
                self.api_server.app.include_router(narrative_router)
                logger.debug("API endpoints registered successfully")
            else:
                logger.warning("API server not initialized, cannot register endpoints")
                
        except Exception as e:
            error_context = {
                "operation": "register_api_endpoints",
                "component": "BotApplication"
            }
            user_message = self.error_handler.handle_error(e, error_context)
            logger.error("Error registering API endpoints: %s", user_message)

    def _setup_webhook_handler(self) -> None:
        """Set up the webhook handler with event bus context."""
        logger.debug("Setting up webhook handler")
        
        # Reinitialize webhook handler with event bus context if available
        if self.event_bus:
            self.webhook_handler = WebhookHandler(event_bus=self.event_bus)
        
        logger.debug("Webhook handler set up successfully")
    
    async def _setup_polling_mode(self) -> bool:
        """Set up the bot to receive updates via polling.
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        logger.info("Setting up polling mode")
        
        try:
            # Start polling in a separate task
            if self.bot and self.dispatcher:
                logger.info("Starting Telegram bot polling")
                # Start polling in the background
                self._polling_task = asyncio.create_task(
                    self.dispatcher.start_polling(self.bot)
                )
                logger.info("Polling mode set up successfully")
                return True
            else:
                logger.error("Bot or dispatcher not initialized")
                return False
                
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