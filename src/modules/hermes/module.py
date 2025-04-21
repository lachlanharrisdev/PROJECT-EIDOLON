"""
Hermes module for Project Eidolon.

A simplified reporting module that transforms data inputs into
readable, minimalistic reports.
"""

import os
import json
import datetime
import pprint
from typing import Any, Dict, List
from pathlib import Path

from core.modules.engine import ModuleCore
from core.modules.util.messagebus import MessageBus


class HermesModule(ModuleCore):
    """
    Hermes module for generating simple, readable reports from data sources.
    """

    def init(self) -> None:
        """Initialize the Hermes module."""
        # Data storage
        self.data_to_report = None

        # Report configuration
        self.config = self.get_arguments() or {}
        self.report_dir = self.config.get("output_dir", "reports")

        # Create report directory if it doesn't exist
        os.makedirs(self.report_dir, exist_ok=True)
        self.log(f"Hermes initialized. Reports will be saved to: {self.report_dir}")

    def process(self, data: Any) -> None:
        """Process incoming data and store it for reporting."""
        if data is None:
            self.log("Received empty data, skipping", "warning")
            return

        # Store the data for reporting
        self.data_to_report = data
        self.log(f"Received data of type: {type(data).__name__}")

        # For reactive mode
        if self._run_mode == "reactive":
            self._input_received = True

    async def execute(self, message_bus: MessageBus) -> None:
        """Generate a report from the received data."""
        if self.data_to_report is None:
            self.log("No data to process, skipping report generation", "warning")
            return

        try:
            self.log("Generating report...")

            # Create the report
            report = self._generate_report()

            # Save the report
            self._save_report(report)

            # Log success
            self.log("Report generation complete")

            # Clear data to avoid duplicate reports
            self.data_to_report = None

        except Exception as e:
            self.log(f"Error generating report: {str(e)}", "error")
            import traceback

            self.log(traceback.format_exc(), "debug")

    def _generate_report(self) -> str:
        """Generate a simple text report from the stored data."""
        # Create a pretty printer with custom settings
        pp = pprint.PrettyPrinter(indent=2, width=100, depth=4, compact=False)

        # Get report title from config
        title = self.config.get("report_title", "Eidolon Data Report")

        # Start building the report
        lines = []
        lines.append("=" * 80)
        lines.append(title.center(80))
        lines.append("=" * 80)
        lines.append(
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append("-" * 80)

        # Add summary based on data type
        if isinstance(self.data_to_report, list):
            lines.append(f"Data type: List with {len(self.data_to_report)} items")
            if self.data_to_report:
                lines.append(f"Item type: {type(self.data_to_report[0]).__name__}")
        elif isinstance(self.data_to_report, dict):
            lines.append(f"Data type: Dictionary with {len(self.data_to_report)} keys")
            if self.data_to_report:
                lines.append("Top-level keys:")
                for key in list(self.data_to_report.keys())[:10]:
                    lines.append(f"  - {key}")
                if len(self.data_to_report) > 10:
                    lines.append(f"  - ... ({len(self.data_to_report) - 10} more keys)")
        else:
            lines.append(f"Data type: {type(self.data_to_report).__name__}")

        lines.append("-" * 80)
        lines.append("DATA CONTENT:")
        lines.append("-" * 80)

        # Format the data for readability
        try:
            # Different handling based on data type for better readability
            if isinstance(self.data_to_report, list) and len(self.data_to_report) > 5:
                # For long lists, show just a few items
                for i, item in enumerate(self.data_to_report[:5]):
                    formatted_item = pp.pformat(item)
                    lines.append(f"Item {i+1}:")
                    lines.extend("  " + line for line in formatted_item.splitlines())
                lines.append(f"... ({len(self.data_to_report) - 5} more items)")
            else:
                # For all other cases, use pretty printing
                formatted_data = pp.pformat(self.data_to_report)
                lines.extend(formatted_data.splitlines())
        except Exception as e:
            lines.append(f"Error formatting data: {str(e)}")
            lines.append(
                str(self.data_to_report)[:5000]
            )  # Fallback to simple string representation
            if len(str(self.data_to_report)) > 5000:
                lines.append("... (truncated)")

        lines.append("=" * 80)
        lines.append("End of Report".center(80))
        lines.append("=" * 80)

        return "\n".join(lines)

    def _save_report(self, report: str) -> None:
        """Save the report to a file."""
        try:
            # Make sure the reports directory exists
            os.makedirs(self.report_dir, exist_ok=True)

            # Generate a filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"report_{timestamp}.txt"
            filepath = os.path.join(self.report_dir, filename)

            # Write the report to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)

            # Also create a "latest.txt" that's always overwritten
            latest_path = os.path.join(self.report_dir, "latest.txt")
            with open(latest_path, "w", encoding="utf-8") as f:
                f.write(report)

            self.log(f"Report saved to {filepath}")

        except Exception as e:
            self.log(f"Error saving report: {str(e)}", "error")

    def default_output_topic(self) -> str:
        """Define default output topic for this module."""
        return "report"
