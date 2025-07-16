"""Constants module for zurch - centralizes magic strings and numbers."""

import os
import sys

def _supports_ansi_colors() -> bool:
    """Check if the terminal supports ANSI color codes."""
    # If we're not in a TTY, don't use colors
    if not sys.stdout.isatty():
        return False
    
    # Check for Windows
    if os.name == 'nt':
        # Windows Terminal, PowerShell, and newer cmd.exe support ANSI
        term = os.environ.get('TERM', '').lower()
        wt_session = os.environ.get('WT_SESSION')
        
        # Windows Terminal has WT_SESSION
        if wt_session:
            return True
        
        # Check if we're in a modern terminal
        if term in ['xterm', 'xterm-256color', 'screen', 'tmux']:
            return True
        
        # Check Windows version - Windows 10 1511+ supports ANSI in cmd.exe
        try:
            import platform
            version = platform.version()
            # Parse version string like "10.0.19041"
            parts = version.split('.')
            if len(parts) >= 3:
                major = int(parts[0])
                minor = int(parts[1])
                build = int(parts[2])
                # Windows 10 build 10586 (1511) and later support ANSI
                if major >= 10 and build >= 10586:
                    return True
        except (ValueError, IndexError):
            pass
        
        # Also check for COLORTERM environment variable
        if os.environ.get('COLORTERM'):
            return True
        
        # For older Windows systems, disable ANSI colors
        return False
    
    # Unix-like systems generally support ANSI colors
    return True

# Check if ANSI colors are supported
_ANSI_SUPPORTED = _supports_ansi_colors()

# ANSI Color Codes
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m' if _ANSI_SUPPORTED else ''
    BOLD = '\033[1m' if _ANSI_SUPPORTED else ''
    
    # Foreground colors
    BLACK = '\033[30m' if _ANSI_SUPPORTED else ''
    RED = '\033[31m' if _ANSI_SUPPORTED else ''
    GREEN = '\033[32m' if _ANSI_SUPPORTED else ''
    YELLOW = '\033[33m' if _ANSI_SUPPORTED else ''
    BLUE = '\033[34m' if _ANSI_SUPPORTED else ''
    MAGENTA = '\033[35m' if _ANSI_SUPPORTED else ''
    CYAN = '\033[36m' if _ANSI_SUPPORTED else ''
    WHITE = '\033[37m' if _ANSI_SUPPORTED else ''
    
    # Background colors
    BG_BLACK = '\033[40m' if _ANSI_SUPPORTED else ''
    BG_RED = '\033[41m' if _ANSI_SUPPORTED else ''
    BG_GREEN = '\033[42m' if _ANSI_SUPPORTED else ''
    BG_YELLOW = '\033[43m' if _ANSI_SUPPORTED else ''
    BG_BLUE = '\033[44m' if _ANSI_SUPPORTED else ''
    BG_MAGENTA = '\033[45m' if _ANSI_SUPPORTED else ''
    BG_CYAN = '\033[46m' if _ANSI_SUPPORTED else ''
    BG_WHITE = '\033[47m' if _ANSI_SUPPORTED else ''
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m' if _ANSI_SUPPORTED else ''
    BRIGHT_RED = '\033[91m' if _ANSI_SUPPORTED else ''
    BRIGHT_GREEN = '\033[92m' if _ANSI_SUPPORTED else ''
    BRIGHT_YELLOW = '\033[93m' if _ANSI_SUPPORTED else ''
    BRIGHT_BLUE = '\033[94m' if _ANSI_SUPPORTED else ''
    BRIGHT_MAGENTA = '\033[95m' if _ANSI_SUPPORTED else ''
    BRIGHT_CYAN = '\033[96m' if _ANSI_SUPPORTED else ''
    BRIGHT_WHITE = '\033[97m' if _ANSI_SUPPORTED else ''
    
    # Common aliases
    GRAY = BRIGHT_BLACK
    GREY = BRIGHT_BLACK

# Item Type Constants
class ItemTypes:
    """Zotero item type constants."""
    BOOK = "book"
    JOURNAL_ARTICLE = "journalArticle"
    JOURNAL_ARTICLE_ALT = "journal article"  # Alternative naming
    WEBPAGE = "webpage"
    THESIS = "thesis"
    CONFERENCE_PAPER = "conferencePaper"
    BOOK_SECTION = "bookSection"
    MANUSCRIPT = "manuscript"
    REPORT = "report"
    DOCUMENT = "document"
    PRESENTATION = "presentation"
    INTERVIEW = "interview"
    FILM = "videoRecording"
    ARTWORK = "artwork"
    ATTACHMENT = "attachment"
    NOTE = "note"

# Attachment Type Constants
class AttachmentTypes:
    """Zotero attachment type constants."""
    PDF = "pdf"
    EPUB = "epub"
    HTML = "html"
    TXT = "txt"
    TEXT = "text"
    DOC = "doc"
    DOCX = "docx"
    ODT = "odt"
    RTF = "rtf"
    
    # File extensions that are considered text attachments
    TEXT_EXTENSIONS = {TXT, TEXT, "md", "markdown", "rst"}
    
    # File extensions that are considered document attachments
    DOCUMENT_EXTENSIONS = {PDF, EPUB, HTML, DOC, DOCX, ODT, RTF}

# Database Field IDs (from Zotero schema)
class FieldIDs:
    """Zotero database field ID constants."""
    TITLE = 1
    FIRST_NAME = 2
    LAST_NAME = 3
    ACCESS_DATE = 14
    PUBLICATION_DATE = 6
    ITEM_TYPE = 'itemTypeID'
    DATE_ADDED = 'dateAdded'
    DATE_MODIFIED = 'dateModified'

# Creator Type Constants
class CreatorTypes:
    """Zotero creator type constants."""
    AUTHOR = "author"
    EDITOR = "editor"
    CONTRIBUTOR = "contributor"
    TRANSLATOR = "translator"
    REVIEWER = "reviewer"
    ARTIST = "artist"
    DIRECTOR = "director"
    PRODUCER = "producer"
    INTERVIEWEE = "interviewee"
    INTERVIEWER = "interviewer"

# Default Configuration Values
class Defaults:
    """Default configuration values."""
    MAX_RESULTS = 100
    MAX_EXPORT_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_FILENAME_LENGTH = 100
    CONFIG_FILE_NAME = "config.json"
    SAMPLE_DB_NAME = "zotero.sqlite"
    SAMPLE_DB_DIR = "zotero-database-example"
    
    # Display defaults
    SHOW_IDS = False
    SHOW_TAGS = False
    SHOW_YEAR = False
    SHOW_AUTHOR = False
    SHOW_CREATED = False
    SHOW_MODIFIED = False
    SHOW_COLLECTIONS = False
    ONLY_ATTACHMENTS = False
    DEBUG = False

# Icon Constants
class Icons:
    """Unicode icons used in display."""
    BOOK_GREEN = "📗"
    BOOK_BLUE = "📘"
    BOOK_RED = "📕"
    BOOK_ORANGE = "📙"
    DOCUMENT = "📄"
    WEBPAGE = "🌐"
    LINK = "🔗"
    FOLDER = "📁"
    TAG = "🏷️"
    SEARCH = "🔍"
    STATS = "📊"
    DATABASE = "🗃️"
    ATTACHMENT = "📎"
    
    # Spinner characters for loading
    SPINNER_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

# SQL Query Limits
class QueryLimits:
    """SQL query limitation constants."""
    SQLITE_MAX_PARAMS = 999  # SQLite parameter limit
    BATCH_SIZE = 999
    MAX_LIKE_PATTERN_LENGTH = 1000
    MAX_QUERY_LENGTH = 100000

# File System Constants
class FileSystem:
    """File system related constants."""
    TEMP_FILE_PREFIX = '.tmp_'
    BACKUP_FILE_SUFFIX = '.bak'
    CONFIG_DIR_NAME = 'zurch'
    
    # File permissions
    FILE_PERMISSIONS = 0o600  # Owner read/write only
    DIR_PERMISSIONS = 0o700   # Owner read/write/execute only
    
    # Dangerous directories (for reference, though we use whitelist now)
    DANGEROUS_DIRS = [
        "/System", "/Library", "/bin", "/sbin", "/usr/bin", "/usr/sbin",
        "/Applications", "/private", "/etc", "/var/log", "/var/db",
        "/var/root", "/root", "C:\\Windows", "C:\\System32",
        "C:\\Program Files", "C:\\Program Files (x86)"
    ]

# Validation Constants
class Validation:
    """Validation related constants."""
    MIN_MAX_RESULTS = 1
    MAX_MAX_RESULTS = 10000
    MIN_FILENAME_LENGTH = 1
    MAX_FILENAME_LENGTH = 255
    SQLITE_HEADER = b'SQLite format 3\x00'
    
    # Regex patterns
    FILENAME_INVALID_CHARS = r'[<>:"/\\|?*]'
    CONTROL_CHARS = r'[\x00-\x1f\x7f-\x9f]'
    
# Network/Protocol Constants
class Network:
    """Network and protocol constants."""
    HTTP_TIMEOUT = 30
    MAX_REDIRECTS = 5
    USER_AGENT = "zurch/0.7.8 (Zotero CLI Tool)"

# Error Messages
class ErrorMessages:
    """Common error message templates."""
    CONFIG_INVALID = "Invalid configuration: {}"
    DATABASE_NOT_FOUND = "Database path does not exist: {}"
    DATABASE_NOT_READABLE = "Database path is not readable: {}"
    DATABASE_NOT_SQLITE = "Database path does not appear to be a SQLite database: {}"
    FILE_TOO_LARGE = "Export file would be too large ({:.1f}MB), maximum is {:.1f}MB"
    UNSAFE_PATH = "Cannot export to {} - path is not in a safe directory"
    EXPORT_FAILED = "Failed to export items to {}"
    EXPORT_CANCELLED = "Export cancelled"
    DIRECTORY_CREATE_FAILED = "Error creating directory: {}"
    
# Success Messages
class SuccessMessages:
    """Common success message templates."""
    EXPORT_SUCCESS = "Successfully exported {} items to {}"
    CONFIG_SAVED = "Configuration saved to {}"
    DIRECTORY_CREATED = "Created directory: {}"
    ATTACHMENT_COPIED = "Copied attachment to: {}"