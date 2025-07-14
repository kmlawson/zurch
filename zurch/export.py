import csv
import json
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from .models import ZoteroItem
from .search import ZoteroDatabase

logger = logging.getLogger(__name__)

def is_safe_path(file_path: Path) -> bool:
    """Check if the file path is safe (not in dangerous system directories)."""
    # Get absolute path to resolve any relative paths
    abs_path = file_path.resolve()
    
    # Dangerous system directories to avoid
    dangerous_dirs = [
        "/System",
        "/Library",
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/Applications",
        "/private",
        "/etc",
        "/var/log",
        "/var/db",
        "/var/root",
        "/root"
    ]
    
    # Add Windows specific dangerous directories
    if os.name == 'nt':
        dangerous_dirs.extend([
            "C:\\Windows",
            "C:\\System32",
            "C:\\Program Files",
            "C:\\Program Files (x86)"
        ])
    
    # Check if path starts with any dangerous directory
    for dangerous_dir in dangerous_dirs:
        if str(abs_path).startswith(dangerous_dir):
            return False
    
    return True

def ensure_directory_exists(file_path: Path) -> bool:
    """Ensure the directory exists, create if needed with user confirmation."""
    directory = file_path.parent
    
    if directory.exists():
        return True
    
    # Ask user if they want to create the directory
    print(f"Directory '{directory}' does not exist.")
    response = input("Do you want to create it? (y/n): ").strip().lower()
    
    if response in ['y', 'yes']:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {directory}")
            return True
        except Exception as e:
            print(f"Error creating directory: {e}")
            return False
    else:
        print("Export cancelled.")
        return False

def generate_export_filename(export_format: str, search_term: str = "") -> str:
    """Generate a default filename for export."""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if search_term:
        # Sanitize search term for filename
        sanitized_term = "".join(c for c in search_term if c.isalnum() or c in (' ', '-', '_')).strip()
        sanitized_term = sanitized_term.replace(' ', '_')
        return f"zurch_export_{sanitized_term}_{timestamp}.{export_format}"
    else:
        return f"zurch_export_{timestamp}.{export_format}"

def export_to_csv(items: List[ZoteroItem], db: ZoteroDatabase, file_path: Path) -> bool:
    """Export items to CSV format."""
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Define CSV headers
            headers = [
                'ID', 'Title', 'Item Type', 'Attachment Type', 'Attachment Path',
                'Authors', 'Publication Year', 'Date Added', 'Date Modified',
                'Collections', 'Tags', 'Abstract', 'DOI', 'URL'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for item in items:
                # Get additional metadata
                try:
                    metadata = db.get_item_metadata(item.item_id)
                    collections = db.get_item_collections(item.item_id)
                    tags = db.get_item_tags(item.item_id)
                    
                    # Format authors
                    authors = []
                    if 'creators' in metadata:
                        for creator in metadata['creators']:
                            if creator.get('creatorType') == 'author':
                                name_parts = []
                                if creator.get('firstName'):
                                    name_parts.append(creator['firstName'])
                                if creator.get('lastName'):
                                    name_parts.append(creator['lastName'])
                                if name_parts:
                                    authors.append(' '.join(name_parts))
                    
                    # Extract publication year from date
                    pub_year = ""
                    if 'date' in metadata:
                        date_str = metadata['date']
                        if date_str and len(date_str) >= 4:
                            pub_year = date_str[:4]
                    
                    # Write row
                    writer.writerow({
                        'ID': item.item_id,
                        'Title': item.title,
                        'Item Type': item.item_type,
                        'Attachment Type': item.attachment_type or '',
                        'Attachment Path': item.attachment_path or '',
                        'Authors': '; '.join(authors),
                        'Publication Year': pub_year,
                        'Date Added': metadata.get('dateAdded', ''),
                        'Date Modified': metadata.get('dateModified', ''),
                        'Collections': '; '.join(collections),
                        'Tags': '; '.join(tags),
                        'Abstract': metadata.get('abstractNote', ''),
                        'DOI': metadata.get('DOI', ''),
                        'URL': metadata.get('url', '')
                    })
                    
                except Exception as e:
                    logger.warning(f"Error getting metadata for item {item.item_id}: {e}")
                    # Write basic row without metadata
                    writer.writerow({
                        'ID': item.item_id,
                        'Title': item.title,
                        'Item Type': item.item_type,
                        'Attachment Type': item.attachment_type or '',
                        'Attachment Path': item.attachment_path or '',
                        'Authors': '',
                        'Publication Year': '',
                        'Date Added': '',
                        'Date Modified': '',
                        'Collections': '',
                        'Tags': '',
                        'Abstract': '',
                        'DOI': '',
                        'URL': ''
                    })
        
        return True
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        return False

def export_to_json(items: List[ZoteroItem], db: ZoteroDatabase, file_path: Path) -> bool:
    """Export items to JSON format."""
    try:
        export_data = []
        
        for item in items:
            # Get additional metadata
            try:
                metadata = db.get_item_metadata(item.item_id)
                collections = db.get_item_collections(item.item_id)
                tags = db.get_item_tags(item.item_id)
                
                # Create export record
                export_record = {
                    'id': item.item_id,
                    'title': item.title,
                    'itemType': item.item_type,
                    'attachmentType': item.attachment_type,
                    'attachmentPath': item.attachment_path,
                    'collections': collections,
                    'tags': tags,
                    'metadata': metadata
                }
                
                export_data.append(export_record)
                
            except Exception as e:
                logger.warning(f"Error getting metadata for item {item.item_id}: {e}")
                # Add basic record without metadata
                export_record = {
                    'id': item.item_id,
                    'title': item.title,
                    'itemType': item.item_type,
                    'attachmentType': item.attachment_type,
                    'attachmentPath': item.attachment_path,
                    'collections': [],
                    'tags': [],
                    'metadata': {}
                }
                export_data.append(export_record)
        
        # Write JSON file
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        return False

def export_items(items: List[ZoteroItem], db: ZoteroDatabase, export_format: str, 
                file_path: Optional[str] = None, search_term: str = "") -> bool:
    """Export items to specified format."""
    if not items:
        print("No items to export.")
        return False
    
    # Determine output file path
    if file_path:
        output_path = Path(file_path)
        # Add extension if not present
        if not output_path.suffix:
            output_path = output_path.with_suffix(f".{export_format}")
    else:
        # Generate filename in current directory
        filename = generate_export_filename(export_format, search_term)
        output_path = Path.cwd() / filename
    
    # Safety checks
    if not is_safe_path(output_path):
        print(f"Error: Cannot export to {output_path} - path is in a protected system directory.")
        return False
    
    # Check if file exists (no overwriting)
    if output_path.exists():
        print(f"Error: File {output_path} already exists. Will not overwrite.")
        return False
    
    # Ensure directory exists
    if not ensure_directory_exists(output_path):
        return False
    
    # Export based on format
    success = False
    if export_format == "csv":
        success = export_to_csv(items, db, output_path)
    elif export_format == "json":
        success = export_to_json(items, db, output_path)
    else:
        print(f"Unsupported export format: {export_format}")
        return False
    
    if success:
        print(f"Successfully exported {len(items)} items to {output_path}")
        return True
    else:
        print(f"Failed to export items to {output_path}")
        return False