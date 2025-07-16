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
from .export import export_items
from .utils import sort_items
from .pagination import handle_pagination_loop
from .hierarchical_pagination import get_paginated_collections

class DisplayOptions:
    """Container for display options to reduce parameter passing."""
    def __init__(self, args=None, **kwargs):
        if args:
            self.show_ids = getattr(args, 'showids', False)
            self.show_tags = getattr(args, 'showtags', False)
            self.show_year = getattr(args, 'showyear', False)
            self.show_author = getattr(args, 'showauthor', False)
            self.show_created = getattr(args, 'showcreated', False)
            self.show_modified = getattr(args, 'showmodified', False)
            self.show_collections = getattr(args, 'showcollections', False)
            self.sort_by_author = hasattr(args, 'sort') and args.sort and args.sort.lower() in ['a', 'author']
        else:
            self.show_ids = kwargs.get('show_ids', False)
            self.show_tags = kwargs.get('show_tags', False)
            self.show_year = kwargs.get('show_year', False)
            self.show_author = kwargs.get('show_author', False)
            self.show_created = kwargs.get('show_created', False)
            self.show_modified = kwargs.get('show_modified', False)
            self.show_collections = kwargs.get('show_collections', False)
            self.sort_by_author = kwargs.get('sort_by_author', False)

def display_sorted_items(items, max_results, args, db=None, search_term="", display_opts: DisplayOptions = None):
    """Display items with optional sorting and pagination."""
    # Sort items if sort flag is provided
    if hasattr(args, 'sort') and args.sort:
        items = sort_items(items, args.sort, db)
    
    # Use display options or create from args
    if display_opts is None:
        display_opts = DisplayOptions(args)
    
    # Check if pagination is enabled and we have more items than max_results
    if hasattr(args, 'pagination') and args.pagination and len(items) > max_results:
        # Use pagination
        def display_page(page_items, search_term, display_opts, db, max_results):
            display_items(page_items, max_results, search_term, 
                         display_opts.show_ids, display_opts.show_tags, display_opts.show_year, 
                         display_opts.show_author, display_opts.show_created, display_opts.show_modified, 
                         display_opts.show_collections, db=db, sort_by_author=display_opts.sort_by_author)
        
        handle_pagination_loop(items, max_results, display_page, search_term, display_opts, db, max_results)
    else:
        # Normal display with max_results limit
        display_items(items[:max_results], max_results, search_term, 
                     display_opts.show_ids, display_opts.show_tags, display_opts.show_year, 
                     display_opts.show_author, display_opts.show_created, display_opts.show_modified, 
                     display_opts.show_collections, db=db, sort_by_author=display_opts.sort_by_author)


def display_sorted_grouped_items(grouped_items, max_results, args, db=None, search_term="", display_opts: DisplayOptions = None):
    """Display grouped items with optional pagination."""
    # Use display options or create from args
    if display_opts is None:
        display_opts = DisplayOptions(args)
    
    # Flatten grouped items to count total items
    all_items = []
    for collection, items in grouped_items:
        all_items.extend(items)
    
    # Check if pagination is enabled and we have more items than max_results
    if hasattr(args, 'pagination') and args.pagination and len(all_items) > max_results:
        # Use pagination for grouped items
        def display_grouped_page(page_items, search_term, display_opts, db, max_results):
            # Need to reconstruct grouped structure for the page
            reconstructed_groups = []
            current_collection = None
            current_items = []
            
            for item in page_items:
                # Find which collection this item belongs to
                item_collection = None
                for collection, items in grouped_items:
                    if item in items:
                        item_collection = collection
                        break
                
                if item_collection != current_collection:
                    # Save previous group if exists
                    if current_collection is not None and current_items:
                        reconstructed_groups.append((current_collection, current_items))
                    
                    # Start new group
                    current_collection = item_collection
                    current_items = [item]
                else:
                    current_items.append(item)
            
            # Add final group
            if current_collection is not None and current_items:
                reconstructed_groups.append((current_collection, current_items))
            
            # Display the reconstructed groups
            display_grouped_items(reconstructed_groups, max_results, search_term,
                                display_opts.show_ids, display_opts.show_tags, display_opts.show_year,
                                display_opts.show_author, display_opts.show_created, display_opts.show_modified,
                                display_opts.show_collections, db=db, sort_by_author=display_opts.sort_by_author)
        
        handle_pagination_loop(all_items, max_results, display_grouped_page, search_term, display_opts, db, max_results)
    else:
        # Normal grouped display
        display_grouped_items(grouped_items, max_results, search_term,
                            display_opts.show_ids, display_opts.show_tags, display_opts.show_year,
                            display_opts.show_author, display_opts.show_created, display_opts.show_modified,
                            display_opts.show_collections, db=db, sort_by_author=display_opts.sort_by_author)

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

def interactive_selection(items, max_results: int = 100, search_term: str = "", grouped_items = None, display_opts: DisplayOptions = None, db=None, return_index: bool = False, show_go_back: bool = True):
    """Handle interactive item selection with automatic pagination.
    
    Returns (item, should_grab) tuple by default, or (item, should_grab, selected_index) if return_index=True.
    User can append 'g' to number to grab attachment: "3g"
    User can type 'l' to re-list all items
    Automatically enables pagination when total items exceed max_results
    """
    if not items:
        return (None, False, None) if return_index else (None, False)
    
    if display_opts is None:
        display_opts = DisplayOptions()
    
    # Check if we need pagination
    total_items = len(items)
    needs_pagination = total_items > max_results
    
    if needs_pagination:
        return interactive_selection_with_pagination(items, max_results, search_term, grouped_items, display_opts, db, return_index, show_go_back)
    else:
        return interactive_selection_simple(items, max_results, search_term, grouped_items, display_opts, db, return_index, show_go_back)


def interactive_selection_simple(items, max_results: int, search_term: str, grouped_items, display_opts: DisplayOptions, db, return_index: bool, show_go_back: bool = True):
    """Simple interactive selection without pagination."""
    first_display = True
    
    while True:
        # Show items on first display or when user asks to re-list
        if first_display:
            first_display = False
            if grouped_items:
                display_grouped_items(grouped_items, max_results, search_term, 
                                     display_opts.show_ids, display_opts.show_tags, display_opts.show_year, 
                                     display_opts.show_author, display_opts.show_created, display_opts.show_modified, 
                                     display_opts.show_collections, db=db, sort_by_author=display_opts.sort_by_author)
            else:
                display_items(items, max_results, search_term, 
                             display_opts.show_ids, display_opts.show_tags, display_opts.show_year, 
                             display_opts.show_author, display_opts.show_created, display_opts.show_modified, 
                             display_opts.show_collections, db=db, sort_by_author=display_opts.sort_by_author)
        try:
            # Try to use immediate key response for navigation keys
            from .keyboard import get_input_with_immediate_keys, is_terminal_interactive
            
            # Build prompt dynamically based on context
            prompt_parts = [f"Select item number (1-{len(items)}", "0 to cancel"]
            if show_go_back:
                prompt_parts.append("'l' to go back")
            prompt_parts.append("add 'g' to grab: 3g")
            prompt = "\n" + ", ".join(prompt_parts) + "): "
            
            if is_terminal_interactive():
                # Define keys that should respond immediately
                immediate_keys = set()
                first_char_only_immediate = {'0'}
                if show_go_back:
                    immediate_keys.update({'l', 'L'})
                choice = get_input_with_immediate_keys(prompt, immediate_keys, first_char_only_immediate).strip()
            else:
                # Fallback to regular input (e.g., when piping input)
                choice = input(prompt).strip()
            
            if choice == "0" or choice == "":
                return (None, False, None) if return_index else (None, False)
            elif choice.lower() == "l" and show_go_back:
                # Return special marker to indicate "go back"
                return ("GO_BACK", False, None) if return_index else ("GO_BACK", False)
            
            # Check for 'g' suffix
            should_grab = choice.lower().endswith('g')
            if should_grab:
                choice = choice[:-1]  # Remove 'g'
            
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return (items[idx], should_grab, idx) if return_index else (items[idx], should_grab)
            else:
                print(f"Please enter a number between 1 and {len(items)}")
        except ValueError:
            print("Invalid input. Please enter a number or valid command.")
            continue
        except KeyboardInterrupt:
            print("\nCancelled")
            return (None, False, None) if return_index else (None, False)
        except EOFError:
            return (None, False, None) if return_index else (None, False)


def interactive_selection_with_pagination(items, max_results: int, search_term: str, grouped_items, display_opts: DisplayOptions, db, return_index: bool, show_go_back: bool = True):
    """Interactive selection with pagination support."""
    total_items = len(items)
    total_pages = (total_items + max_results - 1) // max_results
    current_page = 0
    first_display = True
    
    # Track if we need to display the page
    need_display = True
    
    while True:
        # Calculate page boundaries
        start_idx = current_page * max_results
        end_idx = min(start_idx + max_results, total_items)
        page_items = items[start_idx:end_idx]
        
        # Display current page only when needed
        if need_display:
            if first_display:
                first_display = False
            else:
                print()
            if grouped_items:
                # For grouped items, we need to reconstruct the groups for this page
                page_grouped = []
                current_collection = None
                current_items = []
                
                for item in page_items:
                    # Find which collection this item belongs to
                    item_collection = None
                    for collection, collection_items in grouped_items:
                        if item in collection_items:
                            item_collection = collection
                            break
                    
                    if item_collection != current_collection:
                        # Save previous group if exists
                        if current_collection is not None and current_items:
                            page_grouped.append((current_collection, current_items))
                        
                        # Start new group
                        current_collection = item_collection
                        current_items = [item]
                    else:
                        current_items.append(item)
                
                # Add final group
                if current_collection is not None and current_items:
                    page_grouped.append((current_collection, current_items))
                
                display_grouped_items(page_grouped, max_results, search_term,
                                    display_opts.show_ids, display_opts.show_tags, display_opts.show_year,
                                    display_opts.show_author, display_opts.show_created, display_opts.show_modified,
                                    display_opts.show_collections, db=db, sort_by_author=display_opts.sort_by_author)
            else:
                display_items(page_items, max_results, search_term,
                             display_opts.show_ids, display_opts.show_tags, display_opts.show_year,
                             display_opts.show_author, display_opts.show_created, display_opts.show_modified,
                             display_opts.show_collections, db=db, sort_by_author=display_opts.sort_by_author)
            
            # Show pagination info
            print(f"\nShowing items {start_idx + 1}-{end_idx} of {total_items} total")
            print(f"Page {current_page + 1} of {total_pages}")
            need_display = False
        
        # Build prompt with navigation options
        prompt_parts = [f"Select item number (1-{len(page_items)}"]
        if current_page > 0:
            prompt_parts.append("'b' for back a page")
        if current_page < total_pages - 1:
            prompt_parts.append("'n' for next page")
        # Add navigation options based on context
        if show_go_back:
            prompt_parts.append("'l' to go back")
        prompt_parts.extend(["0 to cancel", "add 'g' to grab"])
        prompt = ", ".join(prompt_parts) + "): "
        
        try:
            # Try to use immediate key response for navigation keys
            from .keyboard import get_input_with_immediate_keys, is_terminal_interactive
            
            if is_terminal_interactive():
                # Define keys that should respond immediately
                immediate_keys = {'n', 'N', 'b', 'B'}
                first_char_only_immediate = {'0'}
                if show_go_back:
                    immediate_keys.update({'l', 'L'})
                choice = get_input_with_immediate_keys(prompt, immediate_keys, first_char_only_immediate).strip()
            else:
                # Fallback to regular input (e.g., when piping input)
                choice = input(prompt).strip()
            
            if choice == "0" or choice == "":
                return (None, False, None) if return_index else (None, False)
            elif choice.lower() == "n" and current_page < total_pages - 1:
                current_page += 1
                need_display = True
                continue
            elif choice.lower() == "b" and current_page > 0:
                current_page -= 1
                need_display = True
                continue
            elif choice.lower() == "n" and current_page >= total_pages - 1:
                print("No more next pages available.")
                # Don't set need_display = True, just re-prompt
                continue
            elif choice.lower() == "b" and current_page <= 0:
                print("No more previous pages available.")
                # Don't set need_display = True, just re-prompt
                continue
            elif choice.lower() == "l" and show_go_back:
                # Return special marker to indicate "go back"
                return ("GO_BACK", False, None) if return_index else ("GO_BACK", False)
            
            # Check for 'g' suffix
            should_grab = choice.lower().endswith('g')
            if should_grab:
                choice = choice[:-1]  # Remove 'g'
            
            idx = int(choice) - 1
            if 0 <= idx < len(page_items):
                selected_item = page_items[idx]
                # Calculate the global index for return_index
                global_idx = start_idx + idx
                return (selected_item, should_grab, global_idx) if return_index else (selected_item, should_grab)
            else:
                print(f"Please enter a number between 1 and {len(page_items)}")
                # Don't set need_display = True, just re-prompt
        except ValueError:
            print("Invalid input. Please enter a number or valid command.")
            continue
        except KeyboardInterrupt:
            print("\nCancelled")
            return (None, False, None) if return_index else (None, False)
        except EOFError:
            return (None, False, None) if return_index else (None, False)

def handle_interactive_mode(db: ZoteroDatabase, items, config: dict, max_results: int = 100, search_term: str = "", grouped_items = None, show_ids: bool = False, show_tags: bool = False, show_year: bool = False, show_author: bool = False, show_created: bool = False, show_modified: bool = False, show_collections: bool = False, sort_by_author: bool = False, show_go_back: bool = True) -> None:
    """Handle interactive item selection and actions."""
    zotero_data_dir = Path(config['zotero_database_path']).parent
    current_index = None  # Track current item for next/previous navigation
    current_page = 0  # Track current page for pagination context
    first_time = True
    
    while True:
        display_opts = DisplayOptions(show_ids=show_ids, show_tags=show_tags, show_year=show_year, show_author=show_author, show_created=show_created, show_modified=show_modified, show_collections=show_collections, sort_by_author=sort_by_author)
        selected, should_grab, selected_index = interactive_selection(items, max_results, search_term, grouped_items, display_opts, db, return_index=True, show_go_back=show_go_back)
        
        # Handle special case of "go back"
        if selected == "GO_BACK":
            return  # Return to previous context
        
        if not selected:
            break
        
        current_index = selected_index
        
        # Check if user wants to grab (via 'g' suffix)
        if should_grab:
            grab_attachment(db, selected, zotero_data_dir)
        else:
            # Show metadata and handle next/previous navigation
            result_index = handle_metadata_navigation(db, items, current_index, zotero_data_dir)
            if result_index == -1:
                break  # Exit completely
            current_index = result_index
            
            # Don't redisplay the list here - let the pagination loop handle it
            # The next iteration will use the preserved current_page

def handle_metadata_navigation(db: ZoteroDatabase, items, current_index: int, zotero_data_dir: Path) -> int:
    """Handle metadata display with next/previous navigation.
    
    Returns the final index after navigation, or current_index if returning to main menu.
    """
    import sys
    
    def get_single_char():
        """Get a single character input without waiting for Enter."""
        try:
            # Try to import and use termios/tty for single character input
            import termios
            import tty
            
            if not sys.stdin.isatty():
                # Fall back to regular input when not in a TTY (e.g., piped input)
                return input().strip()
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                char = sys.stdin.read(1)
                # Handle special keys like Enter
                if ord(char) == 13:  # Enter key
                    char = ""
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return char
        except (ImportError, AttributeError, termios.error, OSError):
            # Fall back to regular input if termios/tty not available or fails
            return input().strip()
    
    while True:
        # Show metadata for current item
        current_item = items[current_index]
        show_item_metadata(db, current_item)
        
        # Check if current item has attachment
        has_attachment = current_item.attachment_type is not None
        
        # Build navigation prompt
        nav_options = []
        if current_index > 0:
            nav_options.append("'b' for previous")
        if current_index < len(items) - 1:
            nav_options.append("'n' for next")
        if has_attachment:
            nav_options.append("'g' to grab attachment")
        nav_options.append("'l' for back to list")
        nav_options.append("'0' or Enter to exit")
        
        nav_text = ", ".join(nav_options)
        
        # Inner loop for input handling that doesn't re-display metadata
        while True:
            try:
                print(f"\nOptions: {nav_text}: ", end='', flush=True)
                choice = get_single_char().lower()
                print(choice if choice else "Enter")  # Echo the choice
                
                if choice == "0" or choice == "":
                    return -1  # Signal to exit completely (0 or Enter)
                elif choice == "l":
                    return current_index  # Return to list
                elif choice == "g" and has_attachment:
                    # Grab attachment for current item
                    grab_attachment(db, current_item, zotero_data_dir)
                    continue  # Stay in input loop, don't re-display metadata
                elif choice == "n" and current_index < len(items) - 1:
                    current_index += 1
                    break  # Break inner loop to show next item metadata
                elif choice == "b" and current_index > 0:
                    current_index -= 1
                    break  # Break inner loop to show previous item metadata
                elif choice == "n" and current_index >= len(items) - 1:
                    print("No more next items available.")
                    continue  # Continue in input loop, don't re-display metadata
                elif choice == "b" and current_index <= 0:
                    print("No more previous items available.")
                    continue  # Continue in input loop, don't re-display metadata
                else:
                    print("Invalid option. Please try again.")
                    continue  # Continue in input loop, don't re-display metadata
                    
            except (KeyboardInterrupt, EOFError):
                return current_index  # Return to main menu on interrupt

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
        else:
            # Use consistent wildcard matching from display.py
            from .display import matches_search_term
            if matches_search_term(collection.name, search_term):
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
    
    # Use hierarchical pagination for interactive mode
    current_page = 0
    
    while True:
        # Get paginated collections maintaining hierarchy
        # If max_results is large enough to show all collections, bypass pagination
        if max_results >= len(collections):
            page_collections = collections
            has_previous = False
            has_next = False
            current_page = 0
            total_pages = 1
        else:
            page_collections, has_previous, has_next, current_page, total_pages = \
                get_paginated_collections(collections, max_results, current_page)
        
        # Display hierarchical collections with numbers for interactive selection
        from .interactive import interactive_collection_selection_with_pagination
        selected_collection = interactive_collection_selection_with_pagination(
            page_collections, current_page, total_pages, has_previous, has_next, display_search_term, len(collections)
        )
        
        # Handle pagination navigation
        if selected_collection == "NEXT_PAGE":
            current_page += 1
            continue
        elif selected_collection == "PREVIOUS_PAGE":
            current_page -= 1
            continue
        elif not selected_collection:
            break
        
        # Get items from selected collection using collection ID
        items = db.items.get_items_in_collection(
            selected_collection.collection_id, args.only_attachments, 
            args.after, args.before, args.books, args.articles, args.tag
        )
        total_count = len(items)
        
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
        
        display_sorted_items(items, max_results, args, db=db)
        
        # Interactive item selection loop
        while True:
            try:
                # Try to use immediate key response for navigation keys
                from .keyboard import get_input_with_immediate_keys, is_terminal_interactive
                
                prompt = f"\nSelect item number (1-{len(items)}, 0 or Enter to cancel, 'l' to go back to collections, add 'g' to grab: 3g): "
                
                if is_terminal_interactive():
                    # Define keys that should respond immediately
                    immediate_keys = {'l', 'L'}
                    first_char_only_immediate = {'0'}
                    choice = get_input_with_immediate_keys(prompt, immediate_keys, first_char_only_immediate).strip()
                else:
                    # Fallback to regular input (e.g., when piping input)
                    choice = input(prompt).strip()
                
                if choice == "0" or choice == "":
                    return  # Exit completely
                elif choice.lower() == "l":
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
                    
            except ValueError:
                print("Invalid input. Please enter a number or valid command.")
                continue
            except KeyboardInterrupt:
                print("\nCancelled")
                return
            except EOFError:
                return

def handle_non_interactive_list_mode(collections: List[ZoteroCollection], search_term: str, max_results: int, show_all_collections: bool = False, args=None) -> None:
    """Handle non-interactive list display."""
    if search_term:
        if show_all_collections:
            print(f"Collections in '{search_term}' and all sub-collections:")
        else:
            print(f"Collections matching '{search_term}':")
    else:
        print("Collections and Sub-collections:")
    
    # When showing all collections (via "/" feature), pass empty search term to display all
    display_search_term = "" if show_all_collections else (search_term or "")
    
    # Check if pagination is enabled and we have more collections than max_results
    if args and hasattr(args, 'pagination') and args.pagination and len(collections) > max_results:
        # Use hierarchical pagination for collections
        current_page = 0
        
        while True:
            # Get paginated collections maintaining hierarchy
            page_collections, has_previous, has_next, current_page, total_pages = \
                get_paginated_collections(collections, max_results, current_page)
            
            # Display the current page
            displayed_count = display_hierarchical_search_results(page_collections, display_search_term, None)
            
            # Calculate how many collections are shown on this page
            print(f"\nShowing {displayed_count} collections")
            print(f"Page {current_page + 1} of {total_pages}")
            
            # If only one page, exit
            if total_pages <= 1:
                break
            
            # Get user input for navigation
            from .pagination import get_pagination_input
            user_input = get_pagination_input(has_previous, has_next)
            
            if user_input == '0' or user_input == '':
                break
            elif user_input == 'n' and has_next:
                current_page += 1
            elif user_input == 'p' and has_previous:
                current_page -= 1
    else:
        # Normal display with limit
        displayed_count = display_hierarchical_search_results(collections, display_search_term, max_results)
        
        # Show count information after display
        if displayed_count > 0:
            if displayed_count < len(collections):
                if search_term:
                    print(f"\nShowing {displayed_count} of {len(collections)} matching collections")
                else:
                    print(f"\nShowing {displayed_count} of {len(collections)} collections")
            else:
                if search_term:
                    print(f"\nShowing {displayed_count} matching collections")
                else:
                    print(f"\nShowing {displayed_count} collections")

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
            handle_non_interactive_list_mode(collections, display_search_term, max_results, show_all_collections, args)
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
    
    # Skip limiting if pagination is enabled - let pagination handle it
    if hasattr(args, 'pagination') and args.pagination:
        items_final = len(items)
    else:
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
    from .spinner import ProgressSpinner
    
    # Get collection count first for progress reporting
    collections = db.search_collections(folder_name, exact_match=args.exact)
    collection_count = len(collections)
    
    with ProgressSpinner(f"Loading items from {collection_count} collections") as spinner:
        grouped_items, total_count = db.get_collection_items_grouped(
            folder_name, args.only_attachments, 
            args.after, args.before, args.books, args.articles, args.tag,
            exact_match=args.exact
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
    sort_by_author = hasattr(args, 'sort') and args.sort and args.sort.lower() in ['a', 'author']
    display_opts = DisplayOptions(args)
    display_sorted_grouped_items(grouped_items, max_results, args, db=db, search_term=folder_name, display_opts=display_opts)
    
    # Get all items for interactive mode
    all_items = []
    for collection, items in grouped_items:
        all_items.extend(items)
    
    # Handle export if requested
    if args.export:
        export_items(all_items, db, args.export, args.file, folder_name)
    
    if args.interactive:
        handle_interactive_mode(db, all_items, config, max_results, folder_name, grouped_items, args.showids, args.showtags, args.showyear, args.showauthor, args.showcreated, args.showmodified, args.showcollections, sort_by_author)
    else:
        # Enable pagination for folder results if requested
        if not hasattr(args, 'pagination'):
            args.pagination = False
    
    return 0

def handle_single_collection(db: ZoteroDatabase, folder_name: str, args, max_results: int, config: dict) -> int:
    """Handle folder command when single collection matches."""
    from .spinner import Spinner
    
    with Spinner(f"Loading items from '{folder_name}'"):
        items, total_count = db.get_collection_items(
            folder_name, args.only_attachments, 
            args.after, args.before, args.books, args.articles, args.tag,
            exact_match=args.exact
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
    
    # Handle export if requested
    if args.export:
        export_items(items, db, args.export, args.file, folder_name)
    
    if args.interactive:
        sort_by_author = hasattr(args, 'sort') and args.sort and args.sort.lower() in ['a', 'author']
        handle_interactive_mode(db, items, config, max_results, folder_name, show_ids=args.showids, show_tags=args.showtags, show_year=args.showyear, show_author=args.showauthor, show_created=args.showcreated, show_modified=args.showmodified, show_collections=args.showcollections, sort_by_author=sort_by_author)
    else:
        # Enable pagination for folder results if requested
        if not hasattr(args, 'pagination'):
            args.pagination = False
        
        display_sorted_items(items, max_results, args, db=db)
    
    return 0

def count_subcollections(collection: ZoteroCollection, db: ZoteroDatabase) -> int:
    """Count the number of sub-collections for a given collection."""
    all_collections = db.list_collections()
    count = 0
    for other_collection in all_collections:
        if other_collection.full_path.startswith(collection.full_path + " > "):
            count += 1
    return count

def display_collections_hierarchically_with_mapping(collections: List[ZoteroCollection], db: ZoteroDatabase) -> List[ZoteroCollection]:
    """Display collections in hierarchical format with proper indentation and return the mapping."""
    
    # Build hierarchy data structure
    hierarchy = {}
    
    for collection in collections:
        parts = collection.full_path.split(' > ')
        current_level = hierarchy
        
        # Build nested structure
        for j, part in enumerate(parts):
            if part not in current_level:
                current_level[part] = {
                    '_children': {},
                    '_collection': None,
                    '_item_count': 0
                }
            
            # If this is the final part, store the collection info
            if j == len(parts) - 1:
                current_level[part]['_collection'] = collection
                current_level[part]['_item_count'] = collection.item_count
            
            current_level = current_level[part]['_children']
    
    # Display the hierarchy with sequential numbering and collect mapping
    counter = {'value': 1}  # Using dict to allow modification in nested function
    collection_mapping = []
    
    def print_hierarchy(level_dict, depth=0):
        indent = "  " * depth
        
        for name, data in sorted(level_dict.items()):
            collection = data['_collection']
            item_count = data['_item_count']
            
            if collection:
                # This is a leaf node (actual collection from our search)
                # Count sub-collections for this collection
                sub_count = count_subcollections(collection, db)
                
                count_info = f" ({item_count} items"
                if sub_count > 0:
                    count_info += f", {sub_count} sub-collections"
                count_info += ")"
                
                print(f"{counter['value']:2d}.{indent} {name}{count_info}")
                collection_mapping.append(collection)
                counter['value'] += 1
            else:
                # This is a parent node - only show if it has children that are in our list
                if data['_children']:
                    print(f"   {indent} {name}")
            
            # Recursively print children
            if data['_children']:
                print_hierarchy(data['_children'], depth + 1)
    
    print_hierarchy(hierarchy)
    return collection_mapping

def create_loading_spinner() -> Tuple[dict, Any]:
    """Create and start a loading spinner."""
    import sys
    import threading
    import time
    
    spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spinner_state = {'running': True}
    
    def show_spinner():
        i = 0
        while spinner_state['running']:
            sys.stdout.write(f'\r{spinner_chars[i % len(spinner_chars)]} Loading collections and sub-collections...')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    
    spinner_thread = threading.Thread(target=show_spinner)
    spinner_thread.daemon = True
    spinner_thread.start()
    
    return spinner_state, spinner_thread

def stop_spinner(spinner_state: dict, spinner_thread) -> None:
    """Stop the loading spinner and clear the line."""
    import sys
    spinner_state['running'] = False
    spinner_thread.join()
    sys.stdout.write('\r' + ' ' * 50 + '\r')  # Clear spinner line
    sys.stdout.flush()

def filter_subcollections(db: ZoteroDatabase, selected_collection: ZoteroCollection) -> List[ZoteroCollection]:
    """Filter collections to include the selected collection and its sub-collections."""
    all_collections = db.list_collections()
    logger.debug(f"Total collections in database: {len(all_collections)}")
    logger.debug(f"Selected collection: {selected_collection.full_path} (ID: {selected_collection.collection_id})")
    
    filtered_collections = []
    for collection in all_collections:
        # Check if this collection is the selected collection or a child of it
        if (collection.collection_id == selected_collection.collection_id or
            collection.full_path.startswith(selected_collection.full_path + " > ")):
            filtered_collections.append(collection)
            logger.debug(f"Added to filtered collections: {collection.full_path}")
    
    logger.debug(f"Filtered collections count: {len(filtered_collections)}")
    return filtered_collections

def load_items_from_collections(db: ZoteroDatabase, collections: List[ZoteroCollection], args) -> Tuple[List[ZoteroItem], int]:
    """Load items from multiple collections with progress display."""
    print(f"Loading items from {len(collections)} collections...")
    
    all_items = []
    total_count = 0
    
    for i, collection in enumerate(collections, 1):
        print(f"\rProcessing collection {i}/{len(collections)}: {collection.name}", end='', flush=True)
        logger.debug(f"Getting items for collection: {collection.name} (full path: {collection.full_path})")
        
        items = db.items.get_items_in_collection(
            collection.collection_id, args.only_attachments, 
            args.after, args.before, args.books, args.articles, args.tag
        )
        logger.debug(f"Got {len(items)} items from collection {collection.name}")
        all_items.extend(items)
        total_count += len(items)
    
    print()  # New line after progress
    return all_items, total_count

def process_subcollection_items(all_items: List[ZoteroItem], args, db: ZoteroDatabase, max_results: int) -> Tuple[List[ZoteroItem], int, int, int]:
    """Process items from subcollections (deduplication and limit)."""
    # Apply deduplication if enabled (important since we may have items in multiple collections)
    duplicates_removed = 0
    if not args.no_dedupe:
        print("Removing duplicates...")
        all_items, duplicates_removed = deduplicate_items(db, all_items, args.debug)
    
    # Apply limit
    items_before_limit = len(all_items)
    all_items = all_items[:max_results]
    items_final = len(all_items)
    
    return all_items, duplicates_removed, items_before_limit, items_final

def display_subcollection_results(selected_collection: ZoteroCollection, items_final: int, items_before_limit: int, 
                                 duplicates_removed: int, total_count: int, args) -> None:
    """Display results for subcollection search."""
    if args.only_attachments:
        print(f"Items in folder '{selected_collection.name}' and sub-collections (with PDF/EPUB attachments):")
    else:
        print(f"Items in folder '{selected_collection.name}' and sub-collections:")
    
    # Show clear count information
    if items_final < items_before_limit:
        if duplicates_removed > 0:
            print(f"Showing {items_final} of {items_before_limit} items ({duplicates_removed} duplicates removed, {total_count} total found):")
        else:
            print(f"Showing first {items_final} of {items_before_limit} items:")
    elif duplicates_removed > 0:
        print(f"Showing {items_final} items ({duplicates_removed} duplicates removed from {total_count} total found):")

def handle_single_collection_with_subcollections(db: ZoteroDatabase, selected_collection: ZoteroCollection, args, max_results: int, config: dict) -> int:
    """Handle folder/ command for a single selected collection and its sub-collections."""
    # Show spinner while loading collections
    spinner_state, spinner_thread = create_loading_spinner()
    
    try:
        # Filter to include sub-collections of the selected collection
        filtered_collections = filter_subcollections(db, selected_collection)
        
        # Stop spinner
        stop_spinner(spinner_state, spinner_thread)
        
        logger.debug(f"Found {len(filtered_collections)} collections (including sub-collections)")
        
        # Load items from all collections
        all_items, total_count = load_items_from_collections(db, filtered_collections, args)
        
        if not all_items:
            print(f"No items found in folder '{selected_collection.name}' and its sub-collections")
            return 1
        
        # Process items (deduplication and limit)
        all_items, duplicates_removed, items_before_limit, items_final = process_subcollection_items(
            all_items, args, db, max_results
        )
        
        # Display results
        display_subcollection_results(selected_collection, items_final, items_before_limit, duplicates_removed, total_count, args)
        display_sorted_items(all_items, max_results, args, db=db)
        
        # Handle export if requested
        if args.export:
            export_items(all_items, db, args.export, args.file, f"{selected_collection.name} and sub-collections")
        
        if args.interactive:
            sort_by_author = hasattr(args, 'sort') and args.sort and args.sort.lower() in ['a', 'author']
            handle_interactive_mode(db, all_items, config, max_results, f"{selected_collection.name} and sub-collections", show_ids=args.showids, show_tags=args.showtags, show_year=args.showyear, show_author=args.showauthor, show_created=args.showcreated, show_modified=args.showmodified, show_collections=args.showcollections, sort_by_author=sort_by_author)
        
        return 0
    
    except Exception as e:
        # Make sure spinner is stopped in case of error
        stop_spinner(spinner_state, spinner_thread)
        raise e

def handle_multiple_collections_with_subcollections(db: ZoteroDatabase, folder_name: str, collections: List[ZoteroCollection], args, max_results: int, config: dict) -> int:
    """Handle folder command when including sub-collections (/ suffix used)."""
    logger.debug(f"Processing {len(collections)} collections for sub-collection search")
    
    # Get items from all specified collections
    all_items = []
    total_count = 0
    
    for i, collection in enumerate(collections):
        logger.debug(f"Processing collection {i+1}/{len(collections)}: '{collection.name}'")
        items, count = db.get_collection_items(
            collection.name, args.only_attachments, 
            args.after, args.before, args.books, args.articles, args.tag,
            exact_match=args.exact
        )
        all_items.extend(items)
        total_count += count
        logger.debug(f"  Found {count} items in collection '{collection.name}'")
    
    logger.debug(f"Total items found: {len(all_items)}, total count: {total_count}")
    
    if not all_items:
        print(f"No items found in folder '{folder_name}' and its sub-collections")
        return 1
    
    # Apply deduplication if enabled (important since we may have items in multiple collections)
    duplicates_removed = 0
    if not args.no_dedupe:
        all_items, duplicates_removed = deduplicate_items(db, all_items, args.debug)
    
    # Apply limit
    items_before_limit = len(all_items)
    all_items = all_items[:max_results]
    items_final = len(all_items)
    
    # Display results
    if args.only_attachments:
        print(f"Items in folder '{folder_name}' and sub-collections (with PDF/EPUB attachments):")
    else:
        print(f"Items in folder '{folder_name}' and sub-collections:")
    
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
    
    display_sorted_items(all_items, max_results, args, db=db)
    
    # Handle export if requested
    if args.export:
        export_items(all_items, db, args.export, args.file, f"{folder_name} and sub-collections")
    
    if args.interactive:
        sort_by_author = hasattr(args, 'sort') and args.sort and args.sort.lower() in ['a', 'author']
        handle_interactive_mode(db, all_items, config, max_results, f"{folder_name} and sub-collections", show_ids=args.showids, show_tags=args.showtags, show_year=args.showyear, show_author=args.showauthor, show_created=args.showcreated, show_modified=args.showmodified, show_collections=args.showcollections, sort_by_author=sort_by_author)
    
    return 0

def parse_folder_parameters(args) -> Tuple[str, bool]:
    """Parse folder command parameters.
    
    Returns: (folder_name, show_subcolls)
    """
    folder_name = ' '.join(args.folder)
    show_subcolls = folder_name.endswith('/')
    if show_subcolls:
        folder_name = folder_name[:-1]  # Remove the trailing "/"
        logger.debug(f"Folder command with sub-collections: '{folder_name}'")
    return folder_name, show_subcolls

def select_collection_for_subcollections(collections: List[ZoteroCollection], folder_name: str, db: ZoteroDatabase) -> Optional[ZoteroCollection]:
    """Handle interactive selection when multiple collections match for sub-collection search."""
    print(f"Multiple collections found matching '{folder_name}':")
    print("Select a collection to show items from it and all its sub-collections:")
    
    # Display collections in hierarchical format and get the mapping
    collection_mapping = display_collections_hierarchically_with_mapping(collections, db)
    
    logger.debug(f"Original collections count: {len(collections)}")
    logger.debug(f"Collection mapping count: {len(collection_mapping)}")
    
    while True:
        try:
            choice = input(f"\nSelect collection number (1-{len(collection_mapping)}, 0 to cancel): ").strip()
            if choice == "0" or choice == "":
                return None
            
            selection_num = int(choice)
            if 1 <= selection_num <= len(collection_mapping):
                selected_collection = collection_mapping[selection_num - 1]
                logger.debug(f"Selected collection: {selected_collection.full_path} (ID: {selected_collection.collection_id})")
                return selected_collection
            else:
                print(f"Please enter a number between 1 and {len(collection_mapping)}")
        except ValueError:
            print("Invalid input. Please enter a number or valid command.")
            continue
        except KeyboardInterrupt:
            print("\nCancelled")
            return None
        except EOFError:
            return None

def handle_subcollections_mode(collections: List[ZoteroCollection], folder_name: str, db: ZoteroDatabase, args, max_results: int, config: dict) -> int:
    """Handle folder command with subcollections (/ suffix)."""
    logger.debug("Processing sub-collections...")
    
    # If multiple collections match, use interactive selection for better performance
    if len(collections) > 1:
        selected_collection = select_collection_for_subcollections(collections, folder_name, db)
        if not selected_collection:
            return 0
        return handle_single_collection_with_subcollections(db, selected_collection, args, max_results, config)
    
    # Single collection - process normally
    selected_collection = collections[0]
    return handle_single_collection_with_subcollections(db, selected_collection, args, max_results, config)

def handle_folder_command(db: ZoteroDatabase, args, max_results: int, config: dict) -> int:
    """Handle -f/--folder command."""
    # Enable pagination automatically for interactive mode
    if args.interactive:
        args.pagination = True
        
    folder_name, show_subcolls = parse_folder_parameters(args)
    
    # Check how many collections match
    collections = db.search_collections(folder_name, exact_match=args.exact)
    logger.debug(f"Found {len(collections)} collections matching '{folder_name}'")
    
    if not collections:
        similar = db.find_similar_collections(folder_name, 5)
        show_collection_suggestions(folder_name, similar)
        return 1
    
    # Route to appropriate handler
    if show_subcolls:
        return handle_subcollections_mode(collections, folder_name, db, args, max_results, config)
    elif len(collections) > 1:
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
    # Enable pagination automatically for interactive mode
    if args.interactive:
        args.pagination = True
        
    # Process search parameters
    name_search, author_search, search_display = process_search_parameters(args)
    
    # Execute search with spinner
    from .spinner import Spinner
    with Spinner(f"Searching for '{search_display}'"):
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
    
    # Handle export if requested
    if args.export:
        export_items(items, db, args.export, args.file, search_display)
    
    if args.interactive:
        sort_by_author = hasattr(args, 'sort') and args.sort and args.sort.lower() in ['a', 'author']
        handle_interactive_mode(db, items, config, max_results, search_display, show_ids=args.showids, show_tags=args.showtags, show_year=args.showyear, show_author=args.showauthor, show_created=args.showcreated, show_modified=args.showmodified, show_collections=args.showcollections, sort_by_author=sort_by_author, show_go_back=False)
    else:
        # Enable pagination for search results if requested
        if not hasattr(args, 'pagination'):
            args.pagination = False
        
        # Use pagination for non-interactive mode
        display_sorted_items(items, max_results, args, db=db, search_term=highlight_term)
    
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