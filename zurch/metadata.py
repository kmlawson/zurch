import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from .database import DatabaseConnection
from .queries import (
    build_item_metadata_query, build_item_creators_query, 
    build_item_collections_query, build_attachment_path_query, build_item_tags_query
)

logger = logging.getLogger(__name__)

class MetadataService:
    """Service for handling metadata and attachment operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def get_item_metadata(self, item_id: int) -> Dict[str, Any]:
        """Get full metadata for an item."""
        # Get basic item info
        basic_query = """
            SELECT it.typeName, i.dateAdded, i.dateModified
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.itemID = ?
        """
        
        item_info = self.db.execute_single_query(basic_query, (item_id,))
        if not item_info:
            raise ValueError(f"Item {item_id} not found")
        
        metadata = {
            "itemType": item_info[0],
            "dateAdded": item_info[1],
            "dateModified": item_info[2]
        }
        
        # Get field data
        field_results = self.db.execute_query(build_item_metadata_query(), (item_id,))
        for field_name, value in field_results:
            metadata[field_name] = value
        
        # Get creators
        creator_results = self.db.execute_query(build_item_creators_query(), (item_id,))
        creators = []
        for creator_type, first_name, last_name in creator_results:
            creator = {"creatorType": creator_type}
            if first_name:
                creator["firstName"] = first_name
            if last_name:
                creator["lastName"] = last_name
            creators.append(creator)
        
        if creators:
            metadata["creators"] = creators
        
        return metadata
    
    def get_item_collections(self, item_id: int) -> List[str]:
        """Get list of collection names that contain this item."""
        try:
            results = self.db.execute_query(build_item_collections_query(), (item_id,))
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting item collections: {e}")
            return []
    
    def get_item_tags(self, item_id: int) -> List[str]:
        """Get list of tags for this item."""
        try:
            results = self.db.execute_query(build_item_tags_query(), (item_id,))
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting item tags: {e}")
            return []
    
    def get_item_attachment_path(self, item_id: int, zotero_data_dir: Path) -> Optional[Path]:
        """Get the file system path for an item's attachment."""
        try:
            result = self.db.execute_single_query(build_attachment_path_query(), (item_id, item_id))
            
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