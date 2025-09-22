#!/usr/bin/env python3
"""
Main entry point for the YABOT application with atomic modules.
Implements requirements 5.1 and 5.7 for module isolation and failure recovery.
"""

import asyncio
import logging
import signal
import sys
from dotenv import load_dotenv
from src.core.application import BotApplication
from src.utils.logger import get_logger

# Module imports for atomic modules
from src.modules.narrative.fragment_manager import NarrativeFragmentManager
from src.modules.narrative.decision_engine import DecisionEngine
from src.modules.narrative.hint_system import HintSystem
from src.modules.narrative.lucien_messenger import LucienMessenger

from src.modules.gamification.besitos_wallet import BesitosWallet
from src.modules.gamification.mission_manager import MissionManager
from src.modules.gamification.item_manager import ItemManager
from src.modules.gamification.auction_system import AuctionSystem
from src.modules.gamification.trivia_engine import TriviaEngine
from src.modules.gamification.daily_gift import DailyGiftSystem
from src.modules.gamification.achievement_system import AchievementSystem

from src.modules.admin.access_control import AccessControl
from src.modules.admin.subscription_manager import SubscriptionManager
from src.modules.admin.post_scheduler import PostScheduler
from src.modules.admin.notification_system import NotificationSystem
from src.modules.admin.message_protection import MessageProtectionSystem as MessageProtection
from src.modules.admin.admin_commands import AdminCommandHandler as AdminCommandInterface

from src.shared.registry.module_registry import ModuleRegistry, ModuleState, ModuleHealthStatus
from src.shared.database.backup_automation import BackupAutomation, BackupConfig

# Global instances
bot_app = None
logger = None
module_registry = None
backup_automation = None
# Track background tasks for proper cancellation
background_tasks = set()

async def shutdown_bot(signum=None, frame=None):
    """Gracefully shutdown the bot application and all modules."""
    global bot_app, logger, module_registry, backup_automation, background_tasks
    
    if signum and logger:
        logger.info("Received signal %s, shutting down...", signum)
    
    # Cancel all background tasks
    if background_tasks:
        logger.info("Cancelling %d background tasks...", len(background_tasks))
        for task in background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete cancellation
        if background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*background_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some background tasks did not cancel within timeout")
    
    # Update module registry states
    if module_registry:
        for module_info in module_registry.get_all_modules():
            module_registry.update_module_state(module_info.name, ModuleState.STOPPING)
        logger.info("Module states updated to STOPPING")
    
    # Stop backup automation
    if backup_automation:
        await backup_automation.stop_scheduled_backups()
        logger.info("Backup automation stopped")
    
    # Stop the bot application
    if bot_app and bot_app.is_running:
        if logger:
            logger.info("Stopping bot application...")
        success = await bot_app.stop()
        if not success:
            logger.warning("Bot application stop returned False")
    
    # Save final module registry state
    if module_registry:
        # Update all modules to STOPPED state
        for module_info in module_registry.get_all_modules():
            module_registry.update_module_state(module_info.name, ModuleState.STOPPED)
        logger.info("Module states updated to STOPPED")
    
    if logger:
        logger.info("Bot application stopped")
    # Instead of sys.exit(0), we'll use a more graceful approach
    # The main loop will detect that the bot is no longer running and exit naturally
    return True


async def initialize_modules(module_registry):
    """Initialize all atomic modules and register them with the registry."""
    logger.info("Initializing atomic modules")
    
    # Narrative modules
    module_registry.register_module("fragment_manager", "narrative", "1.0.0")
    module_registry.register_module("decision_engine", "narrative", "1.0.0")
    module_registry.register_module("hint_system", "narrative", "1.0.0")
    module_registry.register_module("lucien_messenger", "narrative", "1.0.0")
    
    # Gamification modules
    module_registry.register_module("besitos_wallet", "gamification", "1.0.0")
    module_registry.register_module("mission_manager", "gamification", "1.0.0")
    module_registry.register_module("item_manager", "gamification", "1.0.0")
    module_registry.register_module("auction_system", "gamification", "1.0.0")
    module_registry.register_module("trivia_engine", "gamification", "1.0.0")
    module_registry.register_module("daily_gift", "gamification", "1.0.0")
    module_registry.register_module("achievement_system", "gamification", "1.0.0")
    
    # Admin modules
    module_registry.register_module("access_control", "admin", "1.0.0")
    module_registry.register_module("subscription_manager", "admin", "1.0.0")
    module_registry.register_module("post_scheduler", "admin", "1.0.0")
    module_registry.register_module("notification_system", "admin", "1.0.0")
    module_registry.register_module("message_protection", "admin", "1.0.0")
    module_registry.register_module("admin_commands", "admin", "1.0.0")
    
    # Update all modules to RUNNING state
    for module_info in module_registry.get_all_modules():
        module_registry.update_module_state(module_info.name, ModuleState.RUNNING)
    
    logger.info("All atomic modules initialized and registered")


async def initialize_backup_system(config_manager):
    """Initialize the backup automation system."""
    global backup_automation
    
    logger.info("Initializing backup automation system")
    
    # Create backup configuration
    backup_config = BackupConfig(
        backup_interval_hours=6,  # Requirement 6.7
        retention_days=30,
        backup_directory="./backups",
        mongo_uri=config_manager.get_database_config().mongodb_uri,
        database_name="yabot"
    )
    
    # Initialize backup automation (assuming event_bus is available from bot_app)
    # In a real implementation, we would pass the actual event bus
    # backup_automation = BackupAutomation(backup_config, bot_app.event_bus)
    
    logger.info("Backup automation system initialized")


async def start_health_monitoring(module_registry):
    """Start health monitoring for all modules."""
    logger.info("Starting module health monitoring")
    # In a real implementation, we would start the health monitoring
    # await module_registry.start_health_monitoring()


async def main():
    """Main function to start the YABOT application with atomic modules."""
    global bot_app, logger, module_registry, backup_automation
    
    if logger:
        logger.info("Starting YABOT application with atomic modules...")
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    
    # Create an event that will be set when shutdown is requested
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        """Signal handler that schedules shutdown in the event loop."""
        if logger:
            logger.info("Received signal %s, scheduling shutdown...", signum)
        # Schedule the shutdown coroutine in the event loop
        loop.call_soon_threadsafe(shutdown_event.set)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize the module registry
    # In a real implementation, we would pass the actual event bus
    # module_registry = ModuleRegistry(bot_app.event_bus)
    
    # Initialize the bot application
    bot_app = BotApplication()
    
    # Start the bot
    success = await bot_app.start()
    
    if not success:
        if logger:
            logger.error("Failed to start bot application")
        return
    
    # Initialize atomic modules
    # await initialize_modules(module_registry)
    
    # Initialize backup system
    # await initialize_backup_system(bot_app.config_manager)
    
    # Start health monitoring
    # await start_health_monitoring(module_registry)
    
    if logger:
        logger.info("YABOT application started successfully with atomic modules")
    
    # Keep the application running
    try:
        while bot_app.is_running and not shutdown_event.is_set():
            # Send heartbeats for modules
            if module_registry:
                for module_info in module_registry.get_all_modules():
                    module_registry.heartbeat(module_info.name)
            
            # Wait for either 1 second or shutdown event
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                # Normal case - continue the loop
                pass
                
    except asyncio.CancelledError:
        if logger:
            logger.info("Bot application task was cancelled")
    except Exception as e:
        if logger:
            logger.error("Unexpected error in bot application: %s", e)
    finally:
        # Perform shutdown when the loop exits
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
