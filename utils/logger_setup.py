"""
Module: logger_setup.py

Author: Michael Economou
Date: 2025-05-31

logger_setup.py
This module provides the ConfigureLogger class for setting up logging in the application.
It allows for flexible configuration of logging settings, including log levels, output
destinations, and formatting. The logger is configured to log INFO and higher levels to
the console, ERROR and higher to app.log, and DEBUG+ to app_debug.log (optional).
"""

import logging
import os
import re
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from config import ENABLE_DEBUG_LOG_FILE
from utils.logger_file_helper import add_file_handler


def safe_text(text: str) -> str:
    """
    Replaces unsupported Unicode characters with ASCII-safe alternatives.
    """
    replacements = {
        "\u2192": "->",  # → Right arrow
        "\u2014": "--",  # — em dash
        "\u2013": "-",  # – en dash
        "\u2026": "...",  # … ellipsis
    }
    pattern = re.compile("|".join(map(re.escape, replacements.keys())))
    return pattern.sub(lambda m: replacements[m.group(0)], text)


def safe_log(logger_func, message: str):
    """
    Wrapper for logger functions that catches encoding issues and falls back to ASCII.
    """
    try:
        logger_func(message)
    except UnicodeEncodeError:
        logger_func(safe_text(message))


class ConfigureLogger:
    """
    Configures application-wide logging.
    Logs INFO and higher to the console, ERROR and higher to app.log,
    and DEBUG and higher to app_debug.log.
    """

    def __init__(
        self,
        log_name: str = "app",
        log_dir: str = "logs",
        console_level: int = logging.INFO,
        file_level: int = logging.ERROR,
        max_bytes: int = 1_000_000,
        backup_count: int = 3,
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
        self.logger.setLevel(logging.DEBUG)  # Accept everything; handlers filter levels

        if not self.logger.hasHandlers():
            os.makedirs(log_dir, exist_ok=True)

            # Add timestamp to log filename for unique sessions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file_path = os.path.join(log_dir, f"{log_name}_{timestamp}.log")
            debug_file_path = os.path.join(log_dir, f"{log_name}_debug_{timestamp}.log")

            self._setup_console_handler(console_level)
            self._setup_file_handler(log_file_path, file_level, max_bytes, backup_count)

            # Extra handler for DEBUG level (e.g., dev-only logs)
            if ENABLE_DEBUG_LOG_FILE:
                add_file_handler(logger=self.logger, log_path=debug_file_path, level=logging.DEBUG)

    def _setup_console_handler(self, level: int):
        """Sets up console handler with UTF-8-safe formatting."""
        console_handler = logging.StreamHandler(sys.stdout)

        try:
            console_handler.stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

        console_handler.setLevel(level)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _setup_file_handler(self, path: str, level: int, max_bytes: int, backup_count: int):
        """Sets up file handler with rotating file output."""
        file_handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
