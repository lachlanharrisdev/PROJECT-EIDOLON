from typing import Any, Dict, List, Type
import logging
import traceback


class Translations:
    """
    Base class containing translation methods for converting between data types.

    This class is designed to be inherited by TypeTranslator and provides
    the core transformation methods needed for data conversions.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _simple_cast(self, data: Any, target_type: Type) -> Any:
        """
        Attempt a simple casting of data to the target type.

        Args:
            data: The data to convert
            target_type: The target type

        Returns:
            Converted data
        """
        try:
            return target_type(data)
        except Exception as e:
            self.logger.warning(f"Error casting {type(data)} to {target_type}: {e}")
            return data  # Return original data if casting fails

    def _split_string(self, data: str) -> List[str]:
        """
        Split a string into a list of strings.

        Args:
            data: String to split

        Returns:
            List of strings
        """
        try:
            if not data:
                return []

            if isinstance(data, list):
                return data

            # Split by commas, newlines, or spaces based on content
            if "," in data:
                return [item.strip() for item in data.split(",")]
            elif "\n" in data:
                return [item.strip() for item in data.split("\n") if item.strip()]
            else:
                return [item for item in data.split() if item]
        except Exception as e:
            self.logger.warning(
                f"Error splitting string: {e}\n{traceback.format_exc()}"
            )
            # Return a fallback value (empty list) if splitting fails
            return []

    def _string_to_bool(self, data: str) -> bool:
        """
        Convert a string to boolean based on common boolean string representations.

        Args:
            data: String to convert

        Returns:
            Boolean value
        """
        try:
            if isinstance(data, str):
                lowered = data.lower().strip()
                if lowered in ("true", "yes", "y", "1", "on"):
                    return True
                elif lowered in ("false", "no", "n", "0", "off"):
                    return False

            # Default for non-boolean conversions
            return bool(data)
        except Exception as e:
            self.logger.warning(
                f"Error converting to boolean: {e}\n{traceback.format_exc()}"
            )
            # Default to False if conversion fails completely
            return False
