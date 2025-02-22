import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(logs_dir, exist_ok=True)


# Configure logging
def setup_logger(name="app"):
    """Configure and return a logger instance with both file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent adding handlers multiple times
    if not logger.handlers:
        # Create formatters
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")

        # File handler (with rotation)
        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, f"{name}.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# Create default logger instance
logger = setup_logger()
