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
    def filter_modules_paths(modules_package) -> List[str]:
        """
        filters out a list of unwanted directories
        :param modules_package:
        :return: list of directories
        """
        paths = list(
            filter(
                ModuleUtility.__filter_unwanted_directories, os.listdir(modules_package)
            )
        )
        print(f"Filtered module paths: {paths}")  # Debug logging
        return paths

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

    def setup_module_configuration(self, package_name, module_name) -> Optional[str]:
        """
        Handles primary configuration for a give package and module
        :param package_name: package of the potential module
        :param module_name: module of the potential module
        :return: a module name to import
        """
        self._logger.debug(f"Setting up module configuration for {module_name}")
        # if the item has not folder we will assume that it is a directory
        module_path = os.path.join(FileSystem.get_modules_directory(), module_name)
        if os.path.isdir(module_path):
            self._logger.debug(
                f"Checking if configuration file exists for module: {module_name}"
            )
            module_config: Optional[ModuleConfig] = self.__read_configuration(
                module_path
            )
            if module_config is not None:
                self.__manage_requirements(package_name, module_config)
                return module_config.runtime.main
            else:
                self._logger.debug(
                    f"No configuration file exists for module: {module_name}"
                )
        self._logger.debug(
            f"Module: {module_name} is not a directory, skipping scanning phase"
        )
        return None
