"""Metadata to column key mapping utilities.

Handles translation between metadata keys and file table column keys.

Author: Michael Economou
Date: 2026-01-05
"""
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)

# Direct metadata key to column key mapping
METADATA_TO_COLUMN_MAPPING = {
    # Image metadata
    "EXIF:ImageWidth": "image_size",
    "EXIF:ImageHeight": "image_size",
    "EXIF:Orientation": "rotation",
    "EXIF:ISO": "iso",
    "EXIF:FNumber": "aperture",
    "EXIF:ExposureTime": "shutter_speed",
    "EXIF:WhiteBalance": "white_balance",
    "EXIF:Compression": "compression",
    "EXIF:Make": "device_manufacturer",
    "EXIF:Model": "device_model",
    "EXIF:SerialNumber": "device_serial_no",
    # Video metadata
    "QuickTime:Duration": "duration",
    "QuickTime:VideoFrameRate": "video_fps",
    "QuickTime:AvgBitrate": "video_avg_bitrate",
    "QuickTime:VideoCodec": "video_codec",
    "QuickTime:MajorBrand": "video_format",
    # Audio metadata
    "QuickTime:AudioChannels": "audio_channels",
    "QuickTime:AudioFormat": "audio_format",
    # File metadata
    "File:FileSize": "file_size",
    "File:FileType": "type",
    "File:FileModifyDate": "modified",
    "File:MD5": "file_hash",
    "File:SHA1": "file_hash",
    "File:SHA256": "file_hash",
}


def map_metadata_key_to_column_key(metadata_key: str) -> str | None:
    """Map a metadata key path to a file table column key.

    Args:
        metadata_key: Metadata key path (e.g., "EXIF:Make")

    Returns:
        Column key if found, None otherwise
    """
    try:
        # Direct mapping
        if metadata_key in METADATA_TO_COLUMN_MAPPING:
            return METADATA_TO_COLUMN_MAPPING[metadata_key]

        # Fuzzy matching for common patterns
        key_lower = metadata_key.lower()

        if "rotation" in key_lower or "orientation" in key_lower:
            return "rotation"
        elif "duration" in key_lower:
            return "duration"
        elif "iso" in key_lower:
            return "iso"
        elif "aperture" in key_lower or "fnumber" in key_lower:
            return "aperture"
        elif "shutter" in key_lower or "exposure" in key_lower:
            return "shutter_speed"
        elif "white" in key_lower and "balance" in key_lower:
            return "white_balance"
        elif "compression" in key_lower:
            return "compression"
        elif "make" in key_lower or "manufacturer" in key_lower:
            return "device_manufacturer"
        elif "model" in key_lower:
            return "device_model"
        elif "serial" in key_lower:
            return "device_serial_no"
        elif "framerate" in key_lower or "fps" in key_lower:
            return "video_fps"
        elif "bitrate" in key_lower:
            return "video_avg_bitrate"
        elif "codec" in key_lower:
            return "video_codec"
        elif "format" in key_lower:
            if "audio" in key_lower:
                return "audio_format"
            elif "video" in key_lower:
                return "video_format"
        elif "channels" in key_lower and "audio" in key_lower:
            return "audio_channels"
        elif "size" in key_lower and (
            "image" in key_lower or "width" in key_lower or "height" in key_lower
        ):
            return "image_size"
        elif "hash" in key_lower or "md5" in key_lower or "sha" in key_lower:
            return "file_hash"

    except Exception as e:
        logger.warning("Error mapping metadata key to column key: %s", e)

    return None


__all__ = ["map_metadata_key_to_column_key", "METADATA_TO_COLUMN_MAPPING"]
