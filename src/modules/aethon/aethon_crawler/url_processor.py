"""
URL processing utilities for the Aethon Web Crawler
"""

import re
import urllib.parse
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup


# URL validation
def is_valid_url(url: str) -> bool:
    """
    Check if the URL is valid and within scope.
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)

        # Check URL scheme
        if parsed.scheme not in ["http", "https"]:
            return False

        # Check for common binary file patterns we want to skip for crawling
        # These are files we won't extract links from, but may add to the files collection
        binary_extensions = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".ico",
            ".svg",
            ".webp",
            ".mp4",
            ".webm",
            ".mp3",
            ".wav",
            ".ogg",
            ".zip",
            ".tar.gz",
            ".exe",
        ]

        for ext in binary_extensions:
            if parsed.path.lower().endswith(ext):
                return False

        return True
    except Exception:
        return False


def normalize_url(base_url: str, href: str) -> Optional[str]:
    """
    Normalize a URL found in a page.
    """
    if not href:
        return None

    # Skip non-http(s) links, fragments, and javascript
    if href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None

    try:
        # Convert to absolute URL
        full_url = urljoin(base_url, href)

        # Parse the URL
        parsed = urlparse(full_url)

        # Remove fragments
        normalized = urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                "",  # Remove fragment
            )
        )

        return normalized if is_valid_url(normalized) else None
    except Exception:
        return None


def is_excluded(url: str, exclude_pattern: Optional[str]) -> bool:
    """
    Check if URL should be excluded based on pattern.
    """
    if not exclude_pattern or not url:
        return False

    try:
        return bool(re.search(exclude_pattern, url))
    except re.error:
        # If regex is invalid, don't exclude
        return False


def extract_urls(
    base_url: str,
    html_content: str,
    parameters_dict: Dict[str, List[str]],
    js_files_set: Set[str],
    js_endpoints_set: Set[str],
) -> List[str]:
    """
    Extract URLs from the HTML content.
    """
    if not html_content:
        return []

    discovered_urls = []

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all links in a tags
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            url = normalize_url(base_url, href)
            if url and url not in discovered_urls:
                discovered_urls.append(url)

                # Check for URL parameters
                if "?" in url:
                    path = urlparse(url).path.strip("/")
                    endpoint = path.split("/")[-1] if path else "root"

                    # Initialize the dictionary entry if it doesn't exist
                    if endpoint not in parameters_dict:
                        parameters_dict[endpoint] = []

                    # Add the URL to the parameters dictionary
                    parameters_dict[endpoint].append(url)

        # Find links in iframe sources
        for iframe in soup.find_all("iframe", src=True):
            src = iframe.get("src", "")
            iframe_url = normalize_url(base_url, src)
            if iframe_url and iframe_url not in discovered_urls:
                discovered_urls.append(iframe_url)

        # Find JavaScript files
        for script in soup.find_all("script", src=True):
            src = script.get("src", "")
            js_url = normalize_url(base_url, src)
            if js_url:
                if js_url.endswith(".js"):
                    js_files_set.add(js_url)
                if js_url not in discovered_urls:
                    discovered_urls.append(js_url)

        # Find CSS files
        for css in soup.find_all("link", href=True):
            if css.get("rel") and "stylesheet" in css.get("rel"):
                href = css.get("href", "")
                css_url = normalize_url(base_url, href)
                if css_url and css_url not in discovered_urls:
                    discovered_urls.append(css_url)

        # Find image sources
        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            img_url = normalize_url(base_url, src)
            if img_url and img_url not in discovered_urls:
                discovered_urls.append(img_url)

        # Look for URLs in meta tags (e.g., OpenGraph)
        for meta in soup.find_all("meta", content=True):
            if meta.get("property") in ["og:url", "og:image", "og:video"]:
                content = meta.get("content", "")
                meta_url = normalize_url(base_url, content)
                if meta_url and meta_url not in discovered_urls:
                    discovered_urls.append(meta_url)

        # Look for URLs in data attributes
        for tag in soup.find_all(attrs={"data-src": True}):
            data_src = tag.get("data-src", "")
            data_url = normalize_url(base_url, data_src)
            if data_url and data_url not in discovered_urls:
                discovered_urls.append(data_url)

        # Look for JavaScript endpoints in the HTML
        js_patterns = [
            r"api/v[0-9]+/[a-zA-Z0-9_/-]+",
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.[a-z]+\(["\']([^"\']+)["\']',
            r'url:\s*["\']([^"\']+)["\']',
            r'src=["\']((?:http|https)://[^"\']+)["\']',  # Additional pattern for src attributes
            r'href=["\']((?:http|https)://[^"\']+)["\']',  # Additional pattern for href attributes
        ]

        for pattern in js_patterns:
            endpoints = re.findall(pattern, html_content)
            for endpoint in endpoints:
                if isinstance(endpoint, tuple):
                    endpoint = endpoint[
                        0
                    ]  # Extract first group if capturing groups are used
                endpoint_url = normalize_url(base_url, endpoint)
                if endpoint_url and endpoint_url not in js_endpoints_set:
                    if (
                        "/api/" in endpoint_url.lower()
                        or "endpoint" in endpoint_url.lower()
                    ):
                        js_endpoints_set.add(endpoint_url)
                    if endpoint_url not in discovered_urls:
                        discovered_urls.append(endpoint_url)

    except Exception as e:
        # Error handling happens in caller
        pass

    return discovered_urls


def get_file_type(url: str) -> Optional[str]:
    """
    Determine the file type from a URL extension.
    """
    if not url:
        return None

    try:
        # Extract file extension
        path = urlparse(url).path.lower()
        extension = path.split(".")[-1] if "." in path else None

        if not extension:
            return None

        # Map extension to file type
        extension_map = {
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
            "gif": "image",
            "bmp": "image",
            "svg": "image",
            "webp": "image",
            "ico": "image",
            "mp4": "video",
            "webm": "video",
            "avi": "video",
            "mov": "video",
            "mp3": "audio",
            "wav": "audio",
            "ogg": "audio",
            "flac": "audio",
            "pdf": "document",
            "doc": "document",
            "docx": "document",
            "xls": "document",
            "xlsx": "document",
            "ppt": "document",
            "pptx": "document",
            "txt": "document",
            "zip": "archive",
            "tar": "archive",
            "gz": "archive",
            "rar": "archive",
            "js": "code",
            "css": "code",
            "html": "code",
            "xml": "code",
            "json": "code",
            "exe": "executable",
            "dll": "executable",
            "so": "executable",
            "apk": "executable",
        }

        return extension_map.get(extension)

    except Exception:
        return None
