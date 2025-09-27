"""
Core Bot Framework - Router Component

This module routes incoming messages to appropriate handlers based on message type and content.
"""
from aiogram import Dispatcher

from src.utils.logger import get_logger
from src.core.middleware import setup_default_middlewares
from src.core.error_handler import setup_error_handlers
from src.handlers.commands.start_handler import router as start_router


def def setup_routers(dp: Dispatcher) -> None:
    """
    Setup all routers for the dispatcher.

    Args:
        dp: The aiogram Dispatcher instance.
    """
    # Setup default middlewares
    middleware_manager = setup_default_middlewares()

    # Add middlewares to the dispatcher for broad coverage
    for middleware in middleware_manager.get_middlewares():
        dp.message.middleware(middleware)
        dp.callback_query.middleware(middleware)
        dp.inline_query.middleware(middleware)
        dp.chosen_inline_result.middleware(middleware)

    # Include the routers from the handlers
    dp.include_router(start_router)
    # Add other routers here as they are created

    # Setup error handlers
    setup_error_handlers(dp)

    logger = get_logger(__name__)
    logger.info("Routers and middlewares setup completed.")