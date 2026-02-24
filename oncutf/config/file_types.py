"""Module: oncutf.config.file_types.

Author: Michael Economou
Date: 2026-02-24

Unified file type registry -- single source of truth for all file extensions.

Every module that needs to classify files by extension should import from here
instead of maintaining its own extension list. The master dict maps each
extension (lowercase, **no** leading dot) to a :class:`FileTypeInfo` that
carries the category, thumbnail-preview flag, and filetype icon name.

Convenience sets are derived at import time so callers can do cheap
membership checks without rebuilding them on every use.

Usage examples::

    from oncutf.config.file_types import (
        PREVIEWABLE_EXTENSIONS,     # frozenset[str] -- no dot
        PREVIEWABLE_DOT_EXTENSIONS, # frozenset[str] -- with dot
        IMAGE_EXTENSIONS,           # frozenset[str] -- no dot (image+raw)
        get_filetype_icon,          # ext -> icon name
    )
"""

from __future__ import annotations

from typing import TypedDict

# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


class FileTypeInfo(TypedDict):
    """Metadata attached to each known file extension.

    Attributes:
        category:    Semantic group -- one of ``image``, ``raw``, ``video``,
                     ``audio``, ``document``, ``archive``, ``code``,
                     ``subtitle``, ``sidecar``, ``other``.
        previewable: ``True`` if a thumbnail can be generated for this type.
        icon:        Name of the filetype SVG icon (without path/extension)
                     used in the no-preview placeholder of the thumbnail
                     delegate. See ``resources/icons/filetypes/``.

    """

    category: str
    previewable: bool
    icon: str


# ---------------------------------------------------------------------------
# Master registry
# ---------------------------------------------------------------------------

FILE_TYPE_REGISTRY: dict[str, FileTypeInfo] = {
    # -- Raster images -------------------------------------------------------
    "jpg": {"category": "image", "previewable": True, "icon": "photo"},
    "jpeg": {"category": "image", "previewable": True, "icon": "photo"},
    "png": {"category": "image", "previewable": True, "icon": "photo"},
    "gif": {"category": "image", "previewable": True, "icon": "photo"},
    "bmp": {"category": "image", "previewable": True, "icon": "photo"},
    "tiff": {"category": "image", "previewable": True, "icon": "photo"},
    "tif": {"category": "image", "previewable": True, "icon": "photo"},
    "webp": {"category": "image", "previewable": True, "icon": "photo"},
    "heic": {"category": "image", "previewable": True, "icon": "photo"},
    "heif": {"category": "image", "previewable": True, "icon": "photo"},
    "svg": {"category": "image", "previewable": False, "icon": "photo"},
    # -- RAW camera formats --------------------------------------------------
    "raw": {"category": "raw", "previewable": True, "icon": "image"},
    "cr2": {"category": "raw", "previewable": True, "icon": "image"},
    "cr3": {"category": "raw", "previewable": True, "icon": "image"},
    "nef": {"category": "raw", "previewable": True, "icon": "image"},
    "arw": {"category": "raw", "previewable": True, "icon": "image"},
    "dng": {"category": "raw", "previewable": True, "icon": "image"},
    "orf": {"category": "raw", "previewable": True, "icon": "image"},
    "raf": {"category": "raw", "previewable": True, "icon": "image"},
    "rw2": {"category": "raw", "previewable": True, "icon": "image"},
    "pef": {"category": "raw", "previewable": True, "icon": "image"},
    "nrw": {"category": "raw", "previewable": True, "icon": "image"},
    "srw": {"category": "raw", "previewable": True, "icon": "image"},
    "dcr": {"category": "raw", "previewable": True, "icon": "image"},
    "fff": {"category": "raw", "previewable": True, "icon": "image"},
    # -- Video formats -------------------------------------------------------
    "mp4": {"category": "video", "previewable": True, "icon": "film"},
    "mov": {"category": "video", "previewable": True, "icon": "film"},
    "avi": {"category": "video", "previewable": True, "icon": "film"},
    "mkv": {"category": "video", "previewable": True, "icon": "film"},
    "wmv": {"category": "video", "previewable": True, "icon": "film"},
    "m4v": {"category": "video", "previewable": True, "icon": "film"},
    "flv": {"category": "video", "previewable": True, "icon": "film"},
    "webm": {"category": "video", "previewable": True, "icon": "film"},
    "m2ts": {"category": "video", "previewable": True, "icon": "film"},
    "ts": {"category": "video", "previewable": True, "icon": "film"},
    "mts": {"category": "video", "previewable": True, "icon": "film"},
    "3gp": {"category": "video", "previewable": True, "icon": "film"},
    "ogv": {"category": "video", "previewable": True, "icon": "film"},
    "mpg": {"category": "video", "previewable": True, "icon": "film"},
    "mpeg": {"category": "video", "previewable": True, "icon": "film"},
    "mxf": {"category": "video", "previewable": True, "icon": "film"},
    "vob": {"category": "video", "previewable": True, "icon": "film"},
    # -- Audio formats -------------------------------------------------------
    "mp3": {"category": "audio", "previewable": False, "icon": "audio_file"},
    "flac": {"category": "audio", "previewable": False, "icon": "audio_file"},
    "wav": {"category": "audio", "previewable": False, "icon": "audio_file"},
    "aac": {"category": "audio", "previewable": False, "icon": "audio_file"},
    "ogg": {"category": "audio", "previewable": False, "icon": "audio_file"},
    "wma": {"category": "audio", "previewable": False, "icon": "audio_file"},
    "m4a": {"category": "audio", "previewable": False, "icon": "audio_file"},
    "opus": {"category": "audio", "previewable": False, "icon": "audio_file"},
    "aiff": {"category": "audio", "previewable": False, "icon": "audio_file"},
    # -- Document formats ----------------------------------------------------
    "txt": {"category": "document", "previewable": False, "icon": "description"},
    "csv": {"category": "document", "previewable": False, "icon": "description"},
    "xml": {"category": "document", "previewable": False, "icon": "code"},
    "json": {"category": "document", "previewable": False, "icon": "code"},
    "rtf": {"category": "document", "previewable": False, "icon": "description"},
    "pdf": {"category": "document", "previewable": False, "icon": "description"},
    "doc": {"category": "document", "previewable": False, "icon": "description"},
    "docx": {"category": "document", "previewable": False, "icon": "description"},
    "xls": {"category": "document", "previewable": False, "icon": "description"},
    "xlsx": {"category": "document", "previewable": False, "icon": "description"},
    "ppt": {"category": "document", "previewable": False, "icon": "description"},
    "pptx": {"category": "document", "previewable": False, "icon": "description"},
    "odt": {"category": "document", "previewable": False, "icon": "description"},
    "ods": {"category": "document", "previewable": False, "icon": "description"},
    "odp": {"category": "document", "previewable": False, "icon": "description"},
    # -- Archive formats -----------------------------------------------------
    "zip": {"category": "archive", "previewable": False, "icon": "folder_zip"},
    "rar": {"category": "archive", "previewable": False, "icon": "folder_zip"},
    "7z": {"category": "archive", "previewable": False, "icon": "folder_zip"},
    "tar": {"category": "archive", "previewable": False, "icon": "folder_zip"},
    "gz": {"category": "archive", "previewable": False, "icon": "folder_zip"},
    "bz2": {"category": "archive", "previewable": False, "icon": "folder_zip"},
    # -- Code / script formats -----------------------------------------------
    "py": {"category": "code", "previewable": False, "icon": "code"},
    "js": {"category": "code", "previewable": False, "icon": "code"},
    "html": {"category": "code", "previewable": False, "icon": "code"},
    "css": {"category": "code", "previewable": False, "icon": "code"},
    "yaml": {"category": "code", "previewable": False, "icon": "code"},
    "yml": {"category": "code", "previewable": False, "icon": "code"},
    "sh": {"category": "code", "previewable": False, "icon": "code"},
    "bat": {"category": "code", "previewable": False, "icon": "code"},
    # -- Subtitle formats ----------------------------------------------------
    "srt": {"category": "subtitle", "previewable": False, "icon": "description"},
    "vtt": {"category": "subtitle", "previewable": False, "icon": "description"},
    "ass": {"category": "subtitle", "previewable": False, "icon": "description"},
    "ssa": {"category": "subtitle", "previewable": False, "icon": "description"},
    "sub": {"category": "subtitle", "previewable": False, "icon": "description"},
    "idx": {"category": "subtitle", "previewable": False, "icon": "description"},
    # -- Sidecar / companion formats -----------------------------------------
    "xmp": {"category": "sidecar", "previewable": False, "icon": "description"},
    "cube": {"category": "sidecar", "previewable": False, "icon": "description"},
    "3dl": {"category": "sidecar", "previewable": False, "icon": "description"},
    # -- Temporary / system --------------------------------------------------
    "tmp": {"category": "other", "previewable": False, "icon": "description"},
}


# ---------------------------------------------------------------------------
# Derived convenience sets (computed once at import time)
# ---------------------------------------------------------------------------


def _by_category(*categories: str) -> frozenset[str]:
    """Return extensions matching any of the given categories (no dot)."""
    return frozenset(
        ext for ext, info in FILE_TYPE_REGISTRY.items() if info["category"] in categories
    )


def _dotted(exts: frozenset[str]) -> frozenset[str]:
    """Add leading dot to each extension."""
    return frozenset(f".{e}" for e in exts)


# All extensions the application is allowed to manage (superset)
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(FILE_TYPE_REGISTRY)

# Thumbnail-previewable extensions
PREVIEWABLE_EXTENSIONS: frozenset[str] = frozenset(
    ext for ext, info in FILE_TYPE_REGISTRY.items() if info["previewable"]
)

# Category-based sets (no dot)
IMAGE_EXTENSIONS: frozenset[str] = _by_category("image")
RAW_EXTENSIONS: frozenset[str] = _by_category("raw")
VIDEO_EXTENSIONS: frozenset[str] = _by_category("video")
AUDIO_EXTENSIONS: frozenset[str] = _by_category("audio")
DOCUMENT_EXTENSIONS: frozenset[str] = _by_category("document")
ARCHIVE_EXTENSIONS: frozenset[str] = _by_category("archive")
SUBTITLE_EXTENSIONS: frozenset[str] = _by_category("subtitle")
SIDECAR_EXTENSIONS: frozenset[str] = _by_category("sidecar")

# Combined sets (no dot)
IMAGE_AND_RAW_EXTENSIONS: frozenset[str] = IMAGE_EXTENSIONS | RAW_EXTENSIONS
MEDIA_EXTENSIONS: frozenset[str] = IMAGE_AND_RAW_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Dotted variants (for consumers that use ".jpg"-style lookups)
PREVIEWABLE_DOT_EXTENSIONS: frozenset[str] = _dotted(PREVIEWABLE_EXTENSIONS)
IMAGE_DOT_EXTENSIONS: frozenset[str] = _dotted(IMAGE_EXTENSIONS)
RAW_DOT_EXTENSIONS: frozenset[str] = _dotted(RAW_EXTENSIONS)
VIDEO_DOT_EXTENSIONS: frozenset[str] = _dotted(VIDEO_EXTENSIONS)
AUDIO_DOT_EXTENSIONS: frozenset[str] = _dotted(AUDIO_EXTENSIONS)
DOCUMENT_DOT_EXTENSIONS: frozenset[str] = _dotted(DOCUMENT_EXTENSIONS)
IMAGE_AND_RAW_DOT_EXTENSIONS: frozenset[str] = _dotted(IMAGE_AND_RAW_EXTENSIONS)
MEDIA_DOT_EXTENSIONS: frozenset[str] = _dotted(MEDIA_EXTENSIONS)

# Filetype icon map (extension -> icon name, no dot)
FILETYPE_ICON_MAP: dict[str, str] = {ext: info["icon"] for ext, info in FILE_TYPE_REGISTRY.items()}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_filetype_icon(extension: str) -> str:
    """Return the filetype icon name for a given extension.

    Args:
        extension: Lowercase extension without leading dot

    Returns:
        Icon name (e.g. ``"photo"``, ``"film"``).  Falls back to
        ``"description"`` for unknown extensions.

    """
    return FILETYPE_ICON_MAP.get(extension, "description")


def get_category(extension: str) -> str:
    """Return the category for a given extension.

    Args:
        extension: Lowercase extension without leading dot

    Returns:
        Category string (e.g. ``"image"``, ``"video"``).
        Returns ``"unknown"`` for unregistered extensions.

    """
    info = FILE_TYPE_REGISTRY.get(extension)
    return info["category"] if info else "unknown"


def is_previewable(extension: str) -> bool:
    """Check whether an extension supports thumbnail preview.

    Args:
        extension: Lowercase extension without leading dot

    Returns:
        ``True`` if thumbnails can be generated for this type.

    """
    return extension in PREVIEWABLE_EXTENSIONS
