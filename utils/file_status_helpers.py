"""
file_status_helpers.py

Central helpers for file metadata and hash status.
All lookups use path normalization for cross-platform compatibility.
"""
from pathlib import Path
from typing import Optional, Dict

from core.persistent_metadata_cache import get_persistent_metadata_cache
from core.persistent_hash_cache import get_persistent_hash_cache
from utils.path_normalizer import normalize_path

# --- Metadata helpers ---
def get_metadata_for_file(file_path: str | Path) -> Optional[dict]:
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
    return get_metadata_for_file(file_path) is not None

# --- Hash helpers ---
def get_hash_for_file(file_path: str | Path, hash_type: str = "CRC32") -> Optional[str]:
    """Return hash string for file, or None if not found."""
    cache = get_persistent_hash_cache()
    norm_path = normalize_path(file_path)
    return cache.get_hash(norm_path, hash_type)

def has_hash(file_path: str | Path, hash_type: str = "CRC32") -> bool:
    """Return True if file has hash of given type."""
    return get_hash_for_file(file_path, hash_type) is not None

# --- Batch helpers ---
def batch_metadata_status(file_paths: list[str | Path]) -> Dict[str, bool]:
    """Return dict: normalized path -> has_metadata (bool)"""
    return {normalize_path(p): has_metadata(p) for p in file_paths}

def batch_hash_status(file_paths: list[str | Path], hash_type: str = "CRC32") -> Dict[str, bool]:
    """Return dict: normalized path -> has_hash (bool)"""
    return {normalize_path(p): has_hash(p, hash_type) for p in file_paths}
