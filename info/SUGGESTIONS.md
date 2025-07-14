# Suggestions for `zurch`

This document outlines suggestions for improving the `zurch` command-line tool. The suggestions are divided into two sections: enhancements to existing features and proposals for new functionality.

## I. Existing Feature Enhancements

This section details recommendations for refining the current capabilities of `zurch`.

### 1. Combined Author and Title Search

**Current State:** The tool supports searching by author (`-a`) or by title (`-n`) and tags (`-t`), but does not allow for combining author and title searches in a single query. The `search_items_combined` function in `zurch/search.py` has a `TODO` indicating this is a simplified implementation.

**Suggestion:** Implement a true combined search that allows users to filter by both author and title simultaneously.

**Implementation Details:**
- Modify the `build_name_search_query` and `build_author_search_query` in `zurch/queries.py` to accept both author and title parameters, adding the necessary `JOIN`s and `WHERE` clauses to filter on both `items.title` and `creators.lastName`.
- Update `zurch/handlers.py` to properly pass both arguments to the search function.
- This would likely involve creating a new query-building function that dynamically constructs the SQL query based on the presence of author, title, and tag arguments.

### 2. More Granular Date Filtering

**Current State:** The `--after` and `--before` flags filter by year.

**Suggestion:** Enhance date filtering to allow for more specific date ranges, such as by month or a specific date.

**Implementation Details:**
- The `items` table in Zotero's database has a `dateAdded` and `dateModified` field. The `itemDataValues` table also contains date information. The query logic in `zurch/queries.py` could be updated to parse more complex date strings (e.g., "2023-01-15") and use them in the `WHERE` clause of the SQL query.
- The `argparse` configuration in `zurch/parser.py` would need to be updated to accept these new date formats.

### 3. Improved Interactive Mode

**Current State:** The interactive mode is functional but could be more user-friendly. For example, after viewing an item's metadata, the user is returned to the prompt but the list of items is not re-displayed.

**Suggestion:** Improve the interactive experience by providing more context and options.

**Implementation Details:**
- In `zurch/handlers.py`, modify the `interactive_selection` and `handle_interactive_mode` functions to re-display the list of items after an action (like viewing metadata) is completed.
- Add a "help" command within the interactive prompt that lists available actions (e.g., `g` to grab, `m` to view metadata, `q` to quit).

### 4. Fuzzy Searching for Collections and Items

**Current State:** Searching for collections (`-f`) or items (`-n`) relies on exact or partial string matching. If a user misspells a word, no results are returned.

**Suggestion:** Implement fuzzy searching to account for typos and minor variations in search terms.

**Implementation Details:**
- Integrate a library like `thefuzz` (formerly `fuzzywuzzy`) to calculate string similarity scores.
- In `zurch/handlers.py`, when a search yields no results, a secondary search could be triggered that uses fuzzy matching to find the most likely intended target and present it as a suggestion. For example, in `handle_folder_command`, the `find_similar_collections` could be augmented with fuzzy matching.

## II. New Feature Suggestions

This section proposes new features to expand the functionality of `zurch` as a read-only data extraction tool.

### 1. Full-Text Search of Attachments

**Suggestion:** Add the ability to search the full text of attached PDF and text files. This would be a powerful feature for researchers.

**Implementation Details:**
- This is a complex feature that would require an indexing strategy.
- A new command, e.g., `zurch --full-text "search term"`, would trigger this functionality.
- A pre-processing step would be needed to extract text from PDFs (using a library like `PyMuPDF` or `pdfplumber`) and other documents.
- The extracted text would need to be stored in an index. This could be a separate SQLite FTS5 table, or an external search index like Whoosh or a lightweight search engine.
- The search command would then query this index and return the items whose attachments contain the search term.
- Given the read-only nature of the tool, the index would need to be stored separately from the Zotero database, perhaps in the `~/.config/zurch` directory. An initial "index" command would be needed to build the index, and a "re-index" command to update it.

### 2. Exporting Search Results

**Suggestion:** Allow users to export search results to common formats like CSV, JSON, or BibTeX.

**Implementation Details:**
- Add a new flag, e.g., `--export [format]`, to the search commands.
- In `zurch/handlers.py`, after a search is performed, if the `--export` flag is present, the results would be formatted accordingly.
- For CSV, the `csv` module in Python's standard library could be used.
- For JSON, the `json` module can be used.
- For BibTeX, a library like `bibtexparser` would be required to correctly format the entries. The data for the BibTeX file would be retrieved using the existing metadata functions.
- The output could be written to a file or printed to standard output.

### 3. Listing and Searching Tags

**Suggestion:** Add a dedicated command for listing all available tags and searching for items by tag.

**Implementation Details:**
- A new command, e.g., `zurch --list-tags`, would list all unique tags in the database. The `get_all_tags` function already exists in `zurch/search.py`.
- The existing `-t` or `--tag` flag is already implemented for filtering, but a primary search by tag could be made more explicit. For example `zurch --search-by-tag "methodology"`.

### 4. Displaying Item Relationships

**Suggestion:** Zotero allows users to define relationships between items (e.g., "is supplemented by"). Add a feature to display these relationships.

**Implementation Details:**
- The `itemRelations` table in the Zotero database stores these relationships.
- A new function in `zurch/metadata.py` would be needed to query this table and retrieve the related items. The `get_item_relations` function already exists.
- When displaying an item's metadata, this new function could be called to show a list of related items, which could also be interactive, allowing the user to jump to the metadata of a related item.

### 5. Advanced Statistics and Reporting

**Suggestion:** Provide a command to generate statistics about the Zotero library.

**Implementation Details:**
- A new command, e.g., `zurch --stats`, could provide a report with information like:
    - Total number of items, collections, and tags.
    - A breakdown of items by type (book, article, etc.).
    - A list of the most frequently used tags.
    - A count of items with and without attachments.
- The necessary queries would be added to `zurch/queries.py` and the logic to `zurch/handlers.py`. This would leverage existing functions like `get_all_item_types`, `get_all_tags`, etc.
