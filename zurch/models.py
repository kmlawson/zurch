"""Data models for Zotero items and collections.

This module provides both Pydantic models (recommended) and legacy dataclass models
for backward compatibility.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

# Try to import Pydantic models, fall back to legacy if not available
try:
    from .pydantic_models import (
        ZoteroItemModel, 
        ZoteroCollectionModel, 
        ItemTypeEnum, 
        AttachmentTypeEnum
    )
    # Use Pydantic models as the default
    ZoteroItem = ZoteroItemModel
    ZoteroCollection = ZoteroCollectionModel
    ItemType = ItemTypeEnum
    AttachmentType = AttachmentTypeEnum
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback to legacy models if Pydantic not available
    PYDANTIC_AVAILABLE = False

# Legacy dataclass models for backward compatibility
class LegacyItemType(Enum):
    """Legacy enum for item types."""
    BOOK = "book"
    JOURNAL_ARTICLE = "journalArticle"
    DOCUMENT = "document"
    THESIS = "thesis"
    REPORT = "report"
    WEBPAGE = "webpage"
    
    @classmethod
    def from_string(cls, value: str) -> 'LegacyItemType':
        """Convert string to ItemType, defaulting to DOCUMENT."""
        for item_type in cls:
            if item_type.value.lower() == value.lower():
                return item_type
        return cls.DOCUMENT


class LegacyAttachmentType(Enum):
    """Legacy enum for attachment types."""
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"
    
    @classmethod
    def from_string(cls, value: Optional[str]) -> Optional['LegacyAttachmentType']:
        """Convert string to AttachmentType."""
        if not value:
            return None
        for attachment_type in cls:
            if attachment_type.value.lower() == value.lower():
                return attachment_type
        return None


@dataclass(slots=True)
class LegacyZoteroItem:
    """Legacy dataclass for Zotero items."""
    item_id: int
    title: str
    item_type: str
    attachment_type: Optional[str] = None
    attachment_path: Optional[str] = None
    is_duplicate: bool = False
    date_added: Optional[str] = None
    date_modified: Optional[str] = None
    
    def get_item_type_enum(self) -> LegacyItemType:
        """Get ItemType enum for this item."""
        return LegacyItemType.from_string(self.item_type)
    
    def get_attachment_type_enum(self) -> Optional[LegacyAttachmentType]:
        """Get AttachmentType enum for this item."""
        return LegacyAttachmentType.from_string(self.attachment_type)
    
    def has_attachment(self) -> bool:
        """Check if item has a readable attachment."""
        return self.attachment_type in ["pdf", "epub"]


@dataclass(slots=True)
class LegacyZoteroCollection:
    """Legacy dataclass for Zotero collections."""
    collection_id: int
    name: str
    parent_id: Optional[int] = None
    depth: int = 0
    item_count: int = 0
    full_path: str = ""
    library_id: int = 1
    library_type: str = "user"
    library_name: str = "Personal Library"
    
    def is_root(self) -> bool:
        """Check if this is a root collection."""
        return self.parent_id is None
    
    def is_group_collection(self) -> bool:
        """Check if this is a group collection."""
        return self.library_type == "group"
    
    def get_display_name(self) -> str:
        """Get the collection name with library context if needed."""
        if self.is_group_collection():
            return f"{self.name} ({self.library_name})"
        return self.name
    
    def get_path_components(self) -> list[str]:
        """Get collection path as list of components."""
        return self.full_path.split(' > ') if self.full_path else [self.name]


# Utility functions for model conversion (only if Pydantic available)
if PYDANTIC_AVAILABLE:
    def convert_to_pydantic_item(legacy_item: LegacyZoteroItem) -> ZoteroItemModel:
        """Convert legacy dataclass item to Pydantic model."""
        return ZoteroItemModel(
            item_id=legacy_item.item_id,
            title=legacy_item.title,
            item_type=legacy_item.item_type,
            attachment_type=legacy_item.attachment_type,
            attachment_path=legacy_item.attachment_path,
            is_duplicate=legacy_item.is_duplicate,
            date_added=legacy_item.date_added,
            date_modified=legacy_item.date_modified
        )


    def convert_to_pydantic_collection(legacy_collection: LegacyZoteroCollection) -> ZoteroCollectionModel:
        """Convert legacy dataclass collection to Pydantic model."""
        return ZoteroCollectionModel(
            collection_id=legacy_collection.collection_id,
            name=legacy_collection.name,
            parent_id=legacy_collection.parent_id,
            depth=legacy_collection.depth,
            item_count=legacy_collection.item_count,
            full_path=legacy_collection.full_path,
            library_id=legacy_collection.library_id,
            library_type=legacy_collection.library_type,
            library_name=legacy_collection.library_name
        )


# Set fallback models if Pydantic not available
if not PYDANTIC_AVAILABLE:
    ZoteroItem = LegacyZoteroItem
    ZoteroCollection = LegacyZoteroCollection
    ItemType = LegacyItemType
    AttachmentType = LegacyAttachmentType