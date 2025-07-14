"""Duplicate detection and handling for zurch."""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from .search import ZoteroItem, ZoteroDatabase

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class DuplicateKey:
    """Key for identifying duplicate items based on author, title, and year."""
    title: str
    authors: str  # Concatenated author names
    year: Optional[str]
    
    def __post_init__(self):
        # Normalize for consistent hashing and comparison
        object.__setattr__(self, 'title', self.title.lower())
        object.__setattr__(self, 'authors', self.authors.lower())

def extract_year_from_date(date_string: Optional[str]) -> Optional[str]:
    """Extract year from various date formats."""
    if not date_string:
        return None
    
    # Try to extract year from common formats - improved regex to avoid "1999a" matches
    import re
    year_match = re.search(r'\b(19|20)\d{2}\b', date_string)
    return year_match.group(0) if year_match else None

def get_authors_from_metadata(db: ZoteroDatabase, item_id: int) -> str:
    """Get concatenated author names for an item."""
    try:
        metadata = db.get_item_metadata(item_id)
        creators = metadata.get('creators', [])
        
        authors = []
        for creator in creators:
            if creator.get('creatorType') == 'author':
                name_parts = []
                if creator.get('lastName'):
                    name_parts.append(creator['lastName'])
                if creator.get('firstName'):
                    name_parts.append(creator['firstName'])
                if name_parts:
                    authors.append(' '.join(name_parts))
        
        return '; '.join(sorted(authors))  # Sort for consistent comparison
    except Exception as e:
        logger.warning(f"Error getting authors for item {item_id}: {e}")
        return ""

def create_duplicate_key(db: ZoteroDatabase, item: ZoteroItem) -> DuplicateKey:
    """Create a duplicate detection key for an item."""
    # Get authors from metadata
    authors = get_authors_from_metadata(db, item.item_id)
    
    # Get year from metadata
    try:
        metadata = db.get_item_metadata(item.item_id)
        date = metadata.get('date', '')
        year = extract_year_from_date(date)
    except Exception:
        year = None
    
    return DuplicateKey(
        title=item.title,
        authors=authors,
        year=year
    )

def select_best_duplicate(db: ZoteroDatabase, duplicates: List[ZoteroItem]) -> ZoteroItem:
    """Select the best item from a list of duplicates.
    
    Priority:
    1. Item with attachment (PDF/EPUB)
    2. Most recent modification date
    3. Most recent creation date
    """
    if len(duplicates) == 1:
        return duplicates[0]
    
    # Separate items with and without attachments
    with_attachments = [item for item in duplicates if item.attachment_type in ["pdf", "epub"]]
    without_attachments = [item for item in duplicates if item.attachment_type not in ["pdf", "epub"]]
    
    # Prefer items with attachments
    candidates = with_attachments if with_attachments else without_attachments
    
    # Get modification dates for final selection
    dated_candidates = []
    for item in candidates:
        try:
            metadata = db.get_item_metadata(item.item_id)
            date_modified = metadata.get('dateModified', '')
            date_added = metadata.get('dateAdded', '')
            dated_candidates.append((item, date_modified, date_added))
        except Exception:
            # If we can't get dates, use the item anyway
            dated_candidates.append((item, '', ''))
    
    # Sort by modification date (descending), then by creation date (descending)
    dated_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    selected = dated_candidates[0][0]
    logger.debug(f"Selected item {selected.item_id} from {len(duplicates)} duplicates: {selected.title}")
    
    return selected

def deduplicate_items(db: ZoteroDatabase, items: List[ZoteroItem], debug_mode: bool = False) -> Tuple[List[ZoteroItem], int]:
    """Remove duplicates from a list of items with optimized bulk metadata fetching.
    
    Args:
        db: Database connection
        items: List of items to deduplicate
        debug_mode: If True, include duplicates marked as such in the output
    
    Returns:
        Tuple of (deduplicated_items, number_of_duplicates_removed)
    """
    if not items:
        return [], 0
    
    # Fetch all metadata in bulk to avoid N+1 query problem
    item_ids = [item.item_id for item in items]
    try:
        metadata_cache = db.get_bulk_item_metadata(item_ids)
        logger.debug(f"Bulk fetched metadata for {len(item_ids)} items")
    except Exception as e:
        logger.warning(f"Error bulk fetching metadata, falling back to individual queries: {e}")
        # Fall back to individual fetching if bulk fails
        metadata_cache = {}
        for item in items:
            try:
                metadata_cache[item.item_id] = db.get_item_metadata(item.item_id)
            except Exception as e:
                logger.warning(f"Error getting metadata for item {item.item_id}: {e}")
                metadata_cache[item.item_id] = {}
    
    def get_cached_metadata(item_id: int):
        return metadata_cache.get(item_id, {})
    
    # Group items by duplicate key using cached metadata
    duplicate_groups: Dict[DuplicateKey, List[ZoteroItem]] = {}
    
    for item in items:
        try:
            key = create_duplicate_key_with_cache(item, get_cached_metadata)
            duplicate_groups.setdefault(key, []).append(item)
        except Exception as e:
            logger.warning(f"Error processing item {item.item_id} for deduplication: {e}")
            # If we can't process an item, include it anyway
            fallback_key = DuplicateKey(title=item.title, authors="", year=None)
            duplicate_groups.setdefault(fallback_key, []).append(item)
    
    # Select best item from each group and optionally include duplicates
    result_items = []
    duplicates_to_add = []  # Separate list to avoid mutation during iteration
    total_duplicates_removed = 0
    
    for key, group in duplicate_groups.items():
        if len(group) > 1:
            total_duplicates_removed += len(group) - 1
            logger.debug(f"Found {len(group)} duplicates for: {key.title}")
        
        best_item = select_best_duplicate_with_cache(group, get_cached_metadata)
        result_items.append(best_item)
        
        # In debug mode, also include the duplicates marked as such
        if debug_mode and len(group) > 1:
            for item in group:
                if item.item_id != best_item.item_id:
                    # Create a copy and mark as duplicate
                    duplicate_item = ZoteroItem(
                        item_id=item.item_id,
                        title=item.title,
                        item_type=item.item_type,
                        attachment_type=item.attachment_type,
                        attachment_path=item.attachment_path,
                        is_duplicate=True
                    )
                    duplicates_to_add.append(duplicate_item)
    
    # Add duplicates after iteration
    result_items.extend(duplicates_to_add)
    
    # Maintain original order as much as possible
    # Create a mapping of item_id to original position
    original_positions = {item.item_id: i for i, item in enumerate(items)}
    result_items.sort(key=lambda item: original_positions.get(item.item_id, float('inf')))
    
    final_count = len([item for item in result_items if not item.is_duplicate])
    if debug_mode:
        logger.info(f"Deduplication: {len(items)} -> {final_count} items ({total_duplicates_removed} duplicates removed)")
    
    return result_items, total_duplicates_removed


def create_duplicate_key_with_cache(item: ZoteroItem, get_metadata_func) -> DuplicateKey:
    """Create a duplicate detection key using cached metadata."""
    metadata = get_metadata_func(item.item_id)
    
    # Get authors from cached metadata
    creators = metadata.get('creators', [])
    authors = []
    for creator in creators:
        if creator.get('creatorType') == 'author':
            name_parts = []
            if creator.get('lastName'):
                name_parts.append(creator['lastName'])
            if creator.get('firstName'):
                name_parts.append(creator['firstName'])
            if name_parts:
                authors.append(' '.join(name_parts))
    
    # Sort authors for consistent comparison (as per original logic)
    authors_str = '; '.join(sorted(authors))
    
    # Get year from cached metadata
    date = metadata.get('date', '')
    year = extract_year_from_date(date)
    
    return DuplicateKey(
        title=item.title,
        authors=authors_str,
        year=year
    )


def select_best_duplicate_with_cache(duplicates: List[ZoteroItem], get_metadata_func) -> ZoteroItem:
    """Select the best item from duplicates using cached metadata."""
    if len(duplicates) == 1:
        return duplicates[0]
    
    # Separate items with and without attachments
    with_attachments = [item for item in duplicates if item.attachment_type in ["pdf", "epub"]]
    without_attachments = [item for item in duplicates if item.attachment_type not in ["pdf", "epub"]]
    
    # Prefer items with attachments
    candidates = with_attachments if with_attachments else without_attachments
    
    # Get modification dates for final selection using cached metadata
    dated_candidates = []
    for item in candidates:
        metadata = get_metadata_func(item.item_id)
        date_modified = metadata.get('dateModified', '')
        date_added = metadata.get('dateAdded', '')
        dated_candidates.append((item, date_modified, date_added))
    
    # Sort by modification date (descending), then by creation date (descending)
    dated_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    selected = dated_candidates[0][0]
    logger.debug(f"Selected item {selected.item_id} from {len(duplicates)} duplicates: {selected.title}")
    
    return selected

def deduplicate_grouped_items(db: ZoteroDatabase, grouped_items: List[Tuple], debug_mode: bool = False) -> Tuple[List[Tuple], int]:
    """Deduplicate items within grouped collections.
    
    This deduplicates within each collection separately to maintain collection grouping.
    
    Args:
        db: Database connection
        grouped_items: List of (collection, items) tuples
        debug_mode: If True, include duplicates marked as such in the output
    """
    if not grouped_items:
        return [], 0
    
    deduplicated_groups = []
    total_duplicates_removed = 0
    
    for collection, items in grouped_items:
        deduplicated_items, duplicates_removed = deduplicate_items(db, items, debug_mode)
        total_duplicates_removed += duplicates_removed
        
        if deduplicated_items:  # Only include groups with items
            deduplicated_groups.append((collection, deduplicated_items))
    
    return deduplicated_groups, total_duplicates_removed