import shutil
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)
from .search import ZoteroDatabase
from .models import ZoteroItem, ZoteroCollection
from .display import (
    display_items, display_grouped_items, display_hierarchical_search_results, 
    show_item_metadata, display_database_stats
)
from .interactive import interactive_collection_selection
from .duplicates import deduplicate_items, deduplicate_grouped_items

def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """Sanitize filename for cross-platform compatibility."""
    # Remove or replace invalid characters for Windows, macOS, and Linux
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    
    # Trim whitespace
    filename = filename.strip()
    
    # Truncate if too long, but try to preserve extension
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    return filename

def generate_attachment_filename(db: ZoteroDatabase, item: ZoteroItem, original_filename: str) -> str:
    """Generate a better filename for attachments using author and title."""
    # Get item metadata to access author information
    try:
        metadata = db.get_item_metadata(item.item_id)
        creators = metadata.get("creators", [])
        title = metadata.get("title", item.title)
        
        # Get the file extension from original filename
        original_path = Path(original_filename)
        extension = original_path.suffix
        
        # Extract author last name (prefer first author)
        author_lastname = None
        for creator in creators:
            if creator.get("creatorType") == "author" and creator.get("lastName"):
                author_lastname = creator["lastName"]
                break
        
        # Build the filename
        filename_parts = []
        
        # Add author if available
        if author_lastname:
            filename_parts.append(author_lastname)
        
        # Add title (truncated if necessary)
        if title:
            # Calculate remaining length for title
            base_length = 100  # Base max length
            if author_lastname:
                base_length -= len(author_lastname) + 3  # Account for " - "
            base_length -= len(extension)  # Account for extension
            
            # Truncate title if needed
            if len(title) > base_length:
                title = title[:base_length-3] + "..."
            
            filename_parts.append(title)
        
        # Join parts with " - "
        if filename_parts:
            filename = " - ".join(filename_parts)
        else:
            # Fallback to original filename without extension
            filename = original_path.stem
        
        # Add extension back
        filename += extension
        
        # Sanitize the filename
        filename = sanitize_filename(filename)
        
        # Ensure we have a valid filename
        if not filename or filename == extension:
            filename = original_filename
        
        return filename
        
    except Exception as e:
        logger.warning(f"Could not generate filename for item {item.item_id}: {e}")
        return original_filename

def grab_attachment(db: ZoteroDatabase, item: ZoteroItem, zotero_data_dir: Path) -> bool:
    """Copy attachment file to current directory with improved filename."""
    attachment_path = db.get_item_attachment_path(item.item_id, zotero_data_dir)
    
    if not attachment_path:
        print(f"No attachment found for '{item.title}'")
        return False
    
    try:
        # Generate a better filename using author and title
        new_filename = generate_attachment_filename(db, item, attachment_path.name)
        target_path = Path.cwd() / new_filename
        
        # Handle filename conflicts by adding a number suffix
        counter = 1
        original_target = target_path
        while target_path.exists():
            stem = original_target.stem
            suffix = original_target.suffix
            target_path = Path.cwd() / f"{stem} ({counter}){suffix}"
            counter += 1
        
        shutil.copy2(attachment_path, target_path)
        print(f"Copied attachment to: {target_path}")
        return True
    except Exception as e:
        print(f"Error copying attachment: {e}")
        return False

def interactive_selection(items, max_results: int = 100, search_term: str = "", grouped_items = None, show_ids: bool = False, show_tags: bool = False, db=None):
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
                    display_grouped_items(grouped_items, max_results, search_term, show_ids, show_tags, db)
                else:
                    display_items(items, max_results, search_term, show_ids, show_tags, db)
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

def handle_interactive_mode(db: ZoteroDatabase, items, grab_mode: bool, config: dict, max_results: int = 100, search_term: str = "", grouped_items = None, show_ids: bool = False, show_tags: bool = False) -> None:
    """Handle interactive item selection and actions."""
    zotero_data_dir = Path(config['zotero_database_path']).parent
    
    while True:
        selected, should_grab = interactive_selection(items, max_results, search_term, grouped_items, show_ids, show_tags, db)
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
    
    # Handle "/" suffix for showing sub-collections
    show_subcolls = search_term.endswith('/')
    if show_subcolls:
        search_term = search_term[:-1]  # Remove the trailing "/"
    
    filtered_collections = []
    search_term_lower = search_term.lower()
    
    # First, find collections that match the search term
    matching_collections = []
    for collection in collections:
        collection_name = collection.name.lower()
        
        if exact_match:
            if search_term_lower == collection_name:
                matching_collections.append(collection)
        elif '%' in search_term:
            # Handle % wildcard (convert to SQL LIKE pattern)
            like_pattern = search_term.replace('%', '*')
            import fnmatch
            if fnmatch.fnmatch(collection_name, like_pattern):
                matching_collections.append(collection)
        else:
            # Default partial matching
            if search_term_lower in collection_name:
                matching_collections.append(collection)
    
    if show_subcolls:
        # First include the parent collections themselves
        filtered_collections.extend(matching_collections)
        
        # Then find sub-collections of matching collections
        for collection in collections:
            for matched_collection in matching_collections:
                # Check if this collection is a child of the matched collection
                # The full_path already includes the collection name, so child paths will start with parent_path + " > "
                parent_path_prefix = matched_collection.full_path + " > "
                if collection.full_path.startswith(parent_path_prefix):
                    filtered_collections.append(collection)
                        
        # Remove duplicates while preserving order
        seen = set()
        filtered_collections = [col for col in filtered_collections if col.collection_id not in seen and not seen.add(col.collection_id)]
    else:
        filtered_collections = matching_collections
    
    return filtered_collections

def handle_interactive_list_mode(db: ZoteroDatabase, collections: List[ZoteroCollection], args, max_results: int, display_search_term: str = "") -> None:
    """Handle interactive collection selection from list command with enhanced browsing."""
    interactive_collection_browser(db, collections, args, max_results, display_search_term)

def interactive_collection_browser(db: ZoteroDatabase, collections: List[ZoteroCollection], args, max_results: int, display_search_term: str = "") -> None:
    """Enhanced interactive collection browser with item selection and navigation."""
    zotero_data_dir = Path(args.zotero_database_path if hasattr(args, 'zotero_database_path') else str(db.db_path)).parent
    
    while True:
        # Select collection
        selected_collection = interactive_collection_selection(collections[:max_results])
        if not selected_collection:
            break
        
        # Get items from selected collection
        items, total_count = db.get_collection_items(
            selected_collection.name, args.only_attachments, 
            args.after, args.before, args.books, args.articles, args.tag
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
        
        if not items:
            print("No items found in this collection.")
            input("\nPress Enter to continue...")
            continue
        
        display_items(items, max_results, show_ids=args.showids, show_tags=args.showtags, db=db)
        
        # Interactive item selection loop
        while True:
            try:
                choice = input(f"\nSelect item number (1-{len(items)}, 0 or Enter to cancel, 'l' to re-list, 'b' to go back, add 'g' to grab: 3g): ").strip()
                
                if choice == "0" or choice == "":
                    return  # Exit completely
                elif choice.lower() == "l":
                    # Re-display the items
                    print()
                    display_items(items, max_results, show_ids=args.showids, show_tags=args.showtags, db=db)
                    continue
                elif choice.lower() == "b":
                    # Go back to collection list
                    break
                
                # Check for 'g' suffix
                should_grab = choice.lower().endswith('g')
                if should_grab:
                    choice = choice[:-1]  # Remove 'g'
                
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    selected_item = items[idx]
                    
                    if should_grab:
                        # Grab attachment
                        attachment_path = db.get_item_attachment_path(selected_item.item_id, zotero_data_dir)
                        if attachment_path:
                            try:
                                target_path = Path.cwd() / attachment_path.name
                                shutil.copy2(attachment_path, target_path)
                                print(f"Copied attachment to: {target_path}")
                            except Exception as e:
                                print(f"Error copying attachment: {e}")
                        else:
                            print(f"No attachment found for '{selected_item.title}'")
                    else:
                        # Show metadata
                        show_item_metadata(db, selected_item)
                else:
                    print(f"Please enter a number between 1 and {len(items)}")
                    
            except (ValueError, KeyboardInterrupt):
                print("\nCancelled")
                return
            except EOFError:
                return

def handle_non_interactive_list_mode(collections: List[ZoteroCollection], search_term: str, max_results: int, show_all_collections: bool = False) -> None:
    """Handle non-interactive list display."""
    if search_term:
        if show_all_collections:
            print(f"Collections in '{search_term}' and all sub-collections:")
        else:
            print(f"Collections matching '{search_term}':")
    else:
        print("Collections and Sub-collections:")
    
    if len(collections) > max_results:
        if search_term:
            print(f"Showing first {max_results} of {len(collections)} matches:")
        else:
            print(f"Showing first {max_results} of {len(collections)} collections:")
    
    # When showing all collections (via "/" feature), pass empty search term to display all
    display_search_term = "" if show_all_collections else (search_term or "")
    display_hierarchical_search_results(collections, display_search_term, max_results)

def handle_list_command(db: ZoteroDatabase, args, max_results: int) -> int:
    """Handle -l/--list command."""
    collections = db.list_collections()
    
    # Apply filter if provided
    collections = filter_collections(collections, args.list, args.exact)
    
    if collections:
        if args.interactive:
            # For interactive mode, we need to adjust the display similarly
            display_search_term = args.list
            if display_search_term and display_search_term.endswith('/'):
                display_search_term = display_search_term[:-1]
            handle_interactive_list_mode(db, collections, args, max_results, display_search_term)
        else:
            # Remove "/" from search term for display purposes
            display_search_term = args.list
            show_all_collections = False
            if display_search_term and display_search_term.endswith('/'):
                display_search_term = display_search_term[:-1]
                show_all_collections = True
            handle_non_interactive_list_mode(collections, display_search_term, max_results, show_all_collections)
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
        args.after, args.before, args.books, args.articles, args.tag
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
    all_items = display_grouped_items(grouped_items, max_results, show_ids=args.showids, show_tags=args.showtags, db=db)
    
    if args.interactive:
        handle_interactive_mode(db, all_items, args.grab, config, max_results, folder_name, grouped_items, args.showids, args.showtags)
    
    return 0

def handle_single_collection(db: ZoteroDatabase, folder_name: str, args, max_results: int, config: dict) -> int:
    """Handle folder command when single collection matches."""
    items, total_count = db.get_collection_items(
        folder_name, args.only_attachments, 
        args.after, args.before, args.books, args.articles, args.tag
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
    display_items(items, max_results, show_ids=args.showids, show_tags=args.showtags, db=db)
    
    if args.interactive:
        handle_interactive_mode(db, items, args.grab, config, max_results, folder_name, show_ids=args.showids, show_tags=args.showtags)
    
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
    
    tag_filters = []
    if args.tag:
        tag_filters.append(f"tags: {' AND '.join(args.tag)}")

    filter_desc = ""
    if args.only_attachments:
        filter_desc = " (with PDF/EPUB attachments)"
    if date_filters:
        filter_desc += f" ({', '.join(date_filters)})"
    if tag_filters:
        filter_desc += f" ({', '.join(tag_filters)})"
    
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
        only_articles=args.articles,
        tags=args.tag
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
    display_items(items, max_results, highlight_term, args.showids, show_tags=args.showtags, db=db)
    
    if args.interactive:
        handle_interactive_mode(db, items, args.grab, config, max_results, search_display, show_ids=args.showids, show_tags=args.showtags)
    
    return 0

def handle_stats_command(db: ZoteroDatabase) -> int:
    """Handle --stats command."""
    try:
        stats = db.get_database_stats()
        display_database_stats(stats, str(db.db_path))
        return 0
    except Exception as e:
        print(f"Error getting database statistics: {e}")
        return 1