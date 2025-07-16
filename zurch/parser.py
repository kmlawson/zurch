import argparse
from . import __version__

def add_basic_arguments(parser: argparse.ArgumentParser) -> None:
    """Add basic arguments like version, debug, etc."""
    parser.add_argument(
        "-v", "--version", 
        action="version", 
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "-d", "--debug", 
        action="store_true", 
        help="Enable debug mode with detailed logging"
    )
    
    parser.add_argument(
        "-x", "--max-results", 
        type=str, 
        default="100",
        help="Maximum number of results to return (default: 100, use 'all' or '0' for unlimited)"
    )

def add_mode_arguments(parser: argparse.ArgumentParser) -> None:
    """Add interactive mode arguments."""
    parser.add_argument(
        "-i", "--interactive", 
        action="store_true",
        help="Enable interactive mode (default: enabled, append 'g' to item number to grab attachment)"
    )
    
    parser.add_argument(
        "--nointeract", 
        action="store_true",
        help="Disable interactive mode (return to simple list output)"
    )
    
    parser.add_argument(
        "-p", "--pagination", 
        action="store_true",
        help="Enable pagination for long result lists (n=next, p=previous, 0=exit)"
    )

def add_search_arguments(parser: argparse.ArgumentParser) -> None:
    """Add search-related arguments."""
    parser.add_argument(
        "-f", "--folder", 
        type=str,
        nargs='+',
        help="List items in the specified folder"
    )
    
    parser.add_argument(
        "-n", "--name", 
        type=str,
        nargs='+',
        help="Search for items by name/title (multiple words = AND search)"
    )
    
    parser.add_argument(
        "-l", "--list", 
        type=str,
        nargs='?',
        const='',
        help="List all folders and sub-folders (supports %% wildcard)"
    )
    
    parser.add_argument(
        "-a", "--author", 
        type=str,
        nargs='+',
        help="Search for items by author name (multiple words = AND search)"
    )
    
    parser.add_argument(
        "-t", "--tag", 
        type=str,
        nargs='+',
        help="Filter by tags (multiple tags = AND search, case-insensitive)"
    )

def add_filter_arguments(parser: argparse.ArgumentParser) -> None:
    """Add filtering arguments."""
    parser.add_argument(
        "-k", "--exact", 
        action="store_true",
        help="Use exact search instead of partial matching"
    )
    
    parser.add_argument(
        "-o", "--only-attachments", 
        action="store_true",
        help="Show only items with PDF or EPUB attachments"
    )
    
    parser.add_argument(
        "--after", 
        type=int,
        help="Show items published after this year (inclusive)"
    )
    
    parser.add_argument(
        "--before", 
        type=int,
        help="Show items published before this year (inclusive)"
    )
    
    parser.add_argument(
        "--books", 
        action="store_true",
        help="Show only book items in search results"
    )
    
    parser.add_argument(
        "--articles", 
        action="store_true",
        help="Show only article items in search results"
    )
    
    parser.add_argument(
        "--no-dedupe", 
        action="store_true",
        help="Disable automatic deduplication of results"
    )

def add_utility_arguments(parser: argparse.ArgumentParser) -> None:
    """Add utility arguments for specific operations."""
    parser.add_argument(
        "--id", 
        type=int,
        help="Show metadata for a specific item ID"
    )
    
    parser.add_argument(
        "--getbyid", 
        type=int,
        nargs='+',
        help="Grab attachments for specific item IDs"
    )
    
    parser.add_argument(
        "--showids", 
        action="store_true",
        help="Show item ID numbers in search results"
    )
    
    parser.add_argument(
        "--showtags", 
        action="store_true",
        help="Show tags for each item in search results"
    )
    
    parser.add_argument(
        "--stats", 
        action="store_true",
        help="Show comprehensive database statistics"
    )
    
    parser.add_argument(
        "--export", 
        type=str,
        choices=["csv", "json"],
        help="Export search results to specified format (csv or json)"
    )
    
    parser.add_argument(
        "--file", 
        type=str,
        help="Specify output file path for export (defaults to current directory)"
    )
    
    parser.add_argument(
        "--showyear", 
        action="store_true",
        help="Show publication year for each item in search results"
    )
    
    parser.add_argument(
        "--showauthor", 
        action="store_true",
        help="Show first author name (first and last) for each item in search results"
    )
    
    parser.add_argument(
        "--showcreated", 
        action="store_true",
        help="Show item creation date in search results"
    )
    
    parser.add_argument(
        "--showmodified", 
        action="store_true",
        help="Show item modification date in search results"
    )
    
    parser.add_argument(
        "--showcollections", 
        action="store_true",
        help="Show collections each item belongs to in search results"
    )
    
    parser.add_argument(
        "--sort", 
        type=str,
        choices=["t", "title", "d", "date", "a", "author", "c", "created", "m", "modified"],
        help="Sort search results by: t/title, d/date, a/author, c/created, m/modified"
    )
    
    parser.add_argument(
        "--config", 
        action="store_true",
        help="Launch interactive configuration wizard"
    )

from . import __version__

def create_parser():
    parser = argparse.ArgumentParser(
        description="Zurch - Zotero Search CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add argument groups
    add_basic_arguments(parser)
    add_mode_arguments(parser)
    add_search_arguments(parser)
    add_filter_arguments(parser)
    add_utility_arguments(parser)
    
    return parser