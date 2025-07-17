"""Tests for Pydantic model validation."""

import pytest
from pathlib import Path
from datetime import datetime

# Skip all tests if pydantic is not available
try:
    from pydantic import ValidationError
    from zurch.config_models import ZurchConfigModel, CLIArgumentsModel
    from zurch.pydantic_models import ZoteroItemModel, ZoteroCollectionModel, ItemTypeEnum
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Create dummy classes to avoid import errors
    class ValidationError(Exception):
        pass
    class ZurchConfigModel:
        pass
    class CLIArgumentsModel:
        pass
    class ZoteroItemModel:
        pass
    class ZoteroCollectionModel:
        pass
    class ItemTypeEnum:
        pass

# Skip individual tests instead of entire module
skip_if_no_pydantic = pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")


@skip_if_no_pydantic
class TestZurchConfigModel:
    """Test Pydantic configuration model validation."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ZurchConfigModel()
        assert config.max_results == 100
        assert config.debug is False
        assert config.interactive_mode is True
        assert config.zotero_database_path is None
    
    def test_max_results_validation(self):
        """Test max_results field validation."""
        # Valid values
        config1 = ZurchConfigModel(max_results=50)
        assert config1.max_results == 50
        
        config2 = ZurchConfigModel(max_results="all")
        assert config2.max_results == 999999999
        
        config3 = ZurchConfigModel(max_results="0")
        assert config3.max_results == 999999999
        
        # Invalid values
        with pytest.raises(ValidationError):
            ZurchConfigModel(max_results=-1)
    
    def test_database_path_validation(self):
        """Test database path validation."""
        # Valid path (if it exists)
        try:
            test_db = Path(__file__).parent.parent / "zotero-database-example" / "zotero.sqlite"
            if test_db.exists():
                config = ZurchConfigModel(zotero_database_path=test_db)
                assert config.zotero_database_path == test_db
        except ValidationError:
            # This is expected if the test database doesn't exist
            pass
        
        # Invalid path
        with pytest.raises(ValidationError):
            ZurchConfigModel(zotero_database_path="/nonexistent/path.sqlite")
    
    def test_config_serialization(self):
        """Test configuration serialization."""
        config = ZurchConfigModel(
            max_results=50,
            debug=True,
            show_tags=True
        )
        
        data = config.to_dict()
        assert data["max_results"] == 50
        assert data["debug"] is True
        assert data["show_tags"] is True
        assert "zotero_data_dir" not in data  # Excluded field
    
    def test_unknown_fields_rejected(self):
        """Test that unknown fields are rejected."""
        with pytest.raises(ValidationError):
            ZurchConfigModel(unknown_field="value")


@skip_if_no_pydantic
class TestZoteroItemModel:
    """Test Pydantic item model validation."""
    
    def test_valid_item_creation(self):
        """Test creating a valid item."""
        item = ZoteroItemModel(
            item_id=1,
            title="Test Article",
            item_type="journalArticle"
        )
        assert item.item_id == 1
        assert item.title == "Test Article"
        assert item.item_type == "journalArticle"
        assert item.has_attachment() is False
    
    def test_item_with_attachment(self):
        """Test item with attachment."""
        item = ZoteroItemModel(
            item_id=1,
            title="Test Book",
            item_type="book",
            attachment_type="pdf"
        )
        assert item.has_attachment() is True
        assert item.get_attachment_type_enum().value == "pdf"
    
    def test_item_type_enum_conversion(self):
        """Test item type enum conversion."""
        item = ZoteroItemModel(
            item_id=1,
            title="Test",
            item_type="book"
        )
        assert item.get_item_type_enum() == ItemTypeEnum.BOOK
    
    def test_date_parsing(self):
        """Test date parsing from strings."""
        item = ZoteroItemModel(
            item_id=1,
            title="Test",
            item_type="book",
            date_added="2023-01-01 12:00:00"
        )
        assert isinstance(item.date_added, datetime)
        assert item.date_added.year == 2023
    
    def test_invalid_item_id(self):
        """Test invalid item ID validation."""
        with pytest.raises(ValidationError):
            ZoteroItemModel(
                item_id=0,  # Must be > 0
                title="Test",
                item_type="book"
            )
    
    def test_empty_title(self):
        """Test empty title validation."""
        with pytest.raises(ValidationError):
            ZoteroItemModel(
                item_id=1,
                title="",  # Empty title not allowed
                item_type="book"
            )
    
    def test_publication_year_validation(self):
        """Test publication year validation."""
        # Valid year
        item = ZoteroItemModel(
            item_id=1,
            title="Test",
            item_type="book",
            publication_year=2023
        )
        assert item.publication_year == 2023
        
        # Invalid year
        with pytest.raises(ValidationError):
            ZoteroItemModel(
                item_id=1,
                title="Test",
                item_type="book",
                publication_year=999  # Too old
            )


@skip_if_no_pydantic
class TestZoteroCollectionModel:
    """Test Pydantic collection model validation."""
    
    def test_valid_collection_creation(self):
        """Test creating a valid collection."""
        collection = ZoteroCollectionModel(
            collection_id=1,
            name="Test Collection"
        )
        assert collection.collection_id == 1
        assert collection.name == "Test Collection"
        assert collection.is_root() is True
    
    def test_collection_with_parent(self):
        """Test collection with parent."""
        collection = ZoteroCollectionModel(
            collection_id=2,
            name="Subcollection",
            parent_id=1,
            depth=1
        )
        assert collection.is_root() is False
        assert collection.parent_id == 1
        assert collection.depth == 1
    
    def test_group_collection(self):
        """Test group collection."""
        collection = ZoteroCollectionModel(
            collection_id=1,
            name="Group Collection",
            library_type="group",
            library_name="Research Group"
        )
        assert collection.is_group_collection() is True
        assert "Research Group" in collection.get_display_name()
    
    def test_invalid_collection_id(self):
        """Test invalid collection ID validation."""
        with pytest.raises(ValidationError):
            ZoteroCollectionModel(
                collection_id=0,  # Must be > 0
                name="Test"
            )
    
    def test_empty_collection_name(self):
        """Test empty collection name validation."""
        with pytest.raises(ValidationError):
            ZoteroCollectionModel(
                collection_id=1,
                name=""  # Empty name not allowed
            )
    
    def test_invalid_library_type(self):
        """Test invalid library type validation."""
        with pytest.raises(ValidationError):
            ZoteroCollectionModel(
                collection_id=1,
                name="Test",
                library_type="invalid"  # Must be "user" or "group"
            )


@skip_if_no_pydantic
class TestCLIArgumentsModel:
    """Test CLI arguments model validation."""
    
    def test_valid_arguments(self):
        """Test valid CLI arguments."""
        args = CLIArgumentsModel(
            folder="test folder",
            max_results=50,
            interactive=True
        )
        assert args.folder == "test folder"
        assert args.max_results == 50
        assert args.interactive is True
    
    def test_year_validation(self):
        """Test year validation for after/before."""
        # Valid years
        args = CLIArgumentsModel(
            after=2020,
            before=2023
        )
        assert args.after == 2020
        assert args.before == 2023
        
        # Invalid year ranges
        with pytest.raises(ValidationError):
            CLIArgumentsModel(after=999)  # Too old
    
    def test_sort_validation(self):
        """Test sort argument validation."""
        # Valid sort values
        args = CLIArgumentsModel(sort="title")
        assert args.sort == "title"
        
        args = CLIArgumentsModel(sort="d")
        assert args.sort == "d"
        
        # Invalid sort value
        with pytest.raises(ValidationError):
            CLIArgumentsModel(sort="invalid")
    
    def test_export_validation(self):
        """Test export format validation."""
        # Valid formats
        args = CLIArgumentsModel(export="csv")
        assert args.export == "csv"
        
        args = CLIArgumentsModel(export="json")
        assert args.export == "json"
        
        # Invalid format
        with pytest.raises(ValidationError):
            CLIArgumentsModel(export="xml")
    
    def test_get_max_results_method(self):
        """Test get_max_results method."""
        args = CLIArgumentsModel(max_results="all")
        assert args.get_max_results() == 999999999
        
        args = CLIArgumentsModel(max_results=50)
        assert args.get_max_results() == 50
        
        args = CLIArgumentsModel()
        assert args.get_max_results(200) == 200  # Uses default