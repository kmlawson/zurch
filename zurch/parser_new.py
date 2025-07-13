"""Improved argument parser with sub-commands."""

import argparse


def create_subcommand_parser() -> argparse.ArgumentParser:
    """Create parser with sub-commands instead of monolithic flag structure."""
    
    parser = argparse.ArgumentParser(
        description="Zurch - A CLI search tool for Zotero installations",
        prog="zurch"
    )
    
    # Global options
    parser.add_argument(
        "-v", "--version", 
        action="version", 
        version="zurch 0.6.0"
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
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for items by title')
    search_parser.add_argument('terms', nargs='+', help='Search terms (AND logic)')
    search_parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode')
    search_parser.add_argument('-g', '--grab', action='store_true', help='Grab attachments in interactive mode')
    search_parser.add_argument('-k', '--exact', action='store_true', help='Exact match')
    search_parser.add_argument('-o', '--only-attachments', action='store_true', help='Only items with attachments')
    search_parser.add_argument('--after', type=int, help='Published after year')
    search_parser.add_argument('--before', type=int, help='Published before year')
    search_parser.add_argument('--books', action='store_true', help='Only books')
    search_parser.add_argument('--articles', action='store_true', help='Only articles')
    search_parser.add_argument('--no-dedupe', action='store_true', help='Disable deduplication')
    search_parser.add_argument('--showids', action='store_true', help='Show item IDs')
    
    # Author command
    author_parser = subparsers.add_parser('author', help='Search for items by author')
    author_parser.add_argument('name', nargs='+', help='Author name (AND logic)')
    author_parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode')
    author_parser.add_argument('-g', '--grab', action='store_true', help='Grab attachments in interactive mode')
    author_parser.add_argument('-k', '--exact', action='store_true', help='Exact match')
    author_parser.add_argument('-o', '--only-attachments', action='store_true', help='Only items with attachments')
    author_parser.add_argument('--after', type=int, help='Published after year')
    author_parser.add_argument('--before', type=int, help='Published before year')
    author_parser.add_argument('--books', action='store_true', help='Only books')
    author_parser.add_argument('--articles', action='store_true', help='Only articles')
    author_parser.add_argument('--no-dedupe', action='store_true', help='Disable deduplication')
    author_parser.add_argument('--showids', action='store_true', help='Show item IDs')
    
    # Folder command  
    folder_parser = subparsers.add_parser('folder', help='Browse items in a folder')
    folder_parser.add_argument('name', nargs='+', help='Folder name')
    folder_parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode')
    folder_parser.add_argument('-g', '--grab', action='store_true', help='Grab attachments in interactive mode')
    folder_parser.add_argument('-o', '--only-attachments', action='store_true', help='Only items with attachments')
    folder_parser.add_argument('--after', type=int, help='Published after year')
    folder_parser.add_argument('--before', type=int, help='Published before year')
    folder_parser.add_argument('--books', action='store_true', help='Only books')
    folder_parser.add_argument('--articles', action='store_true', help='Only articles')
    folder_parser.add_argument('--no-dedupe', action='store_true', help='Disable deduplication')
    folder_parser.add_argument('--showids', action='store_true', help='Show item IDs')
    
    # Collections command
    collections_parser = subparsers.add_parser('collections', help='List collections')
    collections_parser.add_argument('filter', nargs='?', help='Filter collections by pattern')
    collections_parser.add_argument('-i', '--interactive', action='store_true', help='Interactive selection')
    collections_parser.add_argument('-k', '--exact', action='store_true', help='Exact match')
    
    # Item command (for specific item operations)
    item_parser = subparsers.add_parser('item', help='Operations on specific items')
    item_subparsers = item_parser.add_subparsers(dest='item_action', help='Item actions')
    
    # Show item metadata
    show_parser = item_subparsers.add_parser('show', help='Show item metadata')
    show_parser.add_argument('id', type=int, help='Item ID')
    
    # Grab item attachments
    grab_parser = item_subparsers.add_parser('grab', help='Grab item attachments')
    grab_parser.add_argument('ids', type=int, nargs='+', help='Item IDs')
    
    return parser


def create_legacy_parser() -> argparse.ArgumentParser:
    """Create legacy parser for backward compatibility."""
    from .parser import create_parser
    return create_parser()


def parse_args_with_fallback(args=None):
    """Parse arguments with fallback to legacy parser for compatibility."""
    # Try new subcommand parser first
    try:
        new_parser = create_subcommand_parser()
        parsed_args = new_parser.parse_args(args)
        
        # If we got a command, use new parser
        if hasattr(parsed_args, 'command') and parsed_args.command:
            return parsed_args, 'new'
    except SystemExit:
        pass
    
    # Fall back to legacy parser
    legacy_parser = create_legacy_parser()
    return legacy_parser.parse_args(args), 'legacy'