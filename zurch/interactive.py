"""Interactive mode functionality for zurch."""

from typing import List, Optional, Tuple
from .utils import pad_number, highlight_search_term
from .search import ZoteroCollection

def interactive_collection_selection(collections: List[ZoteroCollection]) -> Optional[ZoteroCollection]:
    """Handle interactive collection selection with numbered list.
    
    Future enhancement: Add arrow key navigation using curses/termios.
    """
    if not collections:
        return None
    
    print("\nCollections (enter number to select):")
    print("─" * 60)
    
    # Build a flat list of collections with their hierarchy info
    flat_collections = []
    collection_map = {}
    index = 0
    
    # Build hierarchy
    hierarchy = {}
    for collection in collections:
        parts = collection.full_path.split(' > ')
        current_level = hierarchy
        
        for i, part in enumerate(parts):
            if part not in current_level:
                current_level[part] = {
                    '_children': {},
                    '_collection': None,
                    '_depth': i
                }
            
            if i == len(parts) - 1:
                current_level[part]['_collection'] = collection
            
            current_level = current_level[part]['_children']
    
    # Flatten hierarchy for display
    def flatten_hierarchy(level_dict, depth=0):
        nonlocal index
        for name, data in sorted(level_dict.items()):
            collection = data['_collection']
            if collection:
                flat_collections.append((index + 1, depth, name, collection))
                collection_map[index + 1] = collection
                index += 1
            
            if data['_children']:
                flatten_hierarchy(data['_children'], depth + 1)
    
    flatten_hierarchy(hierarchy)
    
    # Display collections with hierarchical bullet points
    for num, depth, name, collection in flat_collections:
        # Different bullet points for different depths
        bullet_points = ["•", "◦", "▪", "▫", "‣", "⁃", "◦", "▪"]
        bullet = bullet_points[min(depth, len(bullet_points) - 1)]
        indent = "  " * depth
        prefix = f"{bullet} " if depth > 0 else ""
        count_info = f" ({collection.item_count} items)" if collection.item_count > 0 else ""
        print(f"{pad_number(num, len(flat_collections))}. {indent}{prefix}{name}{count_info}")
    
    # Get selection
    while True:
        try:
            # Try to use immediate key response for navigation keys
            from .keyboard import get_input_with_immediate_keys, is_terminal_interactive
            
            prompt = f"\nSelect collection number (1-{len(flat_collections)}, 0 to cancel): "
            
            if is_terminal_interactive():
                # Define keys that should respond immediately
                immediate_keys = {'q', 'Q'}
                first_char_only_immediate = {'0'}
                choice = get_input_with_immediate_keys(prompt, immediate_keys, first_char_only_immediate).strip()
            else:
                # Fallback to regular input (e.g., when piping input)
                choice = input(prompt).strip()
            
            if choice.lower() == 'q' or choice == "0" or choice == "":
                return None
            
            idx = int(choice)
            if idx in collection_map:
                return collection_map[idx]
            else:
                print(f"Please enter a number between 1 and {len(flat_collections)}")
        except ValueError:
            print("Invalid input. Please enter a number or valid command.")
            continue
        except KeyboardInterrupt:
            print("\nCancelled")
            return None
        except EOFError:
            return None


def interactive_collection_selection_with_pagination(
    collections: List[ZoteroCollection], 
    current_page: int, 
    total_pages: int, 
    has_previous: bool, 
    has_next: bool, 
    search_term: str = "",
    total_collections: int = None
) -> Optional[ZoteroCollection]:
    """Handle interactive collection selection with hierarchical pagination display."""
    if not collections:
        return None
    
    # Display hierarchical collections with numbers and bullet points
    print("\nCollections and Sub-collections:")
    
    # Build hierarchy for display
    libraries = {}
    displayed_collections = []
    
    # Group collections by library
    for collection in collections:
        library_key = f"{collection.library_type}:{collection.library_id}"
        if library_key not in libraries:
            libraries[library_key] = {
                'name': collection.library_name,
                'type': collection.library_type,
                'collections': [],
                'hierarchy': {}
            }
        libraries[library_key]['collections'].append(collection)
    
    # Build hierarchy for each library
    for library_key, library_data in libraries.items():
        hierarchy = {}
        
        for collection in library_data['collections']:
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
                if search_term and search_term.lower() in part.lower():
                    current_level[part]['_is_match'] = True
                
                # If this is the final part, store the collection info
                if i == len(parts) - 1:
                    current_level[part]['_collection'] = collection
                
                current_level = current_level[part]['_children']
        
        library_data['hierarchy'] = hierarchy
    
    # Display the hierarchy with numbers
    collection_map = {}
    current_number = 1
    
    def print_hierarchy_with_numbers(level_dict, depth=0):
        nonlocal current_number
        
        # Different bullet points for different depths
        bullet_points = ["•", "◦", "▪", "▫", "‣", "⁃", "◦", "▪"]
        bullet = bullet_points[min(depth, len(bullet_points) - 1)]
        indent = "  " * depth
        
        for name, data in sorted(level_dict.items()):
            collection = data['_collection']
            
            if collection:
                # This is a leaf node (actual collection)
                count_info = f" ({collection.item_count} items)" if collection.item_count > 0 else ""
                highlighted_name = highlight_search_term(name, search_term) if search_term else name
                prefix = f"{bullet} " if depth > 0 else ""
                
                # Add number and store in map
                number_str = pad_number(current_number, len(collections))
                print(f"{number_str}. {indent}{prefix}{highlighted_name}{count_info}")
                collection_map[current_number] = collection
                displayed_collections.append(collection)
                current_number += 1
            else:
                # This is a parent node - show it without number
                if data['_children']:
                    highlighted_name = highlight_search_term(name, search_term) if search_term else name
                    prefix = f"{bullet} " if depth > 0 else ""
                    print(f"     {indent}{prefix}{highlighted_name}")
            
            # Recursively print children
            if data['_children']:
                print_hierarchy_with_numbers(data['_children'], depth + 1)
    
    # Display each library's hierarchy
    # Sort libraries: user library first, then group libraries alphabetically
    sorted_libraries = sorted(
        libraries.items(),
        key=lambda x: (x[1]['type'] != 'user', x[1]['name'])
    )
    
    for i, (library_key, library_data) in enumerate(sorted_libraries):
        # Show library header for group libraries or when there are multiple libraries
        if len(libraries) > 1 and library_data['type'] == 'group':
            if i > 0:  # Add spacing between libraries
                print()
            print(f"=== {library_data['name']} (Group Library) ===")
        
        # Print the hierarchy for this library
        print_hierarchy_with_numbers(library_data['hierarchy'])
    
    # Show pagination info
    if total_collections is not None:
        print(f"\nShowing {len(collections)} of {total_collections} collections")
    else:
        print(f"\nShowing {len(collections)} collections")
    print(f"Page {current_page + 1} of {total_pages}")
    
    # Get selection
    while True:
        try:
            prompt_parts = [f"Select collection number (1-{len(collections)}"]
            if has_previous:
                prompt_parts.append("'b' for back a page")
            if has_next:
                prompt_parts.append("'n' for next page")
            prompt_parts.append("0 to cancel")
            prompt = ", ".join(prompt_parts) + "): "
            
            # Try to use immediate key response for navigation keys
            from .keyboard import get_input_with_immediate_keys, is_terminal_interactive
            
            if is_terminal_interactive():
                # Define keys that should respond immediately
                immediate_keys = {'n', 'N', 'b', 'B', 'q', 'Q'}
                first_char_only_immediate = {'0'}
                choice = get_input_with_immediate_keys(prompt, immediate_keys, first_char_only_immediate).strip()
            else:
                # Fallback to regular input (e.g., when piping input)
                choice = input(prompt).strip()
            
            if choice.lower() == 'q' or choice == "0" or choice == "":
                return None
            elif choice.lower() == 'n' and has_next:
                return "NEXT_PAGE"
            elif choice.lower() == 'b' and has_previous:
                return "PREVIOUS_PAGE"
            elif choice.lower() == 'n' and not has_next:
                print("No more next pages available.")
                continue
            elif choice.lower() == 'b' and not has_previous:
                print("No more previous pages available.")
                continue
            else:
                idx = int(choice)
                if idx in collection_map:
                    return collection_map[idx]
                else:
                    print(f"Please enter a number between 1 and {len(collections)}")
        except ValueError:
            print("Invalid input. Please enter a number or valid command.")
            continue
        except KeyboardInterrupt:
            print("\nCancelled")
            return None
        except EOFError:
            return None