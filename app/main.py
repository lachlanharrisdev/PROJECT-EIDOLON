import asyncio
import yaml
from logging import Logger, basicConfig, getLogger
from app.scheduler import schedule_task
from core.analysis.keyword_monitor import async_refresh_political_keywords
from core.plugins.engine import PluginEngine
from core.plugins.util import LogUtil


def load_configuration(config_path: str) -> dict:
    """
    Load the configuration from the YAML file.
    """
    with open(config_path, "r") as file:
        return yaml.safe_load(file)


class Main:
    _logger: Logger

    def __init__(self, **args) -> None:
        # Load configuration
        config = load_configuration("settings/configuration.yaml")
        log_level = config["logging"]["level"]

        # Set up logging
        basicConfig(level=log_level)
        self._logger = getLogger(__name__)

        # Initialize the PluginEngine with the correct log level
        self._plugin_engine = PluginEngine(options={"log_level": log_level})

    async def main(self) -> None:
        """
        Main entry point for the application.
        Runs the dynamic keyword detection engine periodically and loads plugins.
        """
        self._logger.info("Starting Project Eidolon...")

        # Load plugins
        self._logger.info("Loading plugins...")
        self._plugin_engine.start()

        # Schedule the keyword refresh task to run every hour
        await schedule_task(async_refresh_political_keywords, interval=3600)


if __name__ == "__main__":
    app = Main()
    asyncio.run(app.main())
