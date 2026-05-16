"""
app_logger.py — Logging configuration for CaseWatch.

Provides rotating file logs and console output.
Named app_logger to avoid shadowing Python's stdlib logging module.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import BASE_DIR

# Log directory
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "casewatch.log"

# Constants
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5
LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(level: str = "INFO") -> None:
    """
    Configure the root logger with rotating file and console handlers.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    global _configured
    if _configured:
        return

    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Rotating file handler
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError as e:
        print(f"[Logger] Warning: Could not create file handler: {e}")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    _configured = True
    logging.getLogger("app_logger").info(
        "Logging initialized (level=%s, file=%s)", level, LOG_FILE
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.

    Args:
        name: Module or component name for the logger.

    Returns:
        A configured Logger instance.
    """
    return logging.getLogger(name)
