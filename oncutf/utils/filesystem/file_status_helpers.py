"""file_status_helpers.py

Central helpers for file metadata and hash status.
All lookups use path normalization for cross-platform compatibility.
"""

from pathlib import Path

from oncutf.utils.logging.logger_factory import get_cached_logger

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

from typing import Any

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
    """Return dict: normalized path -> has_metadata (bool)"""
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
    """Return dict: normalized path -> has_hash (bool)"""
    return {normalize_path(p): has_hash(p, hash_type) for p in file_paths}
