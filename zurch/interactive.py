"""Interactive mode functionality for zurch."""

from typing import List, Optional
from .utils import pad_number
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
    
    # Display collections
    for num, depth, name, collection in flat_collections:
        indent = "  " * depth
        count_info = f" ({collection.item_count} items)" if collection.item_count > 0 else ""
        print(f"{pad_number(num, len(flat_collections))}. {indent}{name}{count_info}")
    
    # Get selection
    while True:
        try:
            choice = input(f"\nSelect collection number (1-{len(flat_collections)}, 0 to cancel): ").strip()
            if choice.lower() == 'q' or choice == "0":
                return None
            
            idx = int(choice)
            if idx in collection_map:
                return collection_map[idx]
            else:
                print(f"Please enter a number between 1 and {len(flat_collections)}")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled")
            return None
        except EOFError:
            return None