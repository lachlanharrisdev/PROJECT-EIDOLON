import asyncio
import sys
import yaml
from logging import Logger, StreamHandler, getLogger


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
        config = load_configuration("src/settings/configuration.yaml")
        log_level = config["logging"]["level"]

        # Initialize the ModuleEngine with the correct log level
        self._module_engine = ModuleEngine(options={"log_level": log_level})

    async def main(self) -> None:
        """
        Main entry point for the application.
        Runs the dynamic keyword detection engine periodically and loads modules.
        """
        self._logger.info("Starting Project Eidolon...")

        # Load and run modules asynchronously
        self._logger.info("Loading and starting modules asynchronously...")
        await self._module_engine.start()

        self._logger.info("Project Eidolon shutdown complete.")


def main():
    # Configure logging
    logger = configure_logging()

    # Ensure all log messages are sent to stderr
    for handler in logger.handlers:
        if isinstance(handler, StreamHandler):
            handler.stream = sys.stderr

    try:
        # Initialize the application
        app = Main(logger)
        asyncio.run(app.main())
        sys.exit(0)  # Exit with zero exit code on success
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        sys.exit(0)  # Clean exit on keyboard interrupt
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)  # Exit with non-zero exit code on failure


if __name__ == "__main__":
    main()
