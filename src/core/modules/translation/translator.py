import logging
import functools
from typing import Any, Dict, List, Tuple, Optional, Type, Union, Callable
import yaml
from pathlib import Path
import traceback

from .consts import type_mapping, default_rules
from .translations import Translations


class TypeTranslator(Translations):
    """
    A lightweight translation layer for handling data type conversions between modules.

    This class provides functionality to convert data between different types based on
    predefined rules in a configuration file. It uses an LRU cache to make repeated
    conversions efficient.

    This implementation is designed to be completely non-disruptive: if any error
    occurs during translation, the original data is passed through unchanged
    and only a warning is logged.
    """

    def __init__(self, config_path: str = "src/settings/translation_rules.yaml"):
        super().__init__()
        self.config_path = config_path
        # Use default rules as a fallback if loading fails
        self.rules = default_rules
        try:
            self.rules = self._load_rules()
        except Exception as e:
            self.logger.warning(
                f"Failed to load translation rules, using defaults: {e}"
            )
            # Continue with default rules

        # Dictionary to map type names to actual types
        self.type_mapping = type_mapping

        # Initialize the LRU cache for translations
        self._translation_cache = {}
        self.max_cache_size = (
            100  # Adjust based on expected number of unique translations
        )

    def _load_rules(self) -> Dict:
        """
        Load translation rules from the configuration file.
        This method contains error handling to prevent any exceptions from
        disrupting the application flow.
        """
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, "r") as f:
                    loaded_rules = yaml.safe_load(f)
                    if loaded_rules:
                        return loaded_rules
            else:
                self.logger.warning(
                    f"Translation rules file not found at '{self.config_path}'. "
                    f"Using default rules and creating the file."
                )

                # Create the default rules file if it doesn't exist
                try:
                    config_dir = Path(self.config_path).parent
                    config_dir.mkdir(exist_ok=True, parents=True)

                    with open(self.config_path, "w") as f:
                        yaml.dump(default_rules, f)
                    self.logger.info(
                        f"Created default translation rules at '{self.config_path}'"
                    )
                except Exception as write_error:
                    self.logger.warning(
                        f"Could not create default rules file: {write_error}"
                    )
                    # Continue with default rules in memory

            return default_rules
        except Exception as e:
            self.logger.warning(
                f"Error loading translation rules: {e}, using default rules"
            )
            return default_rules

    @functools.lru_cache(maxsize=100)
    def get_type_name(self, data_type: Type) -> str:
        """
        Get a string representation of a Python type.
        """
        try:
            for type_name, type_value in self.type_mapping.items():
                if data_type == type_value:
                    return type_name

            # If not found, use the name attribute
            return getattr(data_type, "__name__", str(data_type))
        except Exception as e:
            self.logger.warning(f"Error getting type name: {e}")
            return str(data_type)  # Fallback to string representation

    def get_python_type(self, type_name: str) -> Type:
        """
        Get a Python type from its string representation.
        """
        try:
            return self.type_mapping.get(type_name, Any)
        except Exception as e:
            self.logger.warning(f"Error getting Python type: {e}")
            return Any  # Fallback to Any type

    def _get_conversion_key(self, from_type: str, to_type: str) -> str:
        """
        Generate a key for the conversion cache.
        """
        return f"{from_type}_to_{to_type}"

    def can_convert(self, from_type: str, to_type: str) -> bool:
        """
        Check if a conversion is possible between the given types.
        This method is error-proof and will return False if any exception occurs.
        """
        try:
            if from_type == to_type:
                return True

            # Check if there's a rule for this conversion
            for rule_key, rule in self.rules.get("conversions", {}).items():
                if (
                    rule.get("from_type") == from_type
                    and rule.get("to_type") == to_type
                ):
                    return True

            return False
        except Exception as e:
            self.logger.warning(f"Error checking conversion possibility: {e}")
            return False  # Cannot convert if error

    def convert(self, data: Any, from_type: str, to_type: str) -> Tuple[Any, bool]:
        """
        Convert data from one type to another based on configured rules.
        This method is designed to be error-proof: if any exception occurs,
        it will return the original data and False for success.
        """
        try:
            # No conversion needed if types are the same
            if from_type == to_type:
                return data, True

            # Check the cache first using (from_type, to_type) as the key
            try:
                cache_key = (
                    from_type,
                    to_type,
                    str(data)[:100] if isinstance(data, str) else str(type(data)),
                )
                if cache_key in self._translation_cache:
                    return self._translation_cache[cache_key], True
            except Exception as cache_error:
                # If cache lookup fails, log and continue without using cache
                self.logger.warning(f"Cache lookup error: {cache_error}")

            # Find the appropriate conversion rule
            conversion_method = None
            for rule_key, rule in self.rules.get("conversions", {}).items():
                if (
                    rule.get("from_type") == from_type
                    and rule.get("to_type") == to_type
                ):
                    conversion_method = rule.get("method")
                    break

            if conversion_method is None:
                self.logger.debug(
                    f"No conversion rule found for {from_type} to {to_type}"
                )
                return data, False

            # Apply the appropriate conversion method
            try:
                result = None
                if conversion_method == "simple_cast":
                    target_type = self.get_python_type(to_type)
                    result = self._simple_cast(data, target_type)
                elif conversion_method == "split_string":
                    result = self._split_string(data)
                elif conversion_method == "string_to_bool":
                    result = self._string_to_bool(data)
                else:
                    self.logger.warning(
                        f"Unknown conversion method: {conversion_method}"
                    )
                    return data, False

                # Store in cache for future use
                try:
                    if len(self._translation_cache) >= self.max_cache_size:
                        # Simple cache eviction: clear the entire cache when it's full
                        self._translation_cache.clear()

                    if cache_key:  # Ensure cache_key exists
                        self._translation_cache[cache_key] = result
                except Exception as cache_store_error:
                    self.logger.warning(f"Error storing in cache: {cache_store_error}")
                    # Continue without caching

                return result, True

            except Exception as conversion_error:
                self.logger.warning(
                    f"Error during conversion from {from_type} to {to_type}: {conversion_error}"
                )
                return data, False

        except Exception as e:
            self.logger.warning(
                f"Unexpected error in convert method: {e}\n{traceback.format_exc()}"
            )
            # Return original data unchanged
            return data, False

    def translate_envelope(self, envelope, expected_type: str) -> Tuple[Any, bool]:
        """
        Translate data in a CourierEnvelope to the expected type.
        This method is completely error-proof and will never raise exceptions.
        If translation fails, it returns the original envelope unchanged.
        """
        try:
            # If no type information available, skip translation
            if not envelope.data_type or not expected_type:
                return envelope, False

            # Skip if types already match
            if envelope.data_type == expected_type:
                return envelope, False

            # Attempt conversion
            new_data, success = self.convert(
                envelope.data, envelope.data_type, expected_type
            )

            if success:
                # Update the envelope with the converted data
                envelope.data = new_data
                envelope.data_type = expected_type
                return envelope, True

            return envelope, False

        except Exception as e:
            self.logger.warning(
                f"Error translating envelope: {e}\n{traceback.format_exc()}"
            )
            # Return original envelope unchanged
            return envelope, False


# Create a singleton instance for global use
translator = TypeTranslator()
