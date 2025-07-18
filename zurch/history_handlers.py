"""History management handlers for zurch."""

import logging
from datetime import datetime
from typing import Dict, Any

from .history import SearchHistory
from .display import format_date_for_display

logger = logging.getLogger(__name__)


def handle_history_command(config: Dict[str, Any], limit: int = 20, interactive: bool = True) -> int:
    """Handle --history command to show search history.
    
    Args:
        config: Configuration dictionary
        limit: Maximum number of entries to show
        interactive: Whether to allow interactive selection
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        history = SearchHistory(
            enabled=config.get('history_enabled', True),
            max_items=config.get('history_max_items', 100)
        )
        
        entries = history.get_history(limit)
        
        if not entries:
            print("No search history found.")
            return 0
        
        print(f"📚 Search History (showing {len(entries)} entries):")
        print("=" * 50)
        
        for i, entry in enumerate(entries, 1):
            # Build command that can be executed
            command_str = _build_executable_command(entry['command'], entry['args'])
            
            print(f"{i:2d}. {command_str}")
        
        if not interactive:
            return 0
        
        # Interactive selection
        while True:
            try:
                choice = input(f"\nSelect command to execute (1-{len(entries)}, 0 to cancel): ").strip()
                
                if choice == "0" or choice == "":
                    return 0
                
                try:
                    selection = int(choice)
                    if 1 <= selection <= len(entries):
                        selected_entry = entries[selection - 1]
                        # Execute the selected command by loading it
                        loaded_args = selected_entry['args']
                        print(f"\nExecuting: {_build_executable_command(selected_entry['command'], loaded_args)}")
                        print()
                        return _execute_history_command(selected_entry['command'], loaded_args, config)
                    else:
                        print(f"Please enter a number between 1 and {len(entries)}")
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled")
                return 0
        
    except Exception as e:
        logger.error(f"Error showing history: {e}")
        print(f"Error: Failed to show history - {e}")
        return 1


def _execute_history_command(command: str, args: Dict[str, Any], config: Dict[str, Any]) -> int:
    """Execute a command from history.
    
    Args:
        command: Command type
        args: Command arguments
        config: Configuration dictionary
        
    Returns:
        Exit code from command execution
    """
    try:
        # Import here to avoid circular imports
        from .search import ZoteroDatabase
        from .handlers import (
            handle_search_command, handle_folder_command, handle_list_command
        )
        from .utils import find_zotero_database
        from pathlib import Path
        
        # Get database connection
        db_path = config.get('zotero_database_path')
        if not db_path:
            auto_path = find_zotero_database()
            if auto_path:
                db_path = str(auto_path)
            else:
                print("Error: Zotero database not found")
                return 1
        
        db = ZoteroDatabase(Path(db_path))
        
        # Create a mock args object with the history arguments
        class MockArgs:
            def __init__(self, args_dict):
                self.interactive = config.get('interactive_mode', True)
                self.showids = config.get('show_ids', False)
                self.showtags = config.get('show_tags', False)
                self.showyear = config.get('show_year', False)
                self.showauthor = config.get('show_author', False)
                self.showcreated = config.get('show_created', False)
                self.showmodified = config.get('show_modified', False)
                self.showcollections = config.get('show_collections', False)
                self.only_attachments = args_dict.get('only_attachments', False)
                self.exact = args_dict.get('exact', False)
                self.after = args_dict.get('after')
                self.before = args_dict.get('before')
                self.books = args_dict.get('books', False)
                self.articles = args_dict.get('articles', False)
                self.no_dedupe = args_dict.get('no_dedupe', False)
                self.export = None
                self.file = None
                self.sort = None
                self.pagination = False
                self.debug = False
                self.nointeract = False
                
                # Set command-specific arguments
                if 'name' in args_dict:
                    self.name = args_dict['name']
                    if isinstance(self.name, str):
                        self.name = [self.name]
                else:
                    self.name = None
                    
                if 'author' in args_dict:
                    self.author = args_dict['author']
                    if isinstance(self.author, str):
                        self.author = [self.author]
                else:
                    self.author = None
                    
                if 'folder' in args_dict:
                    self.folder = args_dict['folder']
                    if isinstance(self.folder, str):
                        self.folder = [self.folder]
                else:
                    self.folder = None
                    
                if 'list' in args_dict:
                    self.list = args_dict['list']
                else:
                    self.list = None
                    
                if 'tag' in args_dict:
                    self.tag = args_dict['tag']
                    if isinstance(self.tag, str):
                        self.tag = [self.tag]
                else:
                    self.tag = None
                    
                # Add date filter attributes
                for attr in ['since', 'between']:
                    setattr(self, attr, args_dict.get(attr))
                
                # Add other optional attributes
                for attr in ['shownotes']:
                    setattr(self, attr, args_dict.get(attr, False))
        
        mock_args = MockArgs(args)
        max_results = config.get('max_results', 100)
        
        # Route to appropriate handler
        if command == 'list':
            return handle_list_command(db, mock_args, max_results)
        elif command == 'folder':
            return handle_folder_command(db, mock_args, max_results, config)
        elif command in ['name', 'author', 'tag', 'search']:
            return handle_search_command(db, mock_args, max_results, config)
        else:
            print(f"Unknown command type: {command}")
            return 1
            
    except Exception as e:
        logger.error(f"Error executing history command: {e}")
        print(f"Error: Failed to execute command - {e}")
        return 1


def handle_save_search_command(name: str, command: str, args: Dict[str, Any], config: Dict[str, Any]) -> int:
    """Handle --save-search command to save current search.
    
    Args:
        name: Name for the saved search
        command: The command type
        args: The search arguments
        config: Configuration dictionary
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        history = SearchHistory(
            enabled=config.get('history_enabled', True),
            max_items=config.get('history_max_items', 100)
        )
        
        if history.save_search(name, command, args):
            print(f"✅ Search saved as '{name}'")
            return 0
        else:
            print(f"❌ Failed to save search '{name}'")
            return 1
            
    except Exception as e:
        logger.error(f"Error saving search: {e}")
        print(f"Error: Failed to save search - {e}")
        return 1


def handle_load_search_command(name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Handle --load-search command to load a saved search.
    
    Args:
        name: Name of the saved search
        config: Configuration dictionary
        
    Returns:
        Dictionary containing the search arguments, or empty dict if not found
    """
    try:
        history = SearchHistory(
            enabled=config.get('history_enabled', True),
            max_items=config.get('history_max_items', 100)
        )
        
        search = history.load_search(name)
        
        if search:
            print(f"📚 Loading saved search '{name}'...")
            command_desc = _format_command_description(search['command'], search['args'])
            print(f"Command: {command_desc}")
            print()
            return search['args']
        else:
            print(f"❌ Saved search '{name}' not found")
            return {}
            
    except Exception as e:
        logger.error(f"Error loading search: {e}")
        print(f"Error: Failed to load search - {e}")
        return {}


def handle_list_saved_command(config: Dict[str, Any]) -> int:
    """Handle --list-saved command to list all saved searches.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        history = SearchHistory(
            enabled=config.get('history_enabled', True),
            max_items=config.get('history_max_items', 100)
        )
        
        searches = history.list_saved_searches()
        
        if not searches:
            print("No saved searches found.")
            return 0
        
        print(f"💾 Saved Searches ({len(searches)} total):")
        print("=" * 40)
        
        for search in searches:
            created = datetime.fromisoformat(search['created'])
            updated = datetime.fromisoformat(search['updated'])
            
            command_desc = _format_command_description(search['command'], search['args'])
            
            print(f"Name: {search['name']}")
            print(f"Command: {command_desc}")
            print(f"Created: {format_date_for_display(created)}")
            if created != updated:
                print(f"Updated: {format_date_for_display(updated)}")
            print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Error listing saved searches: {e}")
        print(f"Error: Failed to list saved searches - {e}")
        return 1


def handle_delete_search_command(name: str, config: Dict[str, Any]) -> int:
    """Handle --delete-search command to delete a saved search.
    
    Args:
        name: Name of the saved search to delete
        config: Configuration dictionary
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        history = SearchHistory(
            enabled=config.get('history_enabled', True),
            max_items=config.get('history_max_items', 100)
        )
        
        if history.delete_saved_search(name):
            print(f"✅ Deleted saved search '{name}'")
            return 0
        else:
            print(f"❌ Saved search '{name}' not found")
            return 1
            
    except Exception as e:
        logger.error(f"Error deleting search: {e}")
        print(f"Error: Failed to delete search - {e}")
        return 1


def _build_executable_command(command: str, args: Dict[str, Any]) -> str:
    """Build an executable command string from history entry.
    
    Args:
        command: The command type
        args: The command arguments
        
    Returns:
        Executable command string
    """
    cmd_parts = ["zurch"]
    
    if command == 'name':
        terms = args.get('name', [])
        if isinstance(terms, list):
            terms = ' '.join(terms)
        cmd_parts.extend(["-n", f'"{terms}"'])
    
    elif command == 'author':
        terms = args.get('author', [])
        if isinstance(terms, list):
            terms = ' '.join(terms)
        cmd_parts.extend(["-a", f'"{terms}"'])
    
    elif command == 'folder':
        folders = args.get('folder', [])
        if isinstance(folders, list):
            folders = ' '.join(folders)
        cmd_parts.extend(["-f", f'"{folders}"'])
    
    elif command == 'list':
        pattern = args.get('list', '')
        if pattern:
            cmd_parts.extend(["-l", f'"{pattern}"'])
        else:
            cmd_parts.append("-l")
    
    elif command in ['tags', 'tag']:
        tags = args.get('tag', [])
        if isinstance(tags, list):
            for tag in tags:
                cmd_parts.extend(["-t", f'"{tag}"'])
        else:
            cmd_parts.extend(["-t", f'"{tags}"'])
    
    elif command == 'search':
        # Generic search command - add all available search criteria
        if args.get('name'):
            name = args['name']
            if isinstance(name, list):
                name = ' '.join(name)
            cmd_parts.extend(["-n", f'"{name}"'])
        if args.get('author'):
            author = args['author']
            if isinstance(author, list):
                author = ' '.join(author)
            cmd_parts.extend(["-a", f'"{author}"'])
        if args.get('tag'):
            tags = args['tag']
            if isinstance(tags, list):
                for tag in tags:
                    cmd_parts.extend(["-t", f'"{tag}"'])
            else:
                cmd_parts.extend(["-t", f'"{tags}"'])
    
    # Add common flags
    if args.get('exact'):
        cmd_parts.append("-k")
    if args.get('only_attachments'):
        cmd_parts.append("-o")
    if args.get('since'):
        cmd_parts.extend(["--since", f'"{args["since"]}"'])
    if args.get('between'):
        cmd_parts.extend(["--between", f'"{args["between"]}"'])
    if args.get('after'):
        cmd_parts.extend(["--after", str(args['after'])])
    if args.get('before'):
        cmd_parts.extend(["--before", str(args['before'])])
    
    return ' '.join(cmd_parts)


def _format_command_description(command: str, args: Dict[str, Any]) -> str:
    """Format a command description for display.
    
    Args:
        command: The command type
        args: The command arguments
        
    Returns:
        Formatted command description
    """
    if command == 'name':
        terms = args.get('name', [])
        if isinstance(terms, list):
            terms = ' '.join(terms)
        return f"Search by name: '{terms}'"
    
    elif command == 'author':
        terms = args.get('author', [])
        if isinstance(terms, list):
            terms = ' '.join(terms)
        return f"Search by author: '{terms}'"
    
    elif command == 'folder':
        folders = args.get('folder', [])
        if isinstance(folders, list):
            folders = ' '.join(folders)
        return f"Browse folder: '{folders}'"
    
    elif command == 'list':
        pattern = args.get('list', '')
        if pattern:
            return f"List collections: '{pattern}'"
        else:
            return "List all collections"
    
    elif command in ['tags', 'tag']:
        tags = args.get('tag', [])
        if isinstance(tags, list):
            tags = ', '.join(tags)
        return f"Search by tags: '{tags}'"
    
    elif command == 'search':
        # Generic search command - try to determine what was searched
        parts = []
        if args.get('name'):
            name = args['name']
            if isinstance(name, list):
                name = ' '.join(name)
            parts.append(f"name: '{name}'")
        if args.get('author'):
            author = args['author']
            if isinstance(author, list):
                author = ' '.join(author)
            parts.append(f"author: '{author}'")
        if args.get('tag'):
            tags = args['tag']
            if isinstance(tags, list):
                tags = ', '.join(tags)
            parts.append(f"tags: '{tags}'")
        
        if parts:
            return f"Search by {', '.join(parts)}"
        else:
            return "Search (no criteria)"
    
    else:
        return f"Unknown command: {command}"


def record_search_in_history(command: str, args: Dict[str, Any], results_count: int, config: Dict[str, Any]) -> None:
    """Record a search in history.
    
    Args:
        command: The command type
        args: The search arguments
        results_count: Number of results found
        config: Configuration dictionary
    """
    try:
        if not config.get('history_enabled', True):
            return
            
        history = SearchHistory(
            enabled=config.get('history_enabled', True),
            max_items=config.get('history_max_items', 100)
        )
        
        # Clean up args to remove None values and non-serializable objects
        clean_args = {}
        for key, value in args.items():
            if value is not None and not callable(value):
                clean_args[key] = value
        
        history.add_to_history(command, clean_args, results_count)
        
    except Exception as e:
        logger.debug(f"Failed to record search in history: {e}")
        # Don't fail the main command if history recording fails