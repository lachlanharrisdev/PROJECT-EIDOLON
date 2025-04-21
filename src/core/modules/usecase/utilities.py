import os
import subprocess
import sys

from logging import Logger
from subprocess import CalledProcessError
from typing import List, Dict, Optional

from importlib.metadata import distributions, PackageNotFoundError  # Updated import
from dacite import (
    from_dict,
    ForwardReferenceError,
    UnexpectedDataError,
    WrongTypeError,
    MissingValueError,
)

from core.modules.models import ModuleConfig, DependencyModule
from core.modules.util import FileSystem


class ModuleUtility:
    __IGNORE_LIST = ["__pycache__"]

    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._logger = logger

    @staticmethod
    def __filter_unwanted_directories(name: str) -> bool:
        return not ModuleUtility.__IGNORE_LIST.__contains__(name)

    @staticmethod
    def find_all_modules(base_directory: str) -> List[str]:
        """
        Recursively finds all module paths in the given base directory.
        A module is identified as a directory containing a module.yaml file.

        Args:
            base_directory: Root directory to start scanning for modules

        Returns:
            List of relative paths to modules (relative to base_directory)
        """
        result = []

        def scan_directory(current_path, relative_path=""):
            # Get all items in the current directory
            try:
                items = os.listdir(current_path)
                # Filter out unwanted items like __pycache__
                items = [
                    item
                    for item in items
                    if ModuleUtility.__filter_unwanted_directories(item)
                ]

                for item in items:
                    item_path = os.path.join(current_path, item)
                    item_relative_path = os.path.join(relative_path, item)

                    # If this is a directory, check if it's a module and scan it
                    if os.path.isdir(item_path):
                        # If it has module.yaml, it's a module
                        if os.path.exists(os.path.join(item_path, "module.yaml")):
                            result.append(item_relative_path)

                        # Continue scanning this directory for more modules
                        scan_directory(item_path, item_relative_path)
            except (PermissionError, FileNotFoundError) as e:
                # Skip directories we can't access
                pass

        # Start the recursive scan
        scan_directory(base_directory)
        return result

    @staticmethod
    def filter_modules_paths(modules_package) -> List[str]:
        """
        Filters out a list of unwanted directories (deprecated)
        Use find_all_modules instead for recursive discovery

        :param modules_package: Root path of modules directory
        :return: List of filtered directories
        """
        return ModuleUtility.find_all_modules(modules_package)

    @staticmethod
    def __get_missing_packages(
        installed: List[str], required: Optional[List[DependencyModule]]
    ) -> List[DependencyModule]:
        missing = list()
        if required is not None:
            for required_pkg in required:
                if required_pkg.name not in installed:
                    missing.append(required_pkg)
        return missing

    def __manage_requirements(self, package_name: str, module_config: ModuleConfig):
        installed_packages: List[str] = [
            dist.metadata["Name"] for dist in distributions()
        ]
        missing_packages = self.__get_missing_packages(
            installed_packages, module_config.requirements
        )
        for missing in missing_packages:
            self._logger.info(
                f"Preparing installation of module: {missing} for package: {package_name}"
            )
            try:
                python = sys.executable
                exit_code = subprocess.check_call(
                    [python, "-m", "pip", "install", missing.__str__()],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._logger.info(
                    f"Installation of module: {missing} for package: {package_name} was returned exit code: {exit_code}"
                )
            except CalledProcessError as e:
                self._logger.error(f"Unable to install package {missing}", e)

    def __read_configuration(self, module_path) -> Optional[ModuleConfig]:
        try:
            module_config_data = FileSystem.load_configuration(
                "module.yaml", module_path
            )

            # Extra safety check to ensure module_config_data is not None
            if not module_config_data:
                self._logger.error("Empty or invalid module configuration file")
                return None

            # Process requirements to extract version constraints
            if (
                "requirements" in module_config_data
                and module_config_data["requirements"]
            ):
                for req in module_config_data["requirements"]:
                    if "version" in req:
                        version = req["version"]
                        # Check if version has a constraint prefix like >=, ==, etc.
                        import re

                        match = re.match(r"([>=<~!]+)(.*)", version)
                        if match:
                            constraint, clean_version = match.groups()
                            req["constraint"] = constraint
                            req["version"] = clean_version
                        else:
                            # Default to exact version if no constraint is specified
                            req["constraint"] = "=="

            # Pre-process inputs and outputs to ensure they have the required fields
            if "inputs" in module_config_data and module_config_data["inputs"]:
                for input_item in module_config_data["inputs"]:
                    if "type" not in input_item:
                        input_item["type"] = "Any"  # Default type
                    if "type_name" not in input_item:
                        input_item["type_name"] = input_item[
                            "type"
                        ]  # Copy from type field

            if "outputs" in module_config_data and module_config_data["outputs"]:
                for output_item in module_config_data["outputs"]:
                    if "type" not in output_item:
                        output_item["type"] = "Any"  # Default type
                    if "type_name" not in output_item:
                        output_item["type_name"] = output_item[
                            "type"
                        ]  # Copy from type field

            module_config = from_dict(data_class=ModuleConfig, data=module_config_data)
            return module_config
        except FileNotFoundError as e:
            self._logger.error("Unable to read configuration file", e)
        except (
            NameError,
            ForwardReferenceError,
            UnexpectedDataError,
            WrongTypeError,
            MissingValueError,
        ) as e:
            self._logger.error(
                f"Unable to parse module configuration to data class: {e}"
            )
        return None

    def setup_module_configuration(self, package_name, module_path) -> Optional[str]:
        """
        Handles primary configuration for a given package and module
        :param package_name: package of the potential module
        :param module_path: path to the potential module (relative to modules directory)
        :return: a module name to import
        """
        self._logger.debug(f"Setting up module configuration for {module_path}")
        # Get the full path to the module
        full_module_path = os.path.join(FileSystem.get_modules_directory(), module_path)

        if os.path.isdir(full_module_path):
            self._logger.debug(
                f"Checking if configuration file exists for module: {module_path}"
            )
            module_config: Optional[ModuleConfig] = self.__read_configuration(
                full_module_path
            )
            if module_config is not None:
                self.__manage_requirements(package_name, module_config)
                return module_config.runtime.main
            else:
                self._logger.debug(
                    f"No configuration file exists for module: {module_path}"
                )
        self._logger.debug(
            f"Module: {module_path} is not a directory, skipping scanning phase"
        )
        return None
