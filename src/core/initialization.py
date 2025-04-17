"""
Handles system-wide initialization tasks at startup.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def initialize_system(reset_data: bool = False):
    """
    Initialize system components, optionally resetting data files.

    Args:
        reset_data: If True, data files will be cleared/reset
    """
    logger.info("Initializing system...")

    # Ensure data directories exist
    _ensure_data_directories()

    # Initialize keyword system (in manager.py)
    # The import will automatically call initialize_keywords()
    import core.keywords

    if reset_data:
        logger.info("Resetting keyword data...")
        core.keywords.initialize_keywords(clear_data=True)

    logger.info("System initialization complete")


def _ensure_data_directories():
    """Create necessary data directories if they don't exist."""
    directories = [
        Path("data"),
        Path("data") / "keywords",
        # Add other data directories as needed
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")


# Optional: Add any other initialization tasks below
