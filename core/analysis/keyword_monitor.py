import os
import json
import logging
import datetime
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

try:
    import spacy

    NLP_AVAILABLE = True
except ImportError:
    logger.warning("spaCy not installed. Entity extraction will be limited.")
    NLP_AVAILABLE = False


class KeywordMonitor:
    """
    Monitors political keywords from news headlines and tracks their popularity.
    Uses NLP to extract entities like countries and political figures from headlines.
    """

    def __init__(
        self,
        data_file: str = "political_keywords.json",
        rss_url: str = "https://news.google.com/rss/search?q=politics",
        max_age_days: int = 30,
        min_mentions: int = 1,
    ):
        """
        Initialize the keyword monitor.

        Args:
            data_file: JSON file to store keyword data
            rss_url: URL of the RSS feed to monitor
            max_age_days: Maximum age in days for a keyword before it's considered stale
            min_mentions: Minimum number of mentions for a keyword to be retained
        """
        # Ensure data directory structure exists before creating paths
        data_dir = Path("data") / "keywords"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = data_dir / data_file

        self.rss_url = rss_url
        self.max_age_days = max_age_days
        self.min_mentions = min_mentions

        # Initialize spaCy NLP model
        self.nlp = None
        if NLP_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy NLP model")
            except Exception as e:
                logger.error(f"Failed to load spaCy model: {e}")

        # Load existing keyword data if available
        self.keyword_data = self._load_keyword_data()

    def _load_keyword_data(self) -> Dict[str, Any]:
        """Load existing keyword data from JSON file or initialize if not present."""
        default_data = {
            "entities": {},
            "last_updated": datetime.datetime.now().isoformat(),
        }

        if not self.data_file.exists():
            logger.info(
                f"No existing keyword data file found at {self.data_file}. Creating new database."
            )
            self._save_keyword_data(default_data)
            return default_data

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                file_content = f.read().strip()
                if not file_content:  # Empty file
                    logger.warning(
                        f"Empty keyword data file at {self.data_file}. Creating new database."
                    )
                    self._save_keyword_data(default_data)
                    return default_data

                return json.loads(file_content)

        except json.JSONDecodeError as e:
            logger.error(f"Error loading keyword data (invalid JSON): {e}")
            logger.info(f"Creating new keyword database file at {self.data_file}")
            self._save_keyword_data(default_data)
            return default_data

        except Exception as e:
            logger.error(f"Error loading keyword data: {e}")
            return default_data

    def _save_keyword_data(self, data=None):
        """Save keyword data to JSON file."""
        if data is None:
            data = self.keyword_data

        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved keyword data to {self.data_file}")
        except Exception as e:
            logger.error(f"Error saving keyword data: {e}")

    def fetch_headlines(self) -> List[str]:
        """Fetch headlines from RSS feed."""
        try:
            response = requests.get(self.rss_url, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            headlines = []
            for item in root.findall(".//item"):
                title = item.find("title")
                if title is not None and title.text:
                    headlines.append(title.text)

            logger.info(f"Fetched {len(headlines)} headlines from RSS feed")
            return headlines
        except requests.RequestException as e:
            logger.error(f"Error fetching headlines (request error): {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"Error parsing RSS feed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching headlines: {e}")
            return []

    def extract_entities(self, headlines: List[str]) -> Dict[str, str]:
        """Extract political entities from headlines using NLP."""
        entities = {}

        if not headlines:
            logger.warning("No headlines provided for entity extraction")
            return entities

        if not self.nlp:
            # Fallback method using simple keyword matching
            logger.warning(
                "Using fallback entity extraction method (spaCy model not available)"
            )
            for headline in headlines:
                words = headline.split()
                for word in words:
                    if word[0].isupper() and len(word) > 3 and word.isalpha():
                        entities[word] = "UNKNOWN"
            return entities

        try:
            for headline in headlines:
                doc = self.nlp(headline)

                # Extract named entities (countries, people, organizations)
                for ent in doc.ents:
                    if ent.label_ in ["GPE", "PERSON", "ORG", "NORP"]:
                        # GPE: Countries, cities, states
                        # PERSON: People
                        # ORG: Organizations
                        # NORP: Nationalities, religious or political groups
                        entities[ent.text] = ent.label_

            logger.info(f"Extracted {len(entities)} entities from headlines")
            return entities
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {}

    def update_keyword_database(self, entities: Dict[str, str]):
        """Update the keyword database with newly extracted entities."""
        if not entities:
            logger.warning("No entities provided for database update")
            return

        now = datetime.datetime.now().isoformat()

        # Update existing entities and add new ones
        for entity_text, entity_type in entities.items():
            if entity_text in self.keyword_data["entities"]:
                # Update existing entity
                self.keyword_data["entities"][entity_text]["mentions"] += 1
                self.keyword_data["entities"][entity_text]["last_seen"] = now
            else:
                # Add new entity
                self.keyword_data["entities"][entity_text] = {
                    "type": entity_type,
                    "mentions": 1,
                    "first_seen": now,
                    "last_seen": now,
                }

        # Update last updated timestamp
        self.keyword_data["last_updated"] = now

        # Save the updated data
        self._save_keyword_data()

    def prune_stale_keywords(self):
        """Remove keywords that haven't been mentioned recently or have few mentions."""
        now = datetime.datetime.now()
        stale_cutoff = (now - datetime.timedelta(days=self.max_age_days)).isoformat()

        # Identify entities to remove
        entities_to_remove = []
        for entity, data in self.keyword_data["entities"].items():
            if data["mentions"] < self.min_mentions or data["last_seen"] < stale_cutoff:
                entities_to_remove.append(entity)

        # Remove stale entities
        for entity in entities_to_remove:
            del self.keyword_data["entities"][entity]

        logger.info(f"Pruned {len(entities_to_remove)} stale keywords")

        # Save the updated data if any entities were removed
        if entities_to_remove:
            self._save_keyword_data()

    def refresh(self) -> List[str]:
        """Refresh the keyword database with the latest headlines and return current keywords."""
        # Fetch headlines
        headlines = self.fetch_headlines()

        if headlines:
            # Extract entities
            entities = self.extract_entities(headlines)

            # Update database
            self.update_keyword_database(entities)

            # Prune stale keywords
            self.prune_stale_keywords()
        else:
            logger.warning("No headlines fetched. Using existing keyword database.")

        # Return current keywords
        return self.get_current_keywords()

    def get_current_keywords(self) -> List[str]:
        """Get the current list of monitored keywords."""
        return list(self.keyword_data["entities"].keys())

    def get_keyword_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all keywords."""
        return self.keyword_data["entities"]


# Singleton instance for global access
_keyword_monitor = None


def get_political_keywords() -> List[str]:
    """
    Get the current list of political keywords to monitor.
    This is the main function that should be called by other parts of the system.
    """
    global _keyword_monitor
    if _keyword_monitor is None:
        _keyword_monitor = KeywordMonitor()

    return _keyword_monitor.get_current_keywords()


def refresh_political_keywords() -> List[str]:
    """
    Refresh the political keywords database and return the updated list.
    """
    global _keyword_monitor
    if _keyword_monitor is None:
        _keyword_monitor = KeywordMonitor()

    return _keyword_monitor.refresh()
