"""
General utility functions for the Aethon Web Crawler
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime


def prepare_results_for_publishing(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert data collections for serialization before publishing.
    """
    result_data = {
        "emails": list(extracted["emails"]),
        "social": {
            platform: list(accounts)
            for platform, accounts in extracted["social"].items()
        },
        "aws_buckets": list(extracted["aws_buckets"]),
        "secret_keys": {
            key_type: list(keys) for key_type, keys in extracted["secret_keys"].items()
        },
        "files": {
            file_type: list(files) for file_type, files in extracted["files"].items()
        },
        "subdomains": list(extracted["subdomains"]),
        "js_files": list(extracted["js_files"]),
        "js_endpoints": list(extracted["js_endpoints"]),
        "parameters": extracted["parameters"],
        "custom_regex": (
            list(extracted["custom_regex"]) if extracted.get("custom_regex") else []
        ),
    }
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
    Build a status data dictionary for publishing.
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
        "urls": {
            "discovered": len(discovered_urls),
            "visited": len(visited_urls),
            "queued": len(url_queue),
        },
        "progress": {
            "percentage": percentage,
            "processed": progress["processed"],
            "total": progress["total"],
        },
        "stats": {
            "emails": len(extracted["emails"]),
            "social_accounts": sum(
                len(accounts) for accounts in extracted["social"].values()
            ),
            "js_files": len(extracted["js_files"]),
            "endpoints": len(extracted["js_endpoints"]),
            "parameters": sum(len(urls) for urls in extracted["parameters"].values()),
            "subdomains": len(extracted["subdomains"]),
        },
    }

    return status
