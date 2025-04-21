import logging
import yaml
from pathlib import Path
from datetime import datetime


class ColorFormatter(logging.Formatter):
    """
    Custom formatter to add color coding to specific parts of log lines for console output.
    Also supports fixed-width formatting for level names and logger names.
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

    # Fixed widths for consistent formatting
    LEVEL_WIDTH = 8  # Enough for "CRITICAL"
    NAME_WIDTH = 20  # Adjust based on your logger name lengths
    LOCATION_WIDTH = 28

    def __init__(self, fmt=None, datefmt=None, style="%", use_color=True):
        super().__init__(fmt, datefmt, style)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        # Format level name with fixed width
        level_name = record.levelname.ljust(self.LEVEL_WIDTH)
        # Format logger name with fixed width
        logger_name = record.name[: self.NAME_WIDTH].ljust(self.NAME_WIDTH)

        location = f"[{record.filename}:{record.lineno}]".ljust(self.LOCATION_WIDTH)

        if self.use_color:
            # Apply color to the log level
            log_color = self.COLOR_CODES.get(record.levelname, self.RESET_CODE)
            levelname = f"{self.BOLD_CODE}{log_color}{level_name}{self.RESET_CODE}"

            # Apply toned-down color to the timestamp
            timestamp = f"{self.DIM_CODE}{self.formatTime(record)}{self.RESET_CODE}"

            # Apply bold formatting to the filename and line number
            location = f"{self.BOLD_CODE}{self.DIM_CODE}{location}{self.RESET_CODE}"
        else:
            # Plain text formatting for file logs
            levelname = level_name
            timestamp = self.formatTime(record)
            location = location

        # Default formatting for the message
        message = record.getMessage()

        # Combine all parts into the final formatted string
        return f"{timestamp} {levelname} {location} {message}"


def configure_logging(
    config_path: str = "src/settings/configuration.yaml", log_level: str = None
) -> logging.Logger:
    """
    Configure logging based on the settings in the configuration file.
    Uses a single formatter style with optional color support.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    log_config = config.get("logging", {})
    if log_level is None:
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
    console_handler.setFormatter(ColorFormatter(log_format, use_color=True))
    logger.addHandler(console_handler)

    # File handler with the same formatting but without colors
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(file_level)
    file_handler.setFormatter(ColorFormatter(log_format, use_color=False))
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger
