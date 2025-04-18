from logging import Logger
from typing import List, Dict, Any

from core.modules.engine import ModuleCore
from core.modules.models import Device, Meta
from core.modules.util.messagebus import MessageBus


class TemplateModule(ModuleCore):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)

        try:
            module_data = self.get_config()
            self.meta = Meta(
                name=module_data["name"],
                description=module_data["description"],
                version=module_data["version"],
            )
        except FileNotFoundError:
            self.meta = Meta(
                name="Template Module",
                description="This is a fallback description",
                version="0.1.0",
            )
            self._logger.error("module.yaml file not found. Using default values.")

        # Initialize storage for keywords
        self.keywords: List[str] = []
        self.processed_keywords: Dict[str, int] = {}

    def handle_input(self, data: Any) -> None:
        """
        Handle input data from subscribed topics.

        Args:
            data: Input data (expected to be List[str] of keywords)
        """
        if isinstance(data, list):
            self.keywords = data
            self._logger.info(f"Received {len(data)} keywords for processing")
            # Process keywords and assign priority scores
            self._process_keywords()
        else:
            self._logger.error(
                f"Received data of unexpected type: {type(data).__name__}"
            )

    def _process_keywords(self) -> None:
        """Process the keywords and assign priority scores."""
        self.processed_keywords = {}

        for i, keyword in enumerate(self.keywords):
            # Simple algorithm: assign priority based on keyword length and position
            priority = len(keyword) + (len(self.keywords) - i)
            self.processed_keywords[keyword] = priority

        self._logger.debug(
            f"Processed {len(self.processed_keywords)} keywords with priorities"
        )

    def run(self, messagebus: MessageBus) -> None:
        """
        Run the module's main logic and publish processed keywords if available.

        Args:
            messagebus: The message bus for inter-module communication
        """
        self._logger.info(f"Running {self.meta.name} module...")

        if self.processed_keywords:
            self._logger.info(
                f"Publishing {len(self.processed_keywords)} processed keywords"
            )
            messagebus.publish("processed_keywords", self.processed_keywords)

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name="Sample Device", firmware=0xA2C3F, protocol="SAMPLE", errors=[0x0000]
        )

    def invoke(self, command: chr) -> Device:
        """Handle commands from the module engine."""
        self._logger.debug(f"Command: {command} -> {self.meta}")

        # 'P' for process keywords
        if command == "P" and self.keywords:
            self._process_keywords()
            self._logger.info(
                f"Processed {len(self.processed_keywords)} keywords on demand"
            )

        device = self.__create_device()
        return device
