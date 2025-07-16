# Zurch v0.7.4: Cross-Platform Compatibility Report (Windows & Linux)

## 1. Executive Summary

This report analyzes the `zurch` codebase (version 0.7.4) to assess its compatibility with Windows and Linux environments.

**Overall Assessment:** The `zurch` tool is **highly compatible** with both Windows and Linux. The code demonstrates a strong awareness of cross-platform challenges, employing platform-agnostic libraries like `pathlib` and including explicit OS checks where necessary.

The core functionality—searching, listing, filtering, and exporting—is expected to work flawlessly on both platforms. However, there are minor differences in user experience and behavior, primarily related to interactive features and file permissions, which are detailed below.

---

## 2. Detailed Analysis

### 2.1. Installation

The project uses `pyproject.toml` and `uv`, which are fully cross-platform. The installation process via `uv tool install .` will work without modification on Windows and Linux, provided `uv` is installed. All dependencies listed appear to be pure Python and compatible with both operating systems.

### 2.2. Configuration

Configuration file handling is robust and cross-platform.

-   **Config File Location (`utils.py`):** The tool correctly uses `platform.system()` and environment variables (`APPDATA` on Windows, `XDG_CONFIG_HOME` or `~/.config` on Linux) to store `config.json` in the standard location for each OS. This is excellent practice.
-   **Database Path (`utils.py`):** The `find_zotero_database` function correctly identifies default Zotero installation paths for Windows, macOS, and Linux, making initial setup smooth on all platforms.
-   **Path Handling:** The extensive use of `pathlib` ensures that file paths provided in the configuration (e.g., `zotero_database_path`) are handled correctly regardless of whether they use forward slashes (`/`) or backslashes (`\\`).

### 2.3. Core Functionality

All core features are expected to work correctly on both Windows and Linux.

-   **Database Interaction (`database.py`, `queries.py`):** The use of `sqlite3` and standard SQL queries is fully cross-platform. The read-only connection string (`mode=ro`) is also compatible.
-   **Searching & Filtering (`search.py`, `items.py`, `collections.py`):** All logic for searching and filtering is OS-agnostic.
-   **File Export (`export.py`):** The export functionality is cross-platform. The `is_safe_path` function correctly identifies standard user directories (Documents, Downloads, etc.) on both Windows and POSIX systems. Filename sanitization in `handlers.py` removes characters that are illegal on Windows, preventing errors when creating files.

---

## 3. Potential OS-Specific Issues & Recommendations

While the tool will function correctly, some aspects of the user experience and system interaction will differ between platforms.

### 3.1. Major Issue: Interactive Mode User Experience

-   **Issue:** The enhanced interactive experience, which allows for single-character input without pressing `Enter` (e.g., for pagination or metadata navigation), relies on the `termios` and `tty` modules. These modules are **only available on POSIX-compliant systems (Linux, macOS)**.
-   **Code Analysis (`keyboard.py`, `pagination.py`):** The code correctly handles the absence of these modules by checking `HAS_TERMIOS` and falling back to the standard `input()` function on Windows.
-   **Impact on Windows:** The tool will not crash. However, the user experience will be degraded. Instead of pressing `n` to go to the next page, a Windows user will have to press `n` and then `Enter`. This makes navigation less fluid.
-   **Recommendation:** For a truly equivalent experience, the developers could implement Windows-specific single-character input using the `msvcrt` module. This could be added to `keyboard.py` behind an `os.name == 'nt'` check.

```python
# Example for keyboard.py
import os
if os.name == 'nt':
    import msvcrt
    # ... implementation using msvcrt.getch()
else:
    import termios, tty
    # ... existing implementation
```

### 3.2. Minor Issue: ANSI Color Codes

-   **Issue:** The tool uses ANSI escape codes (e.g., `\033[1m` for bold) in `constants.py` and `display.py` to add color and style to the terminal output.
-   **Impact:** These codes work perfectly on virtually all Linux terminals and on modern Windows environments like **Windows Terminal** and **PowerShell**. However, they may render as garbled text (e.g., `[1m`) in older, legacy Windows command prompts (`cmd.exe`).
-   **Recommendation:** This is a low-priority issue, as modern terminals are now standard. A potential enhancement would be to use a library like `colorama` which can be configured to work on older Windows terminals by converting ANSI codes to the appropriate Win32 API calls.

### 3.3. Minor Issue: Export File Permissions

-   **Issue:** The `export.py` script attempts to set file permissions to `0o600` (owner read/write only) on temporary files using `os.chmod`.
-   **Impact:** This is a POSIX-specific feature. On Windows, `os.chmod` has a very limited effect and cannot replicate this permission scheme. The exported files will be created successfully, but they will not have the same restrictive permissions as they would on Linux.
-   **Recommendation:** This is a minor security difference. The behavior is acceptable, but it's a known limitation of cross-platform file permission handling in Python. No action is required unless strict permission control on Windows is deemed critical.

## 4. Conclusion

The `zurch` tool is well-written from a cross-platform perspective. It should be fully functional and reliable for users on both Windows and Linux. The primary difference is a degradation of the user experience in interactive mode on Windows. Addressing this would bring the tool to near-perfect parity across platforms.

