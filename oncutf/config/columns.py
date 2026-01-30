"""Module: oncutf.config.columns.

Author: Michael Economou
Date: 2026-01-01

Column configuration for tables (FileTable, MetadataTree, Results, HashList).
"""

# =====================================
# COLUMN MANAGEMENT SETTINGS
# =====================================

GLOBAL_MIN_COLUMN_WIDTH = 50

COLUMN_SHORTCUTS = {
    "AUTO_FIT_CONTENT": "Ctrl+T",
    "RESET_TO_DEFAULT": "Ctrl+Shift+T",
}

COLUMN_RESIZE_BEHAVIOR = {
    "ENABLE_HORIZONTAL_SCROLLBAR": True,
    "AUTO_ADJUST_FILENAME": False,
    "PRESERVE_USER_WIDTHS": True,
    "ENABLE_COLUMN_REORDERING": True,
}

# =====================================
# FILE TABLE COLUMN CONFIGURATION
# =====================================

FILE_TABLE_COLUMN_CONFIG = {
    "color": {
        "title": "Color Flag",
        "display_title": "Color",
        "key": "color",
        "default_visible": True,
        "removable": True,
        "resizable": False,
        "width": 50,
        "alignment": "center",
        "min_width": 50,
    },
    "filename": {
        "title": "Filename",
        "key": "filename",
        "default_visible": True,
        "removable": False,
        "resizable": True,
        "alignment": "left",
        "min_width": 80,
    },
    "file_size": {
        "title": "File Size",
        "key": "file_size",
        "default_visible": True,
        "removable": True,
        "resizable": True,
        "width": 85,
        "alignment": "right",
        "min_width": 40,
    },
    "type": {
        "title": "File Type",
        "display_title": "Type",
        "key": "type",
        "default_visible": True,
        "removable": True,
        "resizable": True,
        "width": 60,
        "alignment": "left",
        "min_width": 30,
    },
    "modified": {
        "title": "Last Modified",
        "key": "modified",
        "default_visible": True,
        "removable": True,
        "resizable": True,
        "width": 154,
        "alignment": "left",
        "min_width": 70,
    },
    "rotation": {
        "title": "Rotation",
        "key": "rotation",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 80,
        "alignment": "left",
        "min_width": 60,
    },
    "duration": {
        "title": "Duration",
        "key": "duration",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 80,
        "alignment": "left",
        "min_width": 60,
    },
    "audio_channels": {
        "title": "Audio Channels",
        "key": "audio_channels",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "audio_format": {
        "title": "Audio Format",
        "key": "audio_format",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "aperture": {
        "title": "Aperture",
        "key": "aperture",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 80,
        "alignment": "left",
        "min_width": 60,
    },
    "iso": {
        "title": "ISO",
        "key": "iso",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 60,
        "alignment": "left",
        "min_width": 50,
    },
    "shutter_speed": {
        "title": "Shutter Speed",
        "key": "shutter_speed",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "white_balance": {
        "title": "White Balance",
        "key": "white_balance",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "image_size": {
        "title": "Image Size",
        "key": "image_size",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "compression": {
        "title": "Compression",
        "key": "compression",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "device_model": {
        "title": "Device Model",
        "key": "device_model",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "device_serial_no": {
        "title": "Device Serial No",
        "key": "device_serial_no",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 140,
        "alignment": "left",
        "min_width": 100,
    },
    "video_fps": {
        "title": "Video FPS",
        "key": "video_fps",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 80,
        "alignment": "left",
        "min_width": 60,
    },
    "video_avg_bitrate": {
        "title": "Video Avg. Bitrate",
        "key": "video_avg_bitrate",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "video_codec": {
        "title": "Video Codec",
        "key": "video_codec",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "video_format": {
        "title": "Video Format",
        "key": "video_format",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "device_manufacturer": {
        "title": "Device Manufacturer",
        "key": "device_manufacturer",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 100,
    },
    "color_space": {
        "title": "Color Space",
        "key": "color_space",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 100,
        "alignment": "left",
        "min_width": 80,
    },
    "artist": {
        "title": "Artist",
        "key": "artist",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 80,
    },
    "copyright": {
        "title": "Copyright",
        "key": "copyright",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 150,
        "alignment": "left",
        "min_width": 100,
    },
    "owner_name": {
        "title": "Owner Name",
        "key": "owner_name",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 120,
        "alignment": "left",
        "min_width": 80,
    },
    "target_umid": {
        "title": "Target UMID",
        "key": "target_umid",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 400,
        "alignment": "left",
        "min_width": 200,
    },
    "file_hash": {
        "title": "File Hash",
        "key": "file_hash",
        "default_visible": False,
        "removable": True,
        "resizable": True,
        "width": 90,
        "alignment": "left",
        "min_width": 70,
    },
}

# =====================================
# HASH / RESULTS LIST COLUMN CONFIG
# =====================================

HASH_LIST_COLUMN_CONFIG = {
    "filename": {
        "title": "Filename",
        "key": "filename",
        "default_visible": True,
        "removable": False,
        "width": None,  # Smart-fill / stretch behavior
        "alignment": "left",
        "min_width": FILE_TABLE_COLUMN_CONFIG["filename"]["min_width"],
    },
    "hash": {
        "title": "Hash",
        "key": "hash",
        "default_visible": True,
        "removable": True,
        "width": 100,  # RESULTS_TABLE_RIGHT_COLUMN_WIDTH
        "alignment": "left",
        "min_width": 70,
    },
}

# =====================================
# METADATA TREE COLUMN CONFIGURATION
# =====================================

METADATA_TREE_COLUMN_CONFIG = {
    "key": {
        "title": "Key",
        "key": "key",
        "default_visible": True,
        "removable": False,
        "width": 140,
        "alignment": "left",
        "min_width": 80,
    },
    "value": {
        "title": "Value",
        "key": "value",
        "default_visible": True,
        "removable": False,
        "width": 600,
        "alignment": "left",
        "min_width": 250,
    },
}
