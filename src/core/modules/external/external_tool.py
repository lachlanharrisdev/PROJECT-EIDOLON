# CURRENTLY WIP, DO NOT USE

from core.modules.engine import ModuleCore
from core.modules.util.messagebus import MessageBus
import asyncio
import subprocess
import shlex
import json
from typing import Dict, Any, List, Optional, Union


class ExternalToolModule(ModuleCore):
    """
    Base class for modules that wrap external command-line tools.
    Provides common functionality for executing external tools and processing their output.
    """

    def init(self) -> None:
        """Initialize module-specific components."""
        self.tool_name = ""  # Override this in subclasses
        self.command_template = ""  # Override this in subclasses
        self.last_result = None
        self.output_format = "text"  # Options: text, json, xml
        self.running_process = None
        self.current_args = {}

    async def execute(self, message_bus: MessageBus) -> None:
        """Execute the tool with current parameters."""
        # Skip if already processed or no arguments
        if not self.current_args:
            return

        try:
            self.log(f"Running {self.tool_name} with arguments: {self.current_args}")

            # Build command from template and arguments
            cmd = self._build_command()

            # Run the command asynchronously
            result = await self.run_tool_command(cmd)

            # Process the result based on output format
            processed_result = self._process_output(result)

            # Publish results to message bus
            if processed_result:
                await message_bus.publish(
                    f"{self.tool_name.lower()}_results", processed_result
                )

            # Clear arguments to prevent re-running
            self.current_args = {}

        except Exception as e:
            self.log(f"Error executing {self.tool_name}: {str(e)}", "error")

    def process(self, data: Any) -> None:
        """
        Process incoming data (tool parameters).
        Expects a dictionary with tool-specific arguments.
        """
        if isinstance(data, dict):
            self.current_args = data
            self.log(f"Received parameters for {self.tool_name}: {data}")
        else:
            self.log(f"Unexpected data format: {type(data)}", "warning")

    async def run_tool_command(self, command: str) -> str:
        """
        Execute an external tool command and return its output.
        """
        self.log(f"Executing command: {command}")

        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            self.running_process = process
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                self.log(
                    f"Command failed with exit code {process.returncode}: {stderr.decode('utf-8')}",
                    "error",
                )
                return ""

            return stdout.decode("utf-8")

        except Exception as e:
            self.log(f"Failed to execute command: {str(e)}", "error")
            return ""
        finally:
            self.running_process = None

    def _build_command(self) -> str:
        """
        Build the command string from the template and current arguments.
        Override this in subclasses if needed.
        """
        cmd = self.command_template

        # Replace placeholders in the template with actual values
        for key, value in self.current_args.items():
            placeholder = f"{{{key}}}"
            if placeholder in cmd:
                if isinstance(value, str):
                    cmd = cmd.replace(placeholder, shlex.quote(value))
                else:
                    cmd = cmd.replace(placeholder, str(value))

        return cmd

    def _process_output(self, output: str) -> Any:
        """
        Process the raw output of the tool into a structured format.
        Override this in subclasses for tool-specific output handling.
        """
        if not output:
            return None

        if self.output_format == "json":
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                self.log("Failed to parse JSON output", "error")
                return {"raw": output}
        else:
            # Default text processing
            return {"raw": output}

    async def cleanup(self):
        """Clean up resources, terminate any running processes."""
        if self.running_process:
            try:
                self.running_process.terminate()
                await asyncio.sleep(0.5)
                if self.running_process.returncode is None:
                    self.running_process.kill()
                self.log(f"Terminated running {self.tool_name} process")
            except Exception as e:
                self.log(f"Error terminating process: {str(e)}", "error")
