import json
import os
import logging
from typing import Dict

from .module_security import module_security_manager

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


def get_module_verification_status(modules_directory: str = None) -> Dict[str, bool]:
    """
    Get verification status for all modules.

    Uses the module security system for verification.

    Args:
        modules_directory: Optional custom directory, or default if None

    Returns:
        Dictionary mapping module names to verification status
    """
    if modules_directory is None:
        from core.modules.util import FileSystem

        modules_directory = FileSystem.get_modules_directory()

    status = {}

    # Find all module directories
    try:
        for item in os.listdir(modules_directory):
            module_path = os.path.join(modules_directory, item)
            if os.path.isdir(module_path):
                verification_status, signer_id = module_security_manager.verify_module(
                    module_path
                )

                # Convert to boolean for simple API
                is_verified = (
                    verification_status
                    == module_security_manager.ModuleVerificationStatus.VERIFIED
                )
                status[item] = is_verified

                # Log appropriate message
                if is_verified:
                    logger.debug(
                        f"Module '{item}' verification status: {is_verified}, signer: {signer_id}"
                    )
                else:
                    logger.warning(
                        f"Module '{item}' verification failed - status: {verification_status.value}"
                    )
    except Exception as e:
        logger.error(f"Error checking module verification status: {e}")

    return status


def verify_module(module_path: str, public_key=None) -> bool:
    """
    Verify if a module is officially signed.

    Args:
        module_path: Path to the module directory
        public_key: Ignored parameter kept for API compatibility

    Returns:
        True if module is verified, False otherwise
    """
    status, _ = module_security_manager.verify_module(module_path)
    # Return True only for VERIFIED status
    return status == module_security_manager.ModuleVerificationStatus.VERIFIED


def get_public_key():
    """
    Get a public key for verification.

    Returns:
        First public key from trusted signers, or None if none available
    """
    from .trusted_signers import trusted_signers_manager

    # Get the first trusted signer key
    signers = trusted_signers_manager.get_all_trusted_signers()
    if not signers:
        logger.error("No trusted signers found")
        return None

    # Get the first signer
    first_signer_id = next(iter(signers.keys()))
    return trusted_signers_manager.get_public_key(first_signer_id)


def configure_security_from_args(args):
    """
    Configure the security system from command line arguments.

    Args:
        args: Dictionary or namespace with security settings
    """
    # Set allow unverified flag if present
    if isinstance(args, dict):
        # Handle dictionary style arguments
        if "allow_unverified" in args and args["allow_unverified"]:
            module_security_manager.set_allow_unverified(True)

        # Set security mode if present
        if "security_mode" in args and args["security_mode"]:
            module_security_manager.set_security_mode(args["security_mode"])
    else:
        # Handle namespace style arguments for backward compatibility
        if hasattr(args, "allow_unverified") and args.allow_unverified:
            module_security_manager.set_allow_unverified(True)

        # Set security mode if present
        if hasattr(args, "security_mode") and args.security_mode:
            module_security_manager.set_security_mode(args.security_mode)
