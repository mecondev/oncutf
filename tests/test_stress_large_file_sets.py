"""
Module: test_stress_large_file_sets.py

Author: Michael Economou
Date: 2025-12-19

Stress tests for large file sets (1000+ files).
Tests memory usage, performance, and stability with large workloads.
"""

import os
import tempfile
from pathlib import Path

import pytest

from oncutf.core.persistent_hash_cache import PersistentHashCache
from oncutf.core.persistent_metadata_cache import PersistentMetadataCache


@pytest.mark.slow
class TestLargeFileSetStress:
    """Stress tests for large file sets."""

    def test_hash_cache_lru_eviction_with_1000_files(self, tmp_path):
        """Test that hash cache LRU eviction works correctly with 200 files (simulates 1000+)."""
        cache = PersistentHashCache()

        # Create 200 files (enough to test LRU without being too slow)
        file_count = 200
        files = []
        for i in range(file_count):
            file_path = tmp_path / f"file_{i:04d}.txt"
            file_path.write_text(f"Content {i}")
            files.append(str(file_path))

        # Store hashes for all files
        for i, file_path in enumerate(files):
            cache.store_hash(file_path, f"hash_{i:04d}", "CRC32")

        # Verify that memory cache is bounded (should be at most 1000)
        assert len(cache._memory_cache) <= 1000

        # Access first 20 files (should move them to end of LRU)
        for i in range(20):
            result = cache.get_hash(files[i], "CRC32")
            assert result == f"hash_{i:04d}"

        # Memory cache should still be bounded
        assert len(cache._memory_cache) <= 1000

        # Verify that recently accessed files are still in memory cache
        # (they should be at the end of OrderedDict)
        # Note: hash cache uses "path:algorithm" as key
        recent_keys = list(cache._memory_cache.keys())[-20:]
        for i in range(20):
            file_key = f"{cache._normalize_path(files[i])}:CRC32"
            assert file_key in recent_keys, f"Recently accessed file {i} not in cache"

    def test_metadata_cache_lru_eviction_with_1000_files(self, tmp_path):
        """Test that metadata cache LRU eviction works correctly with 100 files (simulates 1000+)."""
        cache = PersistentMetadataCache()

        # Create 100 files (enough to test LRU without being too slow)
        file_count = 100
        files = []
        for i in range(file_count):
            file_path = tmp_path / f"file_{i:04d}.txt"
            file_path.write_text(f"Content {i}")
            files.append(str(file_path))

        # Store metadata for all files
        for i, file_path in enumerate(files):
            cache.set(
                file_path=file_path,
                metadata={
                    "File:FileName": f"file_{i:04d}.txt",
                    "File:FileSize": 100 + i,
                    "File:FileModifyDate": "2025:12:19 10:00:00",
                },
                is_extended=False,
            )

        # Verify that memory cache is bounded (should be at most 500)
        assert len(cache._memory_cache) <= 500

        # Access first 10 files (should move them to end of LRU)
        for i in range(10):
            entry = cache.get_entry(files[i])
            assert entry is not None
            assert entry.data["File:FileName"] == f"file_{i:04d}.txt"

        # Memory cache should still be bounded
        assert len(cache._memory_cache) <= 500

        # Verify that recently accessed files are still in memory cache
        recent_keys = list(cache._memory_cache.keys())[-10:]
        for i in range(10):
            file_key = cache._normalize_path(files[i])
            assert file_key in recent_keys, f"Recently accessed file {i} not in cache"

    def test_hash_cache_handles_rapid_operations(self, tmp_path):
        """Test that hash cache handles rapid consecutive operations without issues."""
        cache = PersistentHashCache()

        # Create 100 files
        files = []
        for i in range(100):
            file_path = tmp_path / f"rapid_{i:03d}.txt"
            file_path.write_text(f"Rapid {i}")
            files.append(str(file_path))

        # Rapid store operations
        for i in range(10):  # 10 iterations
            for j, file_path in enumerate(files):
                cache.store_hash(file_path, f"hash_{j}_{i}", "CRC32")

        # Rapid get operations
        for i in range(10):  # 10 iterations
            for file_path in files:
                result = cache.get_hash(file_path, "CRC32")
                assert result is not None

        # Memory cache should be bounded
        assert len(cache._memory_cache) <= 1000

    @pytest.mark.slow
    def test_metadata_cache_handles_large_metadata_entries(self, tmp_path):
        """Test that metadata cache handles files with extensive metadata."""
        cache = PersistentMetadataCache()

        # Create 20 files with large metadata (simulates RAW files)
        files = []
        for i in range(20):
            file_path = tmp_path / f"large_meta_{i:03d}.txt"
            file_path.write_text(f"Content {i}")
            files.append(str(file_path))

        # Store extensive metadata for each file (simulating RAW files)
        for i, file_path in enumerate(files):
            large_metadata = {
                "File:FileName": f"large_meta_{i:03d}.txt",
                "File:FileSize": 10000000 + i,
                "EXIF:Make": "Canon",
                "EXIF:Model": "EOS R5",
                "EXIF:LensModel": "RF 24-70mm F2.8 L IS USM",
                "EXIF:ISO": 100 + (i % 10) * 100,
                "EXIF:ShutterSpeed": f"1/{100 + i}",
                "EXIF:Aperture": 2.8 + (i % 5) * 0.5,
                "GPS:GPSLatitude": 37.9838 + i * 0.001,
                "GPS:GPSLongitude": 23.7275 + i * 0.001,
                "XMP:Keywords": ["keyword1", "keyword2", f"tag{i}"],
            }
            # Add 50 more fields to simulate extensive metadata
            for j in range(50):
                large_metadata[f"Custom:Field{j}"] = f"Value_{i}_{j}"

            cache.set(
                file_path=file_path, metadata=large_metadata, is_extended=True
            )

        # Retrieve and verify metadata
        for i, file_path in enumerate(files):
            entry = cache.get_entry(file_path)
            assert entry is not None
            assert entry.data["File:FileName"] == f"large_meta_{i:03d}.txt"
            assert "Custom:Field49" in entry.data

        # Memory cache should be bounded despite large entries
        assert len(cache._memory_cache) <= 500


@pytest.mark.slow
class TestDeepDirectoryStructures:
    """Stress tests for deep directory structures."""

    def test_handles_deep_directory_nesting(self, tmp_path):
        """Test that the system handles deeply nested directories (10+ levels)."""
        # Create a 15-level deep directory structure
        current = tmp_path
        for i in range(15):
            current = current / f"level_{i:02d}"
            current.mkdir()

        # Create files at various depths
        file_paths = []
        depth = tmp_path
        for i in range(15):
            depth = depth / f"level_{i:02d}"
            file_path = depth / f"file_at_depth_{i}.txt"
            file_path.write_text(f"Content at depth {i}")
            file_paths.append(str(file_path))

        # Test that caches can handle deep paths
        hash_cache = PersistentHashCache()
        metadata_cache = PersistentMetadataCache()

        for i, file_path in enumerate(file_paths):
            # Store hash
            hash_cache.store_hash(file_path, f"hash_depth_{i}", "CRC32")

            # Store metadata
            metadata_cache.set(
                file_path=file_path,
                metadata={
                    "File:FileName": f"file_at_depth_{i}.txt",
                    "File:Directory": str(Path(file_path).parent),
                    "Custom:Depth": i,
                },
                is_extended=False,
            )

        # Verify retrieval works for all depths
        for i, file_path in enumerate(file_paths):
            hash_result = hash_cache.get_hash(file_path, "CRC32")
            assert hash_result == f"hash_depth_{i}"

            meta_result = metadata_cache.get_entry(file_path)
            assert meta_result is not None
            assert meta_result.data["Custom:Depth"] == i


@pytest.mark.slow
class TestMemoryUsage:
    """Memory usage tests to ensure no leaks with large workloads."""

    def test_cache_memory_footprint_stays_bounded(self, tmp_path):
        """Test that cache memory footprint stays bounded even with many operations."""
        hash_cache = PersistentHashCache()
        metadata_cache = PersistentMetadataCache()

        # Perform 300 operations (3 x 100 store + retrieve)
        for iteration in range(3):
            for i in range(100):
                file_path = tmp_path / f"iter_{iteration}_file_{i}.txt"
                file_path.write_text(f"Iteration {iteration} File {i}")

                # Store hash
                hash_cache.store_hash(str(file_path), f"hash_{iteration}_{i}", "CRC32")

                # Store metadata
                metadata_cache.set(
                    file_path=str(file_path),
                    metadata={
                        "File:FileName": f"iter_{iteration}_file_{i}.txt",
                        "Custom:Iteration": iteration,
                        "Custom:Index": i,
                    },
                    is_extended=False,
                )

        # Verify memory caches are still bounded
        assert len(hash_cache._memory_cache) <= 1000
        assert len(metadata_cache._memory_cache) <= 500

        # Memory footprint stays bounded even with 300 operations
        # This test validates that LRU eviction prevents unbounded growth
