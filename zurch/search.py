from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .database import DatabaseConnection, DatabaseError, DatabaseLockedError
from .collections import CollectionService
from .items import ItemService
from .metadata import MetadataService
from .models import ZoteroItem, ZoteroCollection

class ZoteroDatabase:
    """Main database interface combining all services."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_connection = DatabaseConnection(db_path)
        self.collections = CollectionService(self.db_connection)
        self.items = ItemService(self.db_connection)
        self.metadata = MetadataService(self.db_connection)
    
    # Collection methods
    def list_collections(self) -> List[ZoteroCollection]:
        """Get all collections with hierarchy information."""
        return self.collections.list_collections()
    
    def search_collections(self, name: str) -> List[ZoteroCollection]:
        """Find collections by name (case-insensitive partial match)."""
        return self.collections.search_collections(name)
    
    def find_similar_collections(self, name: str, limit: int = 5) -> List[ZoteroCollection]:
        """Find collections with similar names for suggestions."""
        return self.collections.find_similar_collections(name, limit)
    
    # Item search methods
    def get_collection_items(self, collection_name: str, 
                           only_attachments: bool = False, after_year: int = None, 
                           before_year: int = None, only_books: bool = False, 
                           only_articles: bool = False) -> Tuple[List[ZoteroItem], int]:
        """Get items from collections matching the given name. Returns (items, total_count)."""
        collections = self.search_collections(collection_name)
        
        if not collections:
            return [], 0
        
        # Get total count first
        total_count = 0
        for collection in collections:
            total_count += self.collections.get_collection_item_count(collection.collection_id)
        
        # Get items from all matching collections, ordered by collection depth
        all_items = []
        
        for collection in collections:
            items = self.items.get_items_in_collection(
                collection.collection_id, only_attachments, 
                after_year, before_year, only_books, only_articles
            )
            all_items.extend(items)
        
        return all_items, total_count
    
    def get_collection_items_grouped(self, collection_name: str, 
                                   only_attachments: bool = False, after_year: int = None, 
                                   before_year: int = None, only_books: bool = False, 
                                   only_articles: bool = False) -> Tuple[List[Tuple[ZoteroCollection, List[ZoteroItem]]], int]:
        """Get items from collections matching the given name, grouped by collection. Returns (grouped_items, total_count)."""
        collections = self.search_collections(collection_name)
        
        if not collections:
            return [], 0
        
        # Get total count first
        total_count = 0
        for collection in collections:
            total_count += self.collections.get_collection_item_count(collection.collection_id)
        
        # Get items from each collection separately, maintaining grouping
        grouped_items = []
        
        for collection in collections:
            items = self.items.get_items_in_collection(
                collection.collection_id, only_attachments,
                after_year, before_year, only_books, only_articles
            )
            
            if items:  # Only add if there are items
                grouped_items.append((collection, items))
        
        return grouped_items, total_count
    
    def search_items_by_name(self, name, exact_match: bool = False,
                           only_attachments: bool = False, after_year: int = None,
                           before_year: int = None, only_books: bool = False,
                           only_articles: bool = False) -> Tuple[List[ZoteroItem], int]:
        """Search items by title content. Returns (items, total_count)."""
        return self.items.search_items_by_name(
            name, exact_match, only_attachments,
            after_year, before_year, only_books, only_articles
        )
    
    def search_items_by_author(self, author, exact_match: bool = False,
                             only_attachments: bool = False, after_year: int = None,
                             before_year: int = None, only_books: bool = False,
                             only_articles: bool = False) -> Tuple[List[ZoteroItem], int]:
        """Search items by author name. Returns (items, total_count)."""
        return self.items.search_items_by_author(
            author, exact_match, only_attachments,
            after_year, before_year, only_books, only_articles
        )
    
    def search_items_combined(self, name=None, author=None, 
                            exact_match: bool = False, only_attachments: bool = False,
                            after_year: int = None, before_year: int = None,
                            only_books: bool = False, only_articles: bool = False) -> Tuple[List[ZoteroItem], int]:
        """Search items by combined criteria (title and/or author). Returns (items, total_count)."""
        return self.items.search_items_combined(
            name, author, exact_match, only_attachments,
            after_year, before_year, only_books, only_articles
        )
    
    # Metadata methods
    def get_item_metadata(self, item_id: int) -> Dict[str, Any]:
        """Get full metadata for an item."""
        return self.metadata.get_item_metadata(item_id)
    
    def get_item_collections(self, item_id: int) -> List[str]:
        """Get list of collection names that contain this item."""
        return self.metadata.get_item_collections(item_id)
    
    def get_item_attachment_path(self, item_id: int, zotero_data_dir: Path) -> Optional[Path]:
        """Get the file system path for an item's attachment."""
        return self.metadata.get_item_attachment_path(item_id, zotero_data_dir)
    
    # Database info methods
    def get_database_version(self) -> str:
        """Get Zotero database version."""
        return self.db_connection.get_database_version()