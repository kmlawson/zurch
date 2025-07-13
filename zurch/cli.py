import argparse
import sys
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from .utils import (
    load_config, save_config, format_attachment_icon, format_item_type_icon, format_attachment_link_icon,
    find_zotero_database, pad_number, highlight_search_term, format_duplicate_title
)
from .search import ZoteroDatabase, ZoteroItem, DatabaseError, DatabaseLockedError
from .interactive import interactive_collection_selection
from .duplicates import deduplicate_items, deduplicate_grouped_items

__version__ = "0.5.1"

def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_parser():
    parser = argparse.ArgumentParser(
        description="Zurch - A CLI search tool for Zotero installations",
        prog="zurch"
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
        nargs='+',
        help="List items in the specified folder (spaces allowed without quotes, use quotes for special chars: ' \" $ ` \\ ( ) [ ] { } | & ; < > * ?)"
    )
    
    parser.add_argument(
        "-n", "--name", 
        type=str,
        nargs='+',
        help="Search for items by name/title (spaces allowed without quotes, use quotes for special chars: ' \" $ ` \\ ( ) [ ] { } | & ; < > * ?)"
    )
    
    parser.add_argument(
        "-l", "--list", 
        type=str,
        nargs='?',
        const='',
        help="List all folders and sub-folders, optionally filtered by pattern (supports %% wildcard, partial match by default)"
    )
    
    parser.add_argument(
        "-k", "--exact", 
        action="store_true",
        help="Use exact search instead of partial matching"
    )
    
    parser.add_argument(
        "-o", "--only-attachments", 
        action="store_true",
        help="Show only items that have PDF or EPUB attachments"
    )
    
    parser.add_argument(
        "--id", 
        type=int,
        help="Show metadata for a specific item ID"
    )
    
    parser.add_argument(
        "--no-dedupe", 
        action="store_true",
        help="Disable automatic deduplication of results"
    )
    
    return parser

def display_items(items: List[ZoteroItem], max_results: int, search_term: str = "") -> None:
    """Display items with numbering and icons."""
    for i, item in enumerate(items[:max_results], 1):
        # Item type icon (books and journal articles)
        type_icon = format_item_type_icon(item.item_type, item.is_duplicate)
        
        # Link icon for PDF/EPUB attachments
        attachment_icon = format_attachment_link_icon(item.attachment_type)
        
        number = pad_number(i, min(len(items), max_results))
        title = highlight_search_term(item.title, search_term) if search_term else item.title
        title = format_duplicate_title(title, item.is_duplicate)
        print(f"{number}. {type_icon}{attachment_icon}{title}")

def display_grouped_items(grouped_items: List[tuple], max_results: int, search_term: str = "") -> List[ZoteroItem]:
    """Display items grouped by collection with separators. Returns flat list for interactive mode."""
    all_items = []
    item_counter = 1
    
    for i, (collection, items) in enumerate(grouped_items):
        if item_counter > max_results:
            break
            
        # Add spacing between collections (except for the first one)
        if i > 0:
            print()
        
        # Collection header
        print(f"=== {collection.full_path} ({len(items)} items) ===")
        
        # Display items in this collection
        for item in items:
            if item_counter > max_results:
                break
                
            # Item type icon (books and journal articles)
            type_icon = format_item_type_icon(item.item_type, item.is_duplicate)
            
            # Link icon for PDF/EPUB attachments
            attachment_icon = format_attachment_link_icon(item.attachment_type)
            
            number = pad_number(item_counter, max_results)
            title = highlight_search_term(item.title, search_term) if search_term else item.title
            title = format_duplicate_title(title, item.is_duplicate)
            print(f"{number}. {type_icon}{attachment_icon}{title}")
            
            all_items.append(item)
            item_counter += 1
    
    return all_items

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

def display_hierarchical_search_results(collections: List, search_term: str, max_results: int = None) -> None:
    """Display search results in hierarchical format showing parent structure."""
    from .search import ZoteroCollection
    
    # Build a hierarchy tree from the collections
    hierarchy = {}
    displayed_count = 0
    
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
        nonlocal displayed_count
        indent = "  " * depth
        
        for name, data in sorted(level_dict.items()):
            # Check if we've reached the limit
            if max_results and displayed_count >= max_results:
                return
                
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
                    if is_match:  # Only count actual matches, not parent nodes
                        displayed_count += 1
                else:
                    # This is a parent node - show it if it has matching children
                    if has_matching_children:
                        highlighted_name = highlight_search_term(name, search_term)
                        print(f"{indent}{highlighted_name}")
                
                # Recursively print children
                if data['_children'] and (not max_results or displayed_count < max_results):
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

def interactive_selection(items: List[ZoteroItem]) -> tuple[Optional[ZoteroItem], bool]:
    """Handle interactive item selection.
    
    Returns (item, should_grab) tuple.
    User can append 'g' to number to grab attachment: "3g"
    """
    if not items:
        return None, False
    
    while True:
        try:
            choice = input(f"\nSelect item number (1-{len(items)}, 0 to cancel, add 'g' to grab: 3g): ").strip()
            if choice == "0":
                return None, False
            
            # Check for 'g' suffix
            should_grab = choice.lower().endswith('g')
            if should_grab:
                choice = choice[:-1]  # Remove 'g'
            
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx], should_grab
            else:
                print(f"Please enter a number between 1 and {len(items)}")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled")
            return None, False
        except EOFError:
            return None, False


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

def format_metadata_field(field_name: str, value: str) -> str:
    """Format a metadata field with bold label."""
    BOLD = '\033[1m'
    RESET = '\033[0m'
    return f"{BOLD}{field_name}:{RESET} {value}"

def show_item_metadata(db: ZoteroDatabase, item: ZoteroItem) -> None:
    """Display full metadata for an item."""
    try:
        metadata = db.get_item_metadata(item.item_id)
        
        print(f"\n--- Metadata for: {item.title} ---")
        print(format_metadata_field("Item Type", metadata.get('itemType', 'Unknown')))
        
        # Display common fields in a nice order
        field_order = ['title', 'abstractNote', 'date', 'language', 'url', 'DOI']
        
        for field in field_order:
            if field in metadata:
                print(format_metadata_field(field.title(), metadata[field]))
        
        # Display creators
        if 'creators' in metadata:
            BOLD = '\033[1m'
            RESET = '\033[0m'
            print(f"{BOLD}Creators:{RESET}")
            for creator in metadata['creators']:
                name_parts = []
                if creator.get('firstName'):
                    name_parts.append(creator['firstName'])
                if creator.get('lastName'):
                    name_parts.append(creator['lastName'])
                name = ' '.join(name_parts) if name_parts else 'Unknown'
                creator_type = creator.get('creatorType', 'Unknown')
                print(f"  {BOLD}{creator_type}:{RESET} {name}")
        
        # Display collections this item belongs to
        collections = db.get_item_collections(item.item_id)
        if collections:
            BOLD = '\033[1m'
            RESET = '\033[0m'
            print(f"{BOLD}Collections:{RESET}")
            for collection in collections:
                print(f"  {collection}")
        
        # Display other fields
        skip_fields = set(field_order + ['itemType', 'creators', 'dateAdded', 'dateModified'])
        other_fields = {k: v for k, v in metadata.items() if k not in skip_fields}
        
        if other_fields:
            BOLD = '\033[1m'
            RESET = '\033[0m'
            print(f"{BOLD}Other fields:{RESET}")
            for field, value in sorted(other_fields.items()):
                print(f"  {BOLD}{field}:{RESET} {value}")
        
        print(format_metadata_field("Date Added", metadata.get('dateAdded', 'Unknown')))
        print(format_metadata_field("Date Modified", metadata.get('dateModified', 'Unknown')))
        
    except Exception as e:
        print(f"Error getting metadata: {e}")

def handle_interactive_mode(db: ZoteroDatabase, items: List[ZoteroItem], grab_mode: bool, config: dict) -> None:
    """Handle interactive item selection and actions."""
    zotero_data_dir = Path(config['zotero_database_path']).parent
    
    while True:
        selected, should_grab = interactive_selection(items)
        if not selected:
            break
        
        # Check if user wants to grab (either via -g flag or 'g' suffix)
        if grab_mode or should_grab:
            grab_attachment(db, selected, zotero_data_dir)
            if grab_mode:  # If -g flag was used, exit after grab
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
    
    if not any([args.folder, args.name, args.list is not None, args.id]):
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
        if args.id:
            # Handle --id flag - show metadata for specific item
            try:
                # Create a dummy ZoteroItem to get basic info first
                metadata = db.get_item_metadata(args.id)
                
                # Get the item's title and type for display
                title = metadata.get('title', 'Untitled')
                item_type = metadata.get('itemType', 'Unknown')
                
                print(f"Item ID {args.id}: {title}")
                print("=" * 60)
                
                # Show all metadata using the existing function
                dummy_item = ZoteroItem(
                    item_id=args.id,
                    title=title,
                    item_type=item_type
                )
                show_item_metadata(db, dummy_item)
                
            except Exception as e:
                print(f"Error: Could not find item with ID {args.id}: {e}")
                return 1
            
            return 0
            
        elif args.list is not None:
            collections = db.list_collections()
            
            # Apply filter if provided
            if args.list:
                filtered_collections = []
                search_term = args.list.lower()
                
                # Check if exact matching is requested via -k flag
                exact_match = args.exact
                
                for collection in collections:
                    collection_name = collection.name.lower()
                    
                    if exact_match:
                        # Exact matching only when -k flag is present
                        if search_term == collection_name:
                            filtered_collections.append(collection)
                    elif '%' in search_term:
                        # Handle % wildcard (convert to SQL LIKE pattern)
                        like_pattern = search_term.replace('%', '*')
                        import fnmatch
                        if fnmatch.fnmatch(collection_name, like_pattern):
                            filtered_collections.append(collection)
                    else:
                        # Default partial matching
                        if search_term in collection_name:
                            filtered_collections.append(collection)
                    
                
                collections = filtered_collections
            
            if collections:
                if args.interactive:
                    # Interactive mode for collection selection
                    selected_collection = interactive_collection_selection(collections[:max_results])
                    if selected_collection:
                        # Run -f on the selected collection
                        items, total_count = db.get_collection_items(selected_collection.name, max_results, args.only_attachments)
                        if args.only_attachments:
                            print(f"\nItems in folder '{selected_collection.name}' (with PDF/EPUB attachments):")
                            if len(items) < total_count:
                                print(f"Showing {len(items)} items with attachments from {total_count} total matches:")
                        else:
                            print(f"\nItems in folder '{selected_collection.name}':")
                            if total_count > max_results:
                                print(f"Showing first {max_results} of {total_count} items:")
                        display_items(items, max_results)
                        
                        if args.grab:
                            handle_interactive_mode(db, items, args.grab, config)
                else:
                    # Non-interactive mode - display hierarchically
                    if args.list:
                        print(f"Collections matching '{args.list}':")
                        if len(collections) > max_results:
                            print(f"Showing first {max_results} of {len(collections)} matches:")
                        display_hierarchical_search_results(collections, args.list, max_results)
                    else:
                        print("Collections and Sub-collections:")
                        if len(collections) > max_results:
                            print(f"Showing first {max_results} of {len(collections)} matches:")
                        display_hierarchical_search_results(collections, "", max_results)
            else:
                print(f"No collections found matching '{args.list}'")
            
            return 0
        
        elif args.folder:
            folder_name = ' '.join(args.folder)
            
            # Check how many collections match
            collections = db.search_collections(folder_name)
            
            if not collections:
                # No exact matches, show suggestions
                similar = db.find_similar_collections(folder_name, 5)
                print(f"No items found in folder '{folder_name}'")
                
                if similar:
                    print("\nSimilar folder names:")
                    for collection in similar:
                        print(f"  {collection.name}")
                return 1
            
            # Use grouped display if multiple collections match
            if len(collections) > 1:
                grouped_items, total_count = db.get_collection_items_grouped(folder_name, max_results, args.only_attachments)
                
                if not grouped_items:
                    print(f"No items found in folders matching '{folder_name}'")
                    return 1
                
                # Apply deduplication if enabled
                duplicates_removed = 0
                if not args.no_dedupe:
                    grouped_items, duplicates_removed = deduplicate_grouped_items(db, grouped_items, args.debug)
                
                if args.only_attachments:
                    print(f"Items in folders matching '{folder_name}' (with PDF/EPUB attachments):")
                else:
                    print(f"Items in folders matching '{folder_name}':")
                
                if total_count > max_results:
                    print(f"Showing first {max_results} of {total_count} total items:")
                if duplicates_removed > 0 and args.debug:
                    print(f"({duplicates_removed} duplicates removed)")
                print()
                
                # Display grouped items and get flat list for interactive mode
                all_items = display_grouped_items(grouped_items, max_results)
                
                if args.interactive:
                    handle_interactive_mode(db, all_items, args.grab, config)
            else:
                # Single collection - use original display
                items, total_count = db.get_collection_items(folder_name, max_results, args.only_attachments)
                
                if not items:
                    print(f"No items found in folder '{folder_name}'")
                    return 1
                
                # Apply deduplication if enabled
                duplicates_removed = 0
                if not args.no_dedupe:
                    items, duplicates_removed = deduplicate_items(db, items, args.debug)
                
                if args.only_attachments:
                    print(f"Items in folder '{folder_name}' (with PDF/EPUB attachments):")
                    if len(items) < total_count:
                        item_word = "item" if len(items) == 1 else "items"
                        print(f"Showing {len(items)} {item_word} with attachments from {total_count} total matches:")
                else:
                    print(f"Items in folder '{folder_name}':")
                    if total_count > max_results:
                        print(f"Showing first {max_results} of {total_count} items:")
                
                if duplicates_removed > 0 and args.debug:
                    print(f"({duplicates_removed} duplicates removed)")
                
                display_items(items, max_results)  # Don't highlight folder name in item titles
                
                if args.interactive:
                    handle_interactive_mode(db, items, args.grab, config)
            
            return 0
        
        elif args.name:
            name_search = ' '.join(args.name)
            items, total_count = db.search_items_by_name(name_search, max_results, exact_match=args.exact, only_attachments=args.only_attachments)
            
            if not items:
                print(f"No items found matching '{name_search}'")
                return 1
            
            # Apply deduplication if enabled
            duplicates_removed = 0
            if not args.no_dedupe:
                items, duplicates_removed = deduplicate_items(db, items, args.debug)
            
            if args.only_attachments:
                print(f"Items matching '{name_search}' (with PDF/EPUB attachments):")
                if len(items) < total_count:
                    item_word = "item" if len(items) == 1 else "items"
                    print(f"Showing {len(items)} {item_word} with attachments from {total_count} total matches:")
            else:
                print(f"Items matching '{name_search}':")
                if total_count > max_results:
                    print(f"Showing first {max_results} of {total_count} items:")
            
            if duplicates_removed > 0 and args.debug:
                print(f"({duplicates_removed} duplicates removed)")
            
            display_items(items, max_results, name_search)
            
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
