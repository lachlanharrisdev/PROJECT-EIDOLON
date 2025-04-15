from logging import Logger
from typing import Optional, List

from core.plugins.models import Meta, Device


class IPluginRegistry(type):
    plugin_registries: List[type] = list()

    def __init__(cls, name, bases, attrs):
        super().__init__(cls)
        if name != "PluginCore":
            IPluginRegistry.plugin_registries.append(cls)


class PluginCore(object, metaclass=IPluginRegistry):
    meta: Optional[Meta]

    def __init__(self, logger: Logger) -> None:
        """
        Entry init block for plugins
        :param logger: logger that plugins can make use of
        """
        self._logger = logger

    def invoke(self, **args) -> Device:
        """
        Starts main plugin flow
        :param args: possible arguments for the plugin
        :return: a device for the plugin
        """
        pass
