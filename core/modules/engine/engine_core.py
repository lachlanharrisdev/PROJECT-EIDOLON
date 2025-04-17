from logging import Logger

import json
import hashlib
import os

from core.modules.usecase import ModuleUseCase
from core.modules.util import LogUtil, FileSystem
from core.modules.util.messagebus import MessageBus

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization


class ModuleEngine:
    def __init__(self, **args):
        self._logger = LogUtil.create(args["options"]["log_level"])
        self.use_case = ModuleUseCase(
            {
                "log_level": args["options"]["log_level"],
                "directory": FileSystem.get_modules_directory(),
            }
        )
        self.verified_modules = self.__load_verified_modules()

    def __load_verified_modules(self):
        try:
            with open("settings/verified_modules.json", "r") as f:
                return json.load(f)["modules"]
        except (FileNotFoundError, KeyError):
            self._logger.warning(
                "verified_modules.json not found or invalid. All modules will be treated as unverified."
            )
            return {}

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
        module_name = os.path.basename(module_path)
        if module_name not in self.verified_modules:
            self._logger.warning(f"Module {module_name} is NOT verified.")
            return False

        module_info = self.verified_modules[module_name]
        computed_hash = self._compute_module_hash(module_path)
        if not computed_hash:
            return False

        if computed_hash != module_info["hash"]:
            self._logger.warning(f"Hash mismatch for module {module_name}.")
            return False

        if not self.__verify_signature(
            module_name, computed_hash, module_info["signature"], public_key
        ):
            return False

        self._logger.info(f"Module {module_name} is verified.")
        return True

    def _compute_module_hash(self, module_path):
        sha256 = hashlib.sha256()
        try:
            config_path = os.path.join(module_path, "module.yaml")
            with open(config_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except FileNotFoundError as e:
            self._logger.error(f"Critical file missing in module {module_path}: {e}")
            return None

    def start(self):
        self.__reload_modules()

    def __reload_modules(self):
        public_key_path = "core/security/public_key.pem"  # Updated path
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())

        self.use_case.discover_modules(True)
        for module in self.use_case.modules:
            module_path = os.path.join(
                FileSystem.get_modules_directory(), module.meta.name
            )
            self.__verify_module(module_path, public_key)
