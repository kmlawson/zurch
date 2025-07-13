"""Configuration management for zurch."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json


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
                with open(config_file, 'r') as f:
                    data = json.load(f)
                return cls(**data)
        except (json.JSONDecodeError, IOError):
            pass
        
        # Return defaults if load failed
        return cls()
    
    def save_to_file(self, config_file: Path) -> None:
        """Atomically save configuration to file."""
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write: write to temp file then rename
        temp_file = config_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
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