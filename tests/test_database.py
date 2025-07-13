import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from zurch.database import DatabaseConnection, DatabaseError, DatabaseLockedError, get_attachment_type


class TestDatabaseConnection:
    """Test the DatabaseConnection class."""
    
    @pytest.fixture
    def sample_db_path(self):
        """Return path to sample database."""
        return Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"
    
    @pytest.fixture
    def db_connection(self, sample_db_path):
        """Create a DatabaseConnection instance."""
        if sample_db_path.exists():
            return DatabaseConnection(sample_db_path)
        else:
            pytest.skip("Sample database not found")
    
    def test_database_connection_initialization(self, sample_db_path):
        """Test database connection initialization."""
        if sample_db_path.exists():
            db = DatabaseConnection(sample_db_path)
            assert db.db_path == sample_db_path
        else:
            pytest.skip("Sample database not found")
    
    def test_database_not_found_error(self):
        """Test error when database file doesn't exist."""
        nonexistent_path = Path("/nonexistent/database.sqlite")
        with pytest.raises(DatabaseError, match="Database not found"):
            DatabaseConnection(nonexistent_path)
    
    def test_invalid_database_error(self):
        """Test error when file is not a valid Zotero database."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            tmp.write(b"not a valid database")
            tmp.flush()
            tmp_path = Path(tmp.name)
            
            try:
                with pytest.raises(DatabaseError, match="Cannot access database"):
                    DatabaseConnection(tmp_path)
            finally:
                # Clean up
                if tmp_path.exists():
                    tmp_path.unlink()
    
    def test_get_database_version(self, db_connection):
        """Test getting database version."""
        version = db_connection.get_database_version()
        assert isinstance(version, str)
        assert len(version) > 0
    
    def test_execute_query(self, db_connection):
        """Test executing a query."""
        results = db_connection.execute_query("SELECT COUNT(*) FROM items")
        assert len(results) == 1
        assert isinstance(results[0][0], int)
    
    def test_execute_single_query(self, db_connection):
        """Test executing a single result query."""
        result = db_connection.execute_single_query("SELECT COUNT(*) FROM items")
        assert result is not None
        assert isinstance(result[0], int)
    
    def test_execute_query_with_parameters(self, db_connection):
        """Test executing a parameterized query."""
        results = db_connection.execute_query("SELECT * FROM items WHERE itemID = ?", (1,))
        assert isinstance(results, list)
    
    def test_database_locked_error(self):
        """Test handling of database locked error."""
        # Create a real temporary file to avoid path checks
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            tmp.write(b"fake database")
            tmp.flush()
            tmp_path = Path(tmp.name)
            
            try:
                with patch('sqlite3.connect') as mock_connect:
                    mock_connect.side_effect = Exception("database is locked")
                    
                    with pytest.raises(DatabaseLockedError, match="database is locked"):
                        DatabaseConnection(tmp_path)
            finally:
                # Clean up
                if tmp_path.exists():
                    tmp_path.unlink()


class TestGetAttachmentType:
    """Test the get_attachment_type utility function."""
    
    def test_pdf_attachment(self):
        """Test PDF attachment type."""
        assert get_attachment_type("application/pdf") == "pdf"
    
    def test_epub_attachment(self):
        """Test EPUB attachment type."""
        assert get_attachment_type("application/epub+zip") == "epub"
    
    def test_text_attachment(self):
        """Test text attachment type."""
        assert get_attachment_type("text/plain") == "txt"
        assert get_attachment_type("text/html") == "txt"
    
    def test_unknown_attachment(self):
        """Test unknown attachment type."""
        assert get_attachment_type("application/unknown") is None
        assert get_attachment_type("video/mp4") is None
    
    def test_none_attachment(self):
        """Test None input."""
        assert get_attachment_type(None) is None
        assert get_attachment_type("") is None
    
    def test_case_insensitive(self):
        """Test case insensitive handling."""
        assert get_attachment_type("APPLICATION/PDF") == "pdf"
        assert get_attachment_type("Application/Epub+Zip") == "epub"