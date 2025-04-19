import json
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization


def load_verified_modules() -> Dict:
    """Load the verified modules from the JSON file.

    Returns:
        Dict: Dictionary containing verified modules information
    """
    verified_modules = {}
    settings_path = Path("src/settings/verified_modules.json")

    try:
        if settings_path.exists():
            with open(settings_path, "r") as f:
                verified_modules = json.load(f).get("modules", {})
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return verified_modules


def _verify_signature(
    module_name: str, module_hash: str, signature: str, public_key
) -> bool:
    """Verify the signature of a module.

    Args:
        module_name: Name of the module
        module_hash: Computed hash of the module
        signature: Expected signature
        public_key: Public key to verify the signature

    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        public_key.verify(
            bytes.fromhex(signature),
            module_hash.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def compute_module_hash(module_path: str) -> Optional[str]:
    """Compute the hash of a module.

    Args:
        module_path: Path to the module directory

    Returns:
        str or None: Hexadecimal hash of the module or None if computation fails
    """
    sha256 = hashlib.sha256()
    try:
        config_path = os.path.join(module_path, "module.yaml")
        with open(config_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        return None


def verify_module(module_path: str, public_key) -> bool:
    """Verify a module using its hash and signature.

    Args:
        module_path: Path to the module directory
        public_key: Public key to verify the signature

    Returns:
        bool: True if module is verified, False otherwise
    """
    # Get the actual directory name of the module
    module_name = os.path.basename(module_path)

    # Load verified modules information
    verified_modules = load_verified_modules()

    # Check if the directory name exists in the verified modules
    if module_name not in verified_modules:
        return False

    module_info = verified_modules[module_name]
    computed_hash = compute_module_hash(module_path)

    if not computed_hash:
        return False

    if computed_hash != module_info["hash"]:
        return False

    if not _verify_signature(
        module_name, computed_hash, module_info["signature"], public_key
    ):
        return False

    return True


def get_public_key():
    """Load the public key from the PEM file.

    Returns:
        Public key object or None if loading fails
    """
    key_path = Path("src/core/security/public_key.pem")

    try:
        with open(key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
            return public_key
    except (FileNotFoundError, ValueError):
        return None


def get_module_verification_status(modules_directory: str = None) -> Dict[str, bool]:
    """Get verification status for all modules.

    Args:
        modules_directory: Directory containing modules

    Returns:
        Dict: Dictionary with module names as keys and verification status as values
    """
    if modules_directory is None:
        return {}

    public_key = get_public_key()
    if not public_key:
        return {}

    verification_status = {}

    try:
        for item in os.listdir(modules_directory):
            module_path = os.path.join(modules_directory, item)
            if os.path.isdir(module_path):
                verification_status[item] = verify_module(module_path, public_key)
    except Exception:
        pass

    return verification_status
