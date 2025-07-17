"""Configuration management using Pydantic models."""

import logging
from pathlib import Path
from typing import Optional
from pydantic import ValidationError

from .config_models import ZurchConfigModel, ZurchConfigModel as ZurchConfig

logger = logging.getLogger(__name__)


def load_config(config_file: Optional[Path] = None) -> ZurchConfigModel:
    """Load configuration from file using Pydantic validation.
    
    Args:
        config_file: Path to config file. If None, uses default location.
        
    Returns:
        Validated configuration object.
    """
    if config_file is None:
        from .utils import get_config_file
        config_file = get_config_file()
    
    try:
        return ZurchConfigModel.load_from_file(config_file)
    except ValidationError as e:
        logger.warning(f"Invalid configuration: {e}")
        logger.info("Using default configuration")
        return ZurchConfigModel()
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return ZurchConfigModel()


def save_config(config: ZurchConfigModel, config_file: Optional[Path] = None) -> bool:
    """Save configuration to file with validation.
    
    Args:
        config: Configuration object to save
        config_file: Path to save to. If None, uses default location.
        
    Returns:
        True if saved successfully, False otherwise.
    """
    if config_file is None:
        from .utils import get_config_file
        config_file = get_config_file()
    
    try:
        config.save_to_file(config_file)
        logger.info(f"Configuration saved to {config_file}")
        return True
    except ValidationError as e:
        logger.error(f"Invalid configuration: {e}")
        return False
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False


def validate_config_data(data: dict) -> tuple[bool, str]:
    """Validate configuration data using Pydantic.
    
    Args:
        data: Configuration dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ZurchConfigModel(**data)
        return True, ""
    except ValidationError as e:
        # Format validation errors nicely
        errors = []
        for error in e.errors():
            field = '.'.join(str(loc) for loc in error['loc'])
            msg = error['msg']
            errors.append(f"{field}: {msg}")
        return False, "; ".join(errors)
    except Exception as e:
        return False, str(e)


def migrate_legacy_config(legacy_config: dict) -> dict:
    """Migrate legacy configuration format to new format.
    
    Args:
        legacy_config: Old format configuration
        
    Returns:
        New format configuration dictionary
    """
    # Map old field names to new ones if needed
    config = legacy_config.copy()
    
    # Ensure path fields are strings
    if 'zotero_database_path' in config and config['zotero_database_path']:
        config['zotero_database_path'] = str(config['zotero_database_path'])
    
    # Remove deprecated fields
    deprecated_fields = ['zotero_data_dir']  # This is now computed
    for field in deprecated_fields:
        config.pop(field, None)
    
    return config


def create_default_config() -> ZurchConfigModel:
    """Create a default configuration object."""
    return ZurchConfigModel()


def update_config_value(config: ZurchConfigModel, key: str, value: any) -> ZurchConfigModel:
    """Update a single configuration value with validation.
    
    Args:
        config: Current configuration
        key: Configuration key to update
        value: New value
        
    Returns:
        Updated configuration object
        
    Raises:
        ValidationError: If the new value is invalid
    """
    # Get current data
    data = config.to_dict()
    
    # Update the value
    data[key] = value
    
    # Create new config with validation
    return ZurchConfigModel(**data)


def get_config_value(config: ZurchConfigModel, key: str, default: any = None) -> any:
    """Get a configuration value with a default.
    
    Args:
        config: Configuration object
        key: Configuration key
        default: Default value if key doesn't exist
        
    Returns:
        Configuration value or default
    """
    return getattr(config, key, default)


# Backward compatibility exports already imported above

__all__ = [
    'load_config',
    'save_config',
    'validate_config_data',
    'migrate_legacy_config',
    'create_default_config',
    'update_config_value',
    'get_config_value',
    'ZurchConfig',
    'ZurchConfigModel'
]