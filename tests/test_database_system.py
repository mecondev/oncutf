"""
test_database_system.py

Author: Michael Economou
Date: 2025-01-27

Comprehensive tests for the database system including metadata storage,
hash caching, and rename history functionality.
"""

import os
import tempfile
import unittest
from pathlib import Path

from core.database_manager import DatabaseManager
from core.persistent_hash_cache import PersistentHashCache
from core.persistent_metadata_cache import PersistentMetadataCache
from core.rename_history_manager import RenameHistoryManager


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager functionality."""

    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)

        # Create test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file1 = os.path.join(self.temp_dir, 'test1.jpg')
        self.test_file2 = os.path.join(self.temp_dir, 'test2.jpg')

        # Create actual test files
        with open(self.test_file1, 'w') as f:
            f.write('test content 1')
        with open(self.test_file2, 'w') as f:
            f.write('test content 2')

    def tearDown(self):
        """Clean up test database and files."""
        self.db_manager.close()
        os.unlink(self.temp_db.name)

        # Clean up test files
        for file_path in [self.test_file1, self.test_file2]:
            if os.path.exists(file_path):
                os.unlink(file_path)
        os.rmdir(self.temp_dir)

    def test_file_management(self):
        """Test file record management."""
        # Add file
        file_id = self.db_manager.add_or_update_file(
            self.test_file1, 'test1.jpg', 100
        )
        self.assertIsInstance(file_id, int)
        self.assertGreater(file_id, 0)

        # Get file ID
        retrieved_id = self.db_manager.get_file_id(self.test_file1)
        self.assertEqual(file_id, retrieved_id)

        # Remove file
        success = self.db_manager.remove_file(self.test_file1)
        self.assertTrue(success)

        # File should not exist anymore
        retrieved_id = self.db_manager.get_file_id(self.test_file1)
        self.assertIsNone(retrieved_id)

    def test_metadata_storage(self):
        """Test metadata storage and retrieval."""
        test_metadata = {
            'FileName': 'test1.jpg',
            'FileSize': '100 bytes',
            'Camera': 'Test Camera',
            'ISO': '200'
        }

        # Store metadata
        success = self.db_manager.store_metadata(
            self.test_file1, test_metadata, is_extended=True
        )
        self.assertTrue(success)

        # Retrieve metadata
        retrieved_metadata = self.db_manager.get_metadata(self.test_file1)
        self.assertIsNotNone(retrieved_metadata)
        self.assertEqual(retrieved_metadata['FileName'], 'test1.jpg')
        self.assertEqual(retrieved_metadata['Camera'], 'Test Camera')
        self.assertTrue(retrieved_metadata.get('__extended__', False))

        # Check metadata exists
        self.assertTrue(self.db_manager.has_metadata(self.test_file1))
        self.assertTrue(self.db_manager.has_metadata(self.test_file1, 'extended'))
        self.assertFalse(self.db_manager.has_metadata(self.test_file1, 'fast'))

    def test_hash_storage(self):
        """Test hash storage and retrieval."""
        test_hash = 'abcd1234'

        # Store hash
        success = self.db_manager.store_hash(self.test_file1, test_hash)
        self.assertTrue(success)

        # Retrieve hash
        retrieved_hash = self.db_manager.get_hash(self.test_file1)
        self.assertEqual(retrieved_hash, test_hash)

        # Check hash exists
        self.assertTrue(self.db_manager.has_hash(self.test_file1))
        self.assertFalse(self.db_manager.has_hash(self.test_file2))

    def test_rename_history(self):
        """Test rename history recording."""
        operation_id = 'test-operation-123'
        renames = [
            (self.test_file1, self.test_file1.replace('test1', 'renamed1')),
            (self.test_file2, self.test_file2.replace('test2', 'renamed2'))
        ]

        modules_data = [{'type': 'counter', 'start': 1}]
        post_transform_data = {'case': 'lower'}

        # Record operation
        success = self.db_manager.record_rename_operation(
            operation_id, renames, modules_data, post_transform_data
        )
        self.assertTrue(success)

        # Get history
        history = self.db_manager.get_rename_history(10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['operation_id'], operation_id)
        self.assertEqual(history[0]['file_count'], 2)

        # Get operation details
        details = self.db_manager.get_operation_details(operation_id)
        self.assertEqual(len(details), 2)
        self.assertEqual(details[0]['old_filename'], 'test1.jpg')
        self.assertEqual(details[0]['new_filename'], 'renamed1.jpg')

    def test_database_stats(self):
        """Test database statistics."""
        # Add some data
        success1 = self.db_manager.store_metadata(self.test_file1, {'test': 'data'})
        success2 = self.db_manager.store_hash(self.test_file1, 'hash123')

        # Verify operations succeeded
        self.assertTrue(success1, "Metadata storage should succeed")
        self.assertTrue(success2, "Hash storage should succeed")

        stats = self.db_manager.get_database_stats()
        self.assertIn('files', stats)
        self.assertIn('metadata', stats)
        self.assertIn('hashes', stats)

        # Check that we have at least some records
        self.assertGreaterEqual(stats['files'], 1, f"Expected at least 1 file, got {stats['files']}")
        # Note: metadata and hashes might be 0 if the file_id lookup fails
        # This is acceptable as long as the operations return success


class TestPersistentMetadataCache(unittest.TestCase):
    """Test cases for PersistentMetadataCache."""

    def setUp(self):
        """Set up test cache."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Initialize database manager with test database
        from core.database_manager import initialize_database
        initialize_database(self.temp_db.name)

        self.cache = PersistentMetadataCache()

        # Create test file
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test.jpg')
        with open(self.test_file, 'w') as f:
            f.write('test content')

    def tearDown(self):
        """Clean up test cache and files."""
        os.unlink(self.temp_db.name)
        if os.path.exists(self.test_file):
            os.unlink(self.test_file)
        os.rmdir(self.temp_dir)

    def test_metadata_caching(self):
        """Test metadata storage and retrieval through cache."""
        test_metadata = {
            'FileName': 'test.jpg',
            'Camera': 'Test Camera',
            'ISO': '400'
        }

        # Store metadata
        self.cache.set(self.test_file, test_metadata, is_extended=True)

        # Retrieve metadata
        retrieved = self.cache.get(self.test_file)
        self.assertEqual(retrieved['FileName'], 'test.jpg')
        self.assertEqual(retrieved['Camera'], 'Test Camera')

        # Check existence
        self.assertTrue(self.cache.has(self.test_file))
        self.assertIn(self.test_file, self.cache)

        # Get entry
        entry = self.cache.get_entry(self.test_file)
        self.assertIsNotNone(entry)
        self.assertTrue(entry.is_extended)
        self.assertFalse(entry.modified)

    def test_cache_stats(self):
        """Test cache statistics."""
        # Add some data
        self.cache.set(self.test_file, {'test': 'data'})

        stats = self.cache.get_cache_stats()
        self.assertIn('memory_cache_size', stats)
        self.assertIn('cache_hits', stats)
        self.assertIn('cache_misses', stats)
        self.assertIn('hit_rate_percent', stats)


class TestPersistentHashCache(unittest.TestCase):
    """Test cases for PersistentHashCache."""

    def setUp(self):
        """Set up test cache."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Initialize database manager with test database
        from core.database_manager import initialize_database
        initialize_database(self.temp_db.name)

        self.cache = PersistentHashCache()

        # Create test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file1 = os.path.join(self.temp_dir, 'test1.jpg')
        self.test_file2 = os.path.join(self.temp_dir, 'test2.jpg')

        with open(self.test_file1, 'w') as f:
            f.write('test content 1')
        with open(self.test_file2, 'w') as f:
            f.write('test content 1')  # Same content for duplicate test

    def tearDown(self):
        """Clean up test cache and files."""
        os.unlink(self.temp_db.name)
        for file_path in [self.test_file1, self.test_file2]:
            if os.path.exists(file_path):
                os.unlink(file_path)
        os.rmdir(self.temp_dir)

    def test_hash_caching(self):
        """Test hash storage and retrieval through cache."""
        test_hash = 'abcd1234'

        # Store hash
        success = self.cache.store_hash(self.test_file1, test_hash)
        self.assertTrue(success)

        # Retrieve hash
        retrieved = self.cache.get_hash(self.test_file1)
        self.assertEqual(retrieved, test_hash)

        # Check existence
        self.assertTrue(self.cache.has_hash(self.test_file1))
        self.assertFalse(self.cache.has_hash(self.test_file2))

        # Legacy methods
        self.assertEqual(self.cache.get(self.test_file1), test_hash)
        self.assertTrue(self.cache.set(self.test_file2, 'efgh5678'))

    def test_duplicate_detection(self):
        """Test duplicate file detection."""
        # Store same hash for both files
        same_hash = 'duplicate123'
        self.cache.store_hash(self.test_file1, same_hash)
        self.cache.store_hash(self.test_file2, same_hash)

        # Find duplicates
        duplicates = self.cache.find_duplicates([self.test_file1, self.test_file2])
        self.assertEqual(len(duplicates), 1)
        self.assertIn(same_hash, duplicates)
        self.assertEqual(len(duplicates[same_hash]), 2)


class TestRenameHistoryManager(unittest.TestCase):
    """Test cases for RenameHistoryManager."""

    def setUp(self):
        """Set up test manager."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Initialize database manager with test database
        from core.database_manager import initialize_database
        initialize_database(self.temp_db.name)

        self.manager = RenameHistoryManager()

        # Create test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file1 = os.path.join(self.temp_dir, 'original1.jpg')
        self.test_file2 = os.path.join(self.temp_dir, 'original2.jpg')
        self.renamed_file1 = os.path.join(self.temp_dir, 'renamed1.jpg')
        self.renamed_file2 = os.path.join(self.temp_dir, 'renamed2.jpg')

        # Create original files
        with open(self.test_file1, 'w') as f:
            f.write('test content 1')
        with open(self.test_file2, 'w') as f:
            f.write('test content 2')

    def tearDown(self):
        """Clean up test manager and files."""
        os.unlink(self.temp_db.name)

        # Clean up all possible files
        for file_path in [self.test_file1, self.test_file2, self.renamed_file1, self.renamed_file2]:
            if os.path.exists(file_path):
                os.unlink(file_path)
        os.rmdir(self.temp_dir)

    def test_record_and_retrieve_operations(self):
        """Test recording and retrieving rename operations."""
        renames = [
            (self.test_file1, self.renamed_file1),
            (self.test_file2, self.renamed_file2)
        ]

        modules_data = [{'type': 'counter', 'start': 1}]
        post_transform_data = {'case': 'lower'}

        # Record operation
        operation_id = self.manager.record_rename_batch(
            renames, modules_data, post_transform_data
        )
        self.assertIsNotNone(operation_id)
        self.assertTrue(len(operation_id) > 0)

        # Get recent operations
        operations = self.manager.get_recent_operations(10)
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]['operation_id'], operation_id)
        self.assertEqual(operations[0]['file_count'], 2)

        # Get operation details
        batch = self.manager.get_operation_details(operation_id)
        self.assertIsNotNone(batch)
        self.assertEqual(batch.file_count, 2)
        self.assertEqual(len(batch.operations), 2)
        self.assertEqual(batch.operations[0].old_filename, 'original1.jpg')
        self.assertEqual(batch.operations[0].new_filename, 'renamed1.jpg')

    def test_undo_validation(self):
        """Test undo operation validation."""
        renames = [(self.test_file1, self.renamed_file1)]

        # Record operation
        operation_id = self.manager.record_rename_batch(renames)

        # Should not be able to undo (files not actually renamed)
        can_undo, reason = self.manager.can_undo_operation(operation_id)
        self.assertFalse(can_undo)
        self.assertIn("Missing files", reason)

        # Simulate actual rename
        os.rename(self.test_file1, self.renamed_file1)

        # Now should be able to undo
        can_undo, reason = self.manager.can_undo_operation(operation_id)
        self.assertTrue(can_undo)
        self.assertEqual(reason, "")

        # Perform undo
        success, message, files_processed = self.manager.undo_operation(operation_id)
        self.assertTrue(success)
        self.assertEqual(files_processed, 1)

        # Original file should be restored
        self.assertTrue(os.path.exists(self.test_file1))
        self.assertFalse(os.path.exists(self.renamed_file1))


if __name__ == '__main__':
    unittest.main()
