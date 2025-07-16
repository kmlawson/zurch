import sys
import logging
from pathlib import Path

from .utils import load_config, save_config, find_zotero_database
from .search import ZoteroDatabase
from .database import DatabaseError, DatabaseLockedError
from .parser import create_parser
from .handlers import (
    handle_id_command, handle_getbyid_command, handle_list_command,
    handle_folder_command, handle_search_command, handle_stats_command
)
from .config_wizard import run_config_wizard

__version__ = "0.7.8"

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
    db_path = config.get('zotero_database_path')
    
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
    
    # Override max_results from command line, handling special values
    max_results = parse_max_results(args.max_results, config.get('max_results', 100))
    
    # Handle interactive mode defaults with config support
    # Priority: --nointeract > -i explicit > config setting > default (True)
    if args.nointeract:
        args.interactive = False
    elif args.interactive:
        # -i was explicitly used, keep it True
        args.interactive = True
    else:
        # Neither -i nor --nointeract was used, use config setting
        args.interactive = config.get('interactive_mode', True)
    
    # Apply display defaults from config if not explicitly set on command line
    if not hasattr(args, 'showids') or not args.showids:
        args.showids = config.get('show_ids', False)
    
    if not hasattr(args, 'showtags') or not args.showtags:
        args.showtags = config.get('show_tags', False)
    
    if not hasattr(args, 'showyear') or not args.showyear:
        args.showyear = config.get('show_year', False)
    
    if not hasattr(args, 'showauthor') or not args.showauthor:
        args.showauthor = config.get('show_author', False)
    
    if not hasattr(args, 'showcreated') or not args.showcreated:
        args.showcreated = config.get('show_created', False)
    
    if not hasattr(args, 'showmodified') or not args.showmodified:
        args.showmodified = config.get('show_modified', False)
    
    if not hasattr(args, 'showcollections') or not args.showcollections:
        args.showcollections = config.get('show_collections', False)
    
    if not hasattr(args, 'only_attachments') or not args.only_attachments:
        args.only_attachments = config.get('only_attachments', False)
    
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
    
    if not any([args.folder, args.name, args.list is not None, args.id, args.author, args.getbyid, args.tag, args.stats]):
        parser.print_help()
        return 1
    
    if args.books and args.articles:
        print("Error: Cannot use both --books and --articles flags together")
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
            return handle_id_command(db, args.id)
            
        elif args.getbyid:
            return handle_getbyid_command(db, args.getbyid, config)
            
        elif args.list is not None:
            return handle_list_command(db, args, max_results)
        
        elif args.folder:
            return handle_folder_command(db, args, max_results, config)
        
        elif args.name or args.author or args.tag:
            return handle_search_command(db, args, max_results, config)
        
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
