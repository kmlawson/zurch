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
        type=int, 
        default=100,
        help="Maximum number of results to return (default: 100)"
    )

def add_mode_arguments(parser: argparse.ArgumentParser) -> None:
    """Add interactive and grab mode arguments."""
    parser.add_argument(
        "-i", "--interactive", 
        action="store_true",
        help="Enable interactive mode"
    )
    
    parser.add_argument(
        "-g", "--grab", 
        action="store_true",
        help="Grab attachment and copy to current directory (requires -i)"
    )

def add_search_arguments(parser: argparse.ArgumentParser) -> None:
    """Add search-related arguments."""
    parser.add_argument(
        "-f", "--folder", 
        type=str,
        nargs='+',
        help="List items in the specified folder (spaces allowed without quotes, use quotes for special chars: ' \" $ ` \\ ( ) [ ] { } | & ; < > * ?)"
    )
    
    parser.add_argument(
        "-n", "--name", 
        type=str,
        nargs='+',
        help="Search for items by name/title. Multiple words = AND search (each word must be present). Quoted text = phrase search (exact phrase). Use quotes for special chars: ' \" $ ` \\ ( ) [ ] { } | & ; < > * ?"
    )
    
    parser.add_argument(
        "-l", "--list", 
        type=str,
        nargs='?',
        const='',
        help="List all folders and sub-folders, optionally filtered by pattern (supports %% wildcard, partial match by default). Add '/' suffix to show all sub-collections of matching collections."
    )
    
    parser.add_argument(
        "-a", "--author", 
        type=str,
        nargs='+',
        help="Search for items by author name. Multiple words = AND search (each word must be present). Quoted text = phrase search (exact phrase)."
    )
    
    parser.add_argument(
        "-t", "--tag", 
        type=str,
        nargs='+',
        help="Filter by tags. Multiple words = AND search (item must have all tags). Case-insensitive."
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
        help="Show only items that have PDF or EPUB attachments"
    )
    
    parser.add_argument(
        "--after", 
        type=int,
        help="Only show items published after this year (inclusive)"
    )
    
    parser.add_argument(
        "--before", 
        type=int,
        help="Only show items published before this year (inclusive)"
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
        help="Grab attachments for specific item IDs (space-separated)."
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

from . import __version__

def create_parser():
    parser = argparse.ArgumentParser(
        description="Zurch - Zotero Search CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Add argument groups
    add_basic_arguments(parser)
    add_mode_arguments(parser)
    add_search_arguments(parser)
    add_filter_arguments(parser)
    add_utility_arguments(parser)
    
    return parser