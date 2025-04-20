"""
URL processing utilities for the Aethon Web Crawler
"""

import re
from typing import Optional, Set
from urllib.parse import urlparse, urljoin

from tld import get_fld

from .constants import FILE_EXTENSIONS


def normalize_url(base_url: str, url: str) -> Optional[str]:
    """
    Normalize a URL against a base URL.
    """
    try:
        # Handle empty or None URLs
        if not url or url.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
            return None

        # Remove fragments
        url = url.split("#")[0]

        # Join with base URL if relative
        full_url = urljoin(base_url, url)

        # Parse and normalize
        parsed = urlparse(full_url)

        # Skip URLs without scheme or netloc
        if not parsed.scheme or not parsed.netloc:
            return None

        # Clean the URL
        return parsed.geturl()

    except Exception:
        return None


def is_valid_url(url: str, domain: str = None, extracted_files: dict = None) -> bool:
    """
    Check if a URL is valid and should be crawled.
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)

        # Must have scheme and domain
        if not parsed.scheme or not parsed.netloc:
            return False

        # Check for common binary file extensions we don't want to crawl
        if any(
            parsed.path.lower().endswith(f".{ext}")
            for ext in FILE_EXTENSIONS["audio"]
            + FILE_EXTENSIONS["video"]
            + FILE_EXTENSIONS["image"]
            + FILE_EXTENSIONS["executable"]
        ):
            # Still track them as files, but don't crawl them
            file_type = get_file_type(url)
            if file_type and extracted_files is not None:
                extracted_files[file_type].add(url)
            return False

        # Must be http or https
        if parsed.scheme not in ["http", "https"]:
            return False

        # Check if URL is in scope (same domain)
        if domain:
            try:
                url_domain = get_fld(url, fix_protocol=True)
                # Only restrict to the same domain if domain is provided
                if url_domain != domain:
                    # Out-of-scope URL
                    return False
            except Exception:
                # If we can't parse the domain, be cautious and don't crawl
                return False

        return True

    except Exception:
        return False


def is_excluded(url: str, exclude_pattern: str) -> bool:
    """
    Check if a URL matches the exclusion pattern.
    """
    if not exclude_pattern:
        return False

    try:
        pattern = re.compile(exclude_pattern)
        return bool(pattern.search(url))
    except re.error:
        # Log error in the calling code
        return False


def get_file_type(url: str) -> Optional[str]:
    """
    Determine the file type based on URL extension.
    """
    path = urlparse(url).path.lower()

    for file_type, extensions in FILE_EXTENSIONS.items():
        if any(path.endswith(f".{ext}") for ext in extensions):
            return file_type

    return None


def extract_urls(
    base_url: str,
    html_content: str,
    extracted_params: dict,
    js_files: set,
    js_endpoints: set,
) -> Set[str]:
    """
    Extract URLs from HTML content and normalize them.
    """
    from bs4 import BeautifulSoup
    import re

    urls = set()
    try:
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, "lxml")

        # Extract URLs from various HTML elements
        for tag, attr in [
            ("a", "href"),
            ("img", "src"),
            ("script", "src"),
            ("link", "href"),
            ("form", "action"),
            ("object", "data"),
            ("embed", "src"),
            ("iframe", "src"),
            ("audio", "src"),
            ("video", "src"),
            ("source", "src"),
        ]:
            for element in soup.find_all(tag):
                if element.has_attr(attr):
                    url = element[attr]
                    # Normalize and filter URLs
                    normalized = normalize_url(base_url, url)
                    if normalized and is_valid_url(normalized):
                        # Track URLs with parameters
                        if "?" in normalized:
                            path = urlparse(normalized).path
                            base = path.split("/")[-1] if "/" in path else path
                            if base:
                                if base not in extracted_params:
                                    extracted_params[base] = []
                                if normalized not in extracted_params[base]:
                                    extracted_params[base].append(normalized)

                        # Special handling for JavaScript files
                        if normalized.lower().endswith(".js"):
                            js_files.add(normalized)

                        # Add to discovered URLs
                        urls.add(normalized)

        # Look for URLs in JavaScript
        for script in soup.find_all("script"):
            if script.string:
                # Extract URLs from inline JavaScript
                js_urls = re.findall(
                    r'(?:url|href|src):\s*[\'"`]([^\'"`,;{}<>]+)[\'"`]',
                    script.string,
                )
                for url in js_urls:
                    normalized = normalize_url(base_url, url)
                    if normalized and is_valid_url(normalized):
                        urls.add(normalized)

                # Extract API endpoints from JavaScript
                api_endpoints = re.findall(
                    r'[\'"`](/api/[^\'"`,;{}<>]+)[\'"`]', script.string
                )
                for endpoint in api_endpoints:
                    normalized = normalize_url(base_url, endpoint)
                    if normalized:
                        js_endpoints.add(normalized)
                        urls.add(normalized)

    except Exception:
        # Log error in the calling code
        pass

    return urls
