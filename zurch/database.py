"""
Handles the connection to the Zotero SQLite database, providing a performant
and robust interface for executing queries.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Any, List, Tuple, Iterable
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for general database errors."""
    pass


class DatabaseLockedError(DatabaseError):
    """Custom exception for when the Zotero database is locked."""
    pass


class DatabaseConnection:
    """
    Manages a persistent, read-only connection to the Zotero SQLite database.

    This class is designed for performance by holding a single connection open
    for the lifetime of the object. It also uses sqlite3.Row as a row factory,
    allowing for dictionary-like access to columns.

    It can be used as a context manager to ensure the connection is closed:
    
    with DatabaseConnection(db_path) as db:
        db.execute_query(...)
    """
    
    def __init__(self, db_path: Path):
        """
        Initializes the database connection.

        Args:
            db_path: The absolute path to the zotero.sqlite file.
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._verify_database_exists()
        self._init_connection()
    
    def _verify_database_exists(self) -> None:
        """Verify that the database file exists on the filesystem."""
        if not self.db_path.exists():
            raise DatabaseError(f"Database not found at path: {self.db_path}")
        if not self.db_path.is_file():
            raise DatabaseError(f"Path is not a file: {self.db_path}")

    def _create_connection(self) -> sqlite3.Connection:
        """
        Creates a new read-only database connection with a Row factory.
        
        Returns:
            A new sqlite3.Connection object.
        """
        try:
            # Connect in read-only mode (uri=True is required for mode)
            conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
            # Use the Row factory for dict-like access to results
            conn.row_factory = sqlite3.Row
            # Ensure UTF-8 encoding for text operations
            conn.text_factory = str
            return conn
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                raise DatabaseError(f"Failed to open database file: {self.db_path}")
            raise

    def _init_connection(self) -> None:
        """Initializes the persistent connection and verifies its integrity."""
        try:
            self._connection = self._create_connection()
            # Perform a quick query to ensure it's a valid Zotero DB
            result = self.execute_single_query("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
            if not result:
                raise DatabaseError("Invalid Zotero database: missing items table")
            logger.debug(f"Successfully initialized database connection to {self.db_path}")
        except DatabaseLockedError:
            # Re-raise DatabaseLockedError as-is
            raise
        except DatabaseError as e:
            # Check if it's about invalid database file
            if "file is not a database" in str(e) or "Invalid Zotero database" in str(e):
                raise DatabaseError(f"Cannot access database: {e}")
            raise
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            if "database is locked" in str(e).lower():
                raise DatabaseLockedError("Zotero database is locked. Please close Zotero and try again.")
            elif "file is not a database" in str(e).lower():
                raise DatabaseError(f"Cannot access database: {e}")
            raise DatabaseError(f"Failed to initialize or verify database: {e}")
        except Exception as e:
            if "database is locked" in str(e).lower():
                raise DatabaseLockedError("Zotero database is locked. Please close Zotero and try again.")
            logger.error(f"An unexpected error occurred during database initialization: {e}")
            raise DatabaseError(f"Cannot access database: {e}")

    @contextmanager
    def get_cursor(self) -> sqlite3.Cursor:
        """
        Provides a cursor from the persistent connection.

        This is a context manager that handles exceptions and ensures that
        the connection is alive.
        """
        if not self._connection:
            raise DatabaseError("Connection is not initialized. Cannot get cursor.")
        
        try:
            yield self._connection.cursor()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                raise DatabaseLockedError("Zotero database is locked during operation. Please close Zotero.")
            raise DatabaseError(f"A database operation failed: {e}")
        except Exception as e:
            raise DatabaseError(f"An unexpected error occurred while executing a query: {e}")

    def execute_query(self, query: str, params: Iterable[Any] = ()) -> List[sqlite3.Row]:
        """
        Execute a query that returns multiple rows.

        Args:
            query: The SQL query string to execute.
            params: A tuple or list of parameters to substitute into the query.

        Returns:
            A list of sqlite3.Row objects.
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_single_query(self, query: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        """
        Execute a query that returns a single row.

        Args:
            query: The SQL query string to execute.
            params: A tuple or list of parameters to substitute into the query.

        Returns:
            A single sqlite3.Row object, or None if no results are found.
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def get_database_version(self) -> str:
        """
        Get the Zotero database schema version.

        Returns:
            The version string, or "unknown" if it cannot be retrieved.
        """
        try:
            result = self.execute_single_query("SELECT version FROM version WHERE schema = 'system'")
            return str(result['version']) if result else "unknown"
        except (DatabaseError, sqlite3.Error) as e:
            logger.warning(f"Could not read database version: {e}")
            return "unknown"

    def close(self) -> None:
        """Closes the database connection if it is open."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Database connection closed.")

    def __enter__(self):
        """Enter the runtime context for the connection."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context, ensuring the connection is closed."""
        self.close()


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