"""
Module: exiftool_wrapper.py

Author: Michael Economou
Date: 2025-05-31

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

# Initialize Logger
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ExifToolWrapper:
    def __init__(self) -> None:
        """Starts the persistent ExifTool process with -stay_open enabled."""
        self.process = subprocess.Popen(
            ["exiftool", "-stay_open", "True", "-@", "-"],
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

        # Health tracking
        self._last_error: str | None = None
        self._last_health_check: float | None = None
        self._consecutive_errors: int = 0

    def __del__(self) -> None:
        """Destructor to ensure ExifTool process is cleaned up."""
        import contextlib

        with contextlib.suppress(Exception):
            self.close()

    def get_metadata(self, file_path: str, use_extended: bool = False) -> dict:
        """
        Get metadata for a single file using exiftool.

        Args:
            file_path: Path to the file
            use_extended: Whether to use extended metadata extraction

        Returns:
            Dictionary containing metadata
        """
        try:
            result = self._get_metadata_with_exiftool(file_path, use_extended)
            return result

        except Exception as e:
            logger.error(f"[ExifToolWrapper] Error getting metadata for {file_path}: {e}")
            return {}

    def _get_metadata_with_exiftool(self, file_path: str, use_extended: bool = False) -> dict:
        """Execute exiftool command and parse results."""
        if use_extended:
            result = self._get_metadata_extended(file_path)
        else:
            result = self._get_metadata_fast(file_path)

        # Convert None to empty dict for consistency
        return result if result is not None else {}

    def _get_metadata_fast(self, file_path: str) -> dict | None:
        """
        Execute ExifTool with standard options for fast metadata extraction.
        """
        # Normalize path for Windows compatibility
        from utils.path_normalizer import normalize_path

        file_path = normalize_path(file_path)

        if not os.path.isfile(file_path):
            logger.warning(f"[ExifToolWrapper] File not found: {file_path}")
            return None

        # Use UTF-8 charset for filename encoding (critical for Windows)
        cmd = ["exiftool", "-json", "-charset", "filename=UTF8", file_path]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                logger.warning(
                    f"[ExifToolWrapper] ExifTool returned error code {result.returncode} for {file_path}"
                )
                if result.stderr:
                    logger.warning(f"[ExifToolWrapper] ExifTool stderr: {result.stderr}")
                return None

            # Success - reset error counter
            self._consecutive_errors = 0
            return self._parse_json_output(result.stdout)

        except subprocess.TimeoutExpired:
            logger.error(f"[ExifToolWrapper] Timeout executing exiftool for {file_path}")
            self._last_error = f"Timeout executing exiftool for {file_path}"
            self._consecutive_errors += 1
            return None
        except Exception as e:
            logger.error(f"[ExifToolWrapper] Error executing exiftool for {file_path}: {e}")
            self._last_error = str(e)
            self._consecutive_errors += 1
            return None

    def _parse_json_output(self, output: str) -> dict | None:
        """Parse exiftool JSON output and return metadata dictionary."""
        try:
            if not output.strip():
                logger.warning("[ExifToolWrapper] Empty output from exiftool")
                return None

            data = json.loads(output)
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            else:
                logger.warning("[ExifToolWrapper] Invalid JSON structure from exiftool")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"[ExifToolWrapper] JSON decode error: {e}")
            logger.debug(
                f"[ExifToolWrapper] Raw output was: {repr(output)}", extra={"dev_only": True}
            )
            return None
        except Exception as e:
            logger.error(f"[ExifToolWrapper] Error parsing output: {e}")
            return None

    def get_metadata_batch(self, file_paths: list[str], use_extended: bool = False) -> list[dict]:
        """
        Load metadata for multiple files in a single ExifTool call (10x faster than individual calls).

        Args:
            file_paths: List of file paths to process
            use_extended: Whether to use extended metadata extraction

        Returns:
            List of metadata dictionaries, one per file (empty dict on error)
        """
        if not file_paths:
            return []

        try:
            cmd = ["exiftool", "-json", "-G"]
            if use_extended:
                cmd.append("-a")  # All tags for extended mode
            cmd.extend(file_paths)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(60, len(file_paths) * 0.5),  # Dynamic timeout based on file count
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
                    f"[ExifToolWrapper] Batch loaded metadata for {len(data)} files",
                    extra={"dev_only": True},
                )
                return data
            else:
                logger.warning(
                    f"[ExifToolWrapper] Batch metadata failed with code {result.returncode}"
                )
                return [{} for _ in file_paths]

        except json.JSONDecodeError as e:
            logger.error(f"[ExifToolWrapper] JSON decode error in batch metadata: {e}")
            return [{} for _ in file_paths]
        except Exception as e:
            logger.error(f"[ExifToolWrapper] Batch metadata error: {e}")
            return [{} for _ in file_paths]

    def _get_metadata_extended(self, file_path: str) -> dict | None:
        """
        Uses a one-shot subprocess call with -ee for extended metadata.
        Parses and merges embedded entries, marks result as extended.
        """
        # Normalize path for Windows compatibility
        from utils.path_normalizer import normalize_path

        file_path = normalize_path(file_path)

        if not os.path.isfile(file_path):
            logger.warning(f"[ExtendedReader] File does not exist: {file_path}")
            return None

        try:
            result = subprocess.run(
                ["exiftool", "-j", "-ee", file_path],
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                errors="replace",
            )
            data = json.loads(result.stdout)

            if not data:
                logger.warning("[ExtendedReader] No metadata returned.")
                return None

            logger.debug(
                f"[ExtendedReader] JSON object count: {len(data)}", extra={"dev_only": True}
            )
            logger.debug(
                f"[ExtendedReader] Top-level keys: {list(data[0].keys())[:10]}",
                extra={"dev_only": True},
            )

            result_dict = data[0]
            if len(data) > 1:
                for i, extra in enumerate(data[1:], start=1):
                    for key, value in extra.items():
                        new_key = f"[Segment {i}] {key}"
                        result_dict[new_key] = value
                logger.debug(
                    f"[ExtendedReader] Merged {len(data) - 1} embedded segments into result.",
                    extra={"dev_only": True},
                )

            result_dict["__extended__"] = True
            logger.debug(
                f"[ExtendedReader] Marked as extended: {file_path}", extra={"dev_only": True}
            )
            logger.debug(
                f"[ExtendedReader] Final keys: {list(result_dict.keys())[:10]}",
                extra={"dev_only": True},
            )
            logger.debug(
                f"[ExtendedReader] __extended__ present? {'__extended__' in result_dict}",
                extra={"dev_only": True},
            )
            logger.debug(
                f"[ExtendedReader] Returning result for {file_path}", extra={"dev_only": True}
            )

            return result_dict

        except Exception as e:
            logger.error(f"[ExtendedReader] Failed to read extended metadata: {e}", exc_info=True)
            return None

    def write_metadata(self, file_path: str, metadata_changes: dict) -> bool:
        """
        Writes metadata changes to a file using exiftool.

        Args:
            file_path (str): Full path to the file
            metadata_changes (dict): Dictionary of metadata changes to write
                       Format: {"EXIF:Rotation": "90", "IPTC:Keywords": "test"}

        Returns:
            bool: True if successful, False otherwise
        """
        # Normalize path for cross-platform compatibility (critical for Windows)
        from utils.path_normalizer import normalize_path

        file_path_normalized = normalize_path(file_path)

        if not os.path.isfile(file_path_normalized):
            logger.warning(f"[ExifToolWrapper] File not found for writing: {file_path_normalized}")
            return False

        if not metadata_changes:
            logger.warning("[ExifToolWrapper] No metadata changes provided")
            return False

        try:
            # Build exiftool command
            cmd = ["exiftool", "-overwrite_original"]

            # Add each metadata change as a tag
            for key, value in metadata_changes.items():
                # Handle special cases for rotation metadata
                key_lower = key.lower()
                if "rotation" in key_lower:
                    # Use the appropriate rotation tag based on file type
                    file_ext = os.path.splitext(file_path_normalized)[1].lower()

                    if file_ext in [".jpg", ".jpeg"]:
                        # For JPEG files, use EXIF:Orientation (1-8) or Rotation (0, 90, 180, 270)
                        if value in ["0", "90", "180", "270"]:
                            tag_name = "Rotation"
                        else:
                            tag_name = "EXIF:Orientation"
                    elif file_ext in [".mp4", ".mov", ".m4v", ".3gp"]:
                        # For QuickTime-based formats (MP4, MOV), use QuickTime:Rotation
                        # This is critical for proper rotation support in video files
                        tag_name = "QuickTime:Rotation"
                        logger.debug(
                            f"[ExifToolWrapper] Using QuickTime:Rotation for {file_ext} file",
                            extra={"dev_only": True},
                        )
                    elif file_ext in [".png"]:
                        # PNG doesn't support EXIF rotation, try XMP or just Rotation
                        tag_name = "Rotation"
                    elif file_ext in [".tiff", ".tif"]:
                        # TIFF supports EXIF:Orientation
                        if value in ["0", "90", "180", "270"]:
                            tag_name = "Rotation"
                        else:
                            tag_name = "EXIF:Orientation"
                    else:
                        # Generic rotation tag for other formats
                        tag_name = "Rotation"

                    logger.debug(
                        f"[ExifToolWrapper] Rotation: {key} -> {tag_name} = {value} for {file_ext}",
                        extra={"dev_only": True},
                    )
                else:
                    # Convert our format (e.g., "EXIF/DateTimeOriginal") to exiftool format
                    tag_name = key.replace("/", ":")

                cmd.append(f"-{tag_name}={value}")

            cmd.append(file_path_normalized)

            logger.debug(
                f"[ExifToolWrapper] Writing metadata with command: {' '.join(cmd)}",
                extra={"dev_only": True},
            )
            logger.debug(
                f"[ExifToolWrapper] Original metadata_changes: {metadata_changes}",
                extra={"dev_only": True},
            )

            # Execute the command
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace"
            )

            if result.returncode == 0:
                logger.info(
                    f"[ExifToolWrapper] Successfully wrote metadata to: {os.path.basename(file_path_normalized)}"
                )
                return True
            else:
                logger.error(f"[ExifToolWrapper] Failed to write metadata: {result.stderr}")
                logger.error(f"[ExifToolWrapper] Command was: {' '.join(cmd)}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(
                f"[ExifToolWrapper] Timeout while writing metadata to: {os.path.basename(file_path_normalized)}"
            )
            return False
        except Exception as e:
            logger.error(f"[ExifToolWrapper] Exception while writing metadata: {e}", exc_info=True)
            return False

    def close(self) -> None:
        """Shuts down the persistent ExifTool process cleanly."""
        if not self.process:
            return

        try:
            with self.lock:  # Ensure thread-safe shutdown
                # First try to close gracefully
                if self.process.stdin and not self.process.stdin.closed:
                    try:
                        self.process.stdin.write("-stay_open\nFalse\n")
                        self.process.stdin.flush()
                    except (BrokenPipeError, OSError, ValueError) as e:
                        # Process may have already terminated or stdin is closed
                        logger.debug(
                            f"[ExifToolWrapper] Expected error during graceful close: {e}",
                            extra={"dev_only": True},
                        )
                    finally:
                        import contextlib

                        with contextlib.suppress(BrokenPipeError, OSError, ValueError):
                            # Ignore errors when closing stdin
                            self.process.stdin.close()

                # Wait for process to terminate gracefully
                try:
                    self.process.wait(timeout=3)
                    logger.debug(
                        "[ExifToolWrapper] Process terminated gracefully", extra={"dev_only": True}
                    )
                except subprocess.TimeoutExpired:
                    # Force terminate if it doesn't close gracefully
                    logger.warning(
                        "[ExifToolWrapper] Process didn't terminate gracefully, forcing termination",
                        extra={"dev_only": True},
                    )
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        # Last resort: kill the process
                        logger.warning(
                            "[ExifToolWrapper] Force killing ExifTool process",
                            extra={"dev_only": True},
                        )
                        self.process.kill()
                        try:
                            self.process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            logger.error(
                                "[ExifToolWrapper] Process refused to die, may be zombie",
                                extra={"dev_only": True},
                            )

        except Exception as e:
            logger.error(f"[ExifToolWrapper] Error during shutdown: {e}", exc_info=True)
            # Force kill as last resort
            try:
                if self.process and self.process.poll() is None:
                    self.process.kill()
                    try:
                        self.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        logger.error(
                            "[ExifToolWrapper] Zombie process detected", extra={"dev_only": True}
                        )
            except Exception:
                pass
        finally:
            self.process = None
            logger.debug("[ExifToolWrapper] ExifTool wrapper closed", extra={"dev_only": True})

    @staticmethod
    def force_cleanup_all_exiftool_processes() -> None:
        """Force cleanup all ExifTool processes system-wide."""
        try:
            import time

            import psutil  # type: ignore

            exiftool_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] and "exiftool" in proc.info["name"].lower():
                        exiftool_processes.append(proc)
                    elif proc.info["cmdline"]:
                        cmdline = " ".join(proc.info["cmdline"]).lower()
                        if "exiftool" in cmdline and "-stay_open" in cmdline:
                            exiftool_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            if not exiftool_processes:
                logger.debug(
                    "[ExifToolWrapper] No orphaned ExifTool processes found",
                    extra={"dev_only": True},
                )
                return

            logger.warning(
                f"[ExifToolWrapper] Found {len(exiftool_processes)} orphaned ExifTool processes",
                extra={"dev_only": True},
            )

            # Try to terminate gracefully first
            for proc in exiftool_processes:
                with contextlib.suppress(psutil.NoSuchProcess):
                    proc.terminate()

            # Wait a bit for graceful termination
            time.sleep(0.5)

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
                    f"[ExifToolWrapper] Force killing {len(remaining_processes)} ExifTool processes",
                    extra={"dev_only": True},
                )
                for proc in remaining_processes:
                    with contextlib.suppress(psutil.NoSuchProcess):
                        proc.kill()
            else:
                logger.debug(
                    "[ExifToolWrapper] No ExifTool processes to clean up", extra={"dev_only": True}
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

    def health_check(self) -> dict[str, any]:
        """Perform comprehensive health check.

        Returns:
            Dictionary with health status and metrics.
        """
        import time

        self._last_health_check = time.time()

        is_process_alive = False
        process_status = "unknown"

        try:
            if self.process is not None:
                poll_result = self.process.poll()
                is_process_alive = poll_result is None
                process_status = "running" if is_process_alive else f"terminated (code: {poll_result})"
            else:
                process_status = "not initialized"
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
                        f"[ExifToolWrapper] Error during ExifTool cleanup: {e}",
                        extra={"dev_only": True},
                    )
                else:
                    logger.debug(
                    "[ExifToolWrapper] No ExifTool processes to clean up", extra={"dev_only": True}
                )
