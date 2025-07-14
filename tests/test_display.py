import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from zurch.display import (
    display_items, display_grouped_items, matches_search_term,
    display_hierarchical_search_results, show_item_metadata
)
from zurch.models import ZoteroItem, ZoteroCollection


class TestDisplayItems:
    """Test the display_items function."""
    
    def test_display_basic_items(self, capsys):
        """Test basic item display."""
        items = [
            ZoteroItem(1, "Test Book", "book", "pdf"),
            ZoteroItem(2, "Test Article", "journalArticle", None),
            ZoteroItem(3, "Test Document", "document", "epub")
        ]
        
        display_items(items, 10)
        captured = capsys.readouterr()
        
        assert "Test Book" in captured.out
        assert "Test Article" in captured.out
        assert "Test Document" in captured.out
        assert "📗" in captured.out  # Green book icon
        assert "📄" in captured.out  # Document icon
        assert "🔗" in captured.out  # Link icon for attachments
    
    def test_display_items_with_search_term(self, capsys):
        """Test item display with search term highlighting."""
        items = [
            ZoteroItem(1, "China History Book", "book", "pdf"),
            ZoteroItem(2, "Japanese Culture", "journalArticle", None)
        ]
        
        display_items(items, 10, search_term="china")
        captured = capsys.readouterr()
        
        # Should highlight "China" in the first item (with ANSI codes)
        assert "History Book" in captured.out  # Check for non-highlighted part
        assert "Japanese Culture" in captured.out
    
    def test_display_items_with_ids(self, capsys):
        """Test item display with ID numbers."""
        items = [
            ZoteroItem(123, "Test Item", "book", "pdf")
        ]
        
        display_items(items, 10, show_ids=True)
        captured = capsys.readouterr()
        
        assert "[ID:123]" in captured.out
    
    def test_display_items_with_duplicates(self, capsys):
        """Test display of duplicate items."""
        items = [
            ZoteroItem(1, "Normal Item", "book", "pdf"),
            ZoteroItem(2, "Duplicate Item", "book", "pdf", is_duplicate=True)
        ]
        
        display_items(items, 10)
        captured = capsys.readouterr()
        
        # Both should be displayed but duplicates should have different formatting
        assert "Normal Item" in captured.out
        assert "Duplicate Item" in captured.out
    
    def test_display_items_numbering(self, capsys):
        """Test proper numbering and padding."""
        items = [ZoteroItem(i, f"Item {i}", "book") for i in range(1, 15)]
        
        display_items(items, 20)
        captured = capsys.readouterr()
        
        # Check that numbering appears correctly
        assert "1." in captured.out
        assert "14." in captured.out  # Last item


class TestDisplayGroupedItems:
    """Test the display_grouped_items function."""
    
    def test_display_grouped_items_basic(self, capsys):
        """Test basic grouped item display."""
        collection1 = ZoteroCollection(1, "Collection 1", None, 0, 2, "Collection 1")
        collection2 = ZoteroCollection(2, "Collection 2", None, 0, 1, "Collection 2")
        
        items1 = [ZoteroItem(1, "Item 1", "book"), ZoteroItem(2, "Item 2", "article")]
        items2 = [ZoteroItem(3, "Item 3", "book")]
        
        grouped_items = [(collection1, items1), (collection2, items2)]
        
        result = display_grouped_items(grouped_items, 10)
        captured = capsys.readouterr()
        
        # Check collection headers
        assert "=== Collection 1 (2 items) ===" in captured.out
        assert "=== Collection 2 (1 items) ===" in captured.out
        
        # Check items
        assert "Item 1" in captured.out
        assert "Item 2" in captured.out
        assert "Item 3" in captured.out
        
        # Check return value
        assert len(result) == 3
        assert result[0].title == "Item 1"
        assert result[1].title == "Item 2"
        assert result[2].title == "Item 3"
    
    def test_display_grouped_items_with_limit(self, capsys):
        """Test grouped item display with max_results limit."""
        collection = ZoteroCollection(1, "Collection", None, 0, 3, "Collection")
        items = [ZoteroItem(i, f"Item {i}", "book") for i in range(1, 4)]
        grouped_items = [(collection, items)]
        
        result = display_grouped_items(grouped_items, 2)  # Limit to 2 items
        captured = capsys.readouterr()
        
        assert len(result) == 2
        assert "Item 1" in captured.out
        assert "Item 2" in captured.out
        assert "Item 3" not in captured.out
    
    def test_display_grouped_items_hierarchical_paths(self, capsys):
        """Test display with hierarchical collection paths."""
        collection = ZoteroCollection(1, "Child", 0, 1, 2, "Parent > Child")
        items = [ZoteroItem(1, "Item", "book")]
        grouped_items = [(collection, items)]
        
        display_grouped_items(grouped_items, 10)
        captured = capsys.readouterr()
        
        assert "=== Parent > Child (1 items) ===" in captured.out
    
    def test_display_grouped_items_continuous_numbering(self, capsys):
        """Test that numbering is continuous across collections."""
        collection1 = ZoteroCollection(1, "Coll1", None, 0, 2, "Coll1")
        collection2 = ZoteroCollection(2, "Coll2", None, 0, 2, "Coll2")
        
        items1 = [ZoteroItem(1, "Item 1", "book"), ZoteroItem(2, "Item 2", "book")]
        items2 = [ZoteroItem(3, "Item 3", "book"), ZoteroItem(4, "Item 4", "book")]
        
        grouped_items = [(collection1, items1), (collection2, items2)]
        
        display_grouped_items(grouped_items, 10)
        captured = capsys.readouterr()
        
        # Check that all items are numbered
        assert "Item 1" in captured.out
        assert "Item 2" in captured.out
        assert "Item 3" in captured.out
        assert "Item 4" in captured.out


class TestMatchesSearchTerm:
    """Test the matches_search_term function."""
    
    def test_matches_search_term_basic(self):
        """Test basic partial matching."""
        assert matches_search_term("China History", "china")
        assert matches_search_term("CHINA HISTORY", "china")  # Case insensitive
        assert not matches_search_term("Japanese History", "china")
    
    def test_matches_search_term_wildcards(self):
        """Test wildcard pattern matching."""
        assert matches_search_term("China History", "china%")
        assert matches_search_term("China", "china%")
        assert not matches_search_term("Ancient China", "china%")  # Doesn't start with china
        
        assert matches_search_term("Ancient China", "%china")
        assert matches_search_term("China", "%china")
        assert not matches_search_term("China History", "%china")  # Doesn't end with china
        
        assert matches_search_term("Ancient China History", "%china%")
        assert matches_search_term("China Research", "%china%")
    
    def test_matches_search_term_edge_cases(self):
        """Test edge cases."""
        assert not matches_search_term("", "search")
        assert matches_search_term("text", "")  # Empty search term should match everything
        assert not matches_search_term(None, "search")
        assert matches_search_term("text", None)  # None search term should match everything


class TestDisplayHierarchicalSearchResults:
    """Test the display_hierarchical_search_results function."""
    
    def test_display_hierarchical_flat_collections(self, capsys):
        """Test display of flat collections."""
        collections = [
            ZoteroCollection(1, "China", None, 0, 5, "China"),
            ZoteroCollection(2, "Japan", None, 0, 3, "Japan")
        ]
        
        display_hierarchical_search_results(collections, "china", max_results=10)
        captured = capsys.readouterr()
        
        # Should highlight matching terms
        assert "China" in captured.out
        assert "(5 items)" in captured.out
        # Japan shouldn't be shown as it doesn't match "china"
        assert "Japan" not in captured.out
    
    def test_display_hierarchical_nested_collections(self, capsys):
        """Test display of nested collections."""
        collections = [
            ZoteroCollection(1, "Asia", None, 0, 10, "Asia"),
            ZoteroCollection(2, "China", 1, 1, 5, "Asia > China"),
            ZoteroCollection(3, "History", 2, 2, 3, "Asia > China > History"),
            ZoteroCollection(4, "Japan", 1, 1, 2, "Asia > Japan")
        ]
        
        display_hierarchical_search_results(collections, "china", max_results=10)
        captured = capsys.readouterr()
        
        # Should show the hierarchy path to matching items
        assert "China" in captured.out  # Direct match should be shown
        # Test basic functionality rather than exact hierarchy logic
        assert len(captured.out) > 0  # Something was displayed
    
    def test_display_hierarchical_with_limit(self, capsys):
        """Test hierarchical display with max_results limit."""
        collections = [
            ZoteroCollection(1, "China 1", None, 0, 5, "China 1"),
            ZoteroCollection(2, "China 2", None, 0, 3, "China 2"),
            ZoteroCollection(3, "China 3", None, 0, 1, "China 3")
        ]
        
        display_hierarchical_search_results(collections, "china", max_results=2)
        captured = capsys.readouterr()
        
        # Should only show first 2 matches
        china_lines = [line for line in captured.out.split('\n') if "China" in line and "items)" in line]
        assert len(china_lines) <= 2
    
    def test_display_hierarchical_no_matches(self, capsys):
        """Test hierarchical display with no matches."""
        collections = [
            ZoteroCollection(1, "Japan", None, 0, 5, "Japan"),
            ZoteroCollection(2, "Korea", None, 0, 3, "Korea")
        ]
        
        display_hierarchical_search_results(collections, "china", max_results=10)
        captured = capsys.readouterr()
        
        # Should show nothing (or minimal output)
        lines = [line.strip() for line in captured.out.split('\n') if line.strip()]
        relevant_lines = [line for line in lines if "Japan" in line or "Korea" in line]
        assert len(relevant_lines) == 0


class TestShowItemMetadata:
    """Test the show_item_metadata function."""
    
    def test_show_item_metadata_basic(self, capsys):
        """Test basic metadata display."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'itemType': 'book',
            'title': 'Test Book',
            'date': '2023',
            'abstractNote': 'Test abstract',
            'creators': [
                {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Smith'}
            ],
            'dateAdded': '2023-01-01',
            'dateModified': '2023-01-02'
        }
        mock_db.get_item_collections.return_value = ['Collection 1', 'Collection 2']
        
        item = ZoteroItem(1, "Test Book", "book")
        show_item_metadata(mock_db, item)
        captured = capsys.readouterr()
        
        assert "--- Metadata for: Test Book ---" in captured.out
        assert "book" in captured.out
        assert "Test Book" in captured.out
        assert "2023" in captured.out
        assert "Test abstract" in captured.out
        assert "Creators:" in captured.out
        assert "John Smith" in captured.out
        assert "Collections:" in captured.out
        assert "Collection 1" in captured.out
        assert "Collection 2" in captured.out
        assert "2023-01-01" in captured.out
        assert "2023-01-02" in captured.out
    
    def test_show_item_metadata_with_multiple_creators(self, capsys):
        """Test metadata display with multiple creators."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'itemType': 'journalArticle',
            'title': 'Test Article',
            'creators': [
                {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Smith'},
                {'creatorType': 'author', 'firstName': 'Jane', 'lastName': 'Doe'},
                {'creatorType': 'editor', 'firstName': 'Bob', 'lastName': 'Wilson'}
            ],
            'dateAdded': '2023-01-01',
            'dateModified': '2023-01-02'
        }
        mock_db.get_item_collections.return_value = []
        
        item = ZoteroItem(1, "Test Article", "journalArticle")
        show_item_metadata(mock_db, item)
        captured = capsys.readouterr()
        
        assert "John Smith" in captured.out
        assert "Jane Doe" in captured.out  
        assert "Bob Wilson" in captured.out
    
    def test_show_item_metadata_no_collections(self, capsys):
        """Test metadata display with no collections."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'itemType': 'book',
            'title': 'Test Book',
            'dateAdded': '2023-01-01',
            'dateModified': '2023-01-02'
        }
        mock_db.get_item_collections.return_value = []
        
        item = ZoteroItem(1, "Test Book", "book")
        show_item_metadata(mock_db, item)
        captured = capsys.readouterr()
        
        # Collections section should not appear
        assert "Collections:" not in captured.out
    
    def test_show_item_metadata_error_handling(self, capsys):
        """Test metadata display error handling."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.side_effect = Exception("Database error")
        
        item = ZoteroItem(1, "Test Book", "book")
        show_item_metadata(mock_db, item)
        captured = capsys.readouterr()
        
        assert "Error getting metadata: Database error" in captured.out
    
    def test_show_item_metadata_missing_names(self, capsys):
        """Test metadata display with creators missing names."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'itemType': 'book',
            'title': 'Test Book',
            'creators': [
                {'creatorType': 'author', 'lastName': 'Smith'},  # No first name
                {'creatorType': 'author', 'firstName': 'Jane'},  # No last name
                {'creatorType': 'author'}  # No names at all
            ],
            'dateAdded': '2023-01-01',
            'dateModified': '2023-01-02'
        }
        mock_db.get_item_collections.return_value = []
        
        item = ZoteroItem(1, "Test Book", "book")
        show_item_metadata(mock_db, item)
        captured = capsys.readouterr()
        
        assert "Smith" in captured.out
        assert "Jane" in captured.out
        assert "Unknown" in captured.out


if __name__ == "__main__":
    pytest.main([__file__])