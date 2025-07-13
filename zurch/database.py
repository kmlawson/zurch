import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    pass

class DatabaseLockedError(DatabaseError):
    pass

class DatabaseConnection:
    """Handles database connection and basic operations."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._verify_database()
    
    def _verify_database(self) -> None:
        """Verify database exists and is accessible."""
        if not self.db_path.exists():
            raise DatabaseError(f"Database not found: {self.db_path}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
                if not cursor.fetchone():
                    raise DatabaseError("Invalid Zotero database: missing items table")
        except (sqlite3.OperationalError, sqlite3.DatabaseError, Exception) as e:
            if "database is locked" in str(e).lower():
                raise DatabaseLockedError("Zotero database is locked. Close Zotero and try again.")
            raise DatabaseError(f"Cannot access database: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get read-only database connection."""
        return sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
    
    def get_database_version(self) -> str:
        """Get Zotero database version."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM version WHERE schema = 'system'")
                result = cursor.fetchone()
                return str(result[0]) if result else "unknown"
        except Exception as e:
            logger.warning(f"Cannot read database version: {e}")
            return "unknown"
    
    def execute_query(self, query: str, params: tuple = ()): # type: ignore
        """Execute a query and return results."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            raise DatabaseError(f"Error executing query: {e}")
    
    def execute_single_query(self, query: str, params: tuple = ()): # type: ignore
        """Execute a query and return a single result."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            raise DatabaseError(f"Error executing single query: {e}")

def get_attachment_type(content_type: str) -> Optional[str]:
    """Convert MIME type to attachment type for icon display."""
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