from unittest.mock import patch, MagicMock
from pathlib import Path

from zurch.models import ZoteroItem
from zurch.notes import NotesService


class TestNotesService:
    """Test the NotesService class."""
    
    def test_has_notes_true(self):
        """Test checking if an item has notes when it does."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [{"count": 1}]
        
        notes_service = NotesService(mock_db)
        item = ZoteroItem(1, "Test Item", "book")
        
        result = notes_service.has_notes(item.item_id)
        assert result is True
        
        # Verify the SQL query was called correctly
        mock_db.execute_query.assert_called_once()
        call_args = mock_db.execute_query.call_args
        assert "SELECT COUNT(*) as count" in call_args[0][0]
        assert "parentItemID = ?" in call_args[0][0]
        assert call_args[0][1] == (item.item_id,)
    
    def test_has_notes_false(self):
        """Test checking if an item has notes when it doesn't."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [{"count": 0}]
        
        notes_service = NotesService(mock_db)
        item = ZoteroItem(1, "Test Item", "book")
        
        result = notes_service.has_notes(item.item_id)
        assert result is False
    
    def test_get_notes_content_success(self):
        """Test getting notes content successfully."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [
            {"note": "<p>This is a test note</p>"},
            {"note": "<p>Another note</p>"}
        ]
        
        notes_service = NotesService(mock_db)
        item = ZoteroItem(1, "Test Item", "book")
        
        result = notes_service.get_notes_content(item.item_id)
        assert len(result) == 2
        assert result[0] == "<p>This is a test note</p>"
        assert result[1] == "<p>Another note</p>"
    
    def test_get_notes_content_empty(self):
        """Test getting notes content when there are no notes."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = []
        
        notes_service = NotesService(mock_db)
        item = ZoteroItem(1, "Test Item", "book")
        
        result = notes_service.get_notes_content(item.item_id)
        assert result == []
    
    def test_get_notes_content_html_stripping(self):
        """Test that HTML tags are stripped from notes content."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [
            {"note": "<p>This is a <strong>test</strong> note with <em>formatting</em></p>"}
        ]
        
        notes_service = NotesService(mock_db)
        item = ZoteroItem(1, "Test Item", "book")
        
        result = notes_service.get_notes_content(item.item_id, strip_html=True)
        assert len(result) == 1
        assert result[0] == "This is a test note with formatting"
    
    def test_save_notes_to_file_success(self):
        """Test saving notes to a file successfully."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [
            {"note": "<p>First note</p>"},
            {"note": "<p>Second note</p>"}
        ]
        
        notes_service = NotesService(mock_db)
        item = ZoteroItem(1, "Test Item", "book")
        
        with patch('pathlib.Path.write_text') as mock_write:
            result = notes_service.save_notes_to_file(item.item_id, Path("test_notes.txt"))
            assert result is True
            mock_write.assert_called_once()
            
            # Check the content that was written
            written_content = mock_write.call_args[0][0]
            assert "First note" in written_content
            assert "Second note" in written_content
    
    def test_save_notes_to_file_no_notes(self):
        """Test saving notes to file when there are no notes."""
        mock_db = MagicMock()
        mock_db.execute_query.return_value = []
        
        notes_service = NotesService(mock_db)
        item = ZoteroItem(1, "Test Item", "book")
        
        result = notes_service.save_notes_to_file(item.item_id, Path("test_notes.txt"))
        assert result is False


class TestNotesDisplayIntegration:
    """Test integration of notes display with other components."""
    
    def test_display_items_with_notes_icons(self):
        """Test that items display notes icons when --shownotes is used."""
        from zurch.utils import format_notes_icon
        
        # Test the notes icon formatting
        assert format_notes_icon(True) == "📝 "
        assert format_notes_icon(False) == ""
    
    def test_shownotes_flag_in_search_results(self):
        """Test that --shownotes flag affects search result display."""
        # This would be tested in integration tests with actual search results
        pass
    
    def test_withnotes_filter_functionality(self):
        """Test that --withnotes flag filters to only items with notes."""
        # This would be tested in integration tests with actual filtering
        pass


class TestNotesUtilities:
    """Test utility functions for notes handling."""
    
    def test_sanitize_notes_content(self):
        """Test sanitizing notes content for safe file output."""
        from zurch.notes import sanitize_notes_content
        
        # Test HTML stripping
        html_content = "<p>This is a <strong>test</strong> note</p>"
        result = sanitize_notes_content(html_content)
        assert result == "This is a test note"
        
        # Test script tag removal
        dangerous_content = "<script>alert('xss')</script><p>Safe content</p>"
        result = sanitize_notes_content(dangerous_content)
        assert "alert" not in result
        assert "Safe content" in result
        
        # Test line break normalization
        multiline_content = "<p>Line 1</p><p>Line 2</p>"
        result = sanitize_notes_content(multiline_content)
        assert "Line 1\n\nLine 2" in result
    
    def test_format_notes_for_display(self):
        """Test formatting notes for terminal display."""
        from zurch.notes import format_notes_for_display
        
        notes = ["First note", "Second note with longer content"]
        result = format_notes_for_display(notes)
        
        assert "First note" in result
        assert "Second note with longer content" in result
        assert "---" in result  # Should have separator between notes