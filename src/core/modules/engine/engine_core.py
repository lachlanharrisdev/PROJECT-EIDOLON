import logging

import os
from typing import Dict, Optional, List, Any

from core.modules.usecase import ModuleUseCase
from core.modules.usecase.pipeline_loader import PipelineLoader
from core.modules.models import ModuleInput, ModuleOutput, PipelineModule
from core.modules.util import LogUtil, FileSystem
from core.modules.util.messagebus import MessageBus

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

        # Track input_mappings from pipeline config
        self.input_mappings: Dict[str, Dict[str, str]] = (
            {}
        )  # module_name -> {input_name -> source}

    def start(self):
        """Start the engine by loading modules from the specified pipeline and connecting them."""
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

        # Connect and invoke modules
        self.__connect_modules()
        self.__invoke_on_modules()
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
        for module in pipeline_modules:
            if module.input_mappings:
                self.input_mappings[module.name] = module.input_mappings
                self._logger.debug(
                    f"Added input mappings for {module.name}: {module.input_mappings}"
                )

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
                    if module_name in self.input_mappings:
                        explicit_source = self.input_mappings[module_name].get(
                            input_def.name
                        )

                    # Use the explicit source or just the input name as the topic
                    topic = explicit_source if explicit_source else input_def.name

                    # Register the input with the message bus for type validation
                    self.message_bus.register_input(topic, input_def, module_name)

                    # Subscribe the module's handle_input method to this topic
                    expected_type = input_def.get_python_type()
                    self.message_bus.subscribe(
                        topic, module.handle_input, expected_type
                    )

                    self._logger.info(
                        f"Module '{module_name}' subscribed to INPUT topic: '{topic}' with type '{input_def.type_name}'"
                    )

    def __invoke_on_modules(self):
        """Invoke all modules."""
        for module in self.use_case.modules:
            try:
                module.run(self.message_bus)
            except Exception as e:
                self._logger.error(f"Error running module {module}: {e}")
