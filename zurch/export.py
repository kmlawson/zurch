import csv
import json
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from .models import ZoteroItem
from .search import ZoteroDatabase

logger = logging.getLogger(__name__)

def get_safe_base_directories() -> List[Path]:
    """Get list of safe base directories where files can be exported."""
    import os
    from pathlib import Path
    
    safe_dirs = []
    
    # Always allow current working directory
    safe_dirs.append(Path.cwd())
    
    # Add user home directory and common subdirectories
    home_dir = Path.home()
    safe_dirs.extend([
        home_dir,
        home_dir / "Documents",
        home_dir / "Downloads", 
        home_dir / "Desktop",
    ])
    
    # Add user-specific directories based on OS
    if os.name == 'posix':  # Unix-like (macOS, Linux)
        # Add common user directories
        safe_dirs.extend([
            home_dir / "tmp",
            Path("/tmp"),
            Path("/var/tmp"),
        ])
        
        # Add XDG directories if they exist
        xdg_documents = os.environ.get('XDG_DOCUMENTS_DIR')
        xdg_download = os.environ.get('XDG_DOWNLOAD_DIR')
        xdg_desktop = os.environ.get('XDG_DESKTOP_DIR')
        
        if xdg_documents:
            safe_dirs.append(Path(xdg_documents))
        if xdg_download:
            safe_dirs.append(Path(xdg_download))
        if xdg_desktop:
            safe_dirs.append(Path(xdg_desktop))
            
    elif os.name == 'nt':  # Windows
        # Add Windows user directories
        appdata = os.environ.get('APPDATA')
        if appdata:
            safe_dirs.append(Path(appdata))
        
        localappdata = os.environ.get('LOCALAPPDATA')
        if localappdata:
            safe_dirs.append(Path(localappdata))
    
    # Filter to only existing directories and resolve paths
    safe_dirs = [d.resolve() for d in safe_dirs if d.exists() and d.is_dir()]
    
    return safe_dirs

def is_safe_path(file_path: Path) -> bool:
    """Check if the file path is within safe directories using whitelist approach.
    
    This uses a whitelist approach which is more secure than blacklisting.
    Only allows files to be written to:
    - Current working directory and subdirectories
    - User home directory and common subdirectories (Documents, Downloads, Desktop)
    - Temporary directories
    - XDG directories (Linux)
    """
    try:
        # Get absolute path to resolve any relative paths
        abs_path = file_path.resolve()
        
        # Get list of safe base directories
        safe_dirs = get_safe_base_directories()
        
        # Check if the file path is within any safe directory
        for safe_dir in safe_dirs:
            try:
                # Check if abs_path is within safe_dir or is safe_dir itself
                abs_path.relative_to(safe_dir)
                logger.debug(f"Path {abs_path} is safe (within {safe_dir})")
                return True
            except ValueError:
                # Path is not within this safe directory, continue checking
                continue
        
        # If we get here, the path is not within any safe directory
        logger.warning(f"Path {abs_path} is not within any safe directory")
        return False
        
    except Exception as e:
        logger.error(f"Error checking path safety: {e}")
        return False

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
    """Export items to CSV format with atomic file creation."""
    import tempfile
    import os
    
    # Create temporary file in same directory as target (for atomic rename)
    temp_fd = None
    temp_path = None
    
    try:
        # Create temp file with restricted permissions
        temp_fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent,
            prefix='.tmp_export_',
            suffix='.csv'
        )
        
        # Set restrictive permissions (owner read/write only)
        # Note: On Windows, os.chmod has limited effect, but won't cause errors
        try:
            os.chmod(temp_path, 0o600)
        except (OSError, NotImplementedError):
            # On some systems, chmod might not be fully supported
            # This is acceptable for temporary files
            pass
        
        # Write to temp file
        with os.fdopen(temp_fd, 'w', newline='', encoding='utf-8') as csvfile:
            temp_fd = None  # fdopen takes ownership
            # Define CSV headers
            headers = [
                'ID', 'Title', 'Item Type', 'Attachment Type', 'Attachment Path',
                'Authors', 'Publication Year', 'Date Added', 'Date Modified',
                'Collections', 'Tags', 'Abstract', 'DOI', 'URL'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            # Bulk fetch metadata to avoid N+1 queries
            item_ids = [item.item_id for item in items]
            try:
                metadata_cache = db.get_bulk_item_metadata(item_ids)
                logger.debug(f"Bulk fetched metadata for CSV export: {len(item_ids)} items")
            except Exception as e:
                logger.warning(f"Error bulk fetching metadata for CSV export: {e}")
                metadata_cache = {}
            
            # Get collections and tags for all items (these could be optimized too)
            collections_cache = {}
            tags_cache = {}
            for item in items:
                try:
                    collections_cache[item.item_id] = db.get_item_collections(item.item_id)
                    tags_cache[item.item_id] = db.get_item_tags(item.item_id)
                except Exception as e:
                    logger.warning(f"Error getting collections/tags for item {item.item_id}: {e}")
                    collections_cache[item.item_id] = []
                    tags_cache[item.item_id] = []
            
            for item in items:
                # Get cached metadata
                try:
                    metadata = metadata_cache.get(item.item_id, {})
                    collections = collections_cache.get(item.item_id, [])
                    tags = tags_cache.get(item.item_id, [])
                    
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
        
        # Atomic rename - this will fail if target exists
        os.rename(temp_path, file_path)
        temp_path = None  # Successfully moved
        
        return True
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        return False
    finally:
        # Clean up temp file if still exists
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except:
                pass
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

def export_to_json(items: List[ZoteroItem], db: ZoteroDatabase, file_path: Path) -> bool:
    """Export items to JSON format with atomic file creation."""
    import tempfile
    import os
    
    # Create temporary file in same directory as target (for atomic rename)
    temp_fd = None
    temp_path = None
    
    try:
        export_data = []
        
        # Bulk fetch metadata to avoid N+1 queries
        item_ids = [item.item_id for item in items]
        try:
            metadata_cache = db.get_bulk_item_metadata(item_ids)
            logger.debug(f"Bulk fetched metadata for JSON export: {len(item_ids)} items")
        except Exception as e:
            logger.warning(f"Error bulk fetching metadata for JSON export: {e}")
            metadata_cache = {}
        
        # Get collections and tags for all items (these could be optimized too)
        collections_cache = {}
        tags_cache = {}
        for item in items:
            try:
                collections_cache[item.item_id] = db.get_item_collections(item.item_id)
                tags_cache[item.item_id] = db.get_item_tags(item.item_id)
            except Exception as e:
                logger.warning(f"Error getting collections/tags for item {item.item_id}: {e}")
                collections_cache[item.item_id] = []
                tags_cache[item.item_id] = []
        
        for item in items:
            # Get cached metadata
            try:
                metadata = metadata_cache.get(item.item_id, {})
                collections = collections_cache.get(item.item_id, [])
                tags = tags_cache.get(item.item_id, [])
                
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
        
        # Create temp file with restricted permissions
        temp_fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent,
            prefix='.tmp_export_',
            suffix='.json'
        )
        
        # Set restrictive permissions (owner read/write only)
        # Note: On Windows, os.chmod has limited effect, but won't cause errors
        try:
            os.chmod(temp_path, 0o600)
        except (OSError, NotImplementedError):
            # On some systems, chmod might not be fully supported
            # This is acceptable for temporary files
            pass
        
        # Write JSON file to temp location
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as jsonfile:
            temp_fd = None  # fdopen takes ownership
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        # Atomic rename - this will fail if target exists
        os.rename(temp_path, file_path)
        temp_path = None  # Successfully moved
        
        return True
        
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        return False
    finally:
        # Clean up temp file if still exists
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except:
                pass
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

from .constants import Defaults, ErrorMessages, SuccessMessages

# Maximum export file size 
MAX_EXPORT_SIZE = Defaults.MAX_EXPORT_SIZE

def export_items(items: List[ZoteroItem], db: ZoteroDatabase, export_format: str, 
                file_path: Optional[str] = None, search_term: str = "") -> bool:
    """Export items to specified format with security checks."""
    if not items:
        print("No items to export.")
        return False
    
    # Check if export would be too large (rough estimate)
    estimated_size = len(items) * 2000  # Assume ~2KB per item average
    if estimated_size > MAX_EXPORT_SIZE:
        print(ErrorMessages.FILE_TOO_LARGE.format(
            estimated_size / 1024 / 1024, MAX_EXPORT_SIZE / 1024 / 1024
        ))
        print("Try reducing the number of items with -x flag.")
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
    
    # Safety checks with improved error messages
    if not is_safe_path(output_path):
        safe_dirs = get_safe_base_directories()
        safe_dir_list = '\n  '.join(str(d) for d in safe_dirs[:5])  # Show first 5 safe directories
        print(f"Error: Cannot export to {output_path}")
        print(f"For security, exports are only allowed to safe directories such as:")
        print(f"  {safe_dir_list}")
        if len(safe_dirs) > 5:
            print(f"  ... and {len(safe_dirs) - 5} other safe locations")
        print(f"Try exporting to a subdirectory of your home directory or current working directory.")
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
        # Final safety check - verify file was created in expected location
        try:
            final_path = output_path.resolve()
            if not is_safe_path(final_path):
                # File ended up in unsafe location - remove it
                logger.error(f"Export ended up in unsafe location: {final_path}")
                try:
                    os.unlink(final_path)
                except:
                    pass
                print(f"Error: Export failed - file created in unsafe location")
                return False
            
            # Verify file exists and has reasonable size
            if not final_path.exists():
                print(f"Error: Export file was not created")
                return False
                
            file_size = final_path.stat().st_size
            if file_size > MAX_EXPORT_SIZE:
                # File is too large - remove it
                logger.error(f"Export file too large: {file_size} bytes")
                try:
                    os.unlink(final_path)
                except:
                    pass
                print(f"Error: Export file exceeded size limit ({file_size / 1024 / 1024:.1f}MB)")
                return False
                
            print(SuccessMessages.EXPORT_SUCCESS.format(len(items), output_path))
            return True
            
        except Exception as e:
            logger.error(f"Error verifying export: {e}")
            print(f"Error: Could not verify export file")
            return False
    else:
        print(f"Failed to export items to {output_path}")
        return False