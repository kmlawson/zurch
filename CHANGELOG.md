# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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