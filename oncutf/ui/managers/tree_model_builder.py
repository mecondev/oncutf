"""Module: build_metadata_tree_model.py.

Author: Michael Economou
Date: 2025-05-10

utils/build_metadata_tree_model.py
Provides a utility function for converting nested metadata
(dicts/lists) into a QStandardItemModel suitable for display in a QTreeView.
Enhanced with better metadata grouping and extended metadata indicators.
"""

import re
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QStandardItem, QStandardItemModel

from oncutf.config import METADATA_ICON_COLORS

# Initialize Logger
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


def format_key(key: str) -> str:
    """Convert 'ImageSensorType' -> 'Image Sensor Type'."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", key)


def classify_key(key: str) -> str:
    """Classify a metadata key into a detailed group label.
    Enhanced grouping for better organization of metadata.
    """
    key_lower = key.lower()

    # File-related metadata
    if key_lower.startswith("draft") or key_lower in {
        "rotation",
        "directory",
        "sourcefile",
    }:
        return "File Info"

    # Camera Settings - Critical for photography/videography
    if any(
        term in key_lower
        for term in [
            "iso",
            "aperture",
            "fnumber",
            "shutter",
            "exposure",
            "focal",
            "flash",
            "metering",
            "whitebalance",
            "gain",
            "lightvalue",
        ]
    ):
        return "Camera Settings"

    # GPS and Location
    if any(term in key_lower for term in ["gps", "location", "latitude", "longitude", "altitude"]):
        return "GPS & Location"

    # Sensor Data (accelerometer, gyroscope, etc.)
    if any(
        term in key_lower
        for term in [
            "accelerometer",
            "gyro",
            "pitch",
            "roll",
            "yaw",
            "rotation",
            "orientation",
            "gravity",
            "magnetometer",
            "compass",
        ]
    ):
        return "Sensor Data"

    # Audio-related metadata
    if key_lower.startswith("audio") or key_lower in {
        "samplerate",
        "channelmode",
        "bitrate",
        "title",
        "album",
        "artist",
        "composer",
        "genre",
        "duration",
    }:
        return "Audio Info"

    # Image-specific metadata
    if (
        key_lower.startswith("image")
        or "sensor" in key_lower
        or any(term in key_lower for term in ["width", "height", "resolution", "dpi", "colorspace"])
    ):
        return "Image Info"

    # Video-specific metadata
    if any(
        term in key_lower
        for term in [
            "movie",
            "frame",
            "codec",
            "bitrate",
            "fps",
            "duration",
            "format",
            "avgbitrate",
            "maxbitrate",
            "videocodec",
        ]
    ):
        return "Video Info"

    # Color and Processing
    if any(
        term in key_lower
        for term in [
            "color",
            "saturation",
            "contrast",
            "brightness",
            "hue",
            "gamma",
            "curve",
            "tone",
            "highlight",
            "shadow",
            "vibrance",
        ]
    ):
        return "Color & Processing"

    # Lens Information
    if any(
        term in key_lower
        for term in ["lens", "zoom", "focus", "distortion", "vignetting", "chromatic"]
    ):
        return "Lens Info"

    # Copyright and Rights
    if any(
        term in key_lower
        for term in ["copyright", "rights", "creator", "owner", "license", "usage"]
    ):
        return "Copyright & Rights"

    # Technical/System
    if any(
        term in key_lower
        for term in [
            "version",
            "software",
            "firmware",
            "make",
            "model",
            "serial",
            "uuid",
            "id",
        ]
    ):
        return "Technical Info"

    # Everything else
    return "Other"


def create_item(text: str, alignment: Any = None, icon_name: str | None = None) -> QStandardItem:
    """Create a QStandardItem with given text, alignment, and optional icon."""
    item = QStandardItem(text)
    if alignment is None:
        alignment = Qt.AlignLeft
    item.setTextAlignment(Qt.Alignment(alignment))

    # Set icon if provided
    if icon_name:
        try:
            from oncutf.ui.services.icon_service import get_menu_icon

            icon = get_menu_icon(icon_name)
            if icon:
                item.setIcon(icon)
        except Exception:
            # Silently fail if icon loading fails
            pass

    return item


def _format_list_value(value: list[Any]) -> str:
    """Format list values for display in the metadata tree."""
    if not value:
        return ""
    if all(isinstance(item, dict) for item in value):
        return ""
    return str(value[0])


def _append_metadata_row(
    parent_item: QStandardItem,
    key: str,
    value: Any,
    group_name: str,
    modified_keys: set[str],
    extended_keys: set[str],
) -> None:
    """Append metadata rows recursively for nested dictionaries and lists."""
    if isinstance(value, dict):
        group_item = create_item(format_key(key))
        group_item.setEditable(False)
        dummy_value_item = create_item("")

        for child_key, child_value in sorted(value.items(), key=lambda item: item[0].lower()):
            _append_metadata_row(
                group_item,
                child_key,
                child_value,
                group_name,
                modified_keys,
                extended_keys,
            )

        parent_item.appendRow([group_item, dummy_value_item])
        return

    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            group_item = create_item(format_key(key))
            group_item.setEditable(False)
            dummy_value_item = create_item("")

            for index, item_value in enumerate(value):
                _append_metadata_row(
                    group_item,
                    f"{key}[{index}]",
                    item_value,
                    group_name,
                    modified_keys,
                    extended_keys,
                )

            parent_item.appendRow([group_item, dummy_value_item])
            return

        value = _format_list_value(value)

    key_item = create_item(format_key(key))
    value_item = create_item(str(value))

    key_path = f"{group_name}/{key}"
    direct_match = key_path in modified_keys or key in modified_keys
    suffix_match = any(mk.endswith(f"/{key}") or mk == key for mk in modified_keys)
    is_modified = direct_match or suffix_match
    is_extended = key in extended_keys

    if is_modified:
        modified_font = QFont()
        modified_font.setBold(True)
        key_item.setFont(modified_font)

        modified_color = QColor(METADATA_ICON_COLORS["modified"])
        key_item.setForeground(modified_color)

        key_item.setToolTip("Modified value" + (" (extended metadata)" if is_extended else ""))
        value_item.setToolTip("Modified value" + (" (extended metadata)" if is_extended else ""))
    elif is_extended:
        extended_font = QFont()
        extended_font.setItalic(True)
        key_item.setFont(extended_font)
        value_item.setFont(extended_font)

        key_item.setText(f"[Ext] {format_key(key)}")
        key_item.setToolTip("Available only in extended metadata mode")
        value_item.setToolTip("Available only in extended metadata mode")

        extended_color = QColor(100, 150, 255)
        key_item.setForeground(extended_color)

    parent_item.appendRow([key_item, value_item])


def get_hidden_fields_for_level(level: str = "essential") -> set[str]:
    """Get the set of fields to hide based on the display level.

    Args:
        level: Display level - "essential", "standard", or "all"

    Returns:
        Set of field names to hide

    """
    # Always hide ExopsisVersion regardless of level
    always_hidden = {"ExopsisVersion"}

    if level == "all":
        return always_hidden

    # Standard level - hide technical binary/offset fields
    standard_hidden = always_hidden | {
        "Directory",
        "SourceFile",
        "FileAccessDate",
        "FileInodeChangeDate",
        "FilePermissions",
        "FileTypeExtension",
        "MIMEType",
        "ExifByteOrder",
        "ThumbnailOffset",
        "ThumbnailLength",
        "ThumbnailImage",
        "PreviewImage",
        "JpgFromRaw",
        "TiffThumbnail",
        "StripOffsets",
        "StripByteCounts",
        "RowsPerStrip",
        "Padding",
        "OffsetSchema",
        "ExifInteroperabilityOffset",
        "InteroperabilityIndex",
        "InteroperabilityVersion",
    }

    if level == "standard":
        return standard_hidden

        # Essential level (default) - hide most technical fields
    return standard_hidden | {
        # Image format technical fields
        "Compression",
        "PhotometricInterpretation",
        "SamplesPerPixel",
        "PlanarConfiguration",
        "SubfileType",
        "YCbCrCoefficients",
        "YCbCrSubSampling",
        "YCbCrPositioning",
        "ReferenceBlackWhite",
        "BitsPerSample",
        "Predictor",
        "FillOrder",
        "DocumentName",
        "ImageDescription",
        "StripByteCounts",
        "MinSampleValue",
        "MaxSampleValue",
        "XResolution",
        "YResolution",
        "ResolutionUnit",
        "TransferFunction",
        "WhitePoint",
        "PrimaryChromaticities",
        # EXIF technical fields
        "ExifVersion",
        "ComponentsConfiguration",
        "FlashpixVersion",
        "RelatedSoundFile",
        "PrintImageMatching",
        "SubSecTime",
        "SubSecTimeOriginal",
        "SubSecTimeDigitized",
        "SpectralSensitivity",
        "OECF",
        "SensitivityType",
        "StandardOutputSensitivity",
        "RecommendedExposureIndex",
        "ISOSpeed",
        "ISOSpeedLatitudeyyy",
        "ISOSpeedLatitudezzz",
        "ExifImageWidth",
        "ExifImageHeight",
        "FileSource",
        "SceneType",
        "CFAPattern",
        "CustomRendered",
        "ExposureMode",
        "WhiteBalance",
        "DigitalZoomRatio",
        "FocalLengthIn35mmFilm",
        "SceneCaptureType",
        "GainControl",
        "Contrast",
        "Saturation",
        "Sharpness",
        "DeviceSettingDescription",
        "SubjectDistanceRange",
        "ImageUniqueID",
        "CameraOwnerName",
        "BodySerialNumber",
        "LensSpecification",
        "LensModel",
        "LensSerialNumber",
        "LensMake",
        "LensInfo",
        # Video technical fields (for MP4/MOV files)
        "CompressorID",
        "SourceImageWidth",
        "SourceImageHeight",
        "CompressorName",
        "BitDepth",
        "ColorTable",
        "GraphicsMode",
        "OpColor",
        "Balance",
        "AudioFormat",
        "AudioVendorID",
        "AudioChannels",
        "AudioBitsPerSample",
        "AudioSampleRate",
        "MatrixStructure",
        "MediaHeaderVersion",
        "MediaCreateDate",
        "MediaModifyDate",
        "MediaTimeScale",
        "MediaDuration",
        "MediaLanguageCode",
        "HandlerClass",
        "HandlerVendorID",
        "HandlerDescription",
        "VideoFrameRate",
        "VideoCodecID",
        "VideoBitrate",
        "AudioCodecID",
        "AudioBitrate",
        "MovieHeaderVersion",
        "CreateDate",
        "ModifyDate",
        "TimeScale",
        "Duration",
        "PreferredRate",
        "PreferredVolume",
        "PreviewTime",
        "PreviewDuration",
        "PosterTime",
        "SelectionTime",
        "SelectionDuration",
        "CurrentTime",
        "NextTrackID",
        # RAW/DNG technical fields
        "CFARepeatPatternDim",
        "BlackLevel",
        "WhiteLevel",
        "DefaultScale",
        "BestQualityScale",
        "DefaultCropOrigin",
        "DefaultCropSize",
        "CalibrationIlluminant1",
        "CalibrationIlluminant2",
        "ColorMatrix1",
        "ColorMatrix2",
        "CameraCalibration1",
        "CameraCalibration2",
        "ReductionMatrix1",
        "ReductionMatrix2",
        "AnalogBalance",
        "AsShotNeutral",
        "AsShotWhiteXY",
        "BaselineExposure",
        "BaselineNoise",
        "BaselineSharpness",
        "BayerGreenSplit",
        "LinearResponseLimit",
        "AntiAliasStrength",
        "ShadowScale",
        "DNGVersion",
        "DNGBackwardVersion",
        "UniqueCameraModel",
        "LocalizedCameraModel",
        "DNGPrivateData",
        "MakerNoteSafety",
        "RawDataUniqueID",
        "OriginalRawFileName",
        "OriginalRawFileData",
        "ActiveArea",
        "MaskedAreas",
        "AsShotICCProfile",
        "AsShotPreProfileMatrix",
        "CurrentICCProfile",
        "CurrentPreProfileMatrix",
        "ColorimetricReference",
        "CameraCalibrationSignature",
        "ProfileCalibrationSignature",
        "ExtraCameraProfiles",
        "AsShotProfileName",
        "NoiseReductionApplied",
        "NoiseProfile",
        "DefaultUserCrop",
        "DefaultBlackRender",
        "BaselineExposureOffset",
        "ProfileLookTableDims",
        "ProfileLookTableData",
        "OpcodeList1",
        "OpcodeList2",
        "OpcodeList3",
        # Binary/proprietary fields
        "MakerNote",
        "UserComment",
        "XMP",
        "IPTC",
        "ICC_Profile",
        "Photoshop",
        "APP14",
        "JFIF",
        "Adobe",
        "FlashPix",
        "PrintIM",
        "Interoperability",
        # GPS technical details (keep basic GPS but hide technical)
        "GPSVersionID",
        "GPSMapDatum",
        "GPSMeasureMode",
        "GPSDOP",
        "GPSSpeedRef",
        "GPSTrackRef",
        "GPSImgDirectionRef",
        "GPSDestBearingRef",
        "GPSDestDistanceRef",
        "GPSProcessingMethod",
        "GPSAreaInformation",
        "GPSDifferential",
    }


def build_metadata_tree_model(
    metadata: dict[str, Any],
    modified_keys: set[str] | None = None,
    extended_keys: set[str] | None = None,
    _display_level: str = "all",
) -> QStandardItemModel:
    """Build a tree model for metadata display with enhanced grouping and extended metadata indicators.

    Args:
        metadata: Dictionary containing metadata
        modified_keys: Set of keys that have been modified
        extended_keys: Set of keys that are only available in extended metadata mode
        display_level: Display level - always "all" (no filtering)

    """
    logger.debug(">>> build_metadata_tree_model called", extra={"dev_only": True})
    logger.debug(
        "metadata type: %s | keys: %s",
        type(metadata),
        list(metadata.keys()) if isinstance(metadata, dict) else "N/A",
        extra={"dev_only": True},
    )

    if modified_keys is None:
        modified_keys = set()
    if extended_keys is None:
        extended_keys = set()

    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Key", "Value"])
    root_item = model.invisibleRootItem()

    grouped: dict[str, list[tuple[str, Any]]] = {}

    for key, value in metadata.items():
        # Skip internal markers
        if key.startswith("__"):
            continue

        group = classify_key(key)
        grouped.setdefault(group, []).append((key, value))

    # Sort groups with File Info first, then alphabetically
    def group_sort_key(group_name: str) -> tuple[int, str]:
        if group_name == "File Info":
            return (0, "File Info")  # Always first
        if group_name == "Other":
            return (2, group_name)  # Always last
        return (1, group_name)  # Alphabetical order for everything else

    ordered_groups = sorted(grouped.keys(), key=group_sort_key)

    for group_name in ordered_groups:
        items = grouped[group_name]
        logger.debug(
            "Creating group: %s with %d items",
            group_name,
            len(items),
            extra={"dev_only": True},
        )

        # Sort items alphabetically within each group
        items.sort(key=lambda item: item[0].lower())

        # Check if this group has extended metadata
        group_has_extended = any(key in extended_keys for key, _ in items)

        # Create group item with enhanced styling
        if group_has_extended:
            display_name = f"{group_name} [Extended] ({len(items)})"
        else:
            display_name = f"{group_name} ({len(items)})"

        group_item = QStandardItem(display_name)
        group_item.setEditable(False)
        group_item.setSelectable(False)

        # Set font with specific size and bold weight for cross-platform consistency
        group_font = QFont()
        group_font.setBold(True)
        group_font.setPointSize(10)
        group_item.setFont(group_font)

        # Add tooltip for extended groups using Qt's native tooltip system
        # Note: We use setToolTip() instead of our custom tooltip system
        # because QStandardItem is not a QWidget and doesn't support our tooltip system
        if group_has_extended:
            extended_count = sum(1 for key, _ in items if key in extended_keys)
            group_item.setToolTip(f"Contains {extended_count} keys from extended metadata")

        dummy_value_item = QStandardItem("")  # empty second column
        dummy_value_item.setSelectable(False)

        for key, value in items:
            _append_metadata_row(
                group_item,
                key,
                value,
                group_name,
                modified_keys,
                extended_keys,
            )

        root_item.appendRow([group_item, dummy_value_item])

    return model
