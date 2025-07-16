"""zurch - A CLI search tool for Zotero installations."""

__version__ = "0.7.8"

from .cli import main
from .search import ZoteroDatabase
from .models import ZoteroItem, ZoteroCollection
from .utils import load_config, save_config

__all__ = ["main", "ZoteroDatabase", "ZoteroItem", "ZoteroCollection", "load_config", "save_config"]