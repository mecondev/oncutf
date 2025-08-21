"""Metadata Module V2 - Composition-based implementation.

This module provides metadata-based renaming functionality using composition
instead of inheritance to avoid QSS and event propagation conflicts.

Features:
- Hash metadata (MD5, SHA1, SHA256, Blake2b)
- Modified date metadata (Year, Month, Day, Hour, etc.)
- EXIF metadata (Camera, Lens, DateTime, GPS, Technical)
- Clean styling without inheritance pollution
- Independent event handling

Author: Michael Economou
Date: 2025-01-27
"""

from typing import Any, Dict, List, Optional

# from modules.base_module import BaseRenameModule  # Will add back later when needed
from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class MetadataModule:
    """Metadata rename module using composition pattern.
    
    This class contains a BaseRenameModule instance as a member (composition)
    rather than inheriting from it, to avoid styling and event conflicts.
    """
    
    def __init__(self) -> None:
        """Initialize the metadata module."""
        # Create base module as a member, not a parent (will add back later)
        # self._base_module = BaseRenameModule()
        
        # Module configuration
        self._module_name = "Metadata"
        self._module_description = "Use file metadata (hash, dates, EXIF) in the new filename"
        
        # Current selections
        self._selected_category: str = ""
        self._selected_field: str = ""
        
        # Metadata categories and fields
        self._metadata_categories = self._build_metadata_categories()
        
        logger.debug(f"[MetadataModule] Initialized with {len(self._metadata_categories)} categories")
    
    def _build_metadata_categories(self) -> Dict[str, List[str]]:
        """Build the complete metadata categories and fields structure."""
        return {
            "Hash": [
                "MD5",
                "SHA1", 
                "SHA256",
                "Blake2b"
            ],
            "Modified Date": [
                "Year",
                "Month", 
                "Day",
                "Hour",
                "Minute", 
                "Second",
                "Date (YYYY-MM-DD)",
                "Time (HH:MM:SS)",
                "DateTime (YYYY-MM-DD HH:MM:SS)",
                "Timestamp (Unix)"
            ],
            "EXIF": [
                "Camera Make",
                "Camera Model", 
                "Lens Model",
                "DateTime Original",
                "DateTime Digitized",
                "ISO Speed",
                "Aperture",
                "Shutter Speed",
                "Focal Length",
                "GPS Latitude",
                "GPS Longitude",
                "GPS Altitude",
                "Orientation",
                "Color Space",
                "White Balance",
                "Flash",
                "Image Width",
                "Image Height"
            ]
        }
    
    # Properties for compatibility with BaseRenameModule interface
    @property
    def module_name(self) -> str:
        """Get the module name."""
        return self._module_name
    
    @property
    def module_description(self) -> str:
        """Get the module description."""
        return self._module_description
    
    @property
    def base_module(self) -> BaseRenameModule:
        """Get the base module instance."""
        return self._base_module
    
    @property
    def metadata_categories(self) -> Dict[str, List[str]]:
        """Get the metadata categories."""
        return self._metadata_categories
    
    @property
    def selected_category(self) -> str:
        """Get the currently selected category."""
        return self._selected_category
    
    @selected_category.setter
    def selected_category(self, value: str) -> None:
        """Set the selected category."""
        self._selected_category = value
        logger.debug(f"[MetadataModule] Category selected: {value}")
    
    @property
    def selected_field(self) -> str:
        """Get the currently selected field."""
        return self._selected_field
    
    @selected_field.setter  
    def selected_field(self, value: str) -> None:
        """Set the selected field."""
        self._selected_field = value
        logger.debug(f"[MetadataModule] Field selected: {value}")
    
    def get_fields_for_category(self, category: str) -> List[str]:
        """Get the fields for a specific category."""
        return self._metadata_categories.get(category, [])
    
    def process_filename(self, filename: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Process a filename using the selected metadata field.
        
        Args:
            filename: The original filename
            metadata: Optional metadata dictionary
            
        Returns:
            The processed metadata value or empty string if not available
        """
        if not self._selected_category or not self._selected_field:
            return ""
        
        if not metadata:
            return ""
        
        try:
            # Process based on category and field
            if self._selected_category == "Hash":
                return self._process_hash_metadata(metadata)
            elif self._selected_category == "Modified Date":
                return self._process_date_metadata(metadata)
            elif self._selected_category == "EXIF":
                return self._process_exif_metadata(metadata)
            else:
                return ""
                
        except Exception as e:
            logger.warning(f"[MetadataModule] Error processing metadata: {e}")
            return ""
    
    def _process_hash_metadata(self, metadata: Dict[str, Any]) -> str:
        """Process hash metadata."""
        field_map = {
            "MD5": "md5",
            "SHA1": "sha1", 
            "SHA256": "sha256",
            "Blake2b": "blake2b"
        }
        
        hash_key = field_map.get(self._selected_field)
        if hash_key and hash_key in metadata:
            return str(metadata[hash_key])
        return ""
    
    def _process_date_metadata(self, metadata: Dict[str, Any]) -> str:
        """Process modified date metadata."""
        import datetime
        
        # Get modification time
        mtime = metadata.get("mtime")
        if not mtime:
            return ""
        
        try:
            dt = datetime.datetime.fromtimestamp(mtime)
            
            field_map = {
                "Year": dt.strftime("%Y"),
                "Month": dt.strftime("%m"),
                "Day": dt.strftime("%d"), 
                "Hour": dt.strftime("%H"),
                "Minute": dt.strftime("%M"),
                "Second": dt.strftime("%S"),
                "Date (YYYY-MM-DD)": dt.strftime("%Y-%m-%d"),
                "Time (HH:MM:SS)": dt.strftime("%H:%M:%S"),
                "DateTime (YYYY-MM-DD HH:MM:SS)": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "Timestamp (Unix)": str(int(mtime))
            }
            
            return field_map.get(self._selected_field, "")
            
        except Exception:
            return ""
    
    def _process_exif_metadata(self, metadata: Dict[str, Any]) -> str:
        """Process EXIF metadata."""
        exif_data = metadata.get("exif", {})
        if not exif_data:
            return ""
        
        field_map = {
            "Camera Make": "Make",
            "Camera Model": "Model",
            "Lens Model": "LensModel", 
            "DateTime Original": "DateTimeOriginal",
            "DateTime Digitized": "DateTimeDigitized",
            "ISO Speed": "ISOSpeedRatings",
            "Aperture": "FNumber",
            "Shutter Speed": "ExposureTime",
            "Focal Length": "FocalLength",
            "GPS Latitude": "GPSLatitude",
            "GPS Longitude": "GPSLongitude", 
            "GPS Altitude": "GPSAltitude",
            "Orientation": "Orientation",
            "Color Space": "ColorSpace",
            "White Balance": "WhiteBalance",
            "Flash": "Flash",
            "Image Width": "ImageWidth",
            "Image Height": "ImageHeight"
        }
        
        exif_key = field_map.get(self._selected_field)
        if exif_key and exif_key in exif_data:
            return str(exif_data[exif_key])
        return ""
    
    def validate_configuration(self) -> bool:
        """Validate the current module configuration."""
        return bool(self._selected_category and self._selected_field)
    
    def get_configuration_summary(self) -> str:
        """Get a summary of the current configuration."""
        if not self.validate_configuration():
            return "No metadata field selected"
        return f"{self._selected_category}: {self._selected_field}"
    
    def reset_configuration(self) -> None:
        """Reset the module configuration."""
        self._selected_category = ""
        self._selected_field = ""
        logger.debug("[MetadataModule] Configuration reset")
