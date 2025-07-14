# zurch - Zotero Search CLI

A command-line interface tool to interact with your local Zotero installation and extract information from it.

## Features

- 📂 **List Collections**: Browse all your Zotero collections and sub-collections
- 🔍 **Search Items**: Find items by title or browse specific folders  
- 🎯 **Interactive Mode**: Select items interactively to view metadata or grab attachments
- 📎 **Attachment Management**: Copy PDF, EPUB, and text attachments to your current directory
- 🎨 **Visual Indicators**: Icons show item types (📗 books, 📄 articles) and attachments (🔗 PDF/EPUB available)
- ⚡ **Fast Performance**: Optimized SQLite queries for quick results
- 🔒 **Safe Access**: Read-only database access prevents corruption
- 🖥️ **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

```bash
# Install with uv (recommended)
uv add zurch

# Or install with pip
pip install zurch
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

# Interactive mode to grab attachments
zurch -n "China" -i -g

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
```

### Browse Folder (-f/--folder)
```bash
# List items in a specific folder
zurch -f "Heritage"

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
- Use with `-g` flag to copy attachments

### Grab Attachments (-g/--grab)
```bash
# Must be used with interactive mode
zurch -f "Papers" -i -g

# Select an item and its attachment will be copied to current directory
```

### Filtering Options
- `-o/--only-attachments`: Show only items with PDF/EPUB attachments
- `--books`: Show only book items in search results  
- `--articles`: Show only journal article items in search results
- `--after YEAR`: Show only items published after this year (inclusive)
- `--before YEAR`: Show only items published before this year (inclusive)
- `-t/--tag TAG [TAG...]`: Filter by tags (case-insensitive, multiple tags = AND logic)
- `-k/--exact`: Use exact matching instead of partial matching

### Other Options
- `-x/--max-results N`: Limit number of results (default: 100) - **Applied as final step after all filtering and deduplication** - **Applied as final step after all filtering and deduplication**
- `-d/--debug`: Enable detailed logging and show purple duplicates
- `-v/--version`: Show version information
- `-h/--help`: Show help message
- `--id ID`: Show metadata for a specific item ID
- `--showids`: Show item ID numbers in search results
- `--getbyid ID [ID...]`: Grab attachments for specific item IDs
- `--no-dedupe`: Disable automatic duplicate removal

### Duplicate Detection
zurch automatically removes duplicate items based on title, author, and year matching:
- **Prioritizes items with attachments** (PDF/EPUB) over those without
- **Selects most recently modified** items when attachments are equal
- **Debug mode (`-d`)** shows all duplicates in purple for investigation
- **`--no-dedupe`** flag disables deduplication to see raw database contents

Example: Search for "World History" reduces 8 duplicate items to 2 unique results.

## Configuration

zurch automatically discovers your Zotero database. Configuration is stored in OS-appropriate locations:
- **Windows**: `%APPDATA%\zurch\config.json`
- **macOS**: `~/Library/Application Support/zurch/config.json`
- **Linux**: `~/.config/zurch/config.json` (or `$XDG_CONFIG_HOME/zurch/config.json`)

**Note**: If you're upgrading from an earlier version, zurch will automatically migrate your config from the old `~/.zurch-config/` location to the new standard location.

Example configuration:
```json
{
  "zotero_database_path": "/path/to/Zotero/zotero.sqlite",
  "max_results": 100,
  "debug": false
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

# Interactively review papers and grab PDFs
zurch -n "social networks" -i -g
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

- **Read-Only Access**: zurch never modifies your Zotero database
- **Database Locking**: Handles cases where Zotero is running
- **Version Compatibility**: Tested with Zotero 7.0
- **Error Handling**: Graceful handling of database issues
- **Cross-Platform**: Platform-specific path handling

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

# Japanese characters  
zurch -n 日本

# Korean characters
zurch -n 한국

# Unicode punctuation and symbols
zurch -n "–"
zurch -n "café"
```

No special escaping is needed for Unicode characters - they work seamlessly in searches.

## Contributing

Contributions are welcome! Please read the development documentation in `info/DEVNOTES.md` for technical details about the codebase.

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- Built for the Zotero research community
- Inspired by the need for command-line access to Zotero data
- Uses the excellent Zotero SQLite database structure