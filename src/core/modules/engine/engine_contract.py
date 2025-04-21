from logging import Logger
from typing import Optional, List, Dict, Any, Callable
import asyncio
import inspect
import os
import yaml
import traceback
from datetime import datetime

from core.modules.models import Meta, Device
from core.modules.util.messagebus import MessageBus


class IModuleRegistry(type):
    module_registries: List[type] = list()

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if name != "ModuleCore":
            IModuleRegistry.module_registries.append(cls)


class ModuleCore(object, metaclass=IModuleRegistry):
    """
    Base class for all modules in Project Eidolon.

    This class provides standard implementations for common module functionality,
    allowing module developers to focus on implementing module-specific logic.

    Core lifecycle methods to override in your modules:
    - init(): For initialization code (instead of overriding __init__)
    - process(data): Process incoming data from subscribed topics
    - execute(message_bus): Execute one iteration of module logic
    - cleanup(): Release resources when module is shutting down
    """

    # ---------------
    # NON-OVERRIDABLE METHODS
    # ---------------

    meta: Optional[Meta]

    def __init__(self, logger: Logger, thread_pool) -> None:
        self._logger = logger
        self._running = False
        self._thread_pool = thread_pool
        self._arguments = {}  # Arguments from pipeline configuration
        self._config = None  # Cache for module configuration
        self._shutdown_event = asyncio.Event()
        self._run_mode = "once"  # Modes: once, loop, reactive
        self._is_completed = False

        # Reactive mode state
        self._is_processing = False
        self._input_received = False
        self._processing_lock = asyncio.Lock()

        # Load metadata from module.yaml
        try:
            config_path = os.path.join(
                os.path.dirname(inspect.getfile(self.__class__)), "module.yaml"
            )
            with open(config_path, "r", encoding="utf-8") as file:
                config_data = yaml.safe_load(file)
                self._config = config_data
                self.meta = Meta(
                    name=config_data.get("name", self.__class__.__name__),
                    description=config_data.get("description", "No description"),
                    version=config_data.get("version", "0.0.0"),
                )
        except FileNotFoundError:
            self.meta = Meta(
                name=self.__class__.__name__,
                description="Module configuration not found",
                version="0.0.0",
            )
            self._logger.warning(
                f"module.yaml file not found for {self.__class__.__name__}. Using default values."
            )
        except Exception as e:
            self.meta = Meta(
                name=self.__class__.__name__,
                description="Error loading module configuration",
                version="0.0.0",
            )
            self._logger.error(f"Failed to load module configuration: {e}")

        # Initialize module-specific state
        self.init()

    def get_config(self) -> dict:
        """
        Retrieve the module's configuration from the module.yaml file.
        """
        if self._config is not None:
            return self._config

        module_dir = os.path.dirname(inspect.getfile(self.__class__))
        config_path = os.path.join(module_dir, "module.yaml")

        try:
            with open(config_path, "r") as file:
                self._config = yaml.safe_load(file)
                return self._config
        except FileNotFoundError:
            self._logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            self._logger.error(f"Error parsing configuration file: {e}")
            raise

    def handle_input(self, data: Any) -> None:
        """
        Handle input data from the message bus.
        """
        try:
            self.process(data)

            # Signal that new input has been received (for reactive mode)
            if self._run_mode == "reactive":
                self._input_received = True
        except Exception as e:
            self._logger.error(f"Error handling input in {self.meta.name}: {e}")
            self._logger.debug(traceback.format_exc())

    async def run(self, message_bus: MessageBus) -> None:
        """
        Run the module's main logic asynchronously.
        This core run loop manages the module lifecycle.
        """
        self._running = True

        try:
            # Module startup
            await self._before_run(message_bus)

            # Handle different run modes
            if self._run_mode == "once":
                try:
                    await self.execute(message_bus)
                    self._is_completed = True
                except Exception as e:
                    self._logger.error(f"Error in {self.meta.name} execution: {e}")
                    self._logger.debug(traceback.format_exc())
                    self._is_completed = True

            elif self._run_mode == "reactive":
                await self._reactive_loop(message_bus)

            else:  # "loop" mode
                while not self._shutdown_event.is_set():
                    try:
                        await self.execute(message_bus)

                        # Wait before next cycle
                        try:
                            await asyncio.wait_for(
                                self._shutdown_event.wait(),
                                timeout=self.cycle_time(),
                            )
                        except asyncio.TimeoutError:
                            # Normal timeout, continue to next cycle
                            pass
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        self._logger.error(f"Error in {self.meta.name} cycle: {e}")
                        self._logger.debug(traceback.format_exc())

            # Module cleanup
            await self._after_run(message_bus)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Fatal error in {self.meta.name} module: {e}")
            self._logger.debug(traceback.format_exc())
        finally:
            self._running = False

    async def _before_run(self, message_bus: MessageBus) -> None:
        # Internal method
        pass

    async def _after_run(self, message_bus: MessageBus) -> None:
        # Internal method
        await self.cleanup()

    async def shutdown(self):
        """
        Gracefully shut down the module.
        """
        if self._running:
            self._logger.info(f"Shutting down module {self.meta.name}")
            self._shutdown_event.set()
            try:
                await self.cleanup()
            except Exception as e:
                self._logger.error(f"Error during {self.meta.name} shutdown: {e}")

    def default_output_topic(self) -> Optional[str]:
        """
        Get the default output topic for this module.

        Returns:
            The default output topic name or None
        """
        # Get the first output from module.yaml
        if self._config and "outputs" in self._config and self._config["outputs"]:
            if isinstance(self._config["outputs"], list) and self._config["outputs"]:
                return self._config["outputs"][0].get("name")
        return None

    def log(self, message: str, log_level: str = "info") -> None:
        """
        Log a message with the specified log level.
        """
        if hasattr(self._logger, log_level):
            getattr(self._logger, log_level)(f"[{self.meta.name}] {message}")
        else:
            self._logger.debug(f"Invalid log level '{log_level}' specified")

    def set_module_arguments(self, arguments: dict) -> None:
        """
        Set module arguments from the pipeline.
        """
        self._arguments = arguments or {}
        # Set args attribute for direct access via self.args
        self.args = self._arguments

    def get_arguments(self) -> dict:
        """
        Get the module arguments set from the pipeline.
        """
        return self._arguments

    def get_argument(self, key: str, default: Any = None) -> Any:
        """
        Get a specific argument value with fallback to default.
        """
        return self._arguments.get(key, default)

    async def _reactive_loop(self, message_bus: MessageBus) -> None:
        """Internal reactive processing loop that processes input as it arrives."""
        # Initial run if needed
        if hasattr(self, "input_data") and self.input_data:
            try:
                async with self._processing_lock:
                    self._is_processing = True
                    await self.execute(message_bus)
                    self._is_processing = False
            except Exception as e:
                self._logger.error(
                    f"Error in {self.meta.name} reactive processing: {e}"
                )
                self._logger.debug(traceback.format_exc())
                self._is_processing = False

        # Main reactive loop
        while not self._shutdown_event.is_set():
            if self._input_received:
                try:
                    async with self._processing_lock:
                        self._input_received = False
                        self._is_processing = True
                        await self.execute(message_bus)
                        self._is_processing = False
                except Exception as e:
                    self._logger.error(
                        f"Error in {self.meta.name} reactive processing: {e}"
                    )
                    self._logger.debug(traceback.format_exc())
                    self._is_processing = False
            else:
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=0.1)
                except asyncio.TimeoutError:
                    # Just a timeout check
                    pass

    # ----------------
    # ABSTRACT METHODS
    # ----------------

    def init(self) -> None:
        """
        Initialize module-specific state.
        Override this method instead of __init__ for module-specific initialization.
        """
        pass

    def process(self, data: Any) -> None:
        """
        Process input data received from subscribed topics.
        Override this method to handle incoming data.

        Args:
            data: Data received from a subscribed topic
        """
        if isinstance(data, dict):
            self.input_data = data
        else:
            self._logger.error(f"Received unexpected data type: {type(data)}")

    async def execute(self, message_bus: MessageBus) -> None:
        """
        Execute one iteration of module logic.
        Override this method to implement the core functionality of your module.

        Args:
            message_bus: The message bus for publishing results
        """
        # Default implementation just processes current input data
        if hasattr(self, "input_data") and self.input_data:
            result = self.transform()
            if result:
                output_topic = self.default_output_topic()
                if output_topic:
                    await message_bus.publish(output_topic, result)

    def transform(self) -> Any:
        """
        Transform the current input data into output data.
        Override this method to implement data transformation logic.

        Returns:
            Transformed data to be published, or None if no publishing should occur
        """
        return None

    def cycle_time(self) -> float:
        """
        Get the time in seconds between module execution cycles.
        Override this method to customize the cycle time.

        Returns:
            The cycle time in seconds
        """
        return 5.0

    async def cleanup(self):
        """
        Release resources when module is shutting down.
        Override this method to implement resource cleanup.
        """
        pass

    async def run_blocking(self, function, *args, **kwargs) -> Any:
        """
        Run a blocking function in the thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._thread_pool, function, *args, **kwargs)
