"""Tests for the aethon_crawler module."""

import asyncio
import logging
import unittest
from unittest.mock import MagicMock, patch

import pytest
import httpx
from concurrent.futures import ThreadPoolExecutor

from ..module import AethonCrawlerModule
from core.modules.util.messagebus import MessageBus


class TestAethonCrawlerModule(unittest.TestCase):
    """Test cases for the AethonCrawlerModule."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger("test_aethon_crawler")
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        self.crawler = AethonCrawlerModule(self.logger, self.thread_pool)
        self.message_bus = MagicMock(spec=MessageBus)

        # Mock configuration
        self.crawler.get_config = MagicMock(
            return_value={
                "concurrency": 5,
                "timeout": 10,
                "retry_count": 1,
                "retry_delay": 0.1,
                "user_agent": "TestAgent/1.0",
                "follow_redirects": True,
                "max_redirects": 3,
                "verify_ssl": False,
            }
        )

    def tearDown(self):
        """Tear down test fixtures."""
        self.thread_pool.shutdown()

    def test_process_input_valid_data(self):
        """Test that valid input data is processed correctly."""
        test_urls = ["https://example.com", "https://test.com"]
        self.crawler._process_input(test_urls)
        self.assertEqual(self.crawler.urls, test_urls)

    def test_process_input_invalid_data(self):
        """Test that invalid input data is rejected."""
        invalid_data = {"url": "https://example.com"}
        self.crawler._process_input(invalid_data)
        self.assertEqual(self.crawler.urls, [])

    @patch("httpx.AsyncClient.get")
    @pytest.mark.asyncio
    async def test_fetch_url(self, mock_get):
        """Test fetching a URL."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html>Test</html>"
        mock_response.content = b"<html>Test</html>"
        mock_get.return_value = mock_response

        semaphore = asyncio.Semaphore(1)
        test_url = "https://example.com"

        # Test fetching the URL
        result = await self.crawler._fetch_url(
            test_url,
            semaphore,
            timeout=10,
            user_agent="Test/1.0",
            follow_redirects=True,
            max_redirects=3,
            retry_count=1,
            retry_delay=0.1,
            verify_ssl=False,
        )

        # Assertions
        self.assertEqual(result["url"], test_url)
        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["content_type"], "text/html")
        self.assertEqual(len(result["text"]), len("<html>Test</html>"))

    @patch("httpx.AsyncClient.get")
    @pytest.mark.asyncio
    async def test_fetch_url_with_error(self, mock_get):
        """Test fetching a URL with error handling."""
        # Setup mock error
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        semaphore = asyncio.Semaphore(1)
        test_url = "https://example.com"

        # Test fetching the URL with error
        result = await self.crawler._fetch_url(
            test_url,
            semaphore,
            timeout=10,
            user_agent="Test/1.0",
            follow_redirects=True,
            max_redirects=3,
            retry_count=1,
            retry_delay=0.1,
            verify_ssl=False,
        )

        # Assertions
        self.assertEqual(result["url"], test_url)
        self.assertFalse(result["success"])
        self.assertIsNone(result["status_code"])
        self.assertIsNotNone(result["error"])

    def test_generate_report(self):
        """Test report generation."""
        # Setup test data
        self.crawler.urls = ["https://example.com", "https://test.com"]
        self.crawler.results = [
            {
                "url": "https://example.com",
                "success": True,
                "status_code": 200,
                "elapsed": 0.5,
            },
            {
                "url": "https://test.com",
                "success": False,
                "status_code": 404,
                "elapsed": 0.3,
                "error": "Not Found",
            },
        ]
        self.crawler.start_time = 1000
        self.crawler.end_time = 1002
        self.crawler.success_count = 1
        self.crawler.failed_count = 1

        # Call the report generation
        with patch.object(self.crawler._logger, "info") as mock_logger:
            self.crawler._generate_report()

            # Verify the logger was called
            self.assertTrue(mock_logger.called)

            # Check that important parts of the report are included
            call_args = [call[0][0] for call in mock_logger.call_args_list]
            self.assertTrue(any("AETHON CRAWLER REPORT" in arg for arg in call_args))
            self.assertTrue(any("URLs processed: 2" in arg for arg in call_args))
            self.assertTrue(any("Successful: 1" in arg for arg in call_args))

    @patch.object(AethonCrawlerModule, "_crawl_urls")
    @pytest.mark.asyncio
    async def test_run(self, mock_crawl_urls):
        """Test the run method."""
        # Setup
        mock_crawl_urls.return_value = [{"url": "https://example.com", "success": True}]
        self.crawler.urls = ["https://example.com"]

        # Test run
        await self.crawler.run(self.message_bus)

        # Verify message_bus.publish was called
        self.message_bus.publish.assert_called_with(
            "crawled_data", mock_crawl_urls.return_value
        )


if __name__ == "__main__":
    unittest.main()
