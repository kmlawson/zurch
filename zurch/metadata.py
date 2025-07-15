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
            "itemType": item_info['typeName'],
            "dateAdded": item_info['dateAdded'],
            "dateModified": item_info['dateModified']
        }
        
        # Get field data
        field_results = self.db.execute_query(build_item_metadata_query(), (item_id,))
        for row in field_results:
            metadata[row['fieldName']] = row['value']
        
        # Get creators
        creator_results = self.db.execute_query(build_item_creators_query(), (item_id,))
        creators = []
        for row in creator_results:
            creator = {"creatorType": row['creatorType']}
            if row['firstName']:
                creator["firstName"] = row['firstName']
            if row['lastName']:
                creator["lastName"] = row['lastName']
            creators.append(creator)
        
        if creators:
            metadata["creators"] = creators
        
        return metadata
    
    def get_bulk_item_metadata(self, item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get metadata for multiple items in bulk to optimize deduplication."""
        if not item_ids:
            return {}
        
        # Convert to set to remove duplicates and back to list for SQL
        unique_ids = list(set(item_ids))
        
        # Handle large batches by splitting into chunks
        batch_size = 999  # SQLite limit for query parameters
        metadata_dict = {}
        
        for i in range(0, len(unique_ids), batch_size):
            batch_ids = unique_ids[i:i + batch_size]
            batch_metadata = self._get_bulk_metadata_batch(batch_ids)
            metadata_dict.update(batch_metadata)
        
        return metadata_dict
    
    def _get_bulk_metadata_batch(self, item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get metadata for a batch of items."""
        if not item_ids:
            return {}
        
        id_placeholders = ','.join(['?'] * len(item_ids))
        
        # Get basic item info for all items
        basic_query = f"""
            SELECT i.itemID, it.typeName, i.dateAdded, i.dateModified
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.itemID IN ({id_placeholders})
        """
        
        try:
            basic_results = self.db.execute_query(basic_query, item_ids)
            metadata_dict = {}
            
            for row in basic_results:
                item_id = row['itemID']
                metadata_dict[item_id] = {
                    "itemType": row['typeName'],
                    "dateAdded": row['dateAdded'],
                    "dateModified": row['dateModified']
                }
            
            # Get field data for all items
            field_query = f"""
                SELECT id.itemID, f.fieldName, idv.value
                FROM itemData id
                JOIN fields f ON id.fieldID = f.fieldID
                JOIN itemDataValues idv ON id.valueID = idv.valueID
                WHERE id.itemID IN ({id_placeholders})
            """
            
            field_results = self.db.execute_query(field_query, item_ids)
            for row in field_results:
                item_id = row['itemID']
                if item_id in metadata_dict:
                    metadata_dict[item_id][row['fieldName']] = row['value']
            
            # Get creators for all items
            creator_query = f"""
                SELECT ic.itemID, crt.creatorType, c.firstName, c.lastName
                FROM itemCreators ic
                JOIN creators c ON ic.creatorID = c.creatorID
                JOIN creatorTypes crt ON ic.creatorTypeID = crt.creatorTypeID
                WHERE ic.itemID IN ({id_placeholders})
                ORDER BY ic.itemID, ic.orderIndex
            """
            
            creator_results = self.db.execute_query(creator_query, item_ids)
            creators_by_item = {}
            
            for row in creator_results:
                item_id = row['itemID']
                if item_id not in creators_by_item:
                    creators_by_item[item_id] = []
                
                creator = {"creatorType": row['creatorType']}
                if row['firstName']:
                    creator["firstName"] = row['firstName']
                if row['lastName']:
                    creator["lastName"] = row['lastName']
                creators_by_item[item_id].append(creator)
            
            # Add creators to metadata
            for item_id, creators in creators_by_item.items():
                if item_id in metadata_dict:
                    metadata_dict[item_id]["creators"] = creators
            
            # Ensure all requested items have at least an empty dict
            for item_id in item_ids:
                if item_id not in metadata_dict:
                    metadata_dict[item_id] = {}
            
            return metadata_dict
            
        except Exception as e:
            logger.error(f"Error in bulk metadata fetch for batch: {e}")
            # Return empty dict for all items to avoid further errors
            return {item_id: {} for item_id in item_ids}
    
    def get_item_collections(self, item_id: int) -> List[str]:
        """Get list of collection names that contain this item."""
        try:
            results = self.db.execute_query(build_item_collections_query(), (item_id,))
            return [row['path'] for row in results]
        except Exception as e:
            logger.error(f"Error getting item collections: {e}")
            return []
    
    def get_item_tags(self, item_id: int) -> List[str]:
        """Get list of tags for this item."""
        try:
            results = self.db.execute_query(build_item_tags_query(), (item_id,))
            return [row['name'] for row in results]
        except Exception as e:
            logger.error(f"Error getting item tags: {e}")
            return []
    
    def get_item_attachment_path(self, item_id: int, zotero_data_dir: Path) -> Optional[Path]:
        """Get the file system path for an item's attachment."""
        try:
            result = self.db.execute_single_query(build_attachment_path_query(), (item_id, item_id))
            
            if not result:
                return None
            
            attachment_path = result['path']
            item_key = result['key']
            
            if attachment_path and attachment_path.startswith("storage:"):
                filename = attachment_path[8:]  # Remove "storage:" prefix
                full_path = zotero_data_dir / "storage" / item_key / filename
                
                if full_path.exists():
                    return full_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting attachment path: {e}")
            return None