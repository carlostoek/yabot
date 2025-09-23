#!/usr/bin/env python3
"""
Temporary script to fix indentation in the menu_factory.py file
"""

def fix_indentation(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find the lines that need to be indented
    in_narrative_builder = False
    in_admin_builder = False
    in_vip_builder = False
    needs_indent = False

    for i, line in enumerate(lines):
        # Track which builder we're in
        if 'class NarrativeMenuBuilder(MenuBuilder):' in line:
            in_narrative_builder = True
            needs_indent = False
        elif 'class AdminMenuBuilder(MenuBuilder):' in line:
            in_narrative_builder = False
            in_admin_builder = True
            needs_indent = False
        elif 'class VIPMenuBuilder(MenuBuilder):' in line:
            in_admin_builder = False
            in_vip_builder = True
            needs_indent = False
        elif 'class MenuFactory:' in line:
            in_vip_builder = False
            needs_indent = False

        # Check if we're in a try block and need to indent
        if in_narrative_builder and 'logger.info(f"Building narrative menu' in line:
            needs_indent = True
        elif in_admin_builder and 'logger.info(f"Building admin menu' in line:
            needs_indent = True
        elif in_vip_builder and 'logger.info(f"Building vip menu' in line:
            needs_indent = True

        # Check if we're at the end of the try block
        if 'except Exception as e:' in line:
            needs_indent = False

        # Add indentation if needed
        if needs_indent and line.strip() and not line.startswith('            '):
            if line.startswith('        '):
                lines[i] = '    ' + line  # Add 4 more spaces

    with open(file_path, 'w') as f:
        f.writelines(lines)

if __name__ == "__main__":
    fix_indentation("menu_factory.py")