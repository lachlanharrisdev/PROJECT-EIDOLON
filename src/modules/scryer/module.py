"""
Scryer module for Project Eidolon.

This module serves as a flexible post-crawl analyzer, designed to extract,
distill, and transform raw page data into structured, usable intelligence.
"""

import re
import json
import csv
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
from urllib.parse import urlparse
import asyncio
from collections import defaultdict, Counter

from bs4 import BeautifulSoup, ResultSet
from core.modules.engine import ModuleCore
from core.modules.util.messagebus import MessageBus
from core.modules.models import CourierEnvelope


class ScryerModule(ModuleCore):
    """
    Scryer module for extracting structured data from crawled web content.
    """

    def init(self) -> None:
        """Initialize the Scryer module."""
        self.crawled_data = []
        self.extracted_data = []
        self.extraction_count = 0
        self.extraction_failures = []
        self.config = {}
        self.extractors = {}
        # Pre-load configuration to be ready immediately
        self.config = self.get_arguments() or {}
        self._initialize_extractors()

    def process(self, envelope: CourierEnvelope) -> None:
        """
        Process input data from the message bus.

        Args:
            envelope: CourierEnvelope containing the data to process
        """
        # Extract actual data from the envelope
        data = envelope.data

        # Log metadata about the incoming data
        source = envelope.source_module or "unknown source"
        self.log(f"Processing data from {source} via topic '{envelope.topic}'")

        # Process the data as before
        if isinstance(data, list):
            self.log(f"Received {len(data)} items for processing")
            # Store the crawled data for processing during execute
            self.crawled_data = data
        else:
            self.log(f"Received unexpected data type: {type(data)}", "warning")

    async def execute(self, message_bus: MessageBus) -> None:
        """Execute the extraction process and publish results."""
        if not self.crawled_data:
            self.log("No crawled data to process, skipping execution", "warning")
            return

        # Ensure we have the latest config
        self.config = self.get_arguments() or self._config

        # Re-initialize extractors if needed
        if not self.extractors:
            self._initialize_extractors()

        # Process the crawled data
        self.log(f"Processing {len(self.crawled_data)} pages of crawled data")

        # Create an empty result list
        self.extracted_data = []
        self.extraction_count = 0
        self.extraction_failures = []

        # Counters for email and phone extractions
        total_emails = 0
        total_phones = 0

        try:
            # Process each URL's data
            for item in self.crawled_data:
                try:
                    result = self._process_page(item)
                    if result:
                        self.extracted_data.append(result)
                        if result.get("success", False):
                            self.extraction_count += 1
                            # Count emails and phones for logging
                            if "emails" in result:
                                total_emails += len(result["emails"])
                            if "phones" in result:
                                total_phones += len(result["phones"])
                except Exception as e:
                    self.log(
                        f"Error processing {item.get('url', 'unknown')}: {str(e)}",
                        "error",
                    )
                    self.extraction_failures.append(
                        {"url": item.get("url", "unknown"), "error": str(e)}
                    )

            # Log extraction summary for contact information
            if total_emails > 0 or total_phones > 0:
                self.log(
                    f"Contact information found: {total_emails} emails, {total_phones} phone numbers",
                    "info",
                )

            # Generate and log extraction summary
            self._log_extraction_summary()

            # Publish results to the message bus
            self.log(
                f"Publishing {len(self.extracted_data)} extraction results and {self.extraction_count} successful count"
            )
            await message_bus.publish("extracted_data", self.extracted_data)
            await message_bus.publish("extraction_count", self.extraction_count)

            # Clear processed data to prevent re-processing
            self.log("Clearing crawled data after processing")
            self.crawled_data = []
        except Exception as e:
            self.log(f"Error during extraction process: {str(e)}", "error")

    def _initialize_extractors(self) -> None:
        """Initialize the extractors based on configuration."""
        extract_config = self.config.get("extract", {})

        self.extractors = {
            "title": extract_config.get("title", True),
            "meta": extract_config.get("meta", ["description", "keywords", "author"]),
            "links": extract_config.get("links", True),
            "emails": extract_config.get("emails", True),
            "phones": extract_config.get(
                "phones", True
            ),  # Changed from False to True to enable by default
            "headers": extract_config.get("headers", False),
            "cookies": extract_config.get("cookies", False),
            "custom_selectors": extract_config.get("custom_selectors", []),
            "regex_patterns": extract_config.get("regex_patterns", []),
        }

        self.log(f"Initialized extractors: {self.extractors}", "debug")

    def _process_page(self, page_data: Dict) -> Dict:
        """
        Process a single page and extract data according to configuration.

        Args:
            page_data: Dictionary containing crawled page data

        Returns:
            Dictionary with extracted data
        """
        url = page_data.get("url", "")
        result = {"url": url, "success": False}

        # Skip processing if necessary conditions aren't met
        if not self._should_process_page(page_data):
            result["skipped"] = True
            result["skip_reason"] = self._get_skip_reason(page_data)
            return result

        # Get the HTML content
        html = page_data.get("text", "")
        if not html:
            result["skipped"] = True
            result["skip_reason"] = "No HTML content"
            return result

        soup = BeautifulSoup(html, "html.parser")

        # Extract data based on active extractors
        try:
            # Extract title if configured
            if self.extractors["title"]:
                title = self._extract_title(soup)
                if title:
                    result["title"] = title

            # Extract meta tags if configured
            if self.extractors["meta"]:
                meta_data = self._extract_meta(soup, self.extractors["meta"])
                if meta_data:
                    result["meta"] = meta_data

            # Extract links if configured
            if self.extractors["links"]:
                links = self._extract_links(soup, url)
                if links:
                    result["links"] = links

            # Extract emails if configured
            if self.extractors["emails"]:
                emails = self._extract_emails(html)
                if emails:
                    result["emails"] = list(emails)

            # Extract phone numbers if configured
            if self.extractors["phones"]:
                phones = self._extract_phones(html)
                if phones:
                    result["phones"] = list(phones)

            # Extract headers if configured
            if self.extractors["headers"]:
                headers = page_data.get("headers", {})
                if headers:
                    result["headers"] = headers

            # Extract cookies if configured
            if self.extractors["cookies"]:
                cookies = self._extract_cookies(page_data)
                if cookies:
                    result["cookies"] = cookies

            # Process custom CSS selectors if configured
            if self.extractors["custom_selectors"]:
                custom_data = self._extract_custom_selectors(
                    soup, self.extractors["custom_selectors"]
                )
                if custom_data:
                    result["custom"] = custom_data

            # Process regex patterns if configured
            if self.extractors["regex_patterns"]:
                regex_data = self._extract_regex_patterns(
                    html, self.extractors["regex_patterns"]
                )
                if regex_data:
                    result["regex_matches"] = regex_data

            # Mark this extraction as successful if we have some data
            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            self.log(f"Error extracting data from {url}: {e}", "error")

        return result

    def _should_process_page(self, page_data: Dict) -> bool:
        """
        Determine if a page should be processed based on configured filters.

        Args:
            page_data: Dictionary containing crawled page data

        Returns:
            Boolean indicating whether the page should be processed
        """
        # If there was an error in crawling, skip
        if page_data.get("error"):
            return False

        # Check the status code
        status_code = page_data.get("status_code", 0)
        allowed_codes = self.config.get("filters", {}).get("status_codes", [200])
        if status_code not in allowed_codes:
            return False

        # Check content type - allow processing if empty but text exists
        content_type = self._get_content_type(page_data)
        allowed_types = self.config.get("filters", {}).get(
            "content_type", ["text/html"]
        )
        has_text = bool(page_data.get("text", ""))  # Check if text content exists

        # If content_type is not empty, check against allowed types
        if content_type and not any(
            allowed in content_type.lower() for allowed in allowed_types
        ):
            return False
        # If content_type IS empty, only proceed if there's text content
        elif not content_type and not has_text:
            # Skip if content type is empty AND there's no text
            return False
        # Otherwise (content_type is allowed OR content_type is empty but text exists), continue checks...

        # Check domain filtering if specified
        url = page_data.get("url", "")
        include_domains = self.config.get("filters", {}).get("include_domains", [])
        if include_domains:
            domain = self._extract_domain(url)
            if domain not in include_domains:
                return False

        # Check text length
        text = page_data.get("text", "")
        min_length = self.config.get("min_text_length", 200)
        max_length = self.config.get("max_text_length", 0)

        if len(text) < min_length:
            return False

        if max_length > 0 and len(text) > max_length:
            # We'll still process it but truncate later
            pass

        return True

    def _get_skip_reason(self, page_data: Dict) -> str:
        """Get the reason why a page was skipped."""
        if page_data.get("error"):
            return f"Crawl error: {page_data['error']}"

        status_code = page_data.get("status_code", 0)
        allowed_codes = self.config.get("filters", {}).get("status_codes", [200])
        if status_code not in allowed_codes:
            return f"Status code {status_code} not in allowed codes {allowed_codes}"

        content_type = self._get_content_type(page_data)
        allowed_types = self.config.get("filters", {}).get(
            "content_type", ["text/html"]
        )
        has_text = bool(page_data.get("text", ""))

        # Check content type condition based on the modified logic
        if content_type and not any(
            allowed in content_type.lower() for allowed in allowed_types
        ):
            return f"Content type '{content_type}' not in allowed types"
        elif not content_type and not has_text:
            return "Content type missing and no text content found"
        # If we got here, content type wasn't the primary reason for skipping (if skipped)

        url = page_data.get("url", "")
        include_domains = self.config.get("filters", {}).get("include_domains", [])
        if include_domains:
            domain = self._extract_domain(url)
            if domain not in include_domains:
                return f"Domain '{domain}' not in included domains"

        text = page_data.get("text", "")
        min_length = self.config.get("min_text_length", 200)
        if len(text) < min_length:
            return f"Text length ({len(text)}) below minimum ({min_length})"

        return "Unknown reason"

    def _get_content_type(self, page_data: Dict) -> str:
        """Extract content type from page headers."""
        headers = page_data.get("headers", {})
        return headers.get("content-type", "").lower()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return ""

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the page title."""
        title_tag = soup.title
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        # Fallback to h1 if no title tag
        h1_tag = soup.find("h1")
        if h1_tag and h1_tag.text:
            return h1_tag.text.strip()

        return None

    def _extract_meta(self, soup: BeautifulSoup, meta_types: List[str]) -> Dict:
        """Extract meta tags of specified types."""
        result = {}

        for meta_tag in soup.find_all("meta"):
            # Handle different meta tag formats
            name = meta_tag.get("name", meta_tag.get("property", "")).lower()
            if name in meta_types:
                content = meta_tag.get("content", "")
                if content:
                    result[name] = content

        return result

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from the page."""
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            # Skip empty, javascript, and anchor links
            if href and not href.startswith(("javascript:", "#")):
                links.append(href)

        return links

    def _extract_emails(self, text: str) -> Set[str]:
        """
        Extract email addresses from text.

        This method extracts email addresses using regex patterns and also checks
        for mailto: links in the HTML when possible.
        """
        # More comprehensive regex for emails that handles more edge cases
        email_pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
        emails = set(re.findall(email_pattern, text))

        # Also look for mailto: links which often contain emails not in plain text
        mailto_pattern = r"mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"
        mailto_emails = set(re.findall(mailto_pattern, text))

        # Combine both sets
        emails.update(mailto_emails)

        # Log what we found for debugging
        if emails:
            self.log(f"Found {len(emails)} email addresses", "debug")

        return emails

    def _extract_phones(self, text: str) -> Set[str]:
        """
        Extract phone numbers from text.

        This method uses multiple regex patterns to extract phone numbers in various formats:
        - North American: +1 (555) 123-4567, 555-123-4567
        - International: +XX XXX XXX XXXX
        - European: +XX XX XXX XX XX
        - Common formats with dots, spaces, or dashes as separators
        """
        phone_patterns = [
            # North American format: +1 (555) 123-4567 or 555-123-4567
            r"(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})",
            # International format with country code: +XX XXXXXXXXXX
            r"(?:\+|00)[1-9][0-9\s\-().]{7,}[0-9]",
            # Additional formats like: 555.123.4567 or 555 123 4567
            r"[0-9]{3}[.\s][0-9]{3}[.\s][0-9]{4}",
            # European formats like: +XX XX XXX XX XX
            r"(?:\+|00)[1-9]{2}(?:[-.\s][0-9]{2}){4}",
        ]

        # Gather results from all patterns
        phones = set()
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            # Handle tuples from capturing groups in the first pattern
            for match in matches:
                if isinstance(match, tuple):
                    # Format the phone number consistently
                    phones.add(f"({match[0]}) {match[1]}-{match[2]}")
                else:
                    phones.add(match)

        # Log what we found for debugging
        if phones:
            self.log(f"Found {len(phones)} phone numbers", "debug")

        return phones

    def _extract_cookies(self, page_data: Dict) -> List[Dict]:
        """Extract cookies from the response."""
        cookies = []
        headers = page_data.get("headers", {})

        # Look for Set-Cookie headers
        for key, value in headers.items():
            if key.lower() == "set-cookie":
                if isinstance(value, list):
                    for cookie in value:
                        cookies.append(self._parse_cookie(cookie))
                else:
                    cookies.append(self._parse_cookie(value))

        return cookies

    def _parse_cookie(self, cookie_str: str) -> Dict:
        """Parse a cookie string into a dictionary."""
        parts = cookie_str.split(";")
        if not parts:
            return {}

        # The first part is the name=value
        main_part = parts[0].strip()
        if "=" in main_part:
            name, value = main_part.split("=", 1)
        else:
            name, value = main_part, ""

        result = {"name": name.strip(), "value": value.strip()}

        # Add other attributes
        for part in parts[1:]:
            part = part.strip()
            if "=" in part:
                attr_name, attr_value = part.split("=", 1)
                result[attr_name.strip().lower()] = attr_value.strip()
            else:
                result[part.lower()] = True

        return result

    def _extract_custom_selectors(
        self, soup: BeautifulSoup, selectors: List[Dict]
    ) -> Dict:
        """Extract content using custom CSS selectors."""
        result = {}

        for selector in selectors:
            if isinstance(selector, str):
                # Simple string selector
                elements = soup.select(selector)
                if elements:
                    result[selector] = [el.text.strip() for el in elements]
            elif isinstance(selector, dict):
                # Dict with name and selector
                sel_name = selector.get("name", "")
                sel_query = selector.get("selector", "")
                attr = selector.get("attribute", None)

                if sel_name and sel_query:
                    elements = soup.select(sel_query)
                    if elements:
                        if attr:
                            # Extract specific attribute
                            values = [
                                el.get(attr, "") for el in elements if el.has_attr(attr)
                            ]
                            if values:
                                result[sel_name] = values
                        else:
                            # Extract text content
                            result[sel_name] = [el.text.strip() for el in elements]

        return result

    def _extract_regex_patterns(self, text: str, patterns: List[str]) -> Dict:
        """Extract content using regex patterns."""
        result = {}

        for pattern_item in patterns:
            if isinstance(pattern_item, str):
                # Simple string pattern
                pattern_name = f"pattern_{len(result)}"
                pattern = pattern_item
            elif isinstance(pattern_item, dict):
                # Dict with name and pattern
                pattern_name = pattern_item.get("name", f"pattern_{len(result)}")
                pattern = pattern_item.get("pattern", "")
            else:
                continue

            if pattern:
                try:
                    matches = re.findall(pattern, text)
                    if matches:
                        result[pattern_name] = matches
                except re.error:
                    self.log(f"Invalid regex pattern: {pattern}", "warning")

        return result

    def _log_extraction_summary(self) -> None:
        """Log a summary of the extraction process."""
        total_pages = len(self.crawled_data)
        successful_extractions = self.extraction_count
        failed_extractions = len(self.extraction_failures)

        success_rate = (
            (successful_extractions / total_pages) * 100 if total_pages > 0 else 0
        )

        # Generate domain stats
        domains = [
            self._extract_domain(item.get("url", "")) for item in self.extracted_data
        ]
        domain_counts = Counter(domains)
        top_domains = domain_counts.most_common(5)

        # Generate tag frequency for successful extractions
        tag_frequency = defaultdict(int)
        for item in self.extracted_data:
            if not item.get("success", False) or "html_tags" not in item:
                continue

            for tag, count in item["html_tags"].items():
                tag_frequency[tag] += count

        top_tags = Counter(tag_frequency).most_common(5)

        # Generate error summary
        error_types = defaultdict(int)
        for failure in self.extraction_failures:
            error = failure.get("error", "")
            error_type = error.split(":")[0] if ":" in error else error
            error_types[error_type] += 1

        # Create and log the report
        report = [
            "=" * 50,
            "SCRYER EXTRACTION REPORT",
            "=" * 50,
            f"Total pages processed: {total_pages}",
            f"Successful extractions: {successful_extractions} ({success_rate:.1f}%)",
            f"Failed extractions: {failed_extractions}",
        ]

        # Add domain information
        if top_domains:
            report.append("")
            report.append("Most common domains:")
            for domain, count in top_domains:
                report.append(f"  {domain}: {count}")

        # Add tag frequency
        if top_tags:
            report.append("")
            report.append("Most common HTML tags:")
            for tag, count in top_tags:
                report.append(f"  {tag}: {count}")

        # Add error summary
        if error_types:
            report.append("")
            report.append("Error summary:")
            for error_type, count in sorted(
                error_types.items(), key=lambda x: x[1], reverse=True
            ):
                report.append(f"  {error_type}: {count}")

        report.append("=" * 50)

        # Log the report
        for line in report:
            self.log(line)

    def transform(self) -> Any:
        """Transform the results to the configured output format."""
        if not hasattr(self, "extracted_data") or not self.extracted_data:
            return None

        output_format = self.config.get("output_format", "json")
        include_failed = self.config.get("include_failed", False)

        # Filter out failed extractions if configured
        if not include_failed:
            data = [item for item in self.extracted_data if item.get("success", False)]
        else:
            data = self.extracted_data

        if output_format == "flat":
            # Flatten the structure for simpler analysis
            return self._flatten_data(data)
        elif output_format == "csv":
            # Not returning actual CSV here, just preparing data in a format
            # that would be suitable for CSV conversion
            return self._prepare_csv_data(data)
        else:
            # Default to JSON structure
            return data

    def _flatten_data(self, data: List[Dict]) -> List[Dict]:
        """Flatten the nested structure of extraction results."""
        flattened = []

        for item in data:
            flat_item = {"url": item.get("url", "")}

            # Add title directly
            if "title" in item:
                flat_item["title"] = item["title"]

            # Flatten meta tags
            if "meta" in item:
                for meta_key, meta_value in item["meta"].items():
                    flat_item[f"meta_{meta_key}"] = meta_value

            # Add other simple fields
            for field in ["emails", "phones"]:
                if field in item and item[field]:
                    flat_item[field] = ", ".join(item[field])

            # Add first few links if available
            if "links" in item and item["links"]:
                for i, link in enumerate(item["links"][:5]):
                    flat_item[f"link_{i+1}"] = link
                flat_item["link_count"] = len(item["links"])

            flattened.append(flat_item)

        return flattened

    def _prepare_csv_data(self, data: List[Dict]) -> List[Dict]:
        """Prepare data in a format suitable for CSV output."""
        csv_ready = []

        # Find all possible keys across all items
        all_keys = set()
        for item in data:
            self._collect_keys(item, all_keys)

        # Create normalized data with all keys
        for item in data:
            flat_item = {}
            for key in all_keys:
                value = self._get_nested_value(item, key)
                if isinstance(value, (list, dict)):
                    flat_item[key] = json.dumps(value)
                else:
                    flat_item[key] = value
            csv_ready.append(flat_item)

        return csv_ready

    def _collect_keys(self, item: Dict, keys_set: Set[str], prefix: str = "") -> None:
        """Recursively collect all keys from nested dictionaries."""
        for key, value in item.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                self._collect_keys(value, keys_set, full_key)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Don't try to flatten lists of objects
                keys_set.add(full_key)
            else:
                keys_set.add(full_key)

    def _get_nested_value(self, item: Dict, key: str) -> Any:
        """Get value from a nested dictionary using dot notation."""
        parts = key.split(".")
        current = item

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def default_output_topic(self) -> str:
        """Return the default output topic for this module."""
        return "extracted_data"

    def cycle_time(self) -> float:
        """Define how frequently the module should run if in loop mode."""
        return 10.0  # Run more frequently to process data faster
