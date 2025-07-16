import pytest
from pathlib import Path
from unittest.mock import MagicMock
import logging

from zurch.database import DatabaseConnection
from zurch.items import ItemService
from zurch.search import ZoteroDatabase
from zurch.models import ZoteroItem

class TestTagSearch:
    @pytest.fixture
    def sample_db_path(self):
        return Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"

    @pytest.fixture
    def db(self, sample_db_path):
        if sample_db_path.exists():
            return ZoteroDatabase(sample_db_path)
        else:
            pytest.skip("Sample database not found")

    @pytest.fixture
    def item_service(self, sample_db_path):
        if sample_db_path.exists():
            db_connection = DatabaseConnection(sample_db_path)
            return ItemService(db_connection)
        else:
            pytest.skip("Sample database not found")

    def test_search_by_single_tag(self, db):
        # Use an existing tag from the sample database
        items, total_count = db.search_items_combined(tags=["History / Military / General"])
        assert len(items) > 0
        assert total_count > 0
        # Further assertions could involve checking if returned items actually have the tag

    def test_search_by_multiple_tags_and_logic(self, db):
        # Use existing tags from the sample database
        items, total_count = db.search_items_combined(tags=["History / Military / General", "Medical / History"])
        assert len(items) > 0
        assert total_count > 0

    def test_search_by_tag_case_insensitivity(self, db):
        items_lower, _ = db.search_items_combined(tags=["history / military / general"])
        items_upper, _ = db.search_items_combined(tags=["HISTORY / MILITARY / GENERAL"])
        assert len(items_lower) == len(items_upper)
        assert set(item.item_id for item in items_lower) == set(item.item_id for item in items_upper)

    def test_search_by_tag_with_folder_filter(self, db):
        # Use an existing folder 'Heritage' with items tagged 'History / Military / General'
        # We have confirmed that no such items exist in the sample database.
        items, total_count = db.get_collection_items("Heritage", tags=["History / Military / General"])
        assert len(items) == 0
        assert total_count == 0

    def test_search_by_nonexistent_tag(self, db):
        items, total_count = db.search_items_combined(tags=["NONEXISTENT_TAG_XYZ123"])
        assert len(items) == 0
        assert total_count == 0

    def test_get_items_in_collection_with_tags(self, item_service):
        # Mock the query builder to control SQL output for testing
        with pytest.MonkeyPatch().context() as m:
            m.setattr("zurch.queries.build_collection_items_query", lambda collection_id, only_attachments, after_year, before_year, only_books, only_articles, tags: (
                "SELECT i.itemID, 'Title', 'book', 0, NULL, NULL FROM items i WHERE i.itemID = ? AND EXISTS (SELECT 1 FROM itemTags it0 JOIN tags t0 ON it0.tagID = t0.tagID WHERE it0.itemID = i.itemID AND LOWER(t0.name) = LOWER(?))",
                [collection_id, tags[0]]
            ))
            mock_db_conn = MagicMock()
            # Create proper row object that supports dict-style access
            row = MagicMock()
            row.__getitem__ = MagicMock(side_effect=lambda k: {
                'itemID': 1, 'title': 'Test Item', 'typeName': 'book', 
                'orderIndex': 0, 'contentType': None, 'path': None,
                'dateAdded': '2023-01-01', 'dateModified': '2023-01-01'
            }[k])
            mock_db_conn.execute_query.return_value = [row]
            item_service.db = mock_db_conn

            items = item_service.get_items_in_collection(1, tags=["testtag"])
            assert len(items) == 1
            assert items[0].title == "Test Item"

    def test_search_items_by_name_with_tags(self, item_service):
        with pytest.MonkeyPatch().context() as m:
            m.setattr("zurch.queries.build_name_search_query", lambda name, exact_match, only_attachments, after_year, before_year, only_books, only_articles, tags: (
                "SELECT COUNT(*) FROM items",
                "SELECT i.itemID, 'Title', 'book', NULL, NULL FROM items i WHERE LOWER(idv.value) LIKE LOWER(?) AND EXISTS (SELECT 1 FROM itemTags it0 JOIN tags t0 ON it0.tagID = t0.tagID WHERE it0.itemID = i.itemID AND LOWER(t0.name) = LOWER(?))",
                ["%test%", tags[0]]
            ))
            mock_db_conn = MagicMock()
            mock_db_conn.execute_single_query.return_value = (1,)
            # Create proper row object that supports dict-style access
            row = MagicMock()
            row.__getitem__ = MagicMock(side_effect=lambda k: {
                'itemID': 1, 'title': 'Test Item', 'typeName': 'book', 
                'contentType': None, 'path': None,
                'dateAdded': '2023-01-01', 'dateModified': '2023-01-01'
            }[k])
            mock_db_conn.execute_query.return_value = [row]
            item_service.db = mock_db_conn

            items, total_count = item_service.search_items_by_name("test", tags=["testtag"])
            assert len(items) == 1
            assert total_count == 1

    def test_search_items_by_author_with_tags(self, item_service):
        with pytest.MonkeyPatch().context() as m:
            m.setattr("zurch.queries.build_author_search_query", lambda author, exact_match, only_attachments, after_year, before_year, only_books, only_articles, tags: (
                "SELECT COUNT(*) FROM items",
                "SELECT i.itemID, 'Title', 'book', NULL, NULL FROM items i WHERE LOWER(c.lastName) LIKE LOWER(?) AND EXISTS (SELECT 1 FROM itemTags it0 JOIN tags t0 ON it0.tagID = t0.tagID WHERE it0.itemID = i.itemID AND LOWER(t0.name) = LOWER(?))",
                ["%test%", tags[0]]
            ))
            mock_db_conn = MagicMock()
            mock_db_conn.execute_single_query.return_value = (1,)
            # Create proper row object that supports dict-style access
            row = MagicMock()
            row.__getitem__ = MagicMock(side_effect=lambda k: {
                'itemID': 1, 'title': 'Test Item', 'typeName': 'book', 
                'contentType': None, 'path': None,
                'dateAdded': '2023-01-01', 'dateModified': '2023-01-01'
            }[k])
            mock_db_conn.execute_query.return_value = [row]
            item_service.db = mock_db_conn

            items, total_count = item_service.search_items_by_author("test", tags=["testtag"])
            assert len(items) == 1
            assert total_count == 1

    def test_search_items_combined_with_tags(self, item_service):
        with pytest.MonkeyPatch().context() as m:
            m.setattr("zurch.items.ItemService.search_items_by_name", MagicMock(return_value=(
                [ZoteroItem(1, "Test", "book")], 1
            )))
            m.setattr("zurch.items.ItemService.search_items_by_author", MagicMock(return_value=(
                [ZoteroItem(2, "Test Author", "article")], 1
            )))

            # Test name and tags
            items, total = item_service.search_items_combined(name="test", tags=["tag1"])
            assert len(items) == 1
            item_service.search_items_by_name.assert_called_once_with(
                "test", False, False, None, None, False, False, ["tag1"]
            )

            item_service.search_items_by_name.reset_mock()
            item_service.search_items_by_author.reset_mock()

            # Test author and tags
            items, total = item_service.search_items_combined(author="test", tags=["tag2"])
            assert len(items) == 1
            item_service.search_items_by_author.assert_called_once_with(
                "test", False, False, None, None, False, False, ["tag2"]
            )

            item_service.search_items_by_name.reset_mock()
            item_service.search_items_by_author.reset_mock()

            # Test name, author, and tags (uses combined query)
            # Mock the database calls needed for combined query
            mock_db = MagicMock()
            mock_db.execute_single_query.return_value = (1,)
            # Create proper row object that supports dict-style access
            row = MagicMock()
            row.__getitem__ = MagicMock(side_effect=lambda k: {
                'itemID': 1, 'title': 'Test Combined', 'typeName': 'book', 
                'contentType': None, 'attachment_path': None,
                'dateAdded': '2023-01-01', 'dateModified': '2023-01-01'
            }[k])
            mock_db.execute_query.return_value = [row]
            item_service.db = mock_db
            
            items, total = item_service.search_items_combined(name="test", author="test", tags=["tag3"])
            assert len(items) == 1
            assert total == 1
            assert items[0].title == "Test Combined"
            # Note: This now uses the combined query, so neither individual method should be called
            item_service.search_items_by_name.assert_not_called()
            item_service.search_items_by_author.assert_not_called()


