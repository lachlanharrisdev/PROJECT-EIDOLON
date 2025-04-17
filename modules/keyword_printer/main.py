from logging import Logger

import yaml

from core.modules.engine import ModuleCore
from core.modules.models import Meta, Device


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

    def handle_input(self, data):
        """
        Handle input data and print it to the console.
        :param data: The input data to handle.
        """
        self._logger.info(f"I'm a keyword printer! I'm printing: {data}")
        print(data)

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name="Sample Device", firmware=0xA2C3F, protocol="SAMPLE", errors=[0x0000]
        )

    def invoke(self, command: chr) -> Device:
        self._logger.debug(f"Command: {command} -> {self.meta}")
        device = self.__create_device()
        return device
