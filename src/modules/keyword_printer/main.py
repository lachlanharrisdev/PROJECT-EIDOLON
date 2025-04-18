from logging import Logger
from typing import List, Any

import yaml

from core.modules.engine import ModuleCore
from core.modules.models import Meta, Device
from core.modules.util.messagebus import MessageBus


class KeywordPrinterModule(ModuleCore):

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
                name="Default Module",
                description="This is a default module description.",
                version="0.0.0",
            )
            self._logger.error("module.yaml file not found. Using default values.")

        self._logger.debug(f"Module meta: {self.meta}")

        self.keywords = []

    def handle_input(self, data: Any):
        """
        Handle input data and print it to the console.
        Type checking will be performed by the MessageBus before this method is called.

        Args:
            data: The input data, expected to be a List[str] of keywords
        """
        if isinstance(data, list):
            self.keywords = data
            self._logger.info(
                f"\nI'm a keyword printer! I'm printing {len(data)} keywords: \n{data}\n"
            )
        else:
            self._logger.error(
                f"Received data of unexpected type: {type(data).__name__}"
            )

    def run(self, message_bus: MessageBus) -> None:
        """Run the module's main logic."""
        if self.keywords:
            self._logger.info(f"Currently tracking {len(self.keywords)} keywords")

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name="Sample Device", firmware=0xA2C3F, protocol="SAMPLE", errors=[0x0000]
        )

    def invoke(self, command: chr) -> Device:
        self._logger.debug(f"Command: {command} -> {self.meta}")
        device = self.__create_device()
        return device
