from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ItemType(Enum):
    """Enum for item types to avoid string typos."""
    BOOK = "book"
    JOURNAL_ARTICLE = "journalArticle"
    DOCUMENT = "document"
    THESIS = "thesis"
    REPORT = "report"
    WEBPAGE = "webpage"
    
    @classmethod
    def from_string(cls, value: str) -> 'ItemType':
        """Convert string to ItemType, defaulting to DOCUMENT."""
        for item_type in cls:
            if item_type.value.lower() == value.lower():
                return item_type
        return cls.DOCUMENT


class AttachmentType(Enum):
    """Enum for attachment types."""
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"
    
    @classmethod
    def from_string(cls, value: Optional[str]) -> Optional['AttachmentType']:
        """Convert string to AttachmentType."""
        if not value:
            return None
        for attachment_type in cls:
            if attachment_type.value.lower() == value.lower():
                return attachment_type
        return None


@dataclass(slots=True)
class ZoteroItem:
    """Represents a Zotero item with optimized memory usage."""
    item_id: int
    title: str
    item_type: str
    attachment_type: Optional[str] = None
    attachment_path: Optional[str] = None
    is_duplicate: bool = False
    date_added: Optional[str] = None
    date_modified: Optional[str] = None
    
    def get_item_type_enum(self) -> ItemType:
        """Get ItemType enum for this item."""
        return ItemType.from_string(self.item_type)
    
    def get_attachment_type_enum(self) -> Optional[AttachmentType]:
        """Get AttachmentType enum for this item."""
        return AttachmentType.from_string(self.attachment_type)
    
    def has_attachment(self) -> bool:
        """Check if item has a readable attachment."""
        return self.attachment_type in ["pdf", "epub"]


@dataclass(slots=True)
class ZoteroCollection:
    """Represents a Zotero collection with optimized memory usage."""
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