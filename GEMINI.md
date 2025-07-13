zurch - Zotero Search CLI

The goal of this CLI application is to interface with a local Zotero installation and be able to extract information from it.

# Guidelines

- use only uv to build this tool, each time you complete tasks, uninstall it, purge uv cache, and reinstall it for testing
    - when reinstalling: `uv tool uninstall zurch && uv cache clean && uv tool install .`
    - for testing install with uv tool install
- keep the code files small, divide things into cli.py, utils.py, search.py, etc. with each collection of features and functions divided into small manageable files
- write unit tests for all new features before developing a feature
- git commit after completion of features or fixing of problems. Update CHANGELOG.md file and README.md when relevant
- keep all tests in a 'tests' folder and move them there if they are not already there, keep the test files short and grouped by function
- eventually this will go on pypi - structure the files so they will work for that structure
- don't overclog the main directory - keep files in appropriate directories


# gitignore

- add as appropriate in your judgement but be sure to include:
    - CLAUDE.md
    - zotero-database-example/

# Desired Features

- stores config data in ~/.config/zurch/zurch.json or appropriate location for the OS (Linux, Windows, Mac)
- has a -d/--debug mode with very detailed logging to help with debugging
- has a -h/--help and -v/--version flag
- has an up to date, detailed and helpful README.md
- has a git repository with this CLAUDE.md file and other relevant files added to gitignore
- NEVER attempts to write or modify the Zotero database, read only
- Is configured to attach to one single Zotero installation
- -f/--folder [folder name] will return a list of the titles of all items in the named folder in the Zotero database. 
    - If there are multiple folders with that exact name, it lists the least "deep" folders first and then lists contents of other folders next in order of depth
    - Items that have attached pdf, epub, or txt files will have a blue, green, or grey book icon after them to reveal this fact
    - the items will be listed by number, padded with spaces
    - if items are in sub-folders, they should be listed hierarchically under their sub-folder
    - if the -i/--interactive flag is also present then it will prompt the user for a number or 0 for cancel. If the -g flag is not present it will merely output all the metadata for that option and return to the prompt for a number. If the -g flag is present it will grab the attachment for that item (if present) and copy it to the current directory
    - a config file variable (default 100) will determine max number of returned hits which can be overriden with -x [number]
    - if [folder name] returns no hits, list 5 closest matches among folders.
- -n/--name [item name] will turn a list of all titles that match all the keywords provided from the Zotero database. 
    - If -k flag is present, then exact search on the supplied [item name] rather than all keywords present 
    - Items that have attached pdf, epub, or txt files will have a blue, green, or grey book icon after them to reveal this fact
    - the items will be listed by number, padded with spaces
    - if the -i/--interactive flag is also present then it will prompt the user for a number or 0 for cancel. If the -g flag is not present it will merely output all the metadata for that option and return to the prompt for a number. If the -g flag is present it will grab the attachment for that item (if present) and copy it to the current directory
    - a config file variable (default 100) will determine max number of returned hits which can be overriden with -x [number]
- -l/--list will return a list of all folders and -sub-folders and allows [search term] argument to do a search of partial matches for a directory. These are listed in hierarchical manner to show what folders are in what. If flag -k is present then only exact search.

# Important Implementation Note

- **-x flag behavior**: The -x/--max-results flag should ALWAYS be applied as the final operation after ALL other processing is complete. The sequence should be:
  1. Find all items matching the search criteria (-n, -a, -f)
  2. Apply content-based filters (-o for attachments, --books, --articles, --after, --before)
  3. Apply deduplication (unless --no-dedupe is used)
  4. **THEN** apply the -x limit as the very last step
  
  This ensures that when -x 5 is specified, the user gets exactly 5 results from the final processed set (unless fewer than 5 items exist after all processing). The -x limit should never be applied before deduplication, as this would cause fewer results than expected when duplicates are removed.

# Research Notes

- you need to explore the sqlite in zotero-database-example in order to understand how to interact with the database

# Documentation Tasks

- you should read the documentation available at https://www.zotero.org/support/dev/client_coding and write detailed notes in info/DEVNOTES.md
