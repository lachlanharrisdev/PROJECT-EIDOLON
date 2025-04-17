from logging import Logger

from core.modules.engine import ModuleCore
from core.modules.models import Device


class SampleModule(ModuleCore):

    def __init__(self, logger: Logger) -> None:
        super().__init__(logger)

    @staticmethod
    def __create_device() -> Device:
        return Device(
            name="Sample Device", firmware=0xA2C3F, protocol="SAMPLE", errors=[0x0000]
        )

    def invoke(self, command: chr) -> Device:
        self._logger.debug(f"Command: {command} -> {self.meta}")
        device = self.__create_device()
        return device
