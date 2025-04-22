"""Unit tests for the Scryer module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from bs4 import BeautifulSoup

from core.modules.util.messagebus import MessageBus
from ..module import ScryerModule


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
    Check our <a href="mailto:contact@example.org">contact email</a>
    """

    emails = module._extract_emails(text)

    assert len(emails) == 4
    assert "info@example.com" in emails
    assert "support@test.org" in emails
    assert "sales@company.co.uk" in emails
    assert "contact@example.org" in emails  # From mailto: link


def test_extract_phones():
    """Test the _extract_phones method with various phone number formats."""
    logger = Mock()
    module = ScryerModule(logger, None)

    text = """
    Call us at: (555) 123-4567 or +1 555-987-6543
    International: +44 20 7123 4567
    European format: +33 01 23 45 67 89
    With dots: 555.123.4567
    With spaces: 555 123 4567
    """

    phones = module._extract_phones(text)

    assert len(phones) >= 6  # At least 6 different formats should be detected
    # Check for specific formats
    assert "(555) 123-4567" in phones
    assert any("+1" in phone for phone in phones)
    assert any("+44" in phone for phone in phones)
    assert any("+33" in phone for phone in phones)


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
