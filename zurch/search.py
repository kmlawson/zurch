import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ZoteroItem:
    item_id: int
    title: str
    item_type: str
    attachment_type: Optional[str] = None
    attachment_path: Optional[str] = None
    is_duplicate: bool = False

@dataclass
class ZoteroCollection:
    collection_id: int
    name: str
    parent_id: Optional[int] = None
    depth: int = 0
    item_count: int = 0
    full_path: str = ""

class DatabaseError(Exception):
    pass

class DatabaseLockedError(DatabaseError):
    pass

class ZoteroDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._verify_database()
    
    def _verify_database(self) -> None:
        """Verify database exists and is accessible."""
        if not self.db_path.exists():
            raise DatabaseError(f"Database not found: {self.db_path}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
                if not cursor.fetchone():
                    raise DatabaseError("Invalid Zotero database: missing items table")
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                raise DatabaseLockedError("Zotero database is locked. Close Zotero and try again.")
            raise DatabaseError(f"Cannot access database: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get read-only database connection."""
        return sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
    
    def get_database_version(self) -> str:
        """Get Zotero database version."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM version WHERE schema = 'system'")
                result = cursor.fetchone()
                return str(result[0]) if result else "unknown"
        except Exception as e:
            logger.warning(f"Cannot read database version: {e}")
            return "unknown"
    
    def list_collections(self) -> List[ZoteroCollection]:
        """Get all collections with hierarchy information."""
        query = """
        WITH RECURSIVE collection_tree AS (
            SELECT 
                collectionID,
                collectionName,
                parentCollectionID,
                0 as depth,
                collectionName as path
            FROM collections 
            WHERE parentCollectionID IS NULL
            
            UNION ALL
            
            SELECT 
                c.collectionID,
                c.collectionName,
                c.parentCollectionID,
                ct.depth + 1,
                ct.path || ' > ' || c.collectionName
            FROM collections c
            JOIN collection_tree ct ON c.parentCollectionID = ct.collectionID
        )
        SELECT 
            ct.collectionID,
            ct.collectionName,
            ct.parentCollectionID,
            ct.depth,
            COUNT(ci.itemID) as item_count,
            ct.path
        FROM collection_tree ct
        LEFT JOIN collectionItems ci ON ct.collectionID = ci.collectionID
        GROUP BY ct.collectionID, ct.collectionName, ct.parentCollectionID, ct.depth, ct.path
        ORDER BY ct.depth, ct.collectionName
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
                
                return [
                    ZoteroCollection(
                        collection_id=row[0],
                        name=row[1],
                        parent_id=row[2],
                        depth=row[3],
                        item_count=row[4],
                        full_path=row[5]
                    )
                    for row in results
                ]
        except Exception as e:
            raise DatabaseError(f"Error listing collections: {e}")
    
    def search_collections(self, name: str) -> List[ZoteroCollection]:
        """Find collections by name (case-insensitive partial match)."""
        collections = self.list_collections()
        matching = [c for c in collections if name.lower() in c.name.lower()]
        
        # Sort by depth (least deep first), then by name
        matching.sort(key=lambda c: (c.depth, c.name.lower()))
        
        return matching
    
    def get_collection_items(self, collection_name: str, max_results: int = 100, only_attachments: bool = False) -> tuple[List[ZoteroItem], int]:
        """Get items from collections matching the given name. Returns (items, total_count)."""
        collections = self.search_collections(collection_name)
        
        if not collections:
            return [], 0
        
        # Get total count first
        total_count = 0
        for collection in collections:
            total_count += self._get_collection_item_count(collection.collection_id)
        
        # Get items from all matching collections, ordered by collection depth
        all_items = []
        
        for collection in collections:
            items = self._get_items_in_collection(collection.collection_id, max_results, only_attachments)
            all_items.extend(items)
            
            if len(all_items) >= max_results:
                break
        
        # Filter again if needed (since we're combining from multiple collections)
        if only_attachments:
            all_items = [item for item in all_items if item.attachment_type in ["pdf", "epub"]]
        
        return all_items[:max_results], total_count

    def get_collection_items_grouped(self, collection_name: str, max_results: int = 100, only_attachments: bool = False) -> tuple[List[tuple[ZoteroCollection, List[ZoteroItem]]], int]:
        """Get items from collections matching the given name, grouped by collection. Returns (grouped_items, total_count)."""
        collections = self.search_collections(collection_name)
        
        if not collections:
            return [], 0
        
        # Get total count first
        total_count = 0
        for collection in collections:
            total_count += self._get_collection_item_count(collection.collection_id)
        
        # Get items from each collection separately, maintaining grouping
        grouped_items = []
        items_added = 0
        
        for collection in collections:
            if items_added >= max_results:
                break
                
            remaining_limit = max_results - items_added
            items = self._get_items_in_collection(collection.collection_id, remaining_limit, only_attachments)
            
            # Filter by attachments if requested
            if only_attachments:
                items = [item for item in items if item.attachment_type in ["pdf", "epub"]]
            
            if items:  # Only add if there are items
                grouped_items.append((collection, items))
                items_added += len(items)
        
        return grouped_items, total_count
    
    def _get_collection_item_count(self, collection_id: int) -> int:
        """Get the total number of items in a collection."""
        query = "SELECT COUNT(*) FROM collectionItems WHERE collectionID = ?"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (collection_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting collection item count: {e}")
            return 0
    
    def _get_items_in_collection(self, collection_id: int, max_results: int, only_attachments: bool = False) -> List[ZoteroItem]:
        """Get items in a specific collection."""
        # First get the basic items without attachments
        query = """
        SELECT 
            i.itemID,
            COALESCE(title_data.value, '') as title,
            it.typeName,
            ci.orderIndex
        FROM collectionItems ci
        JOIN items i ON ci.itemID = i.itemID
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        LEFT JOIN (
            SELECT id.itemID, idv.value
            FROM itemData id
            JOIN itemDataValues idv ON id.valueID = idv.valueID
            WHERE id.fieldID = 1  -- title field
        ) title_data ON i.itemID = title_data.itemID
        WHERE ci.collectionID = ?
        ORDER BY LOWER(COALESCE(title_data.value, ''))
        LIMIT ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (collection_id, max_results))
                results = cursor.fetchall()
                
                items = []
                for row in results:
                    item_id, title, item_type, order_index = row
                    
                    # Get the first attachment for this item
                    attachment_query = """
                    SELECT contentType, path FROM itemAttachments 
                    WHERE parentItemID = ? OR itemID = ?
                    LIMIT 1
                    """
                    cursor.execute(attachment_query, (item_id, item_id))
                    attachment_result = cursor.fetchone()
                    
                    attachment_type = None
                    attachment_path = None
                    if attachment_result:
                        content_type, path = attachment_result
                        attachment_type = self._get_attachment_type(content_type)
                        attachment_path = path
                    
                    item = ZoteroItem(
                        item_id=item_id,
                        title=title or "Untitled",
                        item_type=item_type,
                        attachment_type=attachment_type,
                        attachment_path=attachment_path
                    )
                    
                    # Filter by attachments if requested
                    if only_attachments:
                        if attachment_type in ["pdf", "epub"]:
                            items.append(item)
                    else:
                        items.append(item)
                
                return items
        except Exception as e:
            raise DatabaseError(f"Error getting collection items: {e}")
    
    def search_items_by_name(self, name, max_results: int = 100, exact_match: bool = False, only_attachments: bool = False, after_year: int = None, before_year: int = None) -> tuple[List[ZoteroItem], int]:
        """Search items by title content. Returns (items, total_count).
        
        Args:
            name: Can be a string (phrase search) or list of strings (AND search for multiple keywords)
            max_results: Maximum number of results to return
            exact_match: If True, use exact matching
            only_attachments: If True, only return items with PDF/EPUB attachments
            after_year: If provided, only return items published after this year (inclusive)
            before_year: If provided, only return items published before this year (inclusive)
        """
        # Handle multiple keywords (AND search) vs single phrase search
        if isinstance(name, list) and len(name) > 1 and not exact_match:
            # Multiple keywords - each must be present in title (AND logic)
            from .utils import escape_sql_like_pattern
            search_conditions = []
            search_params = []
            
            for keyword in name:
                if '%' in keyword or '_' in keyword:
                    # User provided wildcards - add partial matching unless already positioned
                    if not keyword.startswith('%'):
                        keyword = '%' + keyword  # Add leading wildcard for partial matching
                    if not keyword.endswith('%'):
                        keyword = keyword + '%'  # Add trailing wildcard for partial matching
                    search_conditions.append("LOWER(idv.value) LIKE LOWER(?)")
                    search_params.append(keyword)
                else:
                    # Escape and add partial matching wildcards
                    escaped_keyword = escape_sql_like_pattern(keyword)
                    search_conditions.append("LOWER(idv.value) LIKE LOWER(?) ESCAPE '\\'")
                    search_params.append(f"%{escaped_keyword}%")
            
            where_clause = "WHERE " + " AND ".join(search_conditions)
            
        else:
            # Single keyword or phrase search (or exact match)
            if isinstance(name, list):
                name = ' '.join(name)  # Join list into single string
                
            if exact_match:
                search_params = [name]
                where_clause = "WHERE LOWER(idv.value) = LOWER(?)"
            else:
                # Handle wildcard patterns vs regular search
                if '%' in name or '_' in name:
                    # User provided wildcards - add partial matching unless already positioned
                    if not name.startswith('%'):
                        name = '%' + name  # Add leading wildcard for partial matching
                    if not name.endswith('%'):
                        name = name + '%'  # Add trailing wildcard for partial matching
                    search_params = [name]
                    where_clause = "WHERE LOWER(idv.value) LIKE LOWER(?)"
                else:
                    # Import escape function
                    from .utils import escape_sql_like_pattern
                    # Escape SQL LIKE wildcards in user input for partial matching
                    escaped_name = escape_sql_like_pattern(name)
                    search_params = [f"%{escaped_name}%"]
                    where_clause = "WHERE LOWER(idv.value) LIKE LOWER(?) ESCAPE '\\'"
        
        # Add date filtering if specified
        date_conditions = []
        if after_year is not None:
            date_conditions.append("CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?")
            search_params.append(after_year)
        if before_year is not None:
            date_conditions.append("CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) <= ?")
            search_params.append(before_year)
        
        if date_conditions:
            where_clause += " AND " + " AND ".join(date_conditions)
        
        # First get the total count
        count_query = f"""
        SELECT COUNT(DISTINCT i.itemID)
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        LEFT JOIN itemData id ON i.itemID = id.itemID AND id.fieldID = 1  -- title field only
        LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
        LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field
        LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
        {where_clause}
        """
        
        # Then get the actual items (without attachments to avoid duplicates)
        items_query = f"""
        SELECT DISTINCT
            i.itemID,
            COALESCE(idv.value, '') as title,
            it.typeName
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        LEFT JOIN itemData id ON i.itemID = id.itemID AND id.fieldID = 1  -- title field only
        LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
        LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field
        LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
        {where_clause}
        ORDER BY LOWER(idv.value)
        LIMIT ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute(count_query, search_params)
                total_count = cursor.fetchone()[0]
                
                # Get items
                cursor.execute(items_query, search_params + [max_results])
                results = cursor.fetchall()
                
                items = []
                for row in results:
                    item_id, title, item_type = row
                    
                    # Get the first attachment for this item
                    attachment_query = """
                    SELECT contentType, path FROM itemAttachments 
                    WHERE parentItemID = ? OR itemID = ?
                    LIMIT 1
                    """
                    cursor.execute(attachment_query, (item_id, item_id))
                    attachment_result = cursor.fetchone()
                    
                    attachment_type = None
                    attachment_path = None
                    if attachment_result:
                        content_type, path = attachment_result
                        attachment_type = self._get_attachment_type(content_type)
                        attachment_path = path
                    
                    item = ZoteroItem(
                        item_id=item_id,
                        title=title or "Untitled",
                        item_type=item_type,
                        attachment_type=attachment_type,
                        attachment_path=attachment_path
                    )
                    
                    # Filter by attachments if requested
                    if only_attachments:
                        if attachment_type in ["pdf", "epub"]:
                            items.append(item)
                    else:
                        items.append(item)
                
                return items, total_count
        except Exception as e:
            raise DatabaseError(f"Error searching items: {e}")
    
    def search_items_by_author(self, author, max_results: int = 100, exact_match: bool = False, only_attachments: bool = False, after_year: int = None, before_year: int = None) -> tuple[List[ZoteroItem], int]:
        """Search items by author name. Returns (items, total_count).
        
        Args:
            author: Can be a string (phrase search) or list of strings (AND search for multiple keywords)
            max_results: Maximum number of results to return
            exact_match: If True, use exact matching
            only_attachments: If True, only return items with PDF/EPUB attachments
            after_year: If provided, only return items published after this year (inclusive)
            before_year: If provided, only return items published before this year (inclusive)
        """
        # Handle multiple keywords (AND search) vs single phrase search
        if isinstance(author, list) and len(author) > 1 and not exact_match:
            # Multiple keywords - each must be present in author names (AND logic)
            from .utils import escape_sql_like_pattern
            search_conditions = []
            search_params = []
            
            for keyword in author:
                if '%' in keyword or '_' in keyword:
                    # User provided wildcards - add partial matching unless already positioned
                    if not keyword.startswith('%'):
                        keyword = '%' + keyword
                    if not keyword.endswith('%'):
                        keyword = keyword + '%'
                    search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                    search_params.extend([keyword, keyword])
                else:
                    # Escape and add partial matching wildcards
                    escaped_keyword = escape_sql_like_pattern(keyword)
                    search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) ESCAPE '\\' OR LOWER(c.lastName) LIKE LOWER(?) ESCAPE '\\')")
                    search_params.extend([f"%{escaped_keyword}%", f"%{escaped_keyword}%"])
            
            author_where_clause = " AND ".join(search_conditions)
            
        else:
            # Single keyword or phrase search (or exact match)
            if isinstance(author, list):
                author = ' '.join(author)  # Join list into single string
                
            if exact_match:
                author_where_clause = "(LOWER(c.firstName) = LOWER(?) OR LOWER(c.lastName) = LOWER(?))"
                search_params = [author, author]
            else:
                # Handle wildcard patterns vs regular search
                if '%' in author or '_' in author:
                    # User provided wildcards - add partial matching unless already positioned
                    if not author.startswith('%'):
                        author = '%' + author
                    if not author.endswith('%'):
                        author = author + '%'
                    author_where_clause = "(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))"
                    search_params = [author, author]
                else:
                    # Import escape function
                    from .utils import escape_sql_like_pattern
                    # Escape SQL LIKE wildcards in user input for partial matching
                    escaped_author = escape_sql_like_pattern(author)
                    author_where_clause = "(LOWER(c.firstName) LIKE LOWER(?) ESCAPE '\\' OR LOWER(c.lastName) LIKE LOWER(?) ESCAPE '\\')"
                    search_params = [f"%{escaped_author}%", f"%{escaped_author}%"]
        
        # Add date filtering if specified
        date_conditions = []
        if after_year is not None:
            date_conditions.append("CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?")
            search_params.append(after_year)
        if before_year is not None:
            date_conditions.append("CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) <= ?")
            search_params.append(before_year)
        
        # Combine conditions
        where_conditions = [f"({author_where_clause})"]
        if date_conditions:
            where_conditions.extend(date_conditions)
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # First get the total count
        count_query = f"""
        SELECT COUNT(DISTINCT i.itemID)
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        JOIN itemCreators ic ON i.itemID = ic.itemID
        JOIN creators c ON ic.creatorID = c.creatorID
        LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field
        LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
        {where_clause}
        """
        
        # Then get the actual items
        items_query = f"""
        SELECT DISTINCT
            i.itemID,
            COALESCE(idv_title.value, '') as title,
            it.typeName
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        JOIN itemCreators ic ON i.itemID = ic.itemID
        JOIN creators c ON ic.creatorID = c.creatorID
        LEFT JOIN itemData id_title ON i.itemID = id_title.itemID AND id_title.fieldID = 1  -- title field
        LEFT JOIN itemDataValues idv_title ON id_title.valueID = idv_title.valueID
        LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field
        LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
        {where_clause}
        ORDER BY LOWER(idv_title.value)
        LIMIT ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute(count_query, search_params)
                total_count = cursor.fetchone()[0]
                
                # Get items
                cursor.execute(items_query, search_params + [max_results])
                results = cursor.fetchall()
                
                items = []
                for row in results:
                    item_id, title, item_type = row
                    
                    # Get the first attachment for this item
                    attachment_query = """
                    SELECT contentType, path FROM itemAttachments 
                    WHERE parentItemID = ? OR itemID = ?
                    LIMIT 1
                    """
                    cursor.execute(attachment_query, (item_id, item_id))
                    attachment_result = cursor.fetchone()
                    
                    attachment_type = None
                    attachment_path = None
                    if attachment_result:
                        content_type, path = attachment_result
                        attachment_type = self._get_attachment_type(content_type)
                        attachment_path = path
                    
                    item = ZoteroItem(
                        item_id=item_id,
                        title=title or "Untitled",
                        item_type=item_type,
                        attachment_type=attachment_type,
                        attachment_path=attachment_path
                    )
                    
                    # Filter by attachments if requested
                    if only_attachments:
                        if attachment_type in ["pdf", "epub"]:
                            items.append(item)
                    else:
                        items.append(item)
                
                return items, total_count
        except Exception as e:
            raise DatabaseError(f"Error searching items by author: {e}")
    
    def search_items_combined(self, name=None, author=None, max_results: int = 100, exact_match: bool = False, only_attachments: bool = False, after_year: int = None, before_year: int = None) -> tuple[List[ZoteroItem], int]:
        """Search items by combined criteria (title and/or author). Returns (items, total_count).
        
        Args:
            name: Title search criteria (string or list of strings)
            author: Author search criteria (string or list of strings)
            max_results: Maximum number of results to return
            exact_match: If True, use exact matching
            only_attachments: If True, only return items with PDF/EPUB attachments
            after_year: If provided, only return items published after this year (inclusive)
            before_year: If provided, only return items published before this year (inclusive)
        """
        search_conditions = []
        search_params = []
        
        # Handle title search criteria
        if name is not None:
            if isinstance(name, list) and len(name) > 1 and not exact_match:
                # Multiple keywords - each must be present in title (AND logic)
                from .utils import escape_sql_like_pattern
                title_conditions = []
                
                for keyword in name:
                    if '%' in keyword or '_' in keyword:
                        if not keyword.startswith('%'):
                            keyword = '%' + keyword
                        if not keyword.endswith('%'):
                            keyword = keyword + '%'
                        title_conditions.append("LOWER(idv_title.value) LIKE LOWER(?)")
                        search_params.append(keyword)
                    else:
                        escaped_keyword = escape_sql_like_pattern(keyword)
                        title_conditions.append("LOWER(idv_title.value) LIKE LOWER(?) ESCAPE '\\'")
                        search_params.append(f"%{escaped_keyword}%")
                
                search_conditions.append("(" + " AND ".join(title_conditions) + ")")
            else:
                # Single keyword or phrase search
                if isinstance(name, list):
                    name = ' '.join(name)
                    
                if exact_match:
                    search_conditions.append("LOWER(idv_title.value) = LOWER(?)")
                    search_params.append(name)
                else:
                    if '%' in name or '_' in name:
                        if not name.startswith('%'):
                            name = '%' + name
                        if not name.endswith('%'):
                            name = name + '%'
                        search_conditions.append("LOWER(idv_title.value) LIKE LOWER(?)")
                        search_params.append(name)
                    else:
                        from .utils import escape_sql_like_pattern
                        escaped_name = escape_sql_like_pattern(name)
                        search_conditions.append("LOWER(idv_title.value) LIKE LOWER(?) ESCAPE '\\'")
                        search_params.append(f"%{escaped_name}%")
        
        # Handle author search criteria
        if author is not None:
            if isinstance(author, list) and len(author) > 1 and not exact_match:
                # Multiple keywords - each must be present in author names (AND logic)
                from .utils import escape_sql_like_pattern
                author_conditions = []
                
                for keyword in author:
                    if '%' in keyword or '_' in keyword:
                        if not keyword.startswith('%'):
                            keyword = '%' + keyword
                        if not keyword.endswith('%'):
                            keyword = keyword + '%'
                        author_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                        search_params.extend([keyword, keyword])
                    else:
                        escaped_keyword = escape_sql_like_pattern(keyword)
                        author_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) ESCAPE '\\' OR LOWER(c.lastName) LIKE LOWER(?) ESCAPE '\\')")
                        search_params.extend([f"%{escaped_keyword}%", f"%{escaped_keyword}%"])
                
                search_conditions.append("(" + " AND ".join(author_conditions) + ")")
            else:
                # Single keyword or phrase search
                if isinstance(author, list):
                    author = ' '.join(author)
                    
                if exact_match:
                    search_conditions.append("(LOWER(c.firstName) = LOWER(?) OR LOWER(c.lastName) = LOWER(?))")
                    search_params.extend([author, author])
                else:
                    if '%' in author or '_' in author:
                        if not author.startswith('%'):
                            author = '%' + author
                        if not author.endswith('%'):
                            author = author + '%'
                        search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                        search_params.extend([author, author])
                    else:
                        from .utils import escape_sql_like_pattern
                        escaped_author = escape_sql_like_pattern(author)
                        search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) ESCAPE '\\' OR LOWER(c.lastName) LIKE LOWER(?) ESCAPE '\\')")
                        search_params.extend([f"%{escaped_author}%", f"%{escaped_author}%"])
        
        # Add date filtering if specified
        if after_year is not None:
            search_conditions.append("CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?")
            search_params.append(after_year)
        if before_year is not None:
            search_conditions.append("CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) <= ?")
            search_params.append(before_year)
        
        # Construct WHERE clause
        if search_conditions:
            where_clause = "WHERE " + " AND ".join(search_conditions)
        else:
            where_clause = ""
        
        # Base tables - need both title and author joins when combining searches
        base_from = """
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        LEFT JOIN itemData id_title ON i.itemID = id_title.itemID AND id_title.fieldID = 1  -- title field
        LEFT JOIN itemDataValues idv_title ON id_title.valueID = idv_title.valueID
        LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field
        LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
        """
        
        # Add author joins only if author search is specified
        if author is not None:
            base_from += """
            JOIN itemCreators ic ON i.itemID = ic.itemID
            JOIN creators c ON ic.creatorID = c.creatorID
            """
        
        # Count query
        count_query = f"""
        SELECT COUNT(DISTINCT i.itemID)
        {base_from}
        {where_clause}
        """
        
        # Items query
        items_query = f"""
        SELECT DISTINCT
            i.itemID,
            COALESCE(idv_title.value, '') as title,
            it.typeName
        {base_from}
        {where_clause}
        ORDER BY LOWER(idv_title.value)
        LIMIT ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute(count_query, search_params)
                total_count = cursor.fetchone()[0]
                
                # Get items
                cursor.execute(items_query, search_params + [max_results])
                results = cursor.fetchall()
                
                items = []
                for row in results:
                    item_id, title, item_type = row
                    
                    # Get the first attachment for this item
                    attachment_query = """
                    SELECT contentType, path FROM itemAttachments 
                    WHERE parentItemID = ? OR itemID = ?
                    LIMIT 1
                    """
                    cursor.execute(attachment_query, (item_id, item_id))
                    attachment_result = cursor.fetchone()
                    
                    attachment_type = None
                    attachment_path = None
                    if attachment_result:
                        content_type, path = attachment_result
                        attachment_type = self._get_attachment_type(content_type)
                        attachment_path = path
                    
                    item = ZoteroItem(
                        item_id=item_id,
                        title=title or "Untitled",
                        item_type=item_type,
                        attachment_type=attachment_type,
                        attachment_path=attachment_path
                    )
                    
                    # Filter by attachments if requested
                    if only_attachments:
                        if attachment_type in ["pdf", "epub"]:
                            items.append(item)
                    else:
                        items.append(item)
                
                return items, total_count
        except Exception as e:
            raise DatabaseError(f"Error searching items with combined criteria: {e}")
    
    def get_item_metadata(self, item_id: int) -> Dict[str, Any]:
        """Get full metadata for an item."""
        query = """
        SELECT 
            f.fieldName,
            idv.value
        FROM itemData id
        JOIN fields f ON id.fieldID = f.fieldID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        WHERE id.itemID = ?
        ORDER BY f.fieldName
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get basic item info
                cursor.execute("""
                    SELECT it.typeName, i.dateAdded, i.dateModified
                    FROM items i
                    JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
                    WHERE i.itemID = ?
                """, (item_id,))
                
                item_info = cursor.fetchone()
                if not item_info:
                    raise DatabaseError(f"Item {item_id} not found")
                
                metadata = {
                    "itemType": item_info[0],
                    "dateAdded": item_info[1],
                    "dateModified": item_info[2]
                }
                
                # Get field data
                cursor.execute(query, (item_id,))
                for field_name, value in cursor.fetchall():
                    metadata[field_name] = value
                
                # Get creators
                cursor.execute("""
                    SELECT ct.creatorType, c.firstName, c.lastName
                    FROM itemCreators ic
                    JOIN creators c ON ic.creatorID = c.creatorID
                    JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
                    WHERE ic.itemID = ?
                    ORDER BY ic.orderIndex
                """, (item_id,))
                
                creators = []
                for creator_type, first_name, last_name in cursor.fetchall():
                    creator = {"creatorType": creator_type}
                    if first_name:
                        creator["firstName"] = first_name
                    if last_name:
                        creator["lastName"] = last_name
                    creators.append(creator)
                
                if creators:
                    metadata["creators"] = creators
                
                return metadata
                
        except Exception as e:
            raise DatabaseError(f"Error getting item metadata: {e}")
    
    def get_item_attachment_path(self, item_id: int, zotero_data_dir: Path) -> Optional[Path]:
        """Get the file system path for an item's attachment."""
        query = """
        SELECT ia.path, i.key
        FROM itemAttachments ia
        JOIN items i ON ia.itemID = i.itemID
        WHERE ia.parentItemID = ? OR ia.itemID = ?
        LIMIT 1
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (item_id, item_id))
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                attachment_path, item_key = result
                
                if attachment_path and attachment_path.startswith("storage:"):
                    filename = attachment_path[8:]  # Remove "storage:" prefix
                    full_path = zotero_data_dir / "storage" / item_key / filename
                    
                    if full_path.exists():
                        return full_path
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting attachment path: {e}")
            return None
    
    def find_similar_collections(self, name: str, limit: int = 5) -> List[ZoteroCollection]:
        """Find collections with similar names for suggestions."""
        collections = self.list_collections()
        
        # Simple similarity scoring based on common words
        def similarity_score(collection_name: str, search_name: str) -> int:
            col_words = set(collection_name.lower().split())
            search_words = set(search_name.lower().split())
            return len(col_words.intersection(search_words))
        
        # Score all collections
        scored_collections = [
            (collection, similarity_score(collection.name, name))
            for collection in collections
        ]
        
        # Filter out collections with zero score and sort by score
        similar = [
            collection for collection, score in scored_collections 
            if score > 0
        ]
        
        # Sort by score (descending) then by name
        similar.sort(key=lambda c: (-similarity_score(c.name, name), c.name.lower()))
        
        return similar[:limit]
    
    def get_item_collections(self, item_id: int) -> List[str]:
        """Get list of collection names that contain this item."""
        query = """
        WITH RECURSIVE collection_tree AS (
            SELECT 
                collectionID,
                collectionName,
                parentCollectionID,
                0 as depth,
                collectionName as path
            FROM collections 
            WHERE parentCollectionID IS NULL
            
            UNION ALL
            
            SELECT 
                c.collectionID,
                c.collectionName,
                c.parentCollectionID,
                ct.depth + 1,
                ct.path || ' > ' || c.collectionName
            FROM collections c
            JOIN collection_tree ct ON c.parentCollectionID = ct.collectionID
        )
        SELECT ct.path
        FROM collection_tree ct
        JOIN collectionItems ci ON ct.collectionID = ci.collectionID
        WHERE ci.itemID = ?
        ORDER BY ct.path
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (item_id,))
                results = cursor.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting item collections: {e}")
            return []

    @staticmethod
    def _get_attachment_type(content_type: str) -> str:
        """Convert MIME type to attachment type for icon display."""
        if not content_type:
            return None
        
        content_type = content_type.lower()
        if content_type == "application/pdf":
            return "pdf"
        elif content_type == "application/epub+zip":
            return "epub"
        elif content_type.startswith("text/"):
            return "txt"
        else:
            return None