"""Tests for in-memory cache key remapping on rename (PersistentMetadataCache /
PersistentHashCache ``rename_path``).

These guard the stable-identity rename wiring: after a file is renamed, the
in-memory caches must move their entries from the old path to the new path so a
lookup by the new path is an immediate hit (the DB side keeps the same path_id
via DatabaseManager.update_file_path).
"""

from unittest.mock import MagicMock, patch

from oncutf.infra.cache.persistent_hash_cache import PersistentHashCache
from oncutf.infra.cache.persistent_metadata_cache import PersistentMetadataCache


def _make_metadata_cache() -> PersistentMetadataCache:
    with patch(
        "oncutf.infra.cache.persistent_metadata_cache.get_database_manager",
        return_value=MagicMock(),
    ):
        return PersistentMetadataCache()


def _make_hash_cache() -> PersistentHashCache:
    with patch(
        "oncutf.infra.cache.persistent_hash_cache.get_database_manager",
        return_value=MagicMock(),
    ):
        return PersistentHashCache()


def test_metadata_rename_path_moves_entry():
    cache = _make_metadata_cache()
    old = cache._normalize_path("/data/clip.mp4")
    new = cache._normalize_path("/data/renamed.mp4")
    sentinel = object()
    cache._memory_cache[old] = sentinel  # type: ignore[assignment]

    cache.rename_path("/data/clip.mp4", "/data/renamed.mp4")

    assert old not in cache._memory_cache
    assert cache._memory_cache[new] is sentinel


def test_metadata_rename_path_noop_when_absent():
    cache = _make_metadata_cache()
    # No entry for the old path -> nothing added, no error.
    cache.rename_path("/data/missing.mp4", "/data/whatever.mp4")
    new = cache._normalize_path("/data/whatever.mp4")
    assert new not in cache._memory_cache


def test_metadata_rename_path_noop_when_same():
    cache = _make_metadata_cache()
    norm = cache._normalize_path("/data/clip.mp4")
    sentinel = object()
    cache._memory_cache[norm] = sentinel  # type: ignore[assignment]

    cache.rename_path("/data/clip.mp4", "/data/clip.mp4")

    assert cache._memory_cache[norm] is sentinel


def test_hash_rename_path_moves_all_algorithms():
    cache = _make_hash_cache()
    old = cache._normalize_path("/data/clip.mp4")
    new = cache._normalize_path("/data/renamed.mp4")
    cache._memory_cache[f"{old}:CRC32"] = "aaaa"
    cache._memory_cache[f"{old}:SHA256"] = "bbbb"

    cache.rename_path("/data/clip.mp4", "/data/renamed.mp4")

    assert f"{old}:CRC32" not in cache._memory_cache
    assert f"{old}:SHA256" not in cache._memory_cache
    assert cache._memory_cache[f"{new}:CRC32"] == "aaaa"
    assert cache._memory_cache[f"{new}:SHA256"] == "bbbb"


def test_hash_rename_path_leaves_other_paths_untouched():
    cache = _make_hash_cache()
    other = cache._normalize_path("/data/other.mp4")
    cache._memory_cache[f"{other}:CRC32"] = "keep"

    cache.rename_path("/data/clip.mp4", "/data/renamed.mp4")

    assert cache._memory_cache[f"{other}:CRC32"] == "keep"
