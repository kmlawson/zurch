"""Duplicate detection and handling for zurch."""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from .search import ZoteroItem, ZoteroDatabase

logger = logging.getLogger(__name__)

@dataclass
class DuplicateKey:
    """Key for identifying duplicate items based on author, title, and year."""
    title: str
    authors: str  # Concatenated author names
    year: Optional[str]
    
    def __hash__(self):
        return hash((self.title.lower(), self.authors.lower(), self.year))
    
    def __eq__(self, other):
        if not isinstance(other, DuplicateKey):
            return False
        return (self.title.lower() == other.title.lower() and 
                self.authors.lower() == other.authors.lower() and 
                self.year == other.year)

def extract_year_from_date(date_string: Optional[str]) -> Optional[str]:
    """Extract year from various date formats."""
    if not date_string:
        return None
    
    # Try to extract year from common formats
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

def deduplicate_items(db: ZoteroDatabase, items: List[ZoteroItem]) -> Tuple[List[ZoteroItem], int]:
    """Remove duplicates from a list of items.
    
    Returns:
        Tuple of (deduplicated_items, number_of_duplicates_removed)
    """
    if not items:
        return [], 0
    
    # Group items by duplicate key
    duplicate_groups: Dict[DuplicateKey, List[ZoteroItem]] = {}
    
    for item in items:
        try:
            key = create_duplicate_key(db, item)
            if key not in duplicate_groups:
                duplicate_groups[key] = []
            duplicate_groups[key].append(item)
        except Exception as e:
            logger.warning(f"Error processing item {item.item_id} for deduplication: {e}")
            # If we can't process an item, include it anyway
            fallback_key = DuplicateKey(title=item.title, authors="", year=None)
            if fallback_key not in duplicate_groups:
                duplicate_groups[fallback_key] = []
            duplicate_groups[fallback_key].append(item)
    
    # Select best item from each group
    deduplicated = []
    total_duplicates_removed = 0
    
    for key, group in duplicate_groups.items():
        if len(group) > 1:
            total_duplicates_removed += len(group) - 1
            logger.debug(f"Found {len(group)} duplicates for: {key.title}")
        
        best_item = select_best_duplicate(db, group)
        deduplicated.append(best_item)
    
    # Maintain original order as much as possible
    # Create a mapping of item_id to original position
    original_positions = {item.item_id: i for i, item in enumerate(items)}
    deduplicated.sort(key=lambda item: original_positions.get(item.item_id, float('inf')))
    
    logger.info(f"Deduplication: {len(items)} -> {len(deduplicated)} items ({total_duplicates_removed} duplicates removed)")
    
    return deduplicated, total_duplicates_removed

def deduplicate_grouped_items(db: ZoteroDatabase, grouped_items: List[Tuple]) -> Tuple[List[Tuple], int]:
    """Deduplicate items within grouped collections.
    
    This deduplicates within each collection separately to maintain collection grouping.
    """
    if not grouped_items:
        return [], 0
    
    deduplicated_groups = []
    total_duplicates_removed = 0
    
    for collection, items in grouped_items:
        deduplicated_items, duplicates_removed = deduplicate_items(db, items)
        total_duplicates_removed += duplicates_removed
        
        if deduplicated_items:  # Only include groups with items
            deduplicated_groups.append((collection, deduplicated_items))
    
    return deduplicated_groups, total_duplicates_removed