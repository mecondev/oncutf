"""Module: metadata_exporter.py.

Author: Michael Economou
Date: 2025-06-10

utils/metadata_exporter.py
Metadata export utility supporting multiple human-readable formats.
Exports metadata with proper grouping, hash information, and application branding.
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from oncutf.config import APP_NAME, APP_VERSION, EXPORT_DATE_FORMAT
from oncutf.ui.managers.tree_model_builder import classify_key
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataExporter:
    """Handles exporting metadata in various human-readable formats.
    Supports JSON, Markdown, and CSV with proper grouping and branding.
    """

    def __init__(self, parent_window: Any = None) -> None:
        """Initialize the exporter with optional parent window for dialogs."""
        self.parent_window = parent_window
        self.app_name = APP_NAME
        self.app_version = f"v{APP_VERSION}"

    def _get_export_timestamp(self) -> str:
        """Get formatted timestamp for export operations."""
        return datetime.now().strftime(EXPORT_DATE_FORMAT)

    def export_selected_files(self, output_dir: str, format_type: str = "json") -> bool:
        """Export metadata for selected files.

        Args:
            output_dir: Directory to save export files
            format_type: Export format ("json", "markdown", "csv")

        Returns:
            bool: True if export successful

        """
        if not self.parent_window:
            logger.error("[MetadataExporter] No parent window available")
            return False

        # Get selected files
        selected_files = self._get_selected_files()
        if not selected_files:
            logger.warning("[MetadataExporter] No files selected for export")
            return False

        return self._export_files(selected_files, output_dir, format_type, "selected")

    def export_all_files(self, output_dir: str, format_type: str = "json") -> bool:
        """Export metadata for all files in the current folder.

        Args:
            output_dir: Directory to save export files
            format_type: Export format ("json", "markdown", "csv")

        Returns:
            bool: True if export successful

        """
        if not self.parent_window:
            logger.error("[MetadataExporter] No parent window available")
            return False

        # Get all files
        all_files = self._get_all_files()
        if not all_files:
            logger.warning("[MetadataExporter] No files available for export")
            return False

        return self._export_files(all_files, output_dir, format_type, "all")

    def export_files(self, files: list[Any], output_dir: str, format_type: str = "json") -> bool:
        """Export metadata for a specific list of files.

        Args:
            files: List of file items to export
            output_dir: Directory to save export files
            format_type: Export format ("json", "markdown", "csv")

        Returns:
            bool: True if export successful

        """
        if not files:
            logger.warning("[MetadataExporter] No files provided for export")
            return False

        return self._export_files(files, output_dir, format_type, "custom")

    def _get_selected_files(self) -> list[Any]:
        """Get currently selected files from file table."""
        if not self.parent_window:
            return []

        # Use unified selection method
        return self.parent_window.get_selected_files_ordered()

    def _get_all_files(self) -> list[Any]:
        """Get all files from file model."""
        if not (hasattr(self.parent_window, "file_model") and self.parent_window.file_model.files):
            return []

        return self.parent_window.file_model.files

    def _export_files(
        self, files: list[Any], output_dir: str, format_type: str, scope: str
    ) -> bool:
        """Export metadata for a list of files.

        Args:
            files: List of file items to export
            output_dir: Output directory
            format_type: Export format
            scope: "selected" or "all"

        """
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            if format_type == "markdown":
                return self._export_markdown(files, output_dir, scope)
            return self._export_json(files, output_dir, scope)

        except Exception as e:
            logger.exception("[MetadataExporter] Export failed")
            return False

    def _export_json(self, files: list[Any], output_dir: str, _scope: str) -> bool:
        """Export metadata in JSON format - one file per source file."""
        try:
            exported_count = 0

            for file_item in files:
                file_data = self._prepare_file_data(file_item)
                if not file_data:
                    continue

                # Create individual export data
                export_data = {
                    "export_info": {
                        "application": self.app_name,
                        "version": self.app_version,
                        "exported_at": datetime.now().isoformat(),
                        "export_date": self._get_export_timestamp(),
                        "scope": "individual",
                        "format": "json",
                    },
                    "file": file_data,
                }

                # Generate filename based on source file
                source_filename = file_data["filename"]
                name_without_ext = Path(source_filename).stem
                output_filename = f"{name_without_ext}.json"
                output_path = str(Path(output_dir) / output_filename)

                # Write individual JSON file
                with Path(output_path).open("w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                exported_count += 1
                logger.debug("[MetadataExporter] Exported JSON for: %s", source_filename)

            logger.info("[MetadataExporter] JSON export completed: %d files", exported_count)
        except Exception:
            logger.exception("[MetadataExporter] JSON export failed")
            return False
        else:
            return exported_count > 0

    def _export_markdown(self, files: list[Any], output_dir: str, _scope: str) -> bool:
        """Export metadata in Markdown format - one file per source file."""
        try:
            exported_count = 0

            for file_item in files:
                file_data = self._prepare_file_data(file_item)
                if not file_data:
                    continue

                # Generate filename based on source file
                source_filename = file_data["filename"]
                name_without_ext = Path(source_filename).stem
                output_filename = f"{name_without_ext}.md"
                output_path = str(Path(output_dir) / output_filename)

                with Path(output_path).open("w", encoding="utf-8") as f:
                    # Header with branding (no logo, no bold, no colons)
                    f.write(f"# Metadata Report - {file_data['filename']}\n\n")
                    f.write(f"Generated by {self.app_name} {self.app_version}  \n")
                    f.write(f"Export Date {self._get_export_timestamp()}  \n")
                    f.write(f"File Size {file_data['file_size']}  \n")

                    # Hash information if available
                    if file_data.get("hash_info"):
                        hash_info = file_data["hash_info"]
                        f.write(f"Hash ({hash_info['algorithm']}) {hash_info['value']}  \n")

                    f.write(f"Metadata Type {file_data['metadata_type']}  \n\n")
                    f.write("---\n\n")

                    # Metadata groups
                    if file_data.get("metadata_groups"):
                        for group_name, group_data in file_data["metadata_groups"].items():
                            extended_count = group_data.get("extended_count", 0)
                            total_count = group_data.get("total_count", 0)

                            if extended_count > 0:
                                f.write(
                                    f"<h2> {group_name} [Extended] ({total_count} keys, {extended_count} extended)\n\n"
                                )
                            else:
                                f.write(f"<h2> {group_name} ({total_count} keys)\n\n")

                            # Write metadata items (no bold formatting, no colons)
                            for key, value in group_data.get("items", {}).items():
                                extended_keys_list = group_data.get("extended_keys", [])
                                is_extended = key in extended_keys_list
                                prefix = "[Ext] " if is_extended else ""
                                # Truncate long values
                                display_value = str(value)
                                if len(display_value) > 100:
                                    display_value = display_value[:100] + "..."
                                f.write(f"- {prefix}{key} {display_value}\n")

                            f.write("\n")
                    else:
                        f.write("No metadata available for this file.\n\n")

                    # Footer
                    f.write(
                        f"\n*Report generated by {self.app_name} {self.app_version} on {self._get_export_timestamp()}*\n"
                    )

                exported_count += 1
                logger.debug("[MetadataExporter] Exported Markdown for: %s", source_filename)

            logger.info("[MetadataExporter] Markdown export completed: %d files", exported_count)
        except Exception:
            logger.exception("[MetadataExporter] Markdown export failed")
            return False
        else:
            return exported_count > 0

    def _prepare_file_data(self, file_item: Any) -> dict[str, Any] | None:
        """Prepare file data for export including metadata grouping and hash info.

        Args:
            file_item: FileItem object

        Returns:
            dict: Prepared file data or None if no metadata available

        """
        try:
            # Basic file info
            file_data = {
                "filename": getattr(file_item, "filename", "Unknown"),
                "full_path": getattr(file_item, "full_path", ""),
                "file_size": self._format_file_size(getattr(file_item, "file_size", 0)),
            }

            # Get hash information if available
            hash_info = self._get_hash_info(file_item)
            if hash_info:
                file_data["hash_info"] = hash_info

            # Get metadata from cache
            metadata = self._get_metadata_for_file(file_item)
            if not metadata:
                file_data["metadata_type"] = "No metadata available"
                return file_data

            # Determine metadata type
            is_extended = metadata.get("__extended__", False)
            file_data["metadata_type"] = "Extended" if is_extended else "Fast"

            # Group metadata
            grouped_metadata = self._group_metadata(metadata)
            if grouped_metadata:
                file_data["metadata_groups"] = grouped_metadata
        except Exception:
            logger.exception("[MetadataExporter] Error preparing file data")
            return None
        else:
            return file_data

    def _get_hash_info(self, file_item: Any) -> dict[str, str] | None:
        """Get hash information for a file if available."""
        try:
            # Check if file has hash information
            if hasattr(file_item, "file_hash") and file_item.file_hash:
                return {
                    "algorithm": "CRC32",  # Default algorithm used by the app
                    "value": file_item.file_hash,
                }

            # Use HashManager to get hash (supports persistent cache)
            if hasattr(file_item, "full_path"):
                try:
                    from oncutf.core.hash.hash_manager import HashManager

                    hash_manager = HashManager()
                    hash_value = hash_manager.calculate_hash(file_item.full_path)
                    if hash_value:
                        return {"algorithm": "CRC32", "value": hash_value}
                except Exception as e:
                    logger.debug("[MetadataExporter] HashManager error: %s", e)
        except Exception as e:
            logger.debug("[MetadataExporter] Could not get hash info: %s", e)
            return None
        else:
            return None

    def _get_metadata_for_file(self, file_item: Any) -> dict[str, Any] | None:
        """Get metadata for a file from cache or file item using file_status_helpers."""
        try:
            # Use file_status_helpers for direct cache access
            from oncutf.utils.filesystem.file_status_helpers import (
                get_metadata_for_file,
            )

            if hasattr(file_item, "full_path"):
                metadata = get_metadata_for_file(file_item.full_path)
                if metadata:
                    return metadata

            # Fallback to file item metadata if no cache available
            if hasattr(file_item, "metadata") and file_item.metadata:
                return file_item.metadata
        except Exception as e:
            logger.debug("[MetadataExporter] Could not get metadata: %s", e)
            return None
        else:
            return None

    def _group_metadata(self, metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Group metadata by categories with extended key detection."""
        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "items": {},
                "extended_keys": set(),
                "total_count": 0,
                "extended_count": 0,
            }
        )

        # Detect extended keys
        extended_keys = set()
        if metadata.get("__extended__"):
            for key in metadata:
                if key.startswith("__"):
                    continue
                key_lower = key.lower()
                # Heuristic detection for extended-only keys
                if any(
                    pattern in key_lower
                    for pattern in [
                        "accelerometer",
                        "gyro",
                        "pitch",
                        "roll",
                        "yaw",
                        "segment",
                        "embedded",
                        "extended",
                        "iso",
                        "aperture",
                        "fnumber",
                        "exposure",
                        "shutter",
                    ]
                ):
                    extended_keys.add(key)

        # Group metadata
        for key, value in metadata.items():
            if key.startswith("__"):
                continue

            group = classify_key(key)
            grouped[group]["items"][key] = value
            grouped[group]["total_count"] += 1

            if key in extended_keys:
                grouped[group]["extended_keys"].add(key)
                grouped[group]["extended_count"] += 1

        # Convert sets to lists for JSON serialization and defaultdict to regular dict
        result = {}
        for group_name, group_data in grouped.items():
            result[group_name] = {
                "items": group_data["items"],
                "extended_keys": list(group_data["extended_keys"]),  # Convert set to list
                "total_count": group_data["total_count"],
                "extended_count": group_data["extended_count"],
            }

        return result

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024
            i += 1

        return f"{size:.1f} {size_names[i]}"
