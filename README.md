# zurch - Zotero Search CLI

[![PyPI version](https://img.shields.io/badge/PyPI-v0.7.8-blue)](https://pypi.org/project/zurch/) [![Tests](https://img.shields.io/badge/Tests-152%2F152%20passing-brightgreen.svg)](https://github.com/kmlawson/zurch) [![Zotero](https://img.shields.io/badge/Zotero-is_Awesome-CC2936.svg)](https://www.zotero.org/) [![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue.svg)](https://claude.ai/code)

A command-line interface tool to interact with your local Zotero installation and extract information from it.

## Introduction

Zotero is a powerful citation manager and research assistant for managing sources. This command-line interface (CLI) can be used to carry out read-only searches on the sqlite database of the Zotero system. Zotero developers generally do not recommend this kind of external direct access to the database. While risk of any impact on your database is low, if you have concerns, you may want to run this on a copy of your Zotero installation and use of this tool is at your own risk. Zurch will not function while the Zotero is running.

## Features

- **List Collections**: Browse all your Zotero collections and sub-collections
- **Search Items**: Find items by title or browse specific folders  
- **Interactive Mode**: Select items interactively to view metadata or grab attachments
- **Attachment Management**: Copy PDF, EPUB, and text attachments to your current directory
- **Visual Indicators**: Icons show item types (📗 books, 📄 articles) and attachments (🔗 PDF/EPUB available)
- **Fast Performance**: Optimized SQLite queries for quick results
- **Cross-Platform**: Full support for Windows, macOS, and Linux with native keyboard input
- **Smart Terminal Detection**: Automatically adapts to your terminal's capabilities
- Provides READ ONLY access to your Zotero database

## Installation

### Install from PyPI

```bash
# Install with uv (recommended) - installs as a globally available tool
uv tool install zurch

# Or install with pip
pip install zurch

# Or install with pipx (if you prefer pipx over uv)
pipx install zurch
```

### Install from source

```bash
# Clone the repository
git clone https://github.com/kmlawson/zurch.git
cd zurch

# Install with uv
uv tool install .
```

## Quick Start

```bash
# List collections (up to default max items to show)
zurch -l

# List collections matching a pattern (partial matching by default)
zurch -l japan

# List collections with exact matching name
zurch -l "Japan" -k

# Browse items in a folder/s partial matching a name
zurch -f "Heritage"
# OR
zurch -f Heritage

# Search for items by name
zurch -n "People's"
zurch -n medicine

# Interactive mode is now the default - select and view metadata or grab attachments
zurch -f "Heritage"
# Interactive mode works with all searches:
zurch -n "China"
zurch -a "Smith"

# Use --nointeract to disable interactive mode and get simple list output
zurch -f "Heritage" --nointeract
zurch -n "China" --nointeract

# Show only hits with PDF/EPUB attachments
zurch -n nationalism -o

# Grabbing the PDF or EPUB attachment while in interactive mode (default):
zurch -n "Introduction to"
# Then type: 5g to grab attachment from item 5 if it includes one

# Debug mode shows additional verbose logging, including duplicates in purple
zurch -n "World History" -d

# Show IDs 
zurch -n nationalism --showids

# Look up metadata of a specific item by ID
zurch --id 12345

# Grab attachment of a specific item by ID
zurch --getbyid 12345

# Disable duplicate removal to see all database entries
zurch -n "duplicate article" --no-dedupe

# Show comprehensive database statistics about the database
zurch --stats

# Show tags under item titles
zurch -n "research methods" --showtags

# Show year and author information
zurch -n "machine learning" --showyear --showauthor

# Export search results to CSV and JSON
zurch -n "digital humanities" --export csv

# Export to specific file path
zurch -n "methodology" --export json --file ~/research/methods.json

# Sort results by publication date (newest first)
zurch -n "machine learning" --sort date

# Sort by author last name
zurch -f "Papers" --sort author

# Navigate through long results with pagination
zurch -n "china" -p -x 5  # Show 5 items per page, navigate with n/p/0

# Show all results without limit
zurch -n "china" -x all  # Show all results
zurch -l "Heritage" -x 0  # Show all Heritage collections
```

## Commands

### List Collections (-l/--list)
```bash
# Show all collections and sub-collections
zurch -l

# Filter collections (partial matching by default)
zurch -l "china"

# Partial match by default but use % wildcard for more control
zurch -l "china%"      # starts with "china" 
zurch -l "%history"   # ends with "history"

# Show collection and all its sub-collections (append / to name)
zurch -l "Digital Humanities/"  # Shows "Digital Humanities" and all sub-collections
zurch -l "Research/"            # Shows all collections under "Research"
```

### Browse Folder (-f/--folder)
```bash
# List items in a specific folder
zurch -f "Heritage"

# Include items from folder AND all sub-collections (append / to name)
zurch -f "Digital Humanities/"  # Shows items from "Digital Humanities" and all sub-collections
zurch -f "Research/"            # Shows items from "Research" and all sub-collections

# Limit results
zurch -f "Digital Humanities" -x 10

# Interactive mode (default behavior)
zurch -f "Travel"

# Disable interactive mode
zurch -f "Travel" --nointeract
```

### Search by Name (-n/--name)
```bash
# Search item titles (supports AND logic for multiple words)
zurch -n machine learning    # Finds items with BOTH "machine" AND "learning"
zurch -n "machine learning"  # Finds items containing "machine learning"

# Case-insensitive, partial matching (default)
zurch -n "china"             # Finds "China", "China's History", "Modern China", etc.

# Exact matching with -k flag
zurch -n "china" -k          # Finds only items with title exactly "china"

# Handling special characters - quotes protect phrases
zurch -n "People's" Republic     # AND search: items with BOTH "People's" AND "Republic"
zurch -n "People's Republic"     # Phrase search: items containing exactly "People's Republic"

# Wildcard patterns (for partial matching)
zurch -n "china%"    # Titles starting with "china"
zurch -n "%history"  # Titles ending with "history"  
zurch -n "%war%"     # Titles containing "war"
```

### Search by Author (-a/--author)
```bash
# Search by author name (supports AND logic for multiple words)
zurch -a smith       # Find items by authors named "smith"
zurch -a john smith  # Find items with BOTH "john" AND "smith" in ANY author name
zurch -a "john smith"# Find items by authors containing "john smith"

# Exact matching with -k flag
zurch -a "john smith" -k  # Find items by authors with exactly "john smith"

# Note: -fa and -la flags for first/last name search are planned for future release

# Works with first or last names
zurch -a benjamin    # Finds Benjamin Franklin, Benjamin Netanyahu, etc.
```

### Filter by Tags (-t/--tag)
```bash
# Search by tag alone (case-insensitive, partial matching by default)
zurch -t methodology  # Find all items tagged with "methodology"
zurch -t china japan  # Find items tagged with BOTH "china" AND "japan"
zurch -t "digital humanities"  # Find items tagged containing "digital humanities"

# Exact tag matching with -k flag
zurch -t "digital humanities" -k  # Find items tagged with exactly "digital humanities"

# Combine with other searches for more specific results
zurch -n "machine learning" -t "data science"  # Items about ML tagged with data science
zurch -f "Research" -t "to-read"  # Items in Research folder tagged as to-read
zurch -a smith -t china  # Items by Smith tagged with china

# Multiple tags = AND logic (item must have ALL tags)
zurch -t "important" "methodology" "python"  # Items with all three tags
```

### Interactive Mode (Default Behavior)
Interactive mode is enabled by default for all searches. It allows you to:
- View detailed metadata for any item
- Navigate through multiple items
- Select an item and its attachment will be copied to current directory if you add g after the number
- Use `--nointeract` to disable interactive mode and return to simple list output
```

### Pagination (-p/--pagination)
Navigate through long result lists page by page:
```bash
# Enable pagination to browse results in manageable chunks
zurch -n "china" -p -x 5    # 5 items per page
zurch -l -p -x 10           # 10 collections per page
zurch -f "Papers" -p -x 20  # 20 folder items per page

# Navigation controls:
# n = next page
# p = previous page  
# 0 or Enter = exit pagination
```

When pagination is enabled (`-p` flag), results exceeding the max limit (`-x` value) will be shown page by page with navigation prompts. This is useful for exploring large result sets without overwhelming the terminal.

### Filtering Options
- `-o/--only-attachments`: Show only items with PDF/EPUB attachments
- `--books`: Show only book items in search results  
- `--articles`: Show only journal article items in search results
- `--after YEAR`: Show only items published after this year (inclusive)
- `--before YEAR`: Show only items published before this year (inclusive)
- `-t/--tag TAG [TAG...]`: Filter by tags (case-insensitive, multiple tags = AND logic)
- `-k/--exact`: Use exact matching instead of partial matching

### Database Statistics (--stats)
Get comprehensive insights into your Zotero library:
```bash
zurch --stats
```
Shows:
- **Overview**: Total items, collections, and tags
- **Item Types**: Breakdown by type (books, articles, etc.) with percentages
- **Attachments**: Count of items with/without PDF/EPUB attachments
- **Top Tags**: Most frequently used tags with item counts
- **Database Location**: Path to your Zotero database file

### Display Options
- `--showids`: Show item ID numbers in search results
- `--showtags`: Show tags for each item in search results
- `--showyear`: Show publication year for each item
- `--showauthor`: Show first author name for each item
- `--showcreated`: (Not yet implemented) Show item creation date in search results
- `--showmodified`: (Not yet implemented) Show item modification date in search results
- `--showcollections`: (Not yet implemented) Show collections each item belongs to in search results

### Sorting Options
- `--sort {t|title|d|date|a|author|c|created|m|modified}`: Sort search results by:
  - `t` or `title`: Sort alphabetically by title
  - `d` or `date`: Sort by publication date (auto-enables `--showyear`)
  - `a` or `author`: Sort by author last name (auto-enables `--showauthor`)
  - `c` or `created`: Sort by item creation date (newest first)
  - `m` or `modified`: Sort by modification date (newest first)

### Export Options
- `--export [csv|json]`: Export search results to CSV or JSON format
- `--file PATH`: Specify output file path for export (defaults to current directory)

### Other Options
- `-x/--max-results N`: Limit number of results (default: 100, use 'all' or '0' for unlimited) - **Applied as final step after all filtering and deduplication**
- `-p/--pagination`: Enable pagination for long result lists (navigate with n/p/0)
- `-i/--interactive`: Enable interactive mode (default: enabled)
- `--nointeract`: Disable interactive mode and return to simple list output
- `-d/--debug`: Enable detailed logging and show purple duplicates
- `-v/--version`: Show version information
- `-h/--help`: Show help message
- `--id ID`: Show metadata for a specific item ID
- `--getbyid ID [ID...]`: Grab attachments for specific item IDs
- `--no-dedupe`: Disable automatic duplicate removal
- `--config`: Launch interactive configuration wizard
- `--stats`: Show comprehensive database statistics

### Duplicate Detection
zurch automatically removes duplicate items based on title, author, and year matching:
- **Prioritizes items with attachments** (PDF/EPUB) over those without
- **Selects most recently modified** items when attachments are equal
- **Debug mode (`-d`)** shows all duplicates in purple for investigation
- **`--no-dedupe`** flag disables deduplication to see raw database contents

Example: Search for "World History" reduces 8 duplicate items to 2 unique results.

## Configuration

### Interactive Configuration Wizard
The easiest way to configure zurch is through the interactive wizard:
```bash
zurch --config
```

This will guide you through:
- Auto-detecting your Zotero database location
- Setting interactive mode default (enabled/disabled)
- Setting default display options (IDs, tags, year, author)
- Configuring search defaults
- Setting maximum results limit

### Manual Configuration
Configuration is stored in OS-appropriate locations:
- **Windows**: `%APPDATA%\zurch\config.json`
- **macOS/Linux**: `~/.config/zurch/config.json` (or `$XDG_CONFIG_HOME/zurch/config.json`)

**Note**: If you're upgrading from an earlier version, zurch will automatically migrate your config from the old `~/.zurch-config/` location to the new standard location.

Example configuration:
```json
{
  "zotero_database_path": "/path/to/Zotero/zotero.sqlite",
  "max_results": 100,
  "debug": false,
  "interactive_mode": true,
  "show_ids": false,
  "show_tags": false,
  "show_year": false,
  "show_author": false,
  "only_attachments": false
}
```

## Processing Order

Zurch processes search requests in a specific order to ensure predictable results:

1. **Search Criteria**: Find all items matching search terms (`-n`, `-a`, `-f`)
2. **Content Filters**: Apply filters like `-o` (attachments), `--books`, `--articles`, `--after`, `--before`
3. **Deduplication**: Remove duplicate items (unless `--no-dedupe` is used)
4. **Result Limiting**: Apply `-x/--max-results` limit as the final step

This means when you specify `-x 5`, you get exactly 5 items from the final processed result set. For example:
- `zurch -n "war crimes" -o -x 5` finds all "war crimes" items, filters for those with attachments, removes duplicates, then shows the first 5
- If you want 5 items before deduplication, use `--no-dedupe`

## Advanced Features

### Interactive Grab with Number Suffix
In interactive mode (default), you can append 'g' to any item number to immediately grab its attachment:

```bash
zurch -f "Papers" -i
# Output shows numbered list:
# 1. Some Paper Title 📕 🔗
# 2. Another Article 📄 🔗  
# 3. Document Without Attachment 📄

# Type "2g" to grab the attachment from item 2
# Type "1" to just view metadata for item 1
```

This works for all searches by default (interactive mode is enabled by default).

### Filter by Attachments Only (-o)
Show only items that have PDF or EPUB attachments:

```bash
# Only show papers with downloadable files
zurch -f "Reading List" -o
zurch -n "machine learning" -o

# Interactive mode works with attachment filtering (default)
zurch -f "Papers" -o  # Browse only items with attachments interactively

# Disable interactive mode with attachment filtering
zurch -f "Papers" -o --nointeract
```

The `-o` flag filters results to include only items with PDF or EPUB attachments, making it easy to find papers you can actually read.

## Examples

### Academic Research Workflow
```bash
# Find all collections related to your research area
zurch -l digital

# Browse a specific collection
zurch -f "Digital Humanities"

# Search for papers on a topic
zurch -n "network analysis"

# Filter by tags to find specific types of papers
zurch -n "social networks" -t "methodology"

# Interactively review papers and grab PDFs (use '3g' to grab item 3) - default behavior
zurch -n "social networks"
```

### Library Management
```bash
# Get overview of your collection structure
zurch -l

# Find items that need attention  
zurch -f "To Read"

# Search for specific authors or topics
zurch -n "foucault"

# Find items by tags
zurch -t "important" -t "methodology"

# Find collections by partial name
zurch -l "digital"
```

## Safety and Compatibility

- **Read-Only Access**: zurch should never modify your Zotero database but use at your own risk
- **Database Locking**: Handles cases where Zotero is running
- **Version Compatibility**: Tested with Zotero 7.0
- **Error Handling**: Graceful handling of database issues
- **Cross-Platform**: Platform-specific path handling
- See the info/ZOTERO_DATABASE_SECURITY_REPORT.md file for an LLM generated threat assessment. 

## Development

zurch is built with:
- **Python 3.8+** for broad compatibility
- **SQLite** for direct database access
- **uv** for modern Python package management
- **pytest** for comprehensive testing

### Building from Source
```bash
git clone <repository>
cd zurch
uv install
uv run pytest  # Run tests
uv build       # Build package
```

## Troubleshooting

### Database Not Found
If zurch can't find your Zotero database:
1. Make sure Zotero is installed and has been run at least once
2. Check the config file and set the correct path
3. Use `zurch -d` for debug information

### Database Locked
If you get a "database locked" error:
1. Close Zotero completely
2. Try the command again
3. If the issue persists, restart your computer

### No Results Found
If searches return no results:
- Check spelling and try partial terms
- Use wildcards in collection filters: `zurch -l "%term%"`
- Use `zurch -l` to see all available collections
- Collection searches use partial matching by default

## Handling Special Characters

When searching for terms containing special shell characters like apostrophes, quotes, or symbols, wrap the search term in quotes:

```bash
# Good - quoted search terms
zurch -n "China's Revolution"
zurch -f "Books & Articles" 
zurch -n "Smith (2020)"

# Will cause shell errors - unquoted special chars
zurch -n China's Revolution    # Shell sees unmatched quote
zurch -f Books & Articles      # Shell interprets & as background process
```

**Special characters that need quoting:** `'` `"` `$` `` ` `` `\` `(` `)` `[` `]` `{` `}` `|` `&` `;` `<` `>` `*` `?`

## Unicode and International Character Support

Zurch fully supports Unicode characters in search terms, including:

```bash
# Chinese characters
zurch -n 中国

# Korean characters
zurch -n 한국

# Unicode punctuation and symbols
zurch -n "café"
```

No special escaping is needed for Unicode characters - they work seamlessly in searches.

## Contributing

Contributions are welcome! Please read the various .md files in the repository help orient yourself. 

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- Thanks to the Zotero developers for such amazing software
- Built for the Zotero research community
- Inspired by the need for command-line access to Zotero data
- Uses the excellent Zotero SQLite database structure
