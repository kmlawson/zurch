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
│   ├── config_wizard.py # Configuration wizard
│   ├── constants.py   # Constants and enums
│   ├── export.py      # Export functionality
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
   - Reinstall after changes: `tools/reinstall.sh`
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
   - **Automated**: Use `make versionbump` (see Makefile section below)
   - **Manual**: Update version in: `pyproject.toml`, `zurch/__init__.py`, `zurch/cli.py`
   - Fix the PyPI badge in README.md
   - Add entry to CHANGELOG.md
   - Commit with descriptive message

### Configuration System
- **Config File**: `config.json` 
- **Locations**:
  - macOS/Linux: `~/.config/zurch/config.json`
  - Windows: `%APPDATA%\zurch\config.json`
- **Interactive Mode**: Can be configured as default via `interactive_mode` setting
  - Priority: `--nointeract` > `-i` explicit > config setting > default (True)

#### Adding New Configuration Fields

**IMPORTANT**: When adding new configuration options, you must update the Pydantic model:

1. **Add field to ZurchConfigModel** in `zurch/config_models.py`:
   ```python
   new_feature_enabled: bool = Field(default=True, description="Enable new feature")
   new_feature_max_items: int = Field(default=50, ge=1, le=1000, description="Max items for new feature")
   ```

2. **Update config wizard** in `zurch/config_wizard.py`:
   - Add prompts for new fields
   - Include in configuration summary
   - Add to `new_config` dictionary

3. **Import correctly** in config wizard:
   ```python
   from .config_pydantic import load_config, save_config, ZurchConfigModel
   ```

4. **Create model from dict** when saving:
   ```python
   config_model = ZurchConfigModel(**new_config)
   save_config(config_model)
   ```

**Common Issues**:
- Config wizard validation errors → Check Pydantic model has all fields
- "Additional properties not allowed" → Missing field in ZurchConfigModel
- Import errors → Use `config_pydantic` not `utils` for save_config

### Database Access
- **IMPORTANT Read-only SQLite access** using URI mode: `sqlite3.connect(f'file:{path}?mode=ro', uri=True)`
- Never modify the Zotero database at any time
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
- 🌐 = Websites
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
- `-x/--max-results N`: Limit results (default 100, 'all' or '0' for unlimited)
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
- `--showtags`: Show tags for each item in results
- `--showyear`: Show publication year for each item in results
- `--showauthor`: Show first author name for each item in results
- `--showcreated`: Show item creation date in results
- `--showmodified`: Show item modification date in results
- `--showcollections`: Show collections each item belongs to in results
- `--sort {t,title,d,date,a,author,c,created,m,modified}`: Sort results
- `--export {csv,json}`: Export search results to file
- `--file FILE`: Specify output file path for export
- `--config`: Launch interactive configuration wizard
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
- ANSI escape codes for terminal formatting (with cross-platform detection):
  - Bold: `\033[1m` ... `\033[0m`
  - Colors automatically disabled in older terminals
- Error handling with custom exceptions (DatabaseError, DatabaseLockedError)
- Cross-platform compatibility using standard library modules
- NO comments in code unless specifically requested

### Common Development Tasks

1. **Adding a New Command Flag**:
   - Add to `create_parser()` in parser.py
   - Implement logic in `main()` in cli.py
   - Update tests
   - Update README.md and CHANGELOG.md

2. **Adding New Configuration Settings**:
   - **CRITICAL**: Update `ZurchConfigModel` in `config_models.py` first
   - Add to config wizard prompts and dictionary
   - Use `config_pydantic.save_config(ZurchConfigModel(**dict))` 
   - Test config wizard doesn't throw validation errors
   - Update documentation

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

### Cross-Platform Support
- **Windows**: Native keyboard input using `msvcrt` module
- **Unix/Linux/macOS**: Uses `termios` and `tty` modules for keyboard input
- **Terminal Detection**: Automatically detects terminal capabilities
  - ANSI colors disabled in older cmd.exe terminals
  - Full color support in Windows Terminal, PowerShell, and Unix terminals
- **File Permissions**: Graceful handling of `os.chmod()` across platforms
- **Path Handling**: Uses `pathlib` for cross-platform path operations
- **Documentation**: See `docs/CROSS_PLATFORM_IMPROVEMENTS.md` for details

### Known Issues and Future Enhancements
1. Add support for arrow key navigation of -i lists.

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

### Makefile Development Automation

The project includes a comprehensive Makefile with automated development tasks:

#### Core Development Commands
```bash
make help           # Show all available targets
make test           # Run all tests
make test-verbose   # Run tests with verbose output
make lint           # Run ruff linting checks
make lint-fix       # Run ruff linting with auto-fix
make check-all      # Run all checks (lint + tests)
```

#### Installation & Building
```bash
make install        # Install zurch using uv
make dev-install    # Install zurch in development mode
make reinstall      # Reinstall zurch (uninstall, clean cache, install)
make build          # Build the package
make clean          # Clean build artifacts
```

#### Version Management - `make versionbump`

The `make versionbump` target provides automated version bumping with two usage modes:

**Auto-increment Mode** (recommended):
```bash
make versionbump
```
- Automatically increments the patch version (e.g., 0.7.9 → 0.7.10)
- Reads current version from `pyproject.toml`
- Uses `awk` to increment the third number: `awk -F. '{print $1"."$2"."$3+1}'`

**Manual Version Mode**:
```bash
make versionbump VERSION=1.0.0
```
- Sets version to specified value
- Useful for major/minor version bumps

#### How `make versionbump` Works

1. **Version Detection**: 
   ```bash
   CURRENT_VERSION=$(grep 'version = ' pyproject.toml | cut -d'"' -f2)
   ```

2. **Auto-increment Logic**:
   ```bash
   NEW_VERSION=$(echo $CURRENT_VERSION | awk -F. '{print $1"."$2"."$3+1}')
   ```

3. **File Updates** (using `sed` with macOS-compatible syntax):
   - `pyproject.toml`: Main package version
   - `zurch/__init__.py`: Package `__version__` variable
   - `zurch/cli.py`: CLI `__version__` variable  
   - `zurch/constants.py`: Network `USER_AGENT` string
   - `README.md`: PyPI badge (`PyPI-v0.7.9-blue`)
   - `CHANGELOG.md`: Adds new version header with current date

4. **Changelog Template**: 
   ```markdown
   ## [0.7.10] - 2025-07-17
   
   ### Changes
   - TBD
   ```

5. **Helpful Reminders**: Shows next steps for completion

#### Additional Makefile Targets
```bash
make test-pydantic   # Run Pydantic model tests only
make test-database   # Run database tests only
make test-handlers   # Run handler tests only
make test-fast       # Run tests with fail-fast (-x)
make test-coverage   # Run tests with coverage report
make install-hooks   # Install git pre-commit hooks
make version         # Show current version
make dev-cycle       # Run lint-fix + test
make release-check   # Run check-all + build
```

### Version Updates (Manual Process)
When bumping the version manually, update ALL of these locations:

**Core Version Files**:
1. `pyproject.toml` - Main package version
2. `zurch/__init__.py` - Package `__version__` variable
3. `zurch/cli.py` - CLI `__version__` variable
4. `zurch/constants.py` - Network `USER_AGENT` string
5. `CHANGELOG.md` - Add new version entry

**Documentation**:
6. `README.md` - Test badge count (if tests changed)
7. `README.md` - PyPI badge (static badge, manually updated)

**Badge Notes**:
- PyPI badge uses static format: `https://img.shields.io/badge/PyPI-v0.7.9-blue` (manually updated)
- Badge must be updated manually before each PyPI deployment

**PyPI Publishing Process**:

Requires `.pypirc` file with PyPI API token

1. Update all version locations above (or use `make versionbump`)
2. `rm -rf dist/ && uv build`
3. `uv run twine upload dist/*`
4. Package appears at: https://pypi.org/project/zurch/

**Recommended Workflow**:
```bash
# 1. Bump version automatically
make versionbump

# 2. Edit CHANGELOG.md to replace "TBD" with actual changes

# 3. Commit and push
git add .
git commit -m "Bump version to 0.7.10"
git push origin main

# 4. Build and deploy
make clean build
uv run twine upload dist/*
```

## Quick Reference

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
