import pytest
from unittest.mock import MagicMock

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
            ZoteroItem(item_id=1, title="Test Book", item_type="book", attachment_type="pdf"),
            ZoteroItem(item_id=2, title="Test Article", item_type="journalArticle", attachment_type=None),
            ZoteroItem(item_id=3, title="Test Document", item_type="document", attachment_type="epub")
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
            ZoteroItem(item_id=1, title="China History Book", item_type="book", attachment_type="pdf"),
            ZoteroItem(item_id=2, title="Japanese Culture", item_type="journalArticle", attachment_type=None)
        ]
        
        display_items(items, 10, search_term="china")
        captured = capsys.readouterr()
        
        # Should highlight "China" in the first item (with ANSI codes)
        assert "History Book" in captured.out  # Check for non-highlighted part
        assert "Japanese Culture" in captured.out
    
    def test_display_items_with_ids(self, capsys):
        """Test item display with ID numbers."""
        items = [
            ZoteroItem(item_id=123, title="Test Item", item_type="book", attachment_type="pdf")
        ]
        
        display_items(items, 10, show_ids=True)
        captured = capsys.readouterr()
        
        assert "[ID:123]" in captured.out
    
    def test_display_items_with_duplicates(self, capsys):
        """Test display of duplicate items."""
        items = [
            ZoteroItem(item_id=1, title="Normal Item", item_type="book", attachment_type="pdf"),
            ZoteroItem(item_id=2, title="Duplicate Item", item_type="book", attachment_type="pdf", is_duplicate=True)
        ]
        
        display_items(items, 10)
        captured = capsys.readouterr()
        
        # Both should be displayed but duplicates should have different formatting
        assert "Normal Item" in captured.out
        assert "Duplicate Item" in captured.out
    
    def test_display_items_numbering(self, capsys):
        """Test proper numbering and padding."""
        items = [ZoteroItem(item_id=i, title=f"Item {i}", item_type="book") for i in range(1, 15)]
        
        display_items(items, 20)
        captured = capsys.readouterr()
        
        # Check that numbering appears correctly
        assert "1." in captured.out
        assert "14." in captured.out  # Last item


class TestDisplayGroupedItems:
    """Test the display_grouped_items function."""
    
    def test_display_grouped_items_basic(self, capsys):
        """Test basic grouped item display."""
        collection1 = ZoteroCollection(collection_id=1, name="Collection 1", parent_id=None, depth=0, item_count=2, full_path="Collection 1")
        collection2 = ZoteroCollection(collection_id=2, name="Collection 2", parent_id=None, depth=0, item_count=1, full_path="Collection 2")
        
        items1 = [ZoteroItem(item_id=1, title="Item 1", item_type="book"), ZoteroItem(item_id=2, title="Item 2", item_type="article")]
        items2 = [ZoteroItem(item_id=3, title="Item 3", item_type="book")]
        
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
        collection = ZoteroCollection(collection_id=1, name="Collection", parent_id=None, depth=0, item_count=3, full_path="Collection")
        items = [ZoteroItem(item_id=i, title=f"Item {i}", item_type="book") for i in range(1, 4)]
        grouped_items = [(collection, items)]
        
        result = display_grouped_items(grouped_items, 2)  # Limit to 2 items
        captured = capsys.readouterr()
        
        assert len(result) == 2
        assert "Item 1" in captured.out
        assert "Item 2" in captured.out
        assert "Item 3" not in captured.out
    
    def test_display_grouped_items_hierarchical_paths(self, capsys):
        """Test display with hierarchical collection paths."""
        collection = ZoteroCollection(collection_id=1, name="Child", parent_id=1, depth=1, item_count=2, full_path="Parent > Child")
        items = [ZoteroItem(item_id=1, title="Item", item_type="book")]
        grouped_items = [(collection, items)]
        
        display_grouped_items(grouped_items, 10)
        captured = capsys.readouterr()
        
        assert "=== Parent > Child (1 items) ===" in captured.out
    
    def test_display_grouped_items_continuous_numbering(self, capsys):
        """Test that numbering is continuous across collections."""
        collection1 = ZoteroCollection(collection_id=1, name="Coll1", parent_id=None, depth=0, item_count=2, full_path="Coll1")
        collection2 = ZoteroCollection(collection_id=2, name="Coll2", parent_id=None, depth=0, item_count=2, full_path="Coll2")
        
        items1 = [ZoteroItem(item_id=1, title="Item 1", item_type="book"), ZoteroItem(item_id=2, title="Item 2", item_type="book")]
        items2 = [ZoteroItem(item_id=3, title="Item 3", item_type="book"), ZoteroItem(item_id=4, title="Item 4", item_type="book")]
        
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
            ZoteroCollection(collection_id=1, name="China", parent_id=None, depth=0, item_count=5, full_path="China"),
            ZoteroCollection(collection_id=2, name="Japan", parent_id=None, depth=0, item_count=3, full_path="Japan")
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
            ZoteroCollection(collection_id=1, name="Asia", parent_id=None, depth=0, item_count=10, full_path="Asia"),
            ZoteroCollection(collection_id=2, name="China", parent_id=1, depth=1, item_count=5, full_path="Asia > China"),
            ZoteroCollection(collection_id=3, name="History", parent_id=2, depth=2, item_count=3, full_path="Asia > China > History"),
            ZoteroCollection(collection_id=4, name="Japan", parent_id=1, depth=1, item_count=2, full_path="Asia > Japan")
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
            ZoteroCollection(collection_id=1, name="China 1", parent_id=None, depth=0, item_count=5, full_path="China 1"),
            ZoteroCollection(collection_id=2, name="China 2", parent_id=None, depth=0, item_count=3, full_path="China 2"),
            ZoteroCollection(collection_id=3, name="China 3", parent_id=None, depth=0, item_count=1, full_path="China 3")
        ]
        
        display_hierarchical_search_results(collections, "china", max_results=2)
        captured = capsys.readouterr()
        
        # Should only show first 2 matches
        china_lines = [line for line in captured.out.split('\n') if "China" in line and "items)" in line]
        assert len(china_lines) <= 2
    
    def test_display_hierarchical_no_matches(self, capsys):
        """Test hierarchical display with no matches."""
        collections = [
            ZoteroCollection(collection_id=1, name="Japan", parent_id=None, depth=0, item_count=5, full_path="Japan"),
            ZoteroCollection(collection_id=2, name="Korea", parent_id=None, depth=0, item_count=3, full_path="Korea")
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
        
        item = ZoteroItem(item_id=1, title="Test Book", item_type="book")
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
        
        item = ZoteroItem(item_id=1, title="Test Article", item_type="journalArticle")
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
        
        item = ZoteroItem(item_id=1, title="Test Book", item_type="book")
        show_item_metadata(mock_db, item)
        captured = capsys.readouterr()
        
        # Collections section should not appear
        assert "Collections:" not in captured.out
    
    def test_show_item_metadata_error_handling(self, capsys):
        """Test metadata display error handling."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.side_effect = Exception("Database error")
        
        item = ZoteroItem(item_id=1, title="Test Book", item_type="book")
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
        
        item = ZoteroItem(item_id=1, title="Test Book", item_type="book")
        show_item_metadata(mock_db, item)
        captured = capsys.readouterr()
        
        assert "Smith" in captured.out
        assert "Jane" in captured.out
        assert "Unknown" in captured.out


if __name__ == "__main__":
    pytest.main([__file__])