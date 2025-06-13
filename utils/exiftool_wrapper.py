"""
exiftool_wrapper.py

Author: Michael Economou
Date: 2025-05-22

This module provides a lightweight ExifTool wrapper using a persistent
'-stay_open True' process for fast metadata extraction. For extended metadata,
it falls back to a one-shot subprocess call with '-ee'.

Requires: exiftool installed and in PATH
"""

import json
import os
import subprocess
import threading
import time
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

    def get_metadata(self, file_path: str, use_extended: bool = False) -> Optional[dict]:
        """
        Executes an ExifTool query for a single file.

        Args:
            file_path (str): Full path to the media file.
            use_extended (bool): Whether to include -ee for embedded streams.

        Returns:
            Optional[dict]: Metadata dictionary or None if parsing fails.
        """
        logger.debug(f"[ExifToolWrapper] get_metadata() CALLED for: {file_path}, extended={use_extended}")

        if use_extended:
            result = self._get_metadata_extended(file_path)
        else:
            result = self._get_metadata_fast(file_path)

        if isinstance(result, dict):
            logger.debug(f"[ExifToolWrapper] Result for {file_path} has {len(result)} keys", extra={"dev_only": True})
            logger.debug(f"[ExifToolWrapper] FIRST KEYS: {list(result.keys())[:10]}", extra={"dev_only": True})
        else:
            logger.warning(f"[ExifToolWrapper] Failed or non-dict result for {file_path}: {type(result)}")

        return result

    def _get_metadata_fast(self, file_path: str) -> Optional[dict]:
        """
        Uses a persistent exiftool -stay_open process to retrieve metadata.
        Communicates via stdin/stdout with a custom execute marker.

        Args:
            file_path (str): Path to the media file.

        Returns:
            dict or None: Extracted metadata or None on failure.
        """
        if not os.path.isfile(file_path):
            logger.warning(f"[ExifToolWrapper] File not found: {file_path}")
            return None

        self.counter += 1
        tag = f"{self.counter:05d}"  # zero-padded tag like 00001
        marker = f"{{ready{tag}}}"

        command = f"-j\n{file_path}\n-execute{tag}\n"

        with self.lock:
            try:
                logger.debug(f"[ExifToolWrapper] Sending command (tag={tag}) for: {file_path}")
                self.process.stdin.write(command)
                self.process.stdin.flush()

                output_lines = []
                start_time = time.time()
                timeout_seconds = 5

                while True:
                    if time.time() - start_time > timeout_seconds:
                        logger.warning(f"[ExifToolWrapper] Timeout waiting for response (tag={tag})")
                        return None

                    line = self.process.stdout.readline()
                    if not line:
                        logger.warning(f"[ExifToolWrapper] Unexpected EOF from exiftool (tag={tag})")
                        return None

                    stripped = line.strip()
                    logger.debug(f"[ExifToolWrapper] STDOUT: {stripped}", extra={"dev_only": True})
                    if stripped == marker:
                        logger.debug(f"[ExifToolWrapper] Received marker: {marker}", extra={"dev_only": True})
                        break

                    output_lines.append(line)

                output = ''.join(output_lines)
                data = json.loads(output)
                return data[0] if data else None

            except Exception as e:
                logger.error(f"[ExifToolWrapper] Exception during metadata read: {e}", exc_info=True)
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

    def close(self) -> None:
        """Shuts down the persistent ExifTool process cleanly."""
        try:
            if self.process and self.process.stdin:
                self.process.stdin.write("-stay_open\nFalse\n")
                self.process.stdin.flush()
                self.process.communicate(timeout=5)
        except Exception:
            # print(f"[ExifToolWrapper] Shutdown error: {e}")
            pass
        finally:
            self.process = None
