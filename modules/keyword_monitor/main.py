from logging import Logger
import os
from typing import List, Dict, Any, Optional

import yaml
import json
import datetime
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

from core.modules.engine import ModuleCore
from core.modules.models import Meta, Device
from core.modules.util.messagebus import MessageBus

# Check for spaCy
try:
    import spacy

    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False


class KeywordMonitor:
    """
    Monitors political keywords from news headlines and tracks their popularity.
    Uses NLP to extract entities like countries and political figures from headlines.
    """

    def __init__(
        self,
        logger: Logger,
        rss_url: str = "https://news.google.com/rss/search?q=politics",
        max_age_days: int = 30,
        min_mentions: int = 1,
    ):
        self._logger = logger
        self.rss_url = rss_url
        self.max_age_days = max_age_days
        self.min_mentions = min_mentions

        # Determine the module directory dynamically
        module_dir = Path(__file__).parent
        self.keywords_file = module_dir / ".keywords.json"

        # Initialize spaCy NLP model
        self.nlp = None
        if NLP_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                self._logger.debug("Loaded spaCy NLP model")
            except Exception as e:
                self._logger.error(f"Failed to load spaCy model: {e}")

        # Track extracted entities internally
        self.entities = {}
        self.last_updated = datetime.datetime.now().isoformat()

        # Load existing keywords from file
        self.keywords = self._load_keywords()

    def _load_keywords(self) -> List[str]:
        """Load keywords from the JSON file or return an empty list if the file doesn't exist."""
        if self.keywords_file.exists():
            try:
                with open(self.keywords_file, "r", encoding="utf-8") as f:
                    keywords = json.load(f)
                    self._logger.debug(f"Loaded {len(keywords)} keywords from file")
                    return keywords
            except Exception as e:
                self._logger.error(f"Error loading keywords: {e}")
        return []

    def _save_keywords(self) -> None:
        """Save keywords to the JSON file."""
        try:
            with open(self.keywords_file, "w", encoding="utf-8") as f:
                json.dump(self.keywords, f, indent=2)
            self._logger.debug(f"Saved {len(self.keywords)} keywords to file")
        except Exception as e:
            self._logger.error(f"Error saving keywords: {e}")

    def add_keyword(self, keyword: str) -> None:
        """Add a new keyword to the list if it doesn't already exist."""
        if keyword not in self.keywords:
            self.keywords.append(keyword)
            self._save_keywords()
            self._logger.debug(f"Added new keyword: {keyword}")

    def get_keywords(self) -> List[str]:
        """Get the current list of keywords."""
        return self.keywords

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

            self._logger.info(f"Fetched {len(headlines)} headlines from RSS feed")
            return headlines
        except requests.RequestException as e:
            self._logger.error(f"Error fetching headlines (request error): {e}")
            return []
        except ET.ParseError as e:
            self._logger.error(f"Error parsing RSS feed: {e}")
            return []
        except Exception as e:
            self._logger.error(f"Error fetching headlines: {e}")
            return []

    def extract_entities(self, headlines: List[str]) -> Dict[str, str]:
        """Extract political entities from headlines using NLP."""
        entities = {}

        if not headlines:
            self._logger.warning("No headlines provided for entity extraction")
            return entities

        if not self.nlp:
            # Fallback method using simple keyword matching
            self._logger.warning(
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

            self._logger.info(f"Extracted {len(entities)} entities from headlines")
            return entities
        except Exception as e:
            self._logger.error(f"Error extracting entities: {e}")
            return {}

    def update_entity_tracking(self, new_entities: Dict[str, str]):
        """Update internal entity tracking with newly extracted entities."""
        if not new_entities:
            self._logger.warning("No entities provided for tracking update")
            return

        now = datetime.datetime.now().isoformat()
        self.last_updated = now

        # Update existing entities and add new ones
        for entity_text, entity_type in new_entities.items():
            if entity_text in self.entities:
                # Update existing entity
                self.entities[entity_text]["mentions"] += 1
                self.entities[entity_text]["last_seen"] = now
            else:
                # Add new entity
                self.entities[entity_text] = {
                    "type": entity_type,
                    "mentions": 1,
                    "first_seen": now,
                    "last_seen": now,
                }

        # Update the global keywords list with our entities
        current_keywords = set(self.get_keywords())
        for entity in self.entities.keys():
            if entity not in current_keywords:
                self.add_keyword(entity)

    def prune_stale_entities(self):
        """Remove entities that haven't been mentioned recently or have few mentions."""
        now = datetime.datetime.now()
        stale_cutoff = (now - datetime.timedelta(days=self.max_age_days)).isoformat()

        # Identify entities to remove
        entities_to_remove = []
        for entity, data in self.entities.items():
            if data["mentions"] < self.min_mentions or data["last_seen"] < stale_cutoff:
                entities_to_remove.append(entity)

        # Remove stale entities
        for entity in entities_to_remove:
            del self.entities[entity]

        self._logger.info(f"Pruned {len(entities_to_remove)} stale keywords")

    def refresh(self) -> List[str]:
        """Refresh the keywords with the latest headlines and return current keywords."""
        # Fetch headlines
        headlines = self.fetch_headlines()

        if headlines:
            # Extract entities
            new_entities = self.extract_entities(headlines)

            # Update tracking
            self.update_entity_tracking(new_entities)

            # Prune stale entities
            self.prune_stale_entities()

            # Add new entities to the keyword list
            for entity in self.entities.keys():
                self.add_keyword(entity)
        else:
            self._logger.warning("No headlines fetched. Using existing keywords.")

        # Return the current list of keywords
        return self.get_keywords()

    def get_entities(self) -> Dict[str, Dict[str, Any]]:
        """Get the current tracked entities."""
        return self.entities


class KeywordMonitorModule(ModuleCore):
    """
    Module that monitors news headlines for political keywords and entities.
    Automatically updates the system's keyword list with found entities.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)

        try:
            module_data = self.get_config()
            self.meta = Meta(
                name=module_data["name"],
                description=module_data["description"],
                version=module_data["version"],
            )
        except FileNotFoundError:
            self.meta = Meta(
                name="Keyword Monitor Module",
                description="Extracts political keywords from news headlines.",
                version="0.1.0",
            )
            self._logger.error("module.yaml file not found. Using default values.")

        self._logger.debug(f"Module meta: {self.meta}")

        # Initialize the keyword monitor
        self.keyword_monitor = KeywordMonitor(logger=logger)

    def run(self, message_bus: MessageBus) -> None:
        self.keyword_monitor.refresh()
        keywords = self.get_keywords()
        message_bus.publish("keywords", keywords)

    def get_keywords(self) -> List[str]:
        """Get the current list of keywords from entities."""
        return list(self.keyword_monitor.entities.keys())

    def refresh_keywords(self) -> List[str]:
        """Refresh keywords from news sources."""
        self._logger.debug("Refreshing keywords from news sources")
        return self.keyword_monitor.refresh()

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name="Keyword Monitor",
            firmware=0xB4C1D,
            protocol="MONITOR",
            errors=[0x0000],
        )

    def invoke(self, command: chr) -> Device:
        """Handle commands from the module engine."""
        self._logger.debug(f"Command: {command} -> {self.meta}")

        # 'R' for refresh keywords
        if command == "R":
            keywords = self.refresh_keywords()
            self._logger.debug(f"Refreshed {len(keywords)} keywords")

        device = self.__create_device()
        return device
