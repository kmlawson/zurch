"""Arrow key navigation for interactive item selection."""

import os
import shutil
from typing import List, Optional, Tuple
from .models import ZoteroItem
from .constants import Colors
from .utils import format_item_type_icon, format_attachment_link_icon, format_notes_icon, pad_number
from .keyboard import get_single_char, is_terminal_interactive

# ANSI escape codes for cursor movement
CURSOR_UP = '\033[A'
CURSOR_DOWN = '\033[B'
CURSOR_RIGHT = '\033[C'
CURSOR_LEFT = '\033[D'
CLEAR_LINE = '\033[2K'
CLEAR_SCREEN = '\033[2J'
CLEAR_TO_END = '\033[0J'
SAVE_CURSOR = '\033[s'
RESTORE_CURSOR = '\033[u'
HIDE_CURSOR = '\033[?25l'
SHOW_CURSOR = '\033[?25h'
HOME_CURSOR = '\033[H'
# Absolute cursor positioning: \033[row;colH
CURSOR_POS = '\033[{};{}H'

# Key codes
ARROW_UP = '\033[A'
ARROW_DOWN = '\033[B'
ENTER = '\n'
ESCAPE = '\x1b'

def get_terminal_size() -> Tuple[int, int]:
    """Get terminal size (columns, rows)."""
    try:
        cols, rows = shutil.get_terminal_size((80, 24))
        return cols, rows
    except Exception:
        return 80, 24  # Default fallback

def calculate_display_lines(text: str, terminal_width: int) -> int:
    """Calculate how many terminal lines a text will occupy when displayed."""
    # Strip ANSI codes for accurate length calculation
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_text = ansi_escape.sub('', text)
    
    if not clean_text:
        return 1
    
    # Calculate wrapped lines
    return max(1, (len(clean_text) + terminal_width - 1) // terminal_width)

def move_cursor_to_row(row: int) -> str:
    """Generate ANSI code to move cursor to specific row."""
    return CURSOR_POS.format(row, 1)

def clear_display_area(start_row: int, num_lines: int) -> None:
    """Clear a specific area of the display using absolute positioning."""
    for i in range(num_lines):
        print(f'{move_cursor_to_row(start_row + i)}{CLEAR_LINE}', end='')
    print(move_cursor_to_row(start_row), end='', flush=True)

def display_items_with_highlight(items: List[ZoteroItem], selected_index: int, start_index: int, 
                                max_display: int, search_term: str = "", show_notes: bool = False,
                                db=None, start_row: int = None) -> Tuple[int, int]:
    """Display items with one highlighted.
    
    Args:
        items: List of items to display
        selected_index: Index of item to highlight
        start_index: Index of first item to display
        max_display: Maximum number of items to display
        search_term: Search term for highlighting
        show_notes: Whether to show notes icons
        db: Database connection
        start_row: Starting row position (if using absolute positioning)
    
    Returns:
        Tuple of (number of items displayed, total terminal lines used)
    """
    cols, _ = get_terminal_size()
    total_lines = 0
    items_displayed = 0
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
        
        # Calculate lines this item will use
        item_lines = calculate_display_lines(display_line, cols)
        
        # Apply highlighting if selected
        if is_selected:
            # Use reverse video for highlighting
            print(f"{Colors.BG_BLUE}{Colors.WHITE}{display_line}{Colors.RESET}")
        else:
            print(display_line)
        
        total_lines += item_lines
        items_displayed += 1
    
    return items_displayed, total_lines

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
    elif char.lower() == 'n':
        return 'next_page'
    elif char.lower() == 'b':
        return 'prev_page'
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
    total_pages = (total_items + max_display - 1) // max_display
    
    # Get terminal dimensions
    cols, rows = get_terminal_size()
    
    # Hide cursor for cleaner display
    print(HIDE_CURSOR, end='', flush=True)
    
    # Store the starting position for absolute positioning
    print(SAVE_CURSOR, end='', flush=True)
    
    # Print instructions
    print("\nUse ↑/↓ or j/k to navigate items, n/b for pages, Enter to select")
    if show_go_back:
        print("'l' to go back, 'g' to grab attachment, 0 to cancel")
    else:
        print("'g' to grab attachment, 0 to cancel")
    print("Type a number to jump to that item")
    print("-" * 60)
    
    instruction_lines = 5  # Number of instruction lines
    
    try:
        display_lines = 0
        number_buffer = ""
        last_error = ""
        need_redraw = True
        
        while True:
            current_page = start_index // max_display
            
            # Only redraw if needed
            if need_redraw:
                # Clear previous display area
                if display_lines > 0:
                    # Use absolute positioning to clear from after instructions
                    clear_display_area(instruction_lines + 1, display_lines)
                
                # Adjust display window if selected item is outside current view
                if selected_index < start_index:
                    start_index = (selected_index // max_display) * max_display
                elif selected_index >= start_index + max_display:
                    start_index = (selected_index // max_display) * max_display
                
                # Display items with current selection highlighted
                items_shown, lines_used = display_items_with_highlight(
                    items, selected_index, start_index, max_display,
                    search_term, show_notes, db
                )
                
                # Show status line
                status_parts = []
                status_parts.append(f"Item {selected_index + 1} of {total_items}")
                if total_pages > 1:
                    status_parts.append(f"Page {current_page + 1} of {total_pages}")
                if number_buffer:
                    status_parts.append(f"Typing: {number_buffer}")
                if last_error:
                    status_parts.append(f"[{last_error}]")
                    last_error = ""  # Clear error after showing
                
                status_line = " | ".join(status_parts)
                print(f"\n{status_line}")
                
                display_lines = lines_used + 2  # Items + status line
                need_redraw = False
            
            # Get user input
            key = handle_arrow_key_input()
            
            if key == 'up':
                if selected_index > 0:
                    selected_index -= 1
                    need_redraw = True
                number_buffer = ""
            elif key == 'down':
                if selected_index < total_items - 1:
                    selected_index += 1
                    need_redraw = True
                number_buffer = ""
            elif key == 'next_page':
                # Jump to next page
                new_index = min(selected_index + max_display, total_items - 1)
                if new_index != selected_index:
                    selected_index = new_index
                    need_redraw = True
                number_buffer = ""
            elif key == 'prev_page':
                # Jump to previous page
                new_index = max(selected_index - max_display, 0)
                if new_index != selected_index:
                    selected_index = new_index
                    need_redraw = True
                number_buffer = ""
            elif key == 'enter':
                if number_buffer:
                    # If user typed a number and pressed enter, jump to that item
                    try:
                        num = int(number_buffer) - 1
                        if 0 <= num < total_items:
                            # Select the item
                            print(RESTORE_CURSOR, end='')
                            print(CLEAR_TO_END, end='', flush=True)
                            print(f"\nSelected: {items[num].title}")
                            return (items[num], False, num)
                        else:
                            last_error = f"Invalid: {number_buffer}"
                            number_buffer = ""
                            need_redraw = True
                    except ValueError:
                        last_error = "Invalid number"
                        number_buffer = ""
                        need_redraw = True
                else:
                    # Regular enter - select current item
                    print(RESTORE_CURSOR, end='')
                    print(CLEAR_TO_END, end='', flush=True)
                    print(f"\nSelected: {items[selected_index].title}")
                    return (items[selected_index], False, selected_index)
            elif key == 'g':
                # Select current item and grab
                print(RESTORE_CURSOR, end='')
                print(CLEAR_TO_END, end='', flush=True)
                print(f"\nSelected (with grab): {items[selected_index].title}")
                return (items[selected_index], True, selected_index)
            elif key == 'l' and show_go_back:
                print(RESTORE_CURSOR, end='')
                print(CLEAR_TO_END, end='', flush=True)
                return ("GO_BACK", False, None)
            elif key == '0' and not number_buffer:
                # Cancel only if 0 is the first character
                print(RESTORE_CURSOR, end='')
                print(CLEAR_TO_END, end='', flush=True)
                print("\nCancelled")
                return (None, False, None)
            elif key.isdigit():
                # Build number buffer
                number_buffer += key
                need_redraw = True  # Show the buffer in status
                
                # Check if the number is complete (would exceed item count if another digit added)
                if number_buffer:
                    try:
                        potential_next = int(number_buffer + "0")
                        if potential_next > total_items:
                            # Auto-jump to the item
                            num = int(number_buffer) - 1
                            if 0 <= num < total_items:
                                selected_index = num
                                number_buffer = ""
                                need_redraw = True
                    except ValueError:
                        pass
            elif key == 'escape':
                print(RESTORE_CURSOR, end='')
                print(CLEAR_TO_END, end='', flush=True)
                print("\nCancelled")
                return (None, False, None)
            
    except (KeyboardInterrupt, EOFError):
        print(RESTORE_CURSOR, end='')
        print(CLEAR_TO_END, end='', flush=True)
        print("\nCancelled")
        return (None, False, None)
    except Exception as e:
        # Error recovery - fall back to simple selection
        print(RESTORE_CURSOR, end='')
        print(CLEAR_TO_END, end='', flush=True)
        print(f"\nError in arrow navigation: {e}")
        print("Falling back to simple selection...")
        from .handlers import interactive_selection_simple, DisplayOptions
        display_opts = DisplayOptions(show_notes=show_notes)
        return interactive_selection_simple(items, len(items), search_term, None, 
                                          display_opts, db, True, show_go_back)
    finally:
        # Show cursor again
        print(SHOW_CURSOR, end='', flush=True)