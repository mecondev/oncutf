"""Module: migrations.py.

Author: Michael Economou
Date: 2026-01-01

Database schema creation and migration functions.
Handles all database schema setup, versioning, and upgrades.
"""

import sqlite3
from typing import Any

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Database schema version for migrations
SCHEMA_VERSION = 5


def create_schema(cursor: sqlite3.Cursor) -> None:
    """Create the new v2 schema with separated tables."""
    # 1. Central file paths table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS file_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            file_size INTEGER,
            modified_time TIMESTAMP,
            color_tag TEXT DEFAULT 'none',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # 2. Dedicated metadata table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS file_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path_id INTEGER NOT NULL,
            metadata_type TEXT NOT NULL DEFAULT 'fast',
            metadata_json TEXT NOT NULL,
            is_modified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE
        )
    """
    )

    # 3. Dedicated hash table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS file_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path_id INTEGER NOT NULL,
            algorithm TEXT NOT NULL DEFAULT 'CRC32',
            hash_value TEXT NOT NULL,
            file_size_at_hash INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE
        )
    """
    )

    # 4. Dedicated rename history table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS file_rename_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL,
            path_id INTEGER NOT NULL,
            old_path TEXT NOT NULL,
            new_path TEXT NOT NULL,
            old_filename TEXT NOT NULL,
            new_filename TEXT NOT NULL,
            operation_type TEXT NOT NULL DEFAULT 'rename',
            modules_data TEXT,
            post_transform_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE
        )
    """
    )

    # 5. Metadata categories table for organizing metadata groups
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # 6. Metadata fields table for individual metadata fields
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_key TEXT NOT NULL UNIQUE,
            field_name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            data_type TEXT NOT NULL DEFAULT 'text',
            is_editable BOOLEAN DEFAULT FALSE,
            is_searchable BOOLEAN DEFAULT TRUE,
            display_format TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES metadata_categories (id) ON DELETE CASCADE
        )
    """
    )

    # 7. Structured metadata storage table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS file_metadata_structured (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path_id INTEGER NOT NULL,
            field_id INTEGER NOT NULL,
            field_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE,
            FOREIGN KEY (field_id) REFERENCES metadata_fields (id) ON DELETE CASCADE,
            UNIQUE(path_id, field_id)
        )
    """
    )

    # 8. Thumbnail cache index table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_path TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_mtime REAL NOT NULL,
            file_size INTEGER NOT NULL,
            cache_filename TEXT NOT NULL,
            video_frame_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(file_path, file_mtime)
        )
    """
    )

    # 9. Thumbnail manual order table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_order (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_path TEXT NOT NULL UNIQUE,
            file_paths TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    logger.debug("[migrations] Schema v2 created")


def migrate_schema(cursor: sqlite3.Cursor, from_version: int, to_version: int) -> None:
    """Migrate from older schema versions."""
    logger.info(
        "[migrations] Migrating from version %d to %d",
        from_version,
        to_version,
    )

    # Migration from version 2 to 3: Add structured metadata tables
    if from_version == 2 and to_version >= 3:
        logger.info("[migrations] Adding structured metadata tables...")

        # Add metadata categories table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Add metadata fields table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field_key TEXT NOT NULL UNIQUE,
                field_name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                data_type TEXT NOT NULL DEFAULT 'text',
                is_editable BOOLEAN DEFAULT FALSE,
                is_searchable BOOLEAN DEFAULT TRUE,
                display_format TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES metadata_categories (id) ON DELETE CASCADE
            )
        """
        )

        # Add structured metadata storage table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_metadata_structured (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_id INTEGER NOT NULL,
                field_id INTEGER NOT NULL,
                field_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (path_id) REFERENCES file_paths (id) ON DELETE CASCADE,
                FOREIGN KEY (field_id) REFERENCES metadata_fields (id) ON DELETE CASCADE,
                UNIQUE(path_id, field_id)
            )
        """
        )

        logger.info("[migrations] Structured metadata tables added successfully")

    # Migration from version 3 to 4: Add color_tag column
    if from_version == 3 and to_version >= 4:
        logger.info("[migrations] Adding color_tag column to file_paths...")

        # Add color_tag column
        cursor.execute(
            """
            ALTER TABLE file_paths ADD COLUMN color_tag TEXT DEFAULT 'none'
            """
        )

        logger.info("[migrations] color_tag column added successfully")

    # Migration from version 4 to 5: Add thumbnail cache tables
    if from_version == 4 and to_version >= 5:
        logger.info("[migrations] Adding thumbnail cache tables...")

        # Thumbnail cache index table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS thumbnail_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_mtime REAL NOT NULL,
                file_size INTEGER NOT NULL,
                cache_filename TEXT NOT NULL,
                video_frame_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_path, file_mtime)
            )
            """
        )

        # Thumbnail manual order table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS thumbnail_order (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path TEXT NOT NULL UNIQUE,
                file_paths TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Create indexes for thumbnail tables
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_thumbnail_cache_folder ON thumbnail_cache(folder_path)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_thumbnail_cache_file ON thumbnail_cache(file_path)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_thumbnail_order_folder ON thumbnail_order(folder_path)"
        )

        logger.info("[migrations] Thumbnail cache tables added successfully")


def create_indexes(cursor: sqlite3.Cursor) -> None:
    """Create database indexes for performance."""
    indexes = [
        # File paths indexes
        "CREATE INDEX IF NOT EXISTS idx_file_paths_path ON file_paths (file_path)",
        "CREATE INDEX IF NOT EXISTS idx_file_paths_filename ON file_paths (filename)",
        # Metadata indexes
        "CREATE INDEX IF NOT EXISTS idx_file_metadata_path_id ON file_metadata (path_id)",
        "CREATE INDEX IF NOT EXISTS idx_file_metadata_type ON file_metadata (metadata_type)",
        # Hash indexes
        "CREATE INDEX IF NOT EXISTS idx_file_hashes_path_id ON file_hashes (path_id)",
        "CREATE INDEX IF NOT EXISTS idx_file_hashes_algorithm ON file_hashes (algorithm)",
        "CREATE INDEX IF NOT EXISTS idx_file_hashes_value ON file_hashes (hash_value)",
        # Rename history indexes
        "CREATE INDEX IF NOT EXISTS idx_file_rename_history_operation_id ON file_rename_history (operation_id)",
        "CREATE INDEX IF NOT EXISTS idx_file_rename_history_path_id ON file_rename_history (path_id)",
        "CREATE INDEX IF NOT EXISTS idx_file_rename_history_created_at ON file_rename_history (created_at)",
        # Metadata categories indexes
        "CREATE INDEX IF NOT EXISTS idx_metadata_categories_name ON metadata_categories (category_name)",
        "CREATE INDEX IF NOT EXISTS idx_metadata_categories_sort_order ON metadata_categories (sort_order)",
        # Metadata fields indexes
        "CREATE INDEX IF NOT EXISTS idx_metadata_fields_key ON metadata_fields (field_key)",
        "CREATE INDEX IF NOT EXISTS idx_metadata_fields_category_id ON metadata_fields (category_id)",
        "CREATE INDEX IF NOT EXISTS idx_metadata_fields_sort_order ON metadata_fields (sort_order)",
        # Structured metadata indexes
        "CREATE INDEX IF NOT EXISTS idx_file_metadata_structured_path_id ON file_metadata_structured (path_id)",
        "CREATE INDEX IF NOT EXISTS idx_file_metadata_structured_field_id ON file_metadata_structured (field_id)",
        "CREATE INDEX IF NOT EXISTS idx_file_metadata_structured_path_field ON file_metadata_structured (path_id, field_id)",
        # Thumbnail cache indexes
        "CREATE INDEX IF NOT EXISTS idx_thumbnail_cache_folder ON thumbnail_cache(folder_path)",
        "CREATE INDEX IF NOT EXISTS idx_thumbnail_cache_file ON thumbnail_cache(file_path)",
        "CREATE INDEX IF NOT EXISTS idx_thumbnail_order_folder ON thumbnail_order(folder_path)",
        # Composite indexes for faster common queries
        "CREATE INDEX IF NOT EXISTS idx_metadata_path_type ON file_metadata (path_id, metadata_type)",
        "CREATE INDEX IF NOT EXISTS idx_hashes_path_algo ON file_hashes (path_id, algorithm)",
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    logger.debug("[migrations] Database indexes created", extra={"dev_only": True})


def initialize_default_metadata_schema(
    get_metadata_categories: Any,
    create_metadata_category: Any,
    create_metadata_field: Any,
) -> bool:
    """Initialize default metadata categories and fields."""
    try:
        # Check if already initialized
        categories = get_metadata_categories()
        if categories:
            logger.debug("[migrations] Metadata schema already initialized")
            return True

        # Create default categories
        category_mapping: dict[str, int | None] = {}

        # Basic File Information
        cat_id = create_metadata_category(
            "file_basic", "File Information", "Basic file properties and information", 0
        )
        category_mapping["file_basic"] = cat_id

        # Image Information
        cat_id = create_metadata_category(
            "image", "Image Properties", "Image-specific metadata and properties", 1
        )
        category_mapping["image"] = cat_id

        # Camera/Device Information
        cat_id = create_metadata_category(
            "camera", "Camera & Device", "Camera settings and device information", 2
        )
        category_mapping["camera"] = cat_id

        # Video Information
        cat_id = create_metadata_category(
            "video", "Video Properties", "Video-specific metadata and properties", 3
        )
        category_mapping["video"] = cat_id

        # Audio Information
        cat_id = create_metadata_category(
            "audio", "Audio Properties", "Audio-specific metadata and properties", 4
        )
        category_mapping["audio"] = cat_id

        # GPS/Location Information
        cat_id = create_metadata_category(
            "location", "Location & GPS", "GPS coordinates and location information", 5
        )
        category_mapping["location"] = cat_id

        # Technical Information
        cat_id = create_metadata_category(
            "technical",
            "Technical Details",
            "Technical metadata and processing information",
            6,
        )
        category_mapping["technical"] = cat_id

        # Create default fields
        default_fields = [
            # File Basic
            ("System:FileName", "Filename", "file_basic", "text", False, True, None, 0),
            (
                "System:FileSize",
                "File Size",
                "file_basic",
                "size",
                False,
                True,
                "bytes",
                1,
            ),
            (
                "System:FileModifyDate",
                "Modified Date",
                "file_basic",
                "datetime",
                False,
                True,
                None,
                2,
            ),
            (
                "System:FileCreateDate",
                "Created Date",
                "file_basic",
                "datetime",
                False,
                True,
                None,
                3,
            ),
            ("File:FileType", "File Type", "file_basic", "text", False, True, None, 4),
            ("File:MIMEType", "MIME Type", "file_basic", "text", False, True, None, 5),
            # Image
            (
                "EXIF:ImageWidth",
                "Image Width",
                "image",
                "number",
                False,
                True,
                "pixels",
                0,
            ),
            (
                "EXIF:ImageHeight",
                "Image Height",
                "image",
                "number",
                False,
                True,
                "pixels",
                1,
            ),
            ("EXIF:Orientation", "Orientation", "image", "text", True, True, None, 2),
            (
                "QuickTime:Rotation",
                "Rotation (Video)",
                "video",
                "text",
                True,
                True,
                "degrees",
                2,
            ),
            ("EXIF:ColorSpace", "Color Space", "image", "text", False, True, None, 3),
            (
                "EXIF:BitsPerSample",
                "Bits Per Sample",
                "image",
                "number",
                False,
                True,
                "bits",
                4,
            ),
            ("EXIF:Compression", "Compression", "image", "text", False, True, None, 5),
            # Camera
            ("EXIF:Make", "Camera Make", "camera", "text", True, True, None, 0),
            ("EXIF:Model", "Camera Model", "camera", "text", True, True, None, 1),
            ("EXIF:LensModel", "Lens Model", "camera", "text", True, True, None, 2),
            ("EXIF:ISO", "ISO", "camera", "number", True, True, None, 3),
            ("EXIF:FNumber", "F-Number", "camera", "number", True, True, "f/", 4),
            (
                "EXIF:ExposureTime",
                "Exposure Time",
                "camera",
                "text",
                True,
                True,
                "sec",
                5,
            ),
            ("EXIF:FocalLength", "Focal Length", "camera", "text", True, True, "mm", 6),
            (
                "EXIF:WhiteBalance",
                "White Balance",
                "camera",
                "text",
                True,
                True,
                None,
                7,
            ),
            ("EXIF:Flash", "Flash", "camera", "text", True, True, None, 8),
            # Video
            (
                "QuickTime:ImageWidth",
                "Video Width",
                "video",
                "number",
                False,
                True,
                "pixels",
                0,
            ),
            (
                "QuickTime:ImageHeight",
                "Video Height",
                "video",
                "number",
                False,
                True,
                "pixels",
                1,
            ),
            (
                "QuickTime:Duration",
                "Duration",
                "video",
                "duration",
                False,
                True,
                "seconds",
                2,
            ),
            (
                "QuickTime:VideoFrameRate",
                "Frame Rate",
                "video",
                "number",
                False,
                True,
                "fps",
                3,
            ),
            (
                "QuickTime:VideoCodec",
                "Video Codec",
                "video",
                "text",
                False,
                True,
                None,
                4,
            ),
            (
                "QuickTime:AvgBitrate",
                "Average Bitrate",
                "video",
                "number",
                False,
                True,
                "kbps",
                5,
            ),
            # Audio
            (
                "QuickTime:AudioChannels",
                "Audio Channels",
                "audio",
                "number",
                False,
                True,
                None,
                0,
            ),
            (
                "QuickTime:AudioSampleRate",
                "Sample Rate",
                "audio",
                "number",
                False,
                True,
                "Hz",
                1,
            ),
            (
                "QuickTime:AudioFormat",
                "Audio Format",
                "audio",
                "text",
                False,
                True,
                None,
                2,
            ),
            (
                "QuickTime:AudioBitrate",
                "Audio Bitrate",
                "audio",
                "number",
                False,
                True,
                "kbps",
                3,
            ),
            # Location
            (
                "GPS:GPSLatitude",
                "Latitude",
                "location",
                "coordinate",
                True,
                True,
                "degrees",
                0,
            ),
            (
                "GPS:GPSLongitude",
                "Longitude",
                "location",
                "coordinate",
                True,
                True,
                "degrees",
                1,
            ),
            (
                "GPS:GPSAltitude",
                "Altitude",
                "location",
                "number",
                True,
                True,
                "meters",
                2,
            ),
            ("GPS:GPSMapDatum", "Map Datum", "location", "text", True, True, None, 3),
            # Technical
            (
                "ExifTool:ExifToolVersion",
                "ExifTool Version",
                "technical",
                "text",
                False,
                False,
                None,
                0,
            ),
            (
                "File:FilePermissions",
                "File Permissions",
                "technical",
                "text",
                False,
                False,
                None,
                1,
            ),
        ]

        for (
            field_key,
            field_name,
            category_name,
            data_type,
            is_editable,
            is_searchable,
            display_format,
            sort_order,
        ) in default_fields:
            category_id = category_mapping.get(category_name)
            if category_id:
                create_metadata_field(
                    field_key,
                    field_name,
                    category_id,
                    data_type,
                    is_editable,
                    is_searchable,
                    display_format,
                    sort_order,
                )

        logger.info("[migrations] Default metadata schema initialized")
        return True

    except Exception as e:
        logger.error("[migrations] Error initializing default metadata schema: %s", e)
        return False
