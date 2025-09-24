"""
Core Bot Framework - Main Application Entry Point

This module serves as the main entry point for the bot application.
It initializes and starts the bot using the BotApplication class.
"""
import asyncio
import logging
import signal
import sys
from typing import Callable, Any

from src.core.application import get_bot_application
from src.utils.logger import get_logger


# Global application reference for signal handling
app = None
logger = get_logger(__name__)


async def main():
    """
    Main application entry point.
    
    Implements requirements:
    - 1.1: WHEN the bot is initialized THEN the system SHALL establish a connection with Telegram API using a valid bot token
    - 1.3: WHEN the bot is configured THEN the system SHALL support both polling and webhook modes for receiving updates
    - 1.4: WHEN the bot starts THEN the system SHALL validate all required configuration parameters before beginning operation
    """
    global app
    
    # Initialize the bot application
    app = get_bot_application()
    
    # Initialize the application components
    try:
        await app.initialize()
        logger.info("Bot application initialized successfully")
    except Exception as e:
        logger.error(
            "Failed to initialize bot application",
            error=str(e),
            error_type=type(e).__name__
        )
        sys.exit(1)
    
    # Start the application
    try:
        logger.info("Starting bot application")
        await app.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(
            "Error during bot execution",
            error=str(e),
            error_type=type(e).__name__
        )
        sys.exit(1)
    finally:
        # Ensure cleanup happens
        if app:
            try:
                await app.stop()
            except Exception as e:
                logger.error(
                    "Error during application shutdown",
                    error=str(e),
                    error_type=type(e).__name__
                )


def signal_handler(signum: int, frame: Any):
    """
    Handle system signals for graceful shutdown.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    if app:
        # In async context, we can't directly call async methods from signal handler
        # Instead, we'll set a flag or use other async-safe mechanisms
        pass
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the main application
    asyncio.run(main())