# Zurch v0.7.8: Future Development Ideas & New Features

*Generated on 2025-07-16*

This document outlines potential new features and future development directions for the Zurch project, building upon the existing v0.7.8 codebase.

## 1. Core Functionality Enhancements

### 1.1. Full-Text Search (FTS)
- **Concept:** Integrate with SQLite's FTS5 extension to enable searching the *content* of indexed PDFs and text attachments, not just metadata.
- **Implementation:**
    -   Add a command, e.g., `zurch --fts "search query"`, to perform a full-text search.
    -   The tool would need to check if the Zotero database has FTS enabled on the `pdfFullText` table.
    -   This would be a read-only operation, but it would dramatically increase the tool's power for researchers.

### 1.2. "Related Items" Discovery
- **Concept:** Add a command to find items related to a given item ID. `zurch --related <item_id>`.
- **Implementation:**
    -   **By Shared Collections:** Find other items in the same collections.
    -   **By Shared Tags:** Find other items with overlapping tags.
    -   **By Shared Authors:** Find other works by the same authors.
    -   The results could be presented in a ranked list based on the number of shared connections.

### 1.3. Note Searching and Management
- **Concept:** Extend search capabilities to include Zotero notes.
- **Implementation:**
    -   `zurch --notes "search term"`: Search the content of all notes.
    -   `zurch --id <item_id> --shownotes`: Display notes attached to a specific item when showing its metadata.

## 2. Advanced Search & Filtering

### 2.1. Date Range and Relative Date Filtering
- **Concept:** Enhance date filtering beyond simple years.
- **Implementation:**
    -   `--date-range YYYY-MM-DD:YYYY-MM-DD`: Search for items with `dateAdded` or `dateModified` within a specific range.
    -   `--since "1 month ago"` or `--since 2w`: Use relative date parsing to find recently added items.

### 2.2. Search by Attachment Content Type
- **Concept:** Allow filtering by specific attachment types beyond the existing PDF/EPUB flag.
- **Implementation:**
    -   `--attachment-type pdf,html,txt`: Search for items that have any of the specified attachment types.

### 2.3. Saved Searches
- **Concept:** Allow users to save complex search queries and re-run them with a simple alias.
- **Implementation:**
    -   `zurch --save-search <alias> -n "complex search" --author "smith" --after 2020`
    -   `zurch --run-search <alias>`
    -   Saved searches could be stored in the `config.json` file.

## 3. Integration & Automation

### 3.1. Shell Completion Scripts
- **Concept:** Generate shell completion scripts for Bash, Zsh, and Fish.
- **Implementation:**
    -   `zurch --generate-completion bash`: Outputs the completion script to `stdout`.
    -   This would provide auto-completion for commands, flags, and potentially even collection names.

### 3.2. "Watch" Mode
- **Concept:** A persistent mode that watches the Zotero database for changes and triggers actions.
- **Implementation:**
    -   `zurch --watch --folder "Inbox" --exec "/path/to/script.sh {{itemID}}"`
    -   This could be used to automatically process new items, e.g., run OCR, rename files, or send notifications.
    -   This would require periodically checking the `dateModified` of items or collections.

### 3.3. BibTeX / CSL-JSON Output
- **Concept:** Directly output bibliographic data for selected items in standard formats.
- **Implementation:**
    -   `zurch --id <item_id> --bibtex`: Output the BibTeX entry for a single item.
    -   `zurch -n "search" --export bibtex`: Export all search results as a `.bib` file.
    -   This would require a Python library to generate BibTeX or CSL-JSON from the Zotero data, or careful manual construction.

## 4. User Experience (UX) & Interface

### 4.1. Enhanced Interactive Mode with `prompt_toolkit`
- **Concept:** Replace the custom `keyboard.py` and pagination logic with a powerful library like `prompt_toolkit`.
- **Implementation:**
    -   This would provide cross-platform arrow key navigation, better history, and more robust interactive controls out-of-the-box.
    -   It would also unify the pagination experience across all commands.

### 4.2. TUI (Text-based User Interface) Mode
- **Concept:** An optional, more advanced interface using a library like `Textual`.
- **Implementation:**
    -   `zurch --tui`
    -   This would launch a full-screen TUI with panes for collections, items, and metadata, providing a more app-like experience within the terminal.

### 4.3. Man Page Generation
- **Concept:** Provide a proper man page for the tool.
- **Implementation:**
    -   `zurch --man`: Display a formatted man page.
    -   This could be generated from the `argparse` definition using a tool like `help2man` or `sphinx-argparse`.

## 5. Output & Exporting

### 5.1. Customizable Export Templates
- **Concept:** Allow users to define their own export formats using a simple templating language.
- **Implementation:**
    -   `--export-template "{{author_lastname}} ({{year}}) - {{title}}.pdf"`
    -   This could be used for flexible file renaming or generating custom text snippets.

### 5.2. Export to Markdown Table
- **Concept:** Add a new export format that creates a clean Markdown table, ready to be pasted into documents.
- **Implementation:**
    -   `--export md`

### 5.3. "Zotero Select" URL Output
- **Concept:** For any item, provide the `zotero://select` URL, which can be used to jump directly to that item in the Zotero desktop client.
- **Implementation:**
    -   `zurch --id <item_id> --url`: Output the `zotero://select/library/items/<itemKey>` URL.
    -   This requires fetching the `itemKey` from the database.
