"""Configuration management for zurch."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json
import logging
import os

try:
    from jsonschema import validate, ValidationError
except ImportError:
    validate = None
    ValidationError = None

logger = logging.getLogger(__name__)

# Configuration validation schema
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "zotero_database_path": {
            "type": ["string", "null"],
            "minLength": 1
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10000
        },
        "debug": {
            "type": "boolean"
        },
        "show_ids": {
            "type": "boolean"
        },
        "show_tags": {
            "type": "boolean"
        },
        "show_year": {
            "type": "boolean"
        },
        "show_author": {
            "type": "boolean"
        },
        "show_created": {
            "type": "boolean"
        },
        "show_modified": {
            "type": "boolean"
        },
        "show_collections": {
            "type": "boolean"
        },
        "only_attachments": {
            "type": "boolean"
        },
        "partial_collection_match": {
            "type": "boolean"
        },
        "interactive_mode": {
            "type": "boolean"
        }
    },
    "required": [],
    "additionalProperties": False
}

def validate_config_data(data: dict) -> tuple[bool, str]:
    """Validate configuration data against schema.
    
    Returns: (is_valid, error_message)
    """
    if validate is None:
        logger.warning("jsonschema not available, skipping config validation")
        return True, ""
    
    try:
        validate(instance=data, schema=CONFIG_SCHEMA)
        
        # Additional validation for database path
        if data.get('zotero_database_path'):
            db_path = Path(data['zotero_database_path'])
            
            # Check if path exists
            if not db_path.exists():
                return False, f"Database path does not exist: {db_path}"
            
            # Check if it's a file
            if not db_path.is_file():
                return False, f"Database path is not a file: {db_path}"
            
            # Check if it's readable
            if not os.access(db_path, os.R_OK):
                return False, f"Database path is not readable: {db_path}"
            
            # Check if it looks like a SQLite database
            try:
                with open(db_path, 'rb') as f:
                    header = f.read(16)
                    if not header.startswith(b'SQLite format 3\x00'):
                        return False, f"Database path does not appear to be a SQLite database: {db_path}"
            except Exception as e:
                return False, f"Cannot read database file: {e}"
        
        return True, ""
        
    except ValidationError as e:
        return False, f"Invalid configuration: {e.message}"
    except Exception as e:
        return False, f"Configuration validation error: {e}"


@dataclass
class ZurchConfig:
    """Configuration settings for zurch application."""
    
    zotero_database_path: Optional[str] = None
    max_results: int = 100
    debug: bool = False
    zotero_data_dir: Optional[Path] = None
    
    @classmethod
    def load_from_file(cls, config_file: Path) -> 'ZurchConfig':
        """Load configuration from file."""
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return cls(**data)
        except (json.JSONDecodeError, IOError):
            pass
        
        # Return defaults if load failed
        return cls()
    
    def save_to_file(self, config_file: Path) -> None:
        """Atomically save configuration to file with validation."""
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get data and validate before saving
        data = self.to_dict()
        is_valid, error_msg = validate_config_data(data)
        if not is_valid:
            logger.error(f"Cannot save invalid configuration: {error_msg}")
            raise ValueError(f"Invalid configuration: {error_msg}")
        
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
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'zotero_database_path': self.zotero_database_path,
            'max_results': self.max_results,
            'debug': self.debug,
            'zotero_data_dir': str(self.zotero_data_dir) if self.zotero_data_dir else None
        }
    
    def get_zotero_data_dir(self) -> Optional[Path]:
        """Get Zotero data directory from database path."""
        if self.zotero_data_dir:
            return self.zotero_data_dir
        elif self.zotero_database_path:
            return Path(self.zotero_database_path).parent
        return None