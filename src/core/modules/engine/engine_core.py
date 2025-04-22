import logging
import os
import asyncio

from typing import Dict, Optional, List, Any, Set
from concurrent.futures import ThreadPoolExecutor

from core.modules.usecase import ModuleUseCase
from core.modules.usecase.pipeline_loader import PipelineLoader
from core.modules.models import ModuleInput, ModuleOutput, PipelineModule
from core.modules.util import LogUtil, FileSystem
from core.modules.util.messagebus import MessageBus
from core.util.shutdown_coordinator import ShutdownCoordinator

from cryptography.hazmat.primitives import serialization
from core.security.utils import (
    verify_module,
    get_public_key,
    get_module_verification_status,
)

# Import the new security verification system
from core.security.module_security import module_security_manager


class ModuleEngine:
    def __init__(self, **args):
        self.verified_modules = {}
        self._logger = logging.getLogger("__name__")
        self.pipeline_name = args.get("pipeline", "default")
        self.thread_pool = None
        self._shutdown_event = asyncio.Event()
        self.use_case = ModuleUseCase(
            {
                "log_level": args["options"]["log_level"],
                "directory": FileSystem.get_modules_directory(),
                "thread_pool": self.thread_pool,
            },
        )
        self.pipeline_loader = PipelineLoader(self._logger)
        self.message_bus = MessageBus()
        self.shutdown_coordinator = ShutdownCoordinator(self._logger)

        # For managing running module tasks
        self.module_tasks = []

        # Track input_mappings from pipeline config
        self.input_mappings: Dict[str, Dict[str, str]] = (
            {}
        )  # module_name -> {input_name -> source}

        # Store CLI-provided module settings
        self.module_settings: Dict[str, Dict[str, Any]] = {}
        if "module_settings" in args:
            self.module_settings = args["module_settings"]

        # Dry run flag - validate config without executing modules
        self.dry_run = args.get("dry_run", False)

        # Additional pipeline options
        self.pipeline_options = args.get("pipeline_options", {})

        # Output file path if specified
        self.output_file = args.get("output", None)

    async def start(self):
        """Start the engine by loading modules from the specified pipeline and connecting them asynchronously."""
        # Load the pipeline configuration
        pipeline = self.pipeline_loader.load_pipeline(self.pipeline_name)
        if not pipeline:
            self._logger.error(
                f"Failed to load pipeline '{self.pipeline_name}'. Cannot start the engine."
            )
            return False

        # Get max threads from pipeline configuration or use from pipeline options
        max_threads = (
            pipeline.execution.max_threads
            if hasattr(pipeline, "execution")
            and hasattr(pipeline.execution, "max_threads")
            else 4
        )
        self.thread_pool = ThreadPoolExecutor(max_workers=max_threads)

        # Update the thread_pool in use_case
        self.use_case.thread_pool = self.thread_pool

        # Extract input mappings from the pipeline configuration
        self._build_input_mappings(pipeline.modules)

        # Load modules based on the pipeline configuration
        self._logger.info(f"Loading modules from pipeline '{pipeline.name}'")
        self._load_modules(pipeline=pipeline)

        # Set module arguments from pipeline
        self._configure_modules(pipeline)

        # Connect modules
        self._connect_modules()

        # If in dry run mode, validate configuration and return without running modules
        if self.dry_run:
            self._logger.info("Running in dry run mode - validating configuration...")

            # Validate each module's configuration
            validation_errors = []
            for module in self.use_case.modules:
                module_name = (
                    module.meta.name
                    if hasattr(module, "meta") and module.meta
                    else str(module)
                )
                try:
                    # Call module's validate_configuration method if it exists
                    if hasattr(module, "validate_configuration") and callable(
                        getattr(module, "validate_configuration")
                    ):
                        valid, errors = module.validate_configuration()
                        if not valid:
                            for error in errors:
                                validation_errors.append(f"{module_name}: {error}")

                    # Check required inputs
                    config = module.get_config()
                    if "inputs" in config:
                        for input_def in config["inputs"]:
                            if input_def.get("required", False):
                                input_name = input_def["name"]
                                # Check if this required input has a mapping defined
                                if (
                                    module_name not in self.input_mappings
                                    or input_name
                                    not in self.input_mappings[module_name]
                                ):
                                    validation_errors.append(
                                        f"{module_name}: Required input '{input_name}' has no defined source"
                                    )
                except Exception as e:
                    validation_errors.append(
                        f"{module_name}: Configuration validation error: {str(e)}"
                    )

            # Report validation results
            if validation_errors:
                self._logger.error("Configuration validation failed with errors:")
                for error in validation_errors:
                    self._logger.error(f"  - {error}")

                # If --force flag isn't set, return an error
                if not self.pipeline_options.get("ignore_warnings", False):
                    return False
                else:
                    self._logger.warning(
                        "Proceeding despite validation errors (--force flag set)"
                    )
            else:
                self._logger.info("Configuration validation completed successfully")

            # Write to output file if specified
            if self.output_file:
                try:
                    with open(self.output_file, "w") as f:
                        f.write("Pipeline configuration validation:\n")
                        if validation_errors:
                            f.write("FAILED with errors:\n")
                            for error in validation_errors:
                                f.write(f"  - {error}\n")
                        else:
                            f.write("PASSED - all modules configured correctly\n")
                    self._logger.info(
                        f"Validation results written to {self.output_file}"
                    )
                except Exception as e:
                    self._logger.error(f"Failed to write to output file: {str(e)}")

            return len(validation_errors) == 0 or self.pipeline_options.get(
                "ignore_warnings", False
            )

        # Register shutdown handler
        self.shutdown_coordinator.register_signal_handlers(self.use_case.modules)

        # Start modules asynchronously
        await self._start_modules()

        try:
            # Apply timeout if specified
            timeout = self.pipeline_options.get("timeout", None)
            if timeout is not None:
                self._logger.info(
                    f"Setting pipeline execution timeout to {timeout} seconds"
                )
                try:
                    # Wait for shutdown with timeout
                    await asyncio.wait_for(
                        self.shutdown_coordinator.wait_for_shutdown(), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    self._logger.warning(
                        f"Pipeline execution timed out after {timeout} seconds"
                    )
                    # Force shutdown
                    self.shutdown_coordinator.trigger_shutdown()
            else:
                # Wait for shutdown signal with no timeout
                await self.shutdown_coordinator.wait_for_shutdown()

            # Perform shutdown process
            await self.shutdown_coordinator.shutdown_application()

            # Wait for all module tasks to complete
            if self.module_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self.module_tasks, return_exceptions=True),
                        timeout=30,
                    )
                except asyncio.TimeoutError:
                    self._logger.warning(
                        "Timeout waiting for module tasks to complete - some tasks may be terminated"
                    )

            # Shutdown the thread pool
            if self.thread_pool:
                self.thread_pool.shutdown()

            return True
        except Exception as e:
            self._logger.critical(f"Critical error during engine shutdown: {e}")
            return False

    def _load_modules(self, modules=None, pipeline=None):
        """
        Load modules from the specified pipeline or module list.

        Args:
            modules: List of specific module names to reload
            pipeline: Pipeline configuration containing modules to load
        """
        # Import here to avoid circular imports
        from core.modules.usecase.utilities import ModuleUtility

        modules_directory = FileSystem.get_modules_directory()
        all_module_paths = ModuleUtility.find_all_modules(modules_directory)

        # Determine which modules to check
        module_paths_to_check = []
        if modules:
            module_paths_to_check = [
                path for path in all_module_paths if os.path.basename(path) in modules
            ]
        elif pipeline:
            pipeline_module_names = {module.name for module in pipeline.modules}
            module_paths_to_check = [
                path
                for path in all_module_paths
                if os.path.basename(path) in pipeline_module_names
            ]
        else:
            module_paths_to_check = all_module_paths

        # Create dictionary to track modules that passed verification
        verified_module_paths = set()

        # First, verify each module before loading it
        for module_path in module_paths_to_check:
            full_path = os.path.join(modules_directory, module_path)
            module_name = os.path.basename(module_path)

            # Use the new module_security_manager to verify the module
            is_allowed = module_security_manager.handle_module_verification(full_path)

            if is_allowed:
                self._logger.info(f"Module '{module_name}' verification successful")
                verified_module_paths.add(module_name)
            else:
                self._logger.warning(
                    f"Module '{module_name}' verification failed - will be excluded from execution"
                )

        # Now discover and load only the verified modules
        # We'll give the discover_modules function a list of modules to ignore
        excluded_modules = [
            os.path.basename(path)
            for path in module_paths_to_check
            if os.path.basename(path) not in verified_module_paths
        ]

        # Discover and load modules
        self.use_case.discover_modules(
            True, pipeline, self.thread_pool, excluded_modules
        )

        # Initialize modules that passed verification
        for module in self.use_case.modules:
            if hasattr(module, "meta") and hasattr(module, "initialize_module"):
                module_name = module.meta.name
                self._logger.debug(f"Initializing verified module: {module_name}")
                module.initialize_module()

    def _build_input_mappings(self, pipeline_modules: List[PipelineModule]) -> None:
        """
        Build input mappings from pipeline configuration.

        Args:
            pipeline_modules: List of PipelineModule objects from pipeline config
        """
        # Create a mapping of module IDs to module names
        self.module_id_mapping = {}

        # First pass: build ID to name mapping
        for module in pipeline_modules:
            module_id = module.get_id()
            if module_id:
                self.module_id_mapping[module_id] = module.name

        # Second pass: build input mappings
        self.input_mappings = {}

        for module in pipeline_modules:
            module_name = module.name

            # Handle input_mappings if present
            if module.input_mappings:
                if module_name not in self.input_mappings:
                    self.input_mappings[module_name] = {}

                # Get the source module name from depends_on list if available
                source_module = None
                if module.depends_on and len(module.depends_on) > 0:
                    source_id = module.depends_on[0]
                    if source_id in self.module_id_mapping:
                        source_module = self.module_id_mapping[source_id]

                # For each input mapping, associate it with the source module's output
                for input_name, output_name in module.input_mappings.items():
                    if source_module:
                        # Create a qualified name with the source module
                        qualified_name = f"{source_module}.{output_name}"
                        self.input_mappings[module_name][input_name] = qualified_name
                    else:
                        # No source module specified, use output name directly
                        self.input_mappings[module_name][input_name] = output_name

    def _configure_modules(self, pipeline):
        """
        Configure modules with arguments from the pipeline.

        Args:
            pipeline: The pipeline configuration object
        """
        for module in self.use_case.modules:
            module_name = (
                module.meta.name
                if hasattr(module, "meta") and module.meta
                else str(module)
            )

            # Set pipeline-provided arguments on the module
            try:
                # Find the corresponding module config in the pipeline
                pipeline_args = None
                pipeline_module = None

                for pm in pipeline.modules:
                    if pm.name == module_name:
                        pipeline_args = pm.config
                        pipeline_module = pm
                        break

                if pipeline_args:
                    module.set_module_arguments(pipeline_args)

                # Apply any CLI-provided settings for this module
                module_id = None
                if pipeline_module and pipeline_module.id:
                    module_id = pipeline_module.id
                else:
                    # Try to use the module name as ID if no explicit ID
                    module_id = module_name.lower()

                # Check if we have CLI settings for this module (by ID or name)
                if module_id in self.module_settings:
                    cli_args = self.module_settings[module_id]
                    self._logger.info(
                        f"Applying CLI settings to module '{module_name}': {cli_args}"
                    )

                    # Merge with existing args if any
                    if not pipeline_args:
                        pipeline_args = {}

                    # Update with CLI args
                    for key, value in cli_args.items():
                        pipeline_args[key] = value

                    # Set the updated arguments
                    module.set_module_arguments(pipeline_args)

                # Set run_mode from pipeline configuration if available
                if pipeline_module and pipeline_module.run_mode:
                    module._run_mode = pipeline_module.run_mode

            except Exception as e:
                self._logger.error(
                    f"Error applying arguments to module '{module_name}': {e}"
                )

    def _connect_modules(self):
        """Connect modules based on their inputs and outputs with type validation."""
        # First register all outputs
        for module in self.use_case.modules:
            module_name = (
                module.meta.name
                if hasattr(module, "meta") and module.meta
                else str(module)
            )

            # Get module configuration
            config = module.get_config()

            # Register outputs with the message bus
            if "outputs" in config and config["outputs"]:
                for output_item in config["outputs"]:
                    # Convert to ModuleOutput
                    output_def = ModuleOutput(
                        name=output_item["name"],
                        type_name=output_item.get("type", "Any"),
                        description=output_item.get("description"),
                    )
                    # Register with message bus
                    topic = output_def.name
                    self.message_bus.register_output(topic, output_def, module_name)

        # Then connect all inputs, now that outputs are registered
        for module in self.use_case.modules:
            module_name = (
                module.meta.name
                if hasattr(module, "meta") and module.meta
                else str(module)
            )
            config = module.get_config()

            # Process inputs with type validation
            if "inputs" in config and config["inputs"]:
                for input_item in config["inputs"]:
                    # Convert to ModuleInput
                    input_def = ModuleInput(
                        name=input_item["name"],
                        type_name=input_item.get("type", "Any"),
                        description=input_item.get("description"),
                    )

                    # Check if there's a specific mapping for this input
                    explicit_source = None
                    source_module = None
                    output_name = None

                    if module_name in self.input_mappings:
                        mapping = self.input_mappings[module_name].get(input_def.name)
                        if mapping:
                            # Check if it's a qualified name (module.output)
                            if "." in mapping:
                                parts = mapping.split(".", 1)
                                source_module = parts[0]
                                output_name = parts[1]
                                explicit_source = output_name
                            else:
                                # It's just a direct output name reference
                                explicit_source = mapping

                    # Use the explicit source from input_mapping or default to input name
                    topic = explicit_source if explicit_source else input_def.name

                    # Register the input with the message bus for type validation
                    self.message_bus.register_input(topic, input_def, module_name)

                    # Subscribe the module's handle_input method to this topic
                    expected_type = input_def.get_python_type()
                    self.message_bus.subscribe(
                        topic, module.handle_input, expected_type
                    )

    async def _start_modules(self):
        """Start all modules asynchronously and monitor their completion."""
        self.module_tasks = []

        for module in self.use_case.modules:
            module_name = (
                module.meta.name
                if hasattr(module, "meta") and module.meta
                else str(module)
            )
            try:
                self._logger.info(f"Starting module: {module_name}")

                # Create and store the task
                task = asyncio.create_task(
                    module.run(self.message_bus), name=f"module_{module_name}"
                )
                self.module_tasks.append(task)

                # Add a callback to handle task completion
                task.add_done_callback(
                    lambda t, m=module_name: (
                        self._logger.info(f"Module {m} task completed")
                        if not t.cancelled()
                        else self._logger.warning(f"Module {m} task was cancelled")
                    )
                )

            except Exception as e:
                self._logger.error(f"Error starting module {module_name}: {e}")

        # Start a task to monitor module completion
        asyncio.create_task(self._monitor_modules())

    async def _monitor_modules(self):
        """
        Monitor the completion status of all modules.
        Triggers system shutdown when all modules have completed or are idle.
        """
        check_interval = 2.0  # Check every 2 seconds

        while not self._shutdown_event.is_set():
            await asyncio.sleep(check_interval)

            # Check if all modules have completed or are in loop mode
            all_completed = True
            has_loop_modules = False
            reactive_modules_idle = True

            for module in self.use_case.modules:
                if module._run_mode == "once":
                    if not module._is_completed:
                        all_completed = False
                        break
                elif module._run_mode == "reactive":
                    # Check if the reactive module is currently processing input
                    if module._is_processing:
                        reactive_modules_idle = False
                else:
                    # Module is in loop mode or another continuous mode
                    has_loop_modules = True

            # If all 'once' modules are completed, all reactive modules are idle,
            # and there are no 'loop' modules, then we can initiate shutdown
            if all_completed and reactive_modules_idle and not has_loop_modules:
                self._logger.info(
                    "All modules have completed or are idle. Initiating system shutdown."
                )
                # Trigger the shutdown through the coordinator
                self.shutdown_coordinator.trigger_shutdown()
                break

    @staticmethod
    def create_engine(**args):
        """Static factory method to create a module engine with the given args."""
        return ModuleEngine(**args)
