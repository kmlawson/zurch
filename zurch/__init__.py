"""zurch - A CLI search tool for Zotero installations."""

__version__ = "0.7.9"

# Core exports that don't import CLI
from .search import ZoteroDatabase
from .models import ZoteroItem, ZoteroCollection

# Try to import Pydantic config, fallback to legacy
try:
    from .config_pydantic import load_config, save_config
except ImportError:
    from .utils import load_config, save_config

__all__ = ["ZoteroDatabase", "ZoteroItem", "ZoteroCollection", "load_config", "save_config"]

# CLI main function available on demand
def main():
    """Entry point for CLI application."""
    from .cli import main as cli_main
    return cli_main()