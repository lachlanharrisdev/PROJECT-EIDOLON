import sys
import signal
from core.modules.engine import ModuleEngine
from core.util.logging import configure_logging


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
  eidolon run [<module>] [--log-level=<level> | --verbose] [--output-format=<format>]
  eidolon version
  eidolon (-h | --help)

Options:
  -h --help                 Show this help message.
  --log-level=<level>       Set the logging level [default: INFO].
                            Options: DEBUG, INFO, WARNING, ERROR, CRITICAL.
  --verbose                 Enable verbose output (equivalent to --log-level=DEBUG).
  --output-format=<format>  Set the output format [default: text].
                            Options: text, json.

Commands:
  run       Run the main application or a specific module.
            If <module> is not specified, all modules will be run.
  version   Show the version of the CLI.

Examples:
  eidolon run --log-level=DEBUG
  eidolon run my_module --output-format=json --verbose
  eidolon version
  eidolon -h
"""


def run_command(args):
    """Run the main application or specific modules."""
    log_level = args["--log-level"].upper()
    verbose = args["--verbose"]
    output_format = args["--output-format"]
    module = args["<module>"]

    if verbose:
        logger = configure_logging(log_level="DEBUG")
    elif log_level and log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logger = configure_logging(log_level=log_level)
    else:
        logger = configure_logging(log_level="INFO")
    engine = ModuleEngine(options={"log_level": log_level})

    if module:
        logger.info(f"Running module: {module}")
        engine.start_from_head(module)
    else:
        logger.info("Running all modules...")
        engine.start()

    if output_format == "json":
        logger.info("Output format set to JSON (not yet implemented).")


def version_command():
    """Display the CLI version."""
    color_print("Eidolon CLI Tool v1.0.0", Colors.GREEN, bold=True)


def main():
    from .docopt import docopt

    # Parse arguments using docopt
    args = docopt(USAGE, version="Eidolon CLI Tool v1.0.0")

    # Gracefully handle SIGINT (Ctrl+C)
    def handle_sigint(signum, frame):
        color_print(
            "Shutdown initiated. Exiting gracefully...", Colors.YELLOW, bold=True
        )
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    # Dispatch commands
    if args["run"]:
        run_command(args)
    elif args["version"]:
        version_command()
    elif args["--help"]:
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
