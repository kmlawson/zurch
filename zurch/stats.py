import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple
from .database import DatabaseConnection
from .queries import (
    build_stats_total_counts_query, build_stats_item_types_query,
    build_stats_attachment_counts_query, build_stats_top_tags_query,
    build_stats_top_collections_query, build_stats_publication_decades_query
)

logger = logging.getLogger(__name__)

@dataclass
class DatabaseStats:
    """Container for database statistics."""
    total_items: int
    total_collections: int
    total_tags: int
    item_types: List[Tuple[str, int]]
    items_with_attachments: int
    items_without_attachments: int
    top_tags: List[Tuple[str, int]]
    top_collections: List[Tuple[str, int]]
    publication_decades: List[Tuple[str, int]]

class StatsService:
    """Service for gathering database statistics."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def get_database_stats(self) -> DatabaseStats:
        """Get comprehensive database statistics."""
        try:
            # Get total counts
            total_counts = self.db.execute_single_query(build_stats_total_counts_query())
            if total_counts:
                total_items = total_counts['total_items']
                total_collections = total_counts['total_collections']
                total_tags = total_counts['total_tags']
            else:
                total_items = total_collections = total_tags = 0
            
            # Get item types
            item_types_results = self.db.execute_query(build_stats_item_types_query())
            item_types = [(row['typeName'], row['count']) for row in item_types_results]
            
            # Get attachment counts
            attachment_counts = self.db.execute_single_query(build_stats_attachment_counts_query())
            if attachment_counts:
                items_with_attachments = attachment_counts['items_with_attachments'] or 0
                items_without_attachments = attachment_counts['items_without_attachments'] or 0
            else:
                items_with_attachments = 0
                items_without_attachments = total_items
            
            # Get top tags
            top_tags_results = self.db.execute_query(build_stats_top_tags_query())
            top_tags = [(row['name'], row['count']) for row in top_tags_results]
            
            # Get top collections
            top_collections_results = self.db.execute_query(build_stats_top_collections_query())
            top_collections = [(row['name'], row['count']) for row in top_collections_results]
            
            # Get publication decades
            publication_decades_results = self.db.execute_query(build_stats_publication_decades_query())
            publication_decades = [(row['decade'], row['count']) for row in publication_decades_results]
            
            return DatabaseStats(
                total_items=total_items,
                total_collections=total_collections,
                total_tags=total_tags,
                item_types=item_types,
                items_with_attachments=items_with_attachments,
                items_without_attachments=items_without_attachments,
                top_tags=top_tags,
                top_collections=top_collections,
                publication_decades=publication_decades
            )
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return DatabaseStats(
                total_items=0,
                total_collections=0,
                total_tags=0,
                item_types=[],
                items_with_attachments=0,
                items_without_attachments=0,
                top_tags=[],
                top_collections=[],
                publication_decades=[]
            )