"""
Module: file_size_formatter.py

Author: Michael Economou
Date: 2025-06-10

file_size_formatter.py
Cross-platform file size formatting utility.
Supports both binary (1024) and decimal (1000) units with locale-aware formatting.
Features:
- Binary units (1024): KiB, MiB, GiB, TiB (IEC standard)
- Decimal units (1000): KB, MB, GB, TB (SI standard)
- Locale-aware decimal separator (. vs ,)
- Cross-platform compatibility (Windows, Linux, macOS)
"""

import locale
import platform

from config import USE_BINARY_UNITS, USE_LOCALE_DECIMAL_SEPARATOR
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


# Global locale setup flag to avoid repeated initialization
_locale_initialized = False
_locale_setup_attempted = False


def _ensure_locale_setup():
    """Ensure locale is set up only once globally."""
    global _locale_initialized, _locale_setup_attempted

    if _locale_setup_attempted:
        return _locale_initialized

    _locale_setup_attempted = True

    try:
        # Try to use system locale
        if platform.system() == "Windows":
            # Windows locale setup
            locale.setlocale(locale.LC_ALL, "")
        else:
            # Unix/Linux locale setup
            locale.setlocale(locale.LC_ALL, "")
        logger.debug(f"[FileSizeFormatter] Locale set to: {locale.getlocale()}")
        _locale_initialized = True
    except locale.Error as e:
        logger.warning(f"[FileSizeFormatter] Failed to set locale: {e}, using default")
        # Fallback to C locale
        try:
            locale.setlocale(locale.LC_ALL, "C")
            _locale_initialized = True
        except locale.Error:
            _locale_initialized = False  # Use whatever is available

    return _locale_initialized


class FileSizeFormatter:
    """
    Cross-platform file size formatter with configurable units and locale support.
    """

    # Unit definitions
    BINARY_UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    DECIMAL_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

    # Legacy units (for compatibility with existing systems)
    LEGACY_BINARY_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]  # Using KB instead of KiB

    def __init__(
        self, use_binary: bool = None, use_locale: bool = None, use_legacy_labels: bool = True
    ):
        """
        Initialize the formatter.

        Args:
            use_binary: Use binary (1024) vs decimal (1000) units. None = use config.
            use_locale: Use locale-aware decimal separator. None = use config.
            use_legacy_labels: Use legacy KB/MB labels instead of KiB/MiB for binary units.
        """
        self.use_binary = USE_BINARY_UNITS if use_binary is None else use_binary
        self.use_locale = USE_LOCALE_DECIMAL_SEPARATOR if use_locale is None else use_locale
        self.use_legacy_labels = use_legacy_labels

        # Initialize locale if needed (done only once globally)
        if self.use_locale:
            _ensure_locale_setup()

    def format_size(self, size_bytes: float) -> str:
        """
        Format file size to human-readable string.

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted size string (e.g., "1.5 MB", "1,5 MB")
        """
        if size_bytes < 0:
            return "0 B"

        # Choose base and units
        if self.use_binary:
            base = 1024
            units = self.LEGACY_BINARY_UNITS if self.use_legacy_labels else self.BINARY_UNITS
        else:
            base = 1000
            units = self.DECIMAL_UNITS

        # Calculate unit index
        size = float(size_bytes)
        unit_index = 0

        while size >= base and unit_index < len(units) - 1:
            size /= base
            unit_index += 1

        # Format number with locale-aware decimal separator
        if self.use_locale and unit_index > 0 and _locale_initialized:  # Only for non-byte sizes
            try:
                formatted_number = locale.format_string("%.1f", size)
            except (locale.Error, ValueError):
                # Fallback to standard formatting
                formatted_number = f"{size:.1f}"
        else:
            formatted_number = f"{size:.1f}"

        # Remove unnecessary .0 for whole numbers
        if formatted_number.endswith((".0", ",0")):
            formatted_number = formatted_number[:-2]

        return f"{formatted_number} {units[unit_index]}"

    def get_decimal_separator(self) -> str:
        """Get the current locale's decimal separator."""
        if not self.use_locale or not _locale_initialized:
            return "."

        try:
            # Get decimal point from locale
            conv = locale.localeconv()
            return conv.get("decimal_point", ".")
        except (locale.Error, AttributeError):
            return "."

    @classmethod
    def get_system_compatible_formatter(cls) -> "FileSizeFormatter":
        """
        Get a formatter that matches the system's file manager behavior.

        Returns:
            FileSizeFormatter configured for system compatibility
        """
        system = platform.system()

        if system == "Windows":
            # Windows typically uses binary units with legacy labels
            return cls(use_binary=True, use_locale=True, use_legacy_labels=True)
        elif system == "Darwin":  # macOS
            # macOS Finder uses decimal units
            return cls(use_binary=False, use_locale=True, use_legacy_labels=True)
        else:  # Linux and other Unix-like
            # Most Linux file managers use decimal units now
            return cls(use_binary=False, use_locale=True, use_legacy_labels=True)

    @classmethod
    def get_traditional_formatter(cls) -> "FileSizeFormatter":
        """
        Get a formatter that uses traditional binary units (1024-based).

        Returns:
            FileSizeFormatter with traditional binary formatting
        """
        return cls(use_binary=True, use_locale=False, use_legacy_labels=True)


# Global formatter instance (configured from config)
_default_formatter = None


def get_default_formatter() -> FileSizeFormatter:
    """Get the default file size formatter instance."""
    global _default_formatter
    if _default_formatter is None:
        _default_formatter = FileSizeFormatter()
    return _default_formatter


def format_file_size(size_bytes: float) -> str:
    """
    Format file size using the default formatter.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted size string
    """
    return get_default_formatter().format_size(size_bytes)


def format_file_size_system_compatible(size_bytes: float) -> str:
    """
    Format file size to match system file manager behavior.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted size string matching system conventions
    """
    formatter = FileSizeFormatter.get_system_compatible_formatter()
    return formatter.format_size(size_bytes)
