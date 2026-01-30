"""Module: metadata_field_mapper.py.

Author: Michael Economou
Date: 2025-05-01

Centralized metadata field mapping and value formatting for file table columns and rename modules.
Maps column keys to metadata keys and formats values for compact display.

Based on comprehensive analysis of fast vs extended metadata across multiple file types.
"""

from typing import Any, ClassVar

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataFieldMapper:
    """Centralized metadata field mapping and value formatting.

    Handles:
    - Mapping from column keys to metadata keys (with fallbacks)
    - Value formatting for compact display in file table columns
    - Consistent metadata access across FileTableModel and MetadataModule
    """

    # Mapping from file table column keys to metadata keys (with fallback options)
    # Based on analysis of real metadata from various file types (images, videos, audio)
    FIELD_KEY_MAPPING: ClassVar[dict[str, list[str]]] = {
        # Rotation/Orientation (images use "Orientation", videos use "Rotation")
        "rotation": ["Orientation", "Rotation", "CameraOrientation", "AutoRotate"],
        # Duration (videos and audio files)
        "duration": [
            "Duration",
            "MediaDuration",
            "VideoTrackDuration",
            "AudioTrackDuration",
        ],
        # Audio properties
        "audio_channels": ["AudioChannels", "Channels"],
        "audio_format": ["AudioFormat", "AudioEncoding", "AudioCodec"],
        # Camera settings (available in extended metadata for some videos)
        "aperture": ["FNumber", "Aperture", "ApertureValue"],
        "iso": ["ISO", "ISOSpeeds"],
        "shutter_speed": ["ExposureTime", "ShutterSpeed", "ExposureTimes"],
        "white_balance": ["WhiteBalance", "WhiteBalanceRGB"],
        # Image dimensions (special handling - combines width x height)
        "image_size": ["ImageWidth", "ImageHeight"],  # Handled specially in get_value()
        # Compression and encoding
        "compression": ["Compression", "CompressionType"],
        # Device information
        "device_model": ["Model", "CameraModel"],
        "device_manufacturer": ["Make", "Manufacturer"],
        "device_serial_no": [
            "SerialNumber",
            "CameraSerialNumber",
            "DeviceSerialNo",
            "OtherSerialNumber",
        ],
        # Video properties
        "video_fps": ["VideoFrameRate", "FrameRate"],
        "video_avg_bitrate": ["AvgBitrate", "BitRate", "VideoBitrate"],
        "video_codec": ["VideoCodec", "Codec"],
        "video_format": ["MajorBrand", "Format", "FileType"],
        # Descriptive metadata (cross-format support)
        "title": ["Title", "ImageDescription", "XMP:Title", "EXIF:ImageDescription"],
        "artist": ["Artist", "Creator", "EXIF:Artist", "XMP:Creator"],
        "description": [
            "Description",
            "ImageDescription",
            "XMP:Description",
            "EXIF:ImageDescription",
        ],
        "keywords": ["Keywords", "IPTC:Keywords", "XMP:Keywords"],
        "copyright": ["Copyright", "EXIF:Copyright", "XMP:Rights"],
        # Unique identifiers
        "target_umid": [
            "TargetMaterialUmidRef",
            "TargetMaterialUMID",
            "UMID",
            "MaterialUMID",
            "QuickTime:TargetMaterialUmidRef",
            "QuickTime:TargetMaterialUMID",
            "QuickTime:UMID",
            "QuickTime:MaterialUMID",
            "XMP:TargetMaterialUmidRef",
            "XMP:TargetMaterialUMID",
            "XMP:UMID",
            "XMP:MaterialUMID",
            "File:TargetMaterialUmidRef",
            "File:TargetMaterialUMID",
            "File:UMID",
            "File:MaterialUMID",
        ],
    }

    @classmethod
    def get_metadata_value(cls, metadata_dict: dict[str, Any], field_key: str) -> str:
        """Get metadata value for a field key with fallback support and formatting.

        Args:
            metadata_dict: Dictionary containing metadata
            field_key: Column key (e.g., "rotation", "aperture", etc.)

        Returns:
            Formatted string value for display, or empty string if not found

        """
        if not isinstance(metadata_dict, dict) or not metadata_dict:
            return ""

        # Special handling for image_size (combines width x height)
        if field_key == "image_size":
            return cls._get_image_size_value(metadata_dict)

        # Get possible metadata keys for this field
        possible_keys = cls.FIELD_KEY_MAPPING.get(field_key, [])
        if not possible_keys:
            logger.debug("No mapping defined for field key: %s", field_key)
            return ""

        # Try each possible key until we find a value
        raw_value = None
        found_key = None
        for key in possible_keys:
            if key in metadata_dict:
                raw_value = metadata_dict[key]
                found_key = key
                break

        if raw_value is None:
            # Debug logging for UMID specifically
            if field_key == "target_umid":
                logger.debug(
                    "UMID not found. Available keys: %s...",
                    list(metadata_dict.keys())[:10],
                    extra={"dev_only": True},
                )
            return ""

        # Format the value for display
        formatted_value = cls._format_value_for_display(field_key, found_key, raw_value)

        logger.debug(
            "Mapped %s -> %s = '%s' -> '%s'",
            field_key,
            found_key,
            raw_value,
            formatted_value,
            extra={"dev_only": True},
        )
        return formatted_value

    @classmethod
    def _get_image_size_value(cls, metadata_dict: dict[str, Any]) -> str:
        """Special handling for image size (combines width x height).

        Args:
            metadata_dict: Dictionary containing metadata

        Returns:
            Formatted image size string (e.g., "1920x1080") or empty string

        """
        # Try different possible keys for width and height
        width_keys = ["ImageWidth", "ExifImageWidth", "PixelXDimension"]
        height_keys = ["ImageHeight", "ExifImageHeight", "PixelYDimension"]

        width = None
        height = None

        # Find width
        for key in width_keys:
            if metadata_dict.get(key):
                try:
                    width = int(metadata_dict[key])
                    break
                except (ValueError, TypeError):
                    continue

        # Find height
        for key in height_keys:
            if metadata_dict.get(key):
                try:
                    height = int(metadata_dict[key])
                    break
                except (ValueError, TypeError):
                    continue

        if width and height:
            return f"{width}x{height}"

        return ""

    @classmethod
    def _format_value_for_display(
        cls, field_key: str, _metadata_key: str | None, raw_value: Any
    ) -> str:
        """Format metadata value for compact display in file table columns.

        Args:
            field_key: Column key (e.g., "rotation", "aperture")
            metadata_key: Actual metadata key that was found
            raw_value: Raw metadata value

        Returns:
            Formatted string for display

        """
        if raw_value is None:
            return ""

        # Convert to string
        value_str = str(raw_value).strip()
        if not value_str:
            return ""

        # Field-specific formatting
        if field_key == "rotation":
            return cls._format_rotation_value(value_str)
        elif field_key == "duration":
            return cls._format_duration_value(value_str)
        elif field_key in ["aperture", "iso", "shutter_speed"]:
            return cls._format_camera_setting_value(field_key, value_str)
        elif field_key in ["device_model", "device_manufacturer"]:
            return cls._format_device_value(value_str)
        elif field_key in ["video_fps", "video_avg_bitrate"]:
            return cls._format_video_value(field_key, value_str)
        elif field_key in ["target_umid", "file_hash", "device_serial_no"]:
            # Keep full value for long identifiers; let the view elide visually
            cleaned = " ".join(value_str.split())
            return cleaned
        else:
            # Default formatting - limit length and clean up
            return cls._format_default_value(value_str)

    @classmethod
    def _format_rotation_value(cls, value: str) -> str:
        """Format rotation/orientation values consistently.

        Examples:
            "Horizontal (normal)" -> "0°"
            "0" -> "0°"
            "90" -> "90°"
            "180" -> "180°"

        """
        value_lower = value.lower()

        # Handle text-based orientation values
        if "horizontal" in value_lower and "normal" in value_lower:
            return "0°"
        elif "rotate" in value_lower and "90" in value_lower:
            return "90°"
        elif "rotate" in value_lower and "180" in value_lower:
            return "180°"
        elif "rotate" in value_lower and "270" in value_lower:
            return "270°"

        # Handle numeric values
        try:
            numeric_value = float(value)
            if numeric_value == int(numeric_value):  # Whole number
                return f"{int(numeric_value)}°"
            else:
                return f"{numeric_value:.1f}°"
        except ValueError:
            pass

        # Fallback - return as is but limit length
        return value[:10]

    @classmethod
    def _format_duration_value(cls, value: str) -> str:
        """Format duration values for compact display.

        Examples:
            "0:01:23" -> "1:23"
            "00:00:05.50" -> "5.5s"
            "123.45 s" -> "2:03"

        """
        # Try to parse common duration formats
        value_clean = value.replace(" s", "").replace("s", "").strip()

        # Handle HH:MM:SS format
        if ":" in value_clean:
            parts = value_clean.split(":")
            if len(parts) >= 2:
                try:
                    # Get minutes and seconds
                    if len(parts) == 3:  # HH:MM:SS
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        seconds = float(parts[2])
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                    else:  # MM:SS
                        minutes = int(parts[0])
                        seconds = float(parts[1])
                        total_seconds = minutes * 60 + seconds

                    # Format compactly
                    if total_seconds < 60:
                        return f"{total_seconds:.1f}s"
                    elif total_seconds < 3600:
                        mins = int(total_seconds // 60)
                        secs = int(total_seconds % 60)
                        return f"{mins}:{secs:02d}"
                    else:
                        hours = int(total_seconds // 3600)
                        mins = int((total_seconds % 3600) // 60)
                        return f"{hours}h{mins}m"
                except ValueError:
                    pass

        # Handle numeric seconds
        try:
            seconds = float(value_clean)
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                mins = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{mins}:{secs:02d}"
            else:
                hours = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                return f"{hours}h{mins}m"
        except ValueError:
            pass

        # Fallback - return original value, truncated
        return value[:10]

    @classmethod
    def _format_camera_setting_value(cls, field_key: str, value: str) -> str:
        """Format camera settings (aperture, ISO, shutter speed) for display.

        Examples:
            "2.8" -> "f/2.8" (aperture)
            "1/250" -> "1/250" (shutter speed)
            "100" -> "ISO 100" (ISO)

        """
        if field_key == "aperture":
            # Add f/ prefix for aperture values
            try:
                numeric = float(value)
                return f"f/{numeric:.1f}"
            except ValueError:
                return value[:8]

        elif field_key == "iso":
            # Add ISO prefix for ISO values
            try:
                numeric = int(float(value))
                return f"ISO {numeric}"
            except ValueError:
                return value[:8]

        elif field_key == "shutter_speed":
            # Format shutter speed
            if "/" in value:
                return value  # Already in fraction format
            try:
                numeric = float(value)
                if numeric >= 1:
                    return f"{numeric:.1f}s"
                else:
                    # Convert to fraction
                    denominator = int(1 / numeric)
                    return f"1/{denominator}"
            except ValueError:
                return value[:10]

        return value[:10]

    @classmethod
    def _format_device_value(cls, value: str) -> str:
        """Format device model/manufacturer values (keep as-is, but limit length).

        Examples:
            "NIKON D800" -> "NIKON D800" (keep as requested)
            "Canon EOS 5D Mark IV" -> "Canon EOS 5D Mark IV"

        """
        # Keep device names as-is but limit to reasonable length for columns
        return value[:20]

    @classmethod
    def _format_video_value(cls, field_key: str, value: str) -> str:
        """Format video-specific values.

        Examples:
            "29.97" -> "30 fps" (video_fps)
            "5000000" -> "5 Mbps" (video_avg_bitrate)

        """
        if field_key == "video_fps":
            try:
                fps = float(value)
                return f"{fps:.0f} fps"
            except ValueError:
                return value[:8]

        elif field_key == "video_avg_bitrate":
            try:
                bitrate = int(float(value))
                if bitrate >= 1000000:
                    return f"{bitrate // 1000000} Mbps"
                elif bitrate >= 1000:
                    return f"{bitrate // 1000} kbps"
                else:
                    return f"{bitrate} bps"
            except ValueError:
                return value[:10]

        return value[:10]

    @classmethod
    def _format_default_value(cls, value: str) -> str:
        """Default value formatting - clean up and limit length.

        Args:
            value: Raw string value

        Returns:
            Cleaned and truncated value

        """
        # Remove extra whitespace
        cleaned = " ".join(value.split())

        # Limit length for column display
        if len(cleaned) > 15:
            return cleaned[:12] + "..."

        return cleaned

    @classmethod
    def get_available_field_keys(cls) -> list[str]:
        """Get list of all available field keys that can be mapped.

        Returns:
            List of field keys (column keys) that have mappings defined

        """
        return list(cls.FIELD_KEY_MAPPING.keys())

    @classmethod
    def get_metadata_keys_for_field(cls, field_key: str) -> list[str]:
        """Get list of metadata keys that are checked for a given field key.

        Args:
            field_key: Column key (e.g., "rotation", "aperture")

        Returns:
            List of metadata keys that are checked in order

        """
        return cls.FIELD_KEY_MAPPING.get(field_key, [])

    @classmethod
    def has_field_mapping(cls, field_key: str) -> bool:
        """Check if a field key has a mapping defined.

        Args:
            field_key: Column key to check

        Returns:
            True if mapping exists, False otherwise

        """
        return field_key in cls.FIELD_KEY_MAPPING
