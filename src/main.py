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

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

# Global bot application instance
bot_app = None


async def shutdown_bot(signum=None, frame=None):
    """Gracefully shutdown the bot application."""
    global bot_app
    
    if signum:
        logger.info("Received signal %s, shutting down...", signum)
    
    if bot_app and bot_app.is_running:
        logger.info("Stopping bot application...")
        await bot_app.stop()
    
    logger.info("Bot application stopped")
    sys.exit(0)


async def main():
    """Main function to start the bot."""
    global bot_app
    
    logger.info("Starting Telegram bot application...")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown_bot(s, f)))
    signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown_bot(s, f)))
    
    # Initialize the bot application
    bot_app = BotApplication()
    
    # Start the bot
    success = await bot_app.start()
    
    if not success:
        logger.error("Failed to start bot application")
        return
    
    logger.info("Bot application started successfully")
    
    # Keep the application running
    try:
        while bot_app.is_running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Bot application task was cancelled")
    except Exception as e:
        logger.error("Unexpected error in bot application: %s", e)
    finally:
        await shutdown_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.error("Bot stopped due to error: %s", e)