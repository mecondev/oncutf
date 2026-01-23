"""Module: field_formatter.py.

Author: Michael Economou
Date: 2025-12-24

Utilities for formatting metadata field names for display.
Handles common metadata prefixes, underscore-separated names, and camelCase.
"""

import re


class FieldFormatter:
    """Formatter for metadata field names to improve readability."""

    # Common replacements for better readability
    FIELD_REPLACEMENTS = {
        "Exif": "EXIF",
        "Gps": "GPS",
        "Iso": "ISO",
        "Rgb": "RGB",
        "Dpi": "DPI",
        "Device": "Device",
        "Model": "Model",
        "Make": "Make",
        "Serial": "Serial",
        "Number": "Number",
        "Date": "Date",
        "Time": "Time",
        "Width": "Width",
        "Height": "Height",
        "Size": "Size",
        "Format": "Format",
        "Codec": "Codec",
        "Frame": "Frame",
        "Rate": "Rate",
        "Bit": "Bit",
        "Audio": "Audio",
        "Video": "Video",
        "Image": "Image",
        "Camera": "Camera",
        "Lens": "Lens",
        "Focal": "Focal",
        "Length": "Length",
        "Aperture": "Aperture",
        "Shutter": "Shutter",
        "Exposure": "Exposure",
        "White": "White",
        "Balance": "Balance",
        "Flash": "Flash",
        "Metering": "Metering",
        "Mode": "Mode",
        "Program": "Program",
        "Sensitivity": "Sensitivity",
        "Compression": "Compression",
        "Quality": "Quality",
        "Resolution": "Resolution",
        "Pixel": "Pixel",
        "Dimension": "Dimension",
        "Orientation": "Orientation",
        "Rotation": "Rotation",
        "Duration": "Duration",
        "Track": "Track",
        "Channel": "Channel",
        "Sample": "Sample",
        "Frequency": "Frequency",
        "Bitrate": "Bitrate",
        "Brand": "Brand",
        "Type": "Type",
        "Version": "Version",
        "Software": "Software",
        "Hardware": "Hardware",
        "Manufacturer": "Manufacturer",
        "Creator": "Creator",
        "Artist": "Artist",
        "Author": "Author",
        "Copyright": "Copyright",
        "Rights": "Rights",
        "Description": "Description",
        "Comment": "Comment",
        "Keyword": "Keyword",
        "Tag": "Tag",
        "Label": "Label",
        "Category": "Category",
        "Genre": "Genre",
        "Subject": "Subject",
        "Title": "Title",
        "Headline": "Headline",
        "Caption": "Caption",
        "Abstract": "Abstract",
        "Location": "Location",
        "Place": "Place",
        "Country": "Country",
        "City": "City",
        "State": "State",
        "Province": "Province",
        "Address": "Address",
        "Street": "Street",
        "Coordinate": "Coordinate",
        "Latitude": "Latitude",
        "Longitude": "Longitude",
        "Altitude": "Altitude",
        "Direction": "Direction",
        "Bearing": "Bearing",
        "Distance": "Distance",
        "Area": "Area",
        "Volume": "Volume",
        "Weight": "Weight",
        "Mass": "Mass",
        "Temperature": "Temperature",
        "Pressure": "Pressure",
        "Humidity": "Humidity",
        "Weather": "Weather",
        "Light": "Light",
        "Color": "Color",
        "Tone": "Tone",
        "Saturation": "Saturation",
        "Brightness": "Brightness",
        "Contrast": "Contrast",
        "Sharpness": "Sharpness",
        "Noise": "Noise",
        "Grain": "Grain",
        "Filter": "Filter",
        "Effect": "Effect",
        "Style": "Style",
        "Theme": "Theme",
        "Mood": "Mood",
        "Atmosphere": "Atmosphere",
    }

    @staticmethod
    def format_metadata_key_name(key: str) -> str:
        """Format metadata key names for better readability.

        Args:
            key: The raw metadata key name (e.g., "EXIF:DeviceName", "file_name")

        Returns:
            Formatted key name for display (e.g., "EXIF: Device Name", "File Name")

        """
        # Handle common metadata prefixes and formats
        if ":" in key:
            # Split by colon (e.g., "EXIF:DeviceName" -> "EXIF: Device Name")
            parts = key.split(":", 1)
            if len(parts) == 2:
                prefix, field = parts
                # Format the field part
                formatted_field = FieldFormatter._format_field_name(field)
                return f"{prefix}: {formatted_field}"

        # Handle underscore-separated keys
        if "_" in key:
            return FieldFormatter._format_field_name(key)

        # Handle camelCase keys
        if key != key.lower() and key != key.upper():
            return FieldFormatter._format_camel_case(key)

        return key

    @staticmethod
    def _format_field_name(field: str) -> str:
        """Format field names by replacing underscores and applying replacements.

        Args:
            field: The field name to format (e.g., "device_name", "iso_speed")

        Returns:
            Formatted field name (e.g., "Device Name", "ISO Speed")

        """
        # Replace underscores with spaces and title case
        formatted = field.replace("_", " ").title()

        # Apply common replacements for better readability
        for old, new in FieldFormatter.FIELD_REPLACEMENTS.items():
            formatted = formatted.replace(old, new)

        return formatted

    @staticmethod
    def _format_camel_case(text: str) -> str:
        """Format camelCase text by adding spaces before capitals.

        Args:
            text: The camelCase text to format (e.g., "DeviceName")

        Returns:
            Formatted text with spaces (e.g., "Device Name")

        """
        # Add space before capital letters, but not at the beginning
        formatted = re.sub(r"(?<!^)(?=[A-Z])", " ", text)
        return formatted.title()
