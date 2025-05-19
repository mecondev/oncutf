"""
Module: metadata_reader.py

Author: Michael Economou
Date: 2025-05-01 (refactored)

This module defines the MetadataReader class, responsible for extracting metadata
from media files using the external tool `exiftool`. It is designed to be cancellable
during long-running operations and integrates with threaded workflows.

Features:
- Subprocess-based metadata reading using exiftool.
- Cancellation support via thread-safe flag.
- Timeout handling and fallback termination (terminate + kill).
"""

import subprocess
import json
import threading
import time
from typing import Optional, Dict

from utils.logger_helper import get_logger

logger = get_logger(__name__)

class MetadataReader:
    """
    Reads metadata from a file using exiftool via subprocess.

    Supports cancellation during metadata reading to allow graceful interruption
    when used in threaded applications (e.g., batch processing with GUI).

    Attributes:
        exiftool_path (str): The path to the exiftool executable.
    """

    def __init__(self, exiftool_path: str = "exiftool") -> None:
        """
        Initializes the MetadataReader.

        Args:
            exiftool_path (str): Path to the exiftool executable (default: "exiftool").
        """
        self.exiftool_path = exiftool_path
        self._active_proc: Optional[subprocess.Popen] = None
        self._cancel_requested = threading.Event()
        self._lock = threading.Lock()

    def cancel_active(self) -> None:
        """
        Signals cancellation of the currently active metadata reading process.

        This sets the cancel flag and attempts to terminate the subprocess if running.
        """
        logger.warning("[MetadataReader] cancel_active() CALLED")
        self._cancel_requested.set()
        with self._lock:
            if self._active_proc and self._active_proc.poll() is None:
                try:
                    self._active_proc.terminate()
                    logger.warning("[MetadataReader] Terminated active exiftool subprocess.")
                except Exception as e:
                    logger.warning(f"[MetadataReader] Failed to terminate exiftool: {e}")

    def read_metadata(self, filepath: str, timeout: int = 10) -> Optional[Dict[str, str]]:
        """
        Reads metadata for a single file using exiftool.

        This function launches exiftool as a subprocess and parses the output.
        It can be cancelled gracefully via `cancel_active()`.

        Args:
            filepath (str): Absolute path to the file to analyze.
            timeout (int): Maximum time (in seconds) to allow the exiftool process to run.

        Returns:
            Optional[Dict[str, str]]: Metadata dictionary if successful, otherwise empty or None.
        """
        self._cancel_requested.clear()
        result: Dict[str, str] = {}

        try:
            logger.warning(f"[Reader] START for: {filepath}")
            proc = subprocess.Popen(
                [self.exiftool_path, "-json", filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )

            with self._lock:
                self._active_proc = proc

            # Poll the process until it finishes or cancellation/timeout occurs
            start_time = time.time()
            while proc.poll() is None:
                if self._cancel_requested.is_set():
                    proc.terminate()
                    logger.warning("[Reader] Cancelled via flag.")
                    return {}
                if time.time() - start_time > timeout:
                    proc.terminate()
                    logger.warning("[Reader] Timeout reached, terminating process.")
                    break
                time.sleep(0.1)

            logger.debug(f"[Reader] Calling communicate() for: {filepath}")
            try:
                output, _ = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                logger.warning(f"[Reader] Timeout on communicate() for: {filepath}")
                try:
                    proc.kill()
                    output, _ = proc.communicate(timeout=1)
                    logger.warning(f"[Reader] Forced kill + communicate() recovered for: {filepath}")
                except Exception as e:
                    logger.error(f"[Reader] Failed to kill/cleanup after timeout: {e}")
                    return {}

            # Parse JSON output
            metadata_list = json.loads(output)
            if metadata_list:
                result.update(metadata_list[0])
                logger.warning(f"[Reader] FINISHED for: {filepath}")

        except Exception as e:
            logger.warning(f"[MetadataReader] Failed to read metadata: {e}")
        finally:
            with self._lock:
                self._active_proc = None

        return result

    def read(self, filepath: str) -> Dict[str, str]:
        """
        Convenience wrapper for read_metadata used in single-file preview (e.g. right-click).
        Returns a metadata dictionary or empty dict on failure.
        """
        return self.read_metadata(filepath) or {}

