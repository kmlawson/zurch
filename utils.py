import json
import os
import platform
from pathlib import Path
from typing import Optional, Dict, Any

def get_config_dir() -> Path:
    """Get the appropriate config directory for the OS."""
    if platform.system() == "Windows":
        config_dir = Path(os.environ.get("APPDATA", "")) / "clizot"
    elif platform.system() == "Darwin":  # macOS
        config_dir = Path.home() / ".clizot-config"
    else:  # Linux and others
        config_dir = Path.home() / ".clizot-config"
    
    config_dir.mkdir(exist_ok=True)
    return config_dir

def get_config_file() -> Path:
    """Get the config file path."""
    return get_config_dir() / "config.json"

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    config_file = get_config_file()
    
    # For development, use the sample database
    sample_db = Path(__file__).parent / "zotero-database-example" / "zotero.sqlite"
    
    default_config = {
        "max_results": 100,
        "zotero_database_path": str(sample_db) if sample_db.exists() else None,
        "debug": False,
        "partial_collection_match": True
    }
    
    if not config_file.exists():
        save_config(default_config)
        return default_config
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        # Merge with defaults to ensure all keys exist
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        return config
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading config: {e}")
        return default_config

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    config_file = get_config_file()
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        print(f"Error saving config: {e}")

def format_attachment_icon(attachment_type: Optional[str]) -> str:
    """Return colored icon based on attachment type."""
    if not attachment_type:
        return ""
    
    attachment_type = attachment_type.lower()
    if attachment_type == "pdf":
        return "\033[34m📘\033[0m"  # Blue book for PDF
    elif attachment_type == "epub":
        return "\033[32m📗\033[0m"  # Green book for EPUB
    elif attachment_type in ["txt", "text"]:
        return "\033[90m📄\033[0m"  # Grey document for TXT
    else:
        return ""

def find_zotero_database() -> Optional[Path]:
    """Attempt to find the Zotero database automatically."""
    possible_paths = []
    
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            possible_paths.extend([
                Path(appdata) / "Zotero" / "Zotero" / "zotero.sqlite",
                Path(appdata) / "Zotero" / "zotero.sqlite"
            ])
    elif platform.system() == "Darwin":  # macOS
        home = Path.home()
        possible_paths.extend([
            home / "Zotero" / "zotero.sqlite",
            home / "Library" / "Application Support" / "Zotero" / "zotero.sqlite"
        ])
    else:  # Linux
        home = Path.home()
        possible_paths.extend([
            home / "Zotero" / "zotero.sqlite",
            home / ".zotero" / "zotero.sqlite",
            home / "snap" / "zotero-snap" / "common" / "Zotero" / "zotero.sqlite"
        ])
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def pad_number(num: int, total: int) -> str:
    """Pad a number with spaces for alignment."""
    max_width = len(str(total))
    return f"{num:>{max_width}}"

def highlight_search_term(text: str, search_term: str) -> str:
    """Highlight search term in text with bold formatting."""
    if not search_term or not text:
        return text
    
    # ANSI escape codes for bold
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    # Handle % wildcards by converting to simple contains matching
    clean_term = search_term.replace('%', '')
    if not clean_term:
        return text
    
    # Case-insensitive highlighting
    import re
    # Escape special regex characters except our search term
    escaped_term = re.escape(clean_term)
    # Use case-insensitive replacement
    highlighted = re.sub(f'({escaped_term})', f'{BOLD}\\1{RESET}', text, flags=re.IGNORECASE)
    
    return highlighted