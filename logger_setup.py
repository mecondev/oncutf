"""
logger_setup.py

This module provides the ConfigureLogger class for setting up logging in the application.
It allows for flexible configuration of logging settings, including log levels, output
destinations, and formatting. The logger is configured to log INFO and higher levels to
the console, and ERROR and higher levels to a rotating file.

Classes:
    ConfigureLogger: Configures application-wide logging with console and file handlers.

Author: Michael Economou
Date: 2025-05-01
"""


import logging
import os
from logging.handlers import RotatingFileHandler

class ConfigureLogger:
    """
    Configures application-wide logging.
    Logs INFO and higher to the console, and ERROR and higher to a rotating file.
    """

    def __init__(
        self,
        log_name: str = "app",
        log_dir: str = "logs",
        console_level: int = logging.INFO,
        file_level: int = logging.ERROR,
        max_bytes: int = 1_000_000,
        backup_count: int = 3
    ):
        """
        Initializes and configures the logger.

        Args:
            log_name (str): Base name for the log file.
            log_dir (str): Directory to store log files.
            console_level (int): Logging level for the console.
            file_level (int): Logging level for the log file.
            max_bytes (int): Max size in bytes for rotating file.
            backup_count (int): Number of backup log files to keep.
        """
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)  # Accept all logs; handlers will filter

        # Create log directory if needed
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, f"{log_name}.log")

        self._setup_console_handler(console_level)
        self._setup_file_handler(log_file_path, file_level, max_bytes, backup_count)

    def _setup_console_handler(self, level: int):
        """Sets up console handler with simple formatting."""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _setup_file_handler(self, path: str, level: int, max_bytes: int, backup_count: int):
        """Sets up file handler with rotating file output."""
        file_handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
