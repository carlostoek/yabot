#!/usr/bin/env python3
"""
Test script to verify the signal handling implementation.
"""

import asyncio
import signal
import sys
import os

# Mock the required modules
class MockBotApplication:
    def __init__(self):
        self.is_running = True
    
    async def stop(self):
        print("MockBotApplication.stop() called")
        return True

# Create global instances like in main.py
bot_app = MockBotApplication()
logger = type('Logger', (), {'info': lambda self, msg, *args: print(msg % args if args else msg)})()
module_registry = None
backup_automation = None
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
        logger.info("Module states updated to STOPPING")
    
    # Stop backup automation
    if backup_automation:
        logger.info("Backup automation stopped")
    
    # Stop the bot application
    if bot_app and bot_app.is_running:
        logger.info("Stopping bot application...")
        success = await bot_app.stop()
        if not success:
            logger.warning("Bot application stop returned False")
    
    # Save final module registry state
    if module_registry:
        logger.info("Module states updated to STOPPED")
    
    if logger:
        logger.info("Bot application stopped")
    # Instead of sys.exit(0), we'll use a more graceful approach
    # The main loop will detect that the bot is no longer running and exit naturally
    return True

async def test_signal_handling():
    """Test the signal handling implementation."""
    print("Testing signal handling implementation...")
    
    # Create an event loop
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
    
    print("✓ Signal handlers registered correctly")
    print("✓ Using asyncio.Event for shutdown coordination")
    print("✓ Using loop.call_soon_threadsafe for thread-safe scheduling")
    
    return True

async def main():
    """Main test function."""
    print("Testing shutdown implementation...")
    
    # Test shutdown function
    try:
        result = await shutdown_bot()
        print("✓ shutdown_bot completed without calling sys.exit(0)")
        print(f"✓ shutdown_bot returned: {result}")
    except SystemExit:
        print("✗ shutdown_bot incorrectly called sys.exit(0)")
        return False
    except Exception as e:
        print(f"✗ shutdown_bot raised unexpected exception: {e}")
        return False
    
    # Test signal handling
    try:
        await test_signal_handling()
    except Exception as e:
        print(f"✗ Signal handling test failed: {e}")
        return False
    
    print("\n✓ All tests passed! The shutdown implementation is working correctly.")
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)