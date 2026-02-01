"""Module: exiftool_wrapper.py.

Author: Michael Economou
Date: 2025-05-23

exiftool_wrapper.py
This module provides a lightweight ExifTool wrapper using a persistent
'-stay_open True' process for fast metadata extraction. For extended metadata,
it falls back to a one-shot subprocess call with '-ee'.
Requires: exiftool installed and in PATH
"""

import contextlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

# Initialize Logger
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ExifToolWrapper:
    """Persistent ExifTool process wrapper with thread-safe operations.

    Manages a long-running exiftool process using -stay_open mode for
    better performance when processing multiple files.

    Features:
    - Thread-safe access via locking
    - Health monitoring and error tracking
    - Batch metadata extraction
    - Metadata writing support
    - Graceful cleanup on shutdown

    Attributes:
        process: Subprocess running exiftool
        lock: Thread lock for safe concurrent access
        counter: Unique tag counter for commands

    """

    def __init__(self) -> None:
        """Starts the persistent ExifTool process with -stay_open enabled."""
        # Get exiftool path from external_tools (bundled or system)
        from oncutf.utils.shared.external_tools import ToolName, get_tool_path

        try:
            exiftool_path = get_tool_path(ToolName.EXIFTOOL, prefer_bundled=True)
        except FileNotFoundError as e:
            logger.error("ExifTool not found: %s", e)
            raise RuntimeError(
                "ExifTool is required but not found. "
                "Please install it or place it in bin/ directory."
            ) from e

        self.process: subprocess.Popen[str] | None = subprocess.Popen(
            [exiftool_path, "-stay_open", "True", "-@", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,  # line buffered
        )
        self.lock = threading.Lock()  # Ensure thread-safe access
        self.counter = 0  # To generate unique termination tags

        # Store path for subprocess calls
        self._exiftool_path = exiftool_path

        # Health tracking
        self._last_error: str | None = None
        self._last_health_check: float | None = None
        self._consecutive_errors: int = 0

    def __del__(self) -> None:
        """Destructor to ensure ExifTool process is cleaned up."""
        import contextlib

        # Destructor must never block (Windows can show "Not Responding").
        with contextlib.suppress(Exception):
            self.close(try_graceful=False)

    @staticmethod
    def is_available() -> bool:
        """Check if ExifTool is available on the system.

        Returns:
            True if ExifTool is installed and accessible

        """
        try:
            from oncutf.utils.shared.external_tools import ToolName, get_tool_path

            exiftool_path = get_tool_path(ToolName.EXIFTOOL, prefer_bundled=True)
            result = subprocess.run(
                [exiftool_path, "-ver"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            available = result.returncode == 0
            if available:
                logger.debug("ExifTool version: %s", result.stdout.strip())
            else:
                logger.warning("ExifTool not available (returncode=%d)", result.returncode)
            return available
        except FileNotFoundError:
            logger.warning("ExifTool not found")
            return False
        except Exception as e:
            logger.warning("Error checking ExifTool availability: %s", e)
            return False

    def get_metadata(self, file_path: str, use_extended: bool = False) -> dict[str, Any]:
        """Get metadata for a single file using exiftool.

        Args:
            file_path: Path to the file
            use_extended: Whether to use extended metadata extraction

        Returns:
            Dictionary containing metadata

        """
        try:
            return self._get_metadata_with_exiftool(file_path, use_extended)

        except Exception as e:
            logger.error("[ExifToolWrapper] Error getting metadata for %s: %s", file_path, e)
            return {}

    def _get_metadata_with_exiftool(
        self, file_path: str, use_extended: bool = False
    ) -> dict[str, Any]:
        """Execute exiftool command and parse results."""
        logger.info(
            "[ExifToolWrapper] _get_metadata_with_exiftool: use_extended=%s for %s",
            use_extended,
            Path(file_path).name,
        )

        if use_extended:
            result = self._get_metadata_extended(file_path)
        else:
            result = self._get_metadata_fast(
                file_path
            )  # Convert None to empty dict for consistency
        return result if result is not None else {}

    def _get_metadata_fast(self, file_path: str) -> dict[str, Any] | None:
        """Execute ExifTool with standard options for fast metadata extraction."""
        # Normalize path for Windows compatibility
        from oncutf.utils.filesystem.path_normalizer import normalize_path

        file_path = normalize_path(file_path)

        if not Path(file_path).is_file():
            logger.warning("[ExifToolWrapper] File not found: %s", file_path)
            return None

        # Use UTF-8 charset for filename encoding (critical for Windows)
        from oncutf.config import EXIFTOOL_TIMEOUT_FAST

        # Use -api largefilesupport=1 for files larger than 2GB
        cmd = [
            self._exiftool_path,
            "-api",
            "largefilesupport=1",
            "-json",
            "-charset",
            "filename=UTF8",
            file_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=EXIFTOOL_TIMEOUT_FAST,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                logger.warning(
                    "[ExifToolWrapper] ExifTool returned error code %d for %s",
                    result.returncode,
                    file_path,
                )
                if result.stderr:
                    logger.warning("[ExifToolWrapper] ExifTool stderr: %s", result.stderr)
                return None

            # Success - reset error counter
            self._consecutive_errors = 0
            return self._parse_json_output(result.stdout)

        except subprocess.TimeoutExpired:
            logger.error("[ExifToolWrapper] Timeout executing exiftool for %s", file_path)
            self._last_error = f"Timeout executing exiftool for {file_path}"
            self._consecutive_errors += 1
            return None
        except Exception as e:
            logger.error("[ExifToolWrapper] Error executing exiftool for %s: %s", file_path, e)
            self._last_error = str(e)
            self._consecutive_errors += 1
            return None

    @staticmethod
    def _parse_json_output(output: str) -> dict[str, Any] | None:
        """Parse exiftool JSON output and return metadata dictionary."""
        try:
            if not output.strip():
                logger.warning("[ExifToolWrapper] Empty output from exiftool")
                return None

            data = json.loads(output)
            if isinstance(data, list) and len(data) > 0:
                result = data[0]
                return dict(result) if isinstance(result, dict) else None
            logger.warning("[ExifToolWrapper] Invalid JSON structure from exiftool")
            return None

        except json.JSONDecodeError as e:
            logger.error("[ExifToolWrapper] JSON decode error: %s", e)
            logger.debug(
                "[ExifToolWrapper] Raw output was: %s",
                repr(output),
                extra={"dev_only": True},
            )
            return None
        except Exception as e:
            logger.error("[ExifToolWrapper] Error parsing output: %s", e)
            return None

    def get_metadata_batch(
        self, file_paths: list[str], use_extended: bool = False
    ) -> list[dict[str, Any]]:
        """Load metadata for multiple files in a single ExifTool call (10x faster than individual calls).

        Args:
            file_paths: List of file paths to process
            use_extended: Whether to use extended metadata extraction

        Returns:
            List of metadata dictionaries, one per file (empty dict on error)

        """
        if not file_paths:
            return []

        try:
            cmd = [self._exiftool_path, "-json", "-G"]
            if use_extended:
                cmd.append("-a")  # All tags for extended mode
            cmd.extend(file_paths)

            from oncutf.config import (
                EXIFTOOL_TIMEOUT_BATCH_BASE,
                EXIFTOOL_TIMEOUT_BATCH_PER_FILE,
            )

            dynamic_timeout = max(
                EXIFTOOL_TIMEOUT_BATCH_BASE,
                len(file_paths) * EXIFTOOL_TIMEOUT_BATCH_PER_FILE,
            )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=dynamic_timeout,  # Dynamic timeout based on file count
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)

                # Mark extended metadata if requested
                if use_extended:
                    for metadata_dict in data:
                        metadata_dict["__extended__"] = True

                logger.debug(
                    "[ExifToolWrapper] Batch loaded metadata for %d files",
                    len(data),
                    extra={"dev_only": True},
                )
                return list(data)
            logger.warning(
                "[ExifToolWrapper] Batch metadata failed with code %d",
                result.returncode,
            )
            return [{} for _ in file_paths]

        except json.JSONDecodeError as e:
            logger.error("[ExifToolWrapper] JSON decode error in batch metadata: %s", e)
            return [{} for _ in file_paths]
        except Exception as e:
            logger.error("[ExifToolWrapper] Batch metadata error: %s", e)
            return [{} for _ in file_paths]

    def _get_metadata_extended(self, file_path: str) -> dict[str, Any] | None:
        """Uses a one-shot subprocess call with -ee for extended metadata.
        Parses and merges embedded entries, marks result as extended.
        """
        # Normalize path for Windows compatibility
        from oncutf.config import EXIFTOOL_TIMEOUT_EXTENDED
        from oncutf.utils.filesystem.path_normalizer import normalize_path

        file_path = normalize_path(file_path)

        if not Path(file_path).is_file():
            logger.warning("[ExtendedReader] File does not exist: %s", file_path)
            return None

        # Construct command with -ee flag for extended metadata and -api largefilesupport=1 for large files
        cmd = [
            self._exiftool_path,
            "-api",
            "largefilesupport=1",
            "-j",
            "-ee",
            file_path,
        ]
        logger.info("[ExtendedReader] Running command: %s", " ".join(cmd))

        try:
            # Use run() with timeout for simpler and more reliable execution
            # communicate() automatically handles stdout/stderr buffering
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=EXIFTOOL_TIMEOUT_EXTENDED,
                encoding="utf-8",
                errors="replace",
            )

            returncode = result.returncode
            stdout = result.stdout
            stderr = result.stderr

            if returncode != 0:
                # Suppress warnings for SIGTERM (-15) during shutdown
                # This is expected when ExifTool is terminated during app shutdown
                if returncode == -15:
                    logger.debug(
                        "[ExtendedReader] ExifTool process terminated (SIGTERM) for %s",
                        file_path,
                    )
                    return None

                logger.warning(
                    "[ExtendedReader] ExifTool returned error code %d for %s",
                    returncode,
                    file_path,
                )
                if stderr:
                    logger.warning("[ExtendedReader] ExifTool stderr: %s", stderr)
                return None

            # Parse JSON output
            data = json.loads(stdout)

            if not data:
                logger.warning("[ExtendedReader] No metadata returned.")
                return None

            logger.info(
                "[ExtendedReader] JSON object count: %d",
                len(data),
            )
            logger.info(
                "[ExtendedReader] Top-level keys: %s",
                list(data[0].keys())[:10],
            )

            result_dict = data[0]

            logger.info(
                "[ExtendedReader] Initial field count: %d",
                len(result_dict),
            )

            if len(data) > 1:
                for i, extra in enumerate(data[1:], start=1):
                    for key, value in extra.items():
                        new_key = f"[Segment {i}] {key}"
                        result_dict[new_key] = value
                logger.debug(
                    "[ExtendedReader] Merged %d embedded segments into result.",
                    len(data) - 1,
                    extra={"dev_only": True},
                )

            result_dict["__extended__"] = True
            logger.debug(
                "[ExtendedReader] Marked as extended: %s",
                file_path,
                extra={"dev_only": True},
            )
            logger.debug(
                "[ExtendedReader] Final keys: %s",
                list(result_dict.keys())[:10],
                extra={"dev_only": True},
            )
            logger.debug(
                "[ExtendedReader] __extended__ present? %s",
                "__extended__" in result_dict,
                extra={"dev_only": True},
            )
            logger.debug(
                "[ExtendedReader] Returning result for %s",
                file_path,
                extra={"dev_only": True},
            )

            return dict(result_dict)

        except subprocess.TimeoutExpired:
            # Timeout is expected for large video files - log as warning, not error
            filename = Path(file_path).name
            logger.warning(
                "[ExtendedReader] Timeout reading extended metadata for %s (exceeded %ss). This is normal for large files.",
                filename,
                EXIFTOOL_TIMEOUT_EXTENDED,
            )
            return None
        except Exception as e:
            logger.error("[ExtendedReader] Failed to read extended metadata: %s", e)
            return None

    def write_metadata(self, file_path: str, metadata_changes: dict[str, Any]) -> bool:
        """Writes metadata changes to a file using exiftool.

        Args:
            file_path (str): Full path to the file
            metadata_changes (dict): Dictionary of metadata changes to write
                       Format: {"EXIF:Rotation": "90", "IPTC:Keywords": "test"}

        Returns:
            bool: True if successful, False otherwise

        """
        # Normalize path for cross-platform compatibility (critical for Windows)
        from oncutf.utils.filesystem.path_normalizer import normalize_path

        file_path_normalized = normalize_path(file_path)

        if not Path(file_path_normalized).is_file():
            logger.warning("[ExifToolWrapper] File not found for writing: %s", file_path_normalized)
            return False

        if not metadata_changes:
            logger.warning("[ExifToolWrapper] No metadata changes provided")
            return False

        try:
            # Build exiftool command
            cmd = [self._exiftool_path, "-overwrite_original"]

            # Use the centralized metadata field mapping helper
            from oncutf.core.metadata.field_mapping_helper import (
                MetadataFieldMappingHelper,
            )

            # Prepare metadata changes using the field mapping helper
            prepared_changes = MetadataFieldMappingHelper.prepare_metadata_for_write(
                metadata_changes, file_path_normalized
            )

            # Add each prepared metadata change as a tag
            for tag_name, value in prepared_changes.items():
                logger.debug(
                    "[ExifToolWrapper] Adding tag: %s=%s",
                    tag_name,
                    value,
                    extra={"dev_only": True},
                )
                cmd.append(f"-{tag_name}={value}")

            cmd.append(file_path_normalized)

            logger.info(
                "[ExifToolWrapper] Writing metadata with command: %s",
                " ".join(cmd),
            )
            logger.info(
                "[ExifToolWrapper] Original metadata_changes: %s",
                metadata_changes,
            )

            # Execute the command
            from oncutf.config import EXIFTOOL_TIMEOUT_WRITE

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=EXIFTOOL_TIMEOUT_WRITE,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                logger.info(
                    "[ExifToolWrapper] Successfully wrote metadata to: %s",
                    Path(file_path_normalized).name,
                )
                return True
            logger.error("[ExifToolWrapper] Failed to write metadata: %s", result.stderr)
            logger.error("[ExifToolWrapper] Command was: %s", " ".join(cmd))
            return False

        except subprocess.TimeoutExpired:
            logger.error(
                "[ExifToolWrapper] Timeout while writing metadata to: %s",
                Path(file_path_normalized).name,
            )
            return False
        except Exception as e:
            logger.exception("[ExifToolWrapper] Exception while writing metadata")
            return False

    def close(
        self,
        *,
        try_graceful: bool = False,
        graceful_wait_s: float = 0.2,
        terminate_wait_s: float = 0.2,
        kill_wait_s: float = 0.1,
    ) -> None:
        """Shuts down the persistent ExifTool process.

        Notes:
            This method is used during app shutdown, often on the UI thread.
            Defaults are intentionally short/bounded to avoid Windows "Not Responding".

        Args:
            try_graceful: If True, attempt a stay_open False request first.
            graceful_wait_s: Max seconds to wait for a graceful exit.
            terminate_wait_s: Max seconds to wait after terminate().
            kill_wait_s: Max seconds to wait after kill().

        """
        proc = self.process
        if not proc:
            return

        try:
            with self.lock:  # Ensure thread-safe shutdown
                if try_graceful and proc.stdin and not proc.stdin.closed:
                    try:
                        proc.stdin.write("-stay_open\nFalse\n")
                        proc.stdin.flush()
                    except (BrokenPipeError, OSError, ValueError) as e:
                        logger.debug(
                            "[ExifToolWrapper] Expected error during graceful close: %s",
                            e,
                            extra={"dev_only": True},
                        )

                # Always close stdin best-effort (even on fast close).
                with contextlib.suppress(BrokenPipeError, OSError, ValueError, AttributeError):
                    if proc.stdin and not proc.stdin.closed:
                        proc.stdin.close()

                if try_graceful:
                    try:
                        proc.wait(timeout=graceful_wait_s)
                        logger.debug(
                            "[ExifToolWrapper] Process terminated gracefully",
                            extra={"dev_only": True},
                        )
                        return
                    except subprocess.TimeoutExpired:
                        logger.debug(
                            "[ExifToolWrapper] Graceful close timed out (%.2fs)",
                            graceful_wait_s,
                            extra={"dev_only": True},
                        )

                with contextlib.suppress(Exception):
                    proc.terminate()
                try:
                    proc.wait(timeout=terminate_wait_s)
                    return
                except subprocess.TimeoutExpired:
                    logger.debug(
                        "[ExifToolWrapper] Terminate timed out (%.2fs)",
                        terminate_wait_s,
                        extra={"dev_only": True},
                    )
                    with contextlib.suppress(Exception):
                        proc.kill()
                    with contextlib.suppress(subprocess.TimeoutExpired):
                        proc.wait(timeout=kill_wait_s)

        except Exception as e:
            logger.exception("[ExifToolWrapper] Error during shutdown")
            # Force kill as last resort
            try:
                if proc and proc.poll() is None:
                    proc.kill()
                    try:
                        proc.wait(timeout=kill_wait_s)
                    except subprocess.TimeoutExpired:
                        logger.error(
                            "[ExifToolWrapper] Zombie process detected",
                            extra={"dev_only": True},
                        )
            except Exception:
                pass
        finally:
            self.process = None
            logger.debug("[ExifToolWrapper] ExifTool wrapper closed", extra={"dev_only": True})

    @staticmethod
    def force_cleanup_all_exiftool_processes(
        *,
        max_scan_s: float = 0.5,
        graceful_wait_s: float = 0.5,
    ) -> None:
        """Force cleanup all ExifTool processes system-wide.

        Notes:
            This can run during app shutdown (often on the UI thread). The work is
            bounded via time caps to reduce the risk of Windows "Not Responding".

        Args:
            max_scan_s: Maximum time to spend scanning processes.
            graceful_wait_s: Maximum time to wait for terminate() before kill().

        """
        try:
            import importlib

            psutil = importlib.import_module("psutil")

            exiftool_processes = []
            scan_start = time.perf_counter()
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if (time.perf_counter() - scan_start) > max_scan_s:
                        logger.debug(
                            "[ExifToolWrapper] Process scan time limit reached (%.2fs)",
                            max_scan_s,
                            extra={"dev_only": True},
                        )
                        break
                    if proc.info["name"] and "exiftool" in proc.info["name"].lower():
                        exiftool_processes.append(proc)
                    elif proc.info["cmdline"]:
                        cmdline = " ".join(proc.info["cmdline"]).lower()
                        if "exiftool" in cmdline and "-stay_open" in cmdline:
                            exiftool_processes.append(proc)
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    pass

            if not exiftool_processes:
                logger.debug(
                    "[ExifToolWrapper] No orphaned ExifTool processes found",
                    extra={"dev_only": True},
                )
                return

            logger.warning(
                "[ExifToolWrapper] Found %d orphaned ExifTool processes",
                len(exiftool_processes),
                extra={"dev_only": True},
            )

            # Try to terminate gracefully first
            for proc in exiftool_processes:
                with contextlib.suppress(psutil.NoSuchProcess):
                    proc.terminate()

            # Wait briefly for graceful termination (bounded)
            wait_deadline = time.perf_counter() + max(0.0, graceful_wait_s)
            while time.perf_counter() < wait_deadline:
                remaining_count = 0
                for proc in exiftool_processes:
                    try:
                        if proc.is_running():
                            remaining_count += 1
                    except psutil.NoSuchProcess:
                        pass

                if remaining_count == 0:
                    break
                time.sleep(0.01)

            # Force kill any remaining processes
            remaining_processes = []
            for proc in exiftool_processes:
                try:
                    if proc.is_running():
                        remaining_processes.append(proc)
                except psutil.NoSuchProcess:
                    pass

            if remaining_processes:
                logger.warning(
                    "[ExifToolWrapper] Force killing %d ExifTool processes",
                    len(remaining_processes),
                    extra={"dev_only": True},
                )
                for proc in remaining_processes:
                    with contextlib.suppress(psutil.NoSuchProcess):
                        proc.kill()
            else:
                logger.debug(
                    "[ExifToolWrapper] No ExifTool processes to clean up",
                    extra={"dev_only": True},
                )

        except ImportError:
            logger.warning(
                "[ExifToolWrapper] psutil not available, cannot clean up orphaned processes",
                extra={"dev_only": True},
            )

    def is_healthy(self) -> bool:
        """Check if ExifTool wrapper is healthy.

        Returns:
            True if the process is running and no consecutive errors exceed threshold.

        """
        try:
            # Check if process is alive
            if self.process is None or self.process.poll() is not None:
                return False

            # Check error threshold (more than 5 consecutive errors = unhealthy)
            return not self._consecutive_errors > 5
        except Exception:
            return False

    def last_error(self) -> str | None:
        """Get the last error message.

        Returns:
            Last error message or None if no errors.

        """
        return self._last_error

    def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Dictionary with health status and metrics.

        """
        self._last_health_check = time.time()

        is_process_alive = False
        process_status = "unknown"

        try:
            if self.process is not None:
                poll_result = self.process.poll()
                is_process_alive = poll_result is None
                process_status = (
                    "running" if is_process_alive else f"terminated (code: {poll_result})"
                )
            # Removed unreachable else branch per mypy analysis
        except Exception as e:
            process_status = f"error: {e}"

        return {
            "healthy": self.is_healthy(),
            "process_alive": is_process_alive,
            "process_status": process_status,
            "last_error": self._last_error,
            "consecutive_errors": self._consecutive_errors,
            "last_check": self._last_health_check,
        }

    @staticmethod
    def cleanup_orphaned_processes() -> None:
        """Clean up orphaned ExifTool processes."""
        try:
            ExifToolWrapper.force_cleanup_all_exiftool_processes()
        except Exception as e:
            if "exiftool" in str(e).lower():
                logger.warning(
                    "[ExifToolWrapper] Error during ExifTool cleanup: %s",
                    e,
                    extra={"dev_only": True},
                )
            else:
                logger.debug(
                    "[ExifToolWrapper] No ExifTool processes to clean up",
                    extra={"dev_only": True},
                )
