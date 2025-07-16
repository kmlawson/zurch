# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.8] - 2025-07-16

### Bug Fixes
- **Fixed Collection List Command (`-l`)**: Multiple critical improvements to collection listing functionality
  - Fixed collection count vs display mismatch where "1 of 23 collections" showed but only displayed 1 collection
  - Fixed % wildcard handling (`zurch -l China%`) that was returning "No collections found" instead of matching collections
  - Fixed "0" key immediate response issue where typing "30" would immediately cancel on "0" instead of allowing full number input
  - Consolidated wildcard handling logic for consistency between filtering and display
  - Interactive mode now properly respects `--nointeract` flag

- **Enhanced Metadata Navigation**: Improved user experience in interactive metadata view
  - Changed navigation from `'p' for previous` to `'b' for previous` to match pagination consistency
  - Added boundary error messages ("No more next items available.", "No more previous items available.") 
  - Fixed error messages to not re-display metadata unnecessarily
  - Improved navigation logic with proper boundary checking

- **Improved Keyboard Input Handling**: Enhanced multi-digit number input support
  - "0" key now provides immediate cancellation only when first character typed
  - Multi-digit numbers like "30" can now be typed without premature cancellation
  - Added `first_char_only_immediate` parameter to keyboard input handling

### Technical Improvements
- **Display Function Return Values**: `display_hierarchical_search_results` now returns actual count of displayed items
- **Enhanced Error Handling**: Better boundary navigation in both pagination and metadata views
- **Code Consolidation**: Unified wildcard matching logic across different search contexts
- **Test Coverage**: All 152 tests continue to pass with new functionality

## [0.7.7] - 2025-07-16

### Documentation
- **Static PyPI Badge**: Switched from dynamic to static PyPI version badge
  - Changed from `https://img.shields.io/pypi/v/zurch.svg` to `https://img.shields.io/badge/PyPI-v0.7.7-blue`
  - Resolves caching issues where badge showed outdated version numbers
  - Badge now requires manual updates before each PyPI deployment
  - Updated DEVELOPMENT.md to reflect static badge management process

## [0.7.6] - 2025-07-16

### Documentation
- **Updated Test Badge**: All 152/152 tests passing after cross-platform improvements
- **Updated PyPI Badge**: Now uses dynamic PyPI version badge for automatic updates

## [0.7.5] - 2025-07-16

### Cross-Platform Improvements
- **Windows Keyboard Support**: Added native Windows keyboard input using `msvcrt` 
  - Interactive mode now works fluidly on Windows (no more pressing Enter after each key)
  - Single-character navigation (n, b, l, 0) works immediately on Windows
  - Proper handling of Ctrl+C, Ctrl+D, and special keys across all platforms
- **Smart ANSI Color Detection**: Implemented intelligent terminal capability detection
  - Automatically detects and disables ANSI escape codes in older Windows cmd.exe terminals
  - Enables colors in modern terminals (Windows Terminal, PowerShell, Unix terminals)
  - No more garbled text in legacy terminals
- **Enhanced Export Reliability**: Improved export file permissions handling
  - Graceful handling of `os.chmod()` failures on Windows systems
  - Export functionality now works reliably across all platforms
  - Maintains security on Unix systems where permissions are supported

### Interactive Mode Enhancements
- **Improved Error Handling**: Enhanced interactive mode input validation
  - Invalid input now shows error message instead of exiting interactive mode
  - Only '0', empty string, and Ctrl+C cause cancellation
  - Users no longer get kicked out accidentally by typing wrong keys
- **Boundary Navigation**: Fixed navigation behavior at page boundaries
  - Pressing 'b' on first page or 'n' on last page shows error message instead of canceling
  - Error messages appear immediately without re-displaying the full item list
- **Conditional Navigation**: Improved context-aware navigation options
  - 'l' (go back) option only appears when there's actually a previous context to return to
  - Direct search (`-n`) no longer shows unnecessary "go back" option

### Technical Improvements
- **Platform Capability Detection**: Added `get_platform_capabilities()` function
- **Enhanced Documentation**: Created comprehensive cross-platform compatibility guide
- **No New Dependencies**: All improvements use standard library modules only

## [0.7.4] - 2025-07-15

### Bug Fixes
- **Database Lock Handling**: Fixed issue where database lock (Zotero running) incorrectly triggered config wizard
  - Only configuration issues (missing/invalid config) now trigger the setup wizard
  - Database lock now shows clear "Please close Zotero" message instead of forcing reconfiguration
  - Improved error handling to distinguish between config issues vs runtime errors
- **Exact Matching**: Fixed `-k/--exact` flag not working with `-f/--folder` command
  - Added exact_match parameter to collection search methods
  - `-f "Heritage" -k` now only matches collections named exactly "Heritage"
  - Maintains backward compatibility with existing partial matching behavior

### Maintenance
- **File Cleanup**: Removed unnecessary files from repository
- **Package Optimization**: Cleaned up project structure

## [0.7.3] - 2025-07-15

### Documentation
- **README Enhancement**: Improved search examples and -k flag documentation
  - Added clear examples showing quote handling for special characters
  - Added comprehensive -k/--exact flag examples for all search types
  - Clarified difference between AND search vs phrase search
  - Fixed misleading author search example comments
  - Added proper examples for People's Republic quote handling
  - Better demonstrates when to use quotes vs no quotes
  - Added note about planned -fa/-la flags for future release

### Technical
- **Badge System**: Added comprehensive status badges to README
  - Added PyPI version badge with automatic version tracking
  - Added test status badge showing current test coverage
  - Added Zotero compatibility badge with brand-matching colors
  - Added Claude Code development badge
  - Organized all badges on single line for better presentation

### Bug Fixes
- **README Examples**: Fixed wildcard syntax in examples
  - Corrected "*" wildcards to "%" (SQL LIKE pattern)
  - Removed unnecessary wildcards from -l flag examples (uses partial matching by default)
  - Updated collection search examples to be more accurate

## [0.7.2] - 2025-07-15

### Enhanced
- **Configuration Management**: Implemented comprehensive configuration validation with JSON schema
  - Added validation for all configuration fields including database path verification
  - Implemented atomic configuration file writes for safety
  - Added auto-launch configuration wizard for first-time users
  - Improved configuration error messages and recovery

### Security
- **Export Security**: Fixed TOCTOU (Time-of-Check Time-of-Use) vulnerability in file export
  - Implemented atomic file creation using temporary files and atomic rename
  - Added file size limits and final safety checks for export operations
  - Enhanced export path validation with whitelist-based security model
  - Added comprehensive UTF-8 encoding enforcement throughout the codebase

### Performance
- **Database Optimization**: Fixed N+1 query performance issues
  - Implemented bulk metadata fetching to reduce database queries
  - Added batch processing for large result sets with SQLite parameter limits
  - Optimized export functions to use bulk operations instead of individual queries

### Technical
- **Code Organization**: Created centralized constants module for maintainability
  - Extracted magic strings and numbers into `constants.py` 
  - Standardized ANSI colors, item types, attachment types, and defaults
  - Improved code readability and reduced duplication
- **Architecture**: Further refactored handler functions for better modularity
  - Continued breaking down complex functions in `handlers.py`
  - Enhanced separation of concerns and improved testability
  - Maintained backward compatibility while improving code structure

### Documentation
- **README Enhancement**: Added comprehensive status badges
  - Added PyPI version badge with automatic version tracking
  - Added test status badge showing 141/163 tests passing
  - Added Zotero compatibility badge with brand-matching color
  - Added Claude Code development badge
  - Organized all badges on single line for better visual presentation

## [0.7.1] - 2025-07-14

### Fixed
- **Display Features Implementation**: Fixed three new display flags to work correctly across all search types
  - `--showcreated`: Now properly displays item creation dates in search results
  - `--showmodified`: Now properly displays item modification dates in search results  
  - `--showcollections`: Now properly displays collection paths for items in search results
  - Fixed data extraction in search methods (`search_items_by_name`, `search_items_by_author`, `search_items_combined`)
  - Updated all display function calls to pass new parameters through the entire call chain
  - Enhanced interactive mode to support all three new display features

### Technical
- Updated SQL result processing in `items.py` to extract `dateAdded` and `dateModified` fields
- Enhanced function signatures for `interactive_selection()` and `handle_interactive_mode()` 
- Fixed parameter passing in all calls to `display_grouped_items()` and `display_items()`
- Improved consistency of display features across folder, name, author, and combined searches

## [0.7.0] - 2025-07-14

### Added
- **PyPI Release**: First official release on PyPI 
- **Installation Instructions**: Updated README with proper PyPI installation instructions
  - Added `uv tool install` as recommended installation method
  - Added `pipx` as alternative to pip
  - Included installation from source instructions

### Enhanced
- **Documentation**: Improved installation documentation for better user experience

## [0.6.9] - 2025-07-14

### Fixed
- **Publication Date Statistics**: Fixed `--stats` command to show actual publication dates instead of access dates
  - Changed field ID from 14 (accessDate) to 6 (publication date) in all date-related queries
  - Publication decades now show realistic historical distribution (peak in 1990s-2010s)
  - Added "No Publication Date" category showing items without publication years (23.5% of items)
  - Fixed date filtering (`--after`, `--before` flags) to use publication dates consistently
  - Affects all date-based operations including search sorting and statistics

### Technical
- Updated 8 SQL query locations in `queries.py` to use correct field ID for publication dates
- Enhanced publication decades query logic to handle missing publication dates properly
- Improved data integrity for all date-related functionality throughout the application

## [0.6.8] - 2025-07-14

### Added
- **--sort Flag**: Sort search results by title, date, author, created, or modified
  - Supports aliases: `t/title`, `d/date`, `a/author`, `c/created`, `m/modified`
  - Auto-enables related display flags (e.g., `--sort date` enables `--showyear`)
  - Works with all search commands (`-f`, `-n`, `-a`, `-t`)

### Enhanced  
- **Database Performance**: Unified database interface with persistent connections
  - Uses `sqlite3.Row` for dictionary-style column access
  - Eliminates redundant connection overhead from old interface
  - Significantly improved performance for large result sets
- **Display System**: Enhanced sorting integration across all display functions
- **Code Architecture**: Consolidated database.py and database_improved.py into single optimized interface

### Technical
- Added `sort_items()` utility function with metadata-aware sorting for date and author
- Added `display_sorted_items()` helper function for consistent sorting behavior
- Enhanced database connection management with context managers and proper error handling
- Updated all database access patterns to use modern sqlite3.Row dictionary access

## [0.6.7] - 2025-07-14

### Added
- **--showyear Flag**: Display publication year in parentheses after item titles
- **--showauthor Flag**: Display first author name with " - " separator after item titles  
- **--config Wizard**: Interactive configuration wizard for easy setup
  - Auto-detects Zotero database location
  - Prompts for all configuration options with current values
  - Validates database path and input values
  - Reports config file location and saves atomically
- **Config Defaults**: Support for display flags as config defaults
  - `show_ids`, `show_tags`, `show_year`, `show_author`, `only_attachments`
  - Command line arguments still override config defaults
  - Backward compatible with existing config files

### Enhanced
- **Display System**: Enhanced all display functions to support year and author information
- **Interactive Mode**: Full support for new display options in interactive mode
- **Export Functionality**: Export includes year and author information when available
- **Configuration Management**: Improved config loading with new display defaults

### Technical
- Added `config_wizard.py` with comprehensive interactive configuration setup
- Enhanced `display_items()` and `display_grouped_items()` with year/author extraction
- Updated all handlers to pass new display parameters through the system
- Added validation functions for database paths and configuration values
- Extended config file schema with new display option defaults

## [0.6.6] - 2025-07-14

### Added
- **--stats Command**: New comprehensive database statistics command providing detailed insights into your Zotero library
  - **Overview**: Total counts of items, collections, and tags with colored formatting
  - **Item Types Breakdown**: Complete breakdown of items by type with counts and percentages (books, articles, notes, etc.)
  - **Attachment Statistics**: Count of items with and without PDF/EPUB attachments with percentages
  - **Most Used Tags**: Top 20 most frequently used tags with item counts and professional formatting
  - **Summary**: One-line summary of database contents

### Enhanced
- **Database Interface**: Added comprehensive stats service with optimized SQL queries for performance
- **Visual Design**: Rich formatting with emojis, colors, and proper alignment for easy reading
- **Query Optimization**: Efficient SQL queries that handle large databases without performance issues

### Technical
- Added `StatsService` class for gathering database statistics
- Added `DatabaseStats` dataclass for structured data handling
- Added `build_stats_*_query()` functions for optimized SQL statistics queries
- Added `display_database_stats()` function with professional formatting
- Added `handle_stats_command()` for CLI integration

## [0.6.5] - 2025-07-14

### Added
- **Enhanced -g Feature**: Improved attachment file naming using author lastname and title (e.g., "Smith - Title of Book.pdf"). Files are automatically sanitized for cross-platform compatibility and include conflict resolution with numbered suffixes.
- **Tags in Metadata Display**: Added tag display in item metadata view showing all associated tags in format "Tags: tag1 | tag2 | tag3".
- **--showtags Flag**: New command-line flag to display tags under each item title in search results, shown in muted gray color for visual clarity.

### Enhanced
- **Attachment Grabbing**: File naming now prioritizes author last names and truncates long titles intelligently while preserving file extensions.
- **Metadata Display**: Tags are now included in the standard metadata view alongside collections and other item information.
- **Search Result Display**: Users can now view tags directly in search results without opening individual items.

### Technical
- Added `get_item_tags()` method to database interface for retrieving item tags
- Added `build_item_tags_query()` function for SQL tag queries
- Enhanced `display_items()` and `display_grouped_items()` functions to support tag display
- Added filename sanitization functions for cross-platform compatibility

## [0.6.4] - 2025-07-14

### Fixed
- **Combined Search Functionality**: Fixed major bug in `search_items_combined` function where combined name and author searches (`-n` + `-a`) were only performing name searches and completely ignoring author filters. Now properly applies AND logic across all search parameters.
- **Standalone Tag Search**: Fixed CLI validation to allow standalone tag searches (`-t` without other search commands) by adding `args.tag` to the list of valid standalone commands.

### Added
- **Proper Combined Query Implementation**: Added `build_combined_search_query()` function that creates proper SQL queries combining name, author, and tag search conditions with correct JOIN logic.
- **Comprehensive Test Suite**: Added `test_combined_search.py` with 9 test cases covering all combinations of name, author, and tag searches to ensure correct behavior.

### Enhanced
- **Search Result Accuracy**: Combined searches now return precise results that match all specified criteria instead of returning overly broad results from partial implementations.

## [0.6.3] - 2025-07-14

### Fixed
- **List Command Without Argument**: Fixed `-l` command when no argument is provided to correctly display all collections instead of showing them as "matches". The display now properly shows "collections" instead of "matches" when no filter is applied.
- **Empty Search Term Handling**: Fixed `matches_search_term` function to return True for empty search terms, allowing proper display of all collections when no filter is specified.
- **Year Filter with Folder Command**: Fixed `--after` and `--before` year filters not working correctly with `-f` folder command. The total count now reflects the filtered items rather than all items in the collection.

## [0.6.2] - 2025-07-13

### Fixed
- **CLI Help Functionality**: Resolved issue where `--help` was not recognized due to `add_help=False` in `ArgumentParser` and conflicting manual help checks. The CLI now correctly displays help messages.
- **Tag Search Failures**: Corrected `search_items_combined` logic to properly handle tag-only searches. Updated `test_tags.py` to use existing tags in the sample database and adjusted assertions to reflect actual data.
- **SQL ESCAPE Error**: Fixed `sqlite3.OperationalError: ESCAPE expression must be a single character` by removing the explicit `ESCAPE '\\'` clause from `LIKE` conditions in SQL queries. The `escape_sql_like_pattern` function now handles escaping correctly without this clause.
- **Test `total_count` for Tag Filters**: Adjusted `get_collection_items` to calculate `total_count` based on the number of items after tag filtering, ensuring consistency between returned items and total count.

## [0.6.1] - 2025-07-13

### Fixed
- **Max Results (-x flag) Behavior**: The `-x` flag now correctly applies the limit as the final operation after all other processing (including deduplication) is complete. This ensures that the specified number of results are returned from the final processed set, as per the `GEMINI.md` specification.

## [0.6.2] - 2025-07-13

### Fixed
- **CLI Help Functionality**: Resolved issue where `--help` was not recognized due to `add_help=False` in `ArgumentParser` and conflicting manual help checks. The CLI now correctly displays help messages.
- **Tag Search Failures**: Corrected `search_items_combined` logic to properly handle tag-only searches. Updated `test_tags.py` to use existing tags in the sample database and adjusted assertions to reflect actual data.
- **SQL ESCAPE Error**: Fixed `sqlite3.OperationalError: ESCAPE expression must be a single character` by removing the explicit `ESCAPE '\\'` clause from `LIKE` conditions in SQL queries. The `escape_sql_like_pattern` function now handles escaping correctly without this clause.
- **Test `total_count` for Tag Filters**: Adjusted `get_collection_items` to calculate `total_count` based on the number of items after tag filtering, ensuring consistency between returned items and total count.

## [0.6.1] - 2025-07-13

### Added
- **Debug Mode Purple Duplicates**: When `-d` flag is used, all duplicate items are displayed in purple color
  - Selected (best) items remain in normal colors for easy identification
  - Duplicates show purple icons and purple text
  - Maintains full duplicate detection and logging information

### Enhanced
- **Visual Improvements**: 
  - Changed book icon from 📕 (red book) to 📗 (green book) for better visual distinction
  - Enhanced color coding system for duplicate identification
  - Improved visual hierarchy in debug mode output

### Technical
- Added `is_duplicate` flag to `ZoteroItem` dataclass
- New `format_duplicate_title()` function for purple text formatting
- Updated `format_item_type_icon()` to support purple color for duplicates
- Modified deduplication logic to include marked duplicates in debug mode

## [0.5.0] - 2025-07-13

### Added
- **Automatic Duplicate Detection and Removal**: Major new feature that intelligently removes duplicates
  - Matches items based on title, author names, and publication year
  - Prioritizes items with PDF/EPUB attachments over those without
  - Falls back to most recent modification date for tie-breaking
  - Works automatically with both `-n` (name search) and `-f` (folder search)
  - Reduces clutter and shows only the best version of each item

- **Duplicate Control Options**:
  - `--no-dedupe` flag to disable automatic deduplication
  - Debug logging shows detailed duplicate detection process
  - Comprehensive logging for troubleshooting duplicate issues

### Enhanced
- **Search Results**: 
  - Example: "World History in People's Republic" reduced from 8 duplicates to 2 unique items
  - "AHR Conversation" searches reduced from 17 duplicates to 6 unique items
  - Maintains all existing functionality while providing cleaner results

### Technical
- New `duplicates.py` module with `DuplicateKey` class for consistent identification
- Smart selection algorithm in `select_best_duplicate()` function
- Maintains original ordering and collection grouping after deduplication
- Comprehensive debug logging for duplicate detection process

## [0.4.4] - 2025-01-13

### Added
- **Grouped Folder Display with Separations**: Enhanced `-f` command for multiple matching folders
  - Clear visual separations between different collections
  - Collection headers show full hierarchical paths and item counts
  - Continuous numbering across folders for interactive mode compatibility
  - Maintains alphabetical sorting within each folder

### Enhanced
- **Multi-Folder Search Results**: 
  - Example output format: `=== World History (13 items) ===` followed by items
  - Then `=== 0 Journals > J of World History (24 items) ===` with its items
  - Provides clear context about which folder each item belongs to

### Technical
- New `get_collection_items_grouped()` method for maintaining collection separation
- Enhanced `display_grouped_items()` function with hierarchical headers
- Improved organization for searches that match multiple collections

## [0.4.3] - 2025-01-13

### Added
- **Item ID Lookup**: New `--id` flag to display metadata for specific item IDs
  - Usage: `zurch --id 12345` shows complete metadata for item 12345
  - Useful for investigating specific items found in search results
  - Includes error handling for invalid item IDs

- **Collection Membership Display**: Enhanced metadata views show item collections
  - All metadata displays now include "Collections:" section
  - Shows full hierarchical collection paths where items are stored
  - Works in both `--id` flag usage and interactive mode (`-i`)
  - Helps understand item organization within Zotero library

### Enhanced
- **Metadata Views**: Both interactive selection and direct ID lookup show collection membership
- **Navigation**: Easier to understand relationships between items and their storage locations

### Technical
- New `get_item_collections()` method with recursive CTE for hierarchical paths
- Enhanced `show_item_metadata()` function to include collection information
- Updated CLI argument parsing and main logic for `--id` flag support

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