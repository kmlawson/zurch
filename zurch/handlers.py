import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)
from .search import ZoteroDatabase
from .models import ZoteroItem, ZoteroCollection
from .display import (
    display_items, display_grouped_items, display_hierarchical_search_results, 
    show_item_metadata
)
from .interactive import interactive_collection_selection
from .duplicates import deduplicate_items, deduplicate_grouped_items

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

def interactive_selection(items, max_results: int = 100, search_term: str = "", grouped_items = None, show_ids: bool = False):
    """Handle interactive item selection.
    
    Returns (item, should_grab) tuple.
    User can append 'g' to number to grab attachment: "3g"
    User can type 'l' to re-list all items
    """
    if not items:
        return None, False
    
    while True:
        try:
            choice = input(f"\nSelect item number (1-{len(items)}, 0 to cancel, 'l' to list, add 'g' to grab: 3g): ").strip()
            if choice == "0":
                return None, False
            elif choice.lower() == "l":
                # Re-display the items
                print()
                if grouped_items:
                    display_grouped_items(grouped_items, max_results, search_term, show_ids)
                else:
                    display_items(items, max_results, search_term, show_ids)
                continue
            
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

def handle_interactive_mode(db: ZoteroDatabase, items, grab_mode: bool, config: dict, max_results: int = 100, search_term: str = "", grouped_items = None, show_ids: bool = False) -> None:
    """Handle interactive item selection and actions."""
    zotero_data_dir = Path(config['zotero_database_path']).parent
    
    while True:
        selected, should_grab = interactive_selection(items, max_results, search_term, grouped_items, show_ids)
        if not selected:
            break
        
        # Check if user wants to grab (either via -g flag or 'g' suffix)
        if grab_mode or should_grab:
            grab_attachment(db, selected, zotero_data_dir)
            if grab_mode:  # If -g flag was used, exit after grab
                break
        else:
            show_item_metadata(db, selected)

def handle_id_command(db: ZoteroDatabase, item_id: int) -> int:
    """Handle --id flag - show metadata for specific item."""
    try:
        # Create a dummy ZoteroItem to get basic info first
        metadata = db.get_item_metadata(item_id)
        
        # Get the item's title and type for display
        title = metadata.get('title', 'Untitled')
        item_type = metadata.get('itemType', 'Unknown')
        
        print(f"Item ID {item_id}: {title}")
        print("=" * 60)
        
        # Show all metadata using the existing function
        dummy_item = ZoteroItem(
            item_id=item_id,
            title=title,
            item_type=item_type
        )
        show_item_metadata(db, dummy_item)
        
    except Exception as e:
        print(f"Error: Could not find item with ID {item_id}: {e}")
        return 1
    
    return 0

def handle_getbyid_command(db: ZoteroDatabase, item_ids, config: dict) -> int:
    """Handle --getbyid flag - grab attachments for specific item IDs."""
    config_path = Path(config['zotero_database_path']).parent
    success_count = 0
    error_count = 0
    
    for item_id in item_ids:
        try:
            # Get item metadata to show what we're grabbing
            metadata = db.get_item_metadata(item_id)
            title = metadata.get('title', 'Untitled')
            
            # Create a dummy ZoteroItem for the grab function
            dummy_item = ZoteroItem(
                item_id=item_id,
                title=title,
                item_type=metadata.get('itemType', 'Unknown')
            )
            
            print(f"Attempting to grab attachment for ID {item_id}: {title}")
            
            # Try to grab the attachment
            if grab_attachment(db, dummy_item, config_path):
                success_count += 1
            else:
                error_count += 1
                print(f"  → No attachment found for ID {item_id}")
                
        except Exception as e:
            error_count += 1
            print(f"Error with ID {item_id}: {e}")
    
    print(f"\nSummary: {success_count} attachments grabbed, {error_count} failed")
    return 0 if error_count == 0 else 1

def filter_collections(collections: List[ZoteroCollection], search_term: str, exact_match: bool) -> List[ZoteroCollection]:
    """Filter collections based on search criteria."""
    if not search_term:
        return collections
    
    filtered_collections = []
    search_term_lower = search_term.lower()
    
    for collection in collections:
        collection_name = collection.name.lower()
        
        if exact_match:
            if search_term_lower == collection_name:
                filtered_collections.append(collection)
        elif '%' in search_term:
            # Handle % wildcard (convert to SQL LIKE pattern)
            like_pattern = search_term.replace('%', '*')
            import fnmatch
            if fnmatch.fnmatch(collection_name, like_pattern):
                filtered_collections.append(collection)
        else:
            # Default partial matching
            if search_term_lower in collection_name:
                filtered_collections.append(collection)
    
    return filtered_collections

def handle_interactive_list_mode(db: ZoteroDatabase, collections: List[ZoteroCollection], args, max_results: int) -> None:
    """Handle interactive collection selection from list command."""
    selected_collection = interactive_collection_selection(collections[:max_results])
    if not selected_collection:
        return
    
    # Get items from selected collection
    items, total_count = db.get_collection_items(
        selected_collection.name, args.only_attachments, 
        args.after, args.before, args.books, args.articles
    )
    
    # Display results
    if args.only_attachments:
        print(f"\nItems in folder '{selected_collection.name}' (with PDF/EPUB attachments):")
        if len(items) < total_count:
            print(f"Showing {len(items)} items with attachments from {total_count} total matches:")
    else:
        print(f"\nItems in folder '{selected_collection.name}':")
        if total_count > max_results:
            print(f"Showing first {max_results} of {total_count} items:")
    
    display_items(items, max_results, show_ids=args.showids)
    
    if args.grab:
        handle_interactive_mode(
            db, items, args.grab, 
            {'zotero_database_path': str(db.db_path)}, 
            max_results, show_ids=args.showids
        )

def handle_non_interactive_list_mode(collections: List[ZoteroCollection], search_term: str, max_results: int) -> None:
    """Handle non-interactive list display."""
    if search_term:
        print(f"Collections matching '{search_term}':")
    else:
        print("Collections and Sub-collections:")
    
    if len(collections) > max_results:
        print(f"Showing first {max_results} of {len(collections)} matches:")
    
    display_hierarchical_search_results(collections, search_term or "", max_results)

def handle_list_command(db: ZoteroDatabase, args, max_results: int) -> int:
    """Handle -l/--list command."""
    collections = db.list_collections()
    
    # Apply filter if provided
    collections = filter_collections(collections, args.list, args.exact)
    
    if collections:
        if args.interactive:
            handle_interactive_list_mode(db, collections, args, max_results)
        else:
            handle_non_interactive_list_mode(collections, args.list, max_results)
    else:
        print(f"No collections found matching '{args.list}'")
    
    return 0

def show_collection_suggestions(folder_name: str, similar_collections: List[ZoteroCollection]) -> None:
    """Display suggestions for similar collection names."""
    print(f"No items found in folder '{folder_name}'")
    
    if similar_collections:
        print("\nSimilar folder names:")
        for collection in similar_collections:
            print(f"  {collection.name}")

def apply_deduplication_and_limit(items: List[ZoteroItem], db: ZoteroDatabase, args, max_results: int) -> Tuple[List[ZoteroItem], int, int, int]:
    """Apply deduplication and limit to items.
    
    Returns: (final_items, duplicates_removed, items_before_limit, items_final)
    """
    duplicates_removed = 0
    if not args.no_dedupe:
        items, duplicates_removed = deduplicate_items(db, items, args.debug)
    
    items_before_limit = len(items)
    items = items[:max_results]
    items_final = len(items)
    
    return items, duplicates_removed, items_before_limit, items_final

def display_folder_results(folder_name: str, items_final: int, items_before_limit: int, 
                          duplicates_removed: int, total_count: int, args) -> None:
    """Display folder search results with count information."""
    if args.only_attachments:
        print(f"Items in folder '{folder_name}' (with PDF/EPUB attachments):")
    else:
        print(f"Items in folder '{folder_name}':")
    
    # Show clear count information
    if items_final < items_before_limit:
        if duplicates_removed > 0:
            print(f"Showing {items_final} of {items_before_limit} items ({duplicates_removed} duplicates removed, {total_count} total found):")
        else:
            print(f"Showing first {items_final} of {items_before_limit} items:")
    elif duplicates_removed > 0:
        print(f"Showing {items_final} items ({duplicates_removed} duplicates removed from {total_count} total found):")
    
    if duplicates_removed > 0 and args.debug:
        print(f"(Debug: {duplicates_removed} duplicates removed)")

def handle_multiple_collections(db: ZoteroDatabase, folder_name: str, args, max_results: int, config: dict) -> int:
    """Handle folder command when multiple collections match."""
    grouped_items, total_count = db.get_collection_items_grouped(
        folder_name, args.only_attachments, 
        args.after, args.before, args.books, args.articles
    )
    
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
    all_items = display_grouped_items(grouped_items, max_results, show_ids=args.showids)
    
    if args.interactive:
        handle_interactive_mode(db, all_items, args.grab, config, max_results, folder_name, grouped_items, args.showids)
    
    return 0

def handle_single_collection(db: ZoteroDatabase, folder_name: str, args, max_results: int, config: dict) -> int:
    """Handle folder command when single collection matches."""
    items, total_count = db.get_collection_items(
        folder_name, args.only_attachments, 
        args.after, args.before, args.books, args.articles
    )
    
    if not items:
        print(f"No items found in folder '{folder_name}'")
        return 1
    
    # Apply deduplication and limit
    items, duplicates_removed, items_before_limit, items_final = apply_deduplication_and_limit(
        items, db, args, max_results
    )
    
    # Display results
    display_folder_results(folder_name, items_final, items_before_limit, duplicates_removed, total_count, args)
    display_items(items, max_results, show_ids=args.showids)
    
    if args.interactive:
        handle_interactive_mode(db, items, args.grab, config, max_results, folder_name, show_ids=args.showids)
    
    return 0

def handle_folder_command(db: ZoteroDatabase, args, max_results: int, config: dict) -> int:
    """Handle -f/--folder command."""
    folder_name = ' '.join(args.folder)
    
    # Check how many collections match
    collections = db.search_collections(folder_name)
    
    if not collections:
        similar = db.find_similar_collections(folder_name, 5)
        show_collection_suggestions(folder_name, similar)
        return 1
    
    # Route to appropriate handler based on number of matches
    if len(collections) > 1:
        return handle_multiple_collections(db, folder_name, args, max_results, config)
    else:
        return handle_single_collection(db, folder_name, args, max_results, config)

def process_search_parameters(args) -> Tuple[Any, Any, str]:
    """Process name and author search parameters.
    
    Returns: (name_search, author_search, search_display)
    """
    name_search = None
    author_search = None
    search_parts = []
    
    # Process name search if provided
    if args.name:
        if len(args.name) > 1 and not args.exact:
            # Multiple unquoted keywords: use AND search
            name_search = args.name  # Pass as list for AND logic
            search_parts.append(' AND '.join(args.name))
        else:
            # Single keyword or exact match: use phrase search
            name_search = ' '.join(args.name)
            search_parts.append(name_search)
    
    # Process author search if provided
    if args.author:
        if len(args.author) > 1 and not args.exact:
            # Multiple unquoted keywords: use AND search
            author_search = args.author  # Pass as list for AND logic
            search_parts.append(f"author:({' AND '.join(args.author)})")
        else:
            # Single keyword or exact match: use phrase search
            author_search = ' '.join(args.author)
            search_parts.append(f"author:{author_search}")
    
    search_display = " + ".join(search_parts)
    return name_search, author_search, search_display

def build_filter_description(args) -> str:
    """Build description string for applied filters."""
    date_filters = []
    if args.after:
        date_filters.append(f"after {args.after}")
    if args.before:
        date_filters.append(f"before {args.before}")
    
    filter_desc = ""
    if args.only_attachments:
        filter_desc = " (with PDF/EPUB attachments)"
    if date_filters:
        filter_desc += f" ({', '.join(date_filters)})"
    
    return filter_desc

def display_search_results(search_display: str, items_final: int, items_before_limit: int, 
                          duplicates_removed: int, total_count: int, args) -> None:
    """Display search results with count information."""
    filter_desc = build_filter_description(args)
    print(f"Items matching '{search_display}'{filter_desc}:")
    
    # Show clear count information
    if items_final < items_before_limit:
        if duplicates_removed > 0:
            print(f"Showing {items_final} of {items_before_limit} items ({duplicates_removed} duplicates removed, {total_count} total found):")
        else:
            print(f"Showing first {items_final} of {items_before_limit} items:")
    elif duplicates_removed > 0:
        print(f"Showing {items_final} items ({duplicates_removed} duplicates removed from {total_count} total found):")
    
    if duplicates_removed > 0 and args.debug:
        print(f"(Debug: {duplicates_removed} duplicates removed)")

def get_highlight_term(args, name_search) -> str:
    """Determine highlight term for search results."""
    # For highlighting: only highlight for phrase searches, not AND searches
    if args.name and not isinstance(name_search, list):
        return name_search
    return ""

def handle_search_command(db: ZoteroDatabase, args, max_results: int, config: dict) -> int:
    """Handle -n/--name and -a/--author search commands."""
    # Process search parameters
    name_search, author_search, search_display = process_search_parameters(args)
    
    # Execute search
    items, total_count = db.search_items_combined(
        name=name_search, 
        author=author_search, 
        exact_match=args.exact, 
        only_attachments=args.only_attachments,
        after_year=args.after,
        before_year=args.before,
        only_books=args.books,
        only_articles=args.articles
    )
    
    if not items:
        print(f"No items found matching '{search_display}'")
        return 1
    
    # Apply deduplication and limit
    items, duplicates_removed, items_before_limit, items_final = apply_deduplication_and_limit(
        items, db, args, max_results
    )
    
    # Display results
    display_search_results(search_display, items_final, items_before_limit, duplicates_removed, total_count, args)
    
    highlight_term = get_highlight_term(args, name_search)
    display_items(items, max_results, highlight_term, args.showids)
    
    if args.interactive:
        handle_interactive_mode(db, items, args.grab, config, max_results, search_display, show_ids=args.showids)
    
    return 0