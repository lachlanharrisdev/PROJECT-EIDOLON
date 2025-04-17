import asyncio
import yaml
from logging import Logger, basicConfig, getLogger

from core.modules.engine import ModuleEngine
from core.util.logging import configure_logging


def load_configuration(config_path: str) -> dict:
    """
    Load the configuration from the YAML file.
    """
    with open(config_path, "r") as file:
        return yaml.safe_load(file)


class Main:
    _logger: Logger

    def __init__(self, logger: Logger, **args) -> None:
        self._logger = logger

        # Load configuration
        config = load_configuration("settings/configuration.yaml")
        log_level = config["logging"]["level"]

        # Initialize the ModuleEngine with the correct log level
        self._module_engine = ModuleEngine(options={"log_level": log_level})

    async def main(self) -> None:
        """
        Main entry point for the application.
        Runs the dynamic keyword detection engine periodically and loads modules.
        """
        self._logger.info("Starting Project Eidolon...")

        # Load modules
        self._logger.info("Loading modules...")
        self._module_engine.start()


def main():
    # Configure logging
    logger = configure_logging()

    # Initialize the application
    app = Main(logger)
    asyncio.run(app.main())


if __name__ == "__main__":
    main()
