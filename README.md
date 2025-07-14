# zurch - Zotero Search CLI

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
- Provides READ ONLY access to your Zotero database 
- Designed for macOS, may work on Windows and Linux

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
# List all collections
zurch -l

# List collections matching a pattern
zurch -l "*japan*"

# Browse items in a folder
zurch -f "Heritage"

# Search for items by name
zurch -n "medicine"

# Interactive mode to select and view metadata
zurch -f "Heritage" -i

# Interactive mode to grab attachments (append 'g' to item number)
zurch -n "China" -i

# Show only items with PDF/EPUB attachments
zurch -f "Heritage" -o

# Interactive grab with number suffix
zurch -f "Papers" -i
# Then type: 5g (to grab attachment from item 5)

# Debug mode shows duplicates in purple
zurch -n "World History" -d

# Look up specific item by ID
zurch --id 12345

# Disable duplicate removal to see all database entries
zurch -n "duplicate article" --no-dedupe

# Show comprehensive database statistics
zurch --stats

# Show tags under item titles
zurch -n "research methods" --showtags

# Show year and author information
zurch -n "machine learning" --showyear --showauthor

# Export search results to CSV
zurch -n "digital humanities" --export csv

# Export to specific file path
zurch -n "methodology" --export json --file ~/research/methods.json
```

## Commands

### List Collections (-l/--list)
```bash
# Show all collections and sub-collections
zurch -l

# Filter collections (partial matching by default)
zurch -l "china"

# Use % wildcard for more control
zurch -l "china%"      # starts with "china"
zurch -l "%history%"   # contains "history"

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

# Interactive mode
zurch -f "Travel" -i
```

### Search by Name (-n/--name)
```bash
# Search item titles (supports AND logic for multiple words)
zurch -n machine learning    # Finds items with BOTH "machine" AND "learning"
zurch -n "machine learning"  # Finds items with exact phrase "machine learning"

# Case-insensitive, partial matching
zurch -n "china"

# Wildcard patterns
zurch -n "china%"    # Titles starting with "china"
zurch -n "%history"  # Titles ending with "history"  
zurch -n "%war%"     # Titles containing "war"
```

### Search by Author (-a/--author)
```bash
# Search by author name (supports AND logic for multiple words)
zurch -a smith       # Find items by authors named "smith"
zurch -a john smith  # Find items by authors with BOTH "john" AND "smith"
zurch -a "john smith"# Find items by author with exact name "john smith"

# Works with first or last names
zurch -a benjamin    # Finds Benjamin Franklin, Benjamin Netanyahu, etc.
```

### Filter by Tags (-t/--tag)
```bash
# Search by tag alone (case-insensitive)
zurch -t methodology  # Find all items tagged with "methodology"
zurch -t china japan  # Find items tagged with BOTH "china" AND "japan"
zurch -t "digital humanities"  # Find items tagged with exact phrase

# Combine with other searches for more specific results
zurch -n "machine learning" -t "data science"  # Items about ML tagged with data science
zurch -f "Research" -t "to-read"  # Items in Research folder tagged as to-read
zurch -a smith -t china  # Items by Smith tagged with china

# Multiple tags = AND logic (item must have ALL tags)
zurch -t "important" "methodology" "python"  # Items with all three tags
```

### Interactive Mode (-i/--interactive)
When combined with folder or name search, enables interactive selection:
- View detailed metadata for any item
- Navigate through multiple items
- Select an item and its attachment will be copied to current directory if you add g after the number
```

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
- `--showcollections`: (Coming soon) Show collections each item belongs to

### Export Options
- `--export [csv|json]`: Export search results to CSV or JSON format
- `--file PATH`: Specify output file path for export (defaults to current directory)

### Other Options
- `-x/--max-results N`: Limit number of results (default: 100) - **Applied as final step after all filtering and deduplication**
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
- Setting default display options (IDs, tags, year, author)
- Configuring search defaults
- Setting maximum results limit

### Manual Configuration
Configuration is stored in OS-appropriate locations:
- **Windows**: `%APPDATA%\zurch\config.json`
- **macOS**: `~/Library/Application Support/zurch/config.json`
- **Linux**: `~/.config/zurch/config.json` (or `$XDG_CONFIG_HOME/zurch/config.json`)

**Note**: If you're upgrading from an earlier version, zurch will automatically migrate your config from the old `~/.zurch-config/` location to the new standard location.

Example configuration:
```json
{
  "zotero_database_path": "/path/to/Zotero/zotero.sqlite",
  "max_results": 100,
  "debug": false,
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
In interactive mode (`-i`), you can append 'g' to any item number to immediately grab its attachment:

```bash
zurch -f "Papers" -i
# Output shows numbered list:
# 1. Some Paper Title 📕 🔗
# 2. Another Article 📄 🔗  
# 3. Document Without Attachment 📄

# Type "2g" to grab the attachment from item 2
# Type "1" to just view metadata for item 1
```

This works for both `-f` (folder) and `-n` (name) searches with `-i`.

### Filter by Attachments Only (-o)
Show only items that have PDF or EPUB attachments:

```bash
# Only show papers with downloadable files
zurch -f "Reading List" -o
zurch -n "machine learning" -o

# Combine with interactive mode
zurch -f "Papers" -o -i  # Browse only items with attachments
```

The `-o` flag filters results to include only items with PDF or EPUB attachments, making it easy to find papers you can actually read.

## Examples

### Academic Research Workflow
```bash
# Find all collections related to your research area
zurch -l "*digital*"

# Browse a specific collection
zurch -f "Digital Humanities"

# Search for papers on a topic
zurch -n "network analysis"

# Filter by tags to find specific types of papers
zurch -n "social networks" -t "methodology"

# Interactively review papers and grab PDFs (use '3g' to grab item 3)
zurch -n "social networks" -i
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
