from typing import List, Tuple, Optional
from .database import DatabaseConnection, get_attachment_type
from .queries import (
    build_collection_items_query, build_name_search_query, build_author_search_query,
    build_attachment_query
)
from .models import ZoteroItem

class ItemService:
    """Service for handling item operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def get_items_in_collection(self, collection_id: int, 
                              only_attachments: bool = False, after_year: int = None, 
                              before_year: int = None, only_books: bool = False, 
                              only_articles: bool = False, tags: Optional[List[str]] = None) -> List[ZoteroItem]:
        """Get items in a specific collection."""
        query, params = build_collection_items_query(
            collection_id, only_attachments, after_year, before_year, only_books, only_articles, tags
        )
        
        results = self.db.execute_query(query, params)
        items = []
        
        for row in results:
            item_id = row['itemID']
            title = row['title']
            item_type = row['typeName']
            order_index = row['orderIndex']
            content_type = row['contentType']
            attachment_path = row['path']
            date_added = row['dateAdded']
            date_modified = row['dateModified']
            
            # Process attachment data directly from query
            attachment_type = get_attachment_type(content_type) if content_type else None
            
            item = ZoteroItem(
                item_id=item_id,
                title=title or "Untitled",
                item_type=item_type,
                attachment_type=attachment_type,
                attachment_path=attachment_path,
                date_added=date_added,
                date_modified=date_modified
            )
            
            items.append(item)
        
        return items
    
    def search_items_by_name(self, name, exact_match: bool = False, 
                           only_attachments: bool = False, after_year: int = None, 
                           before_year: int = None, only_books: bool = False, 
                           only_articles: bool = False, tags: Optional[List[str]] = None) -> Tuple[List[ZoteroItem], int]:
        """Search items by title content. Returns (items, total_count)."""
        count_query, items_query, search_params = build_name_search_query(
            name, exact_match, only_attachments, after_year, before_year, only_books, only_articles, tags
        )
        
        # Get total count
        count_result = self.db.execute_single_query(count_query, search_params)
        total_count = count_result[0] if count_result else 0
        
        # Get all items
        results = self.db.execute_query(items_query, search_params)
        items = []
        
        for row in results:
            item_id = row['itemID']
            title = row['title']
            item_type = row['typeName']
            content_type = row['contentType']
            attachment_path = row['path']
            date_added = row['dateAdded']
            date_modified = row['dateModified']
            
            # Process attachment data directly from query
            attachment_type = get_attachment_type(content_type) if content_type else None
            
            item = ZoteroItem(
                item_id=item_id,
                title=title or "Untitled",
                item_type=item_type,
                attachment_type=attachment_type,
                attachment_path=attachment_path,
                date_added=date_added,
                date_modified=date_modified
            )
            
            items.append(item)
        
        return items, total_count
    
    def search_items_by_author(self, author, exact_match: bool = False,
                             only_attachments: bool = False, after_year: int = None,
                             before_year: int = None, only_books: bool = False,
                             only_articles: bool = False, tags: Optional[List[str]] = None) -> Tuple[List[ZoteroItem], int]:
        """Search items by author name. Returns (items, total_count)."""
        count_query, items_query, search_params = build_author_search_query(
            author, exact_match, only_attachments, after_year, before_year, only_books, only_articles, tags
        )
        
        # Get total count
        count_result = self.db.execute_single_query(count_query, search_params)
        total_count = count_result[0] if count_result else 0
        
        # Get all items
        results = self.db.execute_query(items_query, search_params)
        items = []
        
        for row in results:
            item_id = row['itemID']
            title = row['title']
            item_type = row['typeName']
            content_type = row['contentType']
            attachment_path = row['path']
            date_added = row['dateAdded']
            date_modified = row['dateModified']
            
            # Process attachment data directly from query
            attachment_type = get_attachment_type(content_type) if content_type else None
            
            item = ZoteroItem(
                item_id=item_id,
                title=title or "Untitled",
                item_type=item_type,
                attachment_type=attachment_type,
                attachment_path=attachment_path,
                date_added=date_added,
                date_modified=date_modified
            )
            
            items.append(item)
        
        return items, total_count
    
    def search_items_combined(self, name=None, author=None,
                            exact_match: bool = False, only_attachments: bool = False,
                            after_year: int = None, before_year: int = None,
                            only_books: bool = False, only_articles: bool = False, 
                            tags: Optional[List[str]] = None) -> Tuple[List[ZoteroItem], int]:
        """Search items by combined criteria (title and/or author). Returns (items, total_count)."""
        if name and author:
            # Use proper combined query
            from .queries import build_combined_search_query
            count_query, main_query, params = build_combined_search_query(
                name, author, exact_match, only_attachments,
                after_year, before_year, only_books, only_articles, tags
            )
            
            # Get count
            count_result = self.db.execute_single_query(count_query, params)
            total_count = count_result[0] if count_result else 0
            
            # Get items
            rows = self.db.execute_query(main_query, params)
            items = []
            
            for row in rows:
                item_id = row['itemID']
                title = row['title']
                item_type = row['typeName']
                content_type = row['contentType']
                attachment_path = row['attachment_path']
                date_added = row['dateAdded']
                date_modified = row['dateModified']
                
                # Process attachment data directly from query
                attachment_type = get_attachment_type(content_type) if content_type else None
                
                item = ZoteroItem(
                    item_id=item_id,
                    title=title or "Untitled",
                    item_type=item_type,
                    attachment_type=attachment_type,
                    attachment_path=attachment_path,
                    date_added=date_added,
                    date_modified=date_modified
                )
                
                items.append(item)
            
            return items, total_count
        elif name:
            return self.search_items_by_name(
                name, exact_match, only_attachments,
                after_year, before_year, only_books, only_articles, tags
            )
        elif author:
            return self.search_items_by_author(
                author, exact_match, only_attachments,
                after_year, before_year, only_books, only_articles, tags
            )
        elif tags: # Handle case where only tags are provided
            return self.search_items_by_name(
                None, exact_match, only_attachments,
                after_year, before_year, only_books, only_articles, tags
            )
        else:
            return [], 0