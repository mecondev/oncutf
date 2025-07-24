"""
Module: logger_file_helper.py

Author: Michael Economou
Date: 2025-05-31

logger_file_helper.py
Provides utility functions to attach file handlers to a logger,
with optional filtering by level or logger name.
Functions:
add_file_handler: Attaches a rotating file handler with custom level and optional filter.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def add_file_handler(
    logger: logging.Logger,
    log_path: str,
    level: int = logging.INFO,
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
    filter_by_name: str | None = None,
) -> None:
    """
    Attaches a rotating file handler to a logger.

    Args:
        logger (logging.Logger): The logger to attach the handler to.
        log_path (str): Path to the log file.
        level (int): Logging level for this file handler (e.g., logging.ERROR).
        max_bytes (int): Maximum file size before rotating.
        backup_count (int): Number of backup files to keep.
        filter_by_name (str, optional): Only log messages from loggers with this name.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    if filter_by_name:

        class NameFilter(logging.Filter):
            def filter(self, record):
                return record.name == filter_by_name

        file_handler.addFilter(NameFilter())

    logger.addHandler(file_handler)
