"""
Simple test script to verify UserService menu context methods.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Simple test without external dependencies
def test_menu_context_methods_exist():
    """Test that the menu context methods exist in UserService."""
    try:
        from services.user import UserService
        print("✓ UserService imported successfully")
        
        # Check if the methods we added exist
        methods = [
            'get_user_menu_context',
            'update_user_menu_context',
            'push_menu_navigation',
            'pop_menu_navigation',
            'clear_menu_navigation',
            'update_menu_session_data'
        ]
        
        for method in methods:
            if hasattr(UserService, method):
                print(f"✓ Method {method} exists")
            else:
                print(f"✗ Method {method} is missing")
                return False
        
        print("✓ All menu context methods exist in UserService")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_menu_context_methods_exist()
    sys.exit(0 if success else 1)