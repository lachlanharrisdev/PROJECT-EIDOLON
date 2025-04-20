"""
Tests for the Aethon web crawler module.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import aiohttp
from aiohttp.client_exceptions import ClientError

from core.modules.util.messagebus import MessageBus
from ..main import AethonCrawler


@pytest.fixture
def mock_logger():
    """Fixture for a mock logger."""
    return Mock()


@pytest.fixture
def mock_thread_pool():
    """Fixture for a mock thread pool."""
    return Mock()


@pytest.fixture
def crawler_module(mock_logger, mock_thread_pool):
    """Fixture for an initialized crawler module."""
    module = AethonCrawler(mock_logger, mock_thread_pool)
    return module


@pytest.fixture
def mock_message_bus():
    """Fixture for a mock message bus."""
    message_bus = Mock(spec=MessageBus)
    message_bus.publish = AsyncMock()
    return message_bus


@pytest.fixture
def sample_html():
    """Fixture providing sample HTML content."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <link href="/styles.css" rel="stylesheet">
        <script src="/script.js"></script>
    </head>
    <body>
        <h1>Test Page</h1>
        <p>This is a test page with some links and data for extraction:</p>
        <ul>
            <li><a href="https://example.com/page1">Link 1</a></li>
            <li><a href="https://example.com/page2?id=123">Link with params</a></li>
            <li><a href="/relative/path">Relative Link</a></li>
        </ul>
        <p>Contact us at test@example.com</p>
        <div>Follow us on <a href="https://twitter.com/testaccount">Twitter</a></div>
        <div>Check out our <a href="https://github.com/testuser/project">GitHub</a></div>
        <script>
            const apiUrl = '/api/v1/data';
            const config = {
                apiKey: 'abcdef1234567890',
                endpoint: 'https://example.com/api/v2/endpoint'
            };
        </script>
    </body>
    </html>
    """


@pytest.fixture
def default_config():
    """Fixture providing a default crawler configuration."""
    return {
        "url": "https://example.com",
        "level": 1,
        "threads": 2,
        "delay": 0,
        "timeout": 5,
    }


def test_initialization(crawler_module):
    """Test that the module initializes correctly."""
    assert crawler_module.meta.name == "aethon_crawler"
    assert hasattr(crawler_module, "config")
    assert hasattr(crawler_module, "extracted")
    assert crawler_module.running is False

    # Check initial data structures
    assert isinstance(crawler_module.visited_urls, set)
    assert isinstance(crawler_module.discovered_urls, set)
    assert isinstance(crawler_module.url_queue, list)


def test_is_crawl_config(crawler_module):
    """Test the crawl configuration validation."""
    # Valid configurations
    assert crawler_module._is_crawl_config({"url": "https://example.com"})
    assert crawler_module._is_crawl_config({"level": 2, "threads": 5})
    assert crawler_module._is_crawl_config({"url": "example.com", "exclude": "logout"})

    # Invalid configurations
    assert not crawler_module._is_crawl_config({"invalid_key": "value"})
    assert not crawler_module._is_crawl_config(
        {"urls": ["https://example.com"]}
    )  # wrong key name
    assert not crawler_module._is_crawl_config({})  # empty dict


def test_update_config(crawler_module):
    """Test configuration update functionality."""
    config = {
        "url": "example.com",  # No http prefix
        "level": 3,
        "seeds": ["test.com", "https://other.com"],
    }

    crawler_module._update_config(config)

    # URL should be normalized
    assert crawler_module.config["url"] == "https://example.com"
    assert crawler_module.base_url == "https://example.com"

    # Seeds should be normalized
    assert len(crawler_module.config["seeds"]) == 2
    assert crawler_module.config["seeds"][0] == "https://test.com"
    assert crawler_module.config["seeds"][1] == "https://other.com"

    # Level should be updated
    assert crawler_module.config["level"] == 3

    # Other defaults should remain
    assert crawler_module.config["threads"] == 10


def test_process_input_with_config(crawler_module):
    """Test processing config input."""
    config = {"url": "https://example.com", "level": 2}
    crawler_module._process_input(config)

    assert crawler_module.config["url"] == "https://example.com"
    assert crawler_module.config["level"] == 2


def test_process_input_with_seeds(crawler_module):
    """Test processing seed URLs input."""
    seeds = ["https://example1.com", "https://example2.com"]
    crawler_module._process_input(seeds)

    assert len(crawler_module.config["seeds"]) == 2
    assert all(url in crawler_module.config["seeds"] for url in seeds)


def test_process_input_invalid(crawler_module):
    """Test processing invalid input."""
    crawler_module._process_input("not a valid input")

    # Should log a warning but not crash
    crawler_module._logger.warning.assert_called_once()


def test_normalize_url(crawler_module):
    """Test URL normalization."""
    base = "https://example.com"

    # Absolute URLs
    assert (
        crawler_module._normalize_url(base, "https://other.com") == "https://other.com"
    )

    # Relative URLs
    assert crawler_module._normalize_url(base, "/page") == "https://example.com/page"
    assert (
        crawler_module._normalize_url(base, "subpage") == "https://example.com/subpage"
    )

    # Remove fragments
    assert (
        crawler_module._normalize_url(base, "/page#section")
        == "https://example.com/page"
    )

    # Skip invalid URLs
    assert crawler_module._normalize_url(base, "javascript:void(0)") is None
    assert crawler_module._normalize_url(base, "#fragment") is None
    assert crawler_module._normalize_url(base, "") is None


def test_is_valid_url(crawler_module):
    """Test URL validation."""
    # Set domain for scope checking
    crawler_module.domain = "example.com"

    # Valid URLs
    assert crawler_module._is_valid_url("https://example.com")
    assert crawler_module._is_valid_url("https://example.com/page")

    # Invalid URLs
    assert not crawler_module._is_valid_url("ftp://example.com")  # wrong scheme
    assert not crawler_module._is_valid_url("https://other.com")  # out of scope
    assert not crawler_module._is_valid_url(
        "https://example.com/file.mp4"
    )  # binary file
    assert not crawler_module._is_valid_url("invalid")  # not a URL


@patch("aiohttp.ClientSession")
@pytest.mark.asyncio
async def test_fetch_url(mock_session_class, crawler_module, sample_html):
    """Test URL fetching."""
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text.return_value = sample_html

    # Setup mock session
    mock_session = mock_session_class.return_value
    mock_session.__aenter__.return_value = mock_response

    crawler_module.aiohttp_session = mock_session

    # Test fetching
    content = await crawler_module._fetch_url("https://example.com")

    # Verify content was returned
    assert content == sample_html


@pytest.mark.asyncio
async def test_extract_urls(crawler_module, sample_html):
    """Test URL extraction from HTML."""
    urls = crawler_module._extract_urls("https://example.com", sample_html)

    # Check extracted URLs
    assert "https://example.com/page1" in urls
    assert "https://example.com/page2?id=123" in urls
    assert "https://example.com/relative/path" in urls

    # Check parameters are tracked
    assert "page2" in crawler_module.extracted["parameters"]
    assert (
        "https://example.com/page2?id=123"
        in crawler_module.extracted["parameters"]["page2"]
    )

    # Check JS files are tracked
    assert "https://example.com/script.js" in crawler_module.extracted["js_files"]


def test_extract_data(crawler_module, sample_html):
    """Test data extraction from HTML."""
    crawler_module._extract_data("https://example.com", sample_html)

    # Check emails
    assert "test@example.com" in crawler_module.extracted["emails"]

    # Check social media accounts
    assert "testaccount" in crawler_module.extracted["social"]["twitter"]
    assert "testuser" in crawler_module.extracted["social"]["github"]

    # Enable keys extraction and test
    crawler_module.config["keys"] = True
    crawler_module._extract_data("https://example.com", sample_html)

    # Check API keys
    assert "abcdef1234567890" in crawler_module.extracted["secret_keys"]["api_key"]


@pytest.mark.asyncio
async def test_publish_status(crawler_module, mock_message_bus):
    """Test status publishing."""
    # Setup progress data
    crawler_module.current_level = 1
    crawler_module.config["level"] = 2
    crawler_module.running = True
    crawler_module.discovered_urls = {"url1", "url2"}
    crawler_module.visited_urls = {"url1"}
    crawler_module.url_queue = [("url2", 1)]
    crawler_module.progress = {"total": 2, "processed": 1, "found": 2}
    crawler_module.extracted["emails"] = {"test@example.com"}

    # Publish status
    await crawler_module._publish_status(mock_message_bus)

    # Check that publish was called with correct topic
    mock_message_bus.publish.assert_called_once()
    args = mock_message_bus.publish.call_args[0]
    assert args[0] == "crawl_status"

    # Check status data
    status = args[1]
    assert status["running"] is True
    assert status["level"] == 1
    assert status["max_level"] == 2
    assert status["urls"]["discovered"] == 2
    assert status["urls"]["visited"] == 1
    assert status["urls"]["queued"] == 1
    assert status["progress"]["percentage"] == 50
    assert status["stats"]["emails"] == 1


@pytest.mark.asyncio
async def test_custom_commands(crawler_module):
    """Test custom command handling."""
    # Setup some data
    crawler_module.visited_urls = {"url1", "url2"}
    crawler_module.running = True

    # Test clear command
    device = crawler_module._handle_custom_command("C")
    assert device.protocol == "CLEARED"
    assert len(crawler_module.visited_urls) == 0
    assert crawler_module.running is False

    # Setup running state again
    crawler_module.running = True

    # Test terminate command
    device = crawler_module._handle_custom_command("T")
    assert device.protocol == "TERMINATED"
    assert crawler_module.running is False


@patch("aiohttp.ClientSession")
@pytest.mark.asyncio
async def test_before_run(mock_session_class, crawler_module, mock_message_bus):
    """Test initialization before running."""
    # Setup configuration
    crawler_module.config["url"] = "https://example.com"
    crawler_module.config["seeds"] = ["https://example.org"]

    # Mock aiohttp session
    mock_session = Mock()
    mock_session_class.return_value = mock_session

    # Run before_run
    await crawler_module._before_run(mock_message_bus)

    # Check initialization
    assert crawler_module.running is True
    assert len(crawler_module.url_queue) == 2  # Main URL + seed
    assert "https://example.com" in crawler_module.discovered_urls
    assert "https://example.org" in crawler_module.discovered_urls


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
