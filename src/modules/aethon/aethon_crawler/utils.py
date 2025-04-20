"""
General utility functions for the Aethon Web Crawler
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime


def prepare_results_for_publishing(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert data collections for serialization before publishing.
    """
    # Keep only the most essential data for publishing
    result_data = {
        "emails": list(extracted["emails"]),
        "js_files": list(extracted["js_files"]),
        "js_endpoints": list(extracted["js_endpoints"]),
        "parameters": extracted["parameters"],
        "subdomains": list(extracted["subdomains"]),
    }

    # Only include non-empty social account collections
    social_accounts = {}
    for platform, accounts in extracted["social"].items():
        if accounts:
            social_accounts[platform] = list(accounts)

    if social_accounts:
        result_data["social"] = social_accounts

    return result_data


def build_status_data(
    running: bool,
    is_final: bool,
    current_level: int,
    max_level: int,
    discovered_urls: set,
    visited_urls: set,
    url_queue: List[Tuple[str, int]],
    progress: Dict[str, int],
    extracted: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a simplified status data dictionary for publishing.
    """
    # Calculate progress percentage
    percentage = 0
    if progress["total"] > 0:
        percentage = min(100, round((progress["processed"] / progress["total"]) * 100))

    status = {
        "timestamp": datetime.now().isoformat(),
        "running": running,
        "complete": is_final,
        "level": current_level,
        "max_level": max_level,
        "urls_discovered": len(discovered_urls),
        "urls_visited": len(visited_urls),
        "urls_queued": len(url_queue),
        "progress_percentage": percentage,
        "stats": {
            "emails": len(extracted["emails"]),
            "js_files": len(extracted["js_files"]),
            "subdomains": len(extracted["subdomains"]),
        },
    }

    return status
