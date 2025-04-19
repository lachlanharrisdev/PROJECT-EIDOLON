import sys
import signal
import os
import yaml
import json
import pytest
from pathlib import Path

from core.modules.engine.engine_core import ModuleEngine
from core.util.logging import configure_logging
from core.modules.util import FileSystem
from core.security.utils import verify_module, get_public_key


# ANSI color codes for color-coded output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"


def color_print(message, color=Colors.RESET, bold=False):
    """Print a message with optional color and bold formatting."""
    style = Colors.BOLD if bold else ""
    print(f"{style}{color}{message}{Colors.RESET}")


USAGE = """
Eidolon CLI Tool - A modular OSINT suite for analyzing disinformation.

Usage:
  eidolon run [<pipeline>] [--log-level=<level> | --verbose | --quiet | --silent]
  eidolon list [(pipeline | modules)] [--filter=<filter>]
  eidolon config <setting> [<value>]
  eidolon validate [<directory>]
  eidolon version
    eidolon -V | --version
  eidolon help
    eidolon -h | --help

Options:
  -h --help                 Show this help message.
  -V --version              Show the version of the CLI.
  --log-level=<level>       Set the logging level [default: INFO].
                            Options: DEBUG, INFO, WARNING, ERROR, CRITICAL.
  --verbose                 Enable verbose output (equivalent to --log-level=DEBUG).
  --quiet                   Suppress all output below WARNING (equivalent to --log-level=WARNING).
  --silent                  Suppress all output below ERROR (equivalent to --log-level=ERROR).
  --filter=<filter>         Filter results to only show items that include the filter string in their name.

Arguments:
  <pipeline>                Name of pipeline to run [default: default].
                            This is the name of a YAML file in src/pipelines/ (with or without the .yaml extension).
  <setting>                 Configuration setting path (e.g., 'logging.level' or 'registry.url').
  <value>                   New value for the configuration setting.
  <directory>               Directory to run tests in [default: tests].

Commands:
  run       Run the application with modules specified in the pipeline.
  list      List available pipelines or modules, including descriptions and metadata.
  config    View or update global configuration settings.
  validate  Run tests using pytest in the specified directory.
  version   Show the version of the CLI.

Examples:
  eidolon run
  eidolon run custom_pipeline --verbose
  eidolon list modules --filter=keyword
  eidolon list pipelines
  eidolon config logging.level
  eidolon config logging.level DEBUG
  eidolon validate
"""


def run_command(args):
    """Run the main application with modules from the specified pipeline."""
    log_level = args["--log-level"].upper()
    pipeline = args["<pipeline>"] or "default"

    if args["--verbose"]:
        logger = configure_logging(log_level="DEBUG")
    elif args["--quiet"]:
        logger = configure_logging(log_level="WARNING")
    elif args["--silent"]:
        logger = configure_logging(log_level="ERROR")
    elif log_level and log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logger = configure_logging(log_level=log_level)
    else:
        logger = configure_logging(log_level="INFO")

    logger.info(f"Starting Eidolon with pipeline: {pipeline}")
    engine = ModuleEngine(options={"log_level": log_level}, pipeline=pipeline)

    logger.info("Running modules...")
    if not engine.start():
        logger.error(f"Failed to start engine with pipeline '{pipeline}'")
        return False

    return True


def list_command(args):
    """List available pipelines or modules with their descriptions and metadata."""
    list_type = "modules"  # Default to modules
    if args["pipeline"]:
        list_type = "pipeline"

    filter_str = args["--filter"] or ""

    if list_type == "pipeline":
        list_pipelines(filter_str)
    else:
        list_modules(filter_str)


def list_pipelines(filter_str=""):
    """List available pipelines with descriptions."""
    color_print("Available Pipelines:", Colors.BLUE, bold=True)
    print()

    pipelines_dir = (
        Path(os.path.dirname(os.path.abspath(__file__))) / "../../../src/pipelines"
    )

    pipeline_files = list(pipelines_dir.glob("*.yaml"))

    if not pipeline_files:
        color_print("No pipelines found!", Colors.YELLOW, bold=True)
        return

    for pipeline_file in sorted(pipeline_files):
        pipeline_name = pipeline_file.stem

        # Apply filter if specified
        if filter_str and filter_str.lower() not in pipeline_name.lower():
            continue

        try:
            with open(pipeline_file, "r") as f:
                pipeline_data = yaml.safe_load(f)

            color_print(f"Pipeline: {pipeline_name}", Colors.GREEN, bold=True)

            # Display modules in the pipeline
            if pipeline_data and "modules" in pipeline_data:
                print(f"  Modules ({len(pipeline_data['modules'])}):")
                for module in pipeline_data["modules"]:
                    module_name = module.get("name", "Unknown")
                    dependencies = module.get("depends_on", [])
                    dep_str = (
                        f" (depends on: {', '.join(dependencies)})"
                        if dependencies
                        else ""
                    )
                    print(f"   - {module_name}{dep_str}")
            else:
                print("  No modules defined in this pipeline.")

            print()
        except Exception as e:
            print(f"  Error loading pipeline {pipeline_name}: {str(e)}")
            print()


def list_modules(filter_str=""):
    """List available modules with descriptions, versions, and verification status."""
    color_print("Available Modules:", Colors.BLUE, bold=True)
    print()

    modules_directory_str = FileSystem.get_modules_directory()
    modules_directory = Path(modules_directory_str)

    if not modules_directory.exists():
        color_print("Modules directory not found!", Colors.RED, bold=True)
        return

    # Get verification status for all modules
    from core.security.utils import get_module_verification_status, get_public_key

    public_key = get_public_key()
    if not public_key:
        color_print(
            "Failed to load public key for module verification", Colors.RED, bold=True
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
        color_print("No modules found!", Colors.YELLOW, bold=True)
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
            verification_color = Colors.GREEN if verified else Colors.YELLOW
            verification_status_text = "Verified" if verified else "Unverified"

            color_print(f"Module: {name}", Colors.GREEN, bold=True)
            print(f"  Description: {description}")
            print(f"  Version: {version}")
            color_print(f"  Status: {verification_status_text}", verification_color)

            if "requirements" in module_data and module_data["requirements"]:
                print("  Requirements:")
                for req in module_data["requirements"]:
                    print(f"   - {req.get('name', 'Unknown')} {req.get('version', '')}")

            print()
        except Exception as e:
            print(f"  Error loading module {module_name}: {str(e)}")
            print()


def config_command(args):
    """View or update a configuration setting."""
    setting_path = args["<setting>"]
    new_value = args["<value>"]

    # Load the configuration file
    config_path = (
        Path(os.path.dirname(os.path.abspath(__file__)))
        / "../../../src/settings/configuration.yaml"
    )

    if not config_path.exists():
        color_print(
            f"Configuration file not found at {config_path}", Colors.RED, bold=True
        )
        return False

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Parse the setting path (e.g., 'logging.level')
        setting_parts = setting_path.split(".")

        # Navigate through the config structure to find the setting
        current = config
        for part in setting_parts[:-1]:
            if part not in current:
                color_print(
                    f"Setting '{setting_path}' not found in configuration",
                    Colors.RED,
                    bold=True,
                )
                return False
            current = current[part]

        last_part = setting_parts[-1]
        if last_part not in current:
            color_print(
                f"Setting '{setting_path}' not found in configuration",
                Colors.RED,
                bold=True,
            )
            return False

        current_value = current[last_part]

        # If no new value is provided, just display the current value
        if new_value is None:
            color_print(
                f"Current value of '{setting_path}': {current_value}",
                Colors.GREEN,
                bold=True,
            )
            return True

        # Update the setting with the new value
        old_value = current[last_part]
        current[last_part] = new_value

        # Save the updated configuration back to the file
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        color_print(f"Updated '{setting_path}':", Colors.GREEN, bold=True)
        color_print(f"  Old value: {old_value}", Colors.YELLOW)
        color_print(f"  New value: {new_value}", Colors.GREEN)

        return True

    except Exception as e:
        color_print(f"Error updating configuration: {str(e)}", Colors.RED, bold=True)
        return False


def validate_command(args):
    """Run tests using pytest in the specified directory."""
    directory = args["<directory>"] or "tests"

    color_print(f"Running tests in '{directory}'...", Colors.BLUE, bold=True)

    try:
        exit_code = pytest.main([directory])

        if exit_code == 0:
            color_print("All tests passed!", Colors.GREEN, bold=True)
            return True
        else:
            color_print(
                f"Tests failed with exit code {exit_code}", Colors.RED, bold=True
            )
            return False
    except Exception as e:
        color_print(f"Error running tests: {str(e)}", Colors.RED, bold=True)
        return False


def version_command():
    """Display the CLI version."""
    color_print("v0.3.0", Colors.GREEN, bold=True)


def main():
    from .docopt import docopt

    # Parse arguments using docopt
    args = docopt(USAGE, version="v0.3.0")

    # Gracefully handle SIGINT (Ctrl+C)
    def handle_sigint(signum, frame):
        color_print(
            "Shutdown initiated. Exiting gracefully...", Colors.YELLOW, bold=True
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    # Dispatch commands
    success = True
    if args["run"]:
        success = run_command(args)
        if not success:
            sys.exit(1)
    elif args["list"]:
        success = list_command(args)
        if not success:
            sys.exit(1)
    elif args["config"]:
        success = config_command(args)
        if not success:
            sys.exit(1)
    elif args["validate"]:
        success = validate_command(args)
        if not success:
            sys.exit(1)
    elif args["version"] or args["--version"]:
        version_command()
    elif args["help"] or args["--help"]:
        print(USAGE)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        color_print("Process interrupted by user. Exiting...", Colors.RED, bold=True)
        sys.exit(0)
    except Exception as e:
        color_print(f"Error: {e}", Colors.RED, bold=True)
        sys.exit(1)
