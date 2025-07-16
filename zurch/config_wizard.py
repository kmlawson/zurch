"""Interactive configuration wizard for zurch."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from .utils import get_config_file, load_config, save_config, find_zotero_database


def get_user_input(prompt: str, default: str = "", validation_func=None) -> str:
    """Get user input with optional default and validation."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    while True:
        try:
            value = input(full_prompt).strip()
            if not value and default:
                value = default
            
            if validation_func:
                validation_result = validation_func(value)
                if validation_result is not True:
                    print(f"Invalid input: {validation_result}")
                    continue
            
            return value
        except KeyboardInterrupt:
            print("\nConfiguration cancelled.")
            return None
        except EOFError:
            return None


def get_yes_no_input(prompt: str, default: bool = False) -> bool:
    """Get yes/no input from user."""
    default_str = "y" if default else "n"
    choices = "Y/n" if default else "y/N"
    
    while True:
        try:
            value = input(f"{prompt} [{choices}]: ").strip().lower()
            if not value:
                return default
            if value in ['y', 'yes']:
                return True
            elif value in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'")
        except KeyboardInterrupt:
            print("\nConfiguration cancelled.")
            return None
        except EOFError:
            return None


def validate_database_path(path: str) -> bool:
    """Validate that the database path exists and is a SQLite file."""
    if not path:
        return "Path cannot be empty"
    
    db_path = Path(path)
    if not db_path.exists():
        return f"File does not exist: {path}"
    
    if not db_path.is_file():
        return f"Path is not a file: {path}"
    
    if not db_path.suffix == '.sqlite':
        return f"File is not a SQLite database: {path}"
    
    return True


def validate_max_results(value: str) -> bool:
    """Validate max_results is a positive integer."""
    try:
        num = int(value)
        if num <= 0:
            return "Max results must be a positive integer"
        return True
    except ValueError:
        return "Max results must be a number"


def run_config_wizard() -> int:
    """Run the interactive configuration wizard."""
    print("🔧 Zurch Configuration Wizard")
    print("=" * 40)
    print("This wizard will help you configure zurch for your Zotero installation.")
    print("Press Ctrl+C at any time to cancel.\n")
    
    # Load current configuration
    current_config = load_config()
    config_file = get_config_file()
    
    print(f"Configuration will be saved to: {config_file}")
    print()
    
    # Database path configuration
    print("📚 Zotero Database Configuration")
    print("-" * 35)
    
    current_db_path = current_config.get('zotero_database_path', '')
    
    # Try to auto-detect database if not configured
    if not current_db_path:
        auto_db = find_zotero_database()
        if auto_db:
            print(f"Auto-detected Zotero database at: {auto_db}")
            if get_yes_no_input("Use this database?", True):
                current_db_path = str(auto_db)
    
    if current_db_path:
        print(f"Current database path: {current_db_path}")
    
    db_path = get_user_input(
        "Enter path to your Zotero database (zotero.sqlite)",
        current_db_path,
        validate_database_path
    )
    
    if db_path is None:
        return 1
    
    # Max results configuration
    print("\n📊 Search Results Configuration")
    print("-" * 32)
    
    current_max_results = str(current_config.get('max_results', 100))
    print(f"Current max results: {current_max_results}")
    
    max_results = get_user_input(
        "Maximum number of search results to show",
        current_max_results,
        validate_max_results
    )
    
    if max_results is None:
        return 1
    
    # Display options configuration
    print("\n🎨 Display Options")
    print("-" * 18)
    print("Configure default display options for search results:")
    
    display_options = {
        'interactive_mode': ('Enable interactive mode by default', current_config.get('interactive_mode', True)),
        'show_ids': ('Show item IDs by default', current_config.get('show_ids', False)),
        'show_tags': ('Show tags by default', current_config.get('show_tags', False)),
        'show_year': ('Show publication year by default', current_config.get('show_year', False)),
        'show_author': ('Show first author name (first and last) by default', current_config.get('show_author', False)),
        'only_attachments': ('Show only items with attachments by default', current_config.get('only_attachments', False)),
    }
    
    new_display_options = {}
    for key, (description, default) in display_options.items():
        result = get_yes_no_input(description, default)
        if result is None:
            return 1
        new_display_options[key] = result
    
    # Other options
    print("\n⚙️  Other Options")
    print("-" * 16)
    
    debug_default = current_config.get('debug', False)
    debug_mode = get_yes_no_input("Enable debug mode by default", debug_default)
    if debug_mode is None:
        return 1
    
    # Build new configuration
    new_config = {
        'zotero_database_path': db_path,
        'max_results': int(max_results),
        'debug': debug_mode,
        'partial_collection_match': current_config.get('partial_collection_match', True),
        **new_display_options
    }
    
    # Show configuration summary
    print("\n📋 Configuration Summary")
    print("-" * 25)
    print(f"Database path: {new_config['zotero_database_path']}")
    print(f"Max results: {new_config['max_results']}")
    print(f"Debug mode: {new_config['debug']}")
    print(f"Interactive mode: {new_config['interactive_mode']}")
    print(f"Show IDs: {new_config['show_ids']}")
    print(f"Show tags: {new_config['show_tags']}")
    print(f"Show year: {new_config['show_year']}")
    print(f"Show author: {new_config['show_author']}")
    print(f"Only attachments: {new_config['only_attachments']}")
    
    # Confirm and save
    print()
    if get_yes_no_input("Save this configuration?", True):
        try:
            save_config(new_config)
            print(f"✅ Configuration saved successfully to {config_file}")
            return 0
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            return 1
    else:
        print("Configuration not saved.")
        return 1