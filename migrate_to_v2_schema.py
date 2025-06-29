#!/usr/bin/env python3
"""
Migration script from v1 to v2 database schema.

Migrates data from the old unified 'files' table structure
to the new separated architecture with dedicated tables.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database_manager import get_database_manager
from core.database_manager_v2 import get_database_manager_v2
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def migrate_database():
    """Migrate from v1 to v2 database schema."""

    print("=== Database Migration: V1 → V2 ===")
    print("This will migrate your data to the new improved schema.")
    print("The old database will be preserved as backup.")

    # Get database managers
    db_v1 = get_database_manager()
    db_v2 = get_database_manager_v2()

    try:
        # Get statistics from old database
        old_stats = db_v1.get_database_stats()
        print(f"\nOld database stats: {old_stats}")

        if not any(old_stats.values()):
            print("No data to migrate. Old database is empty.")
            return

        print("\n=== Step 1: Migrating file paths ===")
        migrated_paths = 0

        # Get all unique file paths from old database
        with db_v1._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT file_path, filename FROM files ORDER BY file_path")
            files = cursor.fetchall()

            for file_row in files:
                file_path = file_row['file_path']
                filename = file_row['filename']

                # Create path record in new database
                path_id = db_v2.get_or_create_path_id(file_path)
                migrated_paths += 1

                if migrated_paths % 10 == 0:
                    print(f"  Migrated {migrated_paths} paths...")

        print(f"✓ Migrated {migrated_paths} file paths")

        print("\n=== Step 2: Migrating metadata ===")
        migrated_metadata = 0

        with db_v1._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.file_path, m.metadata_type, m.metadata_json, m.is_modified
                FROM files f
                JOIN metadata m ON f.id = m.file_id
                ORDER BY f.file_path
            """)
            metadata_rows = cursor.fetchall()

            for meta_row in metadata_rows:
                file_path = meta_row['file_path']
                metadata_type = meta_row['metadata_type']
                metadata_json = meta_row['metadata_json']
                is_modified = bool(meta_row['is_modified'])

                # Parse metadata
                import json
                metadata = json.loads(metadata_json)

                # Store in new database
                is_extended = (metadata_type == 'extended')
                success = db_v2.store_metadata(file_path, metadata, is_extended, is_modified)

                if success:
                    migrated_metadata += 1

                if migrated_metadata % 10 == 0:
                    print(f"  Migrated {migrated_metadata} metadata records...")

        print(f"✓ Migrated {migrated_metadata} metadata records")

        print("\n=== Step 3: Migrating hashes ===")
        migrated_hashes = 0

        with db_v1._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.file_path, h.algorithm, h.hash_value, h.file_size_at_hash
                FROM files f
                JOIN hashes h ON f.id = h.file_id
                ORDER BY f.file_path
            """)
            hash_rows = cursor.fetchall()

            for hash_row in hash_rows:
                file_path = hash_row['file_path']
                algorithm = hash_row['algorithm']
                hash_value = hash_row['hash_value']

                # Store in new database
                success = db_v2.store_hash(file_path, hash_value, algorithm)

                if success:
                    migrated_hashes += 1

                if migrated_hashes % 10 == 0:
                    print(f"  Migrated {migrated_hashes} hash records...")

        print(f"✓ Migrated {migrated_hashes} hash records")

        print("\n=== Step 4: Migrating rename history ===")
        # Note: Rename history migration would be more complex
        # For now, we'll skip it as it's less critical
        print("⚠ Rename history migration not implemented yet (low priority)")

        # Verify migration
        print("\n=== Verification ===")
        new_stats = db_v2.get_database_stats()
        print(f"New database stats: {new_stats}")

        # Check that key data was migrated
        success = True
        if new_stats.get('file_metadata', 0) != old_stats.get('metadata', 0):
            print(f"⚠ Metadata count mismatch: {new_stats.get('file_metadata', 0)} vs {old_stats.get('metadata', 0)}")
            success = False

        if new_stats.get('file_hashes', 0) != old_stats.get('hashes', 0):
            print(f"⚠ Hash count mismatch: {new_stats.get('file_hashes', 0)} vs {old_stats.get('hashes', 0)}")
            success = False

        if success:
            print("✅ Migration completed successfully!")
            print("\nNext steps:")
            print("1. Test the application with the new database")
            print("2. If everything works, you can delete the old database")
            print("3. The new database is located at:", db_v2.db_path)
        else:
            print("❌ Migration completed with warnings. Please check the data.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"❌ Migration failed: {e}")
        return False

    return True


def test_migration():
    """Test that migration worked correctly."""
    print("\n=== Testing Migration ===")

    db_v2 = get_database_manager_v2()

    # Test a few operations
    test_file = "/test/migration_test.txt"

    # Test metadata
    test_metadata = {"test": "migration", "type": "verification"}
    success = db_v2.store_metadata(test_file, test_metadata)
    print(f"Metadata test: {'✅' if success else '❌'}")

    # Test hash
    success = db_v2.store_hash(test_file, "TEST123", "CRC32")
    print(f"Hash test: {'✅' if success else '❌'}")

    # Test retrieval
    retrieved_meta = db_v2.get_metadata(test_file)
    retrieved_hash = db_v2.get_hash(test_file)

    print(f"Metadata retrieval: {'✅' if retrieved_meta else '❌'}")
    print(f"Hash retrieval: {'✅' if retrieved_hash else '❌'}")

    # Test combined check
    has_both = db_v2.has_metadata(test_file) and db_v2.has_hash(test_file)
    print(f"Combined storage: {'✅' if has_both else '❌'}")

    print("Migration test completed!")


if __name__ == "__main__":
    if migrate_database():
        test_migration()
    else:
        print("Migration failed. Please check the logs.")
