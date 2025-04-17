import os
from importlib import import_module
from logging import Logger
from typing import List, Any, Dict

from core.modules.engine import IModuleRegistry, ModuleCore
from core.modules.util import LogUtil
from .utilities import ModuleUtility


class ModuleUseCase:
    _logger: Logger
    modules: List[type]

    def __init__(self, options: Dict) -> None:
        self._logger = LogUtil.create(options["log_level"])
        self.modules_package: str = options["directory"]
        self.module_util = ModuleUtility(self._logger)
        self.modules = list()

    def __check_loaded_module_state(self, module_module: Any):
        """
        Check the state of the loaded module and instantiate it.
        """
        if len(IModuleRegistry.module_registries) > 0:
            latest_module = IModuleRegistry.module_registries[-1]
            latest_module_name = latest_module.__module__
            current_module_name = module_module.__name__

            if current_module_name == latest_module_name:
                self._logger.debug(
                    f"Successfully imported module `{current_module_name}`"
                )

                # Instantiate the module and add it to the list
                try:
                    module_instance = latest_module(self._logger)
                    self.modules.append(module_instance)
                except TypeError as e:
                    self._logger.error(
                        f"Failed to instantiate module `{current_module_name}`: {e}"
                    )
            else:
                self._logger.error(
                    f"Expected to import -> `{current_module_name}` but got -> `{latest_module_name}`"
                )

            # Clear modules from the registry when we're done with them
            IModuleRegistry.module_registries.clear()
        else:
            self._logger.error(
                f"No module found in registry for module: {module_module}"
            )

    def __search_for_modules_in(self, modules_path: List[str], package_name: str):
        for directory in modules_path:
            entry_point = self.module_util.setup_module_configuration(
                package_name, directory
            )
            if entry_point is not None:
                module_name, module_ext = os.path.splitext(entry_point)
                import_target_module = f".{directory}.{module_name}"
                module = import_module(import_target_module, package_name)
                self.__check_loaded_module_state(module)
                # Pass module alias for verification
                module.alias = directory
            else:
                self._logger.debug(f"No valid module found in {package_name}")

    def discover_modules(self, reload: bool):
        """
        Discover the module classes contained in Python files, given a
        list of directory names to scan.
        """
        if reload:
            self.modules.clear()
            IModuleRegistry.module_registries.clear()
            self._logger.debug(
                f"Searching for modules under package {self.modules_package}"
            )
            modules_path = ModuleUtility.filter_modules_paths(self.modules_package)
            package_name = os.path.basename(os.path.normpath(self.modules_package))
            self.__search_for_modules_in(modules_path, package_name)

    @staticmethod
    def register_module(module: type, logger: Logger) -> ModuleCore:
        """
        Create a module instance from the given module
        :param module: module to initialize
        :param logger: logger for the module to use
        :return: a high level module
        """
        return module(logger)

    @staticmethod
    def hook_module(module: ModuleCore):
        """
        Return a function accepting commands.
        """
        return module.invoke
