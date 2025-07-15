"""Hierarchical pagination for collections display."""
from typing import List, Dict, Tuple, Optional
from .models import ZoteroCollection


def build_collection_hierarchy(collections: List[ZoteroCollection]) -> Dict[str, Dict]:
    """Build a hierarchical structure from flat collection list.
    
    Returns a dict with structure:
    {
        'user': {
            'name': 'Personal Library',
            'top_level_collections': [
                {
                    'collection': ZoteroCollection,
                    'children': [child_collections...]
                }
            ]
        },
        'group:123': {
            'name': 'Group Name',
            'top_level_collections': [...]
        }
    }
    """
    # Group by library
    libraries = {}
    
    # First pass: organize by library
    for collection in collections:
        library_key = f"{collection.library_type}:{collection.library_id}"
        if library_key not in libraries:
            libraries[library_key] = {
                'name': collection.library_name,
                'type': collection.library_type,
                'collections_by_id': {},
                'top_level_collections': []
            }
        
        libraries[library_key]['collections_by_id'][collection.collection_id] = {
            'collection': collection,
            'children': []
        }
    
    # Second pass: build parent-child relationships
    for library_data in libraries.values():
        for coll_id, coll_data in library_data['collections_by_id'].items():
            collection = coll_data['collection']
            if collection.parent_id is None:
                # This is a top-level collection
                library_data['top_level_collections'].append(coll_data)
            else:
                # Find parent and add as child
                parent_id = collection.parent_id
                if parent_id in library_data['collections_by_id']:
                    library_data['collections_by_id'][parent_id]['children'].append(coll_data)
    
    # Sort top-level collections alphabetically
    for library_data in libraries.values():
        library_data['top_level_collections'].sort(
            key=lambda x: x['collection'].name.lower()
        )
        # Sort children recursively
        sort_children_recursive(library_data['top_level_collections'])
    
    return libraries


def sort_children_recursive(collection_list: List[Dict]):
    """Sort children collections recursively."""
    for coll_data in collection_list:
        if coll_data['children']:
            coll_data['children'].sort(
                key=lambda x: x['collection'].name.lower()
            )
            sort_children_recursive(coll_data['children'])


def count_collection_tree(coll_data: Dict) -> int:
    """Count total collections in a tree (including the root)."""
    count = 1  # Count this collection
    for child in coll_data['children']:
        count += count_collection_tree(child)
    return count


def get_paginated_collections(
    collections: List[ZoteroCollection], 
    page_size: int, 
    current_page: int = 0
) -> Tuple[List[ZoteroCollection], bool, bool, int, int]:
    """Get paginated collections maintaining hierarchical structure.
    
    Returns: (page_collections, has_previous, has_next, current_page, total_pages)
    """
    # Build hierarchy
    hierarchy = build_collection_hierarchy(collections)
    
    # Flatten to top-level collection groups
    top_level_groups = []
    
    # Process user library first
    for library_key, library_data in sorted(hierarchy.items(), 
                                           key=lambda x: (x[1]['type'] != 'user', x[1]['name'])):
        for top_coll_data in library_data['top_level_collections']:
            # Each top-level collection with all its children is one "group"
            group_collections = []
            flatten_collection_tree(top_coll_data, group_collections)
            top_level_groups.append({
                'library_key': library_key,
                'library_name': library_data['name'],
                'library_type': library_data['type'],
                'collections': group_collections
            })
    
    # Now paginate by top-level groups
    total_groups = len(top_level_groups)
    
    if total_groups == 0:
        return [], False, False, 0, 0
    
    # Calculate how many groups fit on each page
    groups_per_page = 0
    collections_count = 0
    temp_groups = []
    
    for group in top_level_groups:
        group_size = len(group['collections'])
        if collections_count + group_size <= page_size:
            temp_groups.append(group)
            collections_count += group_size
        else:
            if not temp_groups:
                # This group is too big for a page, but we need at least one
                temp_groups.append(group)
            break
    
    # Calculate actual pages based on groups
    pages = []
    current_page_groups = []
    current_page_count = 0
    
    for group in top_level_groups:
        group_size = len(group['collections'])
        
        if current_page_count + group_size > page_size and current_page_groups:
            # Start new page
            pages.append(current_page_groups)
            current_page_groups = [group]
            current_page_count = group_size
        else:
            current_page_groups.append(group)
            current_page_count += group_size
    
    if current_page_groups:
        pages.append(current_page_groups)
    
    total_pages = len(pages)
    
    # Ensure current_page is valid
    current_page = max(0, min(current_page, total_pages - 1))
    
    # Get collections for current page
    if pages and 0 <= current_page < total_pages:
        page_groups = pages[current_page]
        page_collections = []
        for group in page_groups:
            page_collections.extend(group['collections'])
    else:
        page_collections = []
    
    has_previous = current_page > 0
    has_next = current_page < total_pages - 1
    
    return page_collections, has_previous, has_next, current_page, total_pages


def flatten_collection_tree(coll_data: Dict, result_list: List[ZoteroCollection]):
    """Flatten a collection tree maintaining hierarchical order."""
    result_list.append(coll_data['collection'])
    for child in coll_data['children']:
        flatten_collection_tree(child, result_list)