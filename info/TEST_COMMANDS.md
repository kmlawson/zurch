# Test Commands for Zurch

This document contains a comprehensive list of test commands used to verify zurch functionality after major changes or releases.

## Installation Testing

```bash
# Reinstall zurch following CLAUDE.md guidelines
uv tool uninstall zurch && uv cache clean && uv tool install .

# Verify installation
zurch --version
```

## Core Feature Testing

### Collection Listing (-l)

```bash
# Test collection listing with limit
zurch -l -x 5

# Test collection listing in non-interactive mode
zurch -l -x 5 --nointeract

# Test with interactive prompt cancellation
echo "0" | zurch -l -x 5
```

### Folder Browsing (-f)

```bash
# Test folder browsing in non-interactive mode
zurch -f "General" -x 3 --nointeract

# Test with interactive mode (automated)
echo -e "0" | zurch -f "General" -x 3
```

### Name Search (-n)

```bash
# Test name search in non-interactive mode
zurch -n "history" -x 3 --nointeract

# Test interactive name search with item selection
echo -e "1\n0" | zurch -n "history" -x 3
```

### Author Search (-a)

```bash
# Test author search
zurch -a "smith" -x 2 --nointeract
```

## Interactive Mode Testing

```bash
# Test interactive mode with item selection and metadata view
echo -e "1\n0" | zurch -n "history" -x 3

# Test returning to list from metadata view
echo -e "1\nl\n0" | zurch -n "test" -x 3
```

## Advanced Features Testing

### Database Statistics

```bash
# Test database stats (show first 10 lines)
zurch --stats | head -10
```

### Item Lookup by ID

```bash
# Test item lookup by specific ID
zurch --id 12345
```

### Export Functionality

```bash
# Test CSV export
zurch -n "test" --export csv --file /tmp/test_export.csv --nointeract -x 5

# Verify export file creation
ls -la /tmp/test_export.csv

# Test JSON export
zurch -n "test" --export json --file /tmp/test_export.json --nointeract -x 3
```

### Display Options

```bash
# Test showing tags
zurch -n "test" --showtags -x 2 --nointeract

# Test showing notes icons
zurch -n "test" --shownotes -x 2 --nointeract

# Test showing years and authors
zurch -n "history" --showyear --showauthor -x 3 --nointeract

# Test showing IDs
zurch -n "test" --showids -x 3 --nointeract

# Test showing collections
zurch -n "test" --showcollections -x 2 --nointeract
```

### Filtering Options

```bash
# Test only attachments
zurch -n "test" -o -x 3 --nointeract

# Test date filtering
zurch -n "history" --after 2020 -x 3 --nointeract
zurch -n "history" --before 2000 -x 3 --nointeract

# Test item type filtering
zurch -n "history" --books -x 3 --nointeract
zurch -n "history" --articles -x 3 --nointeract

# Test exact matching
zurch -n "history" -k -x 3 --nointeract
```

### Sorting Options

```bash
# Test sorting by date
zurch -n "history" --sort date -x 3 --nointeract

# Test sorting by author
zurch -n "history" --sort author -x 3 --nointeract

# Test sorting by title
zurch -n "history" --sort title -x 3 --nointeract
```

### Notes Features

```bash
# Test filtering items with notes
zurch -n "test" --withnotes -x 3 --nointeract

# Test getting notes content
zurch -n "test" --getnotes -x 1 --nointeract

# Test showing notes in metadata view
echo -e "1\nt\n0" | zurch -n "test" -x 3
```

## Error Handling Testing

```bash
# Test with non-existent collection
zurch -f "NonExistentCollection" --nointeract

# Test with empty search
zurch -n "xyzabcnotfound" --nointeract

# Test with invalid item ID
zurch --id 999999999
```

## Performance Testing

```bash
# Test large result sets
zurch -n "the" -x 50 --nointeract

# Test without deduplication
zurch -n "history" --no-dedupe -x 10 --nointeract

# Test with unlimited results (use with caution)
# zurch -n "a" -x all --nointeract
```

## Configuration Testing

```bash
# Test configuration wizard (requires manual input)
# zurch --config

# Test debug mode
zurch -n "test" -d -x 2 --nointeract
```

## Cross-Platform Testing

```bash
# Test help display
zurch --help

# Test version display
zurch --version

# Test with special characters in search
zurch -n "中国" -x 2 --nointeract
zurch -n "日本" -x 2 --nointeract
```

## Regression Testing Commands

Run these commands after any major code changes to ensure no functionality is broken:

```bash
# Quick functionality check
zurch --version && \
zurch --stats | head -5 && \
zurch -l -x 3 --nointeract && \
zurch -n "test" -x 2 --nointeract && \
zurch -f "General" -x 2 --nointeract && \
echo "All basic tests passed"
```

## Expected Behaviors

- All commands should execute without errors
- Interactive prompts should respond correctly to input
- Non-interactive mode should not hang waiting for input
- Export commands should create files successfully
- Search results should show proper item counts and duplicate removal
- Icons should display correctly for different item types and attachments
- Progress indicators should appear for longer operations
- Unicode text should display properly across all platforms

## Notes

- Use `--nointeract` flag for automated testing to prevent hanging on prompts
- Test with both small (`-x 2`) and medium (`-x 10`) result limits
- Verify that duplicate removal is working by checking result counts
- Test interactive features using echo input piping: `echo -e "1\n0" | zurch ...`
- Always test the most commonly used features first: `-l`, `-f`, `-n`, `-a`