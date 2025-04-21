from logging import Logger
from typing import List, Dict, Any, Optional
import asyncio
import re
from urllib.parse import urlparse

from core.modules.engine import ModuleCore
from core.modules.models import Device
from core.modules.util.messagebus import MessageBus

# Import helper modules from src
from .src.filters import *
from .src.utils import *
from .src.consts import *


class URLCleanModule(ModuleCore):
    """
    URL cleaning module that processes URLs based on filters and rules.
    Cleans and filters URLs according to various criteria such as extensions,
    parameters, and content patterns.
    """

    def _initialize_module(self) -> None:
        """Initialize module configuration from pipeline arguments"""
        # Get configuration from pipeline arguments
        self.config = self.get_arguments() or {}

        # Setup default configuration values if not provided
        self.whitelist = self.config.get("whitelist", [])
        self.blacklist = self.config.get(
            "blacklist",
            [
                "css",
                "png",
                "jpg",
                "jpeg",
                "svg",
                "ico",
                "webp",
                "scss",
                "tif",
                "tiff",
                "ttf",
                "otf",
                "woff",
                "woff2",
                "gif",
                "pdf",
                "bmp",
                "eot",
                "mp3",
                "mp4",
                "avi",
            ],
        )
        self.filters = self.config.get("filters", ["removecontent"])
        self.keepslash = self.config.get("keepslash", False)

        # Set up the filter configuration
        self._setup_filters()

        # Initialize data structures for URL processing
        self.urlmap = {}
        self.params_seen = set()
        self.patterns_seen = set()
        self.re_int = re.compile(r"/\d+([?/]|$)")

        # Clean input lists
        if self.whitelist:
            self.ext_list = tuple(clean_nargs(self.whitelist))
        elif self.blacklist:
            self.ext_list = tuple(clean_nargs(self.blacklist))
        else:
            self.ext_list = ()

        self.pending_urls = []
        self.log(f"URL Cleaner initialized with filters: {self.active_filters}")

    def _setup_filters(self) -> None:
        """Set up the filters based on configuration"""
        self.filter_map = filter_map

        self.active_filters = ["removecontent"]

        filters = self.filters[:]  # Make a copy to avoid modifying the original

        # Handle special filter 'allexts'
        if "allexts" in filters:
            filters.remove("allexts")
        else:
            # Apply whitelist or blacklist filter as default
            if self.whitelist:
                self.active_filters.append("whitelist")
            else:
                self.active_filters.append("blacklist")

        # Process each filter in the list
        for filter_name in filters:
            if filter_name in self.filter_map:
                self.active_filters.append(filter_name)
            elif filter_name + "s" in self.filter_map:
                self.active_filters.append(filter_name + "s")
            elif filter_name[:-1] in self.filter_map:
                self.active_filters.append(filter_name[:-1])

        # Handle special cases
        if "keepcontent" in self.active_filters:
            self.active_filters.remove("removecontent")
            self.active_filters.remove("keepcontent")

        # Remove keepslash from filters as it's handled separately
        if "keepslash" in self.active_filters:
            self.active_filters.remove("keepslash")

    def _process_input(self, data: Any) -> None:
        """Process input data from the message bus"""
        if isinstance(data, list):
            # Handle list of URLs
            self.pending_urls.extend(data)
            self.log(f"Received {len(data)} URLs for processing")
        elif isinstance(data, str):
            # Handle single URL
            self.pending_urls.append(data)
            self.log(f"Received 1 URL for processing")
        else:
            self.log(f"Received unexpected data type: {type(data)}", log_level="error")

    def create_pattern(self, path: str) -> re.Pattern:
        """Creates patterns for URLs with integers in them"""
        new_parts = []
        last_index = 0
        for i, part in enumerate(re.escape(path).split("/")):
            if part.isdigit():
                last_index = i
                new_parts.append("\\d+")
            else:
                new_parts.append(part)
        return re.compile("/".join(new_parts[: last_index + 1]))

    def apply_filters(self, path: str, params: Dict) -> bool:
        """
        Apply filters to a URL
        Returns True if the URL should be kept
        """
        meta = {
            "strict": (
                True if ("hasext" in self.filters or "noext" in self.filters) else False
            ),
            "ext_list": self.ext_list,
            "vuln_params": vuln_params,
        }

        for filter_name in self.active_filters:
            if not self.filter_map[filter_name](path, params, meta):
                return False
        return True

    def process_url(self, url_obj) -> None:
        """Process a single URL object"""
        host = url_obj.scheme + "://" + url_obj.netloc
        if host not in self.urlmap:
            self.urlmap[host] = {}

        path, params = url_obj.path, params_to_dict(url_obj.query)
        new_params = (
            []
            if not params
            else [param for param in params.keys() if param not in self.params_seen]
        )

        keep_url = self.apply_filters(path, params)
        if not keep_url:
            return

        self.params_seen.update(new_params)
        new_path = path not in self.urlmap[host]

        if new_path:
            if self.re_int.search(path):
                pattern = self.create_pattern(path)
                if pattern in self.patterns_seen:
                    return
                self.patterns_seen.add(pattern)
            self.urlmap[host][path] = []
            if params:
                self.urlmap[host][path].append(params)
        else:
            if new_params:
                self.urlmap[host][path].append(params)
            elif compare_params(self.urlmap[host][path], params):
                self.urlmap[host][path].append(params)

    def process_line(self, line: str) -> None:
        """Process a single line (URL)"""
        cleanline = line.strip() if self.keepslash else line.strip().rstrip("/")
        try:
            parsed_url = urlparse(cleanline)
            if parsed_url.netloc:
                self.process_url(parsed_url)
        except ValueError:
            pass

    def get_results(self) -> List[str]:
        """Get the processed results as a list of URLs"""
        result = []
        for host, value in self.urlmap.items():
            for path, params in value.items():
                if params:
                    for param in params:
                        result.append(host + path + dict_to_params(param))
                else:
                    result.append(host + path)
        return result

    async def _run_iteration(self, message_bus: MessageBus) -> None:
        """Run one iteration of the module's main logic"""
        if not self.pending_urls:
            return

        # Process pending URLs
        self.log(f"Processing {len(self.pending_urls)} URLs")

        # Clear previous results
        self.urlmap = {}

        # Process each URL
        for url in self.pending_urls:
            self.process_line(url)

        # Clear pending URLs
        self.pending_urls = []

        # Get cleaned results
        cleaned_urls = self.get_results()
        if cleaned_urls:
            self.log(f"Publishing {len(cleaned_urls)} cleaned URLs")
            await message_bus.publish("cleaned_urls", cleaned_urls)
        else:
            self.log("No URLs passed the filters")
