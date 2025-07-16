import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from zurch.search import ZoteroDatabase
from zurch.models import ZoteroItem, ZoteroCollection
from zurch.database import DatabaseError, DatabaseLockedError
from zurch.utils import load_config, format_attachment_icon, pad_number, find_zotero_database
from zurch import cli
from zurch.display import display_items
from zurch.handlers import interactive_selection

class TestZoteroDatabase:
    """Test the ZoteroDatabase class."""
    
    @pytest.fixture
    def sample_db_path(self):
        """Return path to sample database."""
        return Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"
    
    @pytest.fixture
    def db(self, sample_db_path):
        """Create a ZoteroDatabase instance with sample data."""
        if sample_db_path.exists():
            return ZoteroDatabase(sample_db_path)
        else:
            pytest.skip("Sample database not found")
    
    def test_database_initialization(self, sample_db_path):
        """Test database initialization."""
        if sample_db_path.exists():
            db = ZoteroDatabase(sample_db_path)
            assert db.db_path == sample_db_path
        else:
            pytest.skip("Sample database not found")
    
    def test_database_not_found(self):
        """Test error when database file doesn't exist."""
        nonexistent_path = Path("/nonexistent/database.sqlite")
        with pytest.raises(DatabaseError, match="Database not found"):
            ZoteroDatabase(nonexistent_path)
    
    def test_list_collections(self, db):
        """Test listing collections."""
        collections = db.list_collections()
        assert isinstance(collections, list)
        assert len(collections) > 0
        
        # Check that collections have required attributes
        for collection in collections:
            assert isinstance(collection, ZoteroCollection)
            assert hasattr(collection, 'collection_id')
            assert hasattr(collection, 'name')
            assert hasattr(collection, 'depth')
    
    def test_search_collections(self, db):
        """Test searching collections by name."""
        # Search for 'Heritage' which should exist in sample data
        results = db.search_collections("Heritage")
        assert isinstance(results, list)
        
        if results:
            # Verify all results contain the search term
            for collection in results:
                assert "heritage" in collection.name.lower()
    
    def test_get_collection_items(self, db):
        """Test getting items from a collection."""
        # First get a collection that has items
        collections = db.list_collections()
        collection_with_items = None
        
        for collection in collections:
            if collection.item_count > 0:
                collection_with_items = collection
                break
        
        if collection_with_items:
            items, total_count = db.get_collection_items(collection_with_items.name)
            assert isinstance(items, list)
            assert isinstance(total_count, int)
            assert len(items) > 0
            
            # Check item structure
            for item in items:
                assert isinstance(item, ZoteroItem)
                assert hasattr(item, 'item_id')
                assert hasattr(item, 'title')
                assert hasattr(item, 'item_type')
    
    def test_search_items_by_name(self, db):
        """Test searching items by name."""
        items, total_count = db.search_items_by_name("China")
        assert isinstance(items, list)
        assert isinstance(total_count, int)
        assert len(items) > 0
        
        # Verify results contain search term
        for item in items:
            assert "china" in item.title.lower()
    
    def test_search_items_by_name_exact(self, db):
        """Test exact search for items by name."""
        # Test exact search
        items_exact, total_exact = db.search_items_by_name("China", exact_match=True)
        assert isinstance(items_exact, list)
        assert isinstance(total_exact, int)
        
        # Test partial search for comparison
        items_partial, total_partial = db.search_items_by_name("China", exact_match=False)
        
        # Exact search should return fewer or equal results than partial search
        assert total_exact <= total_partial
        
        # All exact matches should have the exact title "China"
        for item in items_exact:
            assert item.title.lower() == "china"
    
    def test_search_items_unicode(self, db):
        """Test searching with Unicode characters (Chinese, Japanese, Korean, etc.)."""
        # Test Chinese characters
        items_cn, total_cn = db.search_items_by_name("中国")
        assert isinstance(items_cn, list)
        assert isinstance(total_cn, int)
        
        # Test Japanese characters  
        items_jp, total_jp = db.search_items_by_name("日本")
        assert isinstance(items_jp, list)
        assert isinstance(total_jp, int)
        
        # Test Korean characters
        items_kr, total_kr = db.search_items_by_name("한국")
        assert isinstance(items_kr, list)
        assert isinstance(total_kr, int)
        
        # Test Unicode punctuation (em dash)
        items_dash, total_dash = db.search_items_by_name("–")
        assert isinstance(items_dash, list)
        assert isinstance(total_dash, int)
        
        # Verify Chinese results contain the search term if any found
        for item in items_cn:
            assert "中国" in item.title
    
    def test_search_items_multiple_keywords(self, db):
        """Test AND search with multiple keywords."""
        # Test AND search with multiple keywords (list input)
        keywords = ["world", "history"]
        items_and, total_and = db.search_items_by_name(keywords)
        assert isinstance(items_and, list)
        assert isinstance(total_and, int)
        
        # All results should contain both keywords
        for item in items_and:
            title_lower = item.title.lower()
            assert "world" in title_lower, f"Item '{item.title}' missing 'world'"
            assert "history" in title_lower, f"Item '{item.title}' missing 'history'"
        
        # Test phrase search (string input) 
        phrase = "world history"
        items_phrase, total_phrase = db.search_items_by_name(phrase)
        assert isinstance(items_phrase, list)
        assert isinstance(total_phrase, int)
        
        # Phrase search results should contain the exact phrase
        for item in items_phrase:
            title_lower = item.title.lower()
            assert "world history" in title_lower, f"Item '{item.title}' missing phrase 'world history'"
        
        # AND search typically returns more results than phrase search
        # (items with "world" and "history" separately vs "world history" together)
        assert total_and >= total_phrase, "AND search should find more or equal items than phrase search"
    
    def test_search_items_wildcards(self, db):
        """Test wildcard patterns in search."""
        # Test prefix wildcard - should find items with "world" patterns
        items_prefix, total_prefix = db.search_items_by_name("world%")
        assert isinstance(items_prefix, list)
        assert isinstance(total_prefix, int)
        
        # All results should contain "world" (the wildcard extends the search)
        for item in items_prefix:
            title_lower = item.title.lower()
            assert "world" in title_lower, f"Item '{item.title}' doesn't contain 'world'"
        
        # Test suffix wildcard - should find words ending with "history" anywhere in title
        items_suffix, total_suffix = db.search_items_by_name("%history")
        assert isinstance(items_suffix, list)
        assert isinstance(total_suffix, int)
        
        # All results should contain "history" (SQL LIKE handles partial matches correctly)
        for item in items_suffix:
            title_lower = item.title.lower()
            assert "history" in title_lower, f"Item '{item.title}' doesn't contain 'history'"
        
        # Test contains wildcard (anywhere)
        items_contains, total_contains = db.search_items_by_name("%world%")
        assert isinstance(items_contains, list)
        assert isinstance(total_contains, int)
        
        # All results should contain "world"
        for item in items_contains:
            title_lower = item.title.lower()
            assert "world" in title_lower, f"Item '{item.title}' doesn't contain 'world'"
    
    def test_get_item_metadata(self, db):
        """Test getting item metadata."""
        # First find an item
        items, total_count = db.search_items_by_name("Heritage")
        
        if items:
            item = items[0]
            metadata = db.get_item_metadata(item.item_id)
            
            assert isinstance(metadata, dict)
            assert 'itemType' in metadata
            # Common fields that should exist
            expected_fields = ['dateAdded', 'dateModified']
            for field in expected_fields:
                assert field in metadata

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_escape_sql_like_pattern(self):
        """Test SQL LIKE pattern escaping."""
        from zurch.utils import escape_sql_like_pattern
        
        # Test escaping % wildcard
        assert escape_sql_like_pattern("50%") == "50\\%"
        assert escape_sql_like_pattern("%test%") == "\\%test\\%"
        
        # Test escaping _ wildcard
        assert escape_sql_like_pattern("test_name") == "test\\_name"
        assert escape_sql_like_pattern("_underscore_") == "\\_underscore\\_"
        
        # Test escaping backslash
        assert escape_sql_like_pattern("path\\to\\file") == "path\\\\to\\\\file"
        
        # Test combined escaping
        assert escape_sql_like_pattern("test_%\\") == "test\\_\\%\\\\"
        
        # Test normal strings remain unchanged
        assert escape_sql_like_pattern("normal text") == "normal text"
        assert escape_sql_like_pattern("O'Brien") == "O'Brien"  # Single quotes handled by parameterized queries
    
    def test_format_attachment_icon(self):
        """Test attachment icon formatting (legacy function)."""
        # Test PDF
        assert "📘" in format_attachment_icon("pdf")
        
        # Test EPUB
        assert "📗" in format_attachment_icon("epub")
        
        # Test TXT
        assert "📄" in format_attachment_icon("txt")
        
        # Test None
        assert format_attachment_icon(None) == ""
        
        # Test unknown type
        assert format_attachment_icon("other") == ""
    
    def test_format_item_type_icon(self):
        """Test item type icon formatting."""
        from zurch.utils import format_item_type_icon
        
        # Test book type
        assert "📗" in format_item_type_icon("book")
        
        # Test journal article type
        assert "📄" in format_item_type_icon("journalArticle")
        assert "📄" in format_item_type_icon("journal article")
        
        # Test other types
        assert format_item_type_icon("document") == ""
        assert format_item_type_icon("thesis") == ""
    
    def test_format_attachment_link_icon(self):
        """Test attachment link icon formatting."""
        from zurch.utils import format_attachment_link_icon
        
        # Test PDF
        assert "🔗" in format_attachment_link_icon("pdf")
        
        # Test EPUB
        assert "🔗" in format_attachment_link_icon("epub")
        
        # Test TXT (should not show link icon)
        assert format_attachment_link_icon("txt") == ""
        
        # Test None
        assert format_attachment_link_icon(None) == ""
        
        # Test unknown type
        assert format_attachment_link_icon("other") == ""
    
    def test_pad_number(self):
        """Test number padding for alignment."""
        assert pad_number(1, 100) == "  1"
        assert pad_number(10, 100) == " 10"
        assert pad_number(100, 100) == "100"
        
        assert pad_number(1, 10) == " 1"
        assert pad_number(5, 10) == " 5"
    
    def test_load_config(self):
        """Test configuration loading."""
        config = load_config()
        assert isinstance(config, dict)
        
        # Check for required keys
        assert 'max_results' in config
        assert 'debug' in config
        assert 'zotero_database_path' in config
        
        # Check default values
        assert config['max_results'] == 100
        assert config['debug'] is False
    
    def test_config_paths(self):
        """Test config directory paths are OS-appropriate."""
        from zurch.utils import get_config_dir
        import platform
        
        config_dir = get_config_dir()
        assert config_dir.exists()
        
        if platform.system() == "Windows":
            assert "AppData" in str(config_dir) and "zurch" in str(config_dir)
        else:  # macOS, Linux and others
            assert (".config/zurch" in str(config_dir) or 
                    "zurch" in str(config_dir))  # XDG_CONFIG_HOME might be set
    
    def test_highlight_search_term(self):
        """Test search term highlighting."""
        from zurch.utils import highlight_search_term
        
        # Test basic highlighting
        result = highlight_search_term("Japanese History", "japan")
        assert "\033[1m" in result  # Contains bold formatting
        assert "Japan" in result
        
        # Test case insensitive
        result = highlight_search_term("JAPANESE HISTORY", "japan")
        assert "\033[1m" in result
        
        # Test with wildcard
        result = highlight_search_term("Japanese History", "japan%")
        assert "\033[1m" in result
        assert "Japan" in result
        
        # Test no match
        result = highlight_search_term("Chinese History", "japan")
        assert "\033[1m" not in result
        
        # Test empty inputs
        result = highlight_search_term("", "japan")
        assert result == ""
        
        result = highlight_search_term("Japanese History", "")
        assert result == "Japanese History"

class TestCLIIntegration:
    """Test CLI integration."""
    
    def test_cli_help(self):
        """Test CLI help output."""
        parser = cli.create_parser()
        help_text = parser.format_help()
        
        # Check for key components
        assert help_text.startswith("usage:")
        assert "--folder" in help_text
        assert "--name" in help_text
        assert "--list" in help_text
        assert "--interactive" in help_text
        assert "append 'g'" in help_text  # Check for grab functionality in interactive mode
        assert "--exact" in help_text
    
    def test_display_items(self, capsys):
        """Test item display functionality."""
        items = [
            ZoteroItem(1, "Test Book", "book", "pdf"),
            ZoteroItem(2, "Test Article", "journalArticle", None),
            ZoteroItem(3, "Test Document", "document", "epub")
        ]
        
        display_items(items, 3)
        captured = capsys.readouterr()
        
        assert "Test Book" in captured.out
        assert "Test Article" in captured.out
        assert "Test Document" in captured.out
        assert "📗" in captured.out  # Green book icon for book
        assert "📄" in captured.out  # Document icon for journal article
        assert "🔗" in captured.out  # Link icon for attachments
    
    @patch('zurch.handlers.input')
    def test_interactive_selection(self, mock_input):
        """Test interactive item selection."""
        items = [
            ZoteroItem(1, "Test Item 1", "book"),
            ZoteroItem(2, "Test Item 2", "article")
        ]
        
        # Test valid selection
        mock_input.return_value = "1"
        selected, should_grab = interactive_selection(items)
        assert selected == items[0]
        assert should_grab == False
        
        # Test cancel
        mock_input.return_value = "0"
        selected, should_grab = interactive_selection(items)
        assert selected is None
        assert should_grab == False
        
        # Test KeyboardInterrupt (Ctrl+C)
        mock_input.side_effect = KeyboardInterrupt()
        selected, should_grab = interactive_selection(items)
        assert selected is None
        assert should_grab == False

class TestFilterFunctionality:
    """Test filtering capabilities."""
    
    def test_collection_filtering(self):
        """Test collection name filtering with % wildcards."""
        import fnmatch
        
        collections = ["China", "Chinese History", "Japan", "Korea", "Burma"]
        
        # Test partial matching (default behavior)
        filtered = [c for c in collections if "china" in c.lower()]
        assert "China" in filtered
        
        # Test % wildcard patterns (converted to fnmatch)
        pattern = "chin%".replace('%', '*')
        filtered = [c for c in collections if fnmatch.fnmatch(c.lower(), pattern)]
        assert "China" in filtered
        assert "Chinese History" in filtered
        
        # Test contains pattern with % 
        pattern = "%ese%".replace('%', '*')
        filtered = [c for c in collections if fnmatch.fnmatch(c.lower(), pattern)]
        assert "Chinese History" in filtered

# Test data integrity
class TestDatabaseIntegrity:
    """Test database integrity and error handling."""
    
    @pytest.fixture
    def sample_db_path(self):
        """Return path to sample database."""
        return Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"
    
    def test_database_version(self, sample_db_path):
        """Test database version detection."""
        if sample_db_path.exists():
            db = ZoteroDatabase(sample_db_path)
            version = db.get_database_version()
            assert isinstance(version, str)
            assert len(version) > 0
        else:
            pytest.skip("Sample database not found")
    
    def test_empty_search_results(self, sample_db_path):
        """Test handling of empty search results."""
        if sample_db_path.exists():
            db = ZoteroDatabase(sample_db_path)
            
            # Search for something that shouldn't exist
            items, total_count = db.search_items_by_name("NONEXISTENT_SEARCH_TERM_XYZ123")
            assert isinstance(items, list)
            assert isinstance(total_count, int)
            assert len(items) == 0
            assert total_count == 0
            
            # Search for nonexistent collection
            collections = db.search_collections("NONEXISTENT_COLLECTION_XYZ123")
            assert isinstance(collections, list)
            assert len(collections) == 0
        else:
            pytest.skip("Sample database not found")

if __name__ == "__main__":
    pytest.main([__file__])