"""file_status_helpers.py.

Central helpers for file metadata and hash status.
All lookups use path normalization for cross-platform compatibility.

This module provides the **canonical entry point** for cache access operations:
- Simple read operations: get_metadata_for_file(), has_metadata(), get_hash_for_file(), has_hash()
- Cache entry access: get_metadata_cache_entry(), set_metadata_for_file()
- Batch operations: batch_metadata_status(), batch_hash_status()

For complex operations requiring signals/progress, use UnifiedMetadataManager.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from oncutf.utils.logging.logger_factory import get_cached_logger

if TYPE_CHECKING:
    from oncutf.core.cache.persistent_metadata_cache import MetadataEntry

logger = get_cached_logger(__name__)
logger.debug("[DEBUG] [FileStatusHelpers] Module imported", extra={"dev_only": True})

try:
    from oncutf.core.cache.persistent_metadata_cache import get_persistent_metadata_cache

    logger.debug(
        "[DEBUG] [FileStatusHelpers] Successfully imported get_persistent_metadata_cache",
        extra={"dev_only": True},
    )
except Exception as e:
    logger.error("[DEBUG] [FileStatusHelpers] Error importing get_persistent_metadata_cache: %s", e)
    raise

try:
    from oncutf.core.cache.persistent_hash_cache import get_persistent_hash_cache

    logger.debug(
        "[DEBUG] [FileStatusHelpers] Successfully imported get_persistent_hash_cache",
        extra={"dev_only": True},
    )
except Exception as e:
    logger.error("[DEBUG] [FileStatusHelpers] Error importing get_persistent_hash_cache: %s", e)
    raise

from oncutf.utils.filesystem.path_normalizer import normalize_path


# --- Metadata helpers ---
def get_metadata_for_file(file_path: str | Path) -> dict[str, Any] | None:
    """Return metadata dict for file, or None if not found."""
    cache = get_persistent_metadata_cache()
    norm_path = normalize_path(file_path)
    if cache.has(norm_path):
        metadata = cache.get(norm_path)
        if metadata:
            # Filter out internal markers
            real_metadata = {k: v for k, v in metadata.items() if not k.startswith("__")}
            if real_metadata:
                return metadata
    return None


def has_metadata(file_path: str | Path) -> bool:
    """Return True if file has metadata (excluding only internal markers)."""
    metadata = get_metadata_for_file(file_path)
    has_meta = metadata is not None
    logger.debug(
        "[DEBUG] [FileStatusHelpers] has_metadata for %s: %s",
        file_path,
        has_meta,
        extra={"dev_only": True},
    )
    return has_meta


def get_metadata_cache_entry(file_path: str | Path) -> "MetadataEntry | None":
    """Return cache entry object for file, or None if not found.

    The cache entry contains additional metadata like is_extended, modified flags.
    """
    cache = get_persistent_metadata_cache()
    norm_path = normalize_path(file_path)
    return cache.get_entry(norm_path)


def set_metadata_for_file(
    file_path: str | Path,
    metadata: dict[str, Any],
    is_extended: bool = False,
    modified: bool = False,
) -> None:
    """Store metadata in cache for a file.

    Args:
        file_path: Path to the file
        metadata: Metadata dictionary to store
        is_extended: Whether this is extended metadata
        modified: Whether the metadata has been modified

    """
    cache = get_persistent_metadata_cache()
    norm_path = normalize_path(file_path)
    cache.set(norm_path, metadata, is_extended=is_extended, modified=modified)


def is_metadata_extended(file_path: str | Path) -> bool:
    """Return True if file has extended metadata."""
    entry = get_metadata_cache_entry(file_path)
    if entry and hasattr(entry, "is_extended"):
        return bool(entry.is_extended)
    return False


def is_metadata_modified(file_path: str | Path) -> bool:
    """Return True if file's metadata has been modified."""
    entry = get_metadata_cache_entry(file_path)
    if entry and hasattr(entry, "modified"):
        return bool(entry.modified)
    return False


def get_metadata_value(file_path: str | Path, key_path: str, default: Any = None) -> Any:
    """Get a specific metadata value by key path.

    Args:
        file_path: Path to the file
        key_path: Key path (e.g., "EXIF/ImageWidth" or "Title")
        default: Default value if not found

    Returns:
        The metadata value or default

    """
    metadata = get_metadata_for_file(file_path)
    if not metadata:
        return default

    # Handle nested keys (e.g., "EXIF/ImageWidth")
    if "/" in key_path:
        parts = key_path.split("/")
        value = metadata
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
    else:
        # Simple key
        return metadata.get(key_path, default)


def set_metadata_value(file_path: str | Path, key_path: str, new_value: Any) -> bool:
    """Set a specific metadata value by key path.

    Args:
        file_path: Path to the file
        key_path: Key path (e.g., "EXIF/ImageWidth" or "Title")
        new_value: New value to set

    Returns:
        bool: True if value was set successfully

    """
    try:
        # Get current metadata
        metadata = get_metadata_for_file(file_path)
        if metadata is None:
            logger.warning(
                "[FileStatusHelpers] Cannot set %s - no metadata found for %s",
                key_path,
                file_path,
            )
            return False

        # Make a copy to avoid modifying the original
        metadata = dict(metadata)

        # Special handling for Rotation - always use "Rotation" (capitalized)
        if key_path.lower() == "rotation":
            # Clean up any existing rotation entries (case-insensitive)
            keys_to_remove = [k for k in metadata if k.lower() == "rotation"]
            for k in keys_to_remove:
                del metadata[k]

            # Also remove from any groups
            for _group_key, group_data in list(metadata.items()):
                if isinstance(group_data, dict):
                    rotation_keys = [k for k in group_data if k.lower() == "rotation"]
                    for k in rotation_keys:
                        del group_data[k]

            # Set as top-level with correct capitalization
            metadata["Rotation"] = new_value
        # Handle nested keys (e.g., "EXIF/ImageWidth")
        elif "/" in key_path:
            parts = key_path.split("/")
            current = metadata

            # Navigate to parent container
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]

            # Set the final value
            current[parts[-1]] = new_value
        else:
            # Simple key
            metadata[key_path] = new_value

        # Update the metadata in cache
        set_metadata_for_file(file_path, metadata, modified=True)
        return True

    except Exception as e:
        logger.error(
            "[FileStatusHelpers] Error setting metadata value for %s: %s",
            file_path,
            e,
        )
        return False


# --- Hash helpers ---
def get_hash_for_file(file_path: str | Path, hash_type: str = "CRC32") -> str | None:
    """Return hash string for file, or None if not found."""
    cache = get_persistent_hash_cache()
    norm_path = normalize_path(file_path)
    return cache.get_hash(norm_path, hash_type)


def has_hash(file_path: str | Path, hash_type: str = "CRC32") -> bool:
    """Return True if file has hash of given type."""
    return get_hash_for_file(file_path, hash_type) is not None


# --- Batch helpers ---
def batch_metadata_status(file_paths: list[str | Path]) -> dict[str, bool]:
    """Return dict: normalized path -> has_metadata (bool)."""
    result = {}
    for p in file_paths:
        norm_path = normalize_path(p)
        has_meta = has_metadata(p)
        result[norm_path] = has_meta
    logger.debug(
        "[DEBUG] [FileStatusHelpers] batch_metadata_status: %s",
        result,
        extra={"dev_only": True},
    )
    return result


def batch_hash_status(file_paths: list[str | Path], hash_type: str = "CRC32") -> dict[str, bool]:
    """Return dict: normalized path -> has_hash (bool)."""
    return {normalize_path(p): has_hash(p, hash_type) for p in file_paths}
