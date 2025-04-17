import os
from importlib import import_module
import logging
from typing import List, Any, Dict

from core.modules.engine import IModuleRegistry, ModuleCore
from core.modules.util import LogUtil
from .utilities import ModuleUtility


class ModuleUseCase:
    modules: List[type]

    def __init__(self, options: Dict) -> None:
        self._logger = logging.getLogger(__name__)
        self.modules_package: str = options["directory"]
        self.module_util = ModuleUtility(self._logger)
        self.modules = list()

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
                    module_instance = latest_module(self._logger)
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

    def __search_for_modules_in(self, modules_path: List[str], package_name: str):
        for directory in modules_path:
            entry_point = self.module_util.setup_module_configuration(
                package_name, directory
            )
            if entry_point is not None:
                module_name, module_ext = os.path.splitext(entry_point)
                # Construct the full import path relative to the modules_package
                relative_path = os.path.relpath(directory, self.modules_package)
                normalized_path = relative_path.replace(os.sep, ".").strip(".")
                import_target_module = f"{package_name}.{normalized_path}.{module_name}"
                self._logger.debug(f"Importing module: {import_target_module}")
                try:
                    module = import_module(import_target_module)
                    self.__check_loaded_module_state(module)
                    # Pass module alias for verification
                    module.alias = os.path.basename(directory)
                except ModuleNotFoundError as e:
                    self._logger.error(
                        f"Failed to import module {import_target_module}: {e}"
                    )
            else:
                self._logger.debug(f"No valid module found in {directory}")

    def discover_modules(self, reload: bool):
        """
        Discover the module classes contained in Python files, given a
        list of directory names to scan.
        """
        if reload:
            self.clear_modules()
            self._logger.debug(
                f"Searching for modules under package {self.modules_package}"
            )
            modules_path = ModuleUtility.filter_modules_paths(self.modules_package)
            package_name = os.path.basename(os.path.normpath(self.modules_package))
            self.__search_for_modules_in(modules_path, package_name)

    def discover_module(self, module_path: str):
        """
        Discover a specific module by its directory name.
        """
        self.clear_modules()
        specific_path = os.path.join(self.modules_package, module_path)
        if os.path.isdir(specific_path):
            self.__search_for_modules_in(
                [specific_path], os.path.basename(self.modules_package)
            )
        else:
            self._logger.error(f"Module path {module_path} is not a directory")

    def clear_modules(self):
        """
        Clear the loaded modules.
        """
        self.modules.clear()
        IModuleRegistry.module_registries.clear()

    def load_module(
        self, module_path: str, loaded_modules: set, dependencies: bool = False
    ):
        """
        Load a module and its dependencies recursively based on its directory name.
        :param module_path: The directory name of the module to load.
        :param loaded_modules: A set to track already loaded modules to avoid circular dependencies.
        :param dependencies: Whether to load dependencies of the module.
        """
        self._logger.debug(f"Attempting to load module: {module_path}")
        if module_path in loaded_modules:
            return  # Avoid circular dependencies

        modules_directory = self.modules_package
        module_folder_path = os.path.join(modules_directory, module_path)

        # Ensure the directory exists
        if not os.path.isdir(module_folder_path):
            self._logger.error(f"Module directory {module_path} not found")
            return

        # Check for the presence of a valid module.yaml file
        config_path = os.path.join(module_folder_path, "module.yaml")
        if not os.path.isfile(config_path):
            self._logger.error(f"Missing module.yaml in module directory {module_path}")
            return

        # Resolve the module instance by its alias
        target_module = next(
            (
                module
                for module in self.modules
                if getattr(module, "alias", None) == module_path
            ),
            None,
        )
        if target_module:
            self._logger.debug(
                f"Module {module_path} already registered, skipping instantiation"
            )
            loaded_modules.add(module_path)
            return

        if not target_module:
            self._logger.error(f"Module {module_path} not found in loaded modules")
            return

        loaded_modules.add(module_path)
        self._logger.debug(f"Module {module_path} loaded successfully")

        # If dependencies are enabled, recursively load dependent modules
        if dependencies:
            config = target_module.get_config()
            inputs = config.get("inputs", [])

            for input_item in inputs:
                input_topic = input_item["name"]
                for module in self.modules:
                    module_config = module.get_config()
                    outputs = module_config.get("outputs", [])
                    for output in outputs:
                        if output["name"] == input_topic:
                            self.load_module(module.alias, loaded_modules, True)

        return loaded_modules

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
