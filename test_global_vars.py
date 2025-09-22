#!/usr/bin/env python3
"""
Test script to verify the global variables fix.
"""

import sys
import os

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_global_variables():
    """Test that global variables are properly defined."""
    try:
        # This will import the main module and define the global variables
        import src.main
        print("✓ Global variables imported successfully")
        
        # Check that the variables exist
        assert hasattr(src.main, 'bot_app'), "bot_app not defined"
        assert hasattr(src.main, 'logger'), "logger not defined"
        assert hasattr(src.main, 'module_registry'), "module_registry not defined"
        assert hasattr(src.main, 'backup_automation'), "backup_automation not defined"
        assert hasattr(src.main, 'background_tasks'), "background_tasks not defined"
        
        print("✓ All global variables are defined")
        print(f"  - bot_app: {src.main.bot_app}")
        print(f"  - logger: {src.main.logger}")
        print(f"  - module_registry: {src.main.module_registry}")
        print(f"  - backup_automation: {src.main.backup_automation}")
        print(f"  - background_tasks: {src.main.background_tasks} (type: {type(src.main.background_tasks)})")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_global_variables()
    if success:
        print("\n✓ Global variables fix verified successfully!")
    else:
        print("\n✗ Global variables fix verification failed!")
        sys.exit(1)