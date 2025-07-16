"""Keyboard input utilities for immediate key response."""

import sys
import os
from typing import Optional

# Try to import platform-specific modules
HAS_TERMIOS = False
HAS_MSVCRT = False

if os.name == 'nt':  # Windows
    try:
        import msvcrt
        HAS_MSVCRT = True
    except ImportError:
        pass
else:  # Unix-like (Linux, macOS)
    try:
        import termios
        import tty
        HAS_TERMIOS = True
    except ImportError:
        pass


def get_single_char() -> str:
    """Get a single character from stdin without waiting for Enter.
    
    Returns:
        str: The character pressed
    """
    if HAS_MSVCRT:
        # Windows implementation using msvcrt
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if isinstance(ch, bytes):
                    ch = ch.decode('utf-8', errors='ignore')
                
                # Handle special characters
                if ch == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt()
                elif ch == '\x04':  # Ctrl+D (EOF)
                    raise EOFError()
                elif ch == '\x1a':  # Ctrl+Z (EOF on Windows)
                    raise EOFError()
                elif ch == '\r':  # Convert \r to \n for consistency
                    return '\n'
                
                return ch
    elif HAS_TERMIOS:
        # Unix implementation using termios
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
    else:
        # Fallback to regular input when no platform-specific modules available
        user_input = input()
        return user_input[0] if user_input else ''


def get_input_with_immediate_keys(prompt: str, immediate_keys: set, first_char_only_immediate: set = None) -> str:
    """Get user input, responding immediately to certain keys.
    
    Args:
        prompt: The prompt to display
        immediate_keys: Set of keys that should return immediately
        first_char_only_immediate: Set of keys that are immediate only when first character
        
    Returns:
        str: The user's input
    """
    if first_char_only_immediate is None:
        first_char_only_immediate = set()
    
    print(prompt, end='', flush=True)
    
    # Build the input line character by character
    input_line = ""
    
    while True:
        char = get_single_char()
        
        # Handle immediate keys
        if char in immediate_keys:
            print(char)  # Echo the character
            return char
        
        # Handle first-character-only immediate keys
        if char in first_char_only_immediate and not input_line:
            print(char)  # Echo the character
            return char
        
        # Handle Enter (return the accumulated input)
        if char in ['\r', '\n']:
            print()  # New line
            return input_line
        
        # Handle backspace (DEL or BS)
        if char in ['\x7f', '\x08']:  # DEL or BS
            if input_line:
                # Remove last character from input line
                input_line = input_line[:-1]
                # Move cursor back and erase character
                print('\b \b', end='', flush=True)
            continue
        
        # Handle Ctrl+C
        if char == '\x03':
            raise KeyboardInterrupt()
        
        # Handle Ctrl+D (EOF)
        if char == '\x04':
            raise EOFError()
        
        # Handle printable characters
        if char.isprintable():
            input_line += char
            print(char, end='', flush=True)
        # Ignore non-printable characters that aren't handled above


def is_terminal_interactive() -> bool:
    """Check if we're in an interactive terminal that supports raw mode.
    
    Returns:
        bool: True if terminal is interactive and supports raw mode
    """
    # Check if stdin is a terminal
    if not sys.stdin.isatty():
        return False
    
    if HAS_MSVCRT:
        # Windows - we can use msvcrt for single character input
        return True
    elif HAS_TERMIOS:
        # Unix-like - check if we can get terminal settings
        try:
            fd = sys.stdin.fileno()
            termios.tcgetattr(fd)
            return True
        except:
            return False
    else:
        # No platform-specific support available
        return False