import argparse
import sys
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from utils import (
    load_config, save_config, format_attachment_icon, 
    find_zotero_database, pad_number, highlight_search_term
)
from search import ZoteroDatabase, ZoteroItem, DatabaseError, DatabaseLockedError

__version__ = "0.1.0"

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_parser():
    parser = argparse.ArgumentParser(
        description="A CLI tool to interface with Zotero installations",
        prog="clizot"
    )
    
    parser.add_argument(
        "-v", "--version", 
        action="version", 
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "-d", "--debug", 
        action="store_true", 
        help="Enable debug mode with detailed logging"
    )
    
    parser.add_argument(
        "-x", "--max-results", 
        type=int, 
        default=100,
        help="Maximum number of results to return (default: 100)"
    )
    
    parser.add_argument(
        "-i", "--interactive", 
        action="store_true",
        help="Enable interactive mode"
    )
    
    parser.add_argument(
        "-g", "--grab", 
        action="store_true",
        help="Grab attachment and copy to current directory (requires -i)"
    )
    
    parser.add_argument(
        "-f", "--folder", 
        type=str,
        help="List items in the specified folder"
    )
    
    parser.add_argument(
        "-n", "--name", 
        type=str,
        help="Search for items by name/title"
    )
    
    parser.add_argument(
        "-l", "--list", 
        type=str,
        nargs='?',
        const='',
        help="List all folders and sub-folders, optionally filtered by pattern (supports %% wildcard, partial match by default)"
    )
    
    return parser

def display_items(items: List[ZoteroItem], max_results: int, search_term: str = "") -> None:
    """Display items with numbering and icons."""
    for i, item in enumerate(items[:max_results], 1):
        icon = format_attachment_icon(item.attachment_type)
        number = pad_number(i, min(len(items), max_results))
        title = highlight_search_term(item.title, search_term) if search_term else item.title
        print(f"{number}. {title} {icon}")

def matches_search_term(text: str, search_term: str) -> bool:
    """Check if text matches the search term (with wildcard support)."""
    if not search_term or not text:
        return False
    
    text_lower = text.lower()
    search_lower = search_term.lower()
    
    # Handle % wildcards
    if '%' in search_lower:
        # Convert % wildcard to simple pattern matching
        import fnmatch
        pattern = search_lower.replace('%', '*')
        return fnmatch.fnmatch(text_lower, pattern)
    else:
        # Default partial matching
        return search_lower in text_lower

def display_hierarchical_search_results(collections: List, search_term: str) -> None:
    """Display search results in hierarchical format showing parent structure."""
    from search import ZoteroCollection
    
    # Build a hierarchy tree from the collections
    hierarchy = {}
    
    for collection in collections:
        parts = collection.full_path.split(' > ')
        current_level = hierarchy
        
        # Build the nested structure
        for i, part in enumerate(parts):
            if part not in current_level:
                current_level[part] = {
                    '_children': {},
                    '_collection': None,
                    '_is_match': False
                }
            
            # Check if this part matches our search
            if matches_search_term(part, search_term):
                current_level[part]['_is_match'] = True
            
            # If this is the final part, store the collection info
            if i == len(parts) - 1:
                current_level[part]['_collection'] = collection
            
            current_level = current_level[part]['_children']
    
    # Display the hierarchy
    def print_hierarchy(level_dict, depth=0, parent_shown=False):
        indent = "  " * depth
        
        for name, data in sorted(level_dict.items()):
            collection = data['_collection']
            is_match = data['_is_match']
            has_matching_children = has_matches_in_subtree(data['_children'])
            
            # Show this level if:
            # 1. It's a direct match, OR
            # 2. It has matching children and we need to show the path
            should_show = is_match or has_matching_children
            
            if should_show:
                if collection:
                    # This is a leaf node (actual collection)
                    count_info = f" ({collection.item_count} items)" if collection.item_count > 0 else ""
                    highlighted_name = highlight_search_term(name, search_term)
                    print(f"{indent}{highlighted_name}{count_info}")
                else:
                    # This is a parent node - show it if it has matching children
                    if has_matching_children:
                        highlighted_name = highlight_search_term(name, search_term)
                        print(f"{indent}{highlighted_name}")
                
                # Recursively print children
                if data['_children']:
                    print_hierarchy(data['_children'], depth + 1, True)
    
    def has_matches_in_subtree(subtree):
        """Check if any node in the subtree is a match or has matching descendants."""
        for name, data in subtree.items():
            if data['_is_match']:
                return True
            if has_matches_in_subtree(data['_children']):
                return True
        return False
    
    print_hierarchy(hierarchy)

def interactive_selection(items: List[ZoteroItem]) -> Optional[ZoteroItem]:
    """Handle interactive item selection."""
    if not items:
        return None
    
    while True:
        try:
            choice = input(f"\nSelect item number (1-{len(items)}, 0 to cancel): ").strip()
            if choice == "0":
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
            else:
                print(f"Please enter a number between 1 and {len(items)}")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled")
            return None
        except EOFError:
            return None

def grab_attachment(db: ZoteroDatabase, item: ZoteroItem, zotero_data_dir: Path) -> bool:
    """Copy attachment file to current directory."""
    attachment_path = db.get_item_attachment_path(item.item_id, zotero_data_dir)
    
    if not attachment_path:
        print(f"No attachment found for '{item.title}'")
        return False
    
    try:
        target_path = Path.cwd() / attachment_path.name
        shutil.copy2(attachment_path, target_path)
        print(f"Copied attachment to: {target_path}")
        return True
    except Exception as e:
        print(f"Error copying attachment: {e}")
        return False

def show_item_metadata(db: ZoteroDatabase, item: ZoteroItem) -> None:
    """Display full metadata for an item."""
    try:
        metadata = db.get_item_metadata(item.item_id)
        
        print(f"\n--- Metadata for: {item.title} ---")
        print(f"Item Type: {metadata.get('itemType', 'Unknown')}")
        
        # Display common fields in a nice order
        field_order = ['title', 'abstractNote', 'date', 'language', 'url', 'DOI']
        
        for field in field_order:
            if field in metadata:
                print(f"{field.title()}: {metadata[field]}")
        
        # Display creators
        if 'creators' in metadata:
            print("Creators:")
            for creator in metadata['creators']:
                name_parts = []
                if creator.get('firstName'):
                    name_parts.append(creator['firstName'])
                if creator.get('lastName'):
                    name_parts.append(creator['lastName'])
                name = ' '.join(name_parts) if name_parts else 'Unknown'
                creator_type = creator.get('creatorType', 'Unknown')
                print(f"  {creator_type}: {name}")
        
        # Display other fields
        skip_fields = set(field_order + ['itemType', 'creators', 'dateAdded', 'dateModified'])
        other_fields = {k: v for k, v in metadata.items() if k not in skip_fields}
        
        if other_fields:
            print("Other fields:")
            for field, value in sorted(other_fields.items()):
                print(f"  {field}: {value}")
        
        print(f"Date Added: {metadata.get('dateAdded', 'Unknown')}")
        print(f"Date Modified: {metadata.get('dateModified', 'Unknown')}")
        
    except Exception as e:
        print(f"Error getting metadata: {e}")

def handle_interactive_mode(db: ZoteroDatabase, items: List[ZoteroItem], grab_mode: bool, config: dict) -> None:
    """Handle interactive item selection and actions."""
    zotero_data_dir = Path(config['zotero_database_path']).parent
    
    while True:
        selected = interactive_selection(items)
        if not selected:
            break
        
        if grab_mode:
            grab_attachment(db, selected, zotero_data_dir)
            break
        else:
            show_item_metadata(db, selected)

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
    
    if not any([args.folder, args.name, args.list is not None]):
        parser.print_help()
        return 1
    
    if args.grab and not args.interactive:
        print("Error: --grab (-g) flag requires --interactive (-i) flag")
        return 1
    
    # Get database connection
    db = get_database(config)
    if not db:
        return 1
    
    try:
        if args.list is not None:
            collections = db.list_collections()
            
            # Apply filter if provided
            if args.list:
                filtered_collections = []
                search_term = args.list.lower()
                
                # Check if partial matching is enabled (default)
                partial_match = config.get('partial_collection_match', True)
                
                for collection in collections:
                    collection_name = collection.name.lower()
                    
                    # Handle % wildcard (convert to SQL LIKE pattern)
                    if '%' in search_term:
                        # Convert % wildcard to SQL LIKE pattern
                        like_pattern = search_term.replace('%', '*')
                        import fnmatch
                        if fnmatch.fnmatch(collection_name, like_pattern):
                            filtered_collections.append(collection)
                    elif partial_match:
                        # Default partial matching
                        if search_term in collection_name:
                            filtered_collections.append(collection)
                    else:
                        # Exact matching only
                        if search_term == collection_name:
                            filtered_collections.append(collection)
                
                collections = filtered_collections
            
            if collections:
                if args.list:
                    print(f"Collections matching '{args.list}':")
                    display_hierarchical_search_results(collections, args.list)
                else:
                    print("Collections and Sub-collections:")
                    
                    for collection in collections:
                        indent = "  " * collection.depth
                        count_info = f" ({collection.item_count} items)" if collection.item_count > 0 else ""
                        print(f"{indent}{collection.name}{count_info}")
            else:
                print(f"No collections found matching '{args.list}'")
            
            return 0
        
        elif args.folder:
            items = db.get_collection_items(args.folder, max_results)
            
            if not items:
                # No exact matches, show suggestions
                similar = db.find_similar_collections(args.folder, 5)
                print(f"No items found in folder '{args.folder}'")
                
                if similar:
                    print("\nSimilar folder names:")
                    for collection in similar:
                        print(f"  {collection.name}")
                return 1
            
            print(f"Items in folder '{args.folder}':")
            display_items(items, max_results, args.folder)
            
            if args.interactive:
                handle_interactive_mode(db, items, args.grab, config)
            
            return 0
        
        elif args.name:
            items = db.search_items_by_name(args.name, max_results)
            
            if not items:
                print(f"No items found matching '{args.name}'")
                return 1
            
            print(f"Items matching '{args.name}':")
            display_items(items, max_results, args.name)
            
            if args.interactive:
                handle_interactive_mode(db, items, args.grab, config)
            
            return 0
        
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
