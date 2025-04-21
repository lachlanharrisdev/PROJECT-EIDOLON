import os
import json
import csv
import xml.etree.ElementTree as ET
import random
from typing import List, Union, Optional, Any
from logging import Logger

from core.modules.engine.engine_contract import ModuleCore
from core.modules.util.messagebus import MessageBus


class URLListModule(ModuleCore):
    """
    Module for loading URLs from files or generating example URLs.

    This module can load URLs from various file formats (.txt, .csv, .json, .xml)
    or generate a sample list of URLs for testing purposes.
    """

    def init(self) -> None:
        """Initialize URL list module with configuration from pipeline args."""
        # Get configuration from pipeline arguments
        config = self.get_arguments() or {}

        # Setup configuration values from pipeline config
        self.supported_formats = config.get(
            "supported_formats", [".txt", ".csv", ".json", ".xml"]
        )
        self.example_mode = config.get("example_mode", False)
        self.example_count = config.get("example_count", 10)
        self.skip_empty_lines = config.get("skip_empty_lines", True)
        self.strip_whitespace = config.get("strip_whitespace", True)
        self.remove_duplicates = config.get("remove_duplicates", True)

        # Handle file_path if provided directly in the pipeline config
        self.file_paths = config.get("file_path", None)
        if self.file_paths:
            self.log(f"File path provided in configuration: {self.file_paths}")

        # Initialize data structures
        self.urls = []

    def process(self, data: Any) -> None:
        """
        Process input data received from message bus.

        Args:
            data: The input data, expected to be a file path or list of file paths
        """
        if isinstance(data, dict) and "file_paths" in data:
            self.file_paths = data["file_paths"]
            self.log(
                f"Received {len(self.file_paths) if isinstance(self.file_paths, list) else 1} file path(s)"
            )
        elif isinstance(data, (str, list)):
            self.file_paths = data
            self.log(f"Received raw file path(s) input")
        else:
            self.log(
                f"Received unexpected data type: {type(data)}", log_level="warning"
            )

    async def execute(self, message_bus: MessageBus) -> None:
        """
        Run the main module logic to load URLs and publish them.

        Args:
            message_bus: The message bus for inter-module communication
        """
        try:
            # Get configuration from pipeline arguments
            # This ensures we have the latest configuration when the module runs
            args = self.get_arguments()
            self.log(f"Running with configuration: {args}", log_level="debug")

            # Setup module configuration with fallbacks to module.yaml defaults
            self.supported_formats = args.get(
                "supported_formats", [".txt", ".csv", ".json", ".xml"]
            )
            self.example_mode = args.get("example_mode", False)
            self.example_count = args.get("example_count", 50)
            self.skip_empty_lines = args.get("skip_empty_lines", True)
            self.strip_whitespace = args.get("strip_whitespace", True)
            self.remove_duplicates = args.get("remove_duplicates", True)

            # Make sure we respect the file_path parameter
            if not hasattr(self, "file_paths") or self.file_paths is None:
                self.file_paths = args.get("file_path", None)
                if self.file_paths:
                    self.log(f"File path found in arguments: {self.file_paths}")

            # Check if we're in example mode
            if self.example_mode:
                self.log(
                    f"Running in example mode, generating {self.example_count} sample URLs"
                )
                urls = self._generate_example_urls()
            else:
                # Process file paths if available
                if self.file_paths:
                    self.log(f"Loading URLs from provided file paths")
                    urls = self._load_urls_from_files(self.file_paths)
                else:
                    self.log(
                        "No file paths provided and not in example mode",
                        log_level="warning",
                    )
                    urls = []

            # Apply processing options
            if self.strip_whitespace:
                urls = [url.strip() for url in urls]

            if self.skip_empty_lines:
                urls = [url for url in urls if url]

            if self.remove_duplicates:
                urls = list(
                    dict.fromkeys(urls)
                )  # Preserves order while removing duplicates

            # Update the module's URL list
            self.urls = urls
            self.log(f"Processed {len(urls)} URLs")

            # Publish the URLs to the message bus
            if urls:
                await message_bus.publish("urls", urls)
                self.log(f"Published {len(urls)} URLs to the message bus")
            else:
                self.log("No URLs to publish", log_level="warning")

        except Exception as e:
            self.log(f"Error processing URLs: {e}", log_level="error")

    def _load_urls_from_files(self, file_paths: Union[str, List[str]]) -> List[str]:
        """
        Load URLs from one or more files.

        Args:
            file_paths: A single file path or a list of file paths

        Returns:
            A list of URLs loaded from the files
        """
        urls = []

        # Convert single path to list for consistent processing
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        for file_path in file_paths:
            try:
                if not os.path.exists(file_path):
                    self.log(f"File not found: {file_path}", log_level="error")
                    continue

                file_extension = os.path.splitext(file_path)[1].lower()

                if file_extension not in self.supported_formats:
                    self.log(
                        f"Unsupported file format: {file_extension}",
                        log_level="warning",
                    )
                    continue

                # Load URLs based on file format
                file_urls = []
                if file_extension == ".txt":
                    file_urls = self._load_from_txt(file_path)
                elif file_extension == ".csv":
                    file_urls = self._load_from_csv(file_path)
                elif file_extension == ".json":
                    file_urls = self._load_from_json(file_path)
                elif file_extension == ".xml":
                    file_urls = self._load_from_xml(file_path)

                self.log(f"Loaded {len(file_urls)} URLs from {file_path}")
                urls.extend(file_urls)

            except Exception as e:
                self.log(f"Error loading URLs from {file_path}: {e}", log_level="error")

        return urls

    def _load_from_txt(self, file_path: str) -> List[str]:
        """Load URLs from a text file (one URL per line)."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().splitlines()

    def _load_from_csv(self, file_path: str) -> List[str]:
        """
        Load URLs from a CSV file.

        Assumes the first column contains URLs or tries to find a column with 'url' in the header.
        """
        urls = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)

            # Try to find a column with "url" in the header
            url_col_index = 0
            if headers:
                for i, header in enumerate(headers):
                    if "url" in header.lower():
                        url_col_index = i
                        break

            # Read URLs from the identified column
            for row in reader:
                if row and len(row) > url_col_index:
                    urls.append(row[url_col_index])

        return urls

    def _load_from_json(self, file_path: str) -> List[str]:
        """
        Load URLs from a JSON file.

        Handles various JSON structures:
        - List of URL strings
        - List of objects with a 'url' property
        - Object with a 'urls' property that contains a list
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        urls = []
        if isinstance(data, list):
            # Handle list of strings or objects
            for item in data:
                if isinstance(item, str):
                    urls.append(item)
                elif isinstance(item, dict) and "url" in item:
                    urls.append(item["url"])
        elif isinstance(data, dict):
            # Check for common JSON structures
            if "urls" in data and isinstance(data["urls"], list):
                for item in data["urls"]:
                    if isinstance(item, str):
                        urls.append(item)
                    elif isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
            elif "url" in data:
                urls.append(data["url"])

        return urls

    def _load_from_xml(self, file_path: str) -> List[str]:
        """
        Load URLs from an XML file.

        Looks for elements with tag 'url' or elements with an attribute 'url'.
        """
        urls = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Look for elements with tag 'url'
            for url_elem in root.findall(".//url"):
                if url_elem.text:
                    urls.append(url_elem.text)

            # Look for elements with href or src attributes
            for elem in root.findall(".//*[@href]"):
                urls.append(elem.get("href"))

            for elem in root.findall(".//*[@src]"):
                urls.append(elem.get("src"))

            # If we still don't have URLs, try to find any element with text that looks like a URL
            if not urls:
                for elem in root.findall(".//*"):
                    if elem.text and (
                        "http://" in elem.text or "https://" in elem.text
                    ):
                        urls.append(elem.text)

        except ET.ParseError as e:
            self.log(f"Error parsing XML file {file_path}: {e}", log_level="error")

        return urls

    def _generate_example_urls(self) -> List[str]:
        """
        Generate example URLs for testing purposes.

        Returns:
            A list of example URLs
        """
        # Base domains for example URLs
        domains = [
            "example.com",
            "test-site.org",
            "sample-domain.net",
            "demo.io",
            "testing.dev",
            "sandbox.app",
            "mockup.co",
            "staging-env.tech",
        ]

        # URL paths and parameters
        paths = [
            "",
            "index.html",
            "about",
            "products",
            "services",
            "contact",
            "blog",
            "articles",
            "news",
            "gallery",
            "faq",
            "support",
            "category/electronics",
            "tag/popular",
            "user/profile",
            "search",
        ]

        params = [
            "",
            "?id=123",
            "?page=1",
            "?category=tech",
            "?q=search+term",
            "?lang=en",
            "?sort=newest",
            "?filter=popular",
            "?view=grid",
            "?session=abc123",
            "?ref=homepage",
            "?utm_source=newsletter",
        ]

        # File extensions for content types
        content_types = [
            "",
            ".html",
            ".php",
            ".aspx",
            ".jsp",
            ".pdf",
            ".jpg",
            ".png",
            ".gif",
            ".css",
            ".js",
        ]

        # Generate random URLs
        urls = []
        for _ in range(self.example_count):
            protocol = random.choice(["http://", "https://"])
            domain = random.choice(domains)

            # Some domains should have www, some shouldn't
            if random.random() > 0.7:
                domain = "www." + domain

            path = random.choice(paths)

            # Add file extension to some paths
            if path and random.random() > 0.7:
                path += random.choice(content_types)

            # Add parameters to some URLs
            param = random.choice(params)

            url = f"{protocol}{domain}/{path}{param}"
            urls.append(url)

        return urls
