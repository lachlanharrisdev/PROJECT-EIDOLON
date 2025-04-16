from logging import Logger

from core.plugins.usecase import PluginUseCase
from core.plugins.util import LogUtil, FileSystem


class PluginEngine:
    _logger: Logger

    def __init__(self, **args) -> None:
        self._logger = LogUtil.create(args["options"]["log_level"])
        self.use_case = PluginUseCase(
            {
                "log_level": args["options"]["log_level"],
                "directory": FileSystem.get_plugins_directory(),
            }
        )

    def start(self) -> None:
        self.__reload_plugins()
        self.__invoke_on_plugins("Q")

    def __reload_plugins(self) -> None:
        """Reset the list of all plugins and initiate the walk over the main
        provided plugin package to load all available plugins
        """
        self.use_case.discover_plugins(True)

    def __invoke_on_plugins(self, command: chr):
        """Apply all of the plugins on the argument supplied to this function"""
        for module in self.use_case.modules:
            plugin = self.use_case.register_plugin(module, self._logger)
            delegate = self.use_case.hook_plugin(plugin)
            device = delegate(command=command)
            self._logger.info(f"Loaded device: {device}")
