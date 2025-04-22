"""
Translation Layer for I/O in the Message Bus.

This package provides functionality for automatic data type conversion
between modules in the message bus system. It includes:

- A TypeTranslator class for converting between data types
- Pre-defined translation rules for common type conversions
- An LRU cache for efficient repeated translations
- A global translator instance for use throughout the application
"""

from .translator import TypeTranslator, translator
from .translations import Translations
from .consts import type_mapping, default_rules

__all__ = [
    "TypeTranslator",
    "translator",
    "Translations",
    "type_mapping",
    "default_rules",
]
