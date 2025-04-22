import os
import json
import logging
import base64
from typing import Dict, Optional, Tuple

from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

# Initialize logger
logger = logging.getLogger(__name__)

# Default trusted signers file path
TRUSTED_SIGNERS_FILE = "src/settings/trusted_signers.json"


class TrustedSignersManager:
    """
    Manages trusted signers for module verification.

    This class handles loading, verifying, and adding trusted signers for
    module signature verification.
    """

    def __init__(self, signers_file_path: str = TRUSTED_SIGNERS_FILE):
        self.signers_file_path = signers_file_path
        self.signers = self._load_trusted_signers()

    def _load_trusted_signers(self) -> Dict:
        """
        Load trusted signers from the JSON file.

        Returns:
            Dictionary with trusted signers data
        """
        try:
            if not os.path.exists(self.signers_file_path):
                logger.warning(
                    f"Trusted signers file not found: {self.signers_file_path}"
                )
                return {}

            with open(self.signers_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to load trusted signers file: {e}")
            return {}

    def save_trusted_signers(self) -> bool:
        """
        Save the current trusted signers to the JSON file.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.signers_file_path), exist_ok=True)

            # Write the JSON file
            with open(self.signers_file_path, "w", encoding="utf-8") as f:
                json.dump(self.signers, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save trusted signers file: {e}")
            return False

    def get_public_key(self, signer_id: str):
        """
        Get a public key for a specific signer.

        Args:
            signer_id: Identifier of the signer

        Returns:
            Loaded public key or None if error
        """
        try:
            if signer_id not in self.signers:
                logger.warning(f"Signer not found: {signer_id}")
                return None

            signer_data = self.signers[signer_id]
            if "pubkey" not in signer_data:
                logger.warning(f"Public key not found for signer: {signer_id}")
                return None

            pubkey_pem = signer_data["pubkey"]
            public_key = serialization.load_pem_public_key(pubkey_pem.encode("utf-8"))
            return public_key
        except Exception as e:
            logger.error(f"Failed to load public key for {signer_id}: {e}")
            return None

    def verify_signature(self, data: bytes, signature: bytes, signer_id: str) -> bool:
        """
        Verify a signature using a specific signer's public key.

        Args:
            data: Data that was signed
            signature: Signature to verify
            signer_id: Identifier of the signer

        Returns:
            True if signature is valid, False otherwise
        """
        public_key = self.get_public_key(signer_id)
        if not public_key:
            return False

        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            logger.warning(f"Invalid signature from signer {signer_id}")
            return False
        except Exception as e:
            logger.error(f"Error verifying signature from {signer_id}: {e}")
            return False

    def add_trusted_signer(
        self, signer_id: str, pubkey: str, comment: str = ""
    ) -> bool:
        """
        Add a new trusted signer.

        Args:
            signer_id: Unique identifier for the signer
            pubkey: PEM-encoded public key
            comment: Optional description of the signer

        Returns:
            True if added successfully, False otherwise
        """
        try:
            # Validate the public key first
            serialization.load_pem_public_key(pubkey.encode("utf-8"))

            # Add to trusted signers
            self.signers[signer_id] = {"pubkey": pubkey, "comment": comment}

            # Save the updated list
            return self.save_trusted_signers()
        except Exception as e:
            logger.error(f"Failed to add trusted signer {signer_id}: {e}")
            return False

    def remove_trusted_signer(self, signer_id: str) -> bool:
        """
        Remove a trusted signer.

        Args:
            signer_id: Identifier of the signer to remove

        Returns:
            True if removed successfully, False if not found or error
        """
        if signer_id not in self.signers:
            return False

        try:
            del self.signers[signer_id]
            return self.save_trusted_signers()
        except Exception as e:
            logger.error(f"Failed to remove trusted signer {signer_id}: {e}")
            return False

    def get_all_trusted_signers(self) -> Dict:
        """
        Get all trusted signers.

        Returns:
            Dictionary of all trusted signers
        """
        return self.signers

    def find_signature_signer(self, data: bytes, signature: bytes) -> Optional[str]:
        """
        Find which trusted signer created a signature.

        Args:
            data: Signed data
            signature: Signature to verify

        Returns:
            Signer ID if found and verified, None otherwise
        """
        for signer_id in self.signers:
            if self.verify_signature(data, signature, signer_id):
                return signer_id
        return None


# Create a singleton instance
trusted_signers_manager = TrustedSignersManager()
