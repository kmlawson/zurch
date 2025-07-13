import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

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
            ZoteroCollection(1, "Collection 1", None, 0, 5, "Collection 1"),
            ZoteroCollection(2, "Collection 2", None, 0, 3, "Collection 2")
        ]
        
        mock_input.return_value = "1"
        result = interactive_collection_selection(collections)
        
        assert result == collections[0]
        assert result.name == "Collection 1"
    
    @patch('zurch.interactive.input')
    def test_cancel_selection(self, mock_input):
        """Test canceling selection with 0."""
        collections = [
            ZoteroCollection(1, "Collection 1", None, 0, 5, "Collection 1")
        ]
        
        mock_input.return_value = "0"
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_quit_selection(self, mock_input):
        """Test quitting selection with 'q'."""
        collections = [
            ZoteroCollection(1, "Collection 1", None, 0, 5, "Collection 1")
        ]
        
        mock_input.return_value = "q"
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_invalid_number_then_valid(self, mock_input):
        """Test invalid number followed by valid selection."""
        collections = [
            ZoteroCollection(1, "Collection 1", None, 0, 5, "Collection 1"),
            ZoteroCollection(2, "Collection 2", None, 0, 3, "Collection 2")
        ]
        
        # First invalid number (too high), then valid selection
        mock_input.side_effect = ["999", "1"]
        result = interactive_collection_selection(collections)
        
        assert result == collections[0]
    
    @patch('zurch.interactive.input')
    def test_invalid_input_then_cancel(self, mock_input):
        """Test invalid input followed by cancel."""
        collections = [
            ZoteroCollection(1, "Collection 1", None, 0, 5, "Collection 1")
        ]
        
        mock_input.side_effect = ["invalid", "0"]
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_keyboard_interrupt(self, mock_input):
        """Test handling of KeyboardInterrupt (Ctrl+C)."""
        collections = [
            ZoteroCollection(1, "Collection 1", None, 0, 5, "Collection 1")
        ]
        
        mock_input.side_effect = KeyboardInterrupt()
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    @patch('zurch.interactive.input')
    def test_eof_error(self, mock_input):
        """Test handling of EOFError."""
        collections = [
            ZoteroCollection(1, "Collection 1", None, 0, 5, "Collection 1")
        ]
        
        mock_input.side_effect = EOFError()
        result = interactive_collection_selection(collections)
        
        assert result is None
    
    def test_hierarchical_display(self, capsys):
        """Test hierarchical display of collections."""
        collections = [
            ZoteroCollection(1, "Parent", None, 0, 5, "Parent"),
            ZoteroCollection(2, "Child", 1, 1, 3, "Parent > Child"),
            ZoteroCollection(3, "Grandchild", 2, 2, 1, "Parent > Child > Grandchild"),
            ZoteroCollection(4, "Other", None, 0, 2, "Other")
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
            ZoteroCollection(1, "With Items", None, 0, 5, "With Items"),
            ZoteroCollection(2, "No Items", None, 0, 0, "No Items")
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
                ZoteroCollection(i + 1, f"Collection {i + 1}", None, 0, 1, f"Collection {i + 1}")
            )
        
        mock_input.return_value = "3"  # Select the 3rd collection
        result = interactive_collection_selection(collections)
        
        assert result == collections[2]  # 0-indexed
        assert result.name == "Collection 3"
    
    def test_complex_hierarchy(self, capsys):
        """Test with complex hierarchy structure."""
        collections = [
            ZoteroCollection(1, "Research", None, 0, 10, "Research"),
            ZoteroCollection(2, "History", 1, 1, 8, "Research > History"),
            ZoteroCollection(3, "Ancient", 2, 2, 3, "Research > History > Ancient"),
            ZoteroCollection(4, "Modern", 2, 2, 5, "Research > History > Modern"),
            ZoteroCollection(5, "Science", 1, 1, 2, "Research > Science"),
            ZoteroCollection(6, "Personal", None, 0, 3, "Personal")
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