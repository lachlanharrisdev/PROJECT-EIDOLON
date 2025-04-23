import logging
import os
import sys
from logging import Logger, StreamHandler, DEBUG
from typing import Union, Optional

import yaml


class FileSystem:

    @staticmethod
    def __get_base_dir():
        """Get the base directory of the project."""
        # Check if running inside a package (installed) vs. source
        if getattr(sys, "frozen", False) or "__file__" not in globals():
            # Running as executable or in an environment where __file__ is not defined
            # Try to find site-packages or use current working directory as fallback
            try:
                # This assumes the installed package structure
                import core

                return os.path.abspath(
                    os.path.join(os.path.dirname(core.__file__), "..")
                )
            except ImportError:
                # Fallback if 'core' isn't found (e.g., during build?)
                return os.getcwd()
        else:
            # Running from source
            current_path = os.path.abspath(os.path.dirname(__file__))
            return os.path.abspath(os.path.join(current_path, "../../../"))

    @staticmethod
    def __get_config_directory() -> str:
        # Config directory is usually relative to the source structure or installation
        # For simplicity, let's assume it's always relative to the base dir found
        base_dir = FileSystem.__get_base_dir()
        # Check if running from source structure
        src_settings = os.path.join(base_dir, "src", "settings")
        if os.path.isdir(src_settings):
            return src_settings
        # Fallback to settings directory directly under base (might be installed structure)
        installed_settings = os.path.join(base_dir, "settings")
        if os.path.isdir(installed_settings):
            return installed_settings
        # Last resort: relative to current file (less reliable)
        current_path = os.path.abspath(os.path.dirname(__file__))
        fallback_settings = os.path.abspath(
            os.path.join(current_path, "../../settings")
        )
        return fallback_settings

    @staticmethod
    def get_modules_directory() -> str:
        """Get the absolute path to the modules directory, checking environment variable first."""
        env_module_dir = os.environ.get("MODULE_DIR")
        if env_module_dir:
            return env_module_dir
        # Fallback logic if env var not set
        base_dir = FileSystem.__get_base_dir()
        src_modules = os.path.join(base_dir, "src", "modules")
        if os.path.isdir(src_modules):
            return src_modules
        installed_modules = os.path.join(base_dir, "modules")
        if os.path.isdir(installed_modules):
            return installed_modules
        current_path = os.path.abspath(os.path.dirname(__file__))
        fallback_modules = os.path.abspath(os.path.join(current_path, "../../modules"))
        return fallback_modules

    @staticmethod
    def get_pipelines_directory() -> str:
        """Get the absolute path to the pipelines directory, checking environment variable first."""
        env_pipeline_dir = os.environ.get("PIPELINE_DIR")
        if env_pipeline_dir:
            return env_pipeline_dir
        # Fallback logic if env var not set
        base_dir = FileSystem.__get_base_dir()
        src_pipelines = os.path.join(base_dir, "src", "pipelines")
        if os.path.isdir(src_pipelines):
            return src_pipelines
        installed_pipelines = os.path.join(base_dir, "pipelines")
        if os.path.isdir(installed_pipelines):
            return installed_pipelines
        current_path = os.path.abspath(os.path.dirname(__file__))
        fallback_pipelines = os.path.abspath(
            os.path.join(current_path, "../../pipelines")
        )
        return fallback_pipelines

    @staticmethod
    def load_configuration(
        name: str = "configuration.yaml", config_directory: Optional[str] = None
    ) -> dict:
        if config_directory is None:
            config_directory = FileSystem.__get_config_directory()
        with open(os.path.join(config_directory, name)) as file:
            input_data = yaml.safe_load(file)

        # Dictionary should always be returned, including empty
        if input_data is None:
            return {}

        return input_data


class LogUtil(Logger):
    __FORMATTER = (
        "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s"
    )

    def __init__(
        self,
        name: str,
        log_format: str = __FORMATTER,
        level: Union[int, str] = DEBUG,
        *args,
        **kwargs
    ) -> None:
        super().__init__(name, level)
        self.formatter = logging.Formatter(log_format)
        self.addHandler(self.__get_stream_handler())

    def __get_stream_handler(self) -> StreamHandler:
        handler = StreamHandler(sys.stdout)
        handler.setFormatter(self.formatter)
        return handler

    @staticmethod
    def create(log_level: str = "DEBUG") -> Logger:
        logging.setLoggerClass(LogUtil)
        logger = logging.getLogger("module.architecture")
        logger.setLevel(log_level)
        return logger
