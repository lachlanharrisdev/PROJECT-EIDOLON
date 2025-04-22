import os
import logging
import hashlib
import base64
from enum import Enum
from typing import Dict, Tuple, Optional, List
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

from .trusted_signers import trusted_signers_manager

# Initialize logger
logger = logging.getLogger(__name__)


class SecurityMode(Enum):
    """Security modes for module verification."""

    PARANOID = "paranoid"  # Only verified modules allowed
    DEFAULT = "default"  # Prompt for untrusted modules
    PERMISSIVE = "permissive"  # Allow all modules with warning


class ModuleVerificationStatus(Enum):
    """Status of module verification."""

    VERIFIED = "verified"  # Signed by trusted signer
    SIGNED_UNTRUSTED = "signed_untrusted"  # Signed but signer not trusted
    UNSIGNED = "unsigned"  # No signature
    INVALID = "invalid"  # Invalid signature
    ERROR = "error"  # Error during verification


class ModuleSecurityManager:
    """
    Manages security verification for modules.

    This class handles the verification of modules against trusted signers
    and provides user interaction for security decisions.
    """

    def __init__(self):
        self.security_mode = SecurityMode.DEFAULT
        self.allow_unverified = False

    def set_security_mode(self, mode: str) -> bool:
        """
        Set the security mode.

        Args:
            mode: One of 'paranoid', 'default', 'permissive'

        Returns:
            True if set successfully, False otherwise
        """
        try:
            self.security_mode = SecurityMode(mode.lower())
            return True
        except ValueError:
            logger.error(f"Invalid security mode: {mode}")
            return False

    def set_allow_unverified(self, allow: bool):
        """Set whether to allow unverified modules without prompting."""
        self.allow_unverified = allow

    def compute_module_hash(self, module_path: str) -> Optional[str]:
        """
        Compute a deterministic hash for a module directory.

        Args:
            module_path: Path to the module directory

        Returns:
            Hash as a hex string, or None if error
        """
        try:
            if not os.path.isdir(module_path):
                logger.error(f"Module path is not a directory: {module_path}")
                return None

            sha256 = hashlib.sha256()

            # Get all files in module directory, sorted for deterministic hashing
            files = []
            for root, _, filenames in os.walk(module_path):
                for filename in filenames:
                    # Skip signature files, pycache and pyc files
                    if (
                        filename == "module.sig"
                        or "__pycache__" in root
                        or filename.endswith(".pyc")
                    ):
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

            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error computing module hash for {module_path}: {e}")
            return None

    def read_signature_file(self, module_path: str) -> Optional[bytes]:
        """
        Read the module's signature file.

        Args:
            module_path: Path to the module directory

        Returns:
            Signature as bytes, or None if not found or error
        """
        sig_file_path = os.path.join(module_path, "module.sig")
        if not os.path.exists(sig_file_path):
            logger.debug(f"No signature file found for module: {module_path}")
            return None

        try:
            with open(sig_file_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read signature file for {module_path}: {e}")
            return None

    def verify_module(
        self, module_path: str
    ) -> Tuple[ModuleVerificationStatus, Optional[str]]:
        """
        Verify a module's signature against trusted signers.

        Args:
            module_path: Path to the module directory

        Returns:
            Tuple of (verification_status, signer_id)
        """
        try:
            if not os.path.isdir(module_path):
                logger.warning(f"Cannot verify non-existent module path: {module_path}")
                return ModuleVerificationStatus.ERROR, None

            # Step 1: Check for signature file
            signature = self.read_signature_file(module_path)
            if not signature:
                logger.debug(f"Module has no signature file: {module_path}")
                return ModuleVerificationStatus.UNSIGNED, None

            # Step 2: Compute module hash
            module_hash = self.compute_module_hash(module_path)
            if not module_hash:
                logger.error(f"Failed to compute hash for module: {module_path}")
                return ModuleVerificationStatus.ERROR, None

            # Step 3: Find which signer signed this module
            hash_bytes = module_hash.encode("utf-8")
            signer_id = trusted_signers_manager.find_signature_signer(
                hash_bytes, signature
            )

            # Step 4: Determine verification status
            if signer_id:
                logger.info(
                    f"Module '{os.path.basename(module_path)}' verified with trusted signer: {signer_id}"
                )
                return ModuleVerificationStatus.VERIFIED, signer_id

            # Try to verify with any known signature format
            # This is to handle the case where the module is signed but not by a trusted signer
            for signer_id in trusted_signers_manager.get_all_trusted_signers():
                public_key = trusted_signers_manager.get_public_key(signer_id)
                if not public_key:
                    continue

                try:
                    # Just detect if the signature is valid without checking the data
                    public_key.verify(
                        signature,
                        b"dummy data to see if signature matches format",
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH,
                        ),
                        hashes.SHA256(),
                    )
                    # We should never reach here as the verification should fail for wrong data
                    pass
                except InvalidSignature:
                    # This is expected, signature format is correct but data doesn't match
                    # It means we found the format, so this might be an untrusted signer
                    # Extract potential signer info from the signature
                    logger.warning(
                        f"Module '{os.path.basename(module_path)}' has a valid signature format but is not from a trusted signer"
                    )
                    return ModuleVerificationStatus.SIGNED_UNTRUSTED, None
                except Exception:
                    # This is not the right format, continue trying
                    pass

            logger.warning(
                f"Module '{os.path.basename(module_path)}' has an invalid signature"
            )
            return ModuleVerificationStatus.INVALID, None

        except Exception as e:
            logger.error(f"Error verifying module {module_path}: {e}")
            return ModuleVerificationStatus.ERROR, None

    def prompt_user_for_module(
        self, module_path: str, status: ModuleVerificationStatus
    ) -> bool:
        """
        Prompt the user to decide whether to run an unverified module.

        Args:
            module_path: Path to the module directory
            status: Verification status of the module

        Returns:
            True if user allows the module, False otherwise
        """
        module_name = os.path.basename(module_path)

        # In paranoid mode, only verified modules are allowed
        if self.security_mode == SecurityMode.PARANOID:
            if status != ModuleVerificationStatus.VERIFIED:
                logger.warning(
                    f"Module '{module_name}' blocked in paranoid mode: {status.value}"
                )
                return False
            return True

        # In permissive mode, all modules are allowed with warning
        if self.security_mode == SecurityMode.PERMISSIVE:
            if status != ModuleVerificationStatus.VERIFIED:
                logger.warning(
                    f"Running unverified module '{module_name}': {status.value}"
                )
            return True

        # If allow_unverified flag is set, allow without prompting
        if self.allow_unverified:
            if status != ModuleVerificationStatus.VERIFIED:
                logger.warning(
                    f"Running unverified module '{module_name}' (--allow-unverified): {status.value}"
                )
            return True

        # Default mode behavior with prompting
        if status == ModuleVerificationStatus.VERIFIED:
            return True

        # For all other statuses, prompt the user
        status_message = {
            ModuleVerificationStatus.SIGNED_UNTRUSTED: "signed but not by a trusted signer",
            ModuleVerificationStatus.UNSIGNED: "unsigned",
            ModuleVerificationStatus.INVALID: "has an INVALID signature",
            ModuleVerificationStatus.ERROR: "could not be verified due to an error",
        }.get(status, "unknown status")

        print(f"\n⚠️  SECURITY WARNING: Module '{module_name}' is {status_message}")
        print("This module has not been verified by any trusted signer.")
        print("Running unverified modules can be a security risk.\n")

        while True:
            choice = (
                input("Do you want to proceed with this module? (yes/no/always): ")
                .strip()
                .lower()
            )

            if choice in ("y", "yes"):
                logger.info(
                    f"User allowed untrusted module '{module_name}' for this run"
                )
                return True

            if choice in ("n", "no"):
                logger.info(f"User declined to run untrusted module '{module_name}'")
                return False

            if choice == "always":
                logger.info(
                    f"User allowed untrusted module '{module_name}' permanently"
                )
                # Setting the allow_unverified flag for this session
                self.allow_unverified = True
                return True

            print("Invalid choice. Please enter 'yes', 'no', or 'always'.")

    def handle_module_verification(self, module_path: str) -> bool:
        """
        Handle the verification of a module and user interaction.

        Args:
            module_path: Path to the module directory

        Returns:
            True if module is allowed to run, False otherwise
        """
        status, signer_id = self.verify_module(module_path)

        if status == ModuleVerificationStatus.VERIFIED:
            # Module is verified by a trusted signer
            logger.info(
                f"Module '{os.path.basename(module_path)}' verified by {signer_id}"
            )
            return True

        # For all other statuses, check security mode and prompt if necessary
        return self.prompt_user_for_module(module_path, status)


# Create a singleton instance
module_security_manager = ModuleSecurityManager()
