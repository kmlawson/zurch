"""Entry point for zurch package when run as a module."""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())