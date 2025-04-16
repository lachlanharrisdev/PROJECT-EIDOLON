"""
Unified keyword management system for Project Eidolon.
Provides a simple API for managing, retrieving, and updating keywords.
"""

from core.keywords.manager import (
    get_keywords,
    add_keyword,
    remove_keyword,
    register_provider,
    reset_keywords,
    initialize_keywords,
)

__all__ = [
    "get_keywords",
    "add_keyword",
    "remove_keyword",
    "register_provider",
    "reset_keywords",
    "initialize_keywords",
]

# Initialize the keyword system when the module is imported
initialize_keywords()
