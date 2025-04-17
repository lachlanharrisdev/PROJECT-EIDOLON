from logging import Logger
from typing import Optional, List

from core.modules.models import Meta, Device
from core.modules.util.messagebus import MessageBus

import yaml
import os
import inspect


class IModuleRegistry(type):
    module_registries: List[type] = list()

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
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
        self._config = None

    def get_config(self) -> dict:
        """
        Retrieve the module's configuration from the module.yaml file.
        :return: A dictionary containing the module's configuration.
        """
        if self._config is not None:
            return self._config  # Return cached config if already loaded

        # Dynamically determine the path to the module.yaml file
        module_dir = os.path.dirname(inspect.getfile(self.__class__))
        config_path = os.path.join(module_dir, "module.yaml")

        try:
            with open(config_path, "r") as file:
                self._config = yaml.safe_load(file)
                return self._config
        except FileNotFoundError:
            self._logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            self._logger.error(f"Error parsing configuration file: {e}")
            raise

    def invoke(self, **args) -> Device:
        """
        Starts main module flow
        :param args: possible arguments for the module
        :return: a device for the module
        """
        pass

    def handle_input(self, data):
        """Handle input data from the message bus."""
        pass

    def run(self, message_bus: MessageBus):
        """Run the module's main logic."""
        pass
