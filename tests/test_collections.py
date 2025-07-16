import pytest
from pathlib import Path
from unittest.mock import MagicMock

from zurch.database import DatabaseConnection
from zurch.collections import CollectionService
from zurch.models import ZoteroCollection


class TestCollectionService:
    """Test the CollectionService class."""
    
    @pytest.fixture
    def sample_db_path(self):
        """Return path to sample database."""
        return Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"
    
    @pytest.fixture
    def collection_service(self, sample_db_path):
        """Create a CollectionService instance."""
        if sample_db_path.exists():
            db_connection = DatabaseConnection(sample_db_path)
            return CollectionService(db_connection)
        else:
            pytest.skip("Sample database not found")
    
    def test_list_collections(self, collection_service):
        """Test listing all collections."""
        collections = collection_service.list_collections()
        assert isinstance(collections, list)
        assert len(collections) > 0
        
        # Check that collections have required attributes
        for collection in collections:
            assert isinstance(collection, ZoteroCollection)
            assert hasattr(collection, 'collection_id')
            assert hasattr(collection, 'name')
            assert hasattr(collection, 'depth')
            assert hasattr(collection, 'full_path')
    
    def test_search_collections(self, collection_service):
        """Test searching collections by name."""
        # Search for collections containing 'Heritage'
        results = collection_service.search_collections("Heritage")
        assert isinstance(results, list)
        
        if results:
            # Verify all results contain the search term
            for collection in results:
                assert "heritage" in collection.name.lower()
        
        # Test case insensitive search
        results_upper = collection_service.search_collections("HERITAGE")
        assert len(results_upper) == len(results)
    
    def test_search_collections_empty_result(self, collection_service):
        """Test searching for non-existent collections."""
        results = collection_service.search_collections("NONEXISTENT_COLLECTION_XYZ123")
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_collection_sorting(self, collection_service):
        """Test that search results are sorted correctly."""
        # Get some collections
        all_collections = collection_service.list_collections()
        if len(all_collections) < 2:
            pytest.skip("Need at least 2 collections for sorting test")
        
        # Search for a common term that should return multiple results
        results = collection_service.search_collections("a")  # Most collections should contain 'a'
        
        if len(results) >= 2:
            # Check sorting: depth first, then name
            for i in range(len(results) - 1):
                current = results[i]
                next_item = results[i + 1]
                
                # If depths are the same, names should be alphabetically ordered
                if current.depth == next_item.depth:
                    assert current.name.lower() <= next_item.name.lower()
                else:
                    # Depth should be ascending
                    assert current.depth <= next_item.depth
    
    def test_find_similar_collections(self, collection_service):
        """Test finding similar collections."""
        # First get a real collection name to test with
        all_collections = collection_service.list_collections()
        if not all_collections:
            pytest.skip("No collections found for similarity test")
        
        real_collection = all_collections[0]
        
        # Test finding similar to a partial name
        partial_name = real_collection.name[:5] if len(real_collection.name) > 5 else real_collection.name
        similar = collection_service.find_similar_collections(partial_name, limit=3)
        
        assert isinstance(similar, list)
        assert len(similar) <= 3
        
        # All results should have some similarity (score > 0)
        for collection in similar:
            assert isinstance(collection, ZoteroCollection)
    
    def test_find_similar_collections_no_matches(self, collection_service):
        """Test finding similar collections with no matches."""
        similar = collection_service.find_similar_collections("XYZNOMATCH123")
        assert isinstance(similar, list)
        assert len(similar) == 0
    
    def test_get_collection_item_count(self, collection_service):
        """Test getting item count for a collection."""
        # Get a collection
        collections = collection_service.list_collections()
        if not collections:
            pytest.skip("No collections found for item count test")
        
        collection = collections[0]
        count = collection_service.get_collection_item_count(collection.collection_id)
        
        assert isinstance(count, int)
        assert count >= 0
        # The count should be reasonable (not testing exact match since 
        # collection.item_count may include sub-collection items while 
        # get_collection_item_count returns only direct items)
        assert count <= collection.item_count
    
    def test_get_collection_item_count_nonexistent(self, collection_service):
        """Test getting item count for non-existent collection."""
        count = collection_service.get_collection_item_count(999999)  # Very unlikely to exist
        assert count == 0


class TestCollectionServiceMocked:
    """Test CollectionService with mocked database connection."""
    
    def test_list_collections_with_mock(self):
        """Test list_collections with mocked data."""
        # Create mock row objects that support dict-style access
        row1 = MagicMock()
        row1.__getitem__ = MagicMock(side_effect=lambda k: {
            'collectionID': 1, 'collectionName': "Test Collection", 
            'parentCollectionID': None, 'depth': 0, 'item_count': 5, 'path': "Test Collection",
            'libraryID': 1, 'library_type': 'user', 'library_name': 'Personal Library'
        }[k])
        
        row2 = MagicMock()
        row2.__getitem__ = MagicMock(side_effect=lambda k: {
            'collectionID': 2, 'collectionName': "Sub Collection", 
            'parentCollectionID': 1, 'depth': 1, 'item_count': 3, 'path': "Test Collection > Sub Collection",
            'libraryID': 1, 'library_type': 'user', 'library_name': 'Personal Library'
        }[k])
        
        mock_db = MagicMock()
        mock_db.execute_query.return_value = [row1, row2]
        
        service = CollectionService(mock_db)
        collections = service.list_collections()
        
        assert len(collections) == 2
        assert collections[0].name == "Test Collection"
        assert collections[0].depth == 0
        assert collections[0].item_count == 5
        assert collections[1].name == "Sub Collection"
        assert collections[1].depth == 1
        assert collections[1].parent_id == 1
    
    def test_search_collections_with_mock(self):
        """Test search_collections with mocked data."""
        mock_db = MagicMock()
        
        # Mock list_collections call
        service = CollectionService(mock_db)
        service.list_collections = MagicMock(return_value=[
            ZoteroCollection(1, "Heritage Studies", None, 0, 5, "Heritage Studies"),
            ZoteroCollection(2, "World Heritage", None, 0, 3, "World Heritage"),
            ZoteroCollection(3, "Modern History", None, 0, 2, "Modern History")
        ])
        
        results = service.search_collections("Heritage")
        
        assert len(results) == 2
        assert all("heritage" in c.name.lower() for c in results)
    
    def test_get_collection_item_count_with_mock(self):
        """Test get_collection_item_count with mocked data."""
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(side_effect=lambda k: {'count': 5}[k])
        
        mock_db = MagicMock()
        mock_db.execute_single_query.return_value = mock_row
        
        service = CollectionService(mock_db)
        count = service.get_collection_item_count(1)
        
        assert count == 5
        mock_db.execute_single_query.assert_called_once()