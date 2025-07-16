# Cross-Platform Improvements for Zurch v0.7.4

## Summary

This document outlines the cross-platform improvements made to zurch to enhance compatibility with Windows, Linux, and macOS systems based on the cross-platform compatibility report.

## Improvements Made

### 1. Enhanced Keyboard Input Support (keyboard.py)

**Problem**: Interactive mode relied on Unix-only `termios` module, causing degraded experience on Windows.

**Solution**: Implemented Windows-specific keyboard support using `msvcrt`:

- **Windows**: Uses `msvcrt.kbhit()` and `msvcrt.getch()` for immediate key response
- **Unix/Linux/macOS**: Uses existing `termios` and `tty` modules  
- **Fallback**: Regular `input()` when neither is available

**Benefits**:
- Windows users now get the same fluid interactive experience as Unix users
- Single-key navigation works on all platforms
- Proper handling of Ctrl+C, Ctrl+D, and other special keys across platforms

### 2. Intelligent ANSI Color Detection (constants.py)

**Problem**: ANSI escape codes would display as garbled text in older Windows terminals (cmd.exe).

**Solution**: Implemented smart ANSI color detection that:

- **Detects Windows Terminal**: Checks for `WT_SESSION` environment variable
- **Detects modern terminals**: Checks `TERM` environment variable for xterm, screen, tmux
- **Detects Windows version**: Windows 10 build 10586+ supports ANSI in cmd.exe
- **Detects COLORTERM**: Checks for `COLORTERM` environment variable
- **Graceful fallback**: Disables colors in older/unsupported terminals

**Benefits**:
- Clean output on all terminal types
- Colors work in modern Windows terminals (Windows Terminal, PowerShell)
- No garbled text in older cmd.exe terminals
- Automatic detection without user configuration

### 3. Improved Export File Permissions (export.py)

**Problem**: `os.chmod(0o600)` would fail on some Windows systems where file permissions work differently.

**Solution**: Added graceful error handling:

```python
try:
    os.chmod(temp_path, 0o600)
except (OSError, NotImplementedError):
    # On some systems, chmod might not be fully supported
    # This is acceptable for temporary files
    pass
```

**Benefits**:
- Export works reliably on all platforms
- Maintains security on Unix-like systems
- Graceful fallback on Windows systems
- No crashes due to permission setting failures

### 4. Enhanced Error Handling for Interactive Mode

**Problem**: Invalid input would cause interactive mode to exit instead of showing error and continuing.

**Solution**: Separated `ValueError` and `KeyboardInterrupt` handling:

- **ValueError**: Shows "Invalid input" message and continues
- **KeyboardInterrupt**: Still cancels with "Cancelled" message  
- **Empty string**: Now treated same as '0' for cancellation

**Benefits**:
- More user-friendly interactive experience
- Users don't get kicked out accidentally
- Consistent behavior across all platforms

### 5. Platform Capability Detection (utils.py)

**Addition**: Added `get_platform_capabilities()` function to detect:

- ANSI color support
- Single character input support  
- File permissions support
- Platform type (Windows/Unix)

**Benefits**:
- Helps developers and users understand platform capabilities
- Enables conditional features based on platform support
- Useful for debugging and support

## Testing

The improvements have been tested to ensure:

1. **Keyboard input** works with immediate response on Windows (msvcrt) and Unix (termios)
2. **ANSI colors** are properly detected and disabled in older terminals
3. **File permissions** are handled gracefully across platforms
4. **Export functionality** works without errors on all platforms
5. **Interactive mode** provides consistent experience across platforms

## Platform-Specific Behaviors

### Windows
- Uses `msvcrt` for single-character input
- ANSI colors disabled in older cmd.exe, enabled in Windows Terminal/PowerShell
- File permissions have limited effect but don't cause errors
- Path handling works correctly with both `/` and `\\` separators

### Unix/Linux/macOS  
- Uses `termios` for single-character input
- ANSI colors enabled in most terminals
- Full file permissions support
- Standard Unix path handling

### All Platforms
- Graceful fallback to regular `input()` when specialized modules unavailable
- Unicode icons and symbols work across platforms
- Path operations use `pathlib` for cross-platform compatibility
- Configuration files stored in OS-appropriate locations

## Future Enhancements

The current implementation provides excellent cross-platform compatibility. Potential future improvements could include:

1. **PowerShell-specific optimizations** for Windows PowerShell users
2. **Terminal capability detection** for more advanced terminal features
3. **Windows-specific file association** handling for attachment opening
4. **macOS-specific features** like integration with Spotlight or Finder

## Dependencies

No additional dependencies were introduced. The improvements use only standard library modules:

- `msvcrt` (Windows standard library)
- `termios` and `tty` (Unix standard library)  
- `os`, `sys`, `platform` (all platforms)
- `pathlib` (cross-platform path handling)

This ensures the tool remains lightweight and doesn't require external packages for cross-platform functionality.