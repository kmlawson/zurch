from typing import List
from .database import DatabaseConnection
from .queries import build_collection_tree_query
from .models import ZoteroCollection

class CollectionService:
    """Service for handling collection operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def list_collections(self) -> List[ZoteroCollection]:
        """Get all collections with hierarchy information."""
        query = build_collection_tree_query()
        results = self.db.execute_query(query)
        
        return [
            ZoteroCollection(
                collection_id=row['collectionID'],
                name=row['collectionName'],
                parent_id=row['parentCollectionID'],
                depth=row['depth'],
                item_count=row['item_count'],
                full_path=row['path'],
                library_id=row['libraryID'],
                library_type=row['library_type'],
                library_name=row['library_name']
            )
            for row in results
        ]
    
    def search_collections(self, name: str, exact_match: bool = False) -> List[ZoteroCollection]:
        """Find collections by name (case-insensitive partial or exact match)."""
        collections = self.list_collections()
        
        if exact_match:
            matching = [c for c in collections if c.name.lower() == name.lower()]
        else:
            matching = [c for c in collections if name.lower() in c.name.lower()]
        
        # Sort by depth (least deep first), then by name
        matching.sort(key=lambda c: (c.depth, c.name.lower()))
        
        return matching
    
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
    
    def get_collection_item_count(self, collection_id: int) -> int:
        """Get the total number of items in a collection."""
        query = "SELECT COUNT(*) as count FROM collectionItems WHERE collectionID = ?"
        result = self.db.execute_single_query(query, (collection_id,))
        return result['count'] if result else 0