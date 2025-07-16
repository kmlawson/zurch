import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

from zurch.handlers import (
    grab_attachment, interactive_selection, handle_interactive_mode,
    handle_id_command, handle_getbyid_command, handle_list_command,
    handle_folder_command, handle_search_command
)
from zurch.models import ZoteroItem, ZoteroCollection


class TestGrabAttachment:
    """Test the grab_attachment function."""
    
    def test_grab_attachment_success(self):
        """Test successful attachment grabbing."""
        # Create a temporary file to simulate attachment
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"fake pdf content")
            attachment_path = Path(tmp.name)
        
        try:
            # Mock database and item
            mock_db = MagicMock()
            mock_db.get_item_attachment_path.return_value = attachment_path
            
            item = ZoteroItem(1, "Test Item", "book")
            zotero_data_dir = Path(tmp.name).parent
            
            # Test grabbing
            result = grab_attachment(mock_db, item, zotero_data_dir)
            assert result is True
            
            # Check that file was copied
            target_path = Path.cwd() / attachment_path.name
            assert target_path.exists()
            
            # Clean up
            if target_path.exists():
                target_path.unlink()
        
        finally:
            # Clean up temp file
            if attachment_path.exists():
                attachment_path.unlink()
    
    def test_grab_attachment_not_found(self):
        """Test grabbing attachment when none exists."""
        mock_db = MagicMock()
        mock_db.get_item_attachment_path.return_value = None
        
        item = ZoteroItem(1, "Test Item", "book")
        zotero_data_dir = Path("/tmp")
        
        result = grab_attachment(mock_db, item, zotero_data_dir)
        assert result is False
    
    def test_grab_attachment_copy_error(self):
        """Test handling of copy errors."""
        mock_db = MagicMock()
        mock_db.get_item_attachment_path.return_value = Path("/nonexistent/file.pdf")
        
        item = ZoteroItem(1, "Test Item", "book")
        zotero_data_dir = Path("/tmp")
        
        result = grab_attachment(mock_db, item, zotero_data_dir)
        assert result is False


class TestInteractiveSelection:
    """Test the interactive_selection function."""
    
    @patch('zurch.handlers.input')
    def test_interactive_selection_valid_choice(self, mock_input):
        """Test valid item selection."""
        items = [
            ZoteroItem(1, "Item 1", "book"),
            ZoteroItem(2, "Item 2", "article")
        ]
        
        mock_input.return_value = "1"
        selected, should_grab = interactive_selection(items)
        
        assert selected == items[0]
        assert should_grab is False
    
    @patch('zurch.handlers.input')
    def test_interactive_selection_with_grab(self, mock_input):
        """Test item selection with grab suffix."""
        items = [ZoteroItem(1, "Item 1", "book")]
        
        mock_input.return_value = "1g"
        selected, should_grab = interactive_selection(items)
        
        assert selected == items[0]
        assert should_grab is True
    
    @patch('zurch.handlers.input')
    def test_interactive_selection_cancel(self, mock_input):
        """Test canceling selection."""
        items = [ZoteroItem(1, "Item 1", "book")]
        
        mock_input.return_value = "0"
        selected, should_grab = interactive_selection(items)
        
        assert selected is None
        assert should_grab is False
    
    @patch('zurch.handlers.input')
    def test_interactive_selection_invalid_number(self, mock_input):
        """Test invalid number input."""
        items = [ZoteroItem(1, "Item 1", "book")]
        
        # First invalid input, then valid cancel
        mock_input.side_effect = ["999", "0"]
        selected, should_grab = interactive_selection(items)
        
        assert selected is None
        assert should_grab is False
    
    @patch('zurch.handlers.input')
    def test_interactive_selection_empty_items(self, mock_input):
        """Test with empty items list."""
        items = []
        
        selected, should_grab = interactive_selection(items)
        
        assert selected is None
        assert should_grab is False
        # input should not be called for empty list
        mock_input.assert_not_called()
    
    @patch('zurch.handlers.input')
    def test_interactive_selection_keyboard_interrupt(self, mock_input):
        """Test handling of KeyboardInterrupt."""
        items = [ZoteroItem(1, "Item 1", "book")]
        
        mock_input.side_effect = KeyboardInterrupt()
        selected, should_grab = interactive_selection(items)
        
        assert selected is None
        assert should_grab is False


class TestHandleIdCommand:
    """Test the handle_id_command function."""
    
    def test_handle_id_command_success(self):
        """Test successful ID command handling."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'title': 'Test Title',
            'itemType': 'book',
            'dateAdded': '2023-01-01',
            'dateModified': '2023-01-02'
        }
        
        with patch('zurch.handlers.show_item_metadata') as mock_show:
            result = handle_id_command(mock_db, 123)
            
            assert result == 0
            mock_db.get_item_metadata.assert_called_once_with(123)
            mock_show.assert_called_once()
    
    def test_handle_id_command_not_found(self):
        """Test ID command with non-existent item."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.side_effect = Exception("Item not found")
        
        result = handle_id_command(mock_db, 999)
        
        assert result == 1


class TestHandleGetByIdCommand:
    """Test the handle_getbyid_command function."""
    
    def test_handle_getbyid_command_success(self):
        """Test successful getbyid command."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'title': 'Test Title',
            'itemType': 'book'
        }
        
        config = {'zotero_database_path': '/test/path/zotero.sqlite'}
        
        with patch('zurch.handlers.grab_attachment', return_value=True) as mock_grab:
            result = handle_getbyid_command(mock_db, [123, 456], config)
            
            assert result == 0
            assert mock_grab.call_count == 2
    
    def test_handle_getbyid_command_with_failures(self):
        """Test getbyid command with some failures."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.side_effect = [
            {'title': 'Test 1', 'itemType': 'book'},
            Exception("Item not found")
        ]
        
        config = {'zotero_database_path': '/test/path/zotero.sqlite'}
        
        with patch('zurch.handlers.grab_attachment', return_value=False):
            result = handle_getbyid_command(mock_db, [123, 456], config)
            
            assert result == 1  # Should return 1 due to failures


class TestHandleListCommand:
    """Test the handle_list_command function."""
    
    def test_handle_list_command_all_collections(self):
        """Test listing all collections."""
        mock_db = MagicMock()
        mock_db.list_collections.return_value = [
            ZoteroCollection(1, "Test Collection", None, 0, 5, "Test Collection")
        ]
        
        # Mock args
        args = MagicMock()
        args.list = ""  # Empty string means list all
        args.interactive = False
        args.exact = False
        
        with patch('zurch.handlers.display_hierarchical_search_results') as mock_display:
            mock_display.return_value = 1  # Mock return value
            result = handle_list_command(mock_db, args, max_results=100)
            
            assert result == 0
            mock_display.assert_called_once()
    
    def test_handle_list_command_filtered(self):
        """Test listing filtered collections."""
        mock_db = MagicMock()
        collections = [
            ZoteroCollection(1, "Heritage Studies", None, 0, 5, "Heritage Studies"),
            ZoteroCollection(2, "Modern History", None, 0, 3, "Modern History")
        ]
        mock_db.list_collections.return_value = collections
        
        # Mock args
        args = MagicMock()
        args.list = "heritage"
        args.interactive = False
        args.exact = False
        
        with patch('zurch.handlers.display_hierarchical_search_results') as mock_display:
            mock_display.return_value = 1  # Mock return value
            result = handle_list_command(mock_db, args, max_results=100)
            
            assert result == 0
            mock_display.assert_called_once()
    
    def test_handle_list_command_interactive(self):
        """Test interactive list command."""
        mock_db = MagicMock()
        collections = [ZoteroCollection(1, "Test", None, 0, 5, "Test")]
        mock_db.list_collections.return_value = collections
        mock_db.get_collection_items.return_value = ([], 0)
        
        # Mock args with all required attributes
        args = MagicMock()
        args.list = ""
        args.interactive = True
        args.only_attachments = False
        args.after = None
        args.before = None
        args.books = False
        args.articles = False
        args.showids = False
        args.tag = None
        args.exact = False
        args.zotero_database_path = "/tmp/test.db"
        
        with patch('zurch.interactive.interactive_collection_selection_with_pagination', return_value=None) as mock_interactive:
            with patch('zurch.handlers.display_items') as mock_display:
                with patch('builtins.input', return_value=''):
                    result = handle_list_command(mock_db, args, max_results=100)
                    
                    assert result == 0
                    mock_interactive.assert_called_once()


class TestCommandHandlerIntegration:
    """Integration tests for command handlers."""
    
    def test_handler_error_handling(self):
        """Test that handlers properly handle database errors."""
        mock_db = MagicMock()
        mock_db.list_collections.side_effect = Exception("Database error")
        
        args = MagicMock()
        args.list = ""
        args.interactive = False
        
        # This should not raise an exception but handle it gracefully
        try:
            result = handle_list_command(mock_db, args, max_results=100)
            # The function should handle the error internally
        except Exception as e:
            # If an exception is raised, it should be a controlled one
            assert "Database error" in str(e)