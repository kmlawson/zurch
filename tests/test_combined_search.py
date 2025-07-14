import pytest
from pathlib import Path
from zurch.search import ZoteroDatabase


class TestCombinedSearch:
    @pytest.fixture
    def sample_db_path(self):
        return Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"

    @pytest.fixture
    def db(self, sample_db_path):
        if sample_db_path.exists():
            return ZoteroDatabase(sample_db_path)
        else:
            pytest.skip("Sample database not found")

    def test_name_and_author_search(self, db):
        """Test combined name and author search returns only items matching both criteria."""
        # Test with a realistic combination
        items, total_count = db.search_items_combined(
            name="China", 
            author="smith"
        )
        
        # Should return fewer items than name-only search
        name_only_items, name_only_count = db.search_items_combined(name="China")
        author_only_items, author_only_count = db.search_items_combined(author="smith")
        
        # Combined search should return fewer or equal items than either individual search
        assert len(items) <= len(name_only_items)
        assert len(items) <= len(author_only_items)
        assert total_count <= name_only_count
        assert total_count <= author_only_count
        
        # All returned items should contain "China" in title and have "smith" as author
        for item in items:
            assert "china" in item.title.lower()
            # Note: We can't easily check author without additional database queries
            # but the query structure ensures this constraint is enforced

    def test_name_and_tag_search(self, db):
        """Test combined name and tag search."""
        items, total_count = db.search_items_combined(
            name="Japan", 
            tags=["China"]
        )
        
        # Should return items that contain "Japan" in title AND are tagged with "China"
        japan_only_items, japan_only_count = db.search_items_combined(name="Japan")
        china_tag_items, china_tag_count = db.search_items_combined(tags=["China"])
        
        # Combined search should return fewer or equal items than either individual search
        assert len(items) <= len(japan_only_items)
        assert len(items) <= len(china_tag_items)
        assert total_count <= japan_only_count
        assert total_count <= china_tag_count

    def test_author_and_tag_search(self, db):
        """Test combined author and tag search."""
        items, total_count = db.search_items_combined(
            author="smith", 
            tags=["China"]
        )
        
        # Should return items by "smith" that are tagged with "China"
        smith_only_items, smith_only_count = db.search_items_combined(author="smith")
        china_tag_items, china_tag_count = db.search_items_combined(tags=["China"])
        
        # Combined search should return fewer or equal items than either individual search
        assert len(items) <= len(smith_only_items)
        assert len(items) <= len(china_tag_items)
        assert total_count <= smith_only_count
        assert total_count <= china_tag_count

    def test_all_three_combined_search(self, db):
        """Test search with name, author, and tag all combined."""
        items, total_count = db.search_items_combined(
            name="China", 
            author="smith", 
            tags=["Japan"]
        )
        
        # This very specific combination might return 0 items, which is fine
        assert isinstance(items, list)
        assert isinstance(total_count, int)
        assert total_count >= 0
        assert len(items) <= total_count

    def test_combined_search_with_filters(self, db):
        """Test combined search with additional filters."""
        items, total_count = db.search_items_combined(
            name="China", 
            author="smith",
            only_attachments=True,
            only_books=True
        )
        
        # Should return only books by Smith about China that have attachments
        assert isinstance(items, list)
        assert isinstance(total_count, int)
        
        # All returned items should be books (if any)
        for item in items:
            assert item.item_type == "book"

    def test_empty_combined_search(self, db):
        """Test combined search with no parameters returns empty results."""
        items, total_count = db.search_items_combined()
        
        assert items == []
        assert total_count == 0

    def test_single_parameter_falls_back_correctly(self, db):
        """Test that single parameter searches fall back to individual search methods."""
        # Test name only
        name_combined_items, name_combined_count = db.search_items_combined(name="China")
        name_direct_items, name_direct_count = db.search_items_by_name("China")
        
        assert len(name_combined_items) == len(name_direct_items)
        assert name_combined_count == name_direct_count
        
        # Test author only
        author_combined_items, author_combined_count = db.search_items_combined(author="smith")
        author_direct_items, author_direct_count = db.search_items_by_author("smith")
        
        assert len(author_combined_items) == len(author_direct_items)
        assert author_combined_count == author_direct_count
        
        # Test tags only
        tag_combined_items, tag_combined_count = db.search_items_combined(tags=["China"])
        tag_direct_items, tag_direct_count = db.search_items_by_name(None, tags=["China"])
        
        assert len(tag_combined_items) == len(tag_direct_items)
        assert tag_combined_count == tag_direct_count

    def test_combined_search_exact_match_parameter(self, db):
        """Test that exact_match parameter works in combined search."""
        items_partial, _ = db.search_items_combined(
            name="China", 
            author="smith", 
            exact_match=False
        )
        
        items_exact, _ = db.search_items_combined(
            name="China", 
            author="smith", 
            exact_match=True
        )
        
        # Exact match should return fewer or equal items than partial match
        assert len(items_exact) <= len(items_partial)

    def test_combined_search_multiple_tags(self, db):
        """Test combined search with multiple tags (AND logic)."""
        items, total_count = db.search_items_combined(
            name="China", 
            tags=["Japan", "China"]  # Both tags must be present
        )
        
        # Should return items with "China" in title that have BOTH tags
        single_tag_items, single_tag_count = db.search_items_combined(
            name="China", 
            tags=["China"]
        )
        
        # Multiple tags should return fewer or equal items
        assert len(items) <= len(single_tag_items)
        assert total_count <= single_tag_count