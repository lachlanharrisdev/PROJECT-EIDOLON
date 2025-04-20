import os
from importlib import import_module
import logging
from typing import List, Any, Dict, Optional, Set

from core.modules.engine import IModuleRegistry, ModuleCore
from core.modules.models import Pipeline
from core.modules.util import LogUtil
from .utilities import ModuleUtility


class ModuleUseCase:
    modules: List[type]

    def __init__(self, options: Dict) -> None:
        self._logger = logging.getLogger(__name__)
        self.modules_package: str = options["directory"]
        self.module_util = ModuleUtility(self._logger)
        self.modules = list()
        self.thread_pool = options.get("thread_pool", None)

    def __check_loaded_module_state(self, module: Any):
        """
        Check the state of the loaded module and instantiate it.
        """
        if len(IModuleRegistry.module_registries) > 0:
            latest_module = IModuleRegistry.module_registries[-1]
            latest_module_name = latest_module.__module__
            current_module_name = module.__name__

            if current_module_name == latest_module_name:
                self._logger.debug(
                    f"Successfully imported module `{current_module_name}`"
                )

                # Instantiate the module and add it to the list
                try:
                    module_instance = latest_module(self._logger, self.thread_pool)
                    self.modules.append(module_instance)
                    self._logger.debug(
                        f"Module `{current_module_name}` registered successfully"
                    )
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
            self._logger.error(f"No module found in registry for module: {module}")

    def __search_for_modules_in(
        self,
        modules_path: List[str],
        package_name: str,
        allowed_modules: Optional[Set[str]] = None,
    ):
        for directory in modules_path:
            # For modules in the pipeline, we need to match only the module name,
            # not the full path including subdirectories
            module_name = os.path.basename(directory)

            # Skip directories not in allowed_modules if specified
            if allowed_modules is not None and module_name.lower() not in {
                mod.lower() for mod in allowed_modules
            }:
                self._logger.debug(
                    f"Skipping module {module_name} (in {directory}) as it's not in the pipeline"
                )
                continue

            entry_point = self.module_util.setup_module_configuration(
                package_name, directory
            )
            if entry_point is not None:
                module_file, module_ext = os.path.splitext(entry_point)
                # Construct the full import path relative to the modules_package
                import_path = os.path.join(directory, module_file)
                normalized_path = import_path.replace(os.sep, ".")
                import_target_module = f"{package_name}.{normalized_path}"

                self._logger.debug(f"Importing module: {import_target_module}")
                try:
                    module = import_module(import_target_module)
                    self.__check_loaded_module_state(module)
                    # Pass module basename as alias for verification
                    module.alias = module_name
                except ModuleNotFoundError as e:
                    self._logger.error(
                        f"Failed to import module {import_target_module}: {e}"
                    )
            else:
                self._logger.debug(f"No valid module found in {directory}")

    def discover_modules(
        self, reload: bool, pipeline: Optional[Pipeline] = None, thread_pool=None
    ):
        """
        Discover the module classes contained in Python files, given a
        list of directory names to scan.

        :param reload: Whether to reload modules or use cached versions
        :param pipeline: Optional pipeline configuration to filter modules
        :param thread_pool: Optional thread pool to pass to modules
        """
        # Update thread_pool if provided
        if thread_pool is not None:
            self.thread_pool = thread_pool

        if reload:
            self.clear_modules()
            self._logger.debug(
                f"Searching for modules under package {self.modules_package}"
            )
            modules_path = ModuleUtility.filter_modules_paths(self.modules_package)
            package_name = os.path.basename(os.path.normpath(self.modules_package))

            # If pipeline is provided, only load modules specified in the pipeline
            allowed_modules = None
            if pipeline:
                allowed_modules = {module.name for module in pipeline.modules}
                self._logger.info(
                    f"Loading only modules specified in pipeline '{pipeline.name}': {', '.join(allowed_modules)}"
                )

            self.__search_for_modules_in(modules_path, package_name, allowed_modules)

    def clear_modules(self):
        """
        Clear the loaded modules.
        """
        self.modules.clear()
        IModuleRegistry.module_registries.clear()

    @staticmethod
    def register_module(module: type, logger: logging.Logger) -> ModuleCore:
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
