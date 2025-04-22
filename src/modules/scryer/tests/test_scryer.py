"""Unit tests for the Scryer module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from bs4 import BeautifulSoup

from core.modules.util.messagebus import MessageBus
from ..module import ScryerModule


@pytest.mark.asyncio
async def test_execute():
    """Test the execute method."""
    logger = Mock()
    module = ScryerModule(logger, None)
    message_bus = AsyncMock(spec=MessageBus)

    # Prepare test data
    test_data = [
        {
            "url": "https://example.com",
            "status_code": 200,
            "text": "<html><head><title>Example</title></head><body>Test</body></html>",
            "headers": {"content-type": "text/html"},
        }
    ]

    # Set up initial data
    module.crawled_data = test_data

    # Mock _initialize_extractors to avoid configuration issues
    with patch.object(module, "_initialize_extractors"), patch.object(
        module, "_log_extraction_summary"
    ):

        # Execute the module
        await module.execute(message_bus)

        # Check that message_bus.publish was called correctly
        assert message_bus.publish.call_count == 2

        # Check that crawled_data was cleared
        assert module.crawled_data == []


def test_extract_title():
    """Test the _extract_title method."""
    logger = Mock()
    module = ScryerModule(logger, None)

    html = "<html><head><title>Test Page</title></head><body>Content</body></html>"
    soup = BeautifulSoup(html, "html.parser")

    title = module._extract_title(soup)
    assert title == "Test Page"

    # Test fallback to h1 when title tag is missing
    html2 = "<html><body><h1>Heading Only</h1><p>Content</p></body></html>"
    soup2 = BeautifulSoup(html2, "html.parser")

    title2 = module._extract_title(soup2)
    assert title2 == "Heading Only"


def test_extract_meta():
    """Test the _extract_meta method."""
    logger = Mock()
    module = ScryerModule(logger, None)

    html = """
    <html>
      <head>
        <meta name="description" content="Page description">
        <meta name="keywords" content="test,page,keywords">
        <meta name="author" content="Test Author">
        <meta property="og:title" content="OG Title">
      </head>
      <body>Content</body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Test with specific meta tags to extract
    meta_tags = ["description", "keywords", "author"]
    meta_data = module._extract_meta(soup, meta_tags)

    assert len(meta_data) == 3
    assert meta_data["description"] == "Page description"
    assert meta_data["keywords"] == "test,page,keywords"
    assert meta_data["author"] == "Test Author"


def test_extract_emails():
    """Test the _extract_emails method."""
    logger = Mock()
    module = ScryerModule(logger, None)

    text = """
    Contact us at info@example.com or support@test.org.
    For sales inquiries: sales@company.co.uk
    Invalid emails: not.an.email, @missing-username.com
    """

    emails = module._extract_emails(text)

    assert len(emails) == 3
    assert "info@example.com" in emails
    assert "support@test.org" in emails
    assert "sales@company.co.uk" in emails


def test_process_page():
    """Test the _process_page method."""
    logger = Mock()
    module = ScryerModule(logger, None)

    # Setup test data
    page_data = {
        "url": "https://example.com",
        "status_code": 200,
        "text": """
        <html>
          <head>
            <title>Test Page</title>
            <meta name="description" content="Test description">
          </head>
          <body>
            <p>Contact us at info@example.com</p>
            <a href="https://example.com/about">About</a>
            <a href="https://example.com/contact">Contact</a>
          </body>
        </html>
        """,
        "headers": {"content-type": "text/html"},
    }

    # Setup config
    module.config = {"filters": {"status_codes": [200]}, "min_text_length": 10}

    # Setup extractors
    module.extractors = {
        "title": True,
        "meta": ["description"],
        "links": True,
        "emails": True,
        "phones": False,
        "headers": False,
        "cookies": False,
        "custom_selectors": [],
        "regex_patterns": [],
    }

    # Process the page
    result = module._process_page(page_data)

    # Check result
    assert result["url"] == "https://example.com"
    assert result["success"] == True
    assert result["title"] == "Test Page"
    assert result["meta"]["description"] == "Test description"
    assert len(result["links"]) == 2
    assert "info@example.com" in result["emails"]


def test_should_process_page():
    """Test the _should_process_page method."""
    logger = Mock()
    module = ScryerModule(logger, None)

    # Setup config
    module.config = {
        "filters": {
            "status_codes": [200],
            "content_type": ["text/html"],
            "include_domains": [],
        },
        "min_text_length": 10,
        "max_text_length": 10000,
    }

    # Valid page
    valid_page = {
        "url": "https://example.com",
        "status_code": 200,
        "text": "This is enough text to pass the length check",
        "headers": {"content-type": "text/html"},
    }

    # Invalid pages
    error_page = {
        "url": "https://example.com/error",
        "error": "Connection failed",
        "status_code": 0,
    }

    not_found_page = {
        "url": "https://example.com/notfound",
        "status_code": 404,
        "text": "Not found",
    }

    image_page = {
        "url": "https://example.com/image.jpg",
        "status_code": 200,
        "headers": {"content-type": "image/jpeg"},
    }

    short_text_page = {
        "url": "https://example.com/short",
        "status_code": 200,
        "text": "Too short",
        "headers": {"content-type": "text/html"},
    }

    # Test valid page
    assert module._should_process_page(valid_page) == True

    # Test invalid pages
    assert module._should_process_page(error_page) == False
    assert module._should_process_page(not_found_page) == False
    assert module._should_process_page(image_page) == False
    assert module._should_process_page(short_text_page) == False

    # Test domain filter
    module.config["filters"]["include_domains"] = ["allowed-domain.com"]
    assert module._should_process_page(valid_page) == False
