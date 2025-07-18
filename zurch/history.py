"""Search history management for zurch."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .utils import get_config_dir

logger = logging.getLogger(__name__)


class SearchHistory:
    """Manages search history and saved searches."""
    
    def __init__(self, enabled: bool = True, max_items: int = 100):
        """Initialize search history manager.
        
        Args:
            enabled: Whether history tracking is enabled
            max_items: Maximum number of history items to keep
        """
        self.enabled = enabled
        self.max_items = max_items
        self.history_file = get_config_dir() / "search_history.json"
        self.saved_searches_file = get_config_dir() / "saved_searches.json"
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Ensure history files exist."""
        for file in [self.history_file, self.saved_searches_file]:
            if not file.exists():
                file.parent.mkdir(parents=True, exist_ok=True)
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
    
    def add_to_history(self, command: str, args: Dict[str, Any], results_count: int) -> None:
        """Add a search to history.
        
        Args:
            command: The command type (e.g., 'name', 'author', 'folder')
            args: The search arguments
            results_count: Number of results found
        """
        if not self.enabled:
            return
        
        try:
            history = self._load_history()
            
            # Create history entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "args": args,
                "results_count": results_count
            }
            
            # Add to beginning of list
            history.insert(0, entry)
            
            # Trim to max items
            if len(history) > self.max_items:
                history = history[:self.max_items]
            
            # Save back to file
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save search history: {e}")
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get search history.
        
        Args:
            limit: Maximum number of items to return
            
        Returns:
            List of history entries
        """
        history = self._load_history()
        if limit:
            return history[:limit]
        return history
    
    def clear_history(self) -> None:
        """Clear all search history."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
    
    def save_search(self, name: str, command: str, args: Dict[str, Any]) -> bool:
        """Save a search for later use.
        
        Args:
            name: Name for the saved search
            command: The command type
            args: The search arguments
            
        Returns:
            True if saved successfully
        """
        try:
            saved_searches = self._load_saved_searches()
            
            # Check if name already exists
            for i, search in enumerate(saved_searches):
                if search['name'] == name:
                    # Update existing
                    saved_searches[i] = {
                        "name": name,
                        "command": command,
                        "args": args,
                        "created": search.get('created', datetime.now().isoformat()),
                        "updated": datetime.now().isoformat()
                    }
                    break
            else:
                # Add new
                saved_searches.append({
                    "name": name,
                    "command": command,
                    "args": args,
                    "created": datetime.now().isoformat(),
                    "updated": datetime.now().isoformat()
                })
            
            # Save back to file
            with open(self.saved_searches_file, 'w', encoding='utf-8') as f:
                json.dump(saved_searches, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save search: {e}")
            return False
    
    def load_search(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a saved search.
        
        Args:
            name: Name of the saved search
            
        Returns:
            The saved search data or None if not found
        """
        saved_searches = self._load_saved_searches()
        for search in saved_searches:
            if search['name'] == name:
                return search
        return None
    
    def list_saved_searches(self) -> List[Dict[str, Any]]:
        """List all saved searches."""
        return self._load_saved_searches()
    
    def delete_saved_search(self, name: str) -> bool:
        """Delete a saved search.
        
        Args:
            name: Name of the search to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            saved_searches = self._load_saved_searches()
            original_count = len(saved_searches)
            saved_searches = [s for s in saved_searches if s['name'] != name]
            
            if len(saved_searches) < original_count:
                with open(self.saved_searches_file, 'w', encoding='utf-8') as f:
                    json.dump(saved_searches, f, indent=2, ensure_ascii=False)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete saved search: {e}")
            return False
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load history from file."""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _load_saved_searches(self) -> List[Dict[str, Any]]:
        """Load saved searches from file."""
        try:
            with open(self.saved_searches_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []