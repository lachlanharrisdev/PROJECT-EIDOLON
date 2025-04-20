"""
Data extraction utilities for the Aethon Web Crawler
"""

import re
import traceback
from typing import Dict, Any, Optional

from .constants import EMAIL_REGEX, SOCIAL_REGEX, AWS_BUCKET_REGEX, SECRET_REGEX


def extract_data(
    url: str,
    content: str,
    extracted: Dict[str, Any],
    config: Dict[str, Any],
    domain: str,
) -> None:
    """
    Extract various data types from the fetched content.
    """
    try:
        # Extract emails
        emails = re.findall(EMAIL_REGEX, content)
        for email in emails:
            extracted["emails"].add(email)

        # Extract social media accounts
        for platform, pattern in SOCIAL_REGEX.items():
            accounts = re.findall(pattern, content)
            for account in accounts:
                extracted["social"][platform].add(account)

        # Extract AWS buckets
        buckets = re.findall(AWS_BUCKET_REGEX, content)
        for bucket in buckets:
            extracted["aws_buckets"].add(bucket)

        # Extract secret keys if enabled
        if config["keys"]:
            for key_type, pattern in SECRET_REGEX.items():
                matches = re.findall(pattern, content)
                for match in matches:
                    # Some patterns have capturing groups, handle both cases
                    key = (
                        match[1]
                        if isinstance(match, tuple) and len(match) > 1
                        else match
                    )
                    extracted["secret_keys"][key_type].add(key)

        # Extract custom regex pattern if specified
        if config["regex"]:
            try:
                custom_matches = re.findall(config["regex"], content)
                for match in custom_matches:
                    if isinstance(match, tuple):
                        for group in match:
                            extracted["custom_regex"].add(group)
                    else:
                        extracted["custom_regex"].add(match)
            except re.error:
                # Logger will be handled in the caller
                pass

        # Extract subdomains if dns option is enabled
        if config["dns"]:
            extract_subdomains(content, domain, extracted["subdomains"])

    except Exception:
        # Logger will be handled in the caller
        pass


def extract_subdomains(content: str, domain: str, subdomain_set: set) -> None:
    """
    Extract subdomains from content.
    """
    if not domain:
        return

    try:
        subdomain_pattern = f"([a-zA-Z0-9]{{1,63}}\.){domain}"
        subdomains = re.findall(subdomain_pattern, content)
        for subdomain in subdomains:
            # Clean up the subdomain string
            clean_subdomain = subdomain.rstrip(".")
            if clean_subdomain != domain:
                subdomain_set.add(clean_subdomain)
    except Exception:
        pass
