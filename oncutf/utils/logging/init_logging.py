"""Module: init_logging.py.

Author: Michael Economou
Date: 2025-05-12

init_logging.py
Provides a single entry point to initialize the logging system
for the application with app-specific log file names.
Functions:
init_logging(app_name): Sets up loggers with rotating file handlers.
"""

import logging

from oncutf.utils.logging.logger_factory import get_cached_logger
from oncutf.utils.logging.logger_file_helper import add_file_handler


def init_logging(app_name: str = "app") -> logging.Logger:
    """Initializes logging for the application, adding rotating file handlers
    for activity and error logs under the given app name.

    Args:
        app_name (str): The base name for log files (e.g., 'oncutf').

    Returns:
        logging.Logger: The main logger for __main__ module.

    """
    logger = get_cached_logger(__name__)

    add_file_handler(logger, f"logs/{app_name}_activity.log", level=logging.INFO)
    add_file_handler(logger, f"logs/{app_name}_errors.log", level=logging.ERROR)

    return logger
