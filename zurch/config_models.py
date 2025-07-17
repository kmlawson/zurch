"""Pydantic models for configuration and data validation."""

import os
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
import logging

logger = logging.getLogger(__name__)


class ZurchConfigModel(BaseModel):
    """Configuration settings for zurch application using Pydantic validation."""
    
    model_config = ConfigDict(extra='forbid')  # Reject unknown fields
    
    # Database configuration
    zotero_database_path: Optional[Path] = Field(
        default=None,
        description="Path to Zotero SQLite database file"
    )
    
    # Display configuration
    max_results: int = Field(
        default=100,
        ge=1,
        description="Maximum number of results to display"
    )
    
    # Feature flags
    debug: bool = Field(default=False, description="Enable debug logging")
    show_ids: bool = Field(default=False, description="Show item IDs in results")
    show_tags: bool = Field(default=False, description="Show tags in results")
    show_year: bool = Field(default=False, description="Show publication year in results")
    show_author: bool = Field(default=False, description="Show author in results")
    show_created: bool = Field(default=False, description="Show creation date in results")
    show_modified: bool = Field(default=False, description="Show modification date in results")
    show_collections: bool = Field(default=False, description="Show collections in results")
    show_notes: bool = Field(default=False, description="Show notes indicator in results")
    
    # Behavior configuration
    only_attachments: bool = Field(default=False, description="Show only items with attachments")
    partial_collection_match: bool = Field(default=True, description="Enable partial collection name matching")
    interactive_mode: bool = Field(default=True, description="Enable interactive mode by default")
    
    # Computed field (not saved to config)
    zotero_data_dir: Optional[Path] = Field(default=None, exclude=True)
    
    @field_validator('zotero_database_path')
    @classmethod
    def validate_database_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate that the database path exists and is a SQLite file."""
        if v is None:
            return None
            
        # Convert string to Path if needed
        if isinstance(v, str):
            v = Path(v)
            
        # Check if path exists
        if not v.exists():
            raise ValueError(f"Database path does not exist: {v}")
        
        # Check if it's a file
        if not v.is_file():
            raise ValueError(f"Database path is not a file: {v}")
        
        # Check if it's readable
        if not os.access(v, os.R_OK):
            raise ValueError(f"Database path is not readable: {v}")
        
        # Check if it looks like a SQLite database
        try:
            with open(v, 'rb') as f:
                header = f.read(16)
                if not header.startswith(b'SQLite format 3\x00'):
                    raise ValueError(f"Database path does not appear to be a SQLite database: {v}")
        except Exception as e:
            raise ValueError(f"Cannot read database file: {e}")
        
        return v
    
    @field_validator('max_results', mode='before')
    @classmethod
    def validate_max_results(cls, v: Union[int, str]) -> int:
        """Handle special values like 'all' or '0' for unlimited results."""
        if isinstance(v, str):
            v = v.strip().lower()
            if v in ['all', '0']:
                return 999999999  # Large number for unlimited
            try:
                return int(v)
            except ValueError:
                raise ValueError(f"Invalid max_results value: {v}")
        return v
    
    def get_zotero_data_dir(self) -> Optional[Path]:
        """Get Zotero data directory from database path."""
        if self.zotero_data_dir:
            return self.zotero_data_dir
        elif self.zotero_database_path:
            return self.zotero_database_path.parent
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = self.model_dump(exclude={'zotero_data_dir'}, exclude_none=True)
        # Convert Path objects to strings for JSON serialization
        if 'zotero_database_path' in data and data['zotero_database_path']:
            data['zotero_database_path'] = str(data['zotero_database_path'])
        return data
    
    @classmethod
    def load_from_file(cls, config_file: Path) -> 'ZurchConfigModel':
        """Load configuration from file with validation."""
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    import json
                    data = json.load(f)
                return cls(**data)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_file}: {e}")
        
        # Return defaults if load failed
        return cls()
    
    def save_to_file(self, config_file: Path) -> None:
        """Atomically save configuration to file."""
        import json
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get data for saving
        data = self.to_dict()
        
        # Atomic write: write to temp file then rename
        temp_file = config_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(config_file)
        except Exception:
            if temp_file.exists():
                temp_file.unlink()
            raise


class CLIArgumentsModel(BaseModel):
    """Model for validating CLI arguments."""
    
    model_config = ConfigDict(extra='ignore')  # Allow extra fields from argparse
    
    # Search parameters
    folder: Optional[str] = Field(default=None, description="Folder name to search")
    name: Optional[Union[str, list[str]]] = Field(default=None, description="Item name to search")
    author: Optional[Union[str, list[str]]] = Field(default=None, description="Author name to search")
    tag: Optional[list[str]] = Field(default=None, description="Tags to filter by")
    
    # Display options
    interactive: Optional[bool] = Field(default=None, description="Enable interactive mode")
    nointeract: bool = Field(default=False, description="Disable interactive mode")
    grab: bool = Field(default=False, description="Enable attachment grabbing")
    only_attachments: bool = Field(default=False, description="Show only items with attachments")
    exact: bool = Field(default=False, description="Use exact matching")
    max_results: Optional[Union[int, str]] = Field(default=None, description="Maximum results to show")
    
    # Filtering options
    after: Optional[int] = Field(default=None, ge=1000, le=9999, description="Show items after year")
    before: Optional[int] = Field(default=None, ge=1000, le=9999, description="Show items before year")
    books: bool = Field(default=False, description="Show only books")
    articles: bool = Field(default=False, description="Show only articles")
    
    # Output options
    showids: bool = Field(default=False, description="Show item IDs")
    showtags: bool = Field(default=False, description="Show tags")
    showyear: bool = Field(default=False, description="Show publication year")
    showauthor: bool = Field(default=False, description="Show author")
    showcreated: bool = Field(default=False, description="Show creation date")
    showmodified: bool = Field(default=False, description="Show modification date")
    showcollections: bool = Field(default=False, description="Show collections")
    shownotes: bool = Field(default=False, description="Show notes indicator")
    
    # Sorting and export
    sort: Optional[str] = Field(default=None, pattern='^(t|title|d|date|a|author|c|created|m|modified)$')
    export: Optional[str] = Field(default=None, pattern='^(csv|json)$')
    file: Optional[Path] = Field(default=None, description="Export file path")
    
    # Other options
    paginate: bool = Field(default=False, description="Enable pagination")
    no_dedupe: bool = Field(default=False, description="Disable deduplication")
    debug: bool = Field(default=False, description="Enable debug logging")
    
    @field_validator('after', 'before', mode='before')
    @classmethod
    def validate_year_range(cls, v: Optional[int], info) -> Optional[int]:
        """Ensure after/before years are reasonable."""
        if v is not None and info.field_name == 'after':
            # Check that 'after' year isn't in the future
            from datetime import datetime
            current_year = datetime.now().year
            if v > current_year:
                raise ValueError(f"'after' year cannot be in the future (current year: {current_year})")
        return v
    
    @field_validator('file', mode='before')
    @classmethod
    def validate_export_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Convert string to Path and validate export location."""
        if v is None:
            return None
            
        if isinstance(v, str):
            v = Path(v)
            
        # Check if parent directory exists
        if not v.parent.exists():
            raise ValueError(f"Parent directory does not exist: {v.parent}")
            
        # Check if file already exists
        if v.exists():
            raise ValueError(f"Export file already exists: {v}")
            
        return v
    
    def get_max_results(self, config_default: int = 100) -> int:
        """Parse max_results value, handling special cases."""
        if self.max_results is None:
            return config_default
            
        if isinstance(self.max_results, str):
            value = self.max_results.strip().lower()
            if value in ['all', '0']:
                return 999999999
            try:
                return int(value)
            except ValueError:
                return config_default
                
        return self.max_results