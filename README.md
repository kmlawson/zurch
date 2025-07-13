# clizot - Zotero CLI

A command-line interface tool to interact with your local Zotero installation and extract information from it.

## Features

- 📂 **List Collections**: Browse all your Zotero collections and sub-collections
- 🔍 **Search Items**: Find items by title or browse specific folders  
- 🎯 **Interactive Mode**: Select items interactively to view metadata or grab attachments
- 📎 **Attachment Management**: Copy PDF, EPUB, and text attachments to your current directory
- 🎨 **Visual Indicators**: Colored icons show attachment types (📘 PDF, 📗 EPUB, 📄 TXT)
- ⚡ **Fast Performance**: Optimized SQLite queries for quick results
- 🔒 **Safe Access**: Read-only database access prevents corruption
- 🖥️ **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

```bash
# Install with uv (recommended)
uv add clizot

# Or install with pip
pip install clizot
```

## Quick Start

```bash
# List all collections
clizot -l

# List collections matching a pattern
clizot -l "*japan*"

# Browse items in a folder
clizot -f "Heritage"

# Search for items by name
clizot -n "medicine"

# Interactive mode to select and view metadata
clizot -f "Heritage" -i

# Interactive mode to grab attachments
clizot -n "China" -i -g
```

## Commands

### List Collections (-l/--list)
```bash
# Show all collections and sub-collections
clizot -l

# Filter collections (partial matching by default)
clizot -l "china"

# Use % wildcard for more control
clizot -l "china%"      # starts with "china"
clizot -l "%history%"   # contains "history"
```

### Browse Folder (-f/--folder)
```bash
# List items in a specific folder
clizot -f "Heritage"

# Limit results
clizot -f "Digital Humanities" -x 10

# Interactive mode
clizot -f "Travel" -i
```

### Search by Name (-n/--name)
```bash
# Search item titles
clizot -n "machine learning"

# Case-insensitive, partial matching
clizot -n "china"
```

### Interactive Mode (-i/--interactive)
When combined with folder or name search, enables interactive selection:
- View detailed metadata for any item
- Navigate through multiple items
- Use with `-g` flag to copy attachments

### Grab Attachments (-g/--grab)
```bash
# Must be used with interactive mode
clizot -f "Papers" -i -g

# Select an item and its attachment will be copied to current directory
```

### Options
- `-x/--max-results N`: Limit number of results (default: 100)
- `-d/--debug`: Enable detailed logging
- `-v/--version`: Show version information
- `-h/--help`: Show help message

## Configuration

clizot automatically discovers your Zotero database. Configuration is stored in:
- **Windows**: `%APPDATA%\clizot\config.json`
- **macOS/Linux**: `~/.clizot-config/config.json`

Example configuration:
```json
{
  "zotero_database_path": "/path/to/Zotero/zotero.sqlite",
  "max_results": 100,
  "debug": false
}
```

## Examples

### Academic Research Workflow
```bash
# Find all collections related to your research area
clizot -l "*digital*"

# Browse a specific collection
clizot -f "Digital Humanities"

# Search for papers on a topic
clizot -n "network analysis"

# Interactively review papers and grab PDFs
clizot -n "social networks" -i -g
```

### Library Management
```bash
# Get overview of your collection structure
clizot -l

# Find items that need attention  
clizot -f "To Read"

# Search for specific authors or topics
clizot -n "foucault"

# Find collections by partial name
clizot -l "digital"
```

## Safety and Compatibility

- **Read-Only Access**: clizot never modifies your Zotero database
- **Database Locking**: Handles cases where Zotero is running
- **Version Compatibility**: Tested with Zotero 7.0
- **Error Handling**: Graceful handling of database issues
- **Cross-Platform**: Platform-specific path handling

## Development

clizot is built with:
- **Python 3.8+** for broad compatibility
- **SQLite** for direct database access
- **uv** for modern Python package management
- **pytest** for comprehensive testing

### Building from Source
```bash
git clone <repository>
cd clizot
uv install
uv run pytest  # Run tests
uv build       # Build package
```

## Troubleshooting

### Database Not Found
If clizot can't find your Zotero database:
1. Make sure Zotero is installed and has been run at least once
2. Check the config file and set the correct path
3. Use `clizot -d` for debug information

### Database Locked
If you get a "database locked" error:
1. Close Zotero completely
2. Try the command again
3. If the issue persists, restart your computer

### No Results Found
If searches return no results:
- Check spelling and try partial terms
- Use wildcards in collection filters: `clizot -l "%term%"`
- Use `clizot -l` to see all available collections
- Collection searches use partial matching by default

## Contributing

Contributions are welcome! Please read the development documentation in `info/DEVNOTES.md` for technical details about the codebase.

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- Built for the Zotero research community
- Inspired by the need for command-line access to Zotero data
- Uses the excellent Zotero SQLite database structure