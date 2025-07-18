# Zurch Feature Suggestions

**Version**: 0.7.10  
**Date**: 2025-01-18  
**Purpose**: Comprehensive list of potential new features and functionality for zurch

## Search & Discovery Features

### 1. Full-Text Search in PDFs (`--search-content`)
- Search within the actual PDF/EPUB content, not just metadata
- Highlight matching text snippets in results
- Would require PDF parsing libraries like PyPDF2
- **Use Case**: Find papers that mention specific concepts even if not in title/abstract

### 2. Smart Search with AI/LLM Integration (`--smart-search`)
- Natural language queries like "papers about climate change from last 5 years"
- Semantic search using embeddings
- Query expansion and synonym matching
- **Use Case**: More intuitive searching for non-technical users

### 3. Related Items Discovery (`--related`)
- Find items similar to a given item based on tags, authors, citations
- "More like this" functionality
- Citation network exploration
- **Use Case**: Literature review expansion, finding related work

### 4. Search History & Saved Searches
- Track previous searches with `--history`
- Save frequently used searches with `--save-search "name"`
- Recall saved searches with `--load-search "name"`
- **Use Case**: Repeated searches for ongoing projects

### 5. Advanced Date Filtering (`--since "3 months"`, `--between "2020-2023"`)
- Relative date filtering (last week, month, year)
- Date range searches
- Filter by added date vs. publication date
- **Use Case**: Finding recent additions or papers from specific periods

## Organization & Management

### 6. Batch Operations
- `--batch-tag` to add tags to multiple items
- `--batch-move` to move items between collections
- `--batch-export` with custom templates
- **Use Case**: Library reorganization and cleanup

### 7. Virtual Collections/Smart Folders
- Create dynamic collections based on search criteria
- Auto-update as new items match criteria
- Save as `.zurch-collection` files
- **Use Case**: Automatic organization without manual sorting

### 8. Reading List Management
- `--add-to-reading-list` flag
- `--show-reading-list` with progress tracking
- Reading status (unread, reading, read) with `--mark-read`
- **Use Case**: Academic reading workflow management

### 9. Duplicate Management Suite
- `--merge-duplicates` to combine metadata from duplicates
- `--show-duplicates` to list all duplicate groups
- `--auto-clean` to automatically remove inferior duplicates
- **Use Case**: Library cleanup and maintenance

## Visualization & Analytics

### 10. Citation Graph Visualization (`--cite-graph`)
- Generate DOT files for Graphviz
- Show citation relationships between items
- Export to various graph formats
- **Use Case**: Understanding research lineage and impact

### 11. Research Timeline (`--timeline`)
- Chronological view of items by publication date
- ASCII art timeline in terminal
- Export to HTML timeline
- **Use Case**: Visualizing research evolution over time

### 12. Co-author Network Analysis (`--coauthor-network`)
- Identify collaboration patterns
- Find most connected authors
- Export collaboration statistics
- **Use Case**: Understanding research communities

### 13. Research Metrics Dashboard (`--metrics`)
- Publication trends over time
- Most cited items (if citation data available)
- Tag cloud visualization
- Reading velocity tracking
- **Use Case**: Research productivity analysis

## Integration Features

### 14. BibTeX/RIS Import/Export
- `--import-bib file.bib` to add items
- `--export-bib` with customizable templates
- Round-trip compatibility
- **Use Case**: Interoperability with other reference managers

### 15. Markdown Note Integration
- `--export-obsidian` for Obsidian-compatible notes
- `--export-roam` for Roam Research
- Include metadata as YAML frontmatter
- **Use Case**: Knowledge management system integration

### 16. Git Integration for Libraries
- `--track-changes` to see what's new since last check
- `--diff "2024-01-01"` to show changes since date
- Export change logs
- **Use Case**: Version control for research libraries

### 17. API Server Mode (`--serve`)
- RESTful API for zurch functionality
- Web UI for remote access
- Webhook support for automation
- **Use Case**: Building custom tools on top of zurch

## Enhanced User Experience

### 18. Interactive TUI (Terminal UI)
- Full ncurses-based interface with `--tui`
- Mouse support for clicking items
- Split panes for browsing while reading metadata
- Built-in file preview
- **Use Case**: More intuitive browsing for visual users

### 19. Fuzzy Search Everything (`--fuzzy`)
- Fuzzy matching for collections, tags, authors
- Typo-tolerant search
- Phonetic matching for author names
- **Use Case**: Finding items despite typos or uncertain spelling

### 20. Plugin System
- `--plugin` to load custom Python modules
- Hook system for extending functionality
- Community plugin repository
- Custom export formats, search providers, etc.
- **Use Case**: Extensibility without modifying core code

## Bonus Ideas

### OCR Support
- Extract text from scanned PDFs
- Make non-searchable PDFs searchable
- **Use Case**: Older papers and scanned documents

### Language Detection
- Filter by document language
- Auto-detect language from content
- **Use Case**: Multilingual research libraries

### Reading Time Estimation
- Calculate based on word count
- Track actual reading time
- **Use Case**: Time management for researchers

### Annotation Export
- Extract highlights and comments from PDFs
- Export in various formats (Markdown, JSON)
- **Use Case**: Note-taking and annotation workflows

### Sync Status
- Show which items are synced to Zotero cloud
- Identify sync conflicts
- **Use Case**: Multi-device workflows

### Custom Fields
- Search and display custom Zotero fields
- Support for specialized metadata
- **Use Case**: Discipline-specific metadata

### Recommendation Engine
- Suggest papers based on reading history
- Collaborative filtering with other users
- **Use Case**: Discovery of relevant literature

## Implementation Considerations

These features would enhance zurch's utility while maintaining its philosophy of being a powerful, terminal-based interface to Zotero data. Priority should be given to features that:

1. Maintain read-only database access
2. Work well in terminal environments
3. Integrate smoothly with existing workflows
4. Have clear command-line interfaces
5. Don't require significant external dependencies

Features could be implemented incrementally, with simpler ones (like advanced date filtering) being good starting points, while more complex ones (like AI integration or TUI) could be longer-term goals.