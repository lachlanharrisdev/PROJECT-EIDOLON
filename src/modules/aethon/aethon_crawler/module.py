from logging import Logger  # Keep this for type hinting if needed elsewhere
from typing import List, Dict, Any, Set, Optional
import asyncio
import time

from core.modules.engine import ModuleCore
from core.modules.models import CourierEnvelope
from core.modules.util.messagebus import MessageBus

# Import the crawl function from our src directory
from .src.main import crawl


class AethonCrawler(ModuleCore):
    """
    Web crawler module using Aethon crawler logic.
    """

    def init(self) -> None:
        """
        Initialize module-specific components and configuration.
        """
        self.results_list: List[Dict[str, Any]] = []

    def process(self, envelope: CourierEnvelope) -> None:
        """
        Process incoming list of URLs to crawl.
        """
        data = envelope.data

        config = self.get_arguments() or {}
        self.log("Initializing Aethon Crawler module", "INFO")

        # Store configuration, using defaults from crawl function signature or reasonable values
        self.start_urls: List[str] = []  # Will be populated by process()
        self.max_depth = config.get("max_depth", 2)
        self.max_urls = config.get("max_urls", 100)
        self.max_concurrency_global = config.get("max_concurrency_global", 10)
        self.max_concurrency_per_domain = config.get("max_concurrency_per_domain", 2)
        self.crawl_delay = config.get("crawl_delay", 0.25)
        self.max_page_size = config.get("max_page_size", 1024 * 1024)  # 1MB default
        self.user_agent = config.get("user_agent", "AethonCrawlerModule/0.1")
        self.stay_on_domain = config.get("stay_on_domain", False)

        # Log effective configuration
        self.log(
            f"Effective config: max_depth={self.max_depth}, max_urls={self.max_urls}, "
            f"concurrency_global={self.max_concurrency_global}, concurrency_domain={self.max_concurrency_per_domain}, "
            f"delay={self.crawl_delay}, max_page_size={self.max_page_size}, "
            f"stay_on_domain={self.stay_on_domain}, user_agent='{self.user_agent}'",
            "INFO",
        )

        if isinstance(data, list) and all(isinstance(item, str) for item in data):
            self.start_urls = data
            self.log(f"Received {len(self.start_urls)} URLs to crawl.", "INFO")
        else:
            self.log(
                f"Received invalid data format for URLs. Expected List[str], got {type(data)}.",
                "WARNING",
            )
            self.start_urls = []  # Clear previous URLs if input is invalid

    async def _process_crawled_page(self, data: Dict[str, Any]):
        """
        Callback function passed to the crawler. Formats and stores data.
        """
        # Prepare data structure according to requirements
        output_data = {
            "url": data.get("url"),
            "timestamp": data.get(
                "timestamp", time.time()
            ),  # Use crawl time if available
            "success": data.get("success", False),
            "status_code": data.get("status_code"),
            "headers": data.get("headers", {}),
            "content_length": data.get("content_length"),
            "content_type": data.get("content_type"),
            "elapsed": data.get("elapsed"),
            "text": data.get("text"),  # Already limited by max_page_size in worker
            "error": data.get("error"),  # Include error message if present
            "depth": data.get("depth"),  # Include depth
        }

        # Append the structured data to the instance list
        self.results_list.append(output_data)
        self.log(
            f"Stored crawled data for: {output_data['url']} (Success: {output_data['success']})",
            "DEBUG",
        )

    async def execute(self, message_bus: MessageBus) -> None:
        """
        Run the crawler with stored configuration and URLs, then publish all results.
        """
        self._message_bus = message_bus  # Store message bus

        if not self.start_urls:
            self.log("No start URLs provided or processed. Skipping execution.", "INFO")
            self._message_bus = None
            return

        # Clear results list before starting a new crawl
        self.results_list = []

        self.log(f"Starting crawl for {len(self.start_urls)} initial URLs...", "INFO")
        crawl_start_time = time.time()

        try:
            processed_count = await crawl(
                start_urls=self.start_urls,
                max_depth=self.max_depth,
                max_urls=self.max_urls,
                max_concurrency_global=self.max_concurrency_global,
                max_concurrency_per_domain=self.max_concurrency_per_domain,
                crawl_delay=self.crawl_delay,
                max_page_size=self.max_page_size,
                user_agent=self.user_agent,
                process_data_callback=self._process_crawled_page,  # Pass the instance method
                stay_on_domain=self.stay_on_domain,
                log_func=self.log,  # Pass the module's self.log method directly
            )
            crawl_duration = time.time() - crawl_start_time
            self.log(
                f"Crawl execution finished in {crawl_duration:.2f} seconds. Processed {processed_count} pages.",
                "INFO",
            )

            # Publish the entire list of results
            if self.results_list:
                self.log(
                    f"Publishing {len(self.results_list)} crawled data results...",
                    "INFO",
                )
                try:
                    await self._message_bus.publish("crawled_data", self.results_list)
                except Exception as e:
                    self.log(f"Failed to publish bulk crawled data: {e}", "ERROR")
            else:
                self.log("No results were collected during the crawl.", "INFO")

            # Publish summary data (optional)
            summary_data = {
                "start_urls_count": len(self.start_urls),
                "processed_count": processed_count,
                "results_published_count": len(self.results_list),
                "duration_seconds": crawl_duration,
                "timestamp": time.time(),
            }
            await self._message_bus.publish("crawl_summary", summary_data)

        except Exception as e:
            self.log(
                f"An error occurred during crawler execution: {e}",
                "CRITICAL",
            )
            # Optionally publish partial results if needed on error
            # if self.results_list:
            #    self.log(f"Publishing {len(self.results_list)} partial results due to error...", "WARNING")
            #    await self._message_bus.publish("crawled_data", self.results_list)
            error_data = {
                "error": f"Crawler execution failed: {e}",
                "timestamp": time.time(),
            }
            await self._message_bus.publish("crawl_error", error_data)
        finally:
            self._message_bus = None  # Clear message bus reference after execution
