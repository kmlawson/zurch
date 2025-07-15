def paginate_items(items, page_size, current_page=0):
    """
    Paginate a list of items.
    
    Args:
        items: List of items to paginate
        page_size: Number of items per page
        current_page: Current page index (0-based)
    
    Returns:
        tuple: (page_items, has_previous, has_next, current_page, total_pages)
    """
    if not items:
        return [], False, False, 0, 0
    
    total_pages = (len(items) + page_size - 1) // page_size
    
    # Ensure current_page is within valid range
    current_page = max(0, min(current_page, total_pages - 1))
    
    start_idx = current_page * page_size
    end_idx = start_idx + page_size
    page_items = items[start_idx:end_idx]
    
    has_previous = current_page > 0
    has_next = current_page < total_pages - 1
    
    return page_items, has_previous, has_next, current_page, total_pages


def get_pagination_input(has_previous, has_next):
    """
    Get user input for pagination navigation.
    
    Args:
        has_previous: Whether previous page is available
        has_next: Whether next page is available
    
    Returns:
        str: User input ('n', 'p', '0', or '')
    """
    # Build dynamic prompt based on available options
    options = []
    valid_chars = ['0']
    
    if has_next:
        options.append("'n' for next page")
        valid_chars.append('n')
    if has_previous:
        options.append("'p' for previous page")
        valid_chars.append('p')
    
    options.append("'0' to exit")
    
    prompt = "Press " + ", ".join(options) + ": "
    
    try:
        import sys
        import termios
        import tty
        
        # Check if we can actually use termios (not in pipe/redirect)
        if not sys.stdin.isatty():
            raise ImportError("Not a tty, fallback to input()")
        
        print(prompt, end='', flush=True)
        
        # Get a single character without pressing Enter
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        print(char)  # Echo the character
        
        # Handle special keys
        if char == '\x03':  # Ctrl+C
            return '0'
        elif char == '\r' or char == '\n':  # Enter
            return '0'
        elif char.lower() in valid_chars:
            return char.lower()
        else:
            # Build error message with valid options
            valid_options = [f"'{c}'" for c in valid_chars if c != '0']
            valid_options.append("'0' to exit")
            print(f"Invalid input. Use " + ", ".join(valid_options) + ".")
            return get_pagination_input(has_previous, has_next)  # Try again
            
    except (EOFError, KeyboardInterrupt):
        return '0'
    except (ImportError, AttributeError, OSError):
        # Fallback for systems without termios or when not in tty (e.g., Windows, pipes)
        try:
            user_input = input(prompt).strip().lower()
            if user_input in valid_chars:
                return user_input
            else:
                valid_options = [f"'{c}'" for c in valid_chars if c != '0']
                valid_options.append("'0' to exit")
                print(f"Invalid input. Use " + ", ".join(valid_options) + ".")
                return get_pagination_input(has_previous, has_next)  # Try again
        except (EOFError, KeyboardInterrupt):
            return '0'


def display_pagination_status(current_page, total_pages, total_items, page_size):
    """
    Display pagination status information.
    
    Args:
        current_page: Current page number (0-based)
        total_pages: Total number of pages
        total_items: Total number of items
        page_size: Items per page
    """
    start_item = current_page * page_size + 1
    end_item = min((current_page + 1) * page_size, total_items)
    
    print(f"\nShowing items {start_item}-{end_item} of {total_items} total (Page {current_page + 1} of {total_pages})")


def handle_pagination_loop(all_items, page_size, display_func, *display_args, **display_kwargs):
    """
    Handle the pagination loop for displaying items.
    
    Args:
        all_items: List of all items to paginate
        page_size: Number of items per page
        display_func: Function to display a page of items
        *display_args: Additional arguments for display_func
        **display_kwargs: Additional keyword arguments for display_func
    """
    if not all_items:
        return
    
    current_page = 0
    
    while True:
        page_items, has_previous, has_next, current_page, total_pages = paginate_items(
            all_items, page_size, current_page
        )
        
        # Display the current page
        display_func(page_items, *display_args, **display_kwargs)
        
        # Show pagination status
        display_pagination_status(current_page, total_pages, len(all_items), page_size)
        
        # If only one page, exit
        if total_pages <= 1:
            break
        
        # Get user input for navigation
        user_input = get_pagination_input(has_previous, has_next)
        
        if user_input == '0' or user_input == '':
            break
        elif user_input == 'n' and has_next:
            current_page += 1
        elif user_input == 'p' and has_previous:
            current_page -= 1
        # Note: We don't need to handle invalid navigation attempts here
        # because get_pagination_input() only accepts valid options