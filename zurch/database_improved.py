"""Improved database connection with connection pooling."""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Any, List, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    pass


class DatabaseLockedError(DatabaseError):
    pass


class DatabaseConnection:
    """Handles database connection with persistent connection for performance."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._verify_database()
        self._init_connection()
    
    def _verify_database(self) -> None:
        """Verify database exists and is accessible."""
        if not self.db_path.exists():
            raise DatabaseError(f"Database not found: {self.db_path}")
        
        try:
            # Quick verification with temporary connection
            with self._create_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
                if not cursor.fetchone():
                    raise DatabaseError("Invalid Zotero database: missing items table")
        except (sqlite3.OperationalError, sqlite3.DatabaseError, Exception) as e:
            if "database is locked" in str(e).lower():
                raise DatabaseLockedError("Zotero database is locked. Close Zotero and try again.")
            raise DatabaseError(f"Cannot access database: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new read-only database connection."""
        conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def _init_connection(self) -> None:
        """Initialize persistent connection."""
        try:
            self._connection = self._create_connection()
            logger.debug(f"Initialized database connection to {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """Get cursor with automatic transaction handling."""
        if not self._connection:
            self._init_connection()
        
        try:
            cursor = self._connection.cursor()
            yield cursor
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                raise DatabaseLockedError("Zotero database is locked. Close Zotero and try again.")
            raise DatabaseError(f"Database operation failed: {e}")
        except Exception as e:
            raise DatabaseError(f"Error executing query: {e}")
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute query and return all results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_single_query(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute query and return single result."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def get_database_version(self) -> str:
        """Get Zotero database version."""
        try:
            result = self.execute_single_query("SELECT version FROM version WHERE schema = 'system'")
            return str(result[0]) if result else "unknown"
        except Exception as e:
            logger.warning(f"Cannot read database version: {e}")
            return "unknown"
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Closed database connection")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_attachment_type(content_type: Optional[str]) -> Optional[str]:
    """Determine attachment type from content type."""
    if not content_type:
        return None
    
    content_type = content_type.lower()
    if content_type == "application/pdf":
        return "pdf"
    elif content_type == "application/epub+zip":
        return "epub"
    elif content_type.startswith("text/"):
        return "txt"
    else:
        return None