import sys
import signal
import os
import yaml
import pytest
import re
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum
from getpass import getpass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from core.modules.engine.engine_core import ModuleEngine
from core.util.logging import configure_logging
from core.modules.util import FileSystem
from core.security.utils import (
    verify_module,
    get_public_key,
    get_module_verification_status,
    configure_security_from_args,
)
from core.security.module_security import (
    module_security_manager,
    SecurityMode,
    ModuleVerificationStatus,
)
from core.security.trusted_signers import trusted_signers_manager
from core.util.version_utils import (
    get_current_version,
    print_version_info,
    download_update,
    check_for_updates,
)
from core.constants import DEFAULT_VERSION

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# Create Typer app
app = typer.Typer(
    help="Eidolon CLI Tool - A modular OSINT suite for analyzing disinformation.",
    add_completion=False,
)

# Create security commands subgroup
security_app = typer.Typer(
    help="Security-related commands for module verification and key management",
    name="security",
)

# Register the security subcommand group
app.add_typer(security_app)

# Console for rich output
console = Console()

# Version is now dynamically determined
VERSION = get_current_version()


class LogLevel(str, Enum):
    """Enum for log levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ListType(str, Enum):
    """Enum for list command types"""

    MODULES = "modules"
    PIPELINES = "pipelines"


def print_styled(
    message: str, style: str = "green", bold: bool = False, panel: bool = False
):
    """Print styled message using Rich"""
    text = Text(message)
    text.stylize(style)
    if bold:
        text.stylize("bold")

    if panel:
        console.print(Panel(text))
    else:
        console.print(text)


@app.command("run")
def run_command(
    pipeline: str = typer.Argument("default", help="Name of pipeline to run"),
    log_level: LogLevel = typer.Option(
        LogLevel.INFO, "--log-level", "-l", help="Set the logging level"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output (equivalent to --log-level=DEBUG)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress output below ERROR (equivalent to --log-level=ERROR)",
    ),
    settings: List[str] = typer.Option(
        [],
        "--set",
        "-s",
        help="Set module arguments defined in pipeline (e.g., 'scraper.timeout=30')",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Validate configuration without executing modules (test mode)",
    ),
    timeout: Optional[int] = typer.Option(
        None,
        "--timeout",
        "-t",
        help="Set execution timeout in seconds for the entire pipeline",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to the specified file instead of stdout",
    ),
    # New security options
    security_mode: Optional[str] = typer.Option(
        None,
        "--security-mode",
        help="Set security mode: 'paranoid' (only verified modules), 'default' (prompt for unverified), or 'permissive' (allow all with warning)",
    ),
    allow_unverified: bool = typer.Option(
        False,
        "--allow-unverified",
        help="Allow unverified modules without prompting",
    ),
):
    """Run the application with modules specified in the pipeline."""

    # Process log level
    level = log_level.value
    if verbose:
        level = log_level.DEBUG.value
    elif quiet:
        level = log_level.ERROR.value

    # Configure logging
    logger = configure_logging(log_level=level)
    logger.info(f"Starting Eidolon with pipeline: {pipeline}")

    # Configure security options
    security_params = {
        "security_mode": security_mode,
        "allow_unverified": allow_unverified,
    }
    configure_security_from_args(security_params)

    # Log security settings
    if security_mode:
        logger.info(f"Security mode set to: {security_mode}")
    if allow_unverified:
        logger.warning("Allowing unverified modules without prompting")

    # Process settings
    module_settings = {}
    for setting in settings:
        # Parse settings in format module.param=value or --module.param=value
        match = re.match(r"^(--)?([\w-]+)\.([\w-]+)=(.+)$", setting)
        if match:
            _, module_id, param_name, value = match.groups()
            if module_id not in module_settings:
                module_settings[module_id] = {}
            module_settings[module_id][param_name] = value
            logger.debug(f"Setting {module_id}.{param_name}={value}")
        else:
            logger.warning(
                f"Invalid setting format: {setting}, expected module.param=value"
            )

    # Handle dry run mode
    if dry_run:
        print_styled(
            "DRY RUN MODE - Validating configuration only",
            style="blue",
            bold=True,
            panel=True,
        )
        logger.info("Running in dry-run mode - modules will not be executed")

    # Handle output file if specified
    if output:
        logger.info(f"Output will be written to file: {output}")

    # Handle timeout
    pipeline_options = {}
    if timeout is not None:
        logger.info(f"Setting pipeline timeout to {timeout} seconds")
        pipeline_options["timeout"] = timeout

    # Initialize the engine with settings
    engine = ModuleEngine(
        options={"log_level": level},
        pipeline=pipeline,
        module_settings=module_settings,  # Pass module settings to the engine
        dry_run=dry_run,  # Pass dry run flag to the engine
        pipeline_options=pipeline_options,  # Pass additional pipeline options
    )

    logger.info("Running modules asynchronously...")

    # Create an async function to run the engine
    async def run_engine():
        try:
            result = await engine.start()
            return result
        except Exception as e:
            logger.error(f"Error running engine: {e}")
            return False

    # Run the async function using asyncio.run
    try:
        result = asyncio.run(run_engine())
        if not result:
            logger.error(f"Failed to start engine with pipeline '{pipeline}'")
            return typer.Exit(code=1)
        return typer.Exit(code=0)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        return typer.Exit(code=0)


@app.command("list")
def list_command(
    list_type: Optional[ListType] = typer.Argument(
        None, help="Type of items to list (modules or pipeline)"
    ),
    filter_str: str = typer.Option(
        "",
        "--filter",
        "-f",
        help="Filter results to only show items that include the filter string in their name",
    ),
):
    """List available pipelines or modules, including descriptions and metadata."""
    # Default to modules if not specified
    type_to_list = list_type or ListType.MODULES

    if type_to_list == ListType.PIPELINES:
        list_pipelines(filter_str)
    else:
        list_modules(filter_str)


def list_pipelines(filter_str: str = ""):
    """List available pipelines with descriptions."""
    print_styled("Available Pipelines:", style="blue", bold=True)
    console.print()

    pipelines_dir = (
        Path(os.path.dirname(os.path.abspath(__file__))) / "../../../src/pipelines"
    )

    pipeline_files = list(pipelines_dir.glob("*.yaml"))

    if not pipeline_files:
        print_styled("No pipelines found!", style="yellow", bold=True)
        return

    for pipeline_file in sorted(pipeline_files):
        pipeline_name = pipeline_file.stem

        # Apply filter if specified
        if filter_str and filter_str.lower() not in pipeline_name.lower():
            continue

        try:
            with open(pipeline_file, "r") as f:
                pipeline_data = yaml.safe_load(f)

            print_styled(f"Pipeline: {pipeline_name}", style="green", bold=True)

            # Display modules in the pipeline
            if pipeline_data and "modules" in pipeline_data:
                console.print(f"  Modules ({len(pipeline_data['modules'])}):")
                for module in pipeline_data["modules"]:
                    module_name = module.get("name", "Unknown")
                    dependencies = module.get("depends_on", [])
                    dep_str = (
                        f" (depends on: {', '.join(dependencies)})"
                        if dependencies
                        else ""
                    )
                    console.print(f"   - {module_name}{dep_str}")
            else:
                console.print("  No modules defined in this pipeline.")

            console.print()
        except Exception as e:
            console.print(f"  Error loading pipeline {pipeline_name}: {str(e)}")
            console.print()


def list_modules(filter_str: str = ""):
    """List available modules with descriptions, versions, and verification status."""
    print_styled("Available Modules:", style="blue", bold=True)
    console.print()

    modules_directory_str = FileSystem.get_modules_directory()
    modules_directory = Path(modules_directory_str)

    if not modules_directory.exists():
        print_styled("Modules directory not found!", style="red", bold=True)
        return

    # Get verification status for all modules
    public_key = get_public_key()
    if not public_key:
        print_styled(
            "Failed to load public key for module verification", style="red", bold=True
        )
        verification_status = {}
    else:
        # Check verification status for all modules
        verification_status = {}
        for item in os.listdir(modules_directory_str):
            module_path = os.path.join(modules_directory_str, item)
            if os.path.isdir(module_path):
                verification_status[item] = verify_module(module_path, public_key)

    # Get module directories
    module_dirs = [d for d in modules_directory.iterdir() if d.is_dir()]

    if not module_dirs:
        print_styled("No modules found!", style="yellow", bold=True)
        return

    for module_dir in sorted(module_dirs):
        module_name = module_dir.name

        # Apply filter if specified
        if filter_str and filter_str.lower() not in module_name.lower():
            continue

        yaml_file = module_dir / "module.yaml"
        if not yaml_file.exists():
            continue

        try:
            with open(yaml_file, "r") as f:
                module_data = yaml.safe_load(f)

            name = module_data.get("name", module_name)
            version = module_data.get("version", "Unknown")
            description = module_data.get("description", "No description available")

            # Check verification status
            verified = verification_status.get(module_name, False)
            verification_style = "green" if verified else "yellow"
            verification_status_text = "Verified" if verified else "Unverified"

            print_styled(f"Module: {name}", style="green", bold=True)
            console.print(f"  Description: {description}")
            console.print(f"  Version: {version}")
            print_styled(
                f"  Status: {verification_status_text}", style=verification_style
            )

            if "requirements" in module_data and module_data["requirements"]:
                console.print("  Requirements:")
                for req in module_data["requirements"]:
                    console.print(
                        f"   - {req.get('name', 'Unknown')} {req.get('version', '')}"
                    )

            console.print()
        except Exception as e:
            console.print(f"  Error loading module {module_name}: {str(e)}")
            console.print()


@app.command("config")
def config_command(
    setting: str = typer.Argument(
        ..., help="Configuration setting path (e.g., 'logging.level')"
    ),
    value: Optional[str] = typer.Argument(
        None, help="New value for the configuration setting"
    ),
):
    """View or update a configuration setting."""
    # Load the configuration file
    config_path = (
        Path(os.path.dirname(os.path.abspath(__file__)))
        / "../../../src/settings/configuration.yaml"
    )

    if not config_path.exists():
        print_styled(
            f"Configuration file not found at {config_path}", style="red", bold=True
        )
        return typer.Exit(code=1)

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Parse the setting path (e.g., 'logging.level')
        setting_parts = setting.split(".")

        # Navigate through the config structure to find the setting
        current = config
        for part in setting_parts[:-1]:
            if part not in current:
                print_styled(
                    f"Setting '{setting}' not found in configuration",
                    style="red",
                    bold=True,
                )
                return typer.Exit(code=1)
            current = current[part]

        last_part = setting_parts[-1]
        if last_part not in current:
            print_styled(
                f"Setting '{setting}' not found in configuration",
                style="red",
                bold=True,
            )
            return typer.Exit(code=1)

        current_value = current[last_part]

        # If no new value is provided, just display the current value
        if value is None:
            print_styled(
                f"Current value of '{setting}': {current_value}",
                style="green",
                bold=True,
            )
            return typer.Exit(code=0)

        # Update the setting with the new value
        old_value = current[last_part]
        current[last_part] = value

        # Save the updated configuration back to the file
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print_styled(f"Updated '{setting}':", style="green", bold=True)
        print_styled(f"  Old value: {old_value}", style="yellow")
        print_styled(f"  New value: {value}", style="green")

        return typer.Exit(code=0)

    except Exception as e:
        print_styled(f"Error updating configuration: {str(e)}", style="red", bold=True)
        return typer.Exit(code=1)


@app.command("validate")
def validate_command(
    directory: str = typer.Argument("tests", help="Directory to run tests in")
):
    """Run tests using pytest in the specified directory."""
    print_styled(f"Running tests in '{directory}'...", style="blue", bold=True)

    try:
        exit_code = pytest.main([directory])

        if exit_code == 0:
            print_styled("All tests passed!", style="green", bold=True)
            return typer.Exit(code=0)
        else:
            print_styled(
                f"Tests failed with exit code {exit_code}", style="red", bold=True
            )
            return typer.Exit(code=1)
    except Exception as e:
        print_styled(f"Error running tests: {str(e)}", style="red", bold=True)
        return typer.Exit(code=1)


@app.command("version")
def version_command(
    check_updates: bool = typer.Option(
        True,
        "--check-updates/--no-check-updates",
        help="Check for updates when displaying version",
    ),
):
    """Display the CLI version and check for updates."""
    # Use the version utility to print version info
    (
        print_version_info()
        if check_updates
        else console.print(f"Eidolon version: {VERSION}", style="green bold")
    )


@app.command("update")
def update_command(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force update even if already on the latest version",
    ),
):
    """Update Eidolon to the latest version from the repository."""
    update_available, current_version, latest_version = check_for_updates(force=True)

    if not update_available and not force:
        console.print(
            f"You are already using the latest version: {current_version}",
            style="green",
        )
        return

    if force:
        console.print(
            f"Forcing update from {current_version} to latest version...",
            style="yellow",
        )
    else:
        console.print(
            f"Updating from {current_version} to {latest_version}...", style="blue"
        )

    # Perform the update
    success = download_update()

    if success:
        console.print("Update completed successfully!", style="green bold")
    else:
        console.print(
            "Update failed. Please try again or update manually.", style="red bold"
        )
        return typer.Exit(code=1)


@security_app.command("sign")
def sign_module_command(
    module_path: Path = typer.Argument(
        ...,
        help="Path to the module directory to sign",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    private_key_file: Path = typer.Option(
        ..., "--key", "-k", help="Path to the private key file"
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to save the signature (default: module_path/module.sig)",
    ),
    extract_pubkey: Optional[Path] = typer.Option(
        None, "--extract-pubkey", "-p", help="Path to save the extracted public key"
    ),
    signer_id: Optional[str] = typer.Option(
        None,
        "--id",
        "-i",
        help="Suggested signer ID to use when importing the public key",
    ),
    password_prompt: bool = typer.Option(
        True,
        "--prompt-password/--no-prompt-password",
        help="Whether to prompt for a private key password",
    ),
):
    """Sign a module with a private key."""
    # Ask for password if needed
    password = None
    if password_prompt:
        try:
            password_input = getpass(
                "Enter private key password (press Enter if none): "
            )
            password = password_input if password_input else None
        except KeyboardInterrupt:
            print_styled("\nOperation cancelled.", style="yellow")
            raise typer.Exit(1)

    # Load private key
    try:
        with open(private_key_file, "rb") as key_file:
            private_key_data = key_file.read()

        if password:
            password_bytes = password.encode("utf-8")
        else:
            password_bytes = None

        private_key = serialization.load_pem_private_key(
            private_key_data,
            password=password_bytes,
        )
    except Exception as e:
        print_styled(f"Failed to load private key: {e}", style="red", bold=True)
        raise typer.Exit(1)

    # Extract public key if requested
    if extract_pubkey or signer_id:
        try:
            public_key = private_key.public_key()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")

            # Save to file if path provided
            if extract_pubkey:
                with open(extract_pubkey, "w") as f:
                    f.write(public_key_pem)
                print_styled(f"Public key saved to: {extract_pubkey}", style="green")

            # Show instructions for adding to trusted signers
            if signer_id:
                print_styled(
                    "\nTo add this key to trusted signers:", style="blue", bold=True
                )
                print_styled(
                    f"Run: eidolon security trust --key {extract_pubkey or 'extracted_key.pem'} --id {signer_id}",
                    style="blue",
                )
        except Exception as e:
            print_styled(f"Failed to extract public key: {e}", style="red")

    # Sign the module
    try:
        # Compute the module hash
        module_hash = module_security_manager.compute_module_hash(str(module_path))
        if not module_hash:
            print_styled(
                f"Failed to compute hash for module: {module_path}",
                style="red",
                bold=True,
            )
            raise typer.Exit(1)

        # Sign the hash
        module_hash_bytes = module_hash.encode("utf-8")
        signature = private_key.sign(
            module_hash_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )

        # Determine signature path
        sig_path = output_path if output_path else module_path / "module.sig"

        # Save the signature to a file
        with open(sig_path, "wb") as sig_file:
            sig_file.write(signature)

        print_styled(
            f"Module signed successfully: {sig_path}", style="green", bold=True
        )
    except Exception as e:
        print_styled(f"Error signing module: {e}", style="red", bold=True)
        raise typer.Exit(1)

    return typer.Exit(0)


@security_app.command("verify")
def verify_module_command(
    module_path: Path = typer.Argument(
        ...,
        help="Path to the module to verify",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    details: bool = typer.Option(
        False, "--details", "-d", help="Show detailed verification information"
    ),
):
    """Verify a module's signature against trusted signers."""
    try:
        status, signer_id = module_security_manager.verify_module(str(module_path))

        if status == ModuleVerificationStatus.VERIFIED:
            print_styled(
                f"✓ Module '{module_path.name}' VERIFIED", style="green", bold=True
            )
            print_styled(f"  Signed by: {signer_id}", style="green")
            return typer.Exit(0)

        status_messages = {
            ModuleVerificationStatus.SIGNED_UNTRUSTED: "SIGNED (by untrusted signer)",
            ModuleVerificationStatus.UNSIGNED: "UNSIGNED (no signature found)",
            ModuleVerificationStatus.INVALID: "INVALID SIGNATURE",
            ModuleVerificationStatus.ERROR: "ERROR during verification",
        }

        message = status_messages.get(status, "UNKNOWN STATUS")
        print_styled(
            f"✗ Module '{module_path.name}' {message}", style="yellow", bold=True
        )

        if details:
            # Show signature details
            sig_file = module_path / "module.sig"
            if sig_file.exists():
                print_styled("Signature details:", style="blue")
                print(f"  Signature file: {sig_file}")
                print(f"  Status: {status.value}")
                print(f"  Size: {os.path.getsize(sig_file)} bytes")
            else:
                print_styled("No signature file found", style="yellow")

            # Show module hash
            module_hash = module_security_manager.compute_module_hash(str(module_path))
            if module_hash:
                print_styled("Module hash:", style="blue")
                print(f"  {module_hash}")

        return typer.Exit(1)
    except Exception as e:
        print_styled(f"Error verifying module: {e}", style="red", bold=True)
        return typer.Exit(1)


@security_app.command("trust")
def trust_key_command(
    key_file: Path = typer.Option(
        ..., "--key", "-k", help="Path to the public key file to trust", exists=True
    ),
    signer_id: str = typer.Option(
        ..., "--id", "-i", help="Unique identifier for the signer"
    ),
    comment: str = typer.Option(
        "", "--comment", "-c", help="Description of the trusted signer"
    ),
):
    """Add a trusted signer's public key."""
    try:
        with open(key_file, "r") as f:
            pubkey_content = f.read()

        # Add to trusted signers
        if trusted_signers_manager.add_trusted_signer(
            signer_id, pubkey_content, comment
        ):
            print_styled(
                f"Successfully added trusted signer: {signer_id}",
                style="green",
                bold=True,
            )
            return typer.Exit(0)
        else:
            print_styled(
                f"Failed to add trusted signer: {signer_id}", style="red", bold=True
            )
            return typer.Exit(1)
    except Exception as e:
        print_styled(
            f"Failed to import key from file {key_file}: {e}", style="red", bold=True
        )
        return typer.Exit(1)


@security_app.command("untrust")
def untrust_key_command(
    signer_id: str = typer.Argument(..., help="Identifier of the signer to remove")
):
    """Remove a trusted signer."""
    if trusted_signers_manager.remove_trusted_signer(signer_id):
        print_styled(
            f"Successfully removed trusted signer: {signer_id}",
            style="green",
            bold=True,
        )
        return typer.Exit(0)
    else:
        print_styled(
            f"Failed to remove trusted signer: {signer_id}", style="red", bold=True
        )
        return typer.Exit(1)


@security_app.command("list-trusted")
def list_trusted_signers_command():
    """List all trusted signers."""
    signers = trusted_signers_manager.get_all_trusted_signers()

    if not signers:
        print_styled("No trusted signers found.", style="yellow", bold=True)
        return typer.Exit(0)

    print_styled("Trusted Signers:", style="blue", bold=True)

    table = Table(title="Trusted Signers")
    table.add_column("ID", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Key Fingerprint", style="magenta")

    for signer_id, data in signers.items():
        comment = data.get("comment", "")
        # Get a fingerprint from the key
        pubkey = data.get("pubkey", "").replace("\\n", "\n")
        pubkey_preview = pubkey.split("\n")[0] + "..."

        table.add_row(signer_id, comment, pubkey_preview)

    console.print(table)
    return typer.Exit(0)


@security_app.command("generate-keypair")
def generate_keypair_command(
    output_dir: Path = typer.Option(
        ".", "--output-dir", "-o", help="Directory to save the key files"
    ),
    prefix: str = typer.Option(
        "eidolon", "--prefix", "-p", help="Prefix for key filenames"
    ),
    key_size: int = typer.Option(
        2048, "--size", "-s", help="Key size in bits (2048, 3072, or 4096)"
    ),
    with_password: bool = typer.Option(
        True,
        "--with-password/--no-password",
        help="Whether to password-protect the private key",
    ),
):
    """Generate a new RSA keypair for signing modules."""
    try:
        # Validate key size
        if key_size not in (2048, 3072, 4096):
            print_styled(
                "Key size must be 2048, 3072, or 4096 bits.", style="red", bold=True
            )
            return typer.Exit(1)

        # Generate key pair
        print_styled(f"Generating {key_size}-bit RSA keypair...", style="blue")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )

        # Get password if needed
        password = None
        if with_password:
            while True:
                password1 = getpass("Enter password for private key: ")
                if not password1:
                    print_styled("Password cannot be empty. Try again.", style="yellow")
                    continue

                password2 = getpass("Confirm password: ")
                if password1 == password2:
                    password = password1
                    break
                else:
                    print_styled("Passwords don't match. Try again.", style="yellow")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Save private key
        private_key_path = os.path.join(output_dir, f"{prefix}_private_key.pem")
        encryption_algorithm = (
            serialization.BestAvailableEncryption(password.encode())
            if password
            else serialization.NoEncryption()
        )
        with open(private_key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=encryption_algorithm,
                )
            )

        # Save public key
        public_key = private_key.public_key()
        public_key_path = os.path.join(output_dir, f"{prefix}_public_key.pem")
        with open(public_key_path, "wb") as f:
            f.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

        print_styled("Key generation successful!", style="green", bold=True)
        print_styled(f"Private key saved to: {private_key_path}", style="green")
        print_styled(f"Public key saved to: {public_key_path}", style="green")

        print_styled("\nNext steps:", style="blue", bold=True)
        print_styled(f"1. Use the private key to sign modules:", style="blue")
        print_styled(
            f"   eidolon security sign --key {private_key_path} /path/to/module",
            style="cyan",
        )
        print_styled(
            f"2. Share the public key with others to verify your modules:", style="blue"
        )
        print_styled(
            f"   eidolon security trust --key {public_key_path} --id your_id --comment 'Your description'",
            style="cyan",
        )

        return typer.Exit(0)
    except Exception as e:
        print_styled(f"Error generating keypair: {e}", style="red", bold=True)
        return typer.Exit(1)


def main():
    """Entry point for the CLI."""

    # Gracefully handle SIGINT (Ctrl+C)
    def handle_sigint(signum, frame):
        print_styled(
            "Shutdown initiated. Exiting gracefully...", style="yellow", bold=True
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    # Run the Typer app
    app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_styled("Process interrupted by user. Exiting...", style="red", bold=True)
        sys.exit(0)
    except Exception as e:
        print_styled(f"Error: {e}", style="red", bold=True)
        sys.exit(1)
