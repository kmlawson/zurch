"""Arrow key navigation for interactive item selection."""

import os
from typing import List, Optional, Tuple
from .models import ZoteroItem
from .constants import Colors
from .utils import format_item_type_icon, format_attachment_link_icon, format_notes_icon, pad_number
from .keyboard import get_single_char, is_terminal_interactive

# ANSI escape codes for cursor movement
CURSOR_UP = '\033[A'
CURSOR_DOWN = '\033[B'
CLEAR_LINE = '\033[2K'
SAVE_CURSOR = '\033[s'
RESTORE_CURSOR = '\033[u'
HIDE_CURSOR = '\033[?25l'
SHOW_CURSOR = '\033[?25h'

# Key codes
ARROW_UP = '\033[A'
ARROW_DOWN = '\033[B'
ENTER = '\n'
ESCAPE = '\x1b'

def clear_screen_section(lines: int) -> None:
    """Clear a section of the screen by moving up and clearing lines."""
    for _ in range(lines):
        print(f'{CURSOR_UP}{CLEAR_LINE}', end='')
    print('\r', end='', flush=True)

def display_items_with_highlight(items: List[ZoteroItem], selected_index: int, start_index: int, 
                                max_display: int, search_term: str = "", show_notes: bool = False,
                                db=None) -> int:
    """Display items with one highlighted.
    
    Returns the number of lines printed.
    """
    lines_printed = 0
    end_index = min(start_index + max_display, len(items))
    
    for i in range(start_index, end_index):
        item = items[i]
        is_selected = (i == selected_index)
        
        # Format item display
        type_icon = format_item_type_icon(item.item_type, item.is_duplicate)
        attachment_icon = format_attachment_link_icon(item.attachment_type)
        
        # Add notes icon if requested
        notes_icon = ""
        if show_notes and db:
            try:
                has_notes = db.notes.has_notes(item.item_id)
                notes_icon = format_notes_icon(has_notes)
            except Exception:
                notes_icon = ""
        
        number = pad_number(i + 1, len(items))
        title = item.title
        
        # Build the display line
        display_line = f"{number}. {type_icon}{attachment_icon}{notes_icon}{title}"
        
        # Apply highlighting if selected
        if is_selected:
            # Use reverse video for highlighting
            print(f"{Colors.BG_BLUE}{Colors.WHITE}{display_line}{Colors.RESET}")
        else:
            print(display_line)
        
        lines_printed += 1
    
    return lines_printed

def handle_arrow_key_input() -> str:
    """Handle arrow key input, returning standardized key codes.
    
    Supports:
    - Unix/Linux/macOS: ESC[A/B/C/D sequences
    - Windows: Special double-byte sequences
    - Vim keys: j/k for down/up
    """
    char = get_single_char()
    
    # Windows special keys (when using msvcrt)
    if os.name == 'nt' and char in ['\x00', '\xe0']:
        # Windows arrow keys send two bytes: first is 0x00 or 0xE0
        try:
            second = get_single_char()
            if second == 'H':  # Up arrow
                return 'up'
            elif second == 'P':  # Down arrow
                return 'down'
            elif second == 'K':  # Left arrow
                return 'left'
            elif second == 'M':  # Right arrow
                return 'right'
        except Exception:
            pass
        return char
    
    # Unix/Linux/macOS escape sequences
    elif char == '\x1b':  # ESC
        # Read the next characters for arrow keys
        try:
            next_char = get_single_char()
            if next_char == '[':
                arrow_char = get_single_char()
                if arrow_char == 'A':
                    return 'up'
                elif arrow_char == 'B':
                    return 'down'
                elif arrow_char == 'C':
                    return 'right'
                elif arrow_char == 'D':
                    return 'left'
                # Handle numeric escape sequences (e.g., ESC[1A)
                elif arrow_char.isdigit():
                    # Read until we get the direction letter
                    while True:
                        next_char = get_single_char()
                        if next_char == 'A':
                            return 'up'
                        elif next_char == 'B':
                            return 'down'
                        elif next_char == 'C':
                            return 'right'
                        elif next_char == 'D':
                            return 'left'
                        elif not next_char.isdigit() and next_char != ';':
                            break
            elif next_char == 'O':
                # Some terminals use ESC O for arrow keys
                arrow_char = get_single_char()
                if arrow_char == 'A':
                    return 'up'
                elif arrow_char == 'B':
                    return 'down'
                elif arrow_char == 'C':
                    return 'right'
                elif arrow_char == 'D':
                    return 'left'
        except Exception:
            pass
        return 'escape'
    
    # Standard keys
    elif char == '\n' or char == '\r':
        return 'enter'
    elif char.lower() == 'j':
        return 'down'
    elif char.lower() == 'k':
        return 'up'
    elif char.lower() == 'g':
        return 'g'
    elif char.lower() == 'l':
        return 'l'
    elif char == '0':
        return '0'
    elif char.isdigit():
        return char
    else:
        return char

def arrow_navigation_selection(items: List[ZoteroItem], max_display: int = 20, 
                             search_term: str = "", show_notes: bool = False,
                             db=None, show_go_back: bool = True) -> Tuple[Optional[ZoteroItem], bool, Optional[int]]:
    """Interactive selection using arrow keys for navigation.
    
    Args:
        items: List of items to select from
        max_display: Maximum number of items to display at once
        search_term: Search term for highlighting
        show_notes: Whether to show notes icons
        db: Database connection for notes lookup
        show_go_back: Whether to show the 'l' to go back option
        
    Returns:
        Tuple of (selected_item, should_grab, selected_index)
        Returns (None, False, None) if cancelled
        Returns ("GO_BACK", False, None) if user chose to go back
    """
    if not items:
        return (None, False, None)
    
    if not is_terminal_interactive():
        # Fall back to simple number selection if not in interactive terminal
        from .handlers import interactive_selection_simple, DisplayOptions
        display_opts = DisplayOptions(show_notes=show_notes)
        return interactive_selection_simple(items, len(items), search_term, None, 
                                          display_opts, db, True, show_go_back)
    
    selected_index = 0
    start_index = 0
    total_items = len(items)
    max_display = min(max_display, total_items)
    
    # Hide cursor for cleaner display
    print(HIDE_CURSOR, end='', flush=True)
    
    # Print instructions
    print("\nUse ↑/↓ or j/k to navigate, Enter to select, 0 to cancel")
    if show_go_back:
        print("'l' to go back, 'g' after selection to grab attachment")
    else:
        print("'g' after selection to grab attachment")
    print("Or type a number to jump to that item")
    print("-" * 60)
    
    try:
        lines_printed = 0
        number_buffer = ""
        
        while True:
            # Clear previous display
            if lines_printed > 0:
                clear_screen_section(lines_printed)
            
            # Adjust display window if selected item is outside current view
            if selected_index < start_index:
                start_index = selected_index
            elif selected_index >= start_index + max_display:
                start_index = selected_index - max_display + 1
            
            # Display items with current selection highlighted
            lines_printed = display_items_with_highlight(
                items, selected_index, start_index, max_display,
                search_term, show_notes, db
            )
            
            # Show page info if scrolling
            if total_items > max_display:
                page_info = f"\nShowing {start_index + 1}-{min(start_index + max_display, total_items)} of {total_items} items"
                print(page_info)
                lines_printed += 2  # Account for newline and page info
            
            # Get user input
            key = handle_arrow_key_input()
            
            if key == 'up':
                if selected_index > 0:
                    selected_index -= 1
                number_buffer = ""  # Clear number buffer on navigation
            elif key == 'down':
                if selected_index < total_items - 1:
                    selected_index += 1
                number_buffer = ""  # Clear number buffer on navigation
            elif key == 'enter':
                if number_buffer:
                    # If user typed a number and pressed enter, jump to that item
                    try:
                        num = int(number_buffer) - 1
                        if 0 <= num < total_items:
                            selected_index = num
                            # Clear the display to show final selection
                            clear_screen_section(lines_printed)
                            print(f"\nSelected: {items[selected_index].title}")
                            return (items[selected_index], False, selected_index)
                        else:
                            # Invalid number, clear buffer and continue
                            number_buffer = ""
                    except ValueError:
                        number_buffer = ""
                else:
                    # Regular enter - select current item
                    # Clear the display to show final selection
                    clear_screen_section(lines_printed)
                    print(f"\nSelected: {items[selected_index].title}")
                    return (items[selected_index], False, selected_index)
            elif key == 'g':
                # Select current item and grab
                clear_screen_section(lines_printed)
                print(f"\nSelected (with grab): {items[selected_index].title}")
                return (items[selected_index], True, selected_index)
            elif key == 'l' and show_go_back:
                clear_screen_section(lines_printed)
                return ("GO_BACK", False, None)
            elif key == '0' and not number_buffer:
                # Cancel only if 0 is the first character
                clear_screen_section(lines_printed)
                print("\nCancelled")
                return (None, False, None)
            elif key.isdigit():
                # Build number buffer
                number_buffer += key
                # Check if the number is complete (would exceed item count if another digit added)
                if number_buffer:
                    potential_next = int(number_buffer + "0")
                    if potential_next > total_items:
                        # Auto-jump to the item
                        try:
                            num = int(number_buffer) - 1
                            if 0 <= num < total_items:
                                selected_index = num
                                number_buffer = ""
                        except ValueError:
                            number_buffer = ""
            elif key == 'escape':
                clear_screen_section(lines_printed)
                print("\nCancelled")
                return (None, False, None)
            
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled")
        return (None, False, None)
    finally:
        # Show cursor again
        print(SHOW_CURSOR, end='', flush=True)