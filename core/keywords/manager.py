"""
Central manager for keyword storage, retrieval, and provider registration.
Uses a single data file and supports multiple keyword providers.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)

# Type definition for keyword providers
KeywordProviderType = Callable[[], List[str]]

# Global state for the keyword system
_keywords: List[str] = []
_providers: Dict[str, KeywordProviderType] = {}
_active_provider: Optional[str] = None
_data_file: Path = Path("data") / "keywords" / "keywords.json"

# Default keywords to use when no provider is available or the data file is empty
_DEFAULT_KEYWORDS = [
    "politics",
    "government",
    "election",
    "democracy",
    "president",
    "congress",
    "senate",
    "parliament",
    "diplomacy",
    "foreign policy",
    "legislation",
]


def _ensure_data_directory():
    """Ensure the data directory exists."""
    data_dir = Path("data") / "keywords"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def initialize_keywords(clear_data: bool = False):
    """
    Initialize the keyword system.

    Args:
        clear_data: If True, any existing keyword data will be cleared.
    """
    global _keywords, _data_file

    # Ensure data directory exists
    _ensure_data_directory()

    # Clear data if requested
    if clear_data and _data_file.exists():
        logger.info(f"Clearing keyword data from {_data_file}")
        _data_file.unlink()
        _keywords = []

    # Load keywords from file if it exists
    if _data_file.exists():
        try:
            with open(_data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    _keywords = data
                elif isinstance(data, dict) and "keywords" in data:
                    _keywords = data["keywords"]
                else:
                    logger.warning(
                        f"Invalid format in keyword data file. Using default keywords."
                    )
                    _keywords = _DEFAULT_KEYWORDS
        except Exception as e:
            logger.error(f"Error loading keywords from {_data_file}: {e}")
            _keywords = _DEFAULT_KEYWORDS
    else:
        # If no file exists, use default keywords
        _keywords = _DEFAULT_KEYWORDS
        _save_keywords()

    # Register the default provider
    register_provider("default", lambda: _DEFAULT_KEYWORDS)

    logger.info(f"Keyword system initialized with {len(_keywords)} keywords")


def _save_keywords():
    """Save the current keywords to the data file."""
    try:
        with open(_data_file, "w", encoding="utf-8") as f:
            json.dump(_keywords, f, indent=2)
        logger.debug(f"Saved {len(_keywords)} keywords to {_data_file}")
    except Exception as e:
        logger.error(f"Error saving keywords: {e}")


def get_keywords() -> List[str]:
    """Get the current list of keywords."""
    global _keywords
    return _keywords.copy()


def add_keyword(keyword: str) -> bool:
    """
    Add a new keyword to the list if it doesn't already exist.

    Returns:
        True if the keyword was added, False otherwise.
    """
    global _keywords
    if keyword not in _keywords:
        _keywords.append(keyword)
        _save_keywords()
        return True
    return False


def remove_keyword(keyword: str) -> bool:
    """
    Remove a keyword from the list if it exists.

    Returns:
        True if the keyword was removed, False otherwise.
    """
    global _keywords
    if keyword in _keywords:
        _keywords.remove(keyword)
        _save_keywords()
        return True
    return False


def reset_keywords():
    """Reset the keywords to the default list."""
    global _keywords
    _keywords = _DEFAULT_KEYWORDS.copy()
    _save_keywords()
    return _keywords


def register_provider(
    name: str, provider: KeywordProviderType, make_active: bool = False
) -> bool:
    """
    Register a new keyword provider.

    Args:
        name: Unique identifier for the provider
        provider: Function that returns a list of keywords
        make_active: Whether to immediately activate this provider

    Returns:
        True if registration was successful, False otherwise
    """
    global _providers, _active_provider

    if name in _providers:
        logger.warning(f"Provider '{name}' already registered. Updating.")

    _providers[name] = provider
    logger.info(f"Registered keyword provider: {name}")

    if make_active or _active_provider is None:
        return activate_provider(name)

    return True


def activate_provider(name: str) -> bool:
    """
    Activate a keyword provider to update the current keyword list.

    Args:
        name: Name of the provider to activate

    Returns:
        True if activation was successful, False otherwise
    """
    global _providers, _active_provider, _keywords

    if name not in _providers:
        logger.error(f"Unknown keyword provider: {name}")
        return False

    try:
        # Get keywords from the provider
        new_keywords = _providers[name]()

        # Update the current keywords
        _keywords = new_keywords
        _active_provider = name

        # Save to disk
        _save_keywords()

        logger.info(f"Activated provider '{name}' with {len(_keywords)} keywords")
        return True
    except Exception as e:
        logger.error(f"Error activating provider '{name}': {e}")
        return False


# Convenience function to get the default keywords
def get_default_keywords() -> List[str]:
    """Get the list of default keywords."""
    return _DEFAULT_KEYWORDS.copy()
