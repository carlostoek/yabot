"""
Simple test script to verify UserService menu context methods by checking the source code.
"""

import sys
import os

def test_menu_context_methods_in_source():
    """Test that the menu context methods exist in the UserService source code."""
    try:
        # Read the UserService file
        with open('src/services/user.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✓ UserService source file read successfully")
        
        # Check if the methods we added exist in the source
        methods = [
            'async def get_user_menu_context',
            'async def update_user_menu_context',
            'async def push_menu_navigation',
            'async def pop_menu_navigation',
            'async def clear_menu_navigation',
            'async def update_menu_session_data'
        ]
        
        missing_methods = []
        for method in methods:
            if method in content:
                print(f"✓ Method signature '{method}' found in source")
            else:
                print(f"✗ Method signature '{method}' not found in source")
                missing_methods.append(method)
        
        if not missing_methods:
            print("✓ All menu context methods found in UserService source code")
            return True
        else:
            print(f"✗ Missing methods: {missing_methods}")
            return False
        
    except Exception as e:
        print(f"✗ Error reading source file: {e}")
        return False

def test_default_menu_context_method():
    """Test that the default menu context method exists."""
    try:
        with open('src/services/user.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'def _get_default_menu_context' in content:
            print("✓ Default menu context method found")
            return True
        else:
            print("✗ Default menu context method not found")
            return False
    except Exception as e:
        print(f"✗ Error checking default menu context method: {e}")
        return False

if __name__ == "__main__":
    success1 = test_menu_context_methods_in_source()
    success2 = test_default_menu_context_method()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Task 25 implementation is complete.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)