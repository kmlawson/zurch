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
    """Get paginated collections with strict page size limit.
    
    page_size is the exact number of collections to show per page.
    Hierarchies can be split across pages if needed.
    
    Returns: (page_collections, has_previous, has_next, current_page, total_pages)
    """
    # Build hierarchy and flatten to preserve order
    hierarchy = build_collection_hierarchy(collections)
    
    # Flatten all collections in hierarchical order
    all_collections_ordered = []
    
    # Process user library first
    for library_key, library_data in sorted(hierarchy.items(), 
                                           key=lambda x: (x[1]['type'] != 'user', x[1]['name'])):
        for top_coll_data in library_data['top_level_collections']:
            flatten_collection_tree(top_coll_data, all_collections_ordered)
    
    if not all_collections_ordered:
        return [], False, False, 0, 0
    
    # Simple pagination: exactly page_size collections per page
    total_collections = len(all_collections_ordered)
    total_pages = (total_collections + page_size - 1) // page_size
    
    # Ensure current_page is valid
    current_page = max(0, min(current_page, total_pages - 1))
    
    # Get collections for the current page
    start_idx = current_page * page_size
    end_idx = min(start_idx + page_size, total_collections)
    page_collections = all_collections_ordered[start_idx:end_idx]
    
    has_previous = current_page > 0
    has_next = current_page < total_pages - 1
    
    return page_collections, has_previous, has_next, current_page, total_pages


def flatten_collection_tree(coll_data: Dict, result_list: List[ZoteroCollection]):
    """Flatten a collection tree maintaining hierarchical order."""
    result_list.append(coll_data['collection'])
    for child in coll_data['children']:
        flatten_collection_tree(child, result_list)