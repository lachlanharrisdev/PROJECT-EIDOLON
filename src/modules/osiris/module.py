"""Osiris data filter module implementation."""

from typing import Any, Dict, List, Optional, Set
import logging

from core.modules.engine import ModuleCore
from core.modules.util.messagebus import MessageBus


class OsirisModule(ModuleCore):
    """
    A lightweight and elegant data filter module for Project Eidolon.

    This module filters incoming data based on configurable rules and outputs
    both the data that passes the filter and the data that doesn't.
    """

    def init(self) -> None:
        """Initialize module-specific state."""
        # Initialize data structures
        self.data = []
        self.filtered_data = []
        self.filtered_out_data = []
        self.pass_count = 0
        self.reject_count = 0

        # Get the filter rules from configuration
        config = self.get_arguments() or {}
        filter_rules = config.get("rules", {})

        # Extract status code filter rules (default to 200-299 for success codes)
        self.status_codes = set(filter_rules.get("status_codes", range(200, 300)))

        self.log(
            f"Osiris filter initialized with status codes: {sorted(list(self.status_codes))}"
        )

    def process(self, data: Any) -> None:
        """
        Process input data (list of dictionaries).

        Args:
            data: Expected to be a list of dictionaries with at least status_code key
        """
        if isinstance(data, list):
            self.log(f"Received {len(data)} items for filtering")
            self.data = data
        else:
            self.log(
                f"Invalid input data format: expected list[dict], got {type(data)}",
                "error",
            )
            self.data = []

    def _filter_by_status_code(self, item: Dict) -> bool:
        """
        Filter an item based on its status code.

        Args:
            item: Dictionary that should contain a status_code key

        Returns:
            True if the item passes the filter, False otherwise
        """
        status_code = item.get("status_code")

        # If status_code doesn't exist, item fails the filter
        if status_code is None:
            return False

        # Check if the status code is in our allowed list
        return status_code in self.status_codes

    def _apply_filters(self) -> None:
        """Apply all filters to the input data and separate into passed/rejected lists."""
        self.filtered_data = []
        self.filtered_out_data = []

        for item in self.data:
            if self._filter_by_status_code(item):
                self.filtered_data.append(item)
            else:
                self.filtered_out_data.append(item)

        self.pass_count = len(self.filtered_data)
        self.reject_count = len(self.filtered_out_data)

    async def execute(self, message_bus: MessageBus) -> None:
        """
        Run the filter module logic.

        Args:
            message_bus: The message bus for publishing results
        """
        # Skip if no data to process
        if not self.data:
            self.log("No data to filter, skipping execution", "warning")
            return

        # Apply filters
        self._apply_filters()

        # Generate a brief report
        self._generate_report()

        # Publish results to message bus
        await message_bus.publish("filtered_data", self.filtered_data)
        await message_bus.publish("filtered_out_data", self.filtered_out_data)
        await message_bus.publish("pass_count", self.pass_count)
        await message_bus.publish("reject_count", self.reject_count)

        # Clear data to prevent reprocessing
        self.data = []

    def _generate_report(self) -> None:
        """Generate and log a report of the filtering operation."""
        total = self.pass_count + self.reject_count
        pass_rate = (self.pass_count / total) * 100 if total > 0 else 0

        report = [
            "=" * 50,
            "OSIRIS FILTER REPORT",
            "=" * 50,
            f"Items processed: {total}",
            f"Items passed: {self.pass_count} ({pass_rate:.1f}%)",
            f"Items rejected: {self.reject_count} ({100-pass_rate:.1f}%)",
            "=" * 50,
        ]

        # Log the report
        for line in report:
            self.log(line)

    def _handle_custom_command(self, command: chr) -> Any:
        """
        Handle custom commands specific to the Osiris module.

        Args:
            command: Single character command

        Returns:
            Result of the command execution
        """
        if command == "F":  # Generate filter report
            self._generate_report()
            return {"name": self.meta.name, "status": "Filter report generated"}
        elif command == "C":  # Clear all data
            self.data = []
            self.filtered_data = []
            self.filtered_out_data = []
            self.pass_count = 0
            self.reject_count = 0
            self.log("All filter data cleared")
            return {"name": self.meta.name, "status": "Filter data cleared"}

        # Fall back to standard command handling for other commands
        return super()._handle_custom_command(command)
