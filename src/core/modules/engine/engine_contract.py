from logging import Logger
from typing import Optional, List, Dict, Any, Set, Callable
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
    """

    meta: Optional[Meta]

    def __init__(self, logger: Logger, thread_pool) -> None:
        self._logger = logger
        self._running = False
        self._thread_pool = thread_pool
        self._input_buffer = {}  # For storing input data by topic
        self._arguments = (
            {}
        )  # For storing arguments passed from the pipeline configuration
        self._config = None  # Cache for module configuration
        self._shutdown_event = asyncio.Event()  # Event for signaling shutdown
        self._run_mode = "once"  # Default run mode: once, loop, on_trigger, reactive
        self._is_completed = False  # Flag to indicate if a "once" module has completed

        # New fields for reactive mode support
        self._is_processing = (
            False  # Flag to track if a reactive module is currently processing
        )
        self._input_received = False  # Flag to indicate if new input was received
        self._processing_lock = asyncio.Lock()  # Lock to prevent concurrent processing
        self._reactive_task = None  # Track the current reactive processing task

        # Load metadata from module configuration file
        try:
            config_path = os.path.join(
                os.path.dirname(inspect.getfile(self.__class__)), "module.yaml"
            )
            with open(config_path, "r", encoding="utf-8") as file:
                config_data = yaml.safe_load(file)
                self._config = config_data  # Cache the config
                # Read name, description and version directly from top level
                self.meta = Meta(
                    name=config_data.get("name", self.__class__.__name__),
                    description=config_data.get("description", "No description"),
                    version=config_data.get("version", "0.0.0"),
                )
                self._logger.debug(
                    f"Initialized module: {self.meta.name} v{self.meta.version}"
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

        # Initialize module-specific components
        self._initialize_module()

    def _initialize_module(self) -> None:
        """
        Initialize module-specific components.
        Override this method in subclasses instead of __init__ for module-specific initialization.
        """
        pass

    def get_config(self) -> dict:
        """
        Retrieve the module's configuration from the module.yaml file.

        Returns:
            A dictionary containing the module's configuration.
        """
        if self._config is not None:
            return self._config  # Return cached config if already loaded

        # Dynamically determine the path to the module.yaml file
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

    def invoke(self, command: chr) -> Device:
        """
        Handle commands from the module engine.

        Args:
            command: A character representing the command to execute
                    'S': Status - Return the module's status
                    'R': Reset - Reset the module's state
                    'P': Process - Process any pending data

        Returns:
            A Device object representing the module's state
        """
        try:
            if command == "S":
                # Status command
                self._logger.debug(f"Status check for {self.meta.name}")
                return self._get_status()
            elif command == "R":
                # Reset command
                self.log(f"Resetting {self.meta.name}")
                return self._reset_state()
            elif command == "P":
                # Process command
                self._logger.debug(f"Process command received for {self.meta.name}")
                return self._process_command()
            else:
                # Custom command handling
                return self._handle_custom_command(command)
        except Exception as e:
            self._logger.error(f"Error processing command '{command}': {e}")
            return Device(
                name=self.meta.name,
                firmware=0x10000,
                protocol="ERROR",
                errors=[f"Command error: {str(e)}"],
            )

    def _get_status(self) -> Device:
        """
        Get the current status of the module.
        Override this method to provide custom status information.

        Returns:
            A Device object representing the module's status
        """
        return Device(
            name=self.meta.name, firmware=0x10000, protocol="STATUS", errors=[]
        )

    def _reset_state(self) -> Device:
        """
        Reset the module's state.
        Override this method to provide custom reset functionality.

        Returns:
            A Device object representing the module's status after reset
        """
        self.input_data = {}
        return Device(
            name=self.meta.name, firmware=0x10000, protocol="RESET", errors=[]
        )

    def _process_command(self) -> Device:
        """
        Process any pending data.
        Override this method to provide custom processing functionality.

        Returns:
            A Device object representing the module's status after processing
        """
        return Device(
            name=self.meta.name, firmware=0x10000, protocol="PROCESS", errors=[]
        )

    def _handle_custom_command(self, command: chr) -> Device:
        """
        Handle custom commands.
        Override this method to implement custom command handling.

        Args:
            command: The custom command character

        Returns:
            A Device object representing the result of the custom command
        """
        return Device(
            name=self.meta.name,
            firmware=0x10000,
            protocol="UNKNOWN",
            errors=[f"Unrecognized command: {command}"],
        )

    def handle_input(self, data: Any) -> None:
        """
        Handle input data from the message bus.
        Default implementation stores data in input_data attribute and triggers reactive processing.

        Args:
            data: The data received from the message bus
        """
        try:
            self._process_input(data)

            # Signal that new input has been received (for reactive mode)
            if self._run_mode == "reactive":
                self._input_received = True
                self.log(
                    f"Received input in reactive module {self.meta.name}",
                    log_level="debug",
                )
        except Exception as e:
            self.log(f"Error handling input: {e}", log_level="error")
            self.log(traceback.format_exc(), log_level="debug")

    def _process_input(self, data: Any) -> None:
        """
        Process input data from the message bus.
        Override this method in subclasses to implement custom input handling.

        Args:
            data: The data received from the message bus
        """
        if isinstance(data, dict):
            self.input_data = data
        else:
            self.logg(f"Received unexpected data type: {type(data)}", log_level="error")

    async def run(self, message_bus: MessageBus) -> None:
        """
        Run the module's main logic asynchronously.
        This method manages the core module lifecycle with error handling.

        Args:
            message_bus: The message bus for inter-module communication
        """
        self._running = True

        try:
            # Initialize module run state
            await self._before_run(message_bus)

            # Handle different run modes
            if self._run_mode == "once":
                # For "once" mode, run a single iteration and then mark as completed
                try:
                    self.log(
                        f"Running module '{self.meta.name}' once", log_level="debug"
                    )
                    await self._run_iteration(message_bus)
                    self._is_completed = True
                    self.log(
                        f"Module '{self.meta.name}' completed successfully",
                        log_level="info",
                    )
                except Exception as e:
                    self._logger.error(
                        f"Error in {self.meta.name} single execution: {e}"
                    )
                    self._logger.debug(traceback.format_exc())
                    self._is_completed = True  # Still mark as completed even on error
            elif self._run_mode == "reactive":
                # For "reactive" mode, process input data as it arrives
                self.log(
                    f"Starting module '{self.meta.name}' in reactive mode",
                    log_level="info",
                )
                await self._reactive_loop(message_bus)
            else:
                # Default "loop" mode or any other mode
                while not self._shutdown_event.is_set():
                    try:
                        # Run a single iteration of module execution
                        await self._run_iteration(message_bus)

                        # Check for shutdown or wait before next iteration
                        try:
                            # Default module cycle time is 5 seconds, but can be overridden
                            await asyncio.wait_for(
                                self._shutdown_event.wait(),
                                timeout=self._get_cycle_time(),
                            )
                        except asyncio.TimeoutError:
                            # This is the normal case - timeout just means continue to next iteration
                            pass
                    except asyncio.CancelledError:
                        self.log(
                            f"{self.meta.name} task was cancelled", log_level="debug"
                        )
                        break
                    except Exception as e:
                        self._logger.error(
                            f"Error in {self.meta.name} module iteration: {e}"
                        )
                        self._logger.debug(traceback.format_exc())
                        # Continue running despite errors in a single iteration

            # Clean up after main loop
            await self._after_run(message_bus)

        except asyncio.CancelledError:
            self.log(f"{self.meta.name} task was cancelled during startup/shutdown")
        except Exception as e:
            self._logger.error(f"Fatal error in {self.meta.name} module: {e}")
            self._logger.debug(traceback.format_exc())
        finally:
            self._running = False
            self.log(f"{self.meta.name} module stopped", log_level="info")

    async def _before_run(self, message_bus: MessageBus) -> None:
        """
        Execute setup code before the main module loop starts.
        Override this method in subclasses for custom initialization.

        Args:
            message_bus: The message bus for inter-module communication
        """
        pass

    async def _run_iteration(self, message_bus: MessageBus) -> None:
        """
        Run a single iteration of the module's main logic.
        Override this method in subclasses to implement module-specific behavior.

        Args:
            message_bus: The message bus for inter-module communication
        """
        # Default implementation just processes current input data
        # Subclasses should override this with their specific logic
        if hasattr(self, "input_data") and self.input_data:
            result = self._process_data()
            if result:
                output_topic = self._get_default_output_topic()
                if output_topic:
                    await message_bus.publish(output_topic, result)

    async def _after_run(self, message_bus: MessageBus) -> None:
        """
        Execute cleanup code after the main module loop ends.
        Override this method in subclasses for custom cleanup.

        Args:
            message_bus: The message bus for inter-module communication
        """
        pass

    def _process_data(self) -> Any:
        """
        Process the current input data.
        Override this method in subclasses to implement data processing logic.

        Returns:
            The processed data to be published, or None if no publishing should occur
        """
        return None

    def _get_cycle_time(self) -> float:
        """
        Get the time in seconds between module execution cycles.
        Override this method in subclasses to customize the cycle time.

        Returns:
            The cycle time in seconds
        """
        return 5.0

    def _get_default_output_topic(self) -> Optional[str]:
        """
        Get the default output topic for this module.
        Override this method to specify a default output topic.

        Returns:
            The default output topic name or None
        """
        # Try to get the first output from module.yaml
        if self._config and "outputs" in self._config and self._config["outputs"]:
            if (
                isinstance(self._config["outputs"], list)
                and len(self._config["outputs"]) > 0
            ):
                return self._config["outputs"][0].get("name")
        return None

    async def shutdown(self):
        """
        Gracefully shut down the module.
        This method signals the module to stop running and performs cleanup.
        """
        if self._running:
            self.log(f"Initiating shutdown of {self.meta.name}...", log_level="info")
            self._shutdown_event.set()

            # Perform custom shutdown logic
            try:
                await self._on_shutdown()
            except Exception as e:
                self._logger.error(
                    f"Error during {self.meta.name} custom shutdown: {e}"
                )
            self.log(f"{self.meta.name} shutdown complete.", log_level="debug")

    async def _on_shutdown(self):
        """
        Execute custom shutdown logic for this module.
        Override this method in subclasses to implement resource cleanup.
        """
        pass

    def log(self, message: str, log_level: str = "info") -> None:
        """
        Log a message with the specified log level.

        Args:
            message: The message to log
            log_level: The log level (e.g., 'info', 'debug', 'warning', 'error', 'critical')
        """
        if hasattr(self._logger, log_level):
            getattr(self._logger, log_level)(f"{message} [{self.meta.name}]")
        else:
            self._logger.debug(
                f"Invalid log level '{log_level}' specified for {self.meta.name} module"
            )

    async def run_blocking(self, function, *args, **kwargs) -> Any:
        """
        Run a blocking function in the thread pool.

        Args:
            function: The blocking function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the blocking function
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, function, *args, **kwargs)

    def set_module_arguments(self, arguments: dict) -> None:
        """
        Set module arguments from the pipeline.
        Called by the ModuleEngine to provide arguments based on pipeline settings.

        Args:
            arguments: A dictionary containing the module's arguments
        """
        self._arguments = arguments or {}
        # Set args attribute so modules can access it directly via self.args
        self.args = self._arguments
        self._logger.debug(
            f"Module arguments set for {self.meta.name}: {self._arguments}"
        )

    def get_arguments(self) -> dict:
        """
        Get the module arguments set from the pipeline.

        Returns:
            A dictionary containing the module arguments
        """
        return self._arguments

    def get_argument(self, key: str, default: Any = None) -> Any:
        """
        Get a specific argument value with fallback to default.

        Args:
            key: The argument key to look up
            default: The default value to return if the key is not found

        Returns:
            The argument value if found, otherwise the default value
        """
        return self._arguments.get(key, default)

    async def _reactive_loop(self, message_bus: MessageBus) -> None:
        """
        Reactive processing loop that processes input as it arrives.
        This is used by modules with the "reactive" run_mode.

        Args:
            message_bus: The message bus for inter-module communication
        """
        self.log(
            f"Starting reactive mode for module {self.meta.name}", log_level="debug"
        )

        # Initial run if needed (some modules may have pre-loaded data)
        if hasattr(self, "input_data") and self.input_data:
            try:
                async with self._processing_lock:
                    self._is_processing = True
                    await self._run_iteration(message_bus)
                    self._is_processing = False
            except Exception as e:
                self._logger.error(
                    f"Error in {self.meta.name} reactive processing: {e}"
                )
                self._logger.debug(traceback.format_exc())
                self._is_processing = False

        # Main reactive loop - wait for shutdown
        while not self._shutdown_event.is_set():
            # Wait for either new input or shutdown
            if self._input_received:
                try:
                    async with self._processing_lock:
                        self._input_received = False
                        self._is_processing = True
                        self.log(
                            f"Processing new input in reactive mode for {self.meta.name}",
                            log_level="debug",
                        )
                        await self._run_iteration(message_bus)
                        self._is_processing = False
                except Exception as e:
                    self._logger.error(
                        f"Error in {self.meta.name} reactive processing: {e}"
                    )
                    self._logger.debug(traceback.format_exc())
                    self._is_processing = False
            else:
                # Wait for new input or shutdown with a small timeout for responsiveness
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=0.1)
                except asyncio.TimeoutError:
                    # Check if we have new input (added by handle_input)
                    pass

        self.log(f"Exiting reactive loop for {self.meta.name}", log_level="debug")
