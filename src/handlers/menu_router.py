"""
Menu Integration Router component for the Telegram bot framework.
"""
import sys
from typing import Any, Optional, Callable, Dict

from aiogram.types import Message, CallbackQuery

from src.core.router import Router
from src.core.middleware import MiddlewareManager, Middleware
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MenuIntegrationRouter(Router):
    """
    A specialized router for handling menu interactions in Telegram.

    This router extends the core Router to provide specific handling for
    Telegram Message and CallbackQuery objects, directing them to the
    appropriate menu handlers. It is designed to work with the MenuFactory
    and other UI components to create a seamless menu navigation experience.

    It introduces a dedicated registry for callback query handlers and integrates
    a middleware manager for menu tracking and other cross-cutting concerns.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the MenuIntegrationRouter.
        Inherits the core Router's initialization and adds a middleware manager.
        """
        # Extract menu_coordinator from kwargs if present
        self.menu_coordinator = kwargs.pop('menu_coordinator', None)
        
        super().__init__(*args, **kwargs)
        self._callback_handlers: Dict[str, Callable] = {}
        self.middleware_manager = MiddlewareManager()
        logger.info("MenuIntegrationRouter initialized with MiddlewareManager.")

    def add_middleware(self, middleware: Middleware) -> None:
        """
        Adds a middleware to the menu router's middleware manager.

        Args:
            middleware (Middleware): The middleware instance to add.
        """
        self.middleware_manager.add_middleware(middleware)

    def register_callback_handler(self, callback_data_prefix: str, handler: Callable) -> None:
        """
        Register callback query handlers based on a prefix.

        Args:
            callback_data_prefix (str): The prefix of the callback_data to match.
            handler (Callable): The handler function to call for matching callbacks.
        """
        if not callable(handler):
            raise TypeError("Handler must be callable")

        self._callback_handlers[callback_data_prefix] = handler
        logger.info("Registered callback handler for prefix: %s", callback_data_prefix)

    async def route_message(self, message: Message) -> Any:
        """
        Routes an incoming Telegram Message object through the middleware pipeline.
        Uses MenuSystemCoordinator for enhanced menu operations when available.

        Args:
            message (Message): The incoming Aiogram Message object.

        Returns:
            Any: The response from the executed handler, processed by middleware.
        """
        logger.debug("Routing message in MenuIntegrationRouter...")
        logger.debug("Message type: %s", type(message).__name__)
        logger.debug("Menu coordinator available: %s", self.menu_coordinator is not None)

        # Check if this is a menu-related command and we have a coordinator
        if message.text and message.text.startswith('/') and self.menu_coordinator:
            command = message.text.strip().lower()
            logger.debug(f"Processing command: {command}")

            # Handle /start and /menu commands through the MenuSystemCoordinator
            if command in ['/start', '/menu', '/help']:
                logger.info(f"Routing {command} command through MenuSystemCoordinator")
                try:
                    result = await self.menu_coordinator.handle_menu_command(message)
                    logger.debug(f"MenuSystemCoordinator result: {result}")
                    if result.get("success"):
                        logger.info(f"MenuSystemCoordinator successfully handled {command}")
                        return result
                    else:
                        logger.warning(f"MenuSystemCoordinator failed for {command}: {result.get('error')}")
                        # Fall through to standard routing
                except Exception as e:
                    logger.error(f"Error in MenuSystemCoordinator for {command}: {e}", exc_info=True)
                    # Fall through to standard routing
        else:
            if not self.menu_coordinator:
                logger.warning("Menu coordinator not available, using standard routing")
            if not message.text or not message.text.startswith('/'):
                logger.debug("Not a command message, using standard routing")

        # Standard routing for non-menu commands or when coordinator is not available
        logger.debug("Using standard routing...")
        response = await self.route_update(message)

        # If we got a CommandResponse, send it back to Telegram
        if response and hasattr(response, 'text'):
            logger.debug("Sending response back to Telegram: %s", response.text[:50] + "..." if len(response.text) > 50 else response.text)
            await message.answer(
                text=response.text,
                parse_mode=getattr(response, 'parse_mode', 'HTML'),
                reply_markup=getattr(response, 'reply_markup', None),
                disable_notification=getattr(response, 'disable_notification', False)
            )

        return response

    async def route_callback(self, callback_query: CallbackQuery) -> Any:
        """
        Routes an incoming Telegram CallbackQuery object through the middleware pipeline.
        Uses MenuSystemCoordinator for menu-related callbacks when available.

        Args:
            callback_query (CallbackQuery): The incoming Aiogram CallbackQuery object.

        Returns:
            Any: The response from the executed handler, processed by middleware.
        """
        logger.debug("Routing callback query...")

        # Check if this is a menu-related callback and we have a coordinator
        if callback_query.data and self.menu_coordinator:
            # Handle menu callbacks through the MenuSystemCoordinator
            if (callback_query.data.startswith('menu:') or
                callback_query.data.startswith('explain_divan_worthiness') or
                callback_query.data.startswith('worthiness_explanation')):
                logger.info(f"Routing callback '{callback_query.data}' through MenuSystemCoordinator")
                try:
                    result = await self.menu_coordinator.handle_callback_query(callback_query)
                    if result.get("success"):
                        logger.info(f"MenuSystemCoordinator successfully handled callback")
                        return result
                    else:
                        logger.warning(f"MenuSystemCoordinator failed for callback: {result.get('error')}")
                        # Fall through to standard routing
                except Exception as e:
                    logger.error(f"Error in MenuSystemCoordinator for callback: {e}")
                    # Fall through to standard routing

        # Process request through middleware
        processed_update = await self.middleware_manager.process_request(callback_query)

        response = None
        if processed_update.data:
            for prefix, handler in self._callback_handlers.items():
                if processed_update.data.startswith(prefix):
                    logger.info("Routing callback with prefix '%s' to handler", prefix)
                    import inspect
                    handler_signature = inspect.signature(handler)
                    if 'router' in handler_signature.parameters:
                        response = await handler(processed_update, router=self)
                    else:
                        response = await handler(processed_update)

                    # Process response through middleware
                    processed_response = await self.middleware_manager.process_response(response)

                    # If we got a CommandResponse, send it back to Telegram
                    if processed_response and hasattr(processed_response, 'text'):
                        logger.debug("Sending callback response back to Telegram: %s", processed_response.text[:50] + "..." if len(processed_response.text) > 50 else processed_response.text)
                        await callback_query.answer()
                        if callback_query.message:
                            await callback_query.message.answer(
                                text=processed_response.text,
                                parse_mode=getattr(processed_response, 'parse_mode', 'HTML'),
                                reply_markup=getattr(processed_response, 'reply_markup', None),
                                disable_notification=getattr(processed_response, 'disable_notification', False)
                            )
                    elif processed_response:
                        # For non-CommandResponse objects, just acknowledge the callback
                        await callback_query.answer()

                    return processed_response

        logger.debug("No specific callback handler found, using generic route_update.")
        response = await self.route_update(processed_update)

        # If we got a CommandResponse from the generic route, send it back to Telegram
        if response and hasattr(response, 'text'):
            logger.debug("Sending generic callback response back to Telegram: %s", response.text[:50] + "..." if len(response.text) > 50 else response.text)
            await callback_query.answer()
            if callback_query.message:
                await callback_query.message.answer(
                    text=response.text,
                    parse_mode=getattr(response, 'parse_mode', 'HTML'),
                    reply_markup=getattr(response, 'reply_markup', None),
                    disable_notification=getattr(response, 'disable_notification', False)
                )
        elif response:
            # For non-CommandResponse objects, just acknowledge the callback
            await callback_query.answer()

        return response

    async def route_update(self, update: Any) -> Any:
        """
        Overrides the parent route_update to wrap handler execution with middleware.

        Args:
            update (Any): The incoming update.

        Returns:
            Any: The final response after middleware processing.
        """
        logger.debug("MenuIntegrationRouter routing update: %s", update)
        logger.debug("Update type: %s", type(update).__name__)
        processed_update = await self.middleware_manager.process_request(update)
        
        # The original routing logic is in the parent class
        logger.debug("Calling parent route_update...")
        response = await super().route_update(processed_update)
        logger.debug("Parent route_update returned: %s", response)
        
        processed_response = await self.middleware_manager.process_response(response)
        
        return processed_response
