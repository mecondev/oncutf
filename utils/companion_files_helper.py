"""
companion_files_helper.py

Utility for detecting and managing companion/sidecar files that are associated with main media files.
Handles patterns like Sony camera XML files, XMP sidecar files, etc.

Author: Michael Economou
Date: 2025-11-25
"""

import os
import re
from pathlib import Path
from typing import Any

from utils.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class CompanionFilesHelper:
    """
    Handles detection and management of companion/sidecar files.

    Common companion file patterns:
    - Sony cameras: C8227.MP4 + C8227M01.XML
    - XMP sidecar: IMG_1234.CR2 + IMG_1234.xmp
    - LUT files: video.mp4 + video.cube
    - Subtitle files: movie.mp4 + movie.srt
    """

    # Companion file patterns (extension -> companion patterns)
    # Based on real-world professional workflows, not theoretical patterns
    COMPANION_PATTERNS = {
        # ========================================
        # VIDEO FILES - Sony metadata + subtitles
        # ========================================
        "mp4": [
            # Sony video cameras: MP4 → M01.XML, M02.XML (metadata logs)
            r"^(.+)M01\.XML$", r"^(.+)M02\.XML$",
            # Subtitles
            r"^(.+)\.srt$", r"^(.+)\.vtt$", r"^(.+)\.ass$", r"^(.+)\.ssa$"
        ],
        "mov": [
            # Sony video cameras: MOV → M01.XML, M02.XML
            r"^(.+)M01\.XML$", r"^(.+)M02\.XML$",
            # Subtitles
            r"^(.+)\.srt$", r"^(.+)\.vtt$", r"^(.+)\.ass$", r"^(.+)\.ssa$"
        ],
        "mts": [r"^(.+)M01\.XML$", r"^(.+)M02\.XML$"],  # AVCHD format (Sony)
        "m2ts": [r"^(.+)M01\.XML$", r"^(.+)M02\.XML$"],  # AVCHD HD format

        # Other video formats with subtitle companions
        "mkv": [r"^(.+)\.srt$", r"^(.+)\.vtt$", r"^(.+)\.ass$", r"^(.+)\.ssa$"],
        "avi": [r"^(.+)\.srt$", r"^(.+)\.vtt$", r"^(.+)\.ass$", r"^(.+)\.ssa$"],
        "wmv": [r"^(.+)\.srt$", r"^(.+)\.vtt$", r"^(.+)\.ass$", r"^(.+)\.ssa$"],

        # ========================================
        # RAW IMAGE FILES - Metadata sidecars
        # ========================================
        # XMP sidecar files (universal post-processing metadata)
        # Created by: Lightroom, darktable, RawTherapee, digiKam, Capture One
        # Pattern: RAW file → .xmp or .XMP file

        # Canon RAW
        "cr2": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar metadata
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",        # JPEG preview (camera-generated or user-added)
            r"^(.+)\.jpeg$", r"^(.+)\.JPEG$",
            r"^(.+)\.vrd$"                          # VRD (Canon DPP recipe)
        ],
        "crw": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # Older Canon RAW
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",
        ],

        # Nikon RAW
        "nef": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar metadata
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",        # JPEG preview
            r"^(.+)\.jpeg$", r"^(.+)\.JPEG$",
            r"^(.+)\.nxd$"                          # NXD (NX Studio recipe)
        ],
        "nrw": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # Nikon mirrorless RAW
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",
        ],

        # Sony RAW
        "arw": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar metadata
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",        # JPEG preview
            r"^(.+)\.jpeg$", r"^(.+)\.JPEG$",
        ],
        "srf": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # Older Sony RAW
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",
        ],

        # Adobe DNG (RAW interchange format)
        "dng": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar metadata
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",        # JPEG preview
            r"^(.+)\.jpeg$", r"^(.+)\.JPEG$",
        ],

        # Olympus RAW
        "orf": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar metadata
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",        # JPEG preview
            r"^(.+)\.jpeg$", r"^(.+)\.JPEG$",
        ],

        # Panasonic RAW
        "rw2": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar metadata
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",        # JPEG preview
            r"^(.+)\.jpeg$", r"^(.+)\.JPEG$",
        ],

        # Pentax RAW
        "pef": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar metadata
            r"^(.+)\.jpg$", r"^(.+)\.JPG$",        # JPEG preview
            r"^(.+)\.jpeg$", r"^(.+)\.JPEG$",
        ],

        # ========================================
        # STANDARD IMAGES - XMP metadata + RAW companions
        # ========================================
        "jpg": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar
            # RAW companions (reverse relationship - JPG can be preview for RAW)
            r"^(.+)\.cr2$", r"^(.+)\.CR2$",        # Canon RAW
            r"^(.+)\.crw$", r"^(.+)\.CRW$",        # Older Canon RAW
            r"^(.+)\.nef$", r"^(.+)\.NEF$",        # Nikon RAW
            r"^(.+)\.nrw$", r"^(.+)\.NRW$",        # Nikon mirrorless RAW
            r"^(.+)\.arw$", r"^(.+)\.ARW$",        # Sony RAW
            r"^(.+)\.srf$", r"^(.+)\.SRF$",        # Older Sony RAW
            r"^(.+)\.dng$", r"^(.+)\.DNG$",        # Adobe DNG
            r"^(.+)\.orf$", r"^(.+)\.ORF$",        # Olympus RAW
            r"^(.+)\.rw2$", r"^(.+)\.RW2$",        # Panasonic RAW
            r"^(.+)\.pef$", r"^(.+)\.PEF$",        # Pentax RAW
        ],
        "jpeg": [
            r"^(.+)\.xmp$", r"^(.+)\.XMP$",        # XMP sidecar
            # RAW companions
            r"^(.+)\.cr2$", r"^(.+)\.CR2$",        # Canon RAW
            r"^(.+)\.crw$", r"^(.+)\.CRW$",
            r"^(.+)\.nef$", r"^(.+)\.NEF$",        # Nikon RAW
            r"^(.+)\.nrw$", r"^(.+)\.NRW$",
            r"^(.+)\.arw$", r"^(.+)\.ARW$",        # Sony RAW
            r"^(.+)\.srf$", r"^(.+)\.SRF$",
            r"^(.+)\.dng$", r"^(.+)\.DNG$",        # Adobe DNG
            r"^(.+)\.orf$", r"^(.+)\.ORF$",        # Olympus RAW
            r"^(.+)\.rw2$", r"^(.+)\.RW2$",        # Panasonic RAW
            r"^(.+)\.pef$", r"^(.+)\.PEF$",        # Pentax RAW
        ],
        "png": [r"^(.+)\.xmp$", r"^(.+)\.XMP$"],
        "tiff": [r"^(.+)\.xmp$", r"^(.+)\.XMP$"],
        "tif": [r"^(.+)\.xmp$", r"^(.+)\.XMP$"],
        "gif": [r"^(.+)\.xmp$", r"^(.+)\.XMP$"],
        "webp": [r"^(.+)\.xmp$", r"^(.+)\.XMP$"],

        # ========================================
        # DUAL RECORDING MODE (if camera supports it)
        # ========================================
        # Some professional cameras can record RAW + JPEG simultaneously
        # Both files have same base name with different extensions
        # This is NOT automatic but a camera setting
        # Note: These are treated as separate main files, not companions,
        # but may share XMP sidecars
    }

    # File extensions that are commonly companion files
    COMPANION_EXTENSIONS = {
        # Metadata formats
        "xmp", "xml", "vrd", "nxd",
        # Subtitles
        "srt", "vtt", "ass", "ssa", "sub",
        # LUT (color grading - usually shared, not per-file)
        "cube", "3dl", "lut",
        # Index/misc
        "idx"
    }

    @classmethod
    def find_companion_files(cls, main_file_path: str, folder_files: list[str]) -> list[str]:
        """
        Find companion files for a given main file.

        Args:
            main_file_path: Path to the main file
            folder_files: List of all files in the same folder

        Returns:
            List of companion file paths
        """
        main_file = Path(main_file_path)
        main_name = main_file.stem  # filename without extension
        main_ext = main_file.suffix[1:].lower()  # extension without dot

        companions = []

        # Get patterns for this file extension
        patterns = cls.COMPANION_PATTERNS.get(main_ext, [])

        for file_path in folder_files:
            if file_path == main_file_path:
                continue

            file_obj = Path(file_path)
            filename = file_obj.name

            # Check each pattern
            for pattern in patterns:
                match = re.match(pattern, filename, re.IGNORECASE)
                if match and match.group(1) == main_name:
                    companions.append(file_path)
                    logger.debug(f"[CompanionFiles] Found companion '{filename}' for '{main_file.name}'")
                    break

        return companions

    @classmethod
    def get_main_file_for_companion(cls, companion_path: str, folder_files: list[str]) -> str | None:
        """
        Find the main file that this companion file belongs to.

        Args:
            companion_path: Path to the companion file
            folder_files: List of all files in the same folder

        Returns:
            Path to main file, or None if not found
        """
        companion_file = Path(companion_path)
        companion_name = companion_file.name
        companion_ext = companion_file.suffix[1:].lower()

        # Check if this is actually a companion file
        if companion_ext not in cls.COMPANION_EXTENSIONS:
            return None

        # Try to find the main file
        for file_path in folder_files:
            if file_path == companion_path:
                continue

            file_obj = Path(file_path)
            file_ext = file_obj.suffix[1:].lower()

            # Check if this file could be the main file for our companion
            patterns = cls.COMPANION_PATTERNS.get(file_ext, [])

            for pattern in patterns:
                match = re.match(pattern, companion_name, re.IGNORECASE)
                if match and match.group(1) == file_obj.stem:
                    logger.debug(f"[CompanionFiles] Found main file '{file_obj.name}' for companion '{companion_name}'")
                    return file_path

        return None

    @classmethod
    def group_files_with_companions(cls, file_paths: list[str]) -> dict[str, dict[str, Any]]:
        """
        Group files with their companions.

        Args:
            file_paths: List of file paths to analyze

        Returns:
            Dictionary with file groups: {main_file: {"main": path, "companions": [paths], "type": "group/standalone"}}
        """
        file_groups: dict[str, dict[str, Any]] = {}
        processed_files: set[str] = set()

        # Get all files by folder for efficient processing
        folders: dict[str, list[str]] = {}
        for path in file_paths:
            folder = os.path.dirname(path)
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(path)

        # Process each file
        for file_path in file_paths:
            if file_path in processed_files:
                continue

            folder = os.path.dirname(file_path)
            folder_files = folders[folder]

            # Check if this is a companion file
            main_file = cls.get_main_file_for_companion(file_path, folder_files)

            if main_file:
                # This is a companion file - skip it for now
                processed_files.add(file_path)
                continue

            # This is a main file - find its companions
            companions = cls.find_companion_files(file_path, folder_files)

            file_groups[file_path] = {
                "main": file_path,
                "companions": companions,
                "type": "group" if companions else "standalone"
            }

            # Mark companions as processed
            for companion in companions:
                processed_files.add(companion)
            processed_files.add(file_path)

        logger.info(f"[CompanionFiles] Grouped {len(file_paths)} files into {len(file_groups)} groups")
        return file_groups

    @classmethod
    def is_companion_file(cls, file_path: str, folder_files: list[str]) -> bool:
        """
        Check if a file is a companion file.

        Args:
            file_path: Path to check
            folder_files: List of all files in the same folder

        Returns:
            True if this is a companion file
        """
        return cls.get_main_file_for_companion(file_path, folder_files) is not None

    @classmethod
    def should_include_companion_files(cls, main_extensions: set[str]) -> bool:
        """
        Check if companion files should be included based on the main file types being loaded.

        Args:
            main_extensions: Set of main file extensions being processed

        Returns:
            True if companion files are relevant for these file types
        """
        relevant_extensions = set(cls.COMPANION_PATTERNS.keys())
        return bool(main_extensions.intersection(relevant_extensions))

    @classmethod
    def get_companion_rename_pairs(cls, main_old_path: str, main_new_path: str, companions: list[str]) -> list[tuple[str, str]]:
        """
        Generate rename pairs for companion files when main file is renamed.

        Args:
            main_old_path: Original main file path
            main_new_path: New main file path
            companions: List of companion file paths

        Returns:
            List of (old_path, new_path) tuples for companions
        """
        if not companions:
            return []

        main_old = Path(main_old_path)
        main_new = Path(main_new_path)

        old_name = main_old.stem
        new_name = main_new.stem
        new_dir = main_new.parent

        rename_pairs = []

        for companion_path in companions:
            companion_file = Path(companion_path)
            companion_name = companion_file.name

            # Replace the old main filename with the new one in the companion name
            new_companion_name = companion_name.replace(old_name, new_name)
            new_companion_path = new_dir / new_companion_name

            rename_pairs.append((companion_path, str(new_companion_path)))

        logger.debug(f"[CompanionFiles] Generated {len(rename_pairs)} companion rename pairs")
        return rename_pairs

    @classmethod
    def extract_companion_metadata(cls, companion_path: str) -> dict[str, Any]:
        """
        Extract useful metadata from companion files (like Sony XML).

        Args:
            companion_path: Path to companion file

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}

        try:
            file_ext = Path(companion_path).suffix[1:].lower()

            if file_ext == "xml":
                metadata = cls._parse_sony_xml_metadata(companion_path)
            elif file_ext == "xmp":
                metadata = cls._parse_xmp_metadata(companion_path)

        except Exception as e:
            logger.warning(f"[CompanionFiles] Failed to parse companion metadata from {companion_path}: {e}")

        return metadata

    @classmethod
    def _parse_sony_xml_metadata(cls, xml_path: str) -> dict[str, Any]:
        """Parse Sony XML metadata file."""
        import xml.etree.ElementTree as ET

        metadata: dict[str, Any] = {}

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Check if this is actually a Sony XML file
            if root.tag != "NonRealTimeMeta":
                logger.debug(f"[CompanionFiles] XML file {xml_path} is not Sony format (root: {root.tag})")
                return metadata

            # This is a Sony XML file
            metadata["source"] = "sony_xml"

            # Extract useful information from Sony XML
            # Device info
            device_elem = root.find(".//{*}Device")
            if device_elem is not None:
                manufacturer = device_elem.get("manufacturer")
                if manufacturer:
                    metadata["device_manufacturer"] = manufacturer
                modelname = device_elem.get("modelName")
                if modelname:
                    metadata["device_model"] = modelname
                serialno = device_elem.get("serialNo")
                if serialno:
                    metadata["device_serial"] = serialno

            # Duration
            duration_elem = root.find(".//{*}Duration")
            if duration_elem is not None:
                duration_value = duration_elem.get("value")
                if duration_value:
                    metadata["duration_frames"] = duration_value

            # Creation date
            creation_elem = root.find(".//{*}CreationDate")
            if creation_elem is not None:
                creation_value = creation_elem.get("value")
                if creation_value:
                    metadata["creation_date"] = creation_value

            # Video format info
            video_format = root.find(".//{*}VideoFormat")
            if video_format is not None:
                # Video codec from format attributes
                video_codec = video_format.get("videoCodec")
                if video_codec:
                    metadata["video_codec"] = video_codec
                audio_codec = video_format.get("audioCodec")
                if audio_codec:
                    metadata["audio_codec"] = audio_codec

                # Frame info
                video_frame = video_format.find(".//{*}VideoFrame")
                if video_frame is not None:
                    for attr in ["videoCodec", "captureFps", "formatFps", "pixel"]:
                        attr_value = video_frame.get(attr)
                        if attr_value:
                            metadata[f"video_{attr.lower()}"] = attr_value
                            # Set video_resolution for pixel attribute
                            if attr == "pixel":
                                metadata["video_resolution"] = attr_value

                # Video layout (fallback for resolution)
                video_layout = video_format.find(".//{*}VideoLayout")
                if video_layout is not None:
                    for attr in ["pixel", "numOfVerticalLine", "aspectRatio"]:
                        attr_value = video_layout.get(attr)
                        if attr_value:
                            metadata[f"video_{attr.lower()}"] = attr_value
                            if attr == "pixel" and "video_resolution" not in metadata:
                                metadata["video_resolution"] = attr_value

            # Audio format info
            audio_format = root.find(".//{*}AudioFormat")
            if audio_format is not None:
                num_channels = audio_format.get("numOfChannel")
                if num_channels:
                    metadata["audio_channels"] = num_channels

        except Exception as e:
            logger.warning(f"[CompanionFiles] Error parsing Sony XML {xml_path}: {e}")

        return metadata

    @classmethod
    def _parse_xmp_metadata(cls, xmp_path: str) -> dict[str, Any]:
        """Parse XMP sidecar metadata file."""
        metadata = {"source": "xmp_sidecar"}

        try:
            with open(xmp_path, encoding='utf-8') as f:
                content = f.read()

            # Basic XMP parsing - look for common tags
            import re

            # Title
            title_match = re.search(r'dc:title.*?<rdf:li[^>]*>([^<]+)</rdf:li>', content, re.DOTALL)
            if title_match:
                metadata["title"] = title_match.group(1).strip()

            # Description
            desc_match = re.search(r'dc:description.*?<rdf:li[^>]*>([^<]+)</rdf:li>', content, re.DOTALL)
            if desc_match:
                metadata["description"] = desc_match.group(1).strip()

            # Keywords
            keywords_pattern = r'dc:subject.*?<rdf:Bag>(.*?)</rdf:Bag>'
            keywords_match = re.search(keywords_pattern, content, re.DOTALL)
            if keywords_match:
                keywords_content = keywords_match.group(1)
                keyword_items = re.findall(r'<rdf:li>([^<]+)</rdf:li>', keywords_content)
                if keyword_items:
                    metadata["keywords"] = ", ".join(keyword_items)

        except Exception as e:
            logger.warning(f"[CompanionFiles] Error parsing XMP {xmp_path}: {e}")

        return metadata
