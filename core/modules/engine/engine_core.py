import logging

import json
import hashlib
import os
import re

from core.modules.usecase import ModuleUseCase
from core.modules.util import LogUtil, FileSystem
from core.modules.util.messagebus import MessageBus

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization


class ModuleEngine:
    def __init__(self, **args):
        self.verified_modules = {}
        self._logger = logging.getLogger("__name__")
        self.use_case = ModuleUseCase(
            {
                "log_level": args["options"]["log_level"],
                "directory": FileSystem.get_modules_directory(),
            }
        )
        self._load_verified_modules()
        self.message_bus = MessageBus()

    def _load_verified_modules(self):
        """Load the verified modules from the JSON file."""
        try:
            with open("settings/verified_modules.json", "r") as f:
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
        self.__reload_modules()
        self.__connect_modules()
        self.__invoke_on_modules()

    def __reload_modules(self):
        self.use_case.discover_modules(True)
        public_key_path = "core/security/public_key.pem"
        try:
            with open(public_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read())
        except (FileNotFoundError, OSError) as e:
            self._logger.error(f"Failed to load public key from {public_key_path}: {e}")
            return

        modules_directory = FileSystem.get_modules_directory()

        # Dynamically iterate through all directories in the modules folder
        for module_name in os.listdir(modules_directory):
            module_path = os.path.join(modules_directory, module_name)

            # Ensure it's a directory before attempting verification
            if os.path.isdir(module_path):
                self.__verify_module(module_path, public_key)
            else:
                self._logger.debug(f"Skipping non-directory item: {module_path}")

    def __connect_modules(self):
        """Connect modules based on their inputs and outputs."""
        for module in self.use_case.modules:
            self._logger.debug(f"Connecting module: {module} (type: {type(module)})")

            # Correctly call get_config() on the module instance
            config = module.get_config()

            outputs = config.get("outputs", [])
            inputs = config.get("inputs", [])

            # Publish outputs to the message bus
            for output in outputs:
                topic = output["name"]  # Extract the name of the output
                if topic in self.message_bus.subscribers:
                    self._logger.warning(
                        f"Multiple modules are providing the same output: {topic}"
                    )
                self._logger.info(f'{module} set to PUBLISH topic: "{topic}"')

            # Subscribe inputs with types
            for input_item in inputs:
                topic = input_item["name"]  # Extract the name of the input
                self.message_bus.subscribe(topic, module.handle_input)
                self._logger.info(f'{module} subscribed to INPUT topic: "{topic}"')

    def __invoke_on_modules(self):
        """Invoke all modules."""
        for module in self.use_case.modules:
            try:
                module.run(self.message_bus)
            except Exception as e:
                self._logger.error(f"Error running module {module}: {e}")
