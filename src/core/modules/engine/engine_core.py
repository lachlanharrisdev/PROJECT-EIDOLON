import logging
import os
import asyncio

from typing import Dict, Optional, List, Any, Set

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


class ModuleEngine:
    def __init__(self, **args):
        self.verified_modules = {}
        self._logger = logging.getLogger("__name__")
        self.pipeline_name = args.get("pipeline", "default")
        self.use_case = ModuleUseCase(
            {
                "log_level": args["options"]["log_level"],
                "directory": FileSystem.get_modules_directory(),
            }
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

    async def start(self):
        """Start the engine by loading modules from the specified pipeline and connecting them asynchronously."""
        # Load the pipeline configuration
        pipeline = self.pipeline_loader.load_pipeline(self.pipeline_name)
        if not pipeline:
            self._logger.error(
                f"Failed to load pipeline '{self.pipeline_name}'. Cannot start the engine."
            )
            return False

        # Extract input mappings from the pipeline configuration
        self.__build_input_mappings(pipeline.modules)

        # Load modules based on the pipeline configuration
        self._logger.info(f"Loading modules from pipeline '{pipeline.name}'")
        self.__reload_modules(pipeline=pipeline)

        # Connect modules
        self.__connect_modules()

        # Register shutdown handler
        self.shutdown_coordinator.register_signal_handlers(self.use_case.modules)

        # Start modules asynchronously
        await self.__invoke_modules()

        # Wait for shutdown signal
        await self.shutdown_coordinator.wait_for_shutdown()

        # Wait for all module tasks to complete during shutdown
        if self.module_tasks:
            self._logger.info("Waiting for module tasks to complete...")
            await asyncio.gather(*self.module_tasks, return_exceptions=True)

        return True

    def __reload_modules(self, modules=None, pipeline=None):
        """
        Reload the specified modules or modules from a pipeline.

        :param modules: List of specific module names to reload
        :param pipeline: Pipeline configuration containing modules to load
        """
        if modules:
            self._logger.debug(f"Reloading specific modules: {modules}")
        elif pipeline:
            self._logger.debug(f"Loading modules from pipeline: {pipeline.name}")
        else:
            self._logger.debug("Loading all available modules")

        # Discover and load modules
        self.use_case.discover_modules(True, pipeline)

        # Verify the loaded modules
        public_key = get_public_key()
        if not public_key:
            self._logger.error("Failed to load public key for module verification")
            return

        modules_directory = FileSystem.get_modules_directory()

        # If specific modules are specified, only check those
        module_dirs_to_check = []
        if modules:
            module_dirs_to_check = [
                os.path.join(modules_directory, m)
                for m in modules
                if os.path.isdir(os.path.join(modules_directory, m))
            ]
        elif pipeline:
            module_dirs_to_check = [
                os.path.join(modules_directory, m.name)
                for m in pipeline.modules
                if os.path.isdir(os.path.join(modules_directory, m.name))
            ]
        else:
            # Check all directories in the modules directory
            module_dirs_to_check = [
                os.path.join(modules_directory, d)
                for d in os.listdir(modules_directory)
                if os.path.isdir(os.path.join(modules_directory, d))
            ]

        for module_path in module_dirs_to_check:
            module_name = os.path.basename(module_path)
            is_verified = verify_module(module_path, public_key)

            if is_verified:
                self._logger.info(f"\033[96mModule {module_name} VERIFIED\033[0m")
            else:
                self._logger.warning(
                    f"\x1b[1;31mModule {module_name} UNVERIFIED\033[0m"
                )

    def __build_input_mappings(self, pipeline_modules: List[PipelineModule]) -> None:
        """
        Build input mappings from pipeline configuration.

        Args:
            pipeline_modules: List of PipelineModule objects from pipeline config
        """
        # Create a mapping of module IDs to module names for lookup during connection
        self.module_id_mapping = {}

        # First pass: build ID to name mapping
        for module in pipeline_modules:
            module_id = module.get_id()
            if module_id:
                self.module_id_mapping[module_id] = module.name
                self._logger.debug(
                    f"Mapped module ID '{module_id}' to module name '{module.name}'"
                )

        # Second pass: build input mappings
        self.input_mappings = {}  # Clear existing mappings

        for module in pipeline_modules:
            module_name = module.name

            # Handle input_mappings if present
            if module.input_mappings:
                if module_name not in self.input_mappings:
                    self.input_mappings[module_name] = {}

                # Get the source module name from depends_on list if available
                source_module = None
                if module.depends_on and len(module.depends_on) > 0:
                    # Get the first source module ID (simple case)
                    source_id = module.depends_on[0]
                    if source_id in self.module_id_mapping:
                        source_module = self.module_id_mapping[source_id]

                # For each input mapping, associate it with the source module's output
                for input_name, output_name in module.input_mappings.items():
                    if source_module:
                        # Create a qualified name with the source module
                        qualified_name = f"{source_module}.{output_name}"
                        self.input_mappings[module_name][input_name] = qualified_name
                        self._logger.debug(
                            f"Mapped input '{module_name}.{input_name}' to '{qualified_name}'"
                        )
                    else:
                        # No source module specified, use output name directly
                        self.input_mappings[module_name][input_name] = output_name
                        self._logger.debug(
                            f"Mapped input '{module_name}.{input_name}' to '{output_name}'"
                        )

            # If no input mappings found
            if (
                module_name not in self.input_mappings
                or not self.input_mappings[module_name]
            ):
                self._logger.debug(
                    f"No input mappings found for {module_name} in pipeline. Skipping."
                )

        self._logger.debug(f"Final input mappings: {self.input_mappings}")

    def __connect_modules(self):
        """Connect modules based on their inputs and outputs with type validation."""
        # First register all outputs
        for module in self.use_case.modules:
            module_name = (
                module.meta.name
                if hasattr(module, "meta") and module.meta
                else str(module)
            )
            self._logger.debug(f"Connecting module: {module_name}")

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
                    self._logger.info(
                        f"Module '{module_name}' set to PUBLISH topic: '{topic}' with type '{output_def.type_name}'"
                    )

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

                    # Check if there's a specific mapping for this input from the pipeline config
                    explicit_source = None
                    source_module = None
                    output_name = None

                    if module_name in self.input_mappings:
                        mapping = self.input_mappings[module_name].get(input_def.name)
                        if mapping:
                            # Check if it's a qualified name (module.output)
                            self._logger.debug(
                                f"Found mapping for input '{input_def.name}' in module '{module_name}': '{mapping}'"
                            )
                            if "." in mapping:
                                parts = mapping.split(".", 1)
                                source_module = parts[0]
                                output_name = parts[1]
                                explicit_source = (
                                    output_name  # Use just the output name as the topic
                                )
                            else:
                                # It's just a direct output name reference
                                explicit_source = mapping

                    # Use the explicit source from input_mapping or default to input name
                    topic = explicit_source if explicit_source else input_def.name

                    # Log the mapping for debugging
                    if source_module:
                        self._logger.debug(
                            f"Module '{module_name}' input '{input_def.name}' mapped to '{source_module}.{output_name}'"
                        )

                    # Register the input with the message bus for type validation
                    self.message_bus.register_input(topic, input_def, module_name)

                    # Subscribe the module's handle_input method to this topic
                    expected_type = input_def.get_python_type()
                    self.message_bus.subscribe(
                        topic, module.handle_input, expected_type
                    )

                    # Log with clear indication of mapping, if applicable
                    if explicit_source and explicit_source != input_def.name:
                        source_info = f"'{source_module}." if source_module else ""
                        self._logger.info(
                            f"Module '{module_name}' subscribed to MAPPED INPUT: '{input_def.name}' → topic: '{topic}' from {source_info}{topic}' with type '{input_def.type_name}'"
                        )
                    else:
                        self._logger.info(
                            f"Module '{module_name}' subscribed to INPUT topic: '{topic}' with type '{input_def.type_name}'"
                        )

    async def __invoke_modules(self):
        """Invoke all modules asynchronously."""
        self.module_tasks = []

        for module in self.use_case.modules:
            module_name = (
                module.meta.name
                if hasattr(module, "meta") and module.meta
                else str(module)
            )
            try:
                # Create and store the task
                self._logger.info(f"Starting module: {module_name}")
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

    @staticmethod
    def create_engine(**args):
        """Static factory method to create a module engine with the given args."""
        return ModuleEngine(**args)
