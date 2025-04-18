import logging

import json
import hashlib
import os
import re
from typing import Dict, Optional, List, Any

from core.modules.usecase import ModuleUseCase
from core.modules.usecase.pipeline_loader import PipelineLoader
from core.modules.models import ModuleInput, ModuleOutput, PipelineModule
from core.modules.util import LogUtil, FileSystem
from core.modules.util.messagebus import MessageBus

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization


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
        self._load_verified_modules()
        self.message_bus = MessageBus()

        # Track input_mappings from pipeline config
        self.input_mappings: Dict[str, Dict[str, str]] = (
            {}
        )  # module_name -> {input_name -> source}

    def _load_verified_modules(self):
        """Load the verified modules from the JSON file."""
        try:
            with open("src/settings/verified_modules.json", "r") as f:
                self.verified_modules = json.load(f).get("modules", {})
                self._logger.debug(f"Verified modules loaded")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._logger.error(f"Failed to load verified modules: {e}")
            self.verified_modules = {}

    def __verify_signature(self, module_name, module_hash, signature, public_key):
        try:
            public_key.verify(
                bytes.fromhex(signature),
                module_hash.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except Exception as e:
            self._logger.error(f"Signature verification failed for {module_name}: {e}")
            return False

    def __verify_module(self, module_path, public_key):
        """Verify a module using its hash and signature."""
        # Get the actual directory name of the module
        module_name = os.path.basename(module_path)
        self._logger.debug(f"Verifying module: {module_name}")

        # Check if the directory name exists in the verified modules
        if module_name not in self.verified_modules:
            self._logger.warning(
                f"\x1b[1;31mModule {module_name} UNVERIFIED \033[0m(directory name not found in self.verified_modules)"
            )
            return False

        module_info = self.verified_modules[module_name]
        computed_hash = self._compute_module_hash(module_path)
        if not computed_hash:
            self._logger.warning(
                f"\x1b[1;31mModule {module_name} UNVERIFIED \033[0m(hash not computed)"
            )
            return False

        if computed_hash != module_info["hash"]:
            self._logger.warning(
                f"\x1b[1;31mModule {module_name} UNVERIFIED \033[0m(hash mismatch)"
            )
            return False

        if not self.__verify_signature(
            module_name, computed_hash, module_info["signature"], public_key
        ):
            self._logger.warning(
                f"\x1b[1;31mModule {module_name} UNVERIFIED \033[0m(incorrect signature)"
            )
            return False

        self._logger.info(f"\033[96mModule {module_name} VERIFIED\033[0m")
        return True

    def _compute_module_hash(self, module_path):
        sha256 = hashlib.sha256()
        try:
            config_path = os.path.join(module_path, "module.yaml")
            self._logger.debug(f"Computing hash for {config_path}")
            with open(config_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except FileNotFoundError as e:
            self._logger.error(f"Critical file missing in module {module_path}: {e}")
            return None

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
        public_key_path = "src/core/security/public_key.pem"
        try:
            with open(public_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read())
        except (FileNotFoundError, OSError) as e:
            self._logger.error(f"Failed to load public key from {public_key_path}: {e}")
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
            self.__verify_module(module_path, public_key)

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
