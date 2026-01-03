"""Centralized logging configuration for the node editor.

This module provides logging setup with multiple handlers for different
log levels and output destinations. Log files are created with timestamps
in separate files by severity level.

Log file structure:
    - INFO_{timestamp}.log: INFO and WARNING messages
    - DEBUG_{timestamp}.log: DEBUG messages only
    - ERROR_{timestamp}.log: ERROR and CRITICAL messages

Functions:
    setup_logging: Configure application-wide logging handlers.
    get_logger: Get a named logger instance for a module.

Author:
    Michael Economou

Date:
    2025-12-11
"""

import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO) -> None:
    """Configure logging for the entire application.

    Creates log directory if needed and sets up handlers for console
    and file output with appropriate filtering.

    Handler configuration:
        - Console: Messages at log_level and above
        - INFO file: INFO and WARNING messages
        - DEBUG file: DEBUG messages only
        - ERROR file: ERROR and CRITICAL messages

    Args:
        log_dir: Directory for log files, created if missing.
        log_level: Minimum level for console output.
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = []

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    info_log_file = os.path.join(log_dir, f"node_editor_INFO_{timestamp}.log")
    info_file_handler = logging.FileHandler(info_log_file, encoding="utf-8")
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.addFilter(lambda record: record.levelno <= logging.WARNING)
    info_file_handler.setFormatter(formatter)
    root_logger.addHandler(info_file_handler)

    debug_log_file = os.path.join(log_dir, f"node_editor_DEBUG_{timestamp}.log")
    debug_file_handler = logging.FileHandler(debug_log_file, encoding="utf-8")
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.addFilter(lambda record: record.levelno == logging.DEBUG)
    debug_file_handler.setFormatter(formatter)
    root_logger.addHandler(debug_file_handler)

    error_log_file = os.path.join(log_dir, f"node_editor_ERROR_{timestamp}.log")
    error_file_handler = logging.FileHandler(error_log_file, encoding="utf-8")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    root_logger.addHandler(error_file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Returns a logger configured by the root logger settings.
    Typically called with __name__ as the argument.

    Args:
        name: Logger name, usually the module's __name__.

    Returns:
        Logger instance for the specified name.
    """
    return logging.getLogger(name)
