# logger_helper.py
import logging

def get_logger(name: str = None) -> logging.Logger:
    """
    Returns a logger with the given name, or the module name if None.

    Args:
        name (str): Optional name for the logger (defaults to caller's module)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name or __name__)
