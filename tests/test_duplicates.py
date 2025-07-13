import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from zurch.duplicates import (
    DuplicateKey, extract_year_from_date, get_authors_from_metadata,
    create_duplicate_key, select_best_duplicate, deduplicate_items,
    deduplicate_grouped_items
)
from zurch.models import ZoteroItem, ZoteroCollection


class TestDuplicateKey:
    """Test the DuplicateKey dataclass."""
    
    def test_duplicate_key_equality(self):
        """Test duplicate key equality comparison."""
        key1 = DuplicateKey("Test Title", "John Smith", "2023")
        key2 = DuplicateKey("test title", "john smith", "2023")
        key3 = DuplicateKey("Different Title", "John Smith", "2023")
        
        assert key1 == key2  # Case insensitive
        assert key1 != key3  # Different title
        assert hash(key1) == hash(key2)  # Same hash for equal keys
    
    def test_duplicate_key_with_none_year(self):
        """Test duplicate key with None year."""
        key1 = DuplicateKey("Test Title", "John Smith", None)
        key2 = DuplicateKey("Test Title", "John Smith", None)
        key3 = DuplicateKey("Test Title", "John Smith", "2023")
        
        assert key1 == key2
        assert key1 != key3


class TestExtractYearFromDate:
    """Test year extraction from date strings."""
    
    def test_extract_year_four_digit(self):
        """Test extracting 4-digit years."""
        assert extract_year_from_date("2023-01-01") == "2023"
        assert extract_year_from_date("1995-12-31") == "1995"
        assert extract_year_from_date("January 2020") == "2020"
        assert extract_year_from_date("2019") == "2019"
    
    def test_extract_year_from_complex_dates(self):
        """Test extracting years from complex date formats."""
        assert extract_year_from_date("Published in 2021") == "2021"
        assert extract_year_from_date("Circa 1990s") is None  # Fixed expectation
        assert extract_year_from_date("2022-03-15T10:30:00Z") == "2022"
    
    def test_extract_year_no_match(self):
        """Test cases where no year is found."""
        assert extract_year_from_date("No year here") is None
        assert extract_year_from_date("1885") is None  # Too old
        assert extract_year_from_date("") is None
        assert extract_year_from_date(None) is None
    
    def test_extract_year_multiple_matches(self):
        """Test when multiple years are present - should get the first valid one."""
        assert extract_year_from_date("From 1995 to 2020") == "1995"


class TestGetAuthorsFromMetadata:
    """Test author extraction from metadata."""
    
    def test_get_authors_simple(self):
        """Test simple author extraction."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'creators': [
                {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Smith'},
                {'creatorType': 'author', 'firstName': 'Jane', 'lastName': 'Doe'}
            ]
        }
        
        result = get_authors_from_metadata(mock_db, 123)
        assert result == "Doe Jane; Smith John"  # Sorted alphabetically
    
    def test_get_authors_mixed_creators(self):
        """Test with mixed creator types."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'creators': [
                {'creatorType': 'author', 'firstName': 'John', 'lastName': 'Smith'},
                {'creatorType': 'editor', 'firstName': 'Jane', 'lastName': 'Doe'},
                {'creatorType': 'author', 'lastName': 'Wilson'}  # No first name
            ]
        }
        
        result = get_authors_from_metadata(mock_db, 123)
        assert result == "Smith John; Wilson"  # Only authors, sorted
    
    def test_get_authors_no_creators(self):
        """Test with no creators."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {}
        
        result = get_authors_from_metadata(mock_db, 123)
        assert result == ""
    
    def test_get_authors_error_handling(self):
        """Test error handling in author extraction."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.side_effect = Exception("Database error")
        
        result = get_authors_from_metadata(mock_db, 123)
        assert result == ""


class TestCreateDuplicateKey:
    """Test duplicate key creation."""
    
    def test_create_duplicate_key(self):
        """Test creating a duplicate key for an item."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'creators': [{'creatorType': 'author', 'firstName': 'John', 'lastName': 'Smith'}],
            'date': '2023-01-01'
        }
        
        item = ZoteroItem(1, "Test Title", "book")
        key = create_duplicate_key(mock_db, item)
        
        assert key.title == "test title"
        assert key.authors == "smith john"
        assert key.year == "2023"
    
    def test_create_duplicate_key_error_handling(self):
        """Test error handling when creating duplicate key."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.side_effect = Exception("Error")
        
        item = ZoteroItem(1, "Test Title", "book")
        key = create_duplicate_key(mock_db, item)
        
        assert key.title == "test title"
        assert key.authors == ""  # Error fallback
        assert key.year is None


class TestSelectBestDuplicate:
    """Test duplicate selection logic."""
    
    def test_select_best_single_item(self):
        """Test selection with single item."""
        mock_db = MagicMock()
        item = ZoteroItem(1, "Test", "book")
        
        result = select_best_duplicate(mock_db, [item])
        assert result == item
    
    def test_select_best_prefer_attachment(self):
        """Test preferring items with attachments."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'dateModified': '2023-01-01',
            'dateAdded': '2023-01-01'
        }
        
        item_no_attach = ZoteroItem(1, "Test", "book", None)
        item_with_pdf = ZoteroItem(2, "Test", "book", "pdf")
        
        result = select_best_duplicate(mock_db, [item_no_attach, item_with_pdf])
        assert result == item_with_pdf
    
    def test_select_best_prefer_recent_modification(self):
        """Test preferring more recently modified items."""
        mock_db = MagicMock()
        
        def mock_metadata(item_id):
            if item_id == 1:
                return {'dateModified': '2023-01-01', 'dateAdded': '2023-01-01'}
            else:
                return {'dateModified': '2023-12-31', 'dateAdded': '2023-01-01'}
        
        mock_db.get_item_metadata.side_effect = mock_metadata
        
        item_old = ZoteroItem(1, "Test", "book", "pdf")
        item_new = ZoteroItem(2, "Test", "book", "pdf")
        
        result = select_best_duplicate(mock_db, [item_old, item_new])
        assert result == item_new


class TestDeduplicateItems:
    """Test item deduplication."""
    
    def test_deduplicate_no_duplicates(self):
        """Test deduplication with no actual duplicates."""
        mock_db = MagicMock()
        
        with patch('zurch.duplicates.create_duplicate_key') as mock_create_key:
            mock_create_key.side_effect = [
                DuplicateKey("Title 1", "Author 1", "2023"),
                DuplicateKey("Title 2", "Author 2", "2023")
            ]
            
            items = [
                ZoteroItem(1, "Title 1", "book"),
                ZoteroItem(2, "Title 2", "book")
            ]
            
            result, removed_count = deduplicate_items(mock_db, items)
            
            assert len(result) == 2
            assert removed_count == 0
    
    def test_deduplicate_with_duplicates(self):
        """Test deduplication with actual duplicates."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'dateModified': '2023-01-01',
            'dateAdded': '2023-01-01'
        }
        
        with patch('zurch.duplicates.create_duplicate_key') as mock_create_key:
            # Same key for both items (duplicates)
            duplicate_key = DuplicateKey("Same Title", "Same Author", "2023")
            mock_create_key.return_value = duplicate_key
            
            items = [
                ZoteroItem(1, "Same Title", "book", None),
                ZoteroItem(2, "Same Title", "book", "pdf")  # Has attachment, should be preferred
            ]
            
            result, removed_count = deduplicate_items(mock_db, items)
            
            assert len(result) == 1
            assert removed_count == 1
            assert result[0].item_id == 2  # PDF attachment preferred
    
    def test_deduplicate_debug_mode(self):
        """Test deduplication in debug mode (includes marked duplicates)."""
        mock_db = MagicMock()
        mock_db.get_item_metadata.return_value = {
            'dateModified': '2023-01-01',
            'dateAdded': '2023-01-01'
        }
        
        with patch('zurch.duplicates.create_duplicate_key') as mock_create_key:
            duplicate_key = DuplicateKey("Same Title", "Same Author", "2023")
            mock_create_key.return_value = duplicate_key
            
            items = [
                ZoteroItem(1, "Same Title", "book", None),
                ZoteroItem(2, "Same Title", "book", "pdf")
            ]
            
            result, removed_count = deduplicate_items(mock_db, items, debug_mode=True)
            
            # Should have 2 items: 1 best + 1 marked duplicate
            assert len(result) == 2
            assert removed_count == 1
            
            # Check that one is marked as duplicate
            duplicates = [item for item in result if item.is_duplicate]
            non_duplicates = [item for item in result if not item.is_duplicate]
            
            assert len(duplicates) == 1
            assert len(non_duplicates) == 1
            assert non_duplicates[0].item_id == 2  # PDF preferred
    
    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list."""
        mock_db = MagicMock()
        
        result, removed_count = deduplicate_items(mock_db, [])
        
        assert result == []
        assert removed_count == 0


class TestDeduplicateGroupedItems:
    """Test grouped item deduplication."""
    
    def test_deduplicate_grouped_items(self):
        """Test deduplicating grouped items."""
        mock_db = MagicMock()
        
        collection1 = ZoteroCollection(1, "Collection 1", None, 0, 2, "Collection 1")
        collection2 = ZoteroCollection(2, "Collection 2", None, 0, 1, "Collection 2")
        
        items1 = [ZoteroItem(1, "Item 1", "book"), ZoteroItem(2, "Item 2", "book")]
        items2 = [ZoteroItem(3, "Item 3", "book")]
        
        grouped_items = [(collection1, items1), (collection2, items2)]
        
        with patch('zurch.duplicates.deduplicate_items') as mock_dedupe:
            mock_dedupe.side_effect = [
                (items1, 0),  # No duplicates in first group
                (items2, 0)   # No duplicates in second group
            ]
            
            result, total_removed = deduplicate_grouped_items(mock_db, grouped_items)
            
            assert len(result) == 2
            assert total_removed == 0
            assert result[0][0] == collection1
            assert result[1][0] == collection2
    
    def test_deduplicate_grouped_items_empty(self):
        """Test deduplicating empty grouped items."""
        mock_db = MagicMock()
        
        result, total_removed = deduplicate_grouped_items(mock_db, [])
        
        assert result == []
        assert total_removed == 0


if __name__ == "__main__":
    pytest.main([__file__])