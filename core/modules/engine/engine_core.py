from logging import Logger

from core.modules.usecase import ModuleUseCase
from core.modules.util import LogUtil, FileSystem


class ModuleEngine:
    _logger: Logger

    def __init__(self, **args) -> None:
        self._logger = LogUtil.create(args["options"]["log_level"])
        self.use_case = ModuleUseCase(
            {
                "log_level": args["options"]["log_level"],
                "directory": FileSystem.get_modules_directory(),
            }
        )

    def start(self) -> None:
        self.__reload_modules()
        self.__invoke_on_modules("Q")

    def __reload_modules(self) -> None:
        """Reset the list of all modules and initiate the walk over the main
        provided module package to load all available modules
        """
        self.use_case.discover_modules(True)

    def __invoke_on_modules(self, command: chr):
        """Apply all of the modules on the argument supplied to this function"""
        for module in self.use_case.modules:
            module = self.use_case.register_module(module, self._logger)
            delegate = self.use_case.hook_module(module)
            device = delegate(command=command)
            self._logger.info(f"Loaded device: {device}")
