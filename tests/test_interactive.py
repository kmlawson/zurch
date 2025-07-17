import pytest
from unittest.mock import patch

from zurch.interactive import interactive_collection_selection
from zurch.models import ZoteroCollection


class TestInteractiveCollectionSelection:
    """Test the interactive collection selection functionality."""
    
    def test_empty_collections_list(self):
        """Test with empty collections list."""
        result = interactive_collection_selection([])
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_valid_selection(self, mock_input):
        """Test valid collection selection."""
        collections = [
            ZoteroCollection(collection_id=1, name="Collection 1", parent_id=None, depth=0, item_count=5, full_path="Collection 1"),
            ZoteroCollection(collection_id=2, name="Collection 2", parent_id=None, depth=0, item_count=3, full_path="Collection 2")
        ]
        
        mock_input.return_value = "1"
        result = interactive_collection_selection(collections)
        
        assert result == collections[0]
        assert result.name == "Collection 1"
    
    @patch('zurch.interactive.input')
    def test_cancel_selection(self, mock_input):
        """Test canceling selection with 0."""
        collections = [
            ZoteroCollection(collection_id=1, name="Collection 1", parent_id=None, depth=0, item_count=5, full_path="Collection 1")
        ]
        
        mock_input.return_value = "0"
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_quit_selection(self, mock_input):
        """Test quitting selection with 'q'."""
        collections = [
            ZoteroCollection(collection_id=1, name="Collection 1", parent_id=None, depth=0, item_count=5, full_path="Collection 1")
        ]
        
        mock_input.return_value = "q"
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_invalid_number_then_valid(self, mock_input):
        """Test invalid number followed by valid selection."""
        collections = [
            ZoteroCollection(collection_id=1, name="Collection 1", parent_id=None, depth=0, item_count=5, full_path="Collection 1"),
            ZoteroCollection(collection_id=2, name="Collection 2", parent_id=None, depth=0, item_count=3, full_path="Collection 2")
        ]
        
        # First invalid number (too high), then valid selection
        mock_input.side_effect = ["999", "1"]
        result = interactive_collection_selection(collections)
        
        assert result == collections[0]
    
    @patch('zurch.interactive.input')
    def test_invalid_input_then_cancel(self, mock_input):
        """Test invalid input followed by cancel."""
        collections = [
            ZoteroCollection(collection_id=1, name="Collection 1", parent_id=None, depth=0, item_count=5, full_path="Collection 1")
        ]
        
        mock_input.side_effect = ["invalid", "0"]
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_keyboard_interrupt(self, mock_input):
        """Test handling of KeyboardInterrupt (Ctrl+C)."""
        collections = [
            ZoteroCollection(collection_id=1, name="Collection 1", parent_id=None, depth=0, item_count=5, full_path="Collection 1")
        ]
        
        mock_input.side_effect = KeyboardInterrupt()
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_eof_error(self, mock_input):
        """Test handling of EOFError."""
        collections = [
            ZoteroCollection(collection_id=1, name="Collection 1", parent_id=None, depth=0, item_count=5, full_path="Collection 1")
        ]
        
        mock_input.side_effect = EOFError()
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    def test_hierarchical_display(self, capsys):
        """Test hierarchical display of collections."""
        collections = [
            ZoteroCollection(collection_id=1, name="Parent", parent_id=None, depth=0, item_count=5, full_path="Parent"),
            ZoteroCollection(collection_id=2, name="Child", parent_id=1, depth=1, item_count=3, full_path="Parent > Child"),
            ZoteroCollection(collection_id=3, name="Grandchild", parent_id=2, depth=2, item_count=1, full_path="Parent > Child > Grandchild"),
            ZoteroCollection(collection_id=4, name="Other", parent_id=None, depth=0, item_count=2, full_path="Other")
        ]
        
        with patch('zurch.interactive.input', side_effect=["0"]):  # Cancel
            interactive_collection_selection(collections)
        
        captured = capsys.readouterr()
        
        # Check that collections are displayed
        assert "Parent" in captured.out
        assert "Child" in captured.out
        assert "Grandchild" in captured.out
        assert "Other" in captured.out
    
    def test_collection_count_display(self, capsys):
        """Test that item counts are displayed correctly."""
        collections = [
            ZoteroCollection(collection_id=1, name="With Items", parent_id=None, depth=0, item_count=5, full_path="With Items"),
            ZoteroCollection(collection_id=2, name="No Items", parent_id=None, depth=0, item_count=0, full_path="No Items")
        ]
        
        with patch('zurch.interactive.input', side_effect=["0"]):  # Cancel
            interactive_collection_selection(collections)
        
        captured = capsys.readouterr()
        
        # Collections with items should show count
        assert "(5 items)" in captured.out
        
        # Collections without items should not show count
        assert "(0 items)" not in captured.out
    
    @patch('zurch.interactive.input')
    def test_large_collection_numbering(self, mock_input):
        """Test proper numbering with many collections."""
        # Create 5 collections to test basic numbering
        collections = []
        for i in range(5):
            collections.append(
                ZoteroCollection(collection_id=i + 1, name=f"Collection {i + 1}", parent_id=None, depth=0, item_count=1, full_path=f"Collection {i + 1}")
            )
        
        mock_input.return_value = "3"  # Select the 3rd collection
        result = interactive_collection_selection(collections)
        
        assert result == collections[2]  # 0-indexed
        assert result.name == "Collection 3"
    
    def test_complex_hierarchy(self, capsys):
        """Test with complex hierarchy structure."""
        collections = [
            ZoteroCollection(collection_id=1, name="Research", parent_id=None, depth=0, item_count=10, full_path="Research"),
            ZoteroCollection(collection_id=2, name="History", parent_id=1, depth=1, item_count=8, full_path="Research > History"),
            ZoteroCollection(collection_id=3, name="Ancient", parent_id=2, depth=2, item_count=3, full_path="Research > History > Ancient"),
            ZoteroCollection(collection_id=4, name="Modern", parent_id=2, depth=2, item_count=5, full_path="Research > History > Modern"),
            ZoteroCollection(collection_id=5, name="Science", parent_id=1, depth=1, item_count=2, full_path="Research > Science"),
            ZoteroCollection(collection_id=6, name="Personal", parent_id=None, depth=0, item_count=3, full_path="Personal")
        ]
        
        with patch('zurch.interactive.input', side_effect=["0"]):  # Cancel
            interactive_collection_selection(collections)
        
        captured = capsys.readouterr()
        
        # Check that all collections are displayed
        assert "Research" in captured.out
        assert "History" in captured.out
        assert "Ancient" in captured.out
        assert "Modern" in captured.out
        assert "Science" in captured.out
        assert "Personal" in captured.out


if __name__ == "__main__":
    pytest.main([__file__])