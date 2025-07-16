from typing import List, Optional, Tuple
import fnmatch
from .models import ZoteroItem, ZoteroCollection
from .stats import DatabaseStats
from .utils import (
    format_item_type_icon, format_attachment_link_icon, pad_number, 
    highlight_search_term, format_duplicate_title, format_metadata_field
)

def display_items(items: List[ZoteroItem], max_results: int, search_term: str = "", show_ids: bool = False, show_tags: bool = False, show_year: bool = False, show_author: bool = False, show_created: bool = False, show_modified: bool = False, show_collections: bool = False, db=None, sort_by_author: bool = False) -> None:
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
        
        # Handle special case for author sorting
        if sort_by_author and db:
            try:
                metadata = db.get_item_metadata(item.item_id)
                author_prefix = ""
                year_display = ""
                
                # Extract first author for prefix
                if 'creators' in metadata:
                    for creator in metadata['creators']:
                        if creator.get('creatorType') == 'author':
                            last_name = creator.get('lastName', '')
                            first_name = creator.get('firstName', '')
                            
                            if last_name and first_name:
                                author_prefix = f"{last_name}, {first_name} - "
                            elif last_name:
                                author_prefix = f"{last_name} - "
                            elif first_name:
                                author_prefix = f"{first_name} - "
                            break
                
                # Extract publication year if needed
                if show_year:
                    pub_year = ""
                    if 'date' in metadata:
                        date_str = metadata['date']
                        if date_str and len(date_str) >= 4:
                            pub_year = date_str[:4]
                    if pub_year:
                        year_display = f" ({pub_year})"
                
                print(f"{number}. {type_icon}{attachment_icon}{author_prefix}{title}{year_display}{id_display}")
                
            except Exception as e:
                # If metadata retrieval fails, show title only
                print(f"{number}. {type_icon}{attachment_icon}{title}{id_display}")
        else:
            # Standard display format
            # Add year and author if requested
            year_display = ""
            author_display = ""
            
            if (show_year or show_author) and db:
                try:
                    metadata = db.get_item_metadata(item.item_id)
                    
                    # Extract publication year
                    if show_year:
                        pub_year = ""
                        if 'date' in metadata:
                            date_str = metadata['date']
                            if date_str and len(date_str) >= 4:
                                pub_year = date_str[:4]
                        if pub_year:
                            year_display = f" ({pub_year})"
                    
                    # Extract first author
                    if show_author:
                        if 'creators' in metadata:
                            for creator in metadata['creators']:
                                if creator.get('creatorType') == 'author':
                                    name_parts = []
                                    if creator.get('firstName'):
                                        name_parts.append(creator['firstName'])
                                    if creator.get('lastName'):
                                        name_parts.append(creator['lastName'])
                                    if name_parts:
                                        author_name = ' '.join(name_parts)
                                        author_display = f" - {author_name}"
                                        break
                    
                except Exception as e:
                    # If metadata retrieval fails, continue without year/author
                    pass
            
            print(f"{number}. {type_icon}{attachment_icon}{title}{year_display}{author_display}{id_display}")
        
        # Show tags if requested
        if show_tags and db:
            tags = db.get_item_tags(item.item_id)
            if tags:
                # Display tags in a muted color
                GRAY = '\033[90m'
                RESET = '\033[0m'
                tag_text = f"{GRAY}    Tags: {' | '.join(tags)}{RESET}"
                print(tag_text)
        
        # Show created/modified dates if requested
        if (show_created or show_modified) and db:
            GRAY = '\033[90m'
            RESET = '\033[0m'
            date_parts = []
            
            if show_created and item.date_added:
                date_parts.append(f"Created: {item.date_added}")
            if show_modified and item.date_modified:
                date_parts.append(f"Modified: {item.date_modified}")
                
            if date_parts:
                date_text = f"{GRAY}    {' | '.join(date_parts)}{RESET}"
                print(date_text)
        
        # Show collections if requested
        if show_collections and db:
            collections = db.get_item_collections(item.item_id)
            if collections:
                GRAY = '\033[90m'
                RESET = '\033[0m'
                collection_text = f"{GRAY}    Collections: {' | '.join(collections)}{RESET}"
                print(collection_text)

def display_grouped_items(grouped_items: List[tuple], max_results: int, search_term: str = "", show_ids: bool = False, show_tags: bool = False, show_year: bool = False, show_author: bool = False, show_created: bool = False, show_modified: bool = False, show_collections: bool = False, db=None, sort_by_author: bool = False) -> List[ZoteroItem]:
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
            
            # Handle special case for author sorting
            if sort_by_author and db:
                try:
                    metadata = db.get_item_metadata(item.item_id)
                    author_prefix = ""
                    year_display = ""
                    
                    # Extract first author for prefix
                    if 'creators' in metadata:
                        for creator in metadata['creators']:
                            if creator.get('creatorType') == 'author':
                                last_name = creator.get('lastName', '')
                                first_name = creator.get('firstName', '')
                                
                                if last_name and first_name:
                                    author_prefix = f"{last_name}, {first_name} - "
                                elif last_name:
                                    author_prefix = f"{last_name} - "
                                elif first_name:
                                    author_prefix = f"{first_name} - "
                                break
                    
                    # Extract publication year if needed
                    if show_year:
                        pub_year = ""
                        if 'date' in metadata:
                            date_str = metadata['date']
                            if date_str and len(date_str) >= 4:
                                pub_year = date_str[:4]
                        if pub_year:
                            year_display = f" ({pub_year})"
                    
                    print(f"{number}. {type_icon}{attachment_icon}{author_prefix}{title}{year_display}{id_display}")
                    
                except Exception as e:
                    # If metadata retrieval fails, show title only
                    print(f"{number}. {type_icon}{attachment_icon}{title}{id_display}")
            else:
                # Standard display format
                # Add year and author if requested
                year_display = ""
                author_display = ""
                
                if (show_year or show_author) and db:
                    try:
                        metadata = db.get_item_metadata(item.item_id)
                        
                        # Extract publication year
                        if show_year:
                            pub_year = ""
                            if 'date' in metadata:
                                date_str = metadata['date']
                                if date_str and len(date_str) >= 4:
                                    pub_year = date_str[:4]
                            if pub_year:
                                year_display = f" ({pub_year})"
                        
                        # Extract first author
                        if show_author:
                            if 'creators' in metadata:
                                for creator in metadata['creators']:
                                    if creator.get('creatorType') == 'author':
                                        name_parts = []
                                        if creator.get('firstName'):
                                            name_parts.append(creator['firstName'])
                                        if creator.get('lastName'):
                                            name_parts.append(creator['lastName'])
                                        if name_parts:
                                            author_name = ' '.join(name_parts)
                                            author_display = f" - {author_name}"
                                            break
                        
                    except Exception as e:
                        # If metadata retrieval fails, continue without year/author
                        pass
                
                print(f"{number}. {type_icon}{attachment_icon}{title}{year_display}{author_display}{id_display}")
            
            # Show tags if requested
            if show_tags and db:
                tags = db.get_item_tags(item.item_id)
                if tags:
                    # Display tags in a muted color
                    GRAY = '\033[90m'
                    RESET = '\033[0m'
                    tag_text = f"{GRAY}    Tags: {' | '.join(tags)}{RESET}"
                    print(tag_text)
            
            # Show created/modified dates if requested
            if (show_created or show_modified) and db:
                GRAY = '\033[90m'
                RESET = '\033[0m'
                date_parts = []
                
                if show_created and item.date_added:
                    date_parts.append(f"Created: {item.date_added}")
                if show_modified and item.date_modified:
                    date_parts.append(f"Modified: {item.date_modified}")
                    
                if date_parts:
                    date_text = f"{GRAY}    {' | '.join(date_parts)}{RESET}"
                    print(date_text)
            
            # Show collections if requested
            if show_collections and db:
                collections = db.get_item_collections(item.item_id)
                if collections:
                    GRAY = '\033[90m'
                    RESET = '\033[0m'
                    collection_text = f"{GRAY}    Collections: {' | '.join(collections)}{RESET}"
                    print(collection_text)
            
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

def display_hierarchical_search_results(collections: List, search_term: str, max_results: int = None) -> int:
    """Display search results in hierarchical format showing parent structure with library grouping.
    
    Returns the number of collections actually displayed.
    """
    # Group collections by library to avoid duplicates
    libraries = {}
    displayed_count = 0
    
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
                if matches_search_term(part, search_term):
                    current_level[part]['_is_match'] = True
                
                # If this is the final part, store the collection info
                if i == len(parts) - 1:
                    current_level[part]['_collection'] = collection
                
                current_level = current_level[part]['_children']
        
        library_data['hierarchy'] = hierarchy
    
    # Display the hierarchy
    def print_hierarchy(level_dict, depth=0, parent_shown=False):
        nonlocal displayed_count
        
        # Different bullet points for different depths
        bullet_points = ["•", "◦", "▪", "▫", "‣", "⁃", "◦", "▪"]
        bullet = bullet_points[min(depth, len(bullet_points) - 1)]
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
                    prefix = f"{indent}{bullet} " if depth > 0 else f"{indent}"
                    print(f"{prefix}{highlighted_name}{count_info}")
                    if is_match:  # Only count actual matches, not parent nodes
                        displayed_count += 1
                else:
                    # This is a parent node - show it if it has matching children
                    if has_matching_children:
                        highlighted_name = highlight_search_term(name, search_term)
                        prefix = f"{indent}{bullet} " if depth > 0 else f"{indent}"
                        print(f"{prefix}{highlighted_name}")
                
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
        print_hierarchy(library_data['hierarchy'])
    
    return displayed_count

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

def display_database_stats(stats: DatabaseStats, db_path: str = None) -> None:
    """Display comprehensive database statistics."""
    BOLD = '\033[1m'
    RESET = '\033[0m'
    BLUE = '\033[34m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    GRAY = '\033[90m'
    
    print(f"{BOLD}📊 Zotero Database Statistics{RESET}")
    print("=" * 50)
    
    # Show database location if provided
    if db_path:
        print(f"{BOLD}📍 Database Location{RESET}")
        print(f"  {GRAY}{db_path}{RESET}")
        print()
    
    # Total counts
    print(f"{BOLD}📚 Overview{RESET}")
    print(f"  Total Items: {BLUE}{stats.total_items:,}{RESET}")
    print(f"  Total Collections: {GREEN}{stats.total_collections:,}{RESET}")
    print(f"  Total Tags: {YELLOW}{stats.total_tags:,}{RESET}")
    print()
    
    # Item types breakdown - show only top 10
    if stats.item_types:
        print(f"{BOLD}📖 Items by Type (Top 10){RESET}")
        # Calculate percentage for each type
        total_items = stats.total_items
        for item_type, count in stats.item_types[:10]:  # Show only top 10
            percentage = (count / total_items * 100) if total_items > 0 else 0
            # Format item type name nicely
            display_name = item_type.replace('_', ' ').title()
            if display_name == 'Journalarticle':
                display_name = 'Journal Article'
            elif display_name == 'Bookchapter':
                display_name = 'Book Chapter'
            elif display_name == 'Booksection':
                display_name = 'Book Section'
            elif display_name == 'Conferencepaper':
                display_name = 'Conference Paper'
            elif display_name == 'Webpage':
                display_name = 'Web Page'
            
            print(f"  {display_name}: {count:,} ({percentage:.1f}%)")
        
        if len(stats.item_types) > 10:
            remaining_count = sum(count for _, count in stats.item_types[10:])
            remaining_percentage = (remaining_count / total_items * 100) if total_items > 0 else 0
            print(f"  Other types: {remaining_count:,} ({remaining_percentage:.1f}%)")
        print()
    
    # Attachment statistics
    print(f"{BOLD}📎 Attachment Statistics{RESET}")
    total_attachment_items = stats.items_with_attachments + stats.items_without_attachments
    with_percentage = (stats.items_with_attachments / total_attachment_items * 100) if total_attachment_items > 0 else 0
    without_percentage = (stats.items_without_attachments / total_attachment_items * 100) if total_attachment_items > 0 else 0
    
    print(f"  Items with PDF/EPUB attachments: {GREEN}{stats.items_with_attachments:,}{RESET} ({with_percentage:.1f}%)")
    print(f"  Items without attachments: {stats.items_without_attachments:,} ({without_percentage:.1f}%)")
    print()
    
    # Top collections
    if stats.top_collections:
        print(f"{BOLD}📁 Most Used Collections (Top 20){RESET}")
        # Calculate max collection name length for alignment
        max_collection_length = min(50, max(len(collection) for collection, _ in stats.top_collections))
        
        for i, (collection, count) in enumerate(stats.top_collections, 1):
            # Truncate very long collection names
            display_name = collection[:47] + "..." if len(collection) > 50 else collection
            padded_name = display_name.ljust(max_collection_length)
            print(f"  {i:2d}. {padded_name} ({count:,} items)")
        print()
    
    # Top tags - show all 40
    if stats.top_tags:
        print(f"{BOLD}🏷️  Most Used Tags (Top 40){RESET}")
        # Calculate max tag name length for alignment
        max_tag_length = min(40, max(len(tag) for tag, _ in stats.top_tags))
        
        for i, (tag, count) in enumerate(stats.top_tags, 1):
            # Truncate very long tag names
            display_name = tag[:37] + "..." if len(tag) > 40 else tag
            padded_tag = display_name.ljust(max_tag_length)
            print(f"  {i:2d}. {padded_tag} ({count:,} items)")
        print()
    
    # Publication decades
    if stats.publication_decades:
        print(f"{BOLD}📅 Publications by Decade{RESET}")
        for decade, count in stats.publication_decades:
            percentage = (count / stats.total_items * 100) if stats.total_items > 0 else 0
            print(f"  {decade:12s}: {count:,} items ({percentage:.1f}%)")
        print()
    
    # Summary line
    print(f"{BOLD}Summary:{RESET} {stats.total_items:,} items across {stats.total_collections:,} collections with {stats.total_tags:,} unique tags")