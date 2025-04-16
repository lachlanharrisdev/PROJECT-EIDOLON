from logging import Logger
from typing import Optional, List

from core.modules.models import Meta, Device


class IModuleRegistry(type):
    module_registries: List[type] = list()

    def __init__(cls, name, bases, attrs):
        super().__init__(cls)
        if name != "ModuleCore":
            IModuleRegistry.module_registries.append(cls)


class ModuleCore(object, metaclass=IModuleRegistry):
    meta: Optional[Meta]

    def __init__(self, logger: Logger) -> None:
        """
        Entry init block for modules
        :param logger: logger that modules can make use of
        """
        self._logger = logger

    def invoke(self, **args) -> Device:
        """
        Starts main module flow
        :param args: possible arguments for the module
        :return: a device for the module
        """
        pass
