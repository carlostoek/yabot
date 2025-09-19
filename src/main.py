#!/usr/bin/env python3
"""
Main entry point for the Telegram bot application.
"""

import asyncio
import logging
import signal
import sys
from dotenv import load_dotenv
from src.core.application import BotApplication
from src.utils.logger import get_logger

# Global bot application instance
bot_app = None
logger = None

async def shutdown_bot(signum=None, frame=None):
    """Gracefully shutdown the bot application."""
    global bot_app, logger
    
    if signum and logger:
        logger.info("Received signal %s, shutting down...", signum)
    
    if bot_app and bot_app.is_running:
        if logger:
            logger.info("Stopping bot application...")
        await bot_app.stop()
    
    if logger:
        logger.info("Bot application stopped")
    sys.exit(0)


async def main():
    """Main function to start the bot."""
    global bot_app, logger
    
    if logger:
        logger.info("Starting Telegram bot application...")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown_bot(s, f)))
    signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown_bot(s, f)))
    
    # Initialize the bot application
    bot_app = BotApplication()
    
    # Start the bot
    success = await bot_app.start()
    
    if not success:
        if logger:
            logger.error("Failed to start bot application")
        return
    
    if logger:
        logger.info("Bot application started successfully")
    
    # Keep the application running
    try:
        while bot_app.is_running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        if logger:
            logger.info("Bot application task was cancelled")
    except Exception as e:
        if logger:
            logger.error("Unexpected error in bot application: %s", e)
    finally:
        await shutdown_bot()


if __name__ == "__main__":
    try:
        # Load environment variables
        load_dotenv()

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        logger = get_logger(__name__)

        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        # Use a basic logger or print if the main logger is not available
        if logger:
            logger.error("Bot stopped due to error: %s", e)
        else:
            logging.basicConfig()
            logging.error("Bot stopped due to error: %s", e, exc_info=True)
