"""
HTTP client utilities for the Aethon Web Crawler
"""

import random
from typing import Dict, Optional, Any

import aiohttp
import requests

from .constants import USER_AGENTS, REFERRERS
from .url_processor import get_file_type


async def fetch_url(
    url: str,
    aiohttp_session: aiohttp.ClientSession,
    config: Dict[str, Any],
    files_collection: Dict[str, set],
) -> Optional[str]:
    """
    Fetch the content of a URL using aiohttp.
    """
    try:
        headers = build_headers(config)

        # Add ninja mode headers if enabled
        if config["ninja"]:
            headers["Referer"] = random.choice(REFERRERS)

        # Add cookies if provided
        cookies = {}
        if config["cookie"]:
            for cookie_part in config["cookie"].split(";"):
                if "=" in cookie_part:
                    name, value = cookie_part.strip().split("=", 1)
                    cookies[name] = value

        async with aiohttp_session.get(
            url,
            headers=headers,
            cookies=cookies,
            allow_redirects=True,
            ssl=None,  # Don't verify SSL in crawler for broader compatibility
        ) as response:
            if response.status != 200:
                return None

            # Check content type for text content
            content_type = response.headers.get("Content-Type", "")
            if (
                "text/" in content_type
                or "application/json" in content_type
                or "application/javascript" in content_type
            ):
                return await response.text()
            elif "xml" in content_type:
                return await response.text()
            else:
                # For binary content, just add it to the appropriate collection
                file_type = get_file_type(url)
                if file_type:
                    files_collection[file_type].add(url)
                return None

    except aiohttp.ClientError:
        # Log error in caller
        return None
    except Exception:
        # Log error in caller
        return None


async def fetch_wayback_urls(
    domain: str,
    aiohttp_session: aiohttp.ClientSession,
    discovered_urls: set,
    url_queue: list,
    wayback_urls: set,
) -> None:
    """
    Fetch URLs from the Wayback Machine (archive.org) for the target domain.
    """
    if not domain:
        return

    try:
        wayback_url = f"http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&collapse=urlkey"

        async with aiohttp_session.get(wayback_url) as response:
            if response.status == 200:
                data = await response.json()
                if len(data) > 1:  # First row is header
                    for item in data[1:]:
                        if len(item) > 2:
                            archived_url = item[2]  # The original URL
                            if archived_url not in discovered_urls:
                                url_queue.append((archived_url, 0))
                                discovered_urls.add(archived_url)
                                wayback_urls.add(archived_url)

    except Exception:
        # Log error in caller
        pass


def build_headers(config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build HTTP headers for requests.
    """
    headers = {
        "User-Agent": config["user_agent"] or random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    # Add custom headers if provided
    if config["headers"]:
        headers.update(config["headers"])

    return headers
