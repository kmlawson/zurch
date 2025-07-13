# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2025-01-13

### Added
- **Interactive Collection Selection**: `zurch -l -i` now provides interactive mode for collection browsing
  - Displays collections in hierarchical numbered list
  - Select a collection by number to view its contents
  - Automatically runs `-f` on the selected collection
  - Can be combined with `-g` to grab attachments from selected collection

### Enhanced
- **Hierarchical Display for All Collections**: `zurch -l` without search term now shows hierarchical structure
  - Previously showed flat indented list
  - Now uses same hierarchical tree display as filtered searches
  - Provides better visualization of collection organization

### Technical
- Moved interactive functionality to separate `interactive.py` module for better code organization
- Standardized config location for macOS to use `~/.config/zurch/config.json` (same as Linux)

## [0.4.0] - 2025-01-13

### Breaking Changes
- **Project Renamed**: `clizot` is now `zurch` - a more descriptive name for the Zotero search CLI
  - Command changed from `clizot` to `zurch`
  - Package name changed from `clizot` to `zurch`
  - Configuration directory changed from `~/.config/clizot/` to `~/.config/zurch/`
  - All import statements updated to use `zurch` module

### Migration
- Uninstall old version: `uv tool uninstall clizot` or `pip uninstall clizot`
- Install new version: `uv tool install zurch` or `pip install zurch`
- Configuration will need to be recreated (automatic discovery will still work)

## [0.3.1] - 2025-01-13

### Enhanced
- **Icon Display Improvements**
  - Journal articles now display 📄 (document icon) to distinguish from books
  - Books continue to display 📕 (closed book icon)
  - PDF and EPUB attachments now show 🔗 (link icon) after the type icon
  - Other attachment types (TXT) no longer show attachment icons
  - Improved visual distinction between item types and attachment availability

### Fixed
- **Duplicate Entry Resolution**
  - Fixed issue where items with multiple attachments appeared as duplicate entries
  - Modified SQL queries to properly handle one-to-many attachment relationships
  - Items now appear only once regardless of number of attachments

- **Command Line Usability**
  - `-f` and `-n` flags now accept multi-word arguments without requiring quotes
  - Can now use `clizot -f Global Maoism` instead of `clizot -f "Global Maoism"`
  - Improved natural command-line experience

- **Metadata Display**
  - Field labels in interactive mode (`-i`) are now bold for better readability
  - Enhanced visual formatting of metadata output

- **Alphabetical Sorting**
  - All item listings now sort alphabetically by title instead of database order
  - Case-insensitive sorting for consistent results

### Technical
- Separated attachment queries from main item queries to prevent JOIN duplicates
- Updated argparse to use `nargs='+'` for multi-word argument handling
- Added ANSI escape codes for bold formatting in terminal output
- Modified SQL ORDER BY clauses for consistent alphabetical sorting

## [0.3.0] - 2025-01-13

### Added
- **NEW: `-k/--exact` flag for exact search functionality**
  - Exact search for item names (`-n "title" -k`)
  - Exact search for collection names (`-l "collection" -k`)
  - Complements existing partial matching with precise control

### Enhanced
- **Project Structure Improvements**
  - Restructured for PyPI deployment with proper package layout
  - Moved tests to dedicated `tests/` folder
  - Created proper Python package structure with `clizot/` directory
  - Added `LICENSE` file (MIT license)
  - Enhanced `pyproject.toml` with full PyPI metadata

- **Installation & Distribution**
  - Added support for `uv tool install .` as specified in requirements
  - Package now builds proper wheel and source distributions
  - Entry points work both as `clizot` command and `python -m clizot`
  - Added build system configuration for Hatchling

- **Testing & Quality**
  - Updated all tests to work with new package structure
  - Added comprehensive tests for exact search functionality
  - All 18 tests pass with new features
  - Fixed test imports to use proper package structure

### Technical
- Updated search database queries to support both partial and exact matching
- Enhanced CLI argument parsing with new `-k/--exact` flag
- Modified collection filtering logic to respect exact match flag
- Improved search result handling with proper tuple unpacking

### Compatibility
- Maintains full backward compatibility with existing functionality
- All existing commands work exactly as before
- New exact search is opt-in via `-k` flag

### Documentation
- Updated help text to include new exact search flag
- All existing documentation remains accurate

## [0.1.0] - 2025-01-13

### Added
- Initial release of clizot - Zotero CLI tool
- Core functionality:
  - `-l/--list` command to list all collections and sub-collections
  - `-l [filter]` command to filter collections with wildcard support (*) 
  - `-f/--folder [name]` command to list items in named folder
  - `-n/--name [term]` command to search items by title
  - `-i/--interactive` mode for item selection and metadata viewing
  - `-g/--grab` mode to copy attachments to current directory
  - `-d/--debug` mode with detailed logging
  - `-x/--max-results` to limit number of results
  - `-v/--version` and `-h/--help` flags

### Features
- Read-only SQLite database access for safety
- Hierarchical collection display with item counts
- Attachment type detection with colored icons:
  - 📘 Blue book for PDF files
  - 📗 Green book for EPUB files  
  - 📄 Grey document for text files
- Fuzzy collection matching with suggestions when no exact match found
- Interactive metadata display for selected items
- Cross-platform configuration management (~/.clizot-config)
- Automatic Zotero database discovery
- Comprehensive error handling and user feedback

### Technical
- Built with Python 3.8+ using uv package manager
- Modular code structure (cli.py, search.py, utils.py)
- Comprehensive unit test suite with pytest
- Zotero 7.0 compatibility
- Detailed development documentation and database structure analysis
- Read-only database access with proper connection handling
- Support for complex SQL queries with performance optimization

### Documentation
- Complete database structure documentation (info/DATABASE_STRUCTURE.md)
- Development notes with API migration strategies (info/DEVNOTES.md)
- Comprehensive test coverage
- Clear installation and usage instructions