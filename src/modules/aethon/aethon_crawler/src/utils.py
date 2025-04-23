import asyncio
import re
from urllib.parse import urljoin, urlparse, urldefrag
from robotexclusionrulesparser import RobotExclusionRulesParser
import httpx
from lxml import html as lxml_html
from typing import Callable  # Import Callable

# Cache for robots.txt rules to avoid re-fetching
_robots_cache = {}
_robots_lock = asyncio.Lock()


async def get_robots_rules(
    url: str,
    client: httpx.AsyncClient,
    log_func: Callable[[str, str], None],  # Use log_func
) -> RobotExclusionRulesParser | None:
    """Fetches, parses, and caches robots.txt rules for a given base URL."""
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")

    async with _robots_lock:
        if base_url in _robots_cache:
            return _robots_cache[base_url]

    try:
        # Use a separate client or configure the main one for short timeouts here
        resp = await client.get(robots_url, timeout=5.0, follow_redirects=True)
        resp.raise_for_status()
        parser = RobotExclusionRulesParser()
        parser.parse(resp.text)
        async with _robots_lock:
            _robots_cache[base_url] = parser
        return parser
    except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
        log_func(
            f"Could not fetch or parse robots.txt from {robots_url}: {e}", "WARNING"
        )  # Use log_func
        # Cache failure to avoid retrying constantly
        async with _robots_lock:
            _robots_cache[base_url] = None
        return None
    except Exception as e:  # Catch broader exceptions during parsing
        log_func(
            f"Error parsing robots.txt from {robots_url}: {e}", "WARNING"
        )  # Use log_func
        async with _robots_lock:
            _robots_cache[base_url] = None
        return None


def normalize_url(base: str, link: str) -> str | None:
    """Normalizes a URL found on a page relative to the base URL."""
    try:
        # Join the base URL and the potentially relative link
        abs_link = urljoin(base, link.strip())
        # Remove fragment identifiers (#...)
        abs_link_no_frag, _ = urldefrag(abs_link)
        # Parse the absolute link
        parsed_link = urlparse(abs_link_no_frag)

        # Ensure it's an HTTP/HTTPS scheme and has a network location (domain)
        if parsed_link.scheme not in ("http", "https") or not parsed_link.netloc:
            return None

        # Reconstruct the URL to ensure consistency (e.g., lowercase scheme/netloc)
        # Path is case-sensitive, query params might be too, keep them as is.
        normalized = f"{parsed_link.scheme.lower()}://{parsed_link.netloc.lower()}{parsed_link.path}"
        if parsed_link.query:
            normalized += f"?{parsed_link.query}"

        # Optional: Add trailing slash for root paths? (Consistency)
        # if not parsed_link.path and not parsed_link.query:
        #     normalized += '/'

        return normalized
    except ValueError:
        # Handle potential errors during urljoin or urlparse
        return None


# Use lxml for more robust link extraction
def extract_links(
    html_content: str, base_url: str, log_func: Callable[[str, str], None]
) -> set[str]:  # Use log_func
    """Extracts and normalizes valid HTTP/HTTPS links from HTML content using lxml."""
    links = set()
    try:
        if not html_content:
            return links
        # Use lxml to parse the HTML content
        tree = lxml_html.fromstring(html_content)
        # Let lxml resolve relative URLs based on the base_url
        tree.make_links_absolute(base_url, resolve_base_href=True)

        # Iterate over all links (<a> tags with href)
        for element, attribute, link, pos in tree.iterlinks():
            if attribute == "href":  # Ensure we are only processing href attributes
                # Normalize the absolute link obtained from lxml
                normalized = normalize_url(
                    base_url, link
                )  # Use base_url again in normalize for consistency checks
                if normalized:
                    links.add(normalized)
    except Exception as e:  # Catch potential parsing errors from lxml
        log_func(
            f"Could not parse HTML from {base_url} with lxml: {e}", "WARNING"
        )  # Use log_func
    return links
