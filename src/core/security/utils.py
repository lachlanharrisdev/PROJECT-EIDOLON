import json
import hashlib
import os
import logging
from pathlib import Path
from typing import Dict, Optional

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

# Initialize logger
logger = logging.getLogger(__name__)


def load_verified_modules() -> Dict:
    """
    Load the verified modules from the JSON file.

    Returns:
        Dictionary containing module verification data
    """
    verified_file = "src/settings/verified_modules.json"
    try:
        if not os.path.exists(verified_file):
            logger.warning(f"Verified modules file not found: {verified_file}")
            return {"modules": {}}

        with open(verified_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to load verified modules file: {e}")
        return {"modules": {}}


def _verify_signature(
    module_name: str, module_hash: str, signature: str, public_key
) -> bool:
    """
    Verify a module's signature using the public key.

    Args:
        module_name: Name of the module
        module_hash: Computed hash of the module
        signature: Signature to verify
        public_key: Public key for verification

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Decode the signature from base64
        import base64

        signature_bytes = base64.b64decode(signature)

        # Verify the signature
        public_key.verify(
            signature_bytes,
            module_hash.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        logger.debug(f"Signature verified for module '{module_name}'")
        return True
    except Exception as e:
        logger.warning(f"Signature verification failed for module '{module_name}': {e}")
        return False


def compute_module_hash(module_path: str) -> Optional[str]:
    """
    Compute SHA-256 hash for a module directory.

    Args:
        module_path: Path to the module directory

    Returns:
        SHA-256 hash as a hex string, or None if error
    """
    try:
        if not os.path.isdir(module_path):
            logger.error(f"Module path is not a directory: {module_path}")
            return None

        # Initialize hash
        sha256 = hashlib.sha256()

        # Get all files in the module directory and sort for deterministic hashing
        files = []
        for root, _, filenames in os.walk(module_path):
            for filename in filenames:
                # Skip __pycache__ directories and .pyc files
                if "__pycache__" in root or filename.endswith(".pyc"):
                    continue
                files.append(os.path.join(root, filename))

        files.sort()

        # Hash each file's content
        for file_path in files:
            try:
                with open(file_path, "rb") as f:
                    sha256.update(f.read())
            except Exception as e:
                logger.warning(f"Failed to read file for hashing: {file_path}: {e}")

        # Return the hex digest
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error computing module hash for {module_path}: {e}")
        return None


def verify_module(module_path: str, public_key) -> bool:
    """
    Verify if a module is officially signed.

    Args:
        module_path: Path to the module directory
        public_key: Public key for verification

    Returns:
        True if module is verified, False otherwise
    """
    if not os.path.isdir(module_path):
        logger.warning(f"Cannot verify non-existent module path: {module_path}")
        return False

    module_name = os.path.basename(module_path)
    verified_modules = load_verified_modules()

    # Check if the module is in the verified list
    if (
        "modules" not in verified_modules
        or module_name not in verified_modules["modules"]
    ):
        logger.debug(f"Module '{module_name}' not found in verified_modules.json")
        return False

    # Get the verified hash and signature
    module_data = verified_modules["modules"][module_name]
    verified_hash = module_data.get("hash")
    signature = module_data.get("signature")

    if not verified_hash or not signature:
        logger.warning(f"Missing hash or signature for module '{module_name}'")
        return False

    # Compute the current hash and compare
    current_hash = compute_module_hash(module_path)
    if not current_hash:
        logger.error(f"Failed to compute hash for module '{module_name}'")
        return False

    if current_hash != verified_hash:
        logger.warning(
            f"Module '{module_name}' hash mismatch: expected={verified_hash}, actual={current_hash}"
        )
        return False

    # Verify the signature
    return _verify_signature(module_name, verified_hash, signature, public_key)


def get_public_key():
    """
    Load the public key for module verification.

    Returns:
        Loaded public key or None if error
    """
    try:
        public_key_path = os.path.join(os.path.dirname(__file__), "public_key.pem")

        if not os.path.exists(public_key_path):
            logger.error(f"Public key not found: {public_key_path}")
            return None

        with open(public_key_path, "rb") as key_file:
            public_key = serialization.load_pem_public_key(key_file.read())
        return public_key
    except Exception as e:
        logger.error(f"Failed to load public key: {e}")
        return None


def get_module_verification_status(modules_directory: str = None) -> Dict[str, bool]:
    """
    Get verification status for all modules.

    Args:
        modules_directory: Optional custom directory, or default if None

    Returns:
        Dictionary mapping module names to verification status
    """
    if modules_directory is None:
        from core.modules.util import FileSystem

        modules_directory = FileSystem.get_modules_directory()

    public_key = get_public_key()
    if not public_key:
        logger.error("Cannot verify modules: public key not available")
        return {}

    status = {}

    # Find all module directories
    try:
        for item in os.listdir(modules_directory):
            module_path = os.path.join(modules_directory, item)
            if os.path.isdir(module_path):
                is_verified = verify_module(module_path, public_key)
                status[item] = is_verified

                log_level = "debug" if is_verified else "warning"
                if log_level == "debug":
                    logger.debug(f"Module '{item}' verification status: {is_verified}")
                else:
                    logger.warning(
                        f"Module '{item}' verification failed - may be tampered or unverified"
                    )
    except Exception as e:
        logger.error(f"Error checking module verification status: {e}")

    return status
