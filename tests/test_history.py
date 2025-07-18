"""Tests for history functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from zurch.history import SearchHistory
from zurch.history_handlers import (
    handle_history_command, handle_save_search_command, 
    handle_load_search_command, record_search_in_history
)
from zurch.date_filters import (
    parse_relative_date, parse_date_range, build_date_filter_clause
)


class TestSearchHistory:
    """Test the SearchHistory class."""
    
    def test_init(self):
        """Test SearchHistory initialization."""
        history = SearchHistory(enabled=True, max_items=50)
        assert history.enabled is True
        assert history.max_items == 50
    
    def test_disabled_history(self):
        """Test that disabled history doesn't save anything."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('zurch.history.get_config_dir', return_value=Path(tmpdir)):
                history = SearchHistory(enabled=False, max_items=10)
                
                # Try to add to history
                history.add_to_history("name", {"name": "test"}, 5)
                
                # Should be empty
                entries = history.get_history()
                assert len(entries) == 0
    
    def test_add_and_get_history(self):
        """Test adding and retrieving history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('zurch.history.get_config_dir', return_value=Path(tmpdir)):
                history = SearchHistory(enabled=True, max_items=10)
                
                # Add some entries
                history.add_to_history("name", {"name": "test1"}, 5)
                history.add_to_history("author", {"author": "Smith"}, 3)
                
                # Get history
                entries = history.get_history()
                assert len(entries) == 2
                
                # Most recent should be first
                assert entries[0]["command"] == "author"
                assert entries[0]["args"]["author"] == "Smith"
                assert entries[0]["results_count"] == 3
                
                assert entries[1]["command"] == "name"
                assert entries[1]["args"]["name"] == "test1"
                assert entries[1]["results_count"] == 5
    
    def test_max_items_limit(self):
        """Test that history respects max_items limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('zurch.history.get_config_dir', return_value=Path(tmpdir)):
                history = SearchHistory(enabled=True, max_items=3)
                
                # Add 5 entries
                for i in range(5):
                    history.add_to_history("name", {"name": f"test{i}"}, i)
                
                # Should only have 3 entries
                entries = history.get_history()
                assert len(entries) == 3
                
                # Should be the most recent ones
                assert entries[0]["args"]["name"] == "test4"
                assert entries[1]["args"]["name"] == "test3"
                assert entries[2]["args"]["name"] == "test2"
    
    def test_save_and_load_search(self):
        """Test saving and loading searches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('zurch.history.get_config_dir', return_value=Path(tmpdir)):
                history = SearchHistory(enabled=True, max_items=10)
                
                # Save a search
                args = {"name": "test search", "exact": True}
                result = history.save_search("my_search", "name", args)
                assert result is True
                
                # Load it back
                loaded = history.load_search("my_search")
                assert loaded is not None
                assert loaded["name"] == "my_search"
                assert loaded["command"] == "name"
                assert loaded["args"]["name"] == "test search"
                assert loaded["args"]["exact"] is True
    
    def test_list_saved_searches(self):
        """Test listing saved searches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('zurch.history.get_config_dir', return_value=Path(tmpdir)):
                history = SearchHistory(enabled=True, max_items=10)
                
                # Save multiple searches
                history.save_search("search1", "name", {"name": "test1"})
                history.save_search("search2", "author", {"author": "Smith"})
                
                # List them
                searches = history.list_saved_searches()
                assert len(searches) == 2
                
                names = [s["name"] for s in searches]
                assert "search1" in names
                assert "search2" in names
    
    def test_delete_saved_search(self):
        """Test deleting saved searches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('zurch.history.get_config_dir', return_value=Path(tmpdir)):
                history = SearchHistory(enabled=True, max_items=10)
                
                # Save a search
                history.save_search("to_delete", "name", {"name": "test"})
                
                # Verify it exists
                searches = history.list_saved_searches()
                assert len(searches) == 1
                
                # Delete it
                result = history.delete_saved_search("to_delete")
                assert result is True
                
                # Verify it's gone
                searches = history.list_saved_searches()
                assert len(searches) == 0
                
                # Try to delete non-existent
                result = history.delete_saved_search("not_exist")
                assert result is False


class TestDateFilters:
    """Test date filtering functionality."""
    
    def test_parse_relative_date(self):
        """Test parsing relative dates."""
        # Test months
        result = parse_relative_date("3m")
        assert result is not None
        
        result = parse_relative_date("6 months")
        assert result is not None
        
        # Test years
        result = parse_relative_date("1y")
        assert result is not None
        
        result = parse_relative_date("2 years")
        assert result is not None
        
        # Test weeks
        result = parse_relative_date("2w")
        assert result is not None
        
        result = parse_relative_date("3 weeks")
        assert result is not None
        
        # Test days
        result = parse_relative_date("30d")
        assert result is not None
        
        result = parse_relative_date("7 days")
        assert result is not None
        
        # Test absolute dates
        result = parse_relative_date("2023")
        assert result is not None
        assert result.year == 2023
        
        result = parse_relative_date("2023-01-15")
        assert result is not None
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15
        
        # Test invalid
        result = parse_relative_date("invalid")
        assert result is None
    
    def test_parse_date_range(self):
        """Test parsing date ranges."""
        # Test year range
        result = parse_date_range("2020-2023")
        assert result is not None
        start, end = result
        assert start.year == 2020
        assert end.year == 2023
        
        # Test with 'to'
        result = parse_date_range("2020 to 2023")
        assert result is not None
        start, end = result
        assert start.year == 2020
        assert end.year == 2023
        
        # Test with dots
        result = parse_date_range("2020..2023")
        assert result is not None
        start, end = result
        assert start.year == 2020
        assert end.year == 2023
        
        # Test invalid
        result = parse_date_range("invalid")
        assert result is None
        
        result = parse_date_range("2020")  # Single date, not range
        assert result is None
    
    def test_build_date_filter_clause(self):
        """Test building SQL date filter clauses."""
        # Test --since
        clause, params = build_date_filter_clause(since="1y")
        assert clause
        assert len(params) == 1
        assert isinstance(params[0], int)
        
        # Test --between
        clause, params = build_date_filter_clause(between="2020-2023")
        assert clause
        assert len(params) == 2
        assert params[0] == 2020
        assert params[1] == 2023
        
        # Test --after and --before
        clause, params = build_date_filter_clause(after=2020, before=2023)
        assert clause
        assert len(params) == 2
        assert params[0] == 2020
        assert params[1] == 2023
        
        # Test no filters
        clause, params = build_date_filter_clause()
        assert clause == ""
        assert len(params) == 0


class TestHistoryHandlers:
    """Test history handler functions."""
    
    @patch('zurch.history_handlers.SearchHistory')
    def test_handle_history_command(self, mock_history_class):
        """Test history command handler."""
        mock_history = Mock()
        mock_history.get_history.return_value = [
            {
                "timestamp": "2023-01-15T10:30:00",
                "command": "name",
                "args": {"name": "test"},
                "results_count": 5
            }
        ]
        mock_history_class.return_value = mock_history
        
        config = {"history_enabled": True, "history_max_items": 100}
        
        # Test successful history display (non-interactive)
        result = handle_history_command(config, limit=10, interactive=False)
        assert result == 0
        
        mock_history.get_history.assert_called_once_with(10)
    
    @patch('zurch.history_handlers.SearchHistory')
    def test_handle_save_search_command(self, mock_history_class):
        """Test save search command handler."""
        mock_history = Mock()
        mock_history.save_search.return_value = True
        mock_history_class.return_value = mock_history
        
        config = {"history_enabled": True, "history_max_items": 100}
        args = {"name": "test"}
        
        result = handle_save_search_command("my_search", "name", args, config)
        assert result == 0
        
        mock_history.save_search.assert_called_once_with("my_search", "name", args)
    
    @patch('zurch.history_handlers.SearchHistory')
    def test_handle_load_search_command(self, mock_history_class):
        """Test load search command handler."""
        mock_history = Mock()
        mock_history.load_search.return_value = {
            "name": "my_search",
            "command": "name",
            "args": {"name": "test"}
        }
        mock_history_class.return_value = mock_history
        
        config = {"history_enabled": True, "history_max_items": 100}
        
        result = handle_load_search_command("my_search", config)
        assert result == {"name": "test"}
        
        mock_history.load_search.assert_called_once_with("my_search")
    
    @patch('zurch.history_handlers.SearchHistory')
    def test_record_search_in_history(self, mock_history_class):
        """Test recording search in history."""
        mock_history = Mock()
        mock_history_class.return_value = mock_history
        
        config = {"history_enabled": True, "history_max_items": 100}
        args = {"name": "test", "exact": True}
        
        record_search_in_history("name", args, 5, config)
        
        mock_history.add_to_history.assert_called_once_with("name", args, 5)
    
    @patch('zurch.history_handlers.SearchHistory')
    def test_record_search_disabled(self, mock_history_class):
        """Test that recording doesn't happen when disabled."""
        mock_history = Mock()
        mock_history_class.return_value = mock_history
        
        config = {"history_enabled": False, "history_max_items": 100}
        args = {"name": "test"}
        
        record_search_in_history("name", args, 5, config)
        
        # Should not be called when disabled
        mock_history_class.assert_not_called()