import sys
import logging
from pathlib import Path

from .utils import load_config, save_config, find_zotero_database
from .search import ZoteroDatabase
from .database import DatabaseError, DatabaseLockedError
from .parser import create_parser
from .handlers import (
    handle_id_command, handle_getbyid_command, handle_list_command,
    handle_folder_command, handle_search_command
)

__version__ = "0.6.2"

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )












def get_database(config: dict) -> ZoteroDatabase:
    """Get and validate Zotero database connection."""
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
            print("Zotero database not found. Please set the path in config.")
            return None
    
    try:
        return ZoteroDatabase(Path(db_path))
    except DatabaseLockedError as e:
        print(f"Error: {e}")
        return None
    except DatabaseError as e:
        print(f"Database error: {e}")
        return None

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    
    if args.debug:
        logger.debug("Debug mode enabled")
        logger.debug(f"Arguments: {args}")
    
    # Load configuration
    config = load_config()
    
    # Override max_results from command line
    max_results = args.max_results or config.get('max_results', 100)
    
    if not any([args.folder, args.name, args.list is not None, args.id, args.author, args.getbyid]):
        parser.print_help()
        return 1
    
    if args.grab and not args.interactive:
        print("Error: --grab (-g) flag requires --interactive (-i) flag")
        return 1
    
    if args.books and args.articles:
        print("Error: Cannot use both --books and --articles flags together")
        return 1
    
    # Get database connection
    db = get_database(config)
    if not db:
        return 1
    
    try:
        if args.id:
            return handle_id_command(db, args.id)
            
        elif args.getbyid:
            return handle_getbyid_command(db, args.getbyid, config)
            
        elif args.list is not None:
            return handle_list_command(db, args, max_results)
        
        elif args.folder:
            return handle_folder_command(db, args, max_results, config)
        
        elif args.name or args.author:
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
