from logging import Logger

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

    def run(self, messagebus: MessageBus) -> None:
        self._logger.info(f"Running {self.meta.name} module...")

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name="Sample Device", firmware=0xA2C3F, protocol="SAMPLE", errors=[0x0000]
        )

    def invoke(self, command: chr) -> Device:
        self._logger.debug(f"Command: {command} -> {self.meta}")
        device = self.__create_device()
        return device
