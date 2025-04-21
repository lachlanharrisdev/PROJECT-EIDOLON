"""
Aethon Web Crawler - A modern, high-performance web crawler

Inspired by Photon (https://github.com/s0md3v/Photon) but rewritten
with improved architecture, performance optimizations, and
seamless integration with the Eidolon ecosystem.
"""

from logging import Logger
from typing import List, Dict, Any, Set, Optional, Tuple, Union
import asyncio
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    import aiohttp
    from tld import get_fld
except ImportError as e:
    raise ImportError(f"Required package not available: {e}")

from core.modules.engine import ModuleCore
from core.modules.models import Device
from core.modules.util.messagebus import MessageBus

from .constants import SOCIAL_REGEX, SECRET_REGEX, FILE_EXTENSIONS
from .url_processor import normalize_url, is_valid_url, is_excluded, extract_urls
from .data_extraction import extract_data
from .http_client import fetch_url, fetch_wayback_urls, build_headers
from .utils import prepare_results_for_publishing, build_status_data


class AethonCrawler(ModuleCore):
    """
    Aethon web crawler module for Eidolon.

    A modern, high-performance web crawler with rich data extraction capabilities.
    """

    def _initialize_module(self) -> None:
        """
        Initialize module-specific state and components.
        Called after the base ModuleCore initialization.
        """
        # Core configuration with defaults
        self.config = {
            "url": None,  # Root URL to start crawling
            "level": 2,  # Crawling depth
            "threads": 10,  # Number of worker threads
            "delay": 0,  # Delay between requests (seconds)
            "cookie": None,  # Cookie string
            "regex": None,  # Custom regex pattern for extraction
            "timeout": 10,  # HTTP request timeout (seconds)
            "exclude": None,  # Regex pattern for URLs to exclude
            "seeds": [],  # Additional seed URLs
            "headers": {},  # Custom HTTP headers
            "user_agent": None,  # User-Agent string (or random)
            "only_urls": False,  # Only extract URLs
            "wayback": False,  # Use archive.org for seeds
            "dns": False,  # Enumerate subdomains
            "keys": False,  # Extract secret keys
            "ninja": False,  # Use stealth request techniques
            "clone": False,  # Clone the website locally
        }

        # Internal state
        self.base_url = ""
        self.domain = ""
        self.session = None
        self.running = False
        self.current_level = 0
        self.progress = {"total": 0, "processed": 0, "found": 0}

        # Data storage
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.url_queue: List[Tuple[str, int]] = []  # (url, depth)

        # Extracted data collections
        self.extracted = {
            "emails": set(),
            "social": {},
            "aws_buckets": set(),
            "secret_keys": {},
            "files": {},
            "subdomains": set(),
            "js_files": set(),
            "js_endpoints": set(),
            "parameters": {},  # URLs with parameters (e.g., ?id=1)
            "custom_regex": set(),
        }

        for social in SOCIAL_REGEX:
            self.extracted["social"][social] = set()

        for secret_type in SECRET_REGEX:
            self.extracted["secret_keys"][secret_type] = set()

        for file_type in FILE_EXTENSIONS:
            self.extracted["files"][file_type] = set()

        # Async resources
        self.semaphore = None  # Will be initialized in _before_run
        self.aiohttp_session = None  # Will be initialized in _before_run

        # Wayback machine integration
        self.wayback_urls: Set[str] = set()

        # Message frequency control
        self.last_status_time = 0
        self.status_update_interval = (
            1  # Reduced from 3 to 1 second for more frequent updates
        )

    def _process_input(self, data: Any) -> None:
        """
        Process input data from the message bus.
        """
        if isinstance(data, dict) and self._is_crawl_config(data):
            self._logger.info(f"Received crawl configuration")
            self._update_config(data)

        elif isinstance(data, list) and all(isinstance(url, str) for url in data):
            self._logger.info(f"Received {len(data)} additional seed URLs")
            self.config["seeds"].extend(data)

            # If we're already running, add these to the queue
            if self.running:
                for url in data:
                    if is_valid_url(url) and url not in self.visited_urls:
                        self.url_queue.append((url, self.current_level))
                        self.discovered_urls.add(url)
        else:
            self._logger.warning(f"Received unrecognized data type: {type(data)}")

    def _is_crawl_config(self, data: Dict) -> bool:
        """
        Check if the provided dictionary is a valid crawler configuration.
        """
        # At minimum, it should contain a URL to crawl
        if "url" in data and isinstance(data["url"], str):
            return True

        # Check for expected configuration keys
        expected_keys = ["level", "threads", "delay", "timeout", "exclude"]
        return any(key in data for key in expected_keys)

    def _update_config(self, config_data: Dict) -> None:
        """
        Update the crawler configuration with the provided data.
        """
        # Update config with provided values
        for key, value in config_data.items():
            if key in self.config:
                self.config[key] = value

        # Normalize URLs to ensure consistency
        if self.config["url"] and not self.config["url"].startswith(
            ("http://", "https://")
        ):
            self.config["url"] = f"https://{self.config['url']}"

        # Extract base domain for scope checking
        if self.config["url"]:
            parsed = urlparse(self.config["url"])
            self.base_url = f"{parsed.scheme}://{parsed.netloc}"
            try:
                self.domain = get_fld(self.config["url"], fix_protocol=True)
            except Exception:
                # Fallback if tld extraction fails
                self.domain = parsed.netloc

        # Process and normalize seeds
        normalized_seeds = []
        for seed in self.config["seeds"]:
            if not seed.startswith(("http://", "https://")):
                seed = f"https://{seed}"
            normalized_seeds.append(seed)
        self.config["seeds"] = normalized_seeds

    async def _before_run(self, message_bus: MessageBus) -> None:
        """
        Setup code that runs once before the main module loop.
        """
        # Record the start time for duration tracking
        self.start_time = datetime.now()

        # Get configuration from pipeline if available
        if hasattr(self, "args") and self.args and isinstance(self.args, dict):
            self._logger.info("Loading configuration from pipeline")
            self._update_config(self.args)

            # Debug logging to verify URL is loaded correctly
            if self.config["url"]:
                self._logger.info(f"Target URL set to: {self.config['url']}")
            else:
                self._logger.warning("No target URL specified in configuration")

        # Initialize semaphore to control concurrency
        self.semaphore = asyncio.Semaphore(self.config["threads"])

        # Create aiohttp session for async requests
        if not self.aiohttp_session:
            self.aiohttp_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config["timeout"]),
                headers=build_headers(self.config),
            )

        # Initialize regular requests session for sync operations
        self.session = requests.Session()
        self.session.headers.update(build_headers(self.config))

        # Reset data structures for a fresh start
        self.visited_urls.clear()
        self.discovered_urls.clear()
        self.url_queue.clear()

        for collection in self.extracted.values():
            if isinstance(collection, dict):
                for key in collection:
                    collection[key].clear()
            else:
                collection.clear()

        # Add the root URL to the queue if provided
        if self.config["url"]:
            self.url_queue.append((self.config["url"], 0))  # Start at depth 0
            self.discovered_urls.add(self.config["url"])
            self._logger.info(f"Added root URL to crawl queue: {self.config['url']}")

        # Add seed URLs to the queue
        for seed in self.config["seeds"]:
            if seed not in self.discovered_urls:
                self.url_queue.append((seed, 0))
                self.discovered_urls.add(seed)

        # Fetch wayback URLs if requested
        if self.config["wayback"] and self.config["url"]:
            await fetch_wayback_urls(
                self.domain,
                self.aiohttp_session,
                self.discovered_urls,
                self.url_queue,
                self.wayback_urls,
            )

        # Reset progress tracking
        self.progress = {
            "total": len(self.url_queue),
            "processed": 0,
            "found": len(self.discovered_urls),
        }

        # Set initial level
        self.current_level = 0

        # Set module as running
        self.running = True

        self.log(f"Starting crawl with {len(self.url_queue)} seed URLs")

    async def _run_iteration(self, message_bus: MessageBus) -> None:
        """
        Execute one iteration of the crawler, processing batches of URLs.
        """
        if not self.running:
            return

        if not self.url_queue:
            if self.current_level < self.config["level"]:
                # Move to next level if there are no more URLs at current level
                # but we found new URLs to process in next level
                self.current_level += 1
                self.log(f"Moving to crawl level {self.current_level}")

                # If we're done with all levels or no new URLs, we're finished
                if (
                    self.current_level >= self.config["level"]
                    or not self.discovered_urls
                ):
                    await self._finalize_crawl(message_bus)
                    return
            else:
                # We've hit our maximum depth, finalize the crawl
                await self._finalize_crawl(message_bus)
                return

        # Process URLs in batches based on thread count
        batch_size = min(len(self.url_queue), self.config["threads"] * 2)
        if batch_size == 0:
            return

        batch = []
        for _ in range(batch_size):
            if not self.url_queue:
                break
            url, depth = self.url_queue.pop(0)
            if depth <= self.current_level and url not in self.visited_urls:
                batch.append((url, depth))

        if not batch:
            return

        # Process the batch of URLs concurrently
        tasks = []
        for url, depth in batch:
            # Add a small delay between creating tasks if configured
            if self.config["delay"] > 0:
                await asyncio.sleep(self.config["delay"])

            tasks.append(self._process_url(url, depth))

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        # Update progress
        self.progress["processed"] += len(batch)
        self.progress["found"] = len(self.discovered_urls)
        self.progress["total"] = len(self.url_queue) + self.progress["processed"]

        # Publish status updates periodically
        current_time = time.time()
        if current_time - self.last_status_time > self.status_update_interval:
            self.last_status_time = current_time
            await self._publish_status(message_bus)

    async def _process_url(self, url: str, depth: int) -> None:
        """
        Process a single URL: fetch it, extract data, and find new links.
        """
        # Skip if we've already visited or it's excluded
        if url in self.visited_urls or is_excluded(url, self.config["exclude"]):
            return

        # Mark as visited to prevent revisiting
        self.visited_urls.add(url)

        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            try:
                response_text = await fetch_url(
                    url, self.aiohttp_session, self.config, self.extracted["files"]
                )
                if not response_text:
                    return

                # Extract all data types unless only_urls is specified
                if not self.config["only_urls"]:
                    extract_data(
                        url, response_text, self.extracted, self.config, self.domain
                    )

                # Only look for new URLs if we're not at max depth
                if depth < self.config["level"]:
                    new_urls = extract_urls(
                        url,
                        response_text,
                        self.extracted["parameters"],
                        self.extracted["js_files"],
                        self.extracted["js_endpoints"],
                    )

                    # Add new URLs to the queue for next level
                    for new_url in new_urls:
                        if (
                            new_url not in self.discovered_urls
                            and new_url not in self.visited_urls
                        ):
                            self.url_queue.append((new_url, depth + 1))
                            self.discovered_urls.add(new_url)

            except Exception as e:
                self.log(f"Error processing URL {url}: {str(e)}", "error")

    async def _finalize_crawl(self, message_bus: MessageBus) -> None:
        """
        Complete the crawl and print a summary to console
        """
        crawl_duration = (
            datetime.now() - self.start_time if hasattr(self, "start_time") else None
        )
        duration_str = (
            str(crawl_duration).split(".")[0] if crawl_duration else "Unknown"
        )

        # Print summary to console
        self.log("-" * 80)
        self.log(f"AETHON CRAWLER SUMMARY")
        self.log(f"Target URL: {self.config['url']}")
        self.log(f"Crawl duration: {duration_str}")
        self.log(f"Depth reached: Level {self.current_level}/{self.config['level']}")
        self.log(f"URLs discovered: {len(self.discovered_urls)}")
        self.log(f"URLs processed: {len(self.visited_urls)}")

        # Print data extraction summary
        self.log(f"Data extracted:")
        self.log(f"  - Emails: {len(self.extracted['emails'])}")
        self.log(
            f"  - Social accounts: {sum(len(accounts) for accounts in self.extracted['social'].values())}"
        )
        self.log(f"  - JavaScript files: {len(self.extracted['js_files'])}")
        self.log(f"  - Endpoints: {len(self.extracted['js_endpoints'])}")
        self.log(
            f"  - Parameters: {sum(len(urls) for urls in self.extracted['parameters'].values())}"
        )
        self.log(f"  - Subdomains: {len(self.extracted['subdomains'])}")
        self.log("-" * 80)

        # Convert sets to lists for serialization
        result_data = prepare_results_for_publishing(self.extracted)

        # Publish minimal data to the message bus for other modules
        await message_bus.publish("crawled_urls", list(self.visited_urls))
        await message_bus.publish("extracted_data", result_data)

        # Final status update
        final_status = {
            "timestamp": datetime.now().isoformat(),
            "target_url": self.config["url"],
            "duration": duration_str,
            "urls_discovered": len(self.discovered_urls),
            "urls_processed": len(self.visited_urls),
            "complete": True,
        }
        await message_bus.publish("crawl_status", final_status)

        # Mark crawl as complete
        self.running = False

    async def _publish_status(
        self, message_bus: MessageBus, is_final: bool = False
    ) -> None:
        """
        Publish the current status of the crawler to the message bus.
        """
        status = build_status_data(
            self.running,
            is_final,
            self.current_level,
            self.config["level"],
            self.discovered_urls,
            self.visited_urls,
            self.url_queue,
            self.progress,
            self.extracted,
        )

        await message_bus.publish("crawl_status", status)

    async def _after_run(self, message_bus: MessageBus) -> None:
        """
        Clean up resources after the crawl is complete.
        """
        if self.aiohttp_session and not self.aiohttp_session.closed:
            await self.aiohttp_session.close()

        self.running = False

    async def _custom_shutdown(self):
        """
        Custom cleanup during shutdown.
        """
        if self.aiohttp_session and not self.aiohttp_session.closed:
            await self.aiohttp_session.close()

    def _handle_custom_command(self, command: chr) -> Device:
        """
        Handle custom module commands.
        """
        if command == "C":  # Clear crawl data
            self._clear_crawl_data()
            return Device(
                name=self.meta.name, firmware=0x10000, protocol="CLEARED", errors=[]
            )
        elif command == "T":  # Terminate active crawl
            self.running = False
            return Device(
                name=self.meta.name, firmware=0x10000, protocol="TERMINATED", errors=[]
            )

        return super()._handle_custom_command(command)

    def _clear_crawl_data(self) -> None:
        """
        Clear all crawl data and reset the crawler.
        """
        self.visited_urls.clear()
        self.discovered_urls.clear()
        self.url_queue.clear()
        self.wayback_urls.clear()

        for collection in self.extracted.values():
            if isinstance(collection, dict):
                for key in collection:
                    collection[key].clear()
            else:
                collection.clear()

        self.progress = {"total": 0, "processed": 0, "found": 0}
        self.running = False

        self.log("Crawl data cleared")

    def _get_cycle_time(self) -> float:
        """
        Get the time between execution cycles.
        """
        if self.running and self.url_queue:
            # Run more frequently when actively crawling
            return 0.5
        return 5.0  # Default cycle time when idle
