# Todo

## Add -g feature [✅] 

- -g and [number]g copying of the PDF to the current directory should rename the file "[author last name] -" (if available) and by the title of the article (up to a reasonable character limit and carefully sanitized to display correctly on MacOS, Linux, or Windows systems). Example:

Smith - Title of Book.pdf
Title of Book.pdf (if no last name available)
Smith - Truncated Name of Very Long Book Titl.pdf

**✅ COMPLETED in v0.6.5** - Enhanced attachment grabbing with author + title naming, cross-platform sanitization, and conflict resolution.

## Add Tags to meta data [✅] 

When showing the meta data for an item, show the tags it has too in a list: 

**Tags:** China | Gender | History / Modern 

**✅ COMPLETED in v0.6.5** - Tags now display in metadata view with pipe-separated format.

## --showtags feature [✅]

When the flag is active, any list of item titles will, in a different color, show the tags divided by "|" for each item on the next line under it.

**✅ COMPLETED in v0.6.5** - Added --showtags flag that shows tags under item titles in muted gray color.

## clean up -h [✅]

The -h is a bit too much with wrapping lines, is there a way to clean it up and make it clearer on small terminal screens, perhaps keeping lines shorter for descriptions of features?

**✅ COMPLETED in v0.6.6** - Help display cleaned up with RawDescriptionHelpFormatter and shorter descriptions.

## export feature [✅]

**Implementation Details:**
- Add a new flag, e.g., `--export [format]`, to the search commands.
- For CSV, the `csv` module in Python's standard library could be used.
- For JSON, the `json` module can be used.
- if --file is present with path, then save the export to that path and file (NO OVERWRITING and check to make sure the path is not in a dangerous place such as system related folders in MacOS, Windows or Linux)
- if --file is not present, then save it in the current directory
- if a path has non-existant directories, ask if the user wants to create a directory in that spot.

**✅ COMPLETED in v0.6.6** - Added comprehensive export functionality with CSV/JSON formats, safety checks, and file conflict resolution.

## --showyear feature [✅]

- includes the year of publication when it is available for an item in all search item lists

**✅ COMPLETED in v0.6.6** - Added --showyear flag that displays publication year in parentheses after item titles.

## --showauthor feature [✅]

- includes the first author (last and first) of an item after the title

**✅ COMPLETED in v0.6.6** - Added --showauthor flag that shows first author name after title with " - " separator.

## config wizard

- create a `--config` which prompts the user to set each of the config options and saves it. 
- should show current values as the prompts are given for each config variable
- should report where the config file is being saved 


## Improve the Config file

Make it possible to have these flags by default in the config file:

showids (default: false)
showtags (default: false)
showyear (default: false)
showauthor (default: false)
onlyattachments (default: false) - runs all searches with -o

