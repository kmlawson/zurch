from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .database import DatabaseConnection, DatabaseError, DatabaseLockedError
from .collections import CollectionService
from .items import ItemService
from .metadata import MetadataService
from .stats import StatsService
from .models import ZoteroItem, ZoteroCollection

class ZoteroDatabase:
    """Main database interface combining all services."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_connection = DatabaseConnection(db_path)
        self.collections = CollectionService(self.db_connection)
        self.items = ItemService(self.db_connection)
        self.metadata = MetadataService(self.db_connection)
        self.stats = StatsService(self.db_connection)
    
    # Collection methods
    def list_collections(self) -> List[ZoteroCollection]:
        """Get all collections with hierarchy information."""
        return self.collections.list_collections()
    
    def search_collections(self, name: str, exact_match: bool = False) -> List[ZoteroCollection]:
        """Find collections by name (case-insensitive partial or exact match)."""
        return self.collections.search_collections(name, exact_match=exact_match)
    
    def find_similar_collections(self, name: str, limit: int = 5) -> List[ZoteroCollection]:
        """Find collections with similar names for suggestions."""
        return self.collections.find_similar_collections(name, limit)
    
    # Item search methods
    def get_collection_items(self, collection_name: str, 
                           only_attachments: bool = False, after_year: int = None, 
                           before_year: int = None, only_books: bool = False, 
                           only_articles: bool = False, tags: Optional[List[str]] = None,
                           exact_match: bool = False) -> Tuple[List[ZoteroItem], int]:
        """Get items from collections matching the given name. Returns (items, total_count)."""
        collections = self.search_collections(collection_name, exact_match=exact_match)
        
        if not collections:
            return [], 0
        
        # Get items from all matching collections, ordered by collection depth
        all_items = []

        for collection in collections:
            items = self.items.get_items_in_collection(
                collection.collection_id, only_attachments,
                after_year, before_year, only_books, only_articles, tags
            )
            all_items.extend(items)

        return all_items, len(all_items)
    
    def get_collection_items_grouped(self, collection_name: str, 
                                   only_attachments: bool = False, after_year: int = None, 
                                   before_year: int = None, only_books: bool = False, 
                                   only_articles: bool = False, tags: Optional[List[str]] = None,
                                   exact_match: bool = False) -> Tuple[List[Tuple[ZoteroCollection, List[ZoteroItem]]], int]:
        """Get items from collections matching the given name, grouped by collection. Returns (grouped_items, total_count)."""
        collections = self.search_collections(collection_name, exact_match=exact_match)
        
        if not collections:
            return [], 0
        
        # Get items from each collection separately, maintaining grouping
        grouped_items = []
        total_count = 0
        
        for collection in collections:
            items = self.items.get_items_in_collection(
                collection.collection_id, only_attachments,
                after_year, before_year, only_books, only_articles, tags
            )
            
            if items:  # Only add if there are items
                grouped_items.append((collection, items))
                total_count += len(items)
        
        return grouped_items, total_count
    
    def search_items_by_name(self, name, exact_match: bool = False,
                           only_attachments: bool = False, after_year: int = None,
                           before_year: int = None, only_books: bool = False,
                           only_articles: bool = False, tags: Optional[List[str]] = None) -> Tuple[List[ZoteroItem], int]:
        """Search items by title content. Returns (items, total_count)."""
        return self.items.search_items_by_name(
            name, exact_match, only_attachments,
            after_year, before_year, only_books, only_articles, tags
        )
    
    def search_items_by_author(self, author, exact_match: bool = False,
                             only_attachments: bool = False, after_year: int = None,
                             before_year: int = None, only_books: bool = False,
                             only_articles: bool = False, tags: Optional[List[str]] = None) -> Tuple[List[ZoteroItem], int]:
        """Search items by author name. Returns (items, total_count)."""
        return self.items.search_items_by_author(
            author, exact_match, only_attachments,
            after_year, before_year, only_books, only_articles, tags
        )
    
    def search_items_combined(self, name=None, author=None, 
                            exact_match: bool = False, only_attachments: bool = False,
                            after_year: int = None, before_year: int = None,
                            only_books: bool = False, only_articles: bool = False, 
                            tags: Optional[List[str]] = None) -> Tuple[List[ZoteroItem], int]:
        """Search items by combined criteria (title and/or author). Returns (items, total_count)."""
        return self.items.search_items_combined(
            name, author, exact_match, only_attachments,
            after_year, before_year, only_books, only_articles, tags
        )
    
    # Metadata methods
    def get_item_metadata(self, item_id: int) -> Dict[str, Any]:
        """Get full metadata for an item."""
        return self.metadata.get_item_metadata(item_id)
    
    def get_bulk_item_metadata(self, item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get metadata for multiple items in bulk to optimize performance."""
        return self.metadata.get_bulk_item_metadata(item_ids)
    
    def get_item_collections(self, item_id: int) -> List[str]:
        """Get list of collection names that contain this item."""
        return self.metadata.get_item_collections(item_id)
    
    def get_item_tags(self, item_id: int) -> List[str]:
        """Get list of tags for this item."""
        return self.metadata.get_item_tags(item_id)
    
    def get_item_attachment_path(self, item_id: int, zotero_data_dir: Path) -> Optional[Path]:
        """Get the file system path for an item's attachment."""
        return self.metadata.get_item_attachment_path(item_id, zotero_data_dir)
    
    # Database info methods
    def get_database_version(self) -> str:
        """Get Zotero database version."""
        return self.db_connection.get_database_version()
    
    def get_database_stats(self):
        """Get comprehensive database statistics."""
        return self.stats.get_database_stats()