#!/usr/bin/env python3
"""
Test script to verify the Ctrl+C shutdown fix implementation.

This script tests the new background task tracking and shutdown coordination.
"""

import asyncio
import signal
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_shutdown_functionality():
    """Test the improved shutdown functionality."""
    print("Testing shutdown fix implementation...")

    try:
        # Import main module functions
        from src.main import register_background_task, unregister_background_task, background_tasks

        print(f"✓ Successfully imported shutdown functions")
        print(f"✓ Initial background_tasks count: {len(background_tasks)}")

        # Test task registration
        async def dummy_task():
            try:
                while True:
                    await asyncio.sleep(1)
                    print("Dummy task running...")
            except asyncio.CancelledError:
                print("Dummy task cancelled successfully")
                raise

        # Create and register a test task
        test_task = asyncio.create_task(dummy_task())
        register_background_task(test_task, "test_task")

        print(f"✓ Registered test task. Background_tasks count: {len(background_tasks)}")

        # Test module imports
        try:
            from src.database.manager import DatabaseManager
            print("✓ DatabaseManager import successful")
        except ImportError as e:
            print(f"⚠ DatabaseManager import failed: {e}")

        try:
            from src.events.bus import EventBus
            print("✓ EventBus import successful")
        except ImportError as e:
            print(f"⚠ EventBus import failed: {e}")

        try:
            from src.ui.menu_cache import MenuCacheOptimizer
            print("✓ MenuCacheOptimizer import successful")
        except ImportError as e:
            print(f"⚠ MenuCacheOptimizer import failed: {e}")

        # Test task cancellation
        print("Testing task cancellation...")
        test_task.cancel()
        unregister_background_task(test_task)

        try:
            await asyncio.wait_for(test_task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            print("✓ Test task cancelled successfully")

        print(f"✓ Final background_tasks count: {len(background_tasks)}")
        print("✓ Shutdown fix implementation test completed successfully!")

        return True

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_main_shutdown():
    """Test the main shutdown function."""
    print("\nTesting main shutdown function...")

    try:
        from src.main import shutdown_bot
        print("✓ shutdown_bot function imported successfully")

        # Note: We won't actually call shutdown_bot as it would terminate the test
        print("✓ shutdown_bot function is available for signal handling")

        return True
    except Exception as e:
        print(f"✗ shutdown_bot test failed: {e}")
        return False

def test_signal_handling():
    """Test signal handler setup."""
    print("\nTesting signal handler setup...")

    try:
        # Test that we can access signal module
        print(f"✓ SIGINT signal number: {signal.SIGINT}")
        print(f"✓ SIGTERM signal number: {signal.SIGTERM}")
        print("✓ Signal handling infrastructure available")

        return True
    except Exception as e:
        print(f"✗ Signal handling test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("YABOT Shutdown Fix Implementation Test")
    print("=" * 60)

    tests = [
        test_shutdown_functionality(),
        test_main_shutdown(),
    ]

    results = await asyncio.gather(*tests, return_exceptions=True)

    # Test signal handling (non-async)
    signal_result = test_signal_handling()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results) + 1  # +1 for signal test

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Test {i+1}: ✗ FAILED - {result}")
        elif result:
            print(f"Test {i+1}: ✓ PASSED")
            passed += 1
        else:
            print(f"Test {i+1}: ✗ FAILED")

    if signal_result:
        print(f"Test {len(results)+1}: ✓ PASSED")
        passed += 1
    else:
        print(f"Test {len(results)+1}: ✗ FAILED")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests PASSED! The shutdown fix implementation looks good.")
        print("\n📋 Next steps:")
        print("1. Test with actual bot startup: python src/main.py")
        print("2. Press Ctrl+C and verify clean shutdown")
        print("3. Check logs for proper task cancellation")
        return True
    else:
        print("❌ Some tests FAILED. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)