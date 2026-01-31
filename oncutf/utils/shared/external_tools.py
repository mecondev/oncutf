"""Module: external_tools.py.

Author: Michael Economou
Date: 2025-12-23

External tool detection and path resolution for cross-platform support.

This module provides utilities for locating external executables (exiftool, ffmpeg)
with support for:
- PyInstaller frozen executables (_MEIPASS)
- Platform-specific binaries (Windows/macOS/Linux)
- System PATH fallback
- Graceful degradation when tools are not available

Usage:
    from oncutf.utils.shared.external_tools import get_tool_path, ToolName

    # Get exiftool path (raises FileNotFoundError if not found)
    exiftool = get_tool_path(ToolName.EXIFTOOL)

    # Check if tool is available
    if is_tool_available(ToolName.FFMPEG):
        ffmpeg = get_tool_path(ToolName.FFMPEG)
"""

import platform
import subprocess
from enum import Enum
from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ToolName(str, Enum):
    """Supported external tools."""

    EXIFTOOL = "exiftool"
    FFMPEG = "ffmpeg"


def get_bundled_tool_path(tool_name: ToolName) -> Path | None:
    """Get path to bundled external tool, handling platform-specific binaries.

    This function searches for tools in the bin/ directory structure:
    - bin/windows/exiftool.exe
    - bin/macos/exiftool (or exiftool-arm64)
    - bin/linux/exiftool

    Args:
        tool_name: Tool to locate (ToolName.EXIFTOOL or ToolName.FFMPEG)

    Returns:
        Path to tool executable or None if not found

    Examples:
        >>> path = get_bundled_tool_path(ToolName.EXIFTOOL)
        >>> if path:
        ...     print(f"Found at: {path}")

    """
    system = platform.system()
    machine = platform.machine().lower()

    # Map system to bin directory and executable name
    if system == "Windows":
        os_dir = "windows"
        executable = f"{tool_name.value}.exe"
        fallback = None
    elif system == "Darwin":  # macOS
        os_dir = "macos"
        # Handle Apple Silicon (arm64) vs Intel (x86_64)
        if machine in ("arm64", "aarch64"):
            executable = f"{tool_name.value}-arm64"
            fallback = tool_name.value  # Fallback to universal binary
        else:
            executable = tool_name.value
            fallback = None
    elif system == "Linux":
        os_dir = "linux"
        executable = tool_name.value
        fallback = None
    else:
        logger.warning("[ExternalTools] Unknown OS: %s", system)
        return None

    # Use centralized path management for bundled tools
    from oncutf.utils.paths import AppPaths

    bundled_dir = AppPaths.get_bundled_tools_dir()

    # Construct path to bundled tool
    tool_path = bundled_dir / os_dir / executable

    # Try fallback if primary not found (e.g., universal binary on macOS)
    if not tool_path.exists() and fallback:
        tool_path = bundled_dir / os_dir / fallback

    if tool_path.exists():
        # Make executable on Unix-like systems
        if system != "Windows":
            try:
                tool_path.chmod(0o755)
            except OSError as e:
                logger.warning("[ExternalTools] Could not set executable bit: %s", e)

        logger.debug("[ExternalTools] Found bundled %s at: %s", tool_name.value, tool_path)
        return tool_path

    logger.debug("[ExternalTools] Bundled %s not found at: %s", tool_name.value, tool_path)
    return None


def get_system_tool_path(tool_name: ToolName) -> str | None:
    """Find tool in system PATH.

    Args:
        tool_name: Tool to locate

    Returns:
        Path string to the tool or None if not found

    Examples:
        >>> path = get_system_tool_path(ToolName.EXIFTOOL)
        >>> if path:
        ...     print(f"System exiftool: {path}")

    """
    try:
        # Use 'where' on Windows, 'which' on Unix-like
        cmd = "where" if platform.system() == "Windows" else "which"

        result = subprocess.run([cmd, tool_name.value], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            # Get first match (where can return multiple paths)
            system_path = result.stdout.strip().split("\n")[0]
            logger.debug("[ExternalTools] Found system %s at: %s", tool_name.value, system_path)
            return system_path

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug("[ExternalTools] Failed to find %s in system PATH: %s", tool_name.value, e)

    return None


def get_tool_path(tool_name: ToolName, prefer_bundled: bool = True) -> str:
    """Get the path to an external tool, with fallback strategies.

    Strategy:
    1. Try bundled version (if prefer_bundled=True)
    2. Try system PATH
    3. Raise FileNotFoundError if not found

    Args:
        tool_name: Tool to locate (ToolName.EXIFTOOL or ToolName.FFMPEG)
        prefer_bundled: Prefer bundled over system version (default: True)

    Returns:
        Path string to the tool

    Raises:
        FileNotFoundError: If tool not found anywhere

    Examples:
        >>> try:
        ...     exiftool = get_tool_path(ToolName.EXIFTOOL)
        ...     print(f"Using: {exiftool}")
        ... except FileNotFoundError:
        ...     print("ExifTool not available")

    """
    # Try bundled first if preferred
    if prefer_bundled:
        bundled = get_bundled_tool_path(tool_name)
        if bundled:
            logger.info("[ExternalTools] Using bundled %s: %s", tool_name.value, bundled)
            return str(bundled)

    # Fall back to system PATH
    system_path = get_system_tool_path(tool_name)
    if system_path:
        logger.info("[ExternalTools] Using system %s: %s", tool_name.value, system_path)
        return system_path

    # Not found anywhere - use same platform mapping as bundled path
    system = platform.system()
    platform_dir = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(
        system, system.lower()
    )
    raise FileNotFoundError(
        f"{tool_name.value} not found. "
        f"Please install it or place it in the bin/{platform_dir} directory. "
        f"Download from: {_get_download_url(tool_name)}"
    )


def is_tool_available(tool_name: ToolName, prefer_bundled: bool = True) -> bool:
    """Check if a tool is available without raising exceptions.

    Args:
        tool_name: Tool to check
        prefer_bundled: Prefer bundled over system version

    Returns:
        True if tool is available, False otherwise

    Examples:
        >>> if is_tool_available(ToolName.EXIFTOOL):
        ...     print("ExifTool is ready")
        ... else:
        ...     print("ExifTool not installed")

    """
    try:
        get_tool_path(tool_name, prefer_bundled=prefer_bundled)
        return True
    except FileNotFoundError:
        return False


def _get_download_url(tool_name: ToolName) -> str:
    """Get download URL for a tool."""
    urls = {
        ToolName.EXIFTOOL: "https://exiftool.org/",
        ToolName.FFMPEG: "https://ffmpeg.org/download.html",
    }
    return urls.get(tool_name, "")


def get_tool_version(tool_name: ToolName) -> str | None:
    """Get version of an external tool.

    Args:
        tool_name: Tool to check

    Returns:
        Version string or None if tool not available

    Examples:
        >>> version = get_tool_version(ToolName.EXIFTOOL)
        >>> if version:
        ...     print(f"ExifTool version: {version}")

    """
    try:
        tool_path = get_tool_path(tool_name)

        # Run tool with -ver flag (works for both exiftool and ffmpeg)
        result = subprocess.run(
            [tool_path, "-ver" if tool_name == ToolName.EXIFTOOL else "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Extract version from output (first line typically contains version)
            version_line = result.stdout.strip().split("\n")[0]
            logger.debug("[ExternalTools] %s version: %s", tool_name.value, version_line)
            return version_line

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug("[ExternalTools] Could not get %s version: %s", tool_name.value, e)

    return None
