# Zotero CLI Development Notes

## Zotero Version Compatibility

### Current Status (2024)
- **Target Version**: Zotero 7.0 (latest stable)
- **Database Format**: SQLite 
- **Schema Stability**: Schema can change between major versions
- **API Availability**: Web API recommended over direct database access

### Zotero 7.0 Considerations
- Latest version with potential schema updates
- Database migration from 5.0 moved data from profile directory to home directory
- Corruption protection includes automatic backups
- Read-only access remains the recommended approach

## Database Access Strategy

### Read-Only Access Requirements
```python
# Always use read-only connections
import sqlite3
conn = sqlite3.connect('file:path/to/zotero.sqlite?mode=ro', uri=True)
```

### Critical Safety Measures
1. **Never modify the database** - Corruption risk, breaks sync
2. **Handle locked databases** - Zotero may be running
3. **Version compatibility** - Check schema version
4. **Backup considerations** - Work with copies for development

### Database Location Discovery
```python
# Platform-specific paths for Zotero 7.0
# Windows: %USERPROFILE%\Zotero\zotero.sqlite
# macOS: ~/Zotero/zotero.sqlite  
# Linux: ~/Zotero/zotero.sqlite
```

## Core Data Model

### Entity-Attribute-Value (EAV) Structure
Zotero uses EAV to handle variable metadata fields across different item types:

```sql
-- Core relationship
items → itemData → itemDataValues
      → fields
```

### Key Tables for CLI Operations

#### Items and Collections
```sql
-- Get items in a collection with hierarchy
SELECT 
    c.collectionName,
    c.parentCollectionID,
    i.itemID,
    it.typeName,
    title.value as title
FROM collections c
LEFT JOIN collectionItems ci ON c.collectionID = ci.collectionID
LEFT JOIN items i ON ci.itemID = i.itemID  
LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
LEFT JOIN (
    SELECT itemID, value 
    FROM itemData id 
    JOIN itemDataValues idv ON id.valueID = idv.valueID 
    WHERE fieldID = 1  -- title field
) title ON i.itemID = title.itemID
WHERE c.collectionName LIKE ?
ORDER BY c.parentCollectionID, ci.orderIndex;
```

#### Attachment Detection
```sql
-- Get items with attachments for icon display
SELECT 
    i.itemID,
    ia.contentType,
    CASE 
        WHEN ia.contentType = 'application/pdf' THEN 'pdf'
        WHEN ia.contentType = 'application/epub+zip' THEN 'epub'
        WHEN ia.contentType LIKE 'text/%' THEN 'txt'
        ELSE NULL
    END as attachment_type
FROM items i
LEFT JOIN itemAttachments ia ON i.itemID = ia.parentItemID;
```

## CLI Feature Implementation

### Collection Hierarchy (-l/--list)
```sql
WITH RECURSIVE collection_tree AS (
    -- Root collections
    SELECT 
        collectionID, 
        collectionName, 
        parentCollectionID, 
        0 as depth,
        collectionName as path
    FROM collections 
    WHERE parentCollectionID IS NULL
    
    UNION ALL
    
    -- Child collections  
    SELECT 
        c.collectionID,
        c.collectionName,
        c.parentCollectionID,
        ct.depth + 1,
        ct.path || ' > ' || c.collectionName
    FROM collections c
    JOIN collection_tree ct ON c.parentCollectionID = ct.collectionID
)
SELECT collectionID, collectionName, depth, path
FROM collection_tree 
ORDER BY path;
```

### Folder Search (-f/--folder)
- Handle multiple folders with same name
- Sort by depth (least deep first)
- Show hierarchical sub-folders
- Display attachment icons
- Support fuzzy matching for no exact matches

### Name Search (-n/--name)
```sql
-- Full-text search across titles and metadata
SELECT DISTINCT
    i.itemID,
    it.typeName,
    title.value as title,
    abstract.value as abstract
FROM items i
JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
LEFT JOIN (
    SELECT itemID, value 
    FROM itemData id 
    JOIN itemDataValues idv ON id.valueID = idv.valueID 
    WHERE fieldID = 1  -- title
) title ON i.itemID = title.itemID
LEFT JOIN (
    SELECT itemID, value 
    FROM itemData id 
    JOIN itemDataValues idv ON id.valueID = idv.valueID 
    WHERE fieldID = 2  -- abstract
) abstract ON i.itemID = abstract.itemID
WHERE 
    title.value LIKE ? OR 
    abstract.value LIKE ?
ORDER BY 
    CASE WHEN title.value LIKE ? THEN 1 ELSE 2 END,
    title.value;
```

### Interactive Mode (-i/--interactive)
```python
def interactive_item_selection(items):
    """Display numbered list and prompt for selection"""
    for i, item in enumerate(items, 1):
        icon = get_attachment_icon(item.attachment_type)
        print(f"{i:>3}. {item.title} {icon}")
    
    while True:
        choice = input("\nSelect item number (0 to cancel): ")
        if choice == "0":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        print("Invalid selection. Try again.")
```

### Attachment Handling (-g/--grab)
```python
def copy_attachment(item_id, zotero_data_dir, target_dir="."):
    """Copy attachment file to target directory"""
    # Get attachment info
    attachment = get_attachment_info(item_id)
    if not attachment:
        return False
    
    # Parse storage path (format: "storage:filename")
    if attachment.path.startswith("storage:"):
        filename = attachment.path[8:]  # Remove "storage:" prefix
        item_key = get_item_key(item_id)
        
        source_path = zotero_data_dir / "storage" / item_key / filename
        target_path = Path(target_dir) / filename
        
        if source_path.exists():
            shutil.copy2(source_path, target_path)
            return True
    
    return False
```

## Error Handling

### Database Access Errors
```python
def safe_db_query(query, params=None):
    """Execute query with proper error handling"""
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        return cursor.fetchall()
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e).lower():
            raise DatabaseLockedError("Zotero database is locked. Close Zotero and try again.")
        raise DatabaseError(f"Database error: {e}")
    except Exception as e:
        raise DatabaseError(f"Unexpected error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
```

### Version Compatibility
```python
def check_database_version(db_path):
    """Verify database compatibility"""
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM version")
        version = cursor.fetchone()[0]
        
        # Known compatible versions
        compatible_versions = ["4", "5", "6", "7"]  # Update as needed
        
        if not any(version.startswith(v) for v in compatible_versions):
            logger.warning(f"Untested database version: {version}")
        
        return version
    except Exception as e:
        raise DatabaseError(f"Cannot read database version: {e}")
    finally:
        conn.close()
```

## Performance Considerations

### Indexing Strategy
- Leverage existing Zotero indexes
- Avoid table scans on large datasets
- Use LIMIT for result pagination
- Consider prepared statements for repeated queries

### Memory Management
- Use iterators for large result sets
- Close database connections promptly
- Stream results rather than loading all into memory

## Configuration Management

### Config File Structure
```json
{
    "zotero_database_path": "/path/to/zotero.sqlite",
    "max_results": 100,
    "debug": false,
    "attachment_icons": {
        "pdf": "📘",
        "epub": "📗", 
        "txt": "📄"
    }
}
```

### Auto-Discovery
1. Check config file first
2. Search standard Zotero data locations
3. Prompt user if not found
4. Validate database accessibility

## Testing Strategy

### Test Database
- Use the provided `zotero-database-example` for tests
- Create isolated test scenarios
- Mock database for unit tests
- Integration tests with real database structure

### Test Cases
1. **Collection listing** - All folders, hierarchical display
2. **Search functionality** - Exact and fuzzy matching
3. **Attachment detection** - Correct icons and file types
4. **Interactive mode** - Input validation and selection
5. **Error conditions** - Locked database, missing files
6. **Performance** - Large collections, complex queries

## Deployment Considerations

### Dependencies
```toml
[project]
dependencies = [
    # No external dependencies beyond Python stdlib
    # sqlite3 is built-in
    # pathlib, json, argparse are stdlib
]
```

### Platform Compatibility
- Cross-platform path handling
- Unicode support for international characters
- Terminal color support detection
- Proper error messages for each OS

## Future Enhancements

### Potential Features
1. **Export capabilities** - JSON, CSV, BibTeX
2. **Advanced search** - Multiple criteria, date ranges
3. **Collection management** - Create, modify (with extreme caution)
4. **Sync integration** - Web API for cloud libraries
5. **Plugin system** - Custom formatters and exporters

### API Migration Path
Consider transitioning to Zotero Web API for write operations:
```python
# Future: Use Web API for modifications
import requests

def create_collection_via_api(name, parent_id=None):
    """Create collection via Web API (safer than direct DB)"""
    # Implementation using Zotero Web API
    pass
```