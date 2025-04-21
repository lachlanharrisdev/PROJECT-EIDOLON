"""Aethon web crawler module implementation."""

import asyncio
import time
from typing import Any, Dict, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import httpx
from core.modules.engine import ModuleCore
from core.modules.util.messagebus import MessageBus


class AethonCrawlerModule(ModuleCore):
    """
    A lightweight and fast web crawler module for Project Eidolon.

    This module performs concurrent web crawling using asyncio and httpx,
    with configurable parameters for concurrency, timeouts, and retry logic.
    """

    def __init__(self, logger: logging.Logger, thread_pool: ThreadPoolExecutor) -> None:
        """Initialize the AethonCrawlerModule."""
        super().__init__(logger, thread_pool)
        self.urls = []
        self.results = []
        self.start_time = 0
        self.end_time = 0
        self.success_count = 0
        self.failed_count = 0

    def _process_input(self, data: Any) -> None:
        """Process input data (list of URLs)."""
        if isinstance(data, list) and all(isinstance(url, str) for url in data):
            self.log(f"Received {len(data)} URLs for crawling")
            self.urls = data
        else:
            self.log(
                f"Invalid input data format: expected list[str], got {type(data)}",
                "error",
            )

    async def _run_iteration(self, message_bus: MessageBus) -> None:
        """Run the crawler module."""
        self.message_bus = message_bus

        # Wait for input data
        if not self.urls:
            self.log("No URLs to crawl, waiting for input...", "debug")
            return

        self.log(f"Starting web crawler with {len(self.urls)} URLs")
        self.start_time = time.time()
        self.results = []
        self.success_count = 0
        self.failed_count = 0

        # Get configuration from pipeline arguments
        config = self.get_arguments() or {}
        self.log(f"Using pipeline configuration: {config}", "debug")
        concurrency = config.get("concurrency", 10)

        # Run the crawler
        try:
            crawled_data = await self._crawl_urls(
                self.urls,
                concurrency=concurrency,
                timeout=config.get("timeout", 30),
                user_agent=config.get("user_agent", "Eidolon/1.0 Web Crawler"),
                follow_redirects=config.get("follow_redirects", True),
                max_redirects=config.get("max_redirects", 5),
                retry_count=config.get("retry_count", 3),
                retry_delay=config.get("retry_delay", 1),
                verify_ssl=config.get("verify_ssl", True),
            )

            # Publish results to message bus
            message_bus.publish("crawled_data", crawled_data)

            # Also publish the count of crawled URLs (new output)
            message_bus.publish("crawl_count", len(crawled_data))

            # Clear URLs to prevent re-running
            self.urls = []

            # Generate report
            self._generate_report()

        except Exception as e:
            self.log(f"Error during crawling: {str(e)}", "error")

    async def _crawl_urls(self, urls: List[str], **kwargs) -> List[Dict]:
        """
        Crawl a list of URLs concurrently.

        Args:
            urls: List of URLs to crawl
            **kwargs: Configuration parameters

        Returns:
            List of dictionaries containing crawl results
        """
        concurrency = kwargs.get("concurrency", 10)
        self.log(f"Starting crawl with concurrency: {concurrency}")

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)

        # Create tasks for each URL
        tasks = [self._fetch_url(url, semaphore, **kwargs) for url in urls]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return results
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                self.log(f"Task error: {str(result)}", "error")
                self.failed_count += 1
            else:
                valid_results.append(result)
                if result.get("status_code", 0) < 400:
                    self.success_count += 1
                else:
                    self.failed_count += 1

        self.end_time = time.time()
        self.results = valid_results
        return valid_results

    async def _fetch_url(
        self, url: str, semaphore: asyncio.Semaphore, **kwargs
    ) -> Dict:
        """
        Fetch a single URL with retry logic.

        Args:
            url: URL to fetch
            semaphore: Asyncio semaphore for concurrency control
            **kwargs: Configuration parameters

        Returns:
            Dictionary containing the crawl result
        """
        timeout = kwargs.get("timeout", 30)
        user_agent = kwargs.get("user_agent", "Eidolon/1.0 Web Crawler")
        follow_redirects = kwargs.get("follow_redirects", True)
        max_redirects = kwargs.get("max_redirects", 5)
        retry_count = kwargs.get("retry_count", 3)
        retry_delay = kwargs.get("retry_delay", 1)
        verify_ssl = kwargs.get("verify_ssl", True)

        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        result = {
            "url": url,
            "timestamp": time.time(),
            "success": False,
            "status_code": None,
            "headers": None,
            "content_length": 0,
            "content_type": None,
            "elapsed": 0,
            "error": None,
        }

        # Try to parse the URL to validate it
        try:
            parsed_url = urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                result["error"] = f"Invalid URL format: {url}"
                return result
        except Exception as e:
            result["error"] = f"URL parsing error: {str(e)}"
            return result

        # Use semaphore to limit concurrent requests
        async with semaphore:
            start_time = time.time()
            attempt = 0

            while attempt <= retry_count:
                attempt += 1
                try:
                    async with httpx.AsyncClient(
                        follow_redirects=follow_redirects,
                        max_redirects=max_redirects,
                        timeout=timeout,
                        verify=verify_ssl,
                    ) as client:
                        response = await client.get(url, headers=headers)

                        result.update(
                            {
                                "success": True,
                                "status_code": response.status_code,
                                "headers": dict(response.headers),
                                "content_length": len(response.content),
                                "content_type": response.headers.get("content-type"),
                                "elapsed": time.time() - start_time,
                                "text": (
                                    response.text[:10000]
                                    if response.status_code < 400
                                    else None
                                ),  # Limit content size
                            }
                        )

                        return result

                except httpx.TimeoutException:
                    error_msg = f"Request timed out after {timeout} seconds"

                except httpx.TooManyRedirects:
                    error_msg = f"Too many redirects (max: {max_redirects})"

                except httpx.HTTPError as e:
                    error_msg = f"HTTP error: {str(e)}"

                except Exception as e:
                    error_msg = f"Unexpected error: {str(e)}"

                # If this is not the last attempt, wait before retrying
                if attempt <= retry_count:
                    await asyncio.sleep(retry_delay)
                else:
                    result["error"] = error_msg
                    result["elapsed"] = time.time() - start_time

            return result

    def _generate_report(self) -> None:
        """Generate and print a report of the crawling operation."""
        duration = self.end_time - self.start_time
        total_urls = len(self.urls)
        success_rate = (self.success_count / total_urls) * 100 if total_urls > 0 else 0

        # Calculate average request time
        successful_results = [r for r in self.results if r.get("success", False)]
        avg_time = (
            sum(r.get("elapsed", 0) for r in successful_results)
            / len(successful_results)
            if successful_results
            else 0
        )

        # Get status code distribution
        status_codes = {}
        for result in self.results:
            status = result.get("status_code")
            if status:
                if status in status_codes:
                    status_codes[status] += 1
                else:
                    status_codes[status] = 1

        # Generate report
        report = [
            "=" * 50,
            "AETHON CRAWLER REPORT",
            "=" * 50,
            f"URLs processed: {total_urls}",
            f"Successful: {self.success_count} ({success_rate:.1f}%)",
            f"Failed: {self.failed_count}",
            f"Total time: {duration:.2f} seconds",
            f"Average request time: {avg_time*1000:.2f} ms",
            "",
            "Status Code Distribution:",
        ]

        for status, count in sorted(status_codes.items()):
            report.append(f"  {status}: {count} ({count/total_urls*100:.1f}%)")

        report.append("=" * 50)

        # Log the report
        for line in report:
            self.log(line)

    def _handle_custom_command(self, command: str) -> Dict:
        """Handle custom commands for the crawler module."""
        if command == "report":
            self._generate_report()
            return {"status": "success", "message": "Report generated"}
        elif command == "clear":
            self.urls = []
            self.results = []
            return {"status": "success", "message": "Cleared crawl data"}
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}
