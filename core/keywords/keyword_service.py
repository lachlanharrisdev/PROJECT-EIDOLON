import json
import logging
from pathlib import Path
from typing import List, Dict, Callable, Optional

logger = logging.getLogger(__name__)

# Type for keyword provider functions
KeywordProviderType = Callable[[], List[str]]


class KeywordService:
    """
    Central service for managing keywords in the system.
    Allows different providers to register and override the keyword list.
    """

    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeywordService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Ensure data directory exists
        self.data_dir = Path("data") / "keywords"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.keywords_file = self.data_dir / "keywords.json"

        # Provider registry and current provider
        self.providers: Dict[str, KeywordProviderType] = {}
        self.current_provider: Optional[str] = None

        # Load built-in keywords
        self._keywords = self._load_keywords()
        self._initialized = True

    def _load_keywords(self) -> List[str]:
        """Load keywords from the JSON file or return empty list if file doesn't exist."""
        if not self.keywords_file.exists():
            logger.info(
                f"No keywords file found at {self.keywords_file}. Using empty list."
            )
            return []

        try:
            with open(self.keywords_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "keywords" in data:
                    return data["keywords"]
                else:
                    logger.warning(f"Invalid keywords file format. Using empty list.")
                    return []
        except Exception as e:
            logger.error(f"Error loading keywords: {e}")
            return []

    def _save_keywords(self, keywords: List[str]) -> None:
        """Save keywords to the JSON file."""
        try:
            with open(self.keywords_file, "w", encoding="utf-8") as f:
                json.dump(keywords, f, indent=2)
            logger.debug(f"Saved {len(keywords)} keywords to {self.keywords_file}")
        except Exception as e:
            logger.error(f"Error saving keywords: {e}")

    def register_provider(
        self, name: str, provider: KeywordProviderType, make_current: bool = False
    ) -> None:
        """
        Register a new keyword provider.

        Args:
            name: Unique name for the provider
            provider: Function that returns a list of keywords
            make_current: Whether to immediately make this the current provider
        """
        self.providers[name] = provider
        logger.info(f"Registered keyword provider: {name}")

        if make_current or self.current_provider is None:
            self.set_current_provider(name)

    def set_current_provider(self, name: str) -> bool:
        """
        Set the current keyword provider.

        Args:
            name: Name of the provider to use

        Returns:
            True if successful, False otherwise
        """
        if name not in self.providers:
            logger.error(f"Unknown keyword provider: {name}")
            return False

        self.current_provider = name
        logger.info(f"Set current keyword provider to: {name}")

        # Update keywords from the new provider
        self.refresh_keywords()
        return True

    def refresh_keywords(self) -> List[str]:
        """
        Refresh keywords from the current provider and save them.

        Returns:
            Current list of keywords
        """
        if self.current_provider and self.current_provider in self.providers:
            try:
                self._keywords = self.providers[self.current_provider]()
                self._save_keywords(self._keywords)
                logger.info(
                    f"Refreshed {len(self._keywords)} keywords from provider: {self.current_provider}"
                )
            except Exception as e:
                logger.error(
                    f"Error refreshing keywords from provider {self.current_provider}: {e}"
                )

        return self._keywords

    def get_keywords(self) -> List[str]:
        """Get the current list of keywords."""
        return self._keywords


# Initialize the singleton service
_keyword_service = KeywordService()


def get_keywords() -> List[str]:
    """Get the current list of keywords."""
    return _keyword_service.get_keywords()


def register_provider(
    name: str, provider: KeywordProviderType, make_current: bool = False
) -> None:
    """Register a new keyword provider."""
    _keyword_service.register_provider(name, provider, make_current)


def set_provider(name: str) -> bool:
    """Set the current keyword provider."""
    return _keyword_service.set_current_provider(name)


def refresh_keywords() -> List[str]:
    """Refresh keywords from the current provider."""
    return _keyword_service.refresh_keywords()
