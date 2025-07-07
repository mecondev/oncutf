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
import json
import os
import subprocess
import threading
from typing import Optional

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
            bufsize=1  # line buffered
        )
        self.lock = threading.Lock()  # Ensure thread-safe access
        self.counter = 0  # To generate unique termination tags

    def __del__(self) -> None:
        """Destructor to ensure ExifTool process is cleaned up."""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during cleanup

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

    def _get_metadata_fast(self, file_path: str) -> Optional[dict]:
        """
        Execute ExifTool with standard options for fast metadata extraction.
        """
        if not os.path.isfile(file_path):
            logger.warning(f"[ExifToolWrapper] File not found: {file_path}")
            return None

        cmd = [
            'exiftool',
            '-json',
            '-charset', 'filename=UTF8',
            file_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)

            if result.returncode != 0:
                logger.warning(f"[ExifToolWrapper] ExifTool returned error code {result.returncode} for {file_path}")
                if result.stderr:
                    logger.warning(f"[ExifToolWrapper] ExifTool stderr: {result.stderr}")
                return None

            return self._parse_json_output(result.stdout)

        except subprocess.TimeoutExpired:
            logger.error(f"[ExifToolWrapper] Timeout executing exiftool for {file_path}")
            return None
        except Exception as e:
            logger.error(f"[ExifToolWrapper] Error executing exiftool for {file_path}: {e}")
            return None

    def _parse_json_output(self, output: str) -> Optional[dict]:
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
            logger.debug(f"[ExifToolWrapper] Raw output was: {repr(output)}")
            return None
        except Exception as e:
            logger.error(f"[ExifToolWrapper] Error parsing output: {e}")
            return None

    def _get_metadata_extended(self, file_path: str) -> Optional[dict]:
        """
        Uses a one-shot subprocess call with -ee for extended metadata.
        Parses and merges embedded entries, marks result as extended.
        """
        if not os.path.isfile(file_path):
            logger.warning(f"[ExtendedReader] File does not exist: {file_path}")
            return None

        try:
            result = subprocess.run(
                ["exiftool", "-j", "-ee", file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            data = json.loads(result.stdout)

            if not data:
                logger.warning("[ExtendedReader] No metadata returned.")
                return None

            logger.debug(f"[ExtendedReader] JSON object count: {len(data)}", extra={"dev_only": True})
            logger.debug(f"[ExtendedReader] Top-level keys: {list(data[0].keys())[:10]}", extra={"dev_only": True})

            result_dict = data[0]
            if len(data) > 1:
                for i, extra in enumerate(data[1:], start=1):
                    for key, value in extra.items():
                        new_key = f"[Segment {i}] {key}"
                        result_dict[new_key] = value
                logger.debug(f"[ExtendedReader] Merged {len(data) - 1} embedded segments into result.", extra={"dev_only": True})

            result_dict["__extended__"] = True
            logger.debug(f"[ExtendedReader] Marked as extended: {file_path}", extra={"dev_only": True})
            logger.debug(f"[ExtendedReader] Final keys: {list(result_dict.keys())[:10]}", extra={"dev_only": True})
            logger.debug(f"[ExtendedReader] __extended__ present? {'__extended__' in result_dict}", extra={"dev_only": True})
            logger.debug(f"[ExtendedReader] Returning result for {file_path}", extra={"dev_only": True})

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
        if not os.path.isfile(file_path):
            logger.warning(f"[ExifToolWrapper] File not found for writing: {file_path}")
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
                    file_ext = os.path.splitext(file_path)[1].lower()

                    if file_ext in ['.jpg', '.jpeg']:
                        # For JPEG files, use EXIF:Orientation (1-8) or Rotation (0, 90, 180, 270)
                        if value in ['0', '90', '180', '270']:
                            tag_name = "Rotation"
                        else:
                            tag_name = "EXIF:Orientation"
                    elif file_ext in ['.png']:
                        # PNG doesn't support EXIF rotation, try XMP or just Rotation
                        tag_name = "Rotation"
                    elif file_ext in ['.tiff', '.tif']:
                        # TIFF supports EXIF:Orientation
                        if value in ['0', '90', '180', '270']:
                            tag_name = "Rotation"
                        else:
                            tag_name = "EXIF:Orientation"
                    else:
                        # Generic rotation tag for other formats
                        tag_name = "Rotation"

                    logger.debug(f"[ExifToolWrapper] Rotation: {key} -> {tag_name} = {value} for {file_ext}", extra={"dev_only": True})
                else:
                    # Convert our format (e.g., "EXIF/DateTimeOriginal") to exiftool format
                    tag_name = key.replace("/", ":")

                cmd.append(f"-{tag_name}={value}")

            cmd.append(file_path)

            logger.debug(f"[ExifToolWrapper] Writing metadata with command: {' '.join(cmd)}")
            logger.debug(f"[ExifToolWrapper] Original metadata_changes: {metadata_changes}", extra={"dev_only": True})

            # Execute the command
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"[ExifToolWrapper] Successfully wrote metadata to: {file_path}")
                return True
            else:
                logger.error(f"[ExifToolWrapper] Failed to write metadata: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"[ExifToolWrapper] Timeout while writing metadata to: {file_path}")
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
                        logger.debug(f"[ExifToolWrapper] Expected error during graceful close: {e}")
                    finally:
                        try:
                            self.process.stdin.close()
                        except (BrokenPipeError, OSError, ValueError):
                            # Ignore errors when closing stdin
                            pass

                # Wait for process to terminate gracefully
                try:
                    self.process.wait(timeout=3)
                    logger.debug("[ExifToolWrapper] Process terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force terminate if it doesn't close gracefully
                    logger.warning("[ExifToolWrapper] Process didn't terminate gracefully, forcing termination")
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        # Last resort: kill the process
                        logger.warning("[ExifToolWrapper] Force killing ExifTool process")
                        self.process.kill()
                        try:
                            self.process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            logger.error("[ExifToolWrapper] Process refused to die, may be zombie")

        except Exception as e:
            logger.warning(f"[ExifToolWrapper] Error during shutdown: {e}")
            # Force kill as last resort
            try:
                if self.process and self.process.poll() is None:
                    self.process.kill()
                    try:
                        self.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        logger.error("[ExifToolWrapper] Zombie process detected")
            except Exception:
                pass
        finally:
            self.process = None
            logger.debug("[ExifToolWrapper] ExifTool wrapper closed")

    @staticmethod
    def force_cleanup_all_exiftool_processes() -> None:
        """Force cleanup all ExifTool processes system-wide."""
        try:
            import psutil
            killed_count = 0

            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'exiftool' in proc.info['name'].lower():
                        logger.warning(f"[ExifToolWrapper] Killing orphaned ExifTool process: PID {proc.info['pid']}")
                        proc.kill()
                        killed_count += 1
                    elif proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline']).lower()
                        if 'exiftool' in cmdline and '-stay_open' in cmdline:
                            logger.warning(f"[ExifToolWrapper] Killing orphaned ExifTool process: PID {proc.info['pid']}")
                            proc.kill()
                            killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            if killed_count > 0:
                logger.info(f"[ExifToolWrapper] Cleaned up {killed_count} orphaned ExifTool processes")
            else:
                logger.debug("[ExifToolWrapper] No orphaned ExifTool processes found")

        except ImportError:
            # Fallback to system commands if psutil not available
            try:
                import os
                import subprocess

                if os.name == 'posix':  # Linux/macOS
                    result = subprocess.run(['pkill', '-f', 'exiftool.*stay_open'],
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info("[ExifToolWrapper] Cleaned up ExifTool processes via pkill")
                    else:
                        logger.debug("[ExifToolWrapper] No ExifTool processes to clean up")
                else:  # Windows
                    result = subprocess.run(['taskkill', '/F', '/IM', 'exiftool.exe'],
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info("[ExifToolWrapper] Cleaned up ExifTool processes via taskkill")
                    else:
                        logger.debug("[ExifToolWrapper] No ExifTool processes to clean up")

            except Exception as e:
                logger.warning(f"[ExifToolWrapper] Failed to cleanup ExifTool processes: {e}")

        except Exception as e:
            logger.warning(f"[ExifToolWrapper] Error during force cleanup: {e}")
