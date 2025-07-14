# Development Notes for Zurch

## Project Overview
Zurch (formerly clizot) is a CLI search tool for Zotero installations. It provides read-only access to Zotero databases and allows users to search and browse their research library from the command line.

## Key Architecture Decisions

### Project Structure
```
zurch/
├── pyproject.toml       # Project configuration and dependencies
├── CLAUDE.md           # AI assistant instructions
├── CHANGELOG.md        # Version history
├── README.md          # User documentation
├── LICENSE            # MIT License (Konrad M. Lawson, 2025)
├── DEVELOPMENT.md     # This file
├── TODO.md            # Current todo items
├── KEYFILES.md        # Key files reference
├── GEMINI.md          # Additional project notes
├── info/              # Documentation directory
│   ├── DEVNOTES.md    # Development notes
│   └── DATABASE_STRUCTURE.md # Database structure docs
├── zurch/             # Main package directory
│   ├── __init__.py    # Package initialization
│   ├── __main__.py    # Entry point for python -m zurch
│   ├── cli.py         # Command line interface
│   ├── parser.py      # Argument parsing
│   ├── handlers.py    # Command handlers
│   ├── search.py      # Main database interface
│   ├── database.py    # Database connection
│   ├── collections.py # Collection queries
│   ├── items.py       # Item queries
│   ├── metadata.py    # Metadata queries
│   ├── models.py      # Data models
│   ├── duplicates.py  # Duplicate detection
│   ├── display.py     # Output formatting
│   ├── interactive.py # Interactive mode
│   ├── config.py      # Configuration management
│   ├── utils.py       # Utility functions
│   └── queries.py     # SQL queries
└── tests/             # Test suite
    ├── test_zurch.py      # Main test file
    ├── test_collections.py # Collection tests
    ├── test_database.py   # Database tests
    ├── test_display.py    # Display tests
    ├── test_duplicates.py # Duplicate tests
    ├── test_handlers.py   # Handler tests
    ├── test_interactive.py # Interactive tests
    ├── test_items.py      # Item tests
    └── test_tags.py       # Tag tests

```

### Development Workflow
1. **Always follow CLAUDE.md guidelines**:
   - Use uv for all package management
   - Reinstall after changes: `uv tool uninstall zurch && uv cache clean && uv tool install .`
   - Write tests before implementing features
   - Keep code files small and focused
   - Commit after completing features with updated CHANGELOG.md

2. **Testing Pattern**:
   ```bash
   # Run all tests
   uv run pytest -v
   
   # Run specific test
   uv run pytest tests/test_zurch.py::TestClassName::test_method_name -v
   ```

3. **Version Bumping**:
   - Update version in: `pyproject.toml`, `zurch/__init__.py`, `zurch/cli.py`
   - Add entry to CHANGELOG.md
   - Commit with descriptive message

### Configuration System
- **Config File**: `config.json` (not `zurch.json`)
- **Locations**:
  - macOS/Linux: `~/.config/zurch/config.json`
  - Windows: `%APPDATA%\zurch\config.json`
- **Legacy Migration**: Automatically migrates from `~/.zurch-config/`

### Database Access
- **Read-only SQLite access** using URI mode: `sqlite3.connect(f'file:{path}?mode=ro', uri=True)`
- **Zotero Database Structure**:
  - Collections: Hierarchical folder structure
  - Items: Research items (books, articles, etc.)
  - Attachments: PDFs, EPUBs linked to items
  - Uses Entity-Attribute-Value (EAV) model for flexible metadata

### Key SQL Patterns

1. **Hierarchical Collections** (using recursive CTE):
```sql
WITH RECURSIVE collection_tree AS (
    SELECT collectionID, collectionName, parentCollectionID, 0 as depth, 
           collectionName as path
    FROM collections WHERE parentCollectionID IS NULL
    UNION ALL
    SELECT c.collectionID, c.collectionName, c.parentCollectionID, 
           ct.depth + 1, ct.path || ' > ' || c.collectionName
    FROM collections c
    JOIN collection_tree ct ON c.parentCollectionID = ct.collectionID
)
```

2. **Avoiding Duplicate Items** (separate attachment queries):
```python
# First get items without JOIN on attachments
items_query = "SELECT ... FROM items ..."
# Then fetch attachments separately
attachment_query = "SELECT ... WHERE parentItemID = ? OR itemID = ?"
```

3. **Case-Insensitive Alphabetical Sorting**:
```sql
ORDER BY LOWER(COALESCE(title_data.value, ''))
```

### Icon System
- 📗 = Books (`item_type == "book"`)
- 📄 = Journal articles (`item_type in ["journalarticle", "journal article"]`)
- 🔗 = PDF/EPUB attachments available
- 📚 = Other item types (default)
- Purple icons = Duplicate items (debug mode only)

### Command Line Arguments
- `-f/--folder [name]`: List items in folder (supports spaces without quotes)
- `-n/--name [term]`: Search items by title
- `-l/--list [pattern]`: List collections (hierarchical display)
- `-a/--author [name]`: Search items by author
- `-t/--tag [tag]`: Filter by tags (case-insensitive)
- `-i/--interactive`: Interactive selection mode
- `-g/--grab`: Copy attachments (requires -i)
- `-o/--only-attachments`: Show only items with PDF/EPUB attachments
- `-k/--exact`: Exact matching instead of partial
- `-x/--max-results N`: Limit results (default 100)
- `-d/--debug`: Debug logging
- `-v/--version`: Show version
- `-h/--help`: Show help
- `--after YEAR`: Show items published after year
- `--before YEAR`: Show items published before year
- `--books`: Show only book items
- `--articles`: Show only article items
- `--id ID`: Show metadata for specific item ID
- `--getbyid ID [ID...]`: Grab attachments for specific item IDs
- `--showids`: Show item ID numbers in results
- `--no-dedupe`: Disable automatic duplicate removal

### Interactive Mode Features
1. **Collection Selection** (`zurch -l -i`):
   - Shows hierarchical numbered list
   - Select by number to run `-f` on that collection
   - Can combine with `-g` to grab attachments

2. **Item Selection** (`zurch -f folder -i` or `zurch -n term -i`):
   - Numbered list of items
   - Select to view full metadata
   - With `-g`, copies attachment to current directory
   - **NEW**: Append 'g' to item number for immediate grab (e.g., "3g")

3. **Attachment Filtering** (`-o` flag):
   - Show only items with PDF or EPUB attachments
   - Works with `-f`, `-n`, and `-l -i` modes
   - Useful for finding readable papers

### Code Style Guidelines
- Type hints for function parameters and returns
- Docstrings for all public functions
- ANSI escape codes for terminal formatting:
  - Bold: `\033[1m` ... `\033[0m`
- Error handling with custom exceptions (DatabaseError, DatabaseLockedError)
- NO comments in code unless specifically requested

### Common Development Tasks

1. **Adding a New Command Flag**:
   - Add to `create_parser()` in cli.py
   - Implement logic in `main()`
   - Update tests
   - Update README.md and CHANGELOG.md

2. **Modifying Database Queries**:
   - Edit methods in search.py
   - Test with sample database
   - Ensure no performance regressions

3. **Adding New Icons**:
   - Update `format_item_type_icon()` in utils.py
   - Update tests in test_zurch.py
   - Document in README.md

### Security and Input Handling
- **SQL Injection Protection**: All database queries use parameterized statements
- **SQL LIKE Escaping**: User input is properly escaped for LIKE queries using `escape_sql_like_pattern()`
- **Unicode Support**: Full Unicode support for all languages (Chinese: 中国, Japanese: 日本, Korean: 한국, etc.)
- **Shell Character Handling**: Users must quote search terms containing shell special characters
  - Special chars requiring quotes: `'` `"` `$` `` ` `` `\` `(` `)` `[` `]` `{` `}` `|` `&` `;` `<` `>` `*` `?`
  - Example: `zurch -n "China's Revolution"` not `zurch -n China's Revolution`
  - Unicode characters work without escaping: `zurch -n 中国`

### Known Issues and Future Enhancements
1. Full arrow key navigation (requires curses/termios)
2. Export functionality for search results
3. Integration with Zotero API for remote access
4. Caching for improved performance on large databases
5. Shell argument pre-processing to auto-escape common characters

### Git Workflow
```bash
# After making changes
git add -A
git commit -m "Clear description of changes

- Detail 1
- Detail 2

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### PyPI Publishing (Future)
- Package name: `zurch`
- Author: Konrad M. Lawson
- Structure already prepared for PyPI deployment
- Use `uv build` to create wheel and source distributions

## Quick Reference

### Reinstall During Development
```bash
uv tool uninstall zurch && uv cache clean && uv tool install .
```

### Run Quick Test
```bash
zurch -f "Global Maoism" -x 3
```

### Check Version
```bash
zurch --version
```

### View Config Location
```bash
python -c "from zurch.utils import get_config_file; print(get_config_file())"
```