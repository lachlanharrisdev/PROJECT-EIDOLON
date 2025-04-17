import logging
import yaml
from pathlib import Path
from datetime import datetime


class ColorFormatter(logging.Formatter):
    """
    Custom formatter to add color coding to specific parts of log lines for console output.
    """

    COLOR_CODES = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET_CODE = "\033[0m"
    BOLD_CODE = "\033[1m"
    DIM_CODE = "\033[2m"  # Toned-down color for timestamps

    def format(self, record: logging.LogRecord) -> str:
        # Apply color to the log level
        log_color = self.COLOR_CODES.get(record.levelname, self.RESET_CODE)
        levelname = f"{self.BOLD_CODE}{log_color}{record.levelname}{self.RESET_CODE}"

        # Apply toned-down color to the timestamp
        timestamp = f"{self.DIM_CODE}{self.formatTime(record)}{self.RESET_CODE}"

        # Apply bold formatting to the filename and line number
        location = f"{self.BOLD_CODE}{record.filename}:{record.lineno}{self.RESET_CODE}"

        # Default formatting for the message
        message = record.getMessage()

        # Combine all parts into the final formatted string
        return f"{timestamp}: {levelname} @{record.name} - {message} [{location}]"


def configure_logging(
    config_path: str = "settings/configuration.yaml",
) -> logging.Logger:
    """
    Configure logging based on the settings in the configuration file.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    log_config = config.get("logging", {})
    log_level = log_config.get("level", "INFO").upper()
    log_format = log_config.get(
        "format",
        "%(asctime)s: %(levelname)s from %(name)s - %(message)s [%(filename)s:%(lineno)d]",
    )
    file_level = log_config.get("file_level", "DEBUG").upper()
    console_level = log_config.get("console_level", "INFO").upper()

    # Create the .logs/ directory if it doesn't exist
    logs_dir = Path(".logs")
    logs_dir.mkdir(exist_ok=True)

    # Generate a new timestamped log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = logs_dir / f"app_{timestamp}.log"

    # Create root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Console handler with color formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ColorFormatter(log_format))
    logger.addHandler(console_handler)

    # File handler with standard formatting
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger
