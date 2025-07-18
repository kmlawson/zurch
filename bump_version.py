#!/usr/bin/env python3
"""Version synchronization script for zurch.

This script updates version numbers across all files in the project:
- pyproject.toml
- zurch/__init__.py
- zurch/cli.py
- zurch/constants.py
- CHANGELOG.md

Usage:
    python bump_version.py <new_version>
    python bump_version.py --patch  # Auto-increment patch version
    python bump_version.py --minor  # Auto-increment minor version
    python bump_version.py --major  # Auto-increment major version
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    content = pyproject_path.read_text(encoding='utf-8')
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    
    return match.group(1)


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse version string into major, minor, patch components."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def increment_version(version: str, level: str) -> str:
    """Increment version at specified level."""
    major, minor, patch = parse_version(version)
    
    if level == "major":
        return f"{major + 1}.0.0"
    elif level == "minor":
        return f"{major}.{minor + 1}.0"
    elif level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid increment level: {level}")


def update_pyproject_toml(new_version: str) -> None:
    """Update version in pyproject.toml."""
    path = Path("pyproject.toml")
    content = path.read_text(encoding='utf-8')
    
    # Update version line
    content = re.sub(
        r'version = "[^"]+"',
        f'version = "{new_version}"',
        content
    )
    
    path.write_text(content, encoding='utf-8')
    print(f"Updated pyproject.toml: {new_version}")


def update_init_py(new_version: str) -> None:
    """Update version in zurch/__init__.py."""
    path = Path("zurch/__init__.py")
    content = path.read_text(encoding='utf-8')
    
    # Update __version__ line
    content = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content
    )
    
    path.write_text(content, encoding='utf-8')
    print(f"Updated zurch/__init__.py: {new_version}")


def update_cli_py(new_version: str) -> None:
    """Update version in zurch/cli.py."""
    path = Path("zurch/cli.py")
    content = path.read_text(encoding='utf-8')
    
    # Update __version__ line
    content = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content
    )
    
    path.write_text(content, encoding='utf-8')
    print(f"Updated zurch/cli.py: {new_version}")


def update_constants_py(new_version: str) -> None:
    """Update version in zurch/constants.py."""
    path = Path("zurch/constants.py")
    content = path.read_text(encoding='utf-8')
    
    # Update USER_AGENT line
    content = re.sub(
        r'USER_AGENT = "zurch/[^"]+"',
        f'USER_AGENT = "zurch/{new_version}"',
        content
    )
    
    path.write_text(content, encoding='utf-8')
    print(f"Updated zurch/constants.py: {new_version}")


def update_changelog(new_version: str) -> None:
    """Update CHANGELOG.md with new version entry."""
    path = Path("CHANGELOG.md")
    content = path.read_text(encoding='utf-8')
    
    # Get current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Add new version entry at the top after the header
    new_entry = f"\n## [{new_version}] - {current_date}\n\n- Version bump to {new_version}\n"
    
    # Find where to insert (after the main header)
    lines = content.split('\n')
    insert_index = 0
    
    # Find the first ## entry (existing version)
    for i, line in enumerate(lines):
        if line.startswith('## ['):
            insert_index = i
            break
    
    # Insert new version entry
    lines.insert(insert_index, new_entry.strip())
    
    # Join and write back
    content = '\n'.join(lines)
    path.write_text(content, encoding='utf-8')
    print(f"Updated CHANGELOG.md: {new_version}")


def validate_version(version: str) -> bool:
    """Validate version format."""
    try:
        parse_version(version)
        return True
    except ValueError:
        return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Synchronize version numbers across all project files"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "version",
        nargs="?",
        help="New version number (e.g., 1.2.3)"
    )
    group.add_argument(
        "--patch",
        action="store_true",
        help="Auto-increment patch version"
    )
    group.add_argument(
        "--minor",
        action="store_true",
        help="Auto-increment minor version"
    )
    group.add_argument(
        "--major",
        action="store_true",
        help="Auto-increment major version"
    )
    
    args = parser.parse_args()
    
    try:
        current_version = get_current_version()
        print(f"Current version: {current_version}")
        
        # Determine new version
        if args.version:
            new_version = args.version
            if not validate_version(new_version):
                print(f"Error: Invalid version format: {new_version}")
                print("Version must be in format: major.minor.patch (e.g., 1.2.3)")
                sys.exit(1)
        elif args.patch:
            new_version = increment_version(current_version, "patch")
        elif args.minor:
            new_version = increment_version(current_version, "minor")
        elif args.major:
            new_version = increment_version(current_version, "major")
        else:
            print("Error: No version specified")
            sys.exit(1)
        
        print(f"New version: {new_version}")
        
        # Confirm with user
        response = input("Update version? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Version update cancelled.")
            sys.exit(0)
        
        # Update all files
        print("\nUpdating files...")
        update_pyproject_toml(new_version)
        update_init_py(new_version)
        update_cli_py(new_version)
        update_constants_py(new_version)
        update_changelog(new_version)
        
        print(f"\n✅ Successfully updated all files to version {new_version}")
        print("\nNext steps:")
        print("1. Review the changes with: git diff")
        print("2. Test the application to ensure it works correctly")
        print("3. Commit the changes: git add -A && git commit -m 'Bump version to {}'".format(new_version))
        print("4. Tag the release: git tag v{}".format(new_version))
        print("5. Push changes and tags: git push && git push --tags")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()