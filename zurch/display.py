from typing import List, Optional, Tuple
import fnmatch
from .models import ZoteroItem, ZoteroCollection
from .utils import (
    format_item_type_icon, format_attachment_link_icon, pad_number, 
    highlight_search_term, format_duplicate_title, format_metadata_field
)

def display_items(items: List[ZoteroItem], max_results: int, search_term: str = "", show_ids: bool = False, show_tags: bool = False, db=None) -> None:
    """Display items with numbering and icons."""
    for i, item in enumerate(items, 1):
        # Item type icon (books and journal articles)
        type_icon = format_item_type_icon(item.item_type, item.is_duplicate)
        
        # Link icon for PDF/EPUB attachments
        attachment_icon = format_attachment_link_icon(item.attachment_type)
        
        number = pad_number(i, min(len(items), max_results))
        title = highlight_search_term(item.title, search_term) if search_term else item.title
        title = format_duplicate_title(title, item.is_duplicate)
        
        # Add ID if requested
        id_display = f" [ID:{item.item_id}]" if show_ids else ""
        
        print(f"{number}. {type_icon}{attachment_icon}{title}{id_display}")
        
        # Show tags if requested
        if show_tags and db:
            tags = db.get_item_tags(item.item_id)
            if tags:
                # Display tags in a muted color
                GRAY = '\033[90m'
                RESET = '\033[0m'
                tag_text = f"{GRAY}    Tags: {' | '.join(tags)}{RESET}"
                print(tag_text)

def display_grouped_items(grouped_items: List[tuple], max_results: int, search_term: str = "", show_ids: bool = False, show_tags: bool = False, db=None) -> List[ZoteroItem]:
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
            
            # Add ID if requested
            id_display = f" [ID:{item.item_id}]" if show_ids else ""
            
            print(f"{number}. {type_icon}{attachment_icon}{title}{id_display}")
            
            # Show tags if requested
            if show_tags and db:
                tags = db.get_item_tags(item.item_id)
                if tags:
                    # Display tags in a muted color
                    GRAY = '\033[90m'
                    RESET = '\033[0m'
                    tag_text = f"{GRAY}    Tags: {' | '.join(tags)}{RESET}"
                    print(tag_text)
            
            all_items.append(item)
            item_counter += 1
    
    return all_items

def matches_search_term(text: str, search_term: str) -> bool:
    """Check if text matches the search term (with wildcard support)."""
    if not search_term:
        return True  # Empty or None search term matches everything
    if not text:
        return False
    
    text_lower = text.lower()
    search_lower = search_term.lower()
    
    # Handle % wildcards
    if '%' in search_lower:
        # Convert % wildcard to simple pattern matching
        pattern = search_lower.replace('%', '*')
        return fnmatch.fnmatch(text_lower, pattern)
    else:
        # Default partial matching
        return search_lower in text_lower

def display_hierarchical_search_results(collections: List, search_term: str, max_results: int = None) -> None:
    """Display search results in hierarchical format showing parent structure."""
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

def show_item_metadata(db, item: ZoteroItem) -> None:
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
        
        # Display tags for this item
        tags = db.get_item_tags(item.item_id)
        if tags:
            BOLD = '\033[1m'
            RESET = '\033[0m'
            print(f"{BOLD}Tags:{RESET} {' | '.join(tags)}")
        
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