#!/usr/bin/env python3
"""
Cleanup Script - Removes blank lines containing only whitespace
Processes all Python files in the addon directory
"""

import os


def clean_whitespace_lines(file_path):
    """
    Remove blank lines that contain only whitespace (spaces/tabs)
    Keep truly empty lines (no characters at all)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        cleaned_lines = []
        changes_made = False

        for line in lines:
            # Check if line has only whitespace (but not completely empty)
            if line.strip() == '' and len(line) > 1:  # > 1 means it has whitespace + newline
                # Replace with truly empty line (just newline)
                cleaned_lines.append('\n')
                changes_made = True
            else:
                # Keep line as-is
                cleaned_lines.append(line)

        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False


def process_directory(directory):
    """
    Recursively process all Python files in directory
    """
    files_processed = 0
    files_modified = 0

    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                files_processed += 1

                if clean_whitespace_lines(file_path):
                    files_modified += 1
                    # Show relative path for readability
                    rel_path = os.path.relpath(file_path, directory)
                    print(f"✓ Cleaned: {rel_path}")

    return files_processed, files_modified


if __name__ == '__main__':
    # Get the addon directory (same directory as this script)
    addon_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("Whitespace Cleanup Script")
    print("=" * 60)
    print(f"Processing: {addon_dir}")
    print("-" * 60)

    processed, modified = process_directory(addon_dir)

    print("-" * 60)
    print(f"Files processed: {processed}")
    print(f"Files modified: {modified}")
    print(f"Files unchanged: {processed - modified}")
    print("=" * 60)

    if modified > 0:
        print("✓ Cleanup complete! All whitespace-only lines removed.")
    else:
        print("✓ No whitespace issues found - all files are clean!")
