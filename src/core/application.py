"""
Bot application for the Telegram bot framework.
"""

import asyncio
import sys
from datetime import datetime
from typing import Any, Optional, Dict, Callable
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from src.config.manager import ConfigManager
from src.core.router import Router
from src.core.middleware import MiddlewareManager
from src.core.error_handler import ErrorHandler
from src.handlers.telegram_commands import CommandHandler
from src.handlers.webhook import WebhookHandler
from src.handlers.menu_router import MenuIntegrationRouter
from src.handlers.menu_system import MenuSystemCoordinator
from src.utils.logger import get_logger, configure_logging
from src.database.manager import DatabaseManager
from src.events.bus import EventBus
from src.services.user import UserService
from src.utils.cache_manager import CacheManager
from src.api.server import APIServer  # Added for API server initialization
from src.shared.registry.module_registry import ModuleRegistry, ModuleState, ModuleHealthStatus

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
        self.module_registry: Optional[ModuleRegistry] = None
        self.cache_manager: Optional[CacheManager] = None
        
        # Initialize API server (will be set up during start)
        self.api_server: Optional[APIServer] = None
        
        # Initialize handlers with database context
        self.command_handler = CommandHandler()
        self.webhook_handler = WebhookHandler()
        self.menu_router: Optional[MenuIntegrationRouter] = None
        self.menu_system_coordinator: Optional[MenuSystemCoordinator] = None
        
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

            # Set up cache manager
            await self._setup_cache_manager()

            # Set up module registry after event bus is initialized
            await self._setup_module_registry()

            # Register core services with the module registry
            await self._register_core_services()

            # Set up user service after database and event bus
            await self._setup_user_service()
            
            # Set up menu router and system coordinator
            await self._setup_menu_router()

            # Verify menu system initialization
            if self.menu_system_coordinator:
                health = await self.menu_system_coordinator.get_system_health()
                health_score = health.get('overall_health_score', 0)
                logger.info(f"Menu system initialized with health score: {health_score:.1f}/100")

                if health_score < 80:
                    logger.warning("Menu system health score below optimal threshold")
                    await self._log_component_health_issues()
            else:
                logger.warning("Menu system coordinator not initialized")
            
            # Initialize emotional intelligence system
            emotional_success = await self.initialize_emotional_intelligence()
            if not emotional_success:
                logger.warning("Emotional intelligence system failed to initialize")
            
            # Set up API server
            await self._setup_api_server()
            
            # Set up command handlers with database context
            self._setup_command_handlers()
            
            # Set up webhook handler with event bus context
            self._setup_webhook_handler()
            
            # Configure update receiving mode (webhook or polling)
            if self._should_use_webhook():
                success = await self._setup_webhook_mode()
            else:
                success = await self._setup_polling_mode()
            
            if not success:
                logger.error("Failed to set up update receiving mode")
                return False
            
            # Update module states to running
            await self._update_module_states_to_running()
            
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
            # Mark as not running first to prevent processing new updates
            self._is_running = False
            
            # Stop dispatcher polling if it's running
            if self.dispatcher:
                try:
                    # Check if polling is active
                    if hasattr(self.dispatcher, '_polling') and self.dispatcher._polling:
                        await self.dispatcher.stop_polling()
                        logger.info("Dispatcher polling stopped")
                    else:
                        logger.info("Dispatcher polling was not active")
                except Exception as e:
                    logger.warning(f"Error stopping dispatcher polling: {e}")
            
            # Stop polling task if it's running
            if hasattr(self, '_polling_task') and self._polling_task and not self._polling_task.done():
                self._polling_task.cancel()
                try:
                    await asyncio.wait_for(self._polling_task, timeout=5.0)
                    logger.info("Polling task stopped")
                except asyncio.CancelledError:
                    logger.info("Polling task cancelled successfully")
                except asyncio.TimeoutError:
                    logger.warning("Polling task did not stop within timeout")
                except Exception as e:
                    logger.warning(f"Error waiting for polling task: {e}")
            
            # Close bot session
            if self.bot:
                try:
                    await self.bot.session.close()
                    logger.info("Bot session closed")
                except Exception as e:
                    logger.warning(f"Error closing bot session: {e}")
            
            # Stop database connections if they exist
            if self.database_manager:
                try:
                    await self.database_manager.close_all()
                    logger.info("Database connections closed")
                except Exception as e:
                    logger.warning(f"Error closing database connections: {e}")
            
            # Stop event bus if it exists
            if self.event_bus:
                try:
                    await self.event_bus.close()
                    logger.info("Event bus closed")
                except Exception as e:
                    logger.warning(f"Error closing event bus: {e}")
            
            # Stop cache manager if it exists
            if self.cache_manager:
                try:
                    await self.cache_manager.close()
                    logger.info("Cache manager closed")
                except Exception as e:
                    logger.warning(f"Error closing cache manager: {e}")
            
            logger.info("Bot application stopped successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "stop",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error during bot shutdown: %s", user_message)
            # Ensure the app is marked as not running
            self._is_running = False
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
    
    async def _setup_menu_router(self) -> None:
        """Initialize the menu router and menu system coordinator."""
        logger.info("Setting up menu router and menu system coordinator")
        # Initialize menu system coordinator if all required services are available
        if self.user_service and self.event_bus and self.database_manager and self.bot:
            self.menu_system_coordinator = MenuSystemCoordinator(
                bot=self.bot,
                event_bus=self.event_bus,
                user_service=self.user_service
            )

            # Initialize the coordinator
            try:
                coordinator_success = await self.menu_system_coordinator.initialize()
                if not coordinator_success:
                    logger.error("Failed to initialize menu system coordinator")
                else:
                    logger.info("Menu system coordinator initialized successfully")
            except Exception as e:
                logger.error("Exception during menu system coordinator initialization", exc_info=True)
        else:
            logger.warning("Some services missing for menu system coordinator, continuing without it")
            self.menu_system_coordinator = None

        # Initialize menu router with available services
        self.menu_router = MenuIntegrationRouter(
            user_service=self.user_service,
            event_bus=self.event_bus,
            database_manager=self.database_manager,
            menu_coordinator=self.menu_system_coordinator
        )
        logger.info("Menu router set up successfully")

        # Connect menu system coordinator to menu handlers for enhanced integration
        if self.menu_system_coordinator and hasattr(self.menu_router, 'menu_handler_system'):
            logger.info("Connecting MenuSystemCoordinator to menu handlers")
            # The menu router should have access to menu handlers that we can enhance
            pass

        # Now register the Telegram handlers with the dispatcher
        self._register_telegram_handlers()

    def _setup_command_handlers(self) -> None:
        """Set up the command handlers with the router."""
        logger.debug("Setting up command handlers")

        # Initialize command handler for fallback only (MenuSystemCoordinator handles most commands)
        if self.user_service and self.event_bus:
            self.command_handler = CommandHandler(self.user_service, self.event_bus)
        elif self.user_service:
            self.command_handler = CommandHandler(self.user_service)
        elif self.event_bus:
            self.command_handler = CommandHandler(event_bus=self.event_bus)
        else:
            self.command_handler = CommandHandler()

        # Register only a fallback handler for unknown commands when MenuSystemCoordinator fails
        router_to_use = self.menu_router if self.menu_router else self.router
        router_to_use.set_default_handler(self.command_handler.handle_unknown)

        logger.debug("Command handlers set up successfully (MenuSystemCoordinator handles primary routing)")
    
    def _register_telegram_handlers(self) -> None:
        """Register Telegram handlers with the dispatcher, using the new MenuIntegrationRouter."""
        logger.info("Registering Telegram handlers via MenuIntegrationRouter")

        if not self.dispatcher or not self.menu_router:
            logger.error("Dispatcher or Menu Router not initialized, cannot register handlers.")
            return

        # Register the menu router to handle all messages and callback queries
        self.dispatcher.message.register(self.menu_router.route_message)
        self.dispatcher.callback_query.register(self.menu_router.route_callback)

        logger.info("Menu router registered with dispatcher to handle all messages and callbacks.")

        # Enhanced registration for menu system coordinator
        if self.menu_system_coordinator:
            logger.info("Enhanced menu system integration active")
    
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

    async def _setup_cache_manager(self) -> bool:
        """Initialize cache manager for caching operations.

        Returns:
            bool: True if cache manager setup was successful, False otherwise
        """
        logger.info("Setting up cache manager")

        try:
            # Initialize cache manager
            self.cache_manager = CacheManager(self.config_manager)

            # Attempt to connect to Redis
            success = await self.cache_manager.connect()

            if not success:
                logger.warning("Failed to connect to Redis, cache will operate in memory mode")

            logger.info("Cache manager set up successfully")
            return True

        except Exception as e:
            error_context = {
                "operation": "setup_cache_manager",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up cache manager: %s", user_message)
            # Don't fail startup, continue without cache
            self.cache_manager = CacheManager(self.config_manager)
            logger.warning("Continuing with basic cache manager")
            return True

    async def _setup_module_registry(self) -> bool:
        """Initialize module registry for dependency management.
        
        Returns:
            bool: True if module registry setup was successful, False otherwise
        """
        logger.info("Setting up module registry")
        
        try:
            # Initialize module registry with event bus
            if self.event_bus:
                self.module_registry = ModuleRegistry(self.event_bus)
                logger.info("Module registry set up successfully")
                return True
            else:
                logger.warning("Event bus not initialized, cannot set up module registry")
                return False
                
        except Exception as e:
            error_context = {
                "operation": "setup_module_registry",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up module registry: %s", user_message)
            return False
    
    async def _register_core_services(self) -> bool:
        """Register core services with the module registry.
        
        Returns:
            bool: True if core services were registered successfully, False otherwise
        """
        logger.info("Registering core services with module registry")
        
        try:
            if not self.module_registry:
                logger.warning("Module registry not initialized, cannot register core services")
                return False
            
            # Register core services in dependency order
            # Config service
            self.module_registry.register_module(
                name="config",
                module_type="core",
                version="1.0.0",
                dependencies=[]
            )
            
            # Database service
            if self.database_manager:
                self.module_registry.register_module(
                    name="database",
                    module_type="core",
                    version="1.0.0",
                    dependencies=["config"]
                )
            
            # Event bus service
            if self.event_bus:
                self.module_registry.register_module(
                    name="event_bus",
                    module_type="core",
                    version="1.0.0",
                    dependencies=["config"]
                )
            
            # User service
            if self.user_service:
                self.module_registry.register_module(
                    name="user_service",
                    module_type="service",
                    version="1.0.0",
                    dependencies=["database", "event_bus"]
                )
            
            # Router service
            self.module_registry.register_module(
                name="router",
                module_type="core",
                version="1.0.0",
                dependencies=["user_service"]
            )
            
            # Middleware service
            self.module_registry.register_module(
                name="middleware",
                module_type="core",
                version="1.0.0",
                dependencies=["router"]
            )
            
            # Error handler service
            self.module_registry.register_module(
                name="error_handler",
                module_type="core",
                version="1.0.0",
                dependencies=[]
            )
            
            logger.info("Core services registered with module registry successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "register_core_services",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error registering core services: %s", user_message)
            return False
    
    async def _update_module_states_to_running(self) -> bool:
        """Update all registered modules to running state.
        
        Returns:
            bool: True if module states were updated successfully, False otherwise
        """
        logger.info("Updating module states to running")
        
        try:
            if not self.module_registry:
                logger.warning("Module registry not initialized, cannot update module states")
                return False
            
            # Update all registered modules to running state
            for module_name in self.module_registry.modules.keys():
                self.module_registry.update_module_state(module_name, ModuleState.RUNNING)
            
            logger.info("Module states updated to running successfully")
            return True
            
        except Exception as e:
            error_context = {
                "operation": "update_module_states_to_running",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error updating module states: %s", user_message)
            return False
    
    async def _setup_user_service(self) -> bool:
        """Initialize user service after database and event bus are set up.
        
        Returns:
            bool: True if user service setup was successful, False otherwise
        """
        logger.info("Setting up user service")
        
        try:
            # Initialize user service with database manager, event bus, and cache manager
            # Even if database_manager is None, we can create a service that handles the absence
            self.user_service = UserService(self.database_manager, self.event_bus, self.cache_manager)
            logger.info("User service set up successfully")
            return True
                
        except Exception as e:
            error_context = {
                "operation": "setup_user_service",
                "component": "BotApplication"
            }
            user_message = await self.error_handler.handle_error(e, error_context)
            logger.error("Error setting up user service: %s", user_message)
            # Don't fail the setup, create a basic user service
            self.user_service = None
            logger.warning("Continuing without user service")
            return True
    
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

    async def initialize_emotional_intelligence(self):
        """Initialize emotional intelligence system.
        
        This method sets up the emotional intelligence system as part of the 
        complete YABOT integration, following the specification requirements.
        """
        try:
            # Import emotional event handlers
            from src.modules.emotional import register_emotional_event_handlers
            
            # Register emotional event handlers if event bus and cross module service are available
            if self.event_bus and hasattr(self, 'cross_module_service') and self.cross_module_service:
                await register_emotional_event_handlers(self.event_bus, self.cross_module_service)
                logger.info("Emotional intelligence event handlers registered successfully")
            
            # Initialize emotional intelligence service
            from src.dependencies import get_emotional_intelligence_service
            emotional_service = await get_emotional_intelligence_service()
            if hasattr(emotional_service, 'initialize'):
                await emotional_service.initialize()
            
            # Add emotional API routes if API server is available
            if self.api_server and hasattr(self.api_server, 'app'):
                from src.api.endpoints.emotional import router as emotional_router
                self.api_server.app.include_router(emotional_router)
            
            logger.info("Emotional intelligence system initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize emotional intelligence: {e}")
            return False

    async def _log_component_health_issues(self) -> None:
        """Log detailed health issues for troubleshooting."""
        logger.info("=== Component Health Status ===")

        # Check database connectivity
        if self.database_manager:
            mongo_connected = hasattr(self.database_manager, '_mongo_client') and self.database_manager._mongo_client is not None
            sqlite_connected = hasattr(self.database_manager, '_sqlite_conn') and self.database_manager._sqlite_conn is not None
            logger.info(f"Database Manager - MongoDB: {'Connected' if mongo_connected else 'Disconnected'}, SQLite: {'Connected' if sqlite_connected else 'Disconnected'}")
        else:
            logger.warning("Database Manager: Not initialized")

        # Check cache manager connectivity
        if self.cache_manager:
            cache_connected = hasattr(self.cache_manager, '_is_connected') and self.cache_manager._is_connected
            logger.info(f"Cache Manager: {'Connected to Redis' if cache_connected else 'Memory-only mode'}")
        else:
            logger.warning("Cache Manager: Not initialized")

        # Check event bus connectivity
        if self.event_bus:
            event_connected = hasattr(self.event_bus, '_is_connected') and getattr(self.event_bus, '_is_connected', False)
            logger.info(f"Event Bus: {'Connected to Redis' if event_connected else 'Local queue mode'}")
        else:
            logger.warning("Event Bus: Not initialized")

        # Check user service status
        if self.user_service:
            has_cache = hasattr(self.user_service, 'cache_manager') and self.user_service.cache_manager is not None
            logger.info(f"User Service: Initialized with {'cache manager' if has_cache else 'no cache manager'}")
        else:
            logger.warning("User Service: Not initialized")

        logger.info("=== End Health Status ===")

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information.

        Returns:
            Dict containing health metrics for all components
        """
        health_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }

        # Database health
        if self.database_manager:
            mongo_connected = hasattr(self.database_manager, '_mongo_client') and self.database_manager._mongo_client is not None
            sqlite_connected = hasattr(self.database_manager, '_sqlite_conn') and self.database_manager._sqlite_conn is not None
            health_info["components"]["database"] = {
                "status": "healthy" if (mongo_connected or sqlite_connected) else "degraded",
                "mongodb_connected": mongo_connected,
                "sqlite_connected": sqlite_connected
            }
        else:
            health_info["components"]["database"] = {"status": "unavailable"}

        # Cache health
        if self.cache_manager:
            cache_connected = hasattr(self.cache_manager, '_is_connected') and self.cache_manager._is_connected
            health_info["components"]["cache"] = {
                "status": "healthy" if cache_connected else "degraded",
                "redis_connected": cache_connected
            }
        else:
            health_info["components"]["cache"] = {"status": "unavailable"}

        # Event bus health
        if self.event_bus:
            event_connected = hasattr(self.event_bus, '_is_connected') and getattr(self.event_bus, '_is_connected', False)
            health_info["components"]["event_bus"] = {
                "status": "healthy" if event_connected else "degraded",
                "redis_connected": event_connected
            }
        else:
            health_info["components"]["event_bus"] = {"status": "unavailable"}

        # Menu system health
        if self.menu_system_coordinator:
            try:
                menu_health = await self.menu_system_coordinator.get_system_health()
                health_info["components"]["menu_system"] = {
                    "status": "healthy" if menu_health.get("overall_health_score", 0) > 80 else "degraded",
                    "health_score": menu_health.get("overall_health_score", 0),
                    "performance_metrics": menu_health.get("performance", {}),
                    "message_management": menu_health.get("message_management", {})
                }
            except Exception as e:
                health_info["components"]["menu_system"] = {
                    "status": "degraded",
                    "error": str(e)
                }
        else:
            health_info["components"]["menu_system"] = {"status": "unavailable"}

        # Determine overall status
        component_statuses = [comp["status"] for comp in health_info["components"].values()]
        if "unavailable" in component_statuses:
            health_info["overall_status"] = "degraded"
        elif "degraded" in component_statuses:
            health_info["overall_status"] = "degraded"

        return health_info
