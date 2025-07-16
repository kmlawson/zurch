import json
import os
import platform
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

def safe_encode_text(text: str, encoding: str = 'utf-8', errors: str = 'replace') -> str:
    """Safely encode text to handle Unicode errors.
    
    Args:
        text: The text to encode
        encoding: Target encoding (default: utf-8)
        errors: How to handle encoding errors (default: replace)
    
    Returns:
        Safely encoded text
    """
    if not isinstance(text, str):
        text = str(text)
    
    try:
        # Try to encode and decode to catch any Unicode issues
        text.encode(encoding)
        return text
    except UnicodeEncodeError as e:
        logger.warning(f"Unicode encoding error: {e}")
        # Replace problematic characters
        return text.encode(encoding, errors=errors).decode(encoding)

def safe_file_write(file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
    """Safely write content to file with UTF-8 encoding and error handling.
    
    Args:
        file_path: Path to write to
        content: Content to write
        encoding: File encoding (default: utf-8)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure content is safely encoded
        safe_content = safe_encode_text(content, encoding)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(safe_content)
        return True
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return False

def get_platform_capabilities() -> Dict[str, bool]:
    """Get platform capabilities for cross-platform compatibility."""
    capabilities = {
        'ansi_colors': False,
        'single_char_input': False,
        'file_permissions': False,
        'is_windows': os.name == 'nt',
        'is_unix': os.name == 'posix'
    }
    
    # Check ANSI color support
    from .constants import _ANSI_SUPPORTED
    capabilities['ansi_colors'] = _ANSI_SUPPORTED
    
    # Check single character input support
    from .keyboard import HAS_TERMIOS, HAS_MSVCRT
    capabilities['single_char_input'] = HAS_TERMIOS or HAS_MSVCRT
    
    # Check file permissions support (Unix-like systems)
    capabilities['file_permissions'] = os.name == 'posix'
    
    return capabilities

def get_config_dir() -> Path:
    """Get the appropriate config directory for the OS using standard paths."""
    if platform.system() == "Windows":
        # Use APPDATA on Windows
        config_dir = Path(os.environ.get("APPDATA", "")) / "zurch"
    else:  # macOS, Linux and others
        # Use XDG Base Directory specification
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            config_dir = Path(xdg_config_home) / "zurch"
        else:
            config_dir = Path.home() / ".config" / "zurch"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_legacy_config_dir() -> Path:
    """Get the old config directory location for migration."""
    if platform.system() == "Darwin":  # macOS
        return Path.home() / ".zurch-config"
    else:  # Linux and others
        return Path.home() / ".zurch-config"

def migrate_config_if_needed() -> None:
    """Migrate config from old location to new location if needed."""
    legacy_dir = get_legacy_config_dir()
    legacy_config = legacy_dir / "config.json"
    
    new_dir = get_config_dir()
    new_config = new_dir / "config.json"
    
    # Only migrate if legacy config exists and new config doesn't
    if legacy_config.exists() and not new_config.exists():
        try:
            import shutil
            # Copy the config file to new location
            shutil.copy2(legacy_config, new_config)
            logger.info(f"Migrated config from {legacy_config} to {new_config}")
            
            # Optionally remove the old config file after successful migration
            legacy_config.unlink()
            
            # Try to remove the old directory if it's empty
            try:
                legacy_dir.rmdir()
            except OSError:
                # Directory not empty, that's okay
                pass
                
        except Exception as e:
            logger.warning(f"Could not migrate config file: {e}")

def get_config_file() -> Path:
    """Get the config file path."""
    return get_config_dir() / "config.json"

def load_config() -> Dict[str, Any]:
    """Load configuration from file with validation."""
    from .config import validate_config_data
    
    # Try to migrate config from old location first
    migrate_config_if_needed()
    
    config_file = get_config_file()
    
    # For development, use the sample database
    sample_db = Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"
    
    from .constants import Defaults
    
    default_config = {
        "max_results": Defaults.MAX_RESULTS,
        "zotero_database_path": str(sample_db) if sample_db.exists() else None,
        "debug": Defaults.DEBUG,
        "partial_collection_match": True,
        "show_ids": Defaults.SHOW_IDS,
        "show_tags": Defaults.SHOW_TAGS,
        "show_year": Defaults.SHOW_YEAR,
        "show_author": Defaults.SHOW_AUTHOR,
        "show_created": Defaults.SHOW_CREATED,
        "show_modified": Defaults.SHOW_MODIFIED,
        "show_collections": Defaults.SHOW_COLLECTIONS,
        "only_attachments": Defaults.ONLY_ATTACHMENTS
    }
    
    if not config_file.exists():
        save_config(default_config)
        return default_config
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate configuration
        is_valid, error_msg = validate_config_data(config)
        if not is_valid:
            logger.error(f"Invalid configuration in {config_file}: {error_msg}")
            print(f"Warning: Configuration file is invalid: {error_msg}")
            print(f"Using default configuration. Run 'zurch --config' to fix.")
            return default_config
        
        # Merge with defaults to ensure all keys exist
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        return config
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading config: {e}")
        return default_config

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file with validation."""
    from .config import validate_config_data
    
    # Validate configuration before saving
    is_valid, error_msg = validate_config_data(config)
    if not is_valid:
        logger.error(f"Cannot save invalid configuration: {error_msg}")
        raise ValueError(f"Invalid configuration: {error_msg}")
    
    config_file = get_config_file()
    
    # Ensure directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Use atomic write for safety
    import tempfile
    import os
    
    temp_fd, temp_path = tempfile.mkstemp(
        dir=config_file.parent,
        prefix='.tmp_config_',
        suffix='.json'
    )
    
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        os.rename(temp_path, config_file)
        
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        logger.error(f"Error saving config: {e}")
        raise

def format_attachment_icon(attachment_type: Optional[str]) -> str:
    """Return colored icon based on attachment type (DEPRECATED - use format_attachment_document_icon)."""
    if not attachment_type:
        return ""
    
    from .constants import AttachmentTypes, Colors, Icons
    
    attachment_type = attachment_type.lower()
    if attachment_type == AttachmentTypes.PDF:
        return f"{Colors.BLUE}{Icons.BOOK_BLUE}{Colors.RESET}"  # Blue book for PDF
    elif attachment_type == AttachmentTypes.EPUB:
        return f"{Colors.GREEN}{Icons.BOOK_GREEN}{Colors.RESET}"  # Green book for EPUB
    elif attachment_type in AttachmentTypes.TEXT_EXTENSIONS:
        return f"{Colors.GRAY}{Icons.DOCUMENT}{Colors.RESET}"  # Grey document for TXT
    else:
        return ""

def format_item_type_icon(item_type: str, is_duplicate: bool = False) -> str:
    """Return icon that goes before the title based on item type."""
    from .constants import ItemTypes, Icons, Colors
    
    item_type_lower = item_type.lower()
    if item_type_lower == ItemTypes.BOOK.lower():
        icon = f"{Icons.BOOK_GREEN} "  # Green book icon for books
    elif item_type_lower in [ItemTypes.JOURNAL_ARTICLE.lower(), ItemTypes.JOURNAL_ARTICLE_ALT.lower()]:
        icon = f"{Icons.DOCUMENT} "  # Document icon for journal articles
    elif item_type_lower == ItemTypes.WEBPAGE.lower():
        icon = f"{Icons.WEBPAGE} "  # Globe icon for web pages
    else:
        icon = ""  # No icon for other types
    
    # Apply purple color to duplicates
    if is_duplicate and icon:
        return f"{Colors.MAGENTA}{icon}{Colors.RESET}"
    
    return icon

def format_attachment_link_icon(attachment_type: Optional[str]) -> str:
    """Return link icon when PDF/EPUB attachments are available."""
    if not attachment_type:
        return ""
    
    attachment_type = attachment_type.lower()
    if attachment_type in ["pdf", "epub"]:
        return "🔗 "  # Link icon for PDF/EPUB attachments (space after)
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

def escape_sql_like_pattern(pattern: str) -> str:
    """Escape special characters in SQL LIKE patterns.
    
    Escapes % and _ characters that have special meaning in SQL LIKE.
    Also escapes the escape character itself (backslash).
    """
    # Escape backslash first, then % and _
    pattern = pattern.replace('\\', '\\\\')
    pattern = pattern.replace('%', '\\%')
    pattern = pattern.replace('_', '\\_')
    return pattern

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

def format_duplicate_title(title: str, is_duplicate: bool = False) -> str:
    """Format title with purple color if it's a duplicate."""
    if is_duplicate:
        PURPLE = '\033[35m'
        RESET = '\033[0m'
        return f"{PURPLE}{title}{RESET}"
    return title

def format_metadata_field(field_name: str, value: str) -> str:
    """Format a metadata field with bold label."""
    BOLD = '\033[1m'
    RESET = '\033[0m'
    return f"{BOLD}{field_name}:{RESET} {value}"

def sort_items(items, sort_by: str, db=None):
    """Sort items by specified criteria."""
    from typing import List
    from .models import ZoteroItem
    
    if not sort_by or not items:
        return items
    
    # Normalize sort criteria
    sort_key = sort_by.lower()
    if sort_key in ['t', 'title']:
        return sorted(items, key=lambda item: item.title.lower())
    elif sort_key in ['c', 'created']:
        return sorted(items, key=lambda item: item.date_added or '', reverse=True)
    elif sort_key in ['m', 'modified']:
        return sorted(items, key=lambda item: item.date_modified or '', reverse=True)
    elif sort_key in ['d', 'date']:
        # For date sorting, we need to get publication year from metadata
        # For now, fall back to title sorting if no database connection
        if not db:
            return sorted(items, key=lambda item: item.title.lower())
        
        # Get publication years for all items
        item_years = {}
        for item in items:
            try:
                metadata = db.metadata.get_item_metadata(item.item_id)
                year = metadata.get('date', '')
                # Extract year from date string (format might be "2023", "2023-01-01", etc.)
                if year:
                    year_str = str(year)[:4]
                    try:
                        item_years[item.item_id] = int(year_str)
                    except ValueError:
                        item_years[item.item_id] = 0
                else:
                    item_years[item.item_id] = 0
            except Exception:
                item_years[item.item_id] = 0
        
        return sorted(items, key=lambda item: item_years.get(item.item_id, 0), reverse=True)
    elif sort_key in ['a', 'author']:
        # For author sorting, we need to get author info from metadata
        if not db:
            return sorted(items, key=lambda item: item.title.lower())
        
        # Get authors for all items
        item_authors = {}
        for item in items:
            try:
                metadata = db.metadata.get_item_metadata(item.item_id)
                creators = metadata.get('creators', [])
                if creators and len(creators) > 0:
                    # Use last name of first author for sorting
                    first_author = creators[0]
                    last_name = first_author.get('lastName', '')
                    if last_name:
                        item_authors[item.item_id] = last_name.lower()
                    else:
                        # Use special value that sorts last (items without authors at bottom)
                        item_authors[item.item_id] = '~~~no_author'
                else:
                    # Use special value that sorts last (items without authors at bottom)
                    item_authors[item.item_id] = '~~~no_author'
            except Exception:
                # Use special value that sorts last (items without authors at bottom)
                item_authors[item.item_id] = '~~~no_author'
        
        return sorted(items, key=lambda item: item_authors.get(item.item_id, '~~~no_author'))
    else:
        # Default to title sorting
        return sorted(items, key=lambda item: item.title.lower())