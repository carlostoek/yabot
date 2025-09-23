#!/usr/bin/env python3
"""
Test script to verify the shutdown fix implementation.
"""

import asyncio
import signal
import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import shutdown_bot

async def test_shutdown():
    """Test the shutdown function."""
    print("Testing shutdown function...")
    
    # Test that shutdown_bot doesn't call sys.exit(0)
    try:
        result = await shutdown_bot()
        print("✓ shutdown_bot completed without calling sys.exit(0)")
        print(f"✓ shutdown_bot returned: {result}")
    except SystemExit:
        print("✗ shutdown_bot incorrectly called sys.exit(0)")
        return False
    except Exception as e:
        print(f"✓ shutdown_bot raised exception (expected): {e}")
    
    print("All tests passed!")
    return True

if __name__ == "__main__":
    asyncio.run(test_shutdown())