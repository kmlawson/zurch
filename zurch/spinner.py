"""Spinner utility for showing loading progress."""

import sys
import time
import threading
from typing import Optional


class Spinner:
    """Simple spinner for showing loading progress."""
    
    def __init__(self, message: str = "Loading", spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        self.message = message
        self.spinner_chars = spinner_chars
        self.spinning = False
        self.thread: Optional[threading.Thread] = None
        self.delay = 0.1
    
    def _spin(self):
        """Internal spinning method."""
        i = 0
        while self.spinning:
            sys.stdout.write(f"\r{self.spinner_chars[i % len(self.spinner_chars)]} {self.message}")
            sys.stdout.flush()
            time.sleep(self.delay)
            i += 1
    
    def start(self):
        """Start the spinner."""
        if not self.spinning:
            self.spinning = True
            self.thread = threading.Thread(target=self._spin)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        """Stop the spinner."""
        if self.spinning:
            self.spinning = False
            if self.thread:
                self.thread.join()
            # Clear the spinner line
            sys.stdout.write(f"\r{' ' * (len(self.message) + 2)}\r")
            sys.stdout.flush()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


class ProgressSpinner:
    """Progress spinner that shows current progress."""
    
    def __init__(self, message: str = "Processing", spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        self.message = message
        self.spinner_chars = spinner_chars
        self.spinning = False
        self.thread: Optional[threading.Thread] = None
        self.delay = 0.1
        self.progress_info = ""
    
    def _spin(self):
        """Internal spinning method."""
        i = 0
        while self.spinning:
            display_msg = f"{self.message} {self.progress_info}" if self.progress_info else self.message
            sys.stdout.write(f"\r{self.spinner_chars[i % len(self.spinner_chars)]} {display_msg}")
            sys.stdout.flush()
            time.sleep(self.delay)
            i += 1
    
    def start(self):
        """Start the spinner."""
        if not self.spinning:
            self.spinning = True
            self.thread = threading.Thread(target=self._spin)
            self.thread.daemon = True
            self.thread.start()
    
    def update_progress(self, progress_info: str):
        """Update the progress information."""
        self.progress_info = progress_info
    
    def stop(self):
        """Stop the spinner."""
        if self.spinning:
            self.spinning = False
            if self.thread:
                self.thread.join()
            # Clear the spinner line
            max_len = len(self.message) + len(self.progress_info) + 3
            sys.stdout.write(f"\r{' ' * max_len}\r")
            sys.stdout.flush()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()