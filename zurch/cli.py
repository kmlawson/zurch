import sys
import logging
from pathlib import Path

from .utils import find_zotero_database
from .config_pydantic import load_config, save_config
from .search import ZoteroDatabase
from .database import DatabaseError, DatabaseLockedError
from .parser import create_parser
from .handlers import (
    handle_id_command, handle_getbyid_command, handle_getnotes_command, handle_list_command,
    handle_folder_command, handle_search_command, handle_stats_command
)
from .config_wizard import run_config_wizard
from .history_handlers import (
    handle_history_command, handle_save_search_command, handle_load_search_command,
    handle_list_saved_command, handle_delete_search_command
)

__version__ = "0.7.10"


def _handle_save_search_and_history(args, command_type: str, config, result: int) -> None:
    """Handle save-search and history recording.
    
    Args:
        args: Command line arguments
        command_type: Type of command (list, folder, search)
        config: Configuration object
        result: Result code from the command
    """
    if result != 0:
        return  # Don't save failed searches
    
    # Convert config to dict if needed
    config_dict = config.to_dict() if hasattr(config, 'to_dict') else config
    
    # Extract search arguments
    search_args = {}
    if command_type == "list":
        search_args['list'] = args.list
    elif command_type == "folder":
        search_args['folder'] = args.folder
    elif command_type in ["search", "name", "author", "tag"]:
        if args.name:
            search_args['name'] = args.name
        if args.author:
            search_args['author'] = args.author
        if args.tag:
            search_args['tag'] = args.tag
    
    # Add common filters
    if hasattr(args, 'exact') and args.exact:
        search_args['exact'] = args.exact
    if hasattr(args, 'only_attachments') and args.only_attachments:
        search_args['only_attachments'] = args.only_attachments
    if hasattr(args, 'since') and args.since:
        search_args['since'] = args.since
    if hasattr(args, 'between') and args.between:
        search_args['between'] = args.between
    if hasattr(args, 'after') and args.after:
        search_args['after'] = args.after
    if hasattr(args, 'before') and args.before:
        search_args['before'] = args.before
    
    # Handle --save-search
    if hasattr(args, 'save_search') and args.save_search:
        handle_save_search_command(args.save_search, command_type, search_args, config_dict)
    
    # Record in history (with dummy results_count for now)
    from .history_handlers import record_search_in_history
    record_search_in_history(command_type, search_args, 0, config_dict)

def parse_max_results(value: str, config_default: int = 100) -> int:
    """Parse max_results value, handling special cases like 'all' and '0'."""
    if not value:
        return config_default
    
    # Handle string values
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ['all', '0']:
            return 999999999  # Use large number to represent unlimited
        try:
            return int(value)
        except ValueError:
            print(f"Invalid max-results value: {value}. Using default.")
            return config_default
    
    # Handle numeric values
    try:
        return int(value)
    except (ValueError, TypeError):
        return config_default

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )












def get_database(config: dict) -> tuple[ZoteroDatabase, str]:
    """Get and validate Zotero database connection.
    
    Returns: (database_instance, error_type)
    error_type can be: 'success', 'config_missing', 'locked', 'error'
    """
    db_path = getattr(config, 'zotero_database_path', None)
    
    if not db_path:
        # Try to find database automatically
        auto_path = find_zotero_database()
        if auto_path:
            db_path = str(auto_path)
            config['zotero_database_path'] = db_path
            save_config(config)
            print(f"Found Zotero database: {db_path}")
        else:
            print("Zotero database not found. Please run 'zurch --config' to set up.")
            return None, 'config_missing'
    
    try:
        db = ZoteroDatabase(Path(db_path))
        return db, 'success'
    except DatabaseLockedError as e:
        print(f"Error: {e}")
        return None, 'locked'
    except DatabaseError as e:
        print(f"Database error: {e}")
        return None, 'error'

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    
    if args.debug:
        logger.debug("Debug mode enabled")
        logger.debug(f"Arguments: {args}")
    
    # Handle config wizard command
    if args.config:
        return run_config_wizard()
    
    # Load configuration
    config = load_config()
    
    # Handle interactive mode defaults with config support BEFORE history commands
    # Priority: --nointeract > -i explicit > config setting > default (True)
    if args.nointeract:
        args.interactive = False
    elif args.interactive:
        # -i was explicitly used, keep it True
        args.interactive = True
    else:
        # Neither -i nor --nointeract was used, use config setting
        args.interactive = getattr(config, 'interactive_mode', True)
    
    # Handle history-related commands (these don't need database access)
    if args.history:
        return handle_history_command(config.to_dict() if hasattr(config, 'to_dict') else config, interactive=args.interactive)
    
    if args.list_saved:
        return handle_list_saved_command(config.to_dict() if hasattr(config, 'to_dict') else config)
    
    if args.delete_search:
        return handle_delete_search_command(args.delete_search, config.to_dict() if hasattr(config, 'to_dict') else config)
    
    # Handle load-search command
    if args.load_search:
        config_dict = config.to_dict() if hasattr(config, 'to_dict') else config
        loaded_args = handle_load_search_command(args.load_search, config_dict)
        if not loaded_args:
            return 1
        
        # Apply loaded arguments to args object
        for key, value in loaded_args.items():
            if not hasattr(args, key) or getattr(args, key) is None:
                setattr(args, key, value)
    
    # Override max_results from command line, handling special values
    max_results = parse_max_results(args.max_results, getattr(config, 'max_results', 100))
    
    # Interactive mode logic already handled above for history commands
    
    # Apply display defaults from config if not explicitly set on command line
    if not hasattr(args, 'showids') or not args.showids:
        args.showids = getattr(config, 'show_ids', False)
    
    if not hasattr(args, 'showtags') or not args.showtags:
        args.showtags = getattr(config, 'show_tags', False)
    
    if not hasattr(args, 'showyear') or not args.showyear:
        args.showyear = getattr(config, 'show_year', False)
    
    if not hasattr(args, 'showauthor') or not args.showauthor:
        args.showauthor = getattr(config, 'show_author', False)
    
    if not hasattr(args, 'showcreated') or not args.showcreated:
        args.showcreated = getattr(config, 'show_created', False)
    
    if not hasattr(args, 'showmodified') or not args.showmodified:
        args.showmodified = getattr(config, 'show_modified', False)
    
    if not hasattr(args, 'showcollections') or not args.showcollections:
        args.showcollections = getattr(config, 'show_collections', False)
    
    if not hasattr(args, 'only_attachments') or not args.only_attachments:
        args.only_attachments = getattr(config, 'only_attachments', False)
    
    # Handle sort flag - auto-enable related display flags
    if args.sort:
        if args.sort in ['d', 'date']:
            args.showyear = True
        elif args.sort in ['a', 'author']:
            args.showauthor = True
        elif args.sort in ['c', 'created']:
            args.showcreated = True
        elif args.sort in ['m', 'modified']:
            args.showmodified = True
    
    # Check if we have any date filters
    has_date_filters = any([
        getattr(args, 'since', None),
        getattr(args, 'between', None),
        getattr(args, 'after', None),
        getattr(args, 'before', None)
    ])
    
    if not any([args.folder, args.name, args.list is not None, args.id, args.author, args.getbyid, args.getnotes, args.tag, args.stats, has_date_filters]):
        parser.print_help()
        return 1
    
    if args.books and args.articles:
        print("Error: Cannot use both --books and --articles flags together")
        return 1
    
    # Check for conflicting date filters
    date_filter_count = sum([
        1 if getattr(args, 'between', None) else 0,
        1 if getattr(args, 'since', None) else 0,
        1 if getattr(args, 'after', None) or getattr(args, 'before', None) else 0
    ])
    
    if date_filter_count > 1:
        print("Error: Cannot use --between with --since, --after, or --before flags")
        print("Use either --between for a date range, or --since for relative dates, or --after/--before for absolute dates")
        return 1
    
    if args.export and not any([args.folder, args.name, args.author, args.tag]):
        print("Error: --export flag requires a search command (-f, -n, -a, or -t)")
        return 1
    
    if args.file and not args.export:
        print("Error: --file flag requires --export flag")
        return 1
    
    # Get database connection
    db, error_type = get_database(config)
    
    if error_type == 'config_missing':
        print("\n=== First Time Setup ===")
        print("It looks like you haven't configured zurch yet.")
        print("Let's set up your Zotero database connection.")
        
        # Auto-launch config wizard
        print("\nRunning configuration wizard...")
        wizard_result = run_config_wizard()
        
        if wizard_result != 0:
            print("Configuration setup cancelled or failed.")
            return 1
        
        # Reload config after wizard
        config = load_config()
        db, error_type = get_database(config)
        
        if error_type != 'success':
            print("\nError: Could not establish database connection even after configuration.")
            print("Please check your Zotero installation and try again.")
            return 1
        
        print("\nSetup complete! You can now use zurch to search your Zotero library.")
        print("Try 'zurch --help' to see all available commands.")
        print("")
    
    elif error_type == 'locked':
        print("\nPlease close Zotero and try again.")
        return 1
    
    elif error_type == 'error':
        print("\nDatabase error occurred. Please check your Zotero installation.")
        return 1
    
    try:
        if args.stats:
            return handle_stats_command(db)
            
        elif args.id:
            return handle_id_command(db, args.id, show_notes=args.shownotes)
            
        elif args.getbyid:
            return handle_getbyid_command(db, args.getbyid, config)
            
        elif args.getnotes:
            return handle_getnotes_command(db, args.getnotes, args.file)
            
        elif args.list is not None:
            result = handle_list_command(db, args, max_results)
            _handle_save_search_and_history(args, "list", config, result)
            return result
        
        elif args.folder:
            result = handle_folder_command(db, args, max_results, config)
            _handle_save_search_and_history(args, "folder", config, result)
            return result
        
        elif args.name or args.author or args.tag:
            result = handle_search_command(db, args, max_results, config)
            # Determine the primary command type for history
            if args.name:
                command_type = "name"
            elif args.author:
                command_type = "author"
            elif args.tag:
                command_type = "tag"
            else:
                command_type = "search"
            _handle_save_search_and_history(args, command_type, config, result)
            return result
        
        elif has_date_filters:
            # Handle standalone date filters (search all items with date constraints)
            result = handle_search_command(db, args, max_results, config)
            _handle_save_search_and_history(args, "date_filter", config, result)
            return result
        
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            raise
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
