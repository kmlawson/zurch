"""Tests for date filter functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from zurch.date_filters import (
    parse_relative_date, parse_date_range, build_date_filter_clause
)
from zurch.cli import main
from zurch.models import ZoteroItem


class TestParseRelativeDate:
    """Test relative date parsing."""
    
    def test_parse_years(self):
        """Test parsing year formats."""
        result = parse_relative_date("1y")
        assert result is not None
        assert result.year == datetime.now().year - 1
        
        result = parse_relative_date("2 years")
        assert result is not None
        assert result.year == datetime.now().year - 2
        
        result = parse_relative_date("3 year")
        assert result is not None
        assert result.year == datetime.now().year - 3
    
    def test_parse_months(self):
        """Test parsing month formats."""
        result = parse_relative_date("6m")
        assert result is not None
        # Approximate: 6 months = 180 days
        expected_date = datetime.now() - timedelta(days=180)
        assert abs((result - expected_date).days) < 30  # Allow some variance
        
        result = parse_relative_date("12 months")
        assert result is not None
        expected_date = datetime.now() - timedelta(days=360)
        assert abs((result - expected_date).days) < 30
    
    def test_parse_weeks(self):
        """Test parsing week formats."""
        result = parse_relative_date("2w")
        assert result is not None
        expected_date = datetime.now() - timedelta(weeks=2)
        assert abs((result - expected_date).days) <= 1
        
        result = parse_relative_date("4 weeks")
        assert result is not None
        expected_date = datetime.now() - timedelta(weeks=4)
        assert abs((result - expected_date).days) <= 1
    
    def test_parse_days(self):
        """Test parsing day formats."""
        result = parse_relative_date("30d")
        assert result is not None
        expected_date = datetime.now() - timedelta(days=30)
        assert abs((result - expected_date).days) <= 1
        
        result = parse_relative_date("7 days")
        assert result is not None
        expected_date = datetime.now() - timedelta(days=7)
        assert abs((result - expected_date).days) <= 1
    
    def test_parse_invalid(self):
        """Test parsing invalid date strings."""
        assert parse_relative_date("invalid") is None
        assert parse_relative_date("") is None
        assert parse_relative_date("abc123") is None


class TestParseDateRange:
    """Test date range parsing."""
    
    def test_parse_year_range(self):
        """Test parsing year ranges."""
        result = parse_date_range("2020-2023")
        assert result is not None
        start, end = result
        assert start.year == 2020
        assert end.year == 2023
        assert end.month == 12
        assert end.day == 31
    
    def test_parse_different_separators(self):
        """Test different separators."""
        result = parse_date_range("2020 to 2023")
        assert result is not None
        start, end = result
        assert start.year == 2020
        assert end.year == 2023
        
        result = parse_date_range("2020 - 2023")
        assert result is not None
        start, end = result
        assert start.year == 2020
        assert end.year == 2023
    
    def test_parse_invalid_range(self):
        """Test parsing invalid ranges."""
        assert parse_date_range("invalid") is None
        assert parse_date_range("2020") is None
        assert parse_date_range("") is None


class TestBuildDateFilterClause:
    """Test date filter clause building."""
    
    def test_since_filter(self):
        """Test --since filter."""
        clause, params = build_date_filter_clause(
            since="1y",
            date_field_name="idv_date.value"
        )
        assert clause
        assert "CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?" in clause
        assert len(params) == 1
        assert params[0] == datetime.now().year - 1
    
    def test_between_filter(self):
        """Test --between filter."""
        clause, params = build_date_filter_clause(
            between="2020-2023",
            date_field_name="idv_date.value"
        )
        assert clause
        assert "CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) BETWEEN ? AND ?" in clause
        assert len(params) == 2
        assert params[0] == 2020
        assert params[1] == 2023
    
    def test_after_before_filter(self):
        """Test --after and --before filters."""
        clause, params = build_date_filter_clause(
            after=2020,
            before=2023,
            date_field_name="idv_date.value"
        )
        assert clause
        assert "CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?" in clause
        assert "CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) < ?" in clause
        assert len(params) == 2
        assert params[0] == 2020
        assert params[1] == 2023
    
    def test_empty_filter(self):
        """Test empty filter."""
        clause, params = build_date_filter_clause()
        assert clause == ""
        assert params == []


class TestDateFilterValidation:
    """Test date filter validation in CLI."""
    
    @patch('zurch.cli.get_database')
    @patch('zurch.cli.load_config')
    def test_conflicting_since_between(self, mock_load_config, mock_get_database):
        """Test that --since and --between cannot be used together."""
        mock_config = Mock()
        mock_config.interactive_mode = False
        mock_load_config.return_value = mock_config
        
        # Mock sys.argv to simulate command line arguments
        with patch('sys.argv', ['zurch', '--since', '1y', '--between', '2020-2023']):
            result = main()
            assert result == 1  # Should fail with error
    
    @patch('zurch.cli.get_database')
    @patch('zurch.cli.load_config')
    def test_conflicting_after_between(self, mock_load_config, mock_get_database):
        """Test that --after and --between cannot be used together."""
        mock_config = Mock()
        mock_config.interactive_mode = False
        mock_load_config.return_value = mock_config
        
        with patch('sys.argv', ['zurch', '--after', '2020', '--between', '2020-2023']):
            result = main()
            assert result == 1  # Should fail with error
    
    @patch('zurch.cli.get_database')
    @patch('zurch.cli.load_config')
    def test_conflicting_before_since(self, mock_load_config, mock_get_database):
        """Test that --before and --since cannot be used together."""
        mock_config = Mock()
        mock_config.interactive_mode = False
        mock_load_config.return_value = mock_config
        
        with patch('sys.argv', ['zurch', '--before', '2023', '--since', '1y']):
            result = main()
            assert result == 1  # Should fail with error
    
    @patch('zurch.cli.get_database')
    @patch('zurch.cli.load_config')
    def test_compatible_after_before(self, mock_load_config, mock_get_database):
        """Test that --after and --before can be used together."""
        mock_config = Mock()
        mock_config.interactive_mode = False
        mock_load_config.return_value = mock_config
        
        # Mock the database to return successful connection
        mock_db = Mock()
        mock_get_database.return_value = (mock_db, 'success')
        
        # Mock the search to return empty results
        mock_db.search_items_combined.return_value = ([], 0)
        
        with patch('sys.argv', ['zurch', '--after', '2020', '--before', '2023', '--nointeract']):
            result = main()
            # Should not fail with validation error (might fail for other reasons like no results)
            # The key is that it doesn't return 1 immediately due to date filter conflicts
            assert result != 1 or mock_db.search_items_combined.called


class TestStandaloneDateFilters:
    """Test standalone date filter functionality."""
    
    @patch('zurch.cli.get_database')
    @patch('zurch.cli.load_config')
    def test_standalone_since_filter(self, mock_load_config, mock_get_database):
        """Test --since filter without search terms."""
        mock_config = Mock()
        mock_config.interactive_mode = False
        mock_load_config.return_value = mock_config
        
        mock_db = Mock()
        mock_get_database.return_value = (mock_db, 'success')
        
        # Mock successful search with date filter
        mock_db.search_items_combined.return_value = ([
            ZoteroItem(item_id=1, title="Test Item", item_type="article")
        ], 1)
        
        with patch('sys.argv', ['zurch', '--since', '1y', '--nointeract']):
            main()
            assert mock_db.search_items_combined.called
            call_args = mock_db.search_items_combined.call_args
            assert call_args[1]['name'] is None  # No name search
            assert call_args[1]['author'] is None  # No author search
            assert call_args[1]['date_filter_clause']  # Should have date filter
    
    @patch('zurch.cli.get_database')
    @patch('zurch.cli.load_config')
    def test_standalone_between_filter(self, mock_load_config, mock_get_database):
        """Test --between filter without search terms."""
        mock_config = Mock()
        mock_config.interactive_mode = False
        mock_load_config.return_value = mock_config
        
        mock_db = Mock()
        mock_get_database.return_value = (mock_db, 'success')
        
        mock_db.search_items_combined.return_value = ([
            ZoteroItem(item_id=1, title="Test Item", item_type="article")
        ], 1)
        
        with patch('sys.argv', ['zurch', '--between', '2020-2023', '--nointeract']):
            main()
            assert mock_db.search_items_combined.called
            call_args = mock_db.search_items_combined.call_args
            assert call_args[1]['name'] is None
            assert call_args[1]['author'] is None
            assert call_args[1]['date_filter_clause']
    
    @patch('zurch.cli.get_database')
    @patch('zurch.cli.load_config')
    def test_standalone_after_before_filter(self, mock_load_config, mock_get_database):
        """Test --after and --before filters without search terms."""
        mock_config = Mock()
        mock_config.interactive_mode = False
        mock_load_config.return_value = mock_config
        
        mock_db = Mock()
        mock_get_database.return_value = (mock_db, 'success')
        
        mock_db.search_items_combined.return_value = ([
            ZoteroItem(item_id=1, title="Test Item", item_type="article")
        ], 1)
        
        with patch('sys.argv', ['zurch', '--after', '2020', '--before', '2023', '--nointeract']):
            main()
            assert mock_db.search_items_combined.called
            call_args = mock_db.search_items_combined.call_args
            assert call_args[1]['name'] is None
            assert call_args[1]['author'] is None
            assert call_args[1]['date_filter_clause']


class TestBeforeExclusivity:
    """Test that --before is exclusive."""
    
    def test_before_filter_exclusive(self):
        """Test that --before excludes the specified year."""
        clause, params = build_date_filter_clause(
            before=2000,
            date_field_name="idv_date.value"
        )
        assert clause
        assert "CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) < ?" in clause
        assert "< ?" in clause  # Should be < not <=
        assert len(params) == 1
        assert params[0] == 2000
    
    def test_after_filter_inclusive(self):
        """Test that --after is inclusive."""
        clause, params = build_date_filter_clause(
            after=2000,
            date_field_name="idv_date.value"
        )
        assert clause
        assert "CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?" in clause
        assert ">= ?" in clause  # Should be >= (inclusive)
        assert len(params) == 1
        assert params[0] == 2000


if __name__ == "__main__":
    pytest.main([__file__])