"""
Aethon Report Generator - Generate comprehensive reports from crawler data

This module transforms the raw data collected by the Aethon crawler
into structured, readable reports in various formats (HTML, Markdown, JSON).
"""

from logging import Logger
from typing import List, Dict, Any, Optional, Set, Union
import os
import json
import time
import asyncio
from datetime import datetime
import traceback

try:
    import jinja2
    import markdown
    from tabulate import tabulate
except ImportError as e:
    raise ImportError(f"Required package not available: {e}")

from core.modules.engine import ModuleCore
from core.modules.models import Device
from core.modules.util.messagebus import MessageBus
from core.modules.util.helpers import FileSystem


class AethonReport(ModuleCore):
    """
    Aethon report generator module for Eidolon.

    Generates comprehensive reports from the data collected by the Aethon crawler.
    """

    def _initialize_module(self) -> None:
        """
        Initialize module-specific state and components.
        """
        # Configuration with defaults
        self.config = {
            "format": "html",  # Output format: html, md, json
            "output_dir": "reports",  # Directory to save reports in
            "filename": None,  # Custom filename (auto-generated if None)
            "template_dir": None,  # Custom templates location
            "include_sections": [  # Sections to include in report
                "summary",
                "urls",
                "parameters",
                "emails",
                "social",
                "secrets",
                "files",
                "js",
                "subdomains",
            ],
            "theme": "default",  # Report theme/style
            "logo": None,  # Custom logo URL or path
            "auto_generate": True,  # Auto-generate report when crawl completes
        }

        # Input data storage
        self.crawl_data = {
            "crawled_urls": [],
            "extracted_data": {},
            "parameters": {},
            "intel": {},
            "secret_keys": {},
            "js_files": {},
            "subdomains": [],
            "crawl_status": {},
        }

        # Output tracking
        self.report_path = None
        self.report_data = {}
        self.report_status = {
            "generated": False,
            "timestamp": None,
            "format": None,
            "sections": [],
        }

        # Source tracking
        self.target_url = None  # Will be extracted from crawl status
        self.crawl_complete = False

        # Template engine
        self.jinja_env = None

        # Keep track of what data has been received
        self.received_data = set()

        # Last data receipt time
        self.last_data_time = time.time()
        self.data_timeout = 15  # seconds to wait for additional data

    def _process_input(self, data: Any) -> None:
        """
        Process input data from the message bus.
        """
        if data is None:
            return

        # Handle report configuration
        if isinstance(data, dict) and self._is_report_config(data):
            self._logger.info("Received report configuration")
            self._update_config(data)
            return

        # Track data receipt to know when we've received complete crawl data
        if (
            isinstance(data, dict)
            and "crawl_status" in data
            and data.get("complete", False)
        ):
            self.crawl_complete = True
            self._logger.info("Received crawl completion notification")

            # Store crawl status
            self.crawl_data["crawl_status"] = data
            self.received_data.add("crawl_status")

            # Extract target URL if available
            if self.target_url is None and "target_url" in data:
                self.target_url = data["target_url"]

        # Handle the various crawler outputs
        elif isinstance(data, list) and all(isinstance(url, str) for url in data):
            self._logger.info(f"Received {len(data)} crawled URLs")
            self.crawl_data["crawled_urls"] = data
            self.received_data.add("crawled_urls")

        elif isinstance(data, dict):
            # Each type of data has different structure, detect by content
            if "emails" in data and "social" in data:
                self._logger.info("Received extracted data")
                self.crawl_data["extracted_data"] = data
                self.received_data.add("extracted_data")

            elif any(key in data for key in ["api_key", "aws_key", "hash"]):
                self._logger.info("Received secret keys data")
                self.crawl_data["secret_keys"] = data
                self.received_data.add("secret_keys")

            elif any(file_type in data for file_type in ["files", "endpoints"]):
                self._logger.info("Received JavaScript data")
                self.crawl_data["js_files"] = data
                self.received_data.add("js_files")

            elif all(isinstance(val, list) for val in data.values()):
                # This is likely the parameters data
                self._logger.info("Received parameters data")
                self.crawl_data["parameters"] = data
                self.received_data.add("parameters")

            elif "emails" in data:
                # This is likely intel data
                self._logger.info("Received intelligence data")
                self.crawl_data["intel"] = data
                self.received_data.add("intel")

        # Handle subdomains
        elif (
            isinstance(data, list)
            and len(data) > 0
            and all(isinstance(d, str) for d in data)
        ):
            if any(
                "." in d for d in data
            ):  # Check if list contains domain-like strings
                self._logger.info(f"Received {len(data)} subdomains")
                self.crawl_data["subdomains"] = data
                self.received_data.add("subdomains")

        # Update last data receipt time
        self.last_data_time = time.time()

    def _is_report_config(self, data: Dict) -> bool:
        """
        Check if the provided dictionary is a valid report configuration.
        """
        if not isinstance(data, dict):
            return False

        # Check for report specific keys
        report_keys = [
            "format",
            "output_dir",
            "filename",
            "template_dir",
            "include_sections",
            "theme",
        ]
        return any(key in data for key in report_keys)

    def _update_config(self, config_data: Dict) -> None:
        """
        Update the report generator configuration with provided data.
        """
        # Update config with provided values
        for key, value in config_data.items():
            if key in self.config:
                self.config[key] = value

        # Validate format
        if self.config["format"] not in ["html", "md", "json", "txt"]:
            self._logger.warning(
                f"Unsupported format: {self.config['format']}, defaulting to HTML"
            )
            self.config["format"] = "html"

        # Create output directory if it doesn't exist
        if self.config["output_dir"]:
            os.makedirs(self.config["output_dir"], exist_ok=True)

    async def _before_run(self, message_bus: MessageBus) -> None:
        """
        Setup code that runs once before the main module loop.
        """
        # Initialize Jinja2 environment for templating
        template_dirs = []

        # If a custom template directory is specified, use that
        if self.config["template_dir"] and os.path.exists(self.config["template_dir"]):
            template_dirs.append(self.config["template_dir"])

        # Always include the default templates that come with the module
        module_dir = os.path.dirname(os.path.abspath(__file__))
        default_templates = os.path.join(module_dir, "templates")

        # Create default templates directory if it doesn't exist
        if not os.path.exists(default_templates):
            os.makedirs(default_templates, exist_ok=True)
            self._create_default_templates(default_templates)

        template_dirs.append(default_templates)

        # Initialize template loader with the directories
        loader = jinja2.FileSystemLoader(template_dirs)
        self.jinja_env = jinja2.Environment(
            loader=loader,
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Create output directory if it doesn't exist
        if self.config["output_dir"]:
            full_path = self.config["output_dir"]
            if not os.path.isabs(full_path):
                # Make relative paths absolute from project root
                full_path = os.path.join(
                    FileSystem._FileSystem__get_base_dir(), self.config["output_dir"]
                )
            os.makedirs(full_path, exist_ok=True)

        self.log(f"Report generator initialized")

    async def _run_iteration(self, message_bus: MessageBus) -> None:
        """
        Execute one iteration of the report generator.
        """
        # If we've received crawl completion notification and auto-generate is enabled,
        # generate the report after a short delay to ensure we have all data
        current_time = time.time()
        if (
            self.crawl_complete
            and self.config["auto_generate"]
            and not self.report_status["generated"]
            and current_time - self.last_data_time >= self.data_timeout
        ):

            # Generate the report
            self.log("Auto-generating report")
            await self._generate_report(message_bus)

        # If we've received significant data but no completion notice,
        # consider generating a preliminary report
        elif (
            len(self.received_data) >= 3
            and not self.report_status["generated"]
            and current_time - self.last_data_time >= self.data_timeout * 2
        ):

            self.log("Generating preliminary report based on available data")
            await self._generate_report(message_bus, preliminary=True)

    async def _generate_report(
        self, message_bus: MessageBus, preliminary: bool = False
    ) -> None:
        """
        Generate a report from the collected crawler data.
        """
        try:
            # Generate a timestamp for the report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Determine the target from crawl data or config
            target = "unknown"
            if self.target_url:
                target = (
                    self.target_url.replace("https://", "")
                    .replace("http://", "")
                    .split("/")[0]
                )
            elif self.crawl_data["crawl_status"].get("target_url"):
                target = self.crawl_data["crawl_status"].get("target_url")
                target = (
                    target.replace("https://", "").replace("http://", "").split("/")[0]
                )

            # Generate filename if not provided
            if not self.config["filename"]:
                status = "preliminary" if preliminary else "final"
                self.config["filename"] = (
                    f"aethon_report_{target}_{status}_{timestamp}.{self.config['format']}"
                )

            # Prepare the output directory
            output_dir = self.config["output_dir"]
            if not os.path.isabs(output_dir):
                # Make relative paths absolute from project root
                output_dir = os.path.join(
                    FileSystem._FileSystem__get_base_dir(), self.config["output_dir"]
                )

            # Create full path to the report file
            self.report_path = os.path.join(output_dir, self.config["filename"])

            # Prepare report data
            self.report_data = self._prepare_report_data()

            # Generate the report based on the desired format
            format_method = getattr(
                self, f"_generate_{self.config['format']}_report", None
            )
            if format_method:
                await format_method(self.report_data)
            else:
                # Fallback to JSON if format not supported
                self.log(
                    f"Unsupported format: {self.config['format']}, falling back to JSON"
                )
                await self._generate_json_report(self.report_data)

            self.log(f"Report generated successfully: {self.report_path}")

            # Update report status
            self.report_status = {
                "generated": True,
                "timestamp": timestamp,
                "format": self.config["format"],
                "path": self.report_path,
                "sections": self.config["include_sections"],
                "preliminary": preliminary,
            }

            # Create a report summary
            summary = self._create_report_summary()

            # Publish outputs
            await message_bus.publish("report_path", self.report_path)
            await message_bus.publish("report_summary", summary)
            await message_bus.publish("completion_status", self.report_status)

        except Exception as e:
            self.log(f"Error generating report: {str(e)}", "error")
            self.log(traceback.format_exc(), "debug")

            # Publish error status
            error_status = {
                "generated": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            await message_bus.publish("completion_status", error_status)

    def _prepare_report_data(self) -> Dict[str, Any]:
        """
        Prepare the data structure for generating the report.
        """
        # Basic information about the crawl
        target_info = {}
        if self.crawl_data["crawl_status"]:
            status = self.crawl_data["crawl_status"]
            target_info = {
                "url": self.target_url or status.get("target_url", "Unknown"),
                "start_time": status.get("timestamp", "Unknown"),
                "duration": status.get("duration", "Unknown"),
                "depth": status.get("level", "Unknown"),
                "visited": len(self.crawl_data["crawled_urls"]),
            }

        # Statistics for different data types
        stats = {
            "urls": len(self.crawl_data["crawled_urls"]),
            "parameters": (
                sum(len(urls) for urls in self.crawl_data["parameters"].values())
                if self.crawl_data["parameters"]
                else 0
            ),
            "emails": len(self.crawl_data["extracted_data"].get("emails", [])),
            "social": sum(
                len(accounts)
                for platform, accounts in self.crawl_data["extracted_data"]
                .get("social", {})
                .items()
            ),
            "subdomains": len(self.crawl_data["subdomains"]),
            "js_files": len(self.crawl_data["js_files"].get("files", [])),
            "js_endpoints": len(self.crawl_data["js_files"].get("endpoints", [])),
            "secret_keys": (
                sum(
                    len(keys)
                    for key_type, keys in self.crawl_data["secret_keys"].items()
                )
                if self.crawl_data["secret_keys"]
                else 0
            ),
            "files": sum(
                len(files)
                for file_type, files in self.crawl_data["extracted_data"]
                .get("files", {})
                .items()
            ),
        }

        # Overall report data
        report_data = {
            "title": f"Aethon Crawler Report - {target_info.get('url', 'Unknown')}",
            "generator": "Aethon Report Generator",
            "generation_time": datetime.now().isoformat(),
            "theme": self.config["theme"],
            "logo": self.config["logo"],
            "target": target_info,
            "stats": stats,
            "data": self.crawl_data,
            "config": {"sections": self.config["include_sections"]},
        }

        return report_data

    def _create_report_summary(self) -> Dict[str, Any]:
        """
        Create a summary of the report content.
        """
        summary = {
            "title": f"Aethon Report Summary",
            "path": self.report_path,
            "format": self.config["format"],
            "timestamp": datetime.now().isoformat(),
            "target": self.target_url,
            "stats": {
                "urls_crawled": len(self.crawl_data["crawled_urls"]),
                "emails_found": len(
                    self.crawl_data["extracted_data"].get("emails", [])
                ),
                "parameters_found": (
                    sum(len(urls) for urls in self.crawl_data["parameters"].values())
                    if self.crawl_data["parameters"]
                    else 0
                ),
                "subdomains_found": len(self.crawl_data["subdomains"]),
                "js_files_found": (
                    len(self.crawl_data["js_files"].get("files", []))
                    if self.crawl_data["js_files"]
                    else 0
                ),
                "secrets_found": (
                    sum(
                        len(keys)
                        for key_type, keys in self.crawl_data["secret_keys"].items()
                    )
                    if self.crawl_data["secret_keys"]
                    else 0
                ),
            },
            "sections": self.config["include_sections"],
            "preliminary": self.report_status.get("preliminary", False),
        }

        return summary

    async def _generate_html_report(self, report_data: Dict[str, Any]) -> None:
        """
        Generate an HTML report.
        """
        try:
            template = self.jinja_env.get_template("report.html")
            html_content = template.render(**report_data)

            with open(self.report_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        except jinja2.exceptions.TemplateError as e:
            self.log(f"Template error: {str(e)}", "error")
            # Create a basic HTML report as fallback
            self._generate_basic_html_report(report_data)

    def _generate_basic_html_report(self, report_data: Dict[str, Any]) -> None:
        """
        Generate a basic HTML report without using templates.
        """
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{report_data['title']}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1, h2 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            "tr:nth-child(even) { background-color: #f9f9f9; }",
            ".section { margin-bottom: 30px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{report_data['title']}</h1>",
            f"<p>Generated on: {report_data['generation_time']}</p>",
            "<div class='section'>",
            "<h2>Summary</h2>",
            "<table>",
            "<tr><th>Target URL</th><td>"
            + str(report_data["target"].get("url", "Unknown"))
            + "</td></tr>",
            "<tr><th>URLs Crawled</th><td>"
            + str(report_data["stats"]["urls"])
            + "</td></tr>",
            "<tr><th>Emails Found</th><td>"
            + str(report_data["stats"]["emails"])
            + "</td></tr>",
            "<tr><th>Parameters Found</th><td>"
            + str(report_data["stats"]["parameters"])
            + "</td></tr>",
            "<tr><th>Subdomains Found</th><td>"
            + str(report_data["stats"]["subdomains"])
            + "</td></tr>",
            "</table>",
            "</div>",
        ]

        # Add URL section if included
        if (
            "urls" in self.config["include_sections"]
            and self.crawl_data["crawled_urls"]
        ):
            html.extend(["<div class='section'>", "<h2>URLs</h2>", "<ul>"])

            for url in self.crawl_data["crawled_urls"][
                :100
            ]:  # Limit to first 100 for performance
                html.append(f"<li>{url}</li>")

            if len(self.crawl_data["crawled_urls"]) > 100:
                html.append(
                    f"<li>... and {len(self.crawl_data['crawled_urls']) - 100} more</li>"
                )

            html.extend(["</ul>", "</div>"])

        # Add emails section if included
        if "emails" in self.config["include_sections"] and self.crawl_data[
            "extracted_data"
        ].get("emails"):
            html.extend(["<div class='section'>", "<h2>Emails</h2>", "<ul>"])

            for email in self.crawl_data["extracted_data"].get("emails", []):
                html.append(f"<li>{email}</li>")

            html.extend(["</ul>", "</div>"])

        # Close the HTML document
        html.extend(["</body>", "</html>"])

        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html))

    async def _generate_md_report(self, report_data: Dict[str, Any]) -> None:
        """
        Generate a Markdown report.
        """
        try:
            template = self.jinja_env.get_template("report.md")
            md_content = template.render(**report_data)

            with open(self.report_path, "w", encoding="utf-8") as f:
                f.write(md_content)

        except jinja2.exceptions.TemplateError as e:
            self.log(f"Template error: {str(e)}", "error")
            # Create a basic Markdown report as fallback
            self._generate_basic_md_report(report_data)

    def _generate_basic_md_report(self, report_data: Dict[str, Any]) -> None:
        """
        Generate a basic Markdown report without using templates.
        """
        md = [
            f"# {report_data['title']}",
            f"Generated on: {report_data['generation_time']}",
            "",
            "## Summary",
            "",
            f"- **Target URL**: {report_data['target'].get('url', 'Unknown')}",
            f"- **URLs Crawled**: {report_data['stats']['urls']}",
            f"- **Emails Found**: {report_data['stats']['emails']}",
            f"- **Parameters Found**: {report_data['stats']['parameters']}",
            f"- **Subdomains Found**: {report_data['stats']['subdomains']}",
            "",
        ]

        # Add URL section if included
        if (
            "urls" in self.config["include_sections"]
            and self.crawl_data["crawled_urls"]
        ):
            md.extend(["## URLs", ""])

            for url in self.crawl_data["crawled_urls"][
                :100
            ]:  # Limit to first 100 for performance
                md.append(f"- {url}")

            if len(self.crawl_data["crawled_urls"]) > 100:
                md.append(
                    f"- ... and {len(self.crawl_data['crawled_urls']) - 100} more"
                )

            md.append("")

        # Add emails section if included
        if "emails" in self.config["include_sections"] and self.crawl_data[
            "extracted_data"
        ].get("emails"):
            md.extend(["## Emails", ""])

            for email in self.crawl_data["extracted_data"].get("emails", []):
                md.append(f"- {email}")

            md.append("")

        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))

    async def _generate_json_report(self, report_data: Dict[str, Any]) -> None:
        """
        Generate a JSON report.
        """
        # Filter out the sections based on include_sections config
        filtered_data = dict(report_data)

        # Make the data JSON serializable
        for key, value in filtered_data.items():
            if isinstance(value, set):
                filtered_data[key] = list(value)

        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(filtered_data, f, indent=2, default=str)

    async def _generate_txt_report(self, report_data: Dict[str, Any]) -> None:
        """
        Generate a plain text report.
        """
        lines = [
            report_data["title"],
            "=" * len(report_data["title"]),
            f"Generated on: {report_data['generation_time']}",
            "",
            "SUMMARY",
            "-------",
            f"Target URL: {report_data['target'].get('url', 'Unknown')}",
            f"URLs Crawled: {report_data['stats']['urls']}",
            f"Emails Found: {report_data['stats']['emails']}",
            f"Parameters Found: {report_data['stats']['parameters']}",
            f"Subdomains Found: {report_data['stats']['subdomains']}",
            "",
        ]

        # Add URL section if included
        if (
            "urls" in self.config["include_sections"]
            and self.crawl_data["crawled_urls"]
        ):
            lines.extend(["URLS", "----", ""])

            for url in self.crawl_data["crawled_urls"][
                :100
            ]:  # Limit to first 100 for performance
                lines.append(f"- {url}")

            if len(self.crawl_data["crawled_urls"]) > 100:
                lines.append(
                    f"- ... and {len(self.crawl_data['crawled_urls']) - 100} more"
                )

            lines.append("")

        # Add emails section if included
        if "emails" in self.config["include_sections"] and self.crawl_data[
            "extracted_data"
        ].get("emails"):
            lines.extend(["EMAILS", "------", ""])

            for email in self.crawl_data["extracted_data"].get("emails", []):
                lines.append(f"- {email}")

            lines.append("")

        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _create_default_templates(self, templates_dir: str) -> None:
        """
        Create default templates for report generation.
        """
        # Create HTML template
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eaeaea;
        }
        .logo img {
            max-height: 60px;
        }
        .title {
            flex-grow: 1;
            text-align: center;
        }
        .section {
            margin-bottom: 30px;
        }
        h1 {
            color: #2c3e50;
        }
        h2 {
            color: #3498db;
            padding-bottom: 5px;
            border-bottom: 1px solid #eaeaea;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 12px;
            border: 1px solid #ddd;
            text-align: left;
        }
        th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .summary-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            width: calc(25% - 20px);
            box-sizing: border-box;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stat-number {
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            font-size: 14px;
            color: #7f8c8d;
        }
        .url-list {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #eaeaea;
            padding: 10px;
            margin-top: 10px;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eaeaea;
            text-align: center;
            font-size: 12px;
            color: #7f8c8d;
        }
        a {
            color: #3498db;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="header">
        {% if logo %}
        <div class="logo">
            <img src="{{ logo }}" alt="Logo">
        </div>
        {% endif %}
        <div class="title">
            <h1>{{ title }}</h1>
            <p>Generated on {{ generation_time }}</p>
        </div>
    </div>

    <div class="section">
        <h2>Summary</h2>
        <table>
            <tr>
                <th>Target URL</th>
                <td>{{ target.url }}</td>
            </tr>
            <tr>
                <th>Start Time</th>
                <td>{{ target.start_time }}</td>
            </tr>
            <tr>
                <th>Crawl Duration</th>
                <td>{{ target.duration }}</td>
            </tr>
            <tr>
                <th>Crawl Depth</th>
                <td>{{ target.depth }}</td>
            </tr>
            <tr>
                <th>URLs Visited</th>
                <td>{{ target.visited }}</td>
            </tr>
        </table>

        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.urls }}</div>
                <div class="stat-label">URLs</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.emails }}</div>
                <div class="stat-label">Emails</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.parameters }}</div>
                <div class="stat-label">Parameters</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.subdomains }}</div>
                <div class="stat-label">Subdomains</div>
            </div>
        </div>
    </div>

    {% if 'urls' in config.sections and data.crawled_urls %}
    <div class="section">
        <h2>URLs</h2>
        <p>Total URLs discovered: {{ stats.urls }}</p>
        <div class="url-list">
            <ul>
                {% for url in data.crawled_urls %}
                <li><a href="{{ url }}" target="_blank">{{ url }}</a></li>
                {% endfor %}
            </ul>
        </div>
    </div>
    {% endif %}

    {% if 'parameters' in config.sections and data.parameters %}
    <div class="section">
        <h2>Parameters</h2>
        <p>URLs with parameters discovered: {{ stats.parameters }}</p>
        <table>
            <tr>
                <th>Endpoint</th>
                <th>URLs</th>
            </tr>
            {% for endpoint, urls in data.parameters.items() %}
            <tr>
                <td>{{ endpoint }}</td>
                <td>
                    <ul>
                        {% for url in urls %}
                        <li><a href="{{ url }}" target="_blank">{{ url }}</a></li>
                        {% endfor %}
                    </ul>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}

    {% if 'emails' in config.sections and data.extracted_data.emails %}
    <div class="section">
        <h2>Emails</h2>
        <p>Total emails found: {{ stats.emails }}</p>
        <ul>
            {% for email in data.extracted_data.emails %}
            <li>{{ email }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if 'social' in config.sections and data.extracted_data.social %}
    <div class="section">
        <h2>Social Media Accounts</h2>
        <p>Total accounts found: {{ stats.social }}</p>
        <table>
            <tr>
                <th>Platform</th>
                <th>Accounts</th>
            </tr>
            {% for platform, accounts in data.extracted_data.social.items() %}
            {% if accounts %}
            <tr>
                <td>{{ platform }}</td>
                <td>
                    <ul>
                        {% for account in accounts %}
                        <li>{{ account }}</li>
                        {% endfor %}
                    </ul>
                </td>
            </tr>
            {% endif %}
            {% endfor %}
        </table>
    </div>
    {% endif %}

    {% if 'secrets' in config.sections and data.secret_keys %}
    <div class="section">
        <h2>Secret Keys</h2>
        <p>Total secrets found: {{ stats.secret_keys }}</p>
        <table>
            <tr>
                <th>Type</th>
                <th>Keys</th>
            </tr>
            {% for key_type, keys in data.secret_keys.items() %}
            {% if keys %}
            <tr>
                <td>{{ key_type }}</td>
                <td>
                    <ul>
                        {% for key in keys %}
                        <li>{{ key }}</li>
                        {% endfor %}
                    </ul>
                </td>
            </tr>
            {% endif %}
            {% endfor %}
        </table>
    </div>
    {% endif %}

    {% if 'js' in config.sections and data.js_files %}
    <div class="section">
        <h2>JavaScript Files &amp; Endpoints</h2>
        <p>JS files found: {{ stats.js_files }}, JS endpoints found: {{ stats.js_endpoints }}</p>
        
        <h3>JavaScript Files</h3>
        <ul>
            {% for file in data.js_files.files %}
            <li><a href="{{ file }}" target="_blank">{{ file }}</a></li>
            {% endfor %}
        </ul>
        
        <h3>JavaScript Endpoints</h3>
        <ul>
            {% for endpoint in data.js_files.endpoints %}
            <li>{{ endpoint }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if 'subdomains' in config.sections and data.subdomains %}
    <div class="section">
        <h2>Subdomains</h2>
        <p>Total subdomains found: {{ stats.subdomains }}</p>
        <ul>
            {% for subdomain in data.subdomains %}
            <li>{{ subdomain }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}

    <div class="footer">
        <p>Generated by {{ generator }} | {{ generation_time }}</p>
    </div>
</body>
</html>"""

        html_template_path = os.path.join(templates_dir, "report.html")
        with open(html_template_path, "w", encoding="utf-8") as f:
            f.write(html_template)

        # Create Markdown template
        md_template = """# {{ title }}

*Generated on: {{ generation_time }}*

## Summary

- **Target URL**: {{ target.url }}
- **Start Time**: {{ target.start_time }}
- **Crawl Duration**: {{ target.duration }}
- **Crawl Depth**: {{ target.depth }}
- **URLs Visited**: {{ target.visited }}

### Statistics

- URLs: {{ stats.urls }}
- Emails: {{ stats.emails }}
- Parameters: {{ stats.parameters }}
- Subdomains: {{ stats.subdomains }}
- JS Files: {{ stats.js_files }}
- JS Endpoints: {{ stats.js_endpoints }}
- Secret Keys: {{ stats.secret_keys }}
- Files: {{ stats.files }}

{% if 'urls' in config.sections and data.crawled_urls %}
## URLs

Total URLs discovered: {{ stats.urls }}

{% for url in data.crawled_urls %}
- [{{ url }}]({{ url }})
{% endfor %}
{% endif %}

{% if 'parameters' in config.sections and data.parameters %}
## Parameters

URLs with parameters discovered: {{ stats.parameters }}

{% for endpoint, urls in data.parameters.items() %}
### {{ endpoint }}

{% for url in urls %}
- [{{ url }}]({{ url }})
{% endfor %}
{% endfor %}
{% endif %}

{% if 'emails' in config.sections and data.extracted_data.emails %}
## Emails

Total emails found: {{ stats.emails }}

{% for email in data.extracted_data.emails %}
- {{ email }}
{% endfor %}
{% endif %}

{% if 'social' in config.sections and data.extracted_data.social %}
## Social Media Accounts

Total accounts found: {{ stats.social }}

{% for platform, accounts in data.extracted_data.social.items() %}
{% if accounts %}
### {{ platform }}

{% for account in accounts %}
- {{ account }}
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

{% if 'secrets' in config.sections and data.secret_keys %}
## Secret Keys

Total secrets found: {{ stats.secret_keys }}

{% for key_type, keys in data.secret_keys.items() %}
{% if keys %}
### {{ key_type }}

{% for key in keys %}
- {{ key }}
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

{% if 'js' in config.sections and data.js_files %}
## JavaScript Files & Endpoints

JS files found: {{ stats.js_files }}, JS endpoints found: {{ stats.js_endpoints }}

### JavaScript Files

{% for file in data.js_files.files %}
- [{{ file }}]({{ file }})
{% endfor %}

### JavaScript Endpoints

{% for endpoint in data.js_files.endpoints %}
- {{ endpoint }}
{% endfor %}
{% endif %}

{% if 'subdomains' in config.sections and data.subdomains %}
## Subdomains

Total subdomains found: {{ stats.subdomains }}

{% for subdomain in data.subdomains %}
- {{ subdomain }}
{% endfor %}
{% endif %}

---
*Generated by {{ generator }} | {{ generation_time }}*
"""

        md_template_path = os.path.join(templates_dir, "report.md")
        with open(md_template_path, "w", encoding="utf-8") as f:
            f.write(md_template)

    async def _after_run(self, message_bus: MessageBus) -> None:
        """
        Clean up resources after the run is complete.
        """
        # Check if we need to generate a final report
        if not self.report_status["generated"] and self.received_data:
            self.log("Generating final report before shutdown")
            await self._generate_report(message_bus)

    def _handle_custom_command(self, command: chr) -> Device:
        """
        Handle custom module commands.
        """
        if command == "G":  # Generate report
            self.report_status["generated"] = False  # Reset to allow regeneration
            self.log("Report generation requested via command")

            return Device(
                name=self.meta.name, firmware=0x10000, protocol="GENERATING", errors=[]
            )
        elif command == "C":  # Clear report data
            self._clear_report_data()
            return Device(
                name=self.meta.name, firmware=0x10000, protocol="CLEARED", errors=[]
            )

        return super()._handle_custom_command(command)

    def _clear_report_data(self) -> None:
        """
        Clear all report data.
        """
        self.crawl_data = {
            "crawled_urls": [],
            "extracted_data": {},
            "parameters": {},
            "intel": {},
            "secret_keys": {},
            "js_files": {},
            "subdomains": [],
            "crawl_status": {},
        }

        self.report_path = None
        self.report_data = {}
        self.report_status = {
            "generated": False,
            "timestamp": None,
            "format": None,
            "sections": [],
        }

        self.received_data.clear()
        self.crawl_complete = False

        self.log("Report data cleared")

    def _get_cycle_time(self) -> float:
        """
        Get the time between execution cycles.
        """
        # Run more frequently when receiving data
        if len(self.received_data) > 0 and not self.report_status["generated"]:
            return 2.0

        return 10.0  # Default cycle time when idle
