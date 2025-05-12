"""
Module: metadata_reader.py

Author: Michael Economou
Date: 2025-05-01

This utility module defines a class responsible for extracting file metadata
using exiftool. It serves as an interface between the oncutf application and
the underlying metadata extraction process.

Supports reading creation date, modification date, camera info, and other
EXIF tags from image and video files.
"""

import subprocess
import json
from typing import Optional, Dict

# Initialize Logger
from utils.logger_helper import get_logger
logger = get_logger(__name__)


class MetadataReader:
    """
    A helper class that uses exiftool to extract metadata from files.
    """

    def __init__(self, exiftool_path: str = "exiftool") -> None:
        self.exiftool_path = exiftool_path

    def read_metadata(self, filepath: str) -> Optional[Dict[str, str]]:
        """
        Extracts metadata from a file using exiftool.

        Args:
            filepath (str): The full path to the file.

        Returns:
            dict or None: A dictionary of metadata fields and values, or None on failure.
        """
        try:
            result = subprocess.run(
                [self.exiftool_path, "-json", filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            metadata_list = json.loads(result.stdout)
            if metadata_list:
                return metadata_list[0]
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error reading metadata: {e}")
        return None

    def read_specific_fields(self, filepath: str, fields: list[str]) -> Dict[str, str]:
        """
        Extracts only specific metadata fields from a file.

        Args:
            filepath (str): Path to the file.
            fields (list): List of exiftool tags to retrieve.

        Returns:
            dict: Dictionary with requested fields.
        """
        command = [self.exiftool_path, "-json"] + [f"-{field}" for field in fields] + [filepath]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            metadata_list = json.loads(result.stdout)
            return metadata_list[0] if metadata_list else {}
        except Exception as e:
            print(f"Error reading fields {fields}: {e}")
            return {}
