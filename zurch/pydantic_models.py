"""Pydantic models for Zotero data structures."""

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ItemTypeEnum(str, Enum):
    """Enum for item types with string value support."""
    BOOK = "book"
    JOURNAL_ARTICLE = "journalArticle"
    JOURNAL_ARTICLE_ALT = "journal article"  # Alternative format
    DOCUMENT = "document"
    THESIS = "thesis"
    REPORT = "report"
    WEBPAGE = "webpage"
    CONFERENCE_PAPER = "conferencePaper"
    MAGAZINE_ARTICLE = "magazineArticle"
    NEWSPAPER_ARTICLE = "newspaperArticle"
    VIDEO_RECORDING = "videoRecording"
    AUDIO_RECORDING = "audioRecording"
    PRESENTATION = "presentation"
    LETTER = "letter"
    MANUSCRIPT = "manuscript"
    MAP = "map"
    BILL = "bill"
    CASE = "case"
    STATUTE = "statute"
    PATENT = "patent"
    OTHER = "other"
    
    @classmethod
    def from_string(cls, value: str) -> 'ItemTypeEnum':
        """Convert string to ItemType, defaulting to DOCUMENT."""
        if not value:
            return cls.DOCUMENT
            
        # Try exact match first
        for item_type in cls:
            if item_type.value == value:
                return item_type
                
        # Try case-insensitive match
        value_lower = value.lower()
        for item_type in cls:
            if item_type.value.lower() == value_lower:
                return item_type
                
        # Handle special cases
        if value_lower in ["journal article", "journalarticle"]:
            return cls.JOURNAL_ARTICLE
            
        return cls.DOCUMENT


class AttachmentTypeEnum(str, Enum):
    """Enum for attachment types."""
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"
    HTML = "html"
    SNAPSHOT = "snapshot"
    
    @classmethod
    def from_string(cls, value: Optional[str]) -> Optional['AttachmentTypeEnum']:
        """Convert string to AttachmentType."""
        if not value:
            return None
            
        value_lower = value.lower()
        for attachment_type in cls:
            if attachment_type.value.lower() == value_lower:
                return attachment_type
        return None


class ZoteroItemModel(BaseModel):
    """Pydantic model for a Zotero item with validation."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    item_id: int = Field(gt=0, description="Unique item identifier")
    title: str = Field(min_length=1, description="Item title")
    item_type: str = Field(description="Type of the item")
    attachment_type: Optional[str] = Field(default=None, description="Type of attachment if any")
    attachment_path: Optional[str] = Field(default=None, description="Path to attachment file")
    is_duplicate: bool = Field(default=False, description="Whether this is a duplicate item")
    date_added: Optional[datetime] = Field(default=None, description="When item was added")
    date_modified: Optional[datetime] = Field(default=None, description="When item was last modified")
    
    # Additional metadata fields
    creators: List[str] = Field(default_factory=list, description="List of creator names")
    publication_year: Optional[int] = Field(default=None, ge=1000, le=9999, description="Year of publication")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier")
    isbn: Optional[str] = Field(default=None, description="ISBN")
    url: Optional[str] = Field(default=None, description="URL")
    abstract: Optional[str] = Field(default=None, description="Abstract or summary")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    collections: List[str] = Field(default_factory=list, description="Collections this item belongs to")
    notes_count: int = Field(default=0, ge=0, description="Number of attached notes")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @field_validator('date_added', 'date_modified', mode='before')
    @classmethod
    def parse_dates(cls, v):
        """Parse date strings to datetime objects."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                # Handle SQLite datetime format
                return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    # Try date only format
                    return datetime.strptime(v, "%Y-%m-%d")
                except ValueError:
                    return None
        return None
    
    def get_item_type_enum(self) -> ItemTypeEnum:
        """Get ItemType enum for this item."""
        return ItemTypeEnum.from_string(self.item_type)
    
    def get_attachment_type_enum(self) -> Optional[AttachmentTypeEnum]:
        """Get AttachmentType enum for this item."""
        return AttachmentTypeEnum.from_string(self.attachment_type)
    
    def has_attachment(self) -> bool:
        """Check if item has a readable attachment."""
        attachment_enum = self.get_attachment_type_enum()
        return attachment_enum in [AttachmentTypeEnum.PDF, AttachmentTypeEnum.EPUB]
    
    def has_notes(self) -> bool:
        """Check if item has attached notes."""
        return self.notes_count > 0
    
    def get_first_creator(self) -> Optional[str]:
        """Get the first creator name if available."""
        return self.creators[0] if self.creators else None
    
    def to_legacy_format(self) -> dict:
        """Convert to legacy format for backward compatibility."""
        return {
            'item_id': self.item_id,
            'title': self.title,
            'item_type': self.item_type,
            'attachment_type': self.attachment_type,
            'attachment_path': self.attachment_path,
            'is_duplicate': self.is_duplicate,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None
        }


class ZoteroCollectionModel(BaseModel):
    """Pydantic model for a Zotero collection with validation."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    collection_id: int = Field(gt=0, description="Unique collection identifier")
    name: str = Field(min_length=1, description="Collection name")
    parent_id: Optional[int] = Field(default=None, ge=1, description="Parent collection ID")
    depth: int = Field(default=0, ge=0, description="Depth in collection hierarchy")
    item_count: int = Field(default=0, ge=0, description="Number of items in collection")
    full_path: str = Field(default="", description="Full hierarchical path")
    library_id: int = Field(default=1, ge=1, description="Library identifier")
    library_type: str = Field(default="user", pattern="^(user|group)$", description="Type of library")
    library_name: str = Field(default="Personal Library", description="Name of the library")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Collection name cannot be empty")
        return v.strip()
    
    @field_validator('full_path', mode='before')
    @classmethod
    def build_full_path(cls, v, info):
        """Build full path if not provided."""
        if not v and 'name' in info.data:
            return info.data['name']
        return v
    
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
    
    def get_path_components(self) -> List[str]:
        """Get collection path as list of components."""
        return self.full_path.split(' > ') if self.full_path else [self.name]
    
    def to_legacy_format(self) -> dict:
        """Convert to legacy format for backward compatibility."""
        return {
            'collection_id': self.collection_id,
            'name': self.name,
            'parent_id': self.parent_id,
            'depth': self.depth,
            'item_count': self.item_count,
            'full_path': self.full_path,
            'library_id': self.library_id,
            'library_type': self.library_type,
            'library_name': self.library_name
        }


class ExportConfigModel(BaseModel):
    """Model for export configuration with validation."""
    
    format: str = Field(pattern="^(csv|json)$", description="Export format")
    file_path: Optional[str] = Field(default=None, description="Output file path")
    include_metadata: bool = Field(default=True, description="Include full metadata")
    include_abstract: bool = Field(default=False, description="Include abstracts")
    max_file_size: int = Field(default=100 * 1024 * 1024, gt=0, description="Max file size in bytes")
    
    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate export file path for security."""
        if v is None:
            return None
            
        from pathlib import Path
        path = Path(v)
        
        # Check for path traversal attempts
        try:
            path.resolve()
        except Exception:
            raise ValueError("Invalid file path")
            
        # Ensure proper extension
        if path.suffix.lower() not in ['.csv', '.json']:
            raise ValueError("Export file must have .csv or .json extension")
            
        return str(path)