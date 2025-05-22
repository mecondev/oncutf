"""
Module: metadata_cache.py

Author: Michael Economou
Date: 2025-05-12

This module defines a simple in-memory metadata cache system used during
batch renaming operations in the oncutf tool. It stores metadata for files
indexed by their normalized absolute paths, in order to avoid redundant
metadata extraction after file renaming or during preview regeneration.

Usage:
    - Cache metadata by calling `metadata_cache.set(path, metadata)`
    - Retrieve cached metadata using `metadata_cache.get(path)`
    - Check presence with `metadata_cache.has(path)`
    - Clear the cache with `metadata_cache.clear()`
"""

import os


class MetadataCache:
    """
    A simple in-memory cache for storing metadata of files
    to avoid re-reading after rename operations.
    """

    def __init__(self):
        self._cache = {}

    def _normalize_path(self, file_path: str) -> str:
        return os.path.abspath(os.path.normpath(file_path))

    def set(self, file_path: str, metadata: dict):
        norm_path = self._normalize_path(file_path)
        self._cache[norm_path] = metadata

    def add(self, file_path: str, metadata: dict):
        norm_path = self._normalize_path(file_path)
        if norm_path in self._cache:
            raise KeyError(f"Metadata for '{file_path}' already exists.")
        self._cache[norm_path] = metadata

    def get(self, file_path: str) -> dict:
        norm_path = self._normalize_path(file_path)
        return self._cache.get(norm_path, {})

    def __getitem__(self, file_path: str) -> dict:
        return self.get(file_path)

    def has(self, file_path: str) -> bool:
        norm_path = self._normalize_path(file_path)
        return norm_path in self._cache

    def clear(self):
        self._cache.clear()

    def update(self, other: dict):
        normalized = {
            self._normalize_path(k): v for k, v in other.items()
        }
        self._cache.update(normalized)

    def retain_only(self, paths: list[str]) -> None:
        """
        Keeps only the metadata entries for the given list of file paths.
        All other metadata entries are removed.
        """
        norm_paths = {self._normalize_path(p) for p in paths}
        self._cache = {
            path: meta for path, meta in self._cache.items() if path in norm_paths
        }


# Global instance
metadata_cache = MetadataCache()
