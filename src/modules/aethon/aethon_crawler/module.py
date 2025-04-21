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

    def init(self) -> None:
        """Initialize module-specific state."""
        self.urls = []
        self.results = []
        self.start_time = 0
        self.end_time = 0
        self.success_count = 0
        self.failed_count = 0
        # Safety measure - store the original URLs separately for report generation
        self.original_url_count = 0

    def process(self, data: Any) -> None:
        """
        Process input data (list of URLs).

        Args:
            data: Expected to be a list of URL strings
        """
        if isinstance(data, list) and all(isinstance(url, str) for url in data):
            self.log(f"Received {len(data)} URLs for crawling")
            self.urls = data
            self.original_url_count = len(data)
        else:
            self.log(
                f"Invalid input data format: expected list[str], got {type(data)}",
                "error",
            )

    async def execute(self, message_bus: MessageBus) -> None:
        """
        Run the crawler module logic.

        Args:
            message_bus: The message bus for publishing results
        """
        # Wait for input data
        if not self.urls:
            self.log("No URLs to crawl, skipping execution", "warning")
            return

        self.log(f"Starting web crawler with {len(self.urls)} URLs")
        self.start_time = time.time()
        self.results = []
        self.success_count = 0
        self.failed_count = 0

        # Get configuration from pipeline arguments
        config = self.get_arguments() or {}
        concurrency = min(config.get("concurrency", 10), max(1, len(self.urls)))

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

            # Make sure we have the end time set even if an error occurs
            self.end_time = time.time()

            # Record all URLs processed, including errors
            self.results = crawled_data

            # Publish results to message bus
            await message_bus.publish("crawled_data", crawled_data)

            # Also publish the count of crawled URLs
            await message_bus.publish("crawl_count", len(crawled_data))

            # Store a copy of the URLs to prevent re-running
            processed_urls = list(self.urls)

            # Clear URLs to prevent re-running
            self.urls = []

            # Generate report
            self._generate_report(processed_urls)

        except Exception as e:
            self.log(f"Error during crawling: {str(e)}", "error")
            # Ensure end_time is set for proper reporting even on failure
            if self.start_time > 0 and self.end_time == 0:
                self.end_time = time.time()

            # Try to generate a partial report if possible
            try:
                self._generate_report(self.urls)
            except Exception as report_error:
                self.log(f"Error generating report: {str(report_error)}", "error")

    async def _crawl_urls(self, urls: List[str], **kwargs) -> List[Dict]:
        """
        Crawl multiple URLs concurrently.

        Args:
            urls: List of URLs to crawl
            **kwargs: Crawler configuration options

        Returns:
            List of crawl result dictionaries
        """
        if not urls:
            return []

        concurrency = min(kwargs.get("concurrency", 10), max(1, len(urls)))
        self.log(f"Using concurrency level: {concurrency}")

        # Create a semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(concurrency)

        # Start all fetch tasks
        tasks = []
        for url in urls:
            task = asyncio.create_task(self._fetch_url(url, semaphore, **kwargs))
            tasks.append(task)

        # Wait for all tasks to complete
        all_results = await asyncio.gather(*tasks, return_exceptions=False)

        # Process results
        processed_results = []
        for result in all_results:
            if not isinstance(result, dict):
                # This shouldn't happen with return_exceptions=False, but just in case
                self.log(f"Unexpected result type: {type(result)}", "error")
                continue

            processed_results.append(result)
            if result.get("error"):
                self.log(
                    f"Error fetching {result['url']}: {result['error']}", "warning"
                )
                self.failed_count += 1
            else:
                if result.get("status_code", 0) < 400:
                    self.success_count += 1
                else:
                    self.failed_count += 1

        self.end_time = time.time()
        return processed_results

    async def _fetch_url(
        self, url: str, semaphore: asyncio.Semaphore, **kwargs
    ) -> Dict:
        """
        Fetch a single URL with retry logic.

        Args:
            url: The URL to fetch
            semaphore: Asyncio semaphore for concurrency control
            **kwargs: Request configuration options

        Returns:
            Dictionary with request results
        """
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

        # Extract configuration from kwargs
        timeout = kwargs.get("timeout", 30)
        follow_redirects = kwargs.get("follow_redirects", True)
        max_redirects = kwargs.get("max_redirects", 5)
        user_agent = kwargs.get("user_agent", "Eidolon/1.0 Web Crawler")
        retry_count = kwargs.get("retry_count", 3)
        retry_delay = kwargs.get("retry_delay", 1)
        verify_ssl = kwargs.get("verify_ssl", True)

        # Set up headers
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        # Try to parse the URL to validate it
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                result["error"] = f"Invalid URL format: {url}"
                return result
        except Exception as e:
            result["error"] = f"URL parsing error: {str(e)}"
            return result

        # Track the start time for accurate elapsed time calculation
        start_time = time.time()

        # Use semaphore to limit concurrent requests
        try:
            async with semaphore:
                attempt = 0

                while attempt <= retry_count:
                    attempt += 1
                    try:
                        timeout_obj = httpx.Timeout(timeout, connect=timeout / 2)
                        async with httpx.AsyncClient(
                            follow_redirects=follow_redirects,
                            max_redirects=max_redirects,
                            timeout=timeout_obj,
                            verify=verify_ssl,
                        ) as client:
                            response = await client.get(url, headers=headers)

                            result.update(
                                {
                                    "success": True,
                                    "status_code": response.status_code,
                                    "headers": dict(response.headers),
                                    "content_length": len(response.content),
                                    "content_type": response.headers.get(
                                        "content-type"
                                    ),
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
        except Exception as e:
            # Catch any unexpected exceptions from the semaphore block
            result["error"] = f"Request failed: {str(e)}"
            result["elapsed"] = time.time() - start_time

        return result

    def _generate_report(self, processed_urls: List[str] = None) -> None:
        """
        Generate and print a report of the crawling operation.

        Args:
            processed_urls: Optional list of processed URLs for better accuracy in reporting
        """
        try:
            duration = max(0.001, self.end_time - self.start_time)

            # Use the most accurate count of URLs we have
            total_urls = (
                len(processed_urls)
                if processed_urls
                else (
                    self.original_url_count
                    if self.original_url_count > 0
                    else max(self.success_count + self.failed_count, 1)
                )
            )

            # Calculate success rate safely
            success_rate = (
                (self.success_count / total_urls) * 100 if total_urls > 0 else 0
            )

            # Calculate average request time safely
            successful_results = [r for r in self.results if r.get("success", False)]
            if successful_results:
                avg_time = sum(r.get("elapsed", 0) for r in successful_results) / len(
                    successful_results
                )
            else:
                avg_time = 0

            # Get status code distribution safely
            status_codes = {}
            for result in self.results:
                status = result.get("status_code")
                if status:
                    status_codes[status] = status_codes.get(status, 0) + 1

            # Generate report
            report = [
                "=" * 50,
                "AETHON CRAWLER REPORT",
                "=" * 50,
                f"URLs processed: {total_urls}",
                f"Successful requests: {self.success_count} ({success_rate:.1f}%)",
                f"Failed requests: {self.failed_count}",
                f"Total crawl time: {duration:.2f} seconds",
                f"Average request time: {avg_time*1000:.2f} ms",
                f"Requests per second: {total_urls / duration:.1f}",
                "",
                "Status Code Distribution:",
            ]

            # Add status code distribution if we have results
            if status_codes:
                for status, count in sorted(status_codes.items()):
                    percentage = (count / total_urls) * 100 if total_urls > 0 else 0
                    report.append(f"  {status}: {count} ({percentage:.1f}%)")
            else:
                report.append("  No successful responses")

            # Add error summary if we have failures
            if self.failed_count > 0:
                error_types = {}
                for result in self.results:
                    error = result.get("error")
                    if error:
                        error_type = error.split(":")[0] if ":" in error else error
                        error_types[error_type] = error_types.get(error_type, 0) + 1

                if error_types:
                    report.append("")
                    report.append("Error Summary:")
                    for error_type, count in sorted(
                        error_types.items(), key=lambda x: x[1], reverse=True
                    ):
                        report.append(f"  {error_type}: {count}")

            report.append("=" * 50)

            # Log the report at info level
            for line in report:
                self.log(line)

        except Exception as e:
            self.log(f"Error generating report: {str(e)}", "error")
