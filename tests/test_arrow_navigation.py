"""Tests for arrow key navigation functionality."""

from unittest.mock import patch, MagicMock, call
import pytest
from zurch.arrow_navigation import (
    handle_arrow_key_input, arrow_navigation_selection,
    display_items_with_highlight
)
from zurch.models import ZoteroItem


class TestArrowKeyInput:
    """Test arrow key input handling."""
    
    def test_unix_arrow_keys(self):
        """Test Unix/Linux/macOS arrow key sequences."""
        with patch('zurch.arrow_navigation.get_single_char') as mock_get_char:
            # Up arrow: ESC [ A
            mock_get_char.side_effect = ['\x1b', '[', 'A']
            assert handle_arrow_key_input() == 'up'
            
            # Down arrow: ESC [ B
            mock_get_char.side_effect = ['\x1b', '[', 'B']
            assert handle_arrow_key_input() == 'down'
            
            # Right arrow: ESC [ C
            mock_get_char.side_effect = ['\x1b', '[', 'C']
            assert handle_arrow_key_input() == 'right'
            
            # Left arrow: ESC [ D
            mock_get_char.side_effect = ['\x1b', '[', 'D']
            assert handle_arrow_key_input() == 'left'
    
    def test_windows_arrow_keys(self):
        """Test Windows arrow key sequences."""
        with patch('zurch.arrow_navigation.os.name', 'nt'):
            with patch('zurch.arrow_navigation.get_single_char') as mock_get_char:
                # Up arrow: 0xE0 H
                mock_get_char.side_effect = ['\xe0', 'H']
                assert handle_arrow_key_input() == 'up'
                
                # Down arrow: 0xE0 P
                mock_get_char.side_effect = ['\xe0', 'P']
                assert handle_arrow_key_input() == 'down'
                
                # Left arrow: 0xE0 K
                mock_get_char.side_effect = ['\xe0', 'K']
                assert handle_arrow_key_input() == 'left'
                
                # Right arrow: 0xE0 M
                mock_get_char.side_effect = ['\xe0', 'M']
                assert handle_arrow_key_input() == 'right'
    
    def test_vim_keys(self):
        """Test vim-style navigation keys."""
        with patch('zurch.arrow_navigation.get_single_char') as mock_get_char:
            # j for down
            mock_get_char.return_value = 'j'
            assert handle_arrow_key_input() == 'down'
            
            # k for up
            mock_get_char.return_value = 'k'
            assert handle_arrow_key_input() == 'up'
            
            # Capital letters should also work
            mock_get_char.return_value = 'J'
            assert handle_arrow_key_input() == 'down'
            
            mock_get_char.return_value = 'K'
            assert handle_arrow_key_input() == 'up'
    
    def test_standard_keys(self):
        """Test standard key handling."""
        with patch('zurch.arrow_navigation.get_single_char') as mock_get_char:
            # Enter key
            mock_get_char.return_value = '\n'
            assert handle_arrow_key_input() == 'enter'
            
            # Carriage return
            mock_get_char.return_value = '\r'
            assert handle_arrow_key_input() == 'enter'
            
            # Escape key
            mock_get_char.return_value = '\x1b'
            assert handle_arrow_key_input() == 'escape'
            
            # Letter keys
            mock_get_char.return_value = 'g'
            assert handle_arrow_key_input() == 'g'
            
            mock_get_char.return_value = 'l'
            assert handle_arrow_key_input() == 'l'
            
            # Number keys
            mock_get_char.return_value = '0'
            assert handle_arrow_key_input() == '0'
            
            mock_get_char.return_value = '5'
            assert handle_arrow_key_input() == '5'


class TestDisplayWithHighlight:
    """Test the display function with highlighting."""
    
    def test_display_with_highlight(self):
        """Test displaying items with one highlighted."""
        from zurch.constants import Colors
        
        items = [
            ZoteroItem(item_id=1, title="First Item", item_type="book"),
            ZoteroItem(item_id=2, title="Second Item", item_type="journalArticle"),
            ZoteroItem(item_id=3, title="Third Item", item_type="book")
        ]
        
        with patch('builtins.print') as mock_print:
            lines = display_items_with_highlight(items, selected_index=1, 
                                               start_index=0, max_display=3)
            
            # Should have printed 3 lines
            assert lines == 3
            assert mock_print.call_count == 3
            
            # Check that the second item was highlighted
            calls = mock_print.call_args_list
            
            # When colors are supported, check highlighting
            if Colors.BG_BLUE:
                # First item - no highlighting
                assert Colors.BG_BLUE not in calls[0][0][0]
                # Second item - highlighted
                assert Colors.BG_BLUE in calls[1][0][0]
                assert Colors.WHITE in calls[1][0][0]
                # Third item - no highlighting
                assert Colors.BG_BLUE not in calls[2][0][0]
            else:
                # When colors not supported, just check that items were printed
                assert "1. " in calls[0][0][0]
                assert "2. " in calls[1][0][0]
                assert "3. " in calls[2][0][0]


class TestArrowNavigationSelection:
    """Test the arrow navigation selection function."""
    
    def test_basic_navigation(self):
        """Test basic up/down navigation."""
        items = [
            ZoteroItem(item_id=1, title="Item 1", item_type="book"),
            ZoteroItem(item_id=2, title="Item 2", item_type="article"),
            ZoteroItem(item_id=3, title="Item 3", item_type="book")
        ]
        
        with patch('zurch.arrow_navigation.is_terminal_interactive', return_value=True):
            with patch('zurch.arrow_navigation.handle_arrow_key_input') as mock_input:
                with patch('builtins.print'):
                    # Simulate: down, down, enter
                    mock_input.side_effect = ['down', 'down', 'enter']
                    
                    result = arrow_navigation_selection(items, max_display=10)
                    
                    # Should have selected the third item (index 2)
                    assert result[0] == items[2]
                    assert result[1] == False  # Not grabbing
                    assert result[2] == 2  # Index 2
    
    def test_grab_selection(self):
        """Test selecting with grab."""
        items = [
            ZoteroItem(item_id=1, title="Item with PDF", item_type="book", 
                      attachment_type="pdf")
        ]
        
        with patch('zurch.arrow_navigation.is_terminal_interactive', return_value=True):
            with patch('zurch.arrow_navigation.handle_arrow_key_input') as mock_input:
                with patch('builtins.print'):
                    # Simulate pressing 'g'
                    mock_input.return_value = 'g'
                    
                    result = arrow_navigation_selection(items, max_display=10)
                    
                    assert result[0] == items[0]
                    assert result[1] == True  # Should grab
                    assert result[2] == 0
    
    def test_number_jump(self):
        """Test jumping to item by number."""
        items = [
            ZoteroItem(item_id=i, title=f"Item {i}", item_type="book")
            for i in range(1, 11)
        ]
        
        with patch('zurch.arrow_navigation.is_terminal_interactive', return_value=True):
            with patch('zurch.arrow_navigation.handle_arrow_key_input') as mock_input:
                with patch('builtins.print'):
                    # Simulate typing "5" then enter
                    mock_input.side_effect = ['5', 'enter']
                    
                    result = arrow_navigation_selection(items, max_display=10)
                    
                    # Should have selected item 5 (index 4)
                    assert result[0] == items[4]
                    assert result[2] == 4
    
    def test_cancel_selection(self):
        """Test cancelling selection."""
        items = [
            ZoteroItem(item_id=1, title="Item 1", item_type="book")
        ]
        
        with patch('zurch.arrow_navigation.is_terminal_interactive', return_value=True):
            with patch('zurch.arrow_navigation.handle_arrow_key_input') as mock_input:
                with patch('builtins.print'):
                    # Simulate pressing '0'
                    mock_input.return_value = '0'
                    
                    result = arrow_navigation_selection(items, max_display=10)
                    
                    assert result[0] is None
                    assert result[1] == False
                    assert result[2] is None
    
    def test_go_back(self):
        """Test going back with 'l'."""
        items = [
            ZoteroItem(item_id=1, title="Item 1", item_type="book")
        ]
        
        with patch('zurch.arrow_navigation.is_terminal_interactive', return_value=True):
            with patch('zurch.arrow_navigation.handle_arrow_key_input') as mock_input:
                with patch('builtins.print'):
                    # Simulate pressing 'l'
                    mock_input.return_value = 'l'
                    
                    result = arrow_navigation_selection(items, max_display=10, 
                                                      show_go_back=True)
                    
                    assert result[0] == "GO_BACK"
                    assert result[1] == False
                    assert result[2] is None
    
    def test_non_interactive_fallback(self):
        """Test fallback to simple selection when not interactive."""
        items = [
            ZoteroItem(item_id=1, title="Item 1", item_type="book")
        ]
        
        with patch('zurch.arrow_navigation.is_terminal_interactive', return_value=False):
            with patch('zurch.handlers.interactive_selection_simple') as mock_simple:
                mock_simple.return_value = (items[0], False, 0)
                
                result = arrow_navigation_selection(items, max_display=10)
                
                # Should have called the simple selection
                mock_simple.assert_called_once()
                assert result == (items[0], False, 0)