from logging import Logger
from typing import List, Dict, Any
import asyncio

from core.modules.engine import ModuleCore
from core.modules.models import Device
from core.modules.util.messagebus import MessageBus


class TemplateModule(ModuleCore):
    """
    Template module that demonstrates the use of the enhanced ModuleCore functionality.
    This module processes input data and publishes results to the message bus.
    """

    def _initialize_module(self) -> None:
        """
        Initialize module-specific components.
        Called after the base ModuleCore initialization.
        """
        self.keywords: List[str] = []
        self.processed_keywords: Dict[str, int] = {}

    async def _before_run(self, message_bus: MessageBus) -> None:
        """
        Execute setup code before the main module loop starts.
        """
        self._logger.info(f"Setting up {self.meta.name} module...")
        # Any pre-run setup can go here

    async def _run_iteration(self, message_bus: MessageBus) -> None:
        """
        A single iteration of the module's main logic.
        This is called periodically by the ModuleCore's run method.
        """
        if self.keywords:
            self._process_keywords()

            if self.processed_keywords:
                self._logger.info(
                    f"Publishing {len(self.processed_keywords)} processed keywords"
                )
                await message_bus.publish("processed_keywords", self.processed_keywords)

    def _process_keywords(self) -> None:
        """
        Process the keywords and assign priority scores.
        This is an example of module-specific business logic.
        """
        self.processed_keywords = {}

        for keyword in self.keywords:
            # Simple example: score is based on length
            score = len(keyword)
            self.processed_keywords[keyword] = score

        self._logger.debug(f"Processed {len(self.keywords)} keywords")

    def _process_input(self, data: Any) -> None:
        """
        Process input data from the message bus.
        Override of the ModuleCore _process_input method.
        """
        if isinstance(data, list) and all(isinstance(item, str) for item in data):
            self.keywords = data
            self._logger.info(f"Received {len(data)} keywords")
        else:
            self._logger.warning(f"Received data of unexpected type: {type(data)}")

    def _get_cycle_time(self) -> float:
        """
        Get the time between execution cycles.
        """
        return 10.0  # Run every 10 seconds

    def _get_default_output_topic(self) -> str:
        """
        Get the default output topic for this module.
        """
        return "processed_keywords"

    def _handle_custom_command(self, command: chr) -> Device:
        """
        Handle custom module commands.
        """
        if command == "C":
            # Example custom command to clear keywords
            self.keywords = []
            self._logger.info("Keywords cleared")
            return Device(
                name=self.meta.name, firmware=0xB0000, protocol="CUSTOM", errors=[]
            )

        return super()._handle_custom_command(command)
