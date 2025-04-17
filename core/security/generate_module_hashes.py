import os
import hashlib
import json
import logging

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

logger = logging.getLogger(__name__)

MODULES_DIR = "modules"
OUTPUT_FILE = "settings/verified_modules.json"
PRIVATE_KEY_ENV = (
    "PRIVATE_KEY"  # The private key will be passed as an environment variable
)


def compute_hash(module_path):
    """Compute SHA-256 hash for a module."""
    sha256 = hashlib.sha256()
    config_path = os.path.join(module_path, "module.yaml")
    if not os.path.exists(config_path):
        logger.warning(f"Missing 'module.yaml' in module {module_path}. Skipping.")
        return None
    try:
        with open(config_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error reading 'module.yaml' in module {module_path}: {e}")

def sign_hash(hash_value, private_key):
    """Sign a hash using the private key."""
    if isinstance(hash_value, str):
        hash_value = hash_value.encode("utf-8")  # Ensure hash_value is bytes
    signature = private_key.sign(
        hash_value,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return signature.hex()


def generate_signed_hashes(private_key):
    """Generate signed hashes for all modules."""
    signed_hashes = {"modules": {}}
    for module_name in os.listdir(MODULES_DIR):
        module_path = os.path.join(MODULES_DIR, module_name)
        if os.path.isdir(module_path):
            module_hash = compute_hash(module_path)
            if module_hash:
                # Load module.yaml to extract version and repository
                config_path = os.path.join(module_path, "module.yaml")
                try:
                    with open(config_path, "r") as f:
                        module_config = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Error parsing 'module.yaml' in module {module_path}: {e}")
                    continue

                version = module_config.get("version", "unknown")
                repo = module_config.get("repository", "unknown")

                # Sign the hash
                signature = sign_hash(module_hash, private_key)

                # Add to the signed hashes
                signed_hashes["modules"][module_name] = {
                    "version": version,
                    "hash": module_hash,
                    "signature": signature,
                    "repo": repo,
                }
    return signed_hashes


if __name__ == "__main__":
    # Retrieve the private key from the environment
    private_key_pem = os.getenv(PRIVATE_KEY_ENV)
    if not private_key_pem:
        raise ValueError("PRIVATE_KEY environment variable is not set")

    # Load the private key
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),  # Ensure private_key_pem is bytes
        password=None,
    )

    # Generate signed hashes
    signed_hashes = generate_signed_hashes(private_key)

    # Save to verified_modules.json
    with open(OUTPUT_FILE, "w") as f:
        json.dump(signed_hashes, f, indent=4)
    print(f"Signed hashes saved to {OUTPUT_FILE}")
