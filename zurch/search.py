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
    
    def get_collection_items(self, collection_name: str, max_results: int = 100) -> tuple[List[ZoteroItem], int]:
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
            items = self._get_items_in_collection(collection.collection_id, max_results)
            all_items.extend(items)
            
            if len(all_items) >= max_results:
                break
        
        return all_items[:max_results], total_count
    
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
    
    def _get_items_in_collection(self, collection_id: int, max_results: int) -> List[ZoteroItem]:
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
                    
                    items.append(ZoteroItem(
                        item_id=item_id,
                        title=title or "Untitled",
                        item_type=item_type,
                        attachment_type=attachment_type,
                        attachment_path=attachment_path
                    ))
                
                return items
        except Exception as e:
            raise DatabaseError(f"Error getting collection items: {e}")
    
    def search_items_by_name(self, name: str, max_results: int = 100, exact_match: bool = False) -> tuple[List[ZoteroItem], int]:
        """Search items by title content. Returns (items, total_count)."""
        if exact_match:
            search_pattern = name
            where_clause = "WHERE LOWER(idv.value) = LOWER(?)"
        else:
            search_pattern = f"%{name}%"
            where_clause = "WHERE LOWER(idv.value) LIKE LOWER(?)"
        
        # First get the total count
        count_query = f"""
        SELECT COUNT(DISTINCT i.itemID)
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        LEFT JOIN itemData id ON i.itemID = id.itemID AND id.fieldID = 1  -- title field only
        LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
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
        {where_clause}
        ORDER BY LOWER(idv.value)
        LIMIT ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute(count_query, (search_pattern,))
                total_count = cursor.fetchone()[0]
                
                # Get items
                cursor.execute(items_query, (search_pattern, max_results))
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
                    
                    items.append(ZoteroItem(
                        item_id=item_id,
                        title=title or "Untitled",
                        item_type=item_type,
                        attachment_type=attachment_type,
                        attachment_path=attachment_path
                    ))
                
                return items, total_count
        except Exception as e:
            raise DatabaseError(f"Error searching items: {e}")
    
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