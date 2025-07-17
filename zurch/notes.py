import re
import html
from pathlib import Path
from typing import List
import logging

from .database import DatabaseConnection

logger = logging.getLogger(__name__)


class NotesService:
    """Service for handling Zotero notes operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
    
    def has_notes(self, item_id: int) -> bool:
        """Check if an item has attached notes."""
        query = """
        SELECT COUNT(*) as count
        FROM itemNotes
        WHERE parentItemID = ?
        """
        
        result = self.db_connection.execute_query(query, (item_id,))
        return result[0]["count"] > 0 if result else False
    
    def get_notes_content(self, item_id: int, strip_html: bool = False) -> List[str]:
        """Get all notes content for an item."""
        query = """
        SELECT note
        FROM itemNotes
        WHERE parentItemID = ?
        ORDER BY itemID
        """
        
        result = self.db_connection.execute_query(query, (item_id,))
        notes = []
        
        for row in result:
            note_content = row["note"] or ""
            if strip_html:
                note_content = sanitize_notes_content(note_content)
            notes.append(note_content)
        
        return notes
    
    def save_notes_to_file(self, item_id: int, file_path: Path) -> bool:
        """Save item notes to a file."""
        notes = self.get_notes_content(item_id, strip_html=True)
        
        if not notes:
            logger.info(f"No notes found for item {item_id}")
            return False
        
        try:
            content = format_notes_for_display(notes)
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"Notes saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving notes to file: {e}")
            return False


def sanitize_notes_content(html_content: str) -> str:
    """Sanitize HTML notes content for safe display and file output."""
    if not html_content:
        return ""
    
    # Remove script tags and their content
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove style tags and their content
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert paragraph breaks to double newlines
    html_content = re.sub(r'</p>\s*<p[^>]*>', '\n\n', html_content)
    html_content = re.sub(r'<p[^>]*>', '', html_content)
    html_content = re.sub(r'</p>', '', html_content)
    
    # Convert line breaks
    html_content = re.sub(r'<br\s*/?>', '\n', html_content)
    
    # Remove all remaining HTML tags
    html_content = re.sub(r'<[^>]+>', '', html_content)
    
    # Decode HTML entities
    html_content = html.unescape(html_content)
    
    # Clean up whitespace
    html_content = re.sub(r'\n\s*\n', '\n\n', html_content)  # Multiple newlines to double
    html_content = re.sub(r'[ \t]+', ' ', html_content)  # Multiple spaces to single
    html_content = html_content.strip()
    
    return html_content


def format_notes_for_display(notes: List[str]) -> str:
    """Format notes for terminal display or file output."""
    if not notes:
        return "No notes available."
    
    formatted_notes = []
    for i, note in enumerate(notes, 1):
        if len(notes) > 1:
            formatted_notes.append(f"Note {i}:")
            formatted_notes.append("=" * 40)
        formatted_notes.append(note)
        if i < len(notes):
            formatted_notes.append("\n" + "-" * 40 + "\n")
    
    return "\n".join(formatted_notes)


def format_notes_icon(has_notes: bool) -> str:
    """Format the notes icon for display."""
    return "📝" if has_notes else ""