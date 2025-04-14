import os
import platform
import logging
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def get_platform_info():
    """Get information about the current platform in a standardized way"""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
    }

def ensure_data_dir(subdir=None):
    """Ensure data directory exists and return path"""
    # Use Path for cross-platform compatibility
    base_path = Path("data")
    if subdir:
        base_path = base_path / subdir
    
    # Create directory if it doesn't exist
    base_path.mkdir(parents=True, exist_ok=True)
    
    return base_path

def save_json(data, filename, subdir=None):
    """Save data as JSON to the data directory"""
    data_dir = ensure_data_dir(subdir)
    file_path = data_dir / filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.debug(f"Data saved to {file_path}")
    return file_path

def load_json(filename, subdir=None):
    """Load data from JSON file in the data directory"""
    data_dir = ensure_data_dir(subdir)
    file_path = data_dir / filename
    
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.debug(f"Data loaded from {file_path}")
    return data

def timestamp_filename(prefix="data", extension="json"):
    """Generate a filename with a timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"