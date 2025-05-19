"""
logger_helper.py

Provides utility functions for working with loggers in a safe and consistent way.
Includes functions to retrieve or configure named loggers and to safely log
Unicode messages to the console across platforms (Windows, Linux, macOS).

Functions:
    get_logger(name): Returns a patched logger with UTF-8-safe handlers and logging methods.
    safe_text(text): Replaces problematic Unicode characters with ASCII equivalents.
    safe_log(logger_func, message): Logs a message safely, falling back to ASCII if needed.

DevOnlyFilter:
    A logging filter that hides dev-only debug messages from the console,
    while still allowing them to be stored in file logs.

Author: Michael Economou
Date: 2025-05-12
"""

import logging
import sys
import re
from functools import partial
from config import SHOW_DEV_ONLY_IN_CONSOLE

def safe_text(text: str) -> str:
    """
    Replaces unsupported Unicode characters with ASCII-safe alternatives.

    Args:
        text (str): The original text containing Unicode symbols.

    Returns:
        str: A version of the text with replacements for problematic characters.
    """
    replacements = {
        '\u2192': '->',  # -> Right arrow
        '\u2014': '--',  # — em dash
        '\u2013': '-',   # – en dash
        '\u2026': '...', # … ellipsis
    }
    pattern = re.compile('|'.join(map(re.escape, replacements.keys())))
    return pattern.sub(lambda m: replacements[m.group(0)], text)

def safe_log(logger_func, message: str, *args, **kwargs):
    """
    Logs a message using the given logger function (e.g. logger.info),
    falling back to ASCII-safe output if UnicodeEncodeError occurs.

    Args:
        logger_func (Callable): A logger method like logger.info or logger.error.
        message (str): The message to log.
    """
    try:
        if not isinstance(message, str):
            message = repr(message)
        logger_func(message, *args, **kwargs)
    except UnicodeEncodeError:
        logger_func(safe_text(str(message)), *args, **kwargs)

def patch_logger_safe_methods(logger: logging.Logger):
    """
    Replaces logger's logging methods with safe_log-wrapped versions.
    """
    for method_name in ['debug', 'info', 'warning', 'error', 'critical']:
        orig_func = getattr(logger, method_name)
        setattr(logger, method_name, partial(safe_log, orig_func))

def get_logger(name: str = None) -> logging.Logger:
    """
    Returns a logger with the given name, setting up a UTF-8-safe console handler
    if no handlers exist. Also patches its logging methods to avoid UnicodeEncodeError.

    Args:
        name (str): Optional name for the logger (defaults to caller's module)

    Returns:
        logging.Logger: Configured and patched logger instance
    """
    logger = logging.getLogger(name or __name__)
    logger.setLevel(logging.DEBUG)

    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(DevOnlyFilter())
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)

        try:
            handler.stream.reconfigure(encoding='utf-8')
        except Exception:
            pass

        logger.addHandler(handler)

    if not getattr(logger, "_patched_for_safe_log", False):
        patch_logger_safe_methods(logger)
        logger._patched_for_safe_log = True

    return logger

class DevOnlyFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if SHOW_DEV_ONLY_IN_CONSOLE:
            return True
        return not getattr(record, "dev_only", False)
