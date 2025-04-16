from logging import Logger

import yaml

from core.plugins.engine import PluginCore
from core.plugins.models import Meta, Device


class SamplePlugin(PluginCore):

    def __read_plugin_yaml(self) -> dict:
        with open("plugin.yaml", "r") as file:
            data = yaml.safe_load(file)
        return data

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)

        try:
            plugin_data = self.__read_plugin_yaml()
            self.meta = Meta(
                name=plugin_data["name"],
                description=plugin_data["description"],
                version=plugin_data["version"],
            )
        except FileNotFoundError:
            self.meta = Meta(
                name="Default Plugin",
                description="This is a default plugin description.",
                version="0.0.0",
            )
            self._logger.error("plugin.yaml file not found. Using default values.")

        self._logger.debug(f"Plugin meta: {self.meta}")

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name="Sample Device", firmware=0xA2C3F, protocol="SAMPLE", errors=[0x0000]
        )

    def invoke(self, command: chr) -> Device:
        self._logger.debug(f"Command: {command} -> {self.meta}")
        device = self.__create_device()
        return device
