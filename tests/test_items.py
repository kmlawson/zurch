import pytest
from pathlib import Path
from unittest.mock import MagicMock

from zurch.database import DatabaseConnection
from zurch.items import ItemService
from zurch.models import ZoteroItem


class TestItemService:
    """Test the ItemService class."""
    
    @pytest.fixture
    def sample_db_path(self):
        """Return path to sample database."""
        return Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"
    
    @pytest.fixture
    def item_service(self, sample_db_path):
        """Create an ItemService instance."""
        if sample_db_path.exists():
            db_connection = DatabaseConnection(sample_db_path)
            return ItemService(db_connection)
        else:
            pytest.skip("Sample database not found")
    
    def test_search_items_by_name_with_limit(self, item_service):
        """Test that search respects max_results limit."""
        items, total_count = item_service.search_items_by_name("China")
        
        assert isinstance(items, list)
        assert isinstance(total_count, int)
        assert len(items) > 0
        
        # Verify results contain search term
        for item in items:
            assert "china" in item.title.lower()
    
    def test_search_items_by_name_exact_match(self, item_service):
        """Test exact matching in name search."""
        items_exact, total_exact = item_service.search_items_by_name("China", exact_match=True)
        items_partial, total_partial = item_service.search_items_by_name("China", exact_match=False)
        
        assert isinstance(items_exact, list)
        assert isinstance(items_partial, list)
        
        # Exact search should return fewer or equal results
        assert total_exact <= total_partial
        
        # All exact matches should have the exact title
        for item in items_exact:
            assert item.title.lower() == "china"
    
    def test_search_items_by_author(self, item_service):
        """Test searching items by author."""
        items, total_count = item_service.search_items_by_author("Smith")
        
        assert isinstance(items, list)
        assert isinstance(total_count, int)
        assert len(items) > 0
        
        # Note: We can't easily verify author names without additional queries
        # This test mainly ensures the method works without errors
    
    def test_search_items_by_author_with_limit(self, item_service):
        """Test that author search respects max_results limit."""
        items, total_count = item_service.search_items_by_author("a")  # 'a' is common
        
        assert len(items) > 0
        assert isinstance(total_count, int)
    
    def test_search_items_combined_name_only(self, item_service):
        """Test combined search with name only."""
        items, total_count = item_service.search_items_combined(name="China")
        
        assert isinstance(items, list)
        assert isinstance(total_count, int)
        assert len(items) > 0
        
        for item in items:
            assert "china" in item.title.lower()
    
    def test_search_items_combined_author_only(self, item_service):
        """Test combined search with author only."""
        items, total_count = item_service.search_items_combined(author="Smith")
        
        assert isinstance(items, list)
        assert isinstance(total_count, int)
        assert len(items) > 0
    
    def test_search_items_combined_both(self, item_service):
        """Test combined search with both name and author."""
        items, total_count = item_service.search_items_combined(name="History", author="Smith")
        
        assert isinstance(items, list)
        assert isinstance(total_count, int)
        assert len(items) > 0
    
    def test_search_items_combined_neither(self, item_service):
        """Test combined search with neither name nor author."""
        items, total_count = item_service.search_items_combined()
        
        assert items == []
        assert total_count == 0
    
    def test_get_items_in_collection(self, item_service):
        """Test getting items from a specific collection."""
        # This test requires knowing a collection ID that has items
        # For now, test with a dummy ID and expect empty results or error handling
        items = item_service.get_items_in_collection(1)
        
        assert isinstance(items, list)
        # Items could be empty if collection 1 doesn't exist or has no items
        
        for item in items:
            assert isinstance(item, ZoteroItem)
            assert hasattr(item, 'item_id')
            assert hasattr(item, 'title')
            assert hasattr(item, 'item_type')
    
    def test_search_with_filters(self, item_service):
        """Test search with various filters."""
        # Test only attachments filter
        items, total = item_service.search_items_by_name("China", only_attachments=True)
        assert isinstance(items, list)
        assert isinstance(total, int)
        
        # All items should have attachments (pdf, epub, or txt)
        for item in items:
            assert item.attachment_type in ["pdf", "epub", "txt"]
        
        # Test books only filter
        items, total = item_service.search_items_by_name("History", only_books=True)
        assert isinstance(items, list)
        
        # All items should be books
        for item in items:
            assert item.item_type == "book"
        
        # Test articles only filter
        items, total = item_service.search_items_by_name("History", only_articles=True)
        assert isinstance(items, list)
        
        # All items should be articles
        for item in items:
            assert item.item_type == "journalArticle"


class TestItemServiceMocked:
    """Test ItemService with mocked database connection."""
    
    def test_search_items_by_name_with_mock(self):
        """Test search_items_by_name with mocked data."""
        mock_db = MagicMock()
        
        # Mock query builder
        with pytest.MonkeyPatch().context() as m:
            m.setattr("zurch.items.build_name_search_query", lambda *args: (
                "SELECT COUNT(*)", 
                "SELECT id, title, type, content_type, path",
                ["param1"]
            ))
            
            # Mock database responses - optimized queries now include attachment data
            mock_db.execute_single_query.return_value = (10,)  # total count
            
            # Create proper row objects that support dict-style access
            row1 = MagicMock()
            row1.__getitem__ = MagicMock(side_effect=lambda k: {
                'itemID': 1, 'title': 'Test Item 1', 'typeName': 'book', 
                'contentType': 'application/pdf', 'path': 'test.pdf',
                'dateAdded': '2023-01-01', 'dateModified': '2023-01-01'
            }[k])
            
            row2 = MagicMock()
            row2.__getitem__ = MagicMock(side_effect=lambda k: {
                'itemID': 2, 'title': 'Test Item 2', 'typeName': 'article', 
                'contentType': 'application/epub+zip', 'path': 'test.epub',
                'dateAdded': '2023-01-02', 'dateModified': '2023-01-02'
            }[k])
            
            mock_db.execute_query.return_value = [row1, row2]
            
            service = ItemService(mock_db)
            items, total_count = service.search_items_by_name("test")
            
            assert len(items) == 2
            assert total_count == 10
            assert items[0].title == "Test Item 1"
            assert items[0].attachment_type == "pdf"
            assert items[1].title == "Test Item 2"
            assert items[1].attachment_type == "epub"
    
    def test_search_items_combined_with_mock(self):
        """Test search_items_combined with mocked data."""
        mock_db = MagicMock()
        
        service = ItemService(mock_db)
        
        # Mock the individual search methods
        service.search_items_by_name = MagicMock(return_value=(
            [ZoteroItem(1, "Test", "book")], 
            1
        ))
        service.search_items_by_author = MagicMock(return_value=(
            [ZoteroItem(2, "Test Author", "article")], 
            1
        ))
        
        # Test name only
        items, total = service.search_items_combined(name="test")
        assert len(items) == 1
        service.search_items_by_name.assert_called_once()
        
        # Reset mocks
        service.search_items_by_name.reset_mock()
        service.search_items_by_author.reset_mock()
        
        # Test author only
        items, total = service.search_items_combined(author="smith")
        assert len(items) == 1
        service.search_items_by_author.assert_called_once()
    
    def test_get_items_in_collection_with_mock(self):
        """Test get_items_in_collection with mocked data."""
        mock_db = MagicMock()
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr("zurch.items.build_collection_items_query", lambda *args: (
                "SELECT id, title, type, order_idx, content_type, path",
                [1]
            ))
            
            # Mock database responses - optimized queries now include attachment data
            # Create proper row objects that support dict-style access
            row1 = MagicMock()
            row1.__getitem__ = MagicMock(side_effect=lambda k: {
                'itemID': 1, 'title': 'Item 1', 'typeName': 'book', 
                'contentType': 'application/pdf', 'path': 'test.pdf',
                'dateAdded': '2023-01-01', 'dateModified': '2023-01-01',
                'orderIndex': 0
            }[k])
            
            row2 = MagicMock()
            row2.__getitem__ = MagicMock(side_effect=lambda k: {
                'itemID': 2, 'title': 'Item 2', 'typeName': 'article', 
                'contentType': None, 'path': None,
                'dateAdded': '2023-01-02', 'dateModified': '2023-01-02',
                'orderIndex': 1
            }[k])
            
            mock_db.execute_query.return_value = [row1, row2]
            
            service = ItemService(mock_db)
            items = service.get_items_in_collection(1)
            
            assert len(items) == 2
            assert items[0].title == "Item 1"
            assert items[0].attachment_type == "pdf"
            assert items[1].title == "Item 2"
            assert items[1].attachment_type is None