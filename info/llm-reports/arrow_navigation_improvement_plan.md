# Arrow Key Navigation Improvement Plan

**Date**: 2025-07-19
**Author**: Claude (Opus 4)
**Purpose**: Fix and improve arrow key navigation issues in zurch

## Issues Identified

### 1. Multiple lines highlighted simultaneously
- **Root cause**: The terminal clearing mechanism (`clear_screen_section`) doesn't properly handle line wrapping or terminal buffer states
- When items have long titles that wrap to multiple lines, the line count becomes incorrect
- Terminal buffering can cause partial updates, leaving artifacts

### 2. Missing page navigation (n/b keys)
- The arrow navigation only supports single-item navigation
- Users expect 'n' for next page and 'b' for back/previous page like in the standard pagination

### 3. Number entry and exit behavior
- Number entry works but pressing Enter without typing anything doesn't exit
- The code only checks for empty enter when there's a number buffer

### 4. Terminal top boundary issues
- ANSI cursor movement codes try to move beyond the top of the visible terminal
- This causes display corruption when scrolling near the top

## Proposed Solutions

### 1. Fix Display and Highlighting Issues
- **Replace the cursor-based clearing mechanism** with a more robust approach:
  - Use absolute cursor positioning instead of relative movements
  - Save cursor position before drawing and restore after
  - Clear entire display area at once instead of line-by-line
  - Account for line wrapping by calculating actual terminal lines used

- **Add terminal size detection**:
  - Use `shutil.get_terminal_size()` to get terminal dimensions
  - Calculate wrapped lines based on terminal width
  - Prevent cursor movement beyond terminal boundaries

### 2. Add Page Navigation Support
- **Implement n/b key handling**:
  - 'n' or 'N' - jump forward by `max_display` items
  - 'b' or 'B' - jump backward by `max_display` items
  - Update the display window and selected index appropriately
  - Show page number in status line

### 3. Fix Exit Behavior
- **Handle empty Enter press**:
  - Check for Enter key without number buffer and treat as cancel
  - Make behavior consistent with standard interactive selection

### 4. Improve Terminal Handling
- **Add boundary checking**:
  - Track current cursor position relative to terminal top
  - Use alternative clearing methods when near boundaries
  - Implement a "redraw from scratch" option for recovery

- **Add debouncing/buffering**:
  - Ensure all display updates complete before accepting new input
  - Add small delays after clearing to allow terminal to catch up

### 5. Additional Improvements
- **Show current input buffer**: Display the number being typed as user enters it
- **Add Home/End key support**: Jump to first/last item
- **Better status line**: Show "Item X of Y | Page P of Q" format
- **Escape key handling**: Properly handle multi-byte escape sequences
- **Terminal compatibility**: Add fallback modes for terminals that don't support certain ANSI codes

## Implementation Steps

### 1. Refactor display mechanism
- Create new `terminal_safe_display()` function with boundary checking
- Implement proper line wrapping calculation
- Add absolute positioning support

### 2. Extend key handling
- Add 'n'/'b' to `handle_arrow_key_input()`
- Implement page jumping logic
- Add empty Enter handling

### 3. Improve status display
- Create consistent status line format
- Show number buffer as it's being typed
- Add page information

### 4. Add error recovery
- Implement "full redraw" mechanism
- Add try/except blocks around display operations
- Provide fallback to non-arrow navigation on errors

### 5. Test thoroughly
- Test with long item titles that wrap
- Test at terminal boundaries (top/bottom)
- Test with small terminal windows
- Test rapid key presses

## Technical Details

### Terminal Size Calculation
```python
cols, rows = shutil.get_terminal_size((80, 24))
# Calculate wrapped lines for each item
def calculate_display_lines(text, terminal_width):
    # Account for ANSI codes not taking visual space
    visual_length = len(strip_ansi_codes(text))
    return (visual_length + terminal_width - 1) // terminal_width
```

### Safe Cursor Movement
```python
def safe_cursor_move(current_row, target_row, max_rows):
    if target_row < 1:
        target_row = 1
    if target_row > max_rows:
        target_row = max_rows
    # Use absolute positioning
    return f'\033[{target_row};1H'
```

### Page Navigation Logic
```python
elif key in ['n', 'N']:
    # Next page
    new_index = min(selected_index + max_display, total_items - 1)
    selected_index = new_index
    start_index = (new_index // max_display) * max_display
elif key in ['b', 'B']:
    # Previous page
    new_index = max(selected_index - max_display, 0)
    selected_index = new_index
    start_index = (new_index // max_display) * max_display
```

## Expected Outcomes

1. **Stable display**: No more multiple highlighted lines or display corruption
2. **Full navigation**: Users can navigate by item (arrows) or by page (n/b)
3. **Consistent behavior**: Number entry and exit behavior matches standard interactive mode
4. **Terminal safety**: Works correctly at all terminal positions and sizes
5. **Better UX**: Clear status information and visual feedback

This plan will make the arrow navigation more robust, feature-complete, and consistent with user expectations while fixing all the identified issues.