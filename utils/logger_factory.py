"""
Module: logger_factory.py

Author: Michael Economou
Date: 2025-05-31

logger_factory.py
Optimized logger factory with caching for improved performance.
Provides centralized logger management with thread-safe operations.
"""
import logging
import threading
from typing import Dict, Optional

from utils.logger_helper import get_cached_logger as original_get_logger


class LoggerFactory:
    """
    Thread-safe logger factory with caching for optimal performance.

    Maintains a single logger instance per module name, reducing memory usage
    and improving performance compared to creating new loggers repeatedly.
    """

    _loggers: Dict[str, logging.Logger] = {}
    _lock = threading.Lock()
    _global_level: Optional[int] = None

    @classmethod
    def get_logger(cls, name: str = None) -> logging.Logger:
        """
        Get or create a cached logger for the given name.

        Args:
            name (str): Logger name, typically __name__ from calling module

        Returns:
            logging.Logger: Cached logger instance
        """
        # Use calling module name if not provided
        if name is None:
            import inspect
            frame = inspect.currentframe().f_back
            name = frame.f_globals.get('__name__', 'unknown')

        # Thread-safe cache lookup
        with cls._lock:
            if name not in cls._loggers:
                logger = original_get_logger(name)

                # Apply global level if set
                if cls._global_level is not None:
                    logger.setLevel(cls._global_level)

                cls._loggers[name] = logger

            return cls._loggers[name]

    @classmethod
    def set_global_level(cls, level: int) -> None:
        """
        Set logging level for all cached loggers.

        Args:
            level (int): Logging level (e.g., logging.DEBUG, logging.INFO)
        """
        with cls._lock:
            cls._global_level = level
            for logger in cls._loggers.values():
                logger.setLevel(level)

    @classmethod
    def get_logger_count(cls) -> int:
        """
        Get number of cached loggers.

        Returns:
            int: Number of cached logger instances
        """
        return len(cls._loggers)

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear all cached loggers.

        Warning: This will remove all logger instances. Use with caution.
        """
        with cls._lock:
            cls._loggers.clear()

    @classmethod
    def get_cached_names(cls) -> list:
        """
        Get list of all cached logger names.

        Returns:
            list: List of logger names currently in cache
        """
        return list(cls._loggers.keys())


# Convenience function - maintains backward compatibility
def get_cached_logger(name: str = None) -> logging.Logger:
    """
    Convenience function for getting cached logger.

    Args:
        name (str): Logger name

    Returns:
        logging.Logger: Cached logger instance
    """
    return LoggerFactory.get_logger(name)


# Optional: Create module-level instance for direct access
logger_factory = LoggerFactory()
