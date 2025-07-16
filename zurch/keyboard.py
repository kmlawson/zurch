"""Keyboard input utilities for immediate key response."""

import sys
from typing import Optional

# Try to import Unix-specific modules
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False


def get_single_char() -> str:
    """Get a single character from stdin without waiting for Enter.
    
    Returns:
        str: The character pressed
    """
    if not HAS_TERMIOS:
        # Fallback to regular input on Windows or when termios not available
        return input()[0] if input() else ''
    
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        # Handle special characters
        if ch == '\x03':  # Ctrl+C
            raise KeyboardInterrupt()
        elif ch == '\x04':  # Ctrl+D (EOF)
            raise EOFError()
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_input_with_immediate_keys(prompt: str, immediate_keys: set) -> str:
    """Get user input, responding immediately to certain keys.
    
    Args:
        prompt: The prompt to display
        immediate_keys: Set of keys that should return immediately
        
    Returns:
        str: The user's input
    """
    print(prompt, end='', flush=True)
    
    # Get first character
    first_char = get_single_char()
    
    # If it's an immediate key, return it right away
    if first_char in immediate_keys:
        print(first_char)  # Echo the character
        return first_char
    
    # Otherwise, switch back to normal input mode
    # First, restore the terminal and echo the character
    print(first_char, end='', flush=True)
    
    # If it's Enter, return empty string
    if first_char in ['\r', '\n']:
        print()  # New line
        return ''
    
    # Read the rest of the line normally
    try:
        rest = input()
        return first_char + rest
    except (KeyboardInterrupt, EOFError):
        print()  # New line for cleaner output
        raise


def is_terminal_interactive() -> bool:
    """Check if we're in an interactive terminal that supports raw mode.
    
    Returns:
        bool: True if terminal is interactive and supports raw mode
    """
    if not HAS_TERMIOS:
        return False
        
    try:
        # Check if stdin is a terminal
        if not sys.stdin.isatty():
            return False
        
        # Try to get terminal settings (will fail if not supported)
        fd = sys.stdin.fileno()
        termios.tcgetattr(fd)
        return True
    except:
        return False