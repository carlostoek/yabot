#!/usr/bin/env python3
"""
Simple test script to verify the global variables fix by parsing the file.
"""

import ast
import sys

def test_global_variables_in_file():
    """Test that global variables are properly defined in the source file."""
    try:
        with open('src/main.py', 'r') as f:
            content = f.read()
        
        # Parse the Python file
        tree = ast.parse(content)
        
        # Look for the global variables assignment
        global_vars_found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id in ['bot_app', 'logger', 'module_registry', 'backup_automation', 'background_tasks']:
                            global_vars_found.append(target.id)
        
        print("✓ File parsed successfully")
        print(f"✓ Found global variables: {global_vars_found}")
        
        required_vars = ['bot_app', 'logger', 'module_registry', 'backup_automation', 'background_tasks']
        missing_vars = [var for var in required_vars if var not in global_vars_found]
        
        if missing_vars:
            print(f"✗ Missing global variables: {missing_vars}")
            return False
        else:
            print("✓ All required global variables are defined in the file")
            return True
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_global_variables_in_file()
    if success:
        print("\n✓ Global variables fix verified successfully!")
    else:
        print("\n✗ Global variables fix verification failed!")
        sys.exit(1)