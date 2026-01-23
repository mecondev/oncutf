"""Metadata key registry with undo/redo, semantic aliases, and persistence.

Provides centralized management of metadata key mappings with support for:
- Undo/redo with history snapshots
- Semantic aliases for cross-format field unification
- Export/import for backup and sharing
- Conflict resolution storage

Author: Michael Economou
Date: 2026-01-15
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


@dataclass
class KeyMapping:
    """Mapping between original and simplified/semantic key.

    Attributes:
        original: Original metadata key (e.g., "Audio Format Audio Rec Port Audio Codec")
        simplified: Simplified key (e.g., "Audio Codec")
        semantic: Optional semantic alias (e.g., "Audio Codec" unified across formats)
        priority: Priority for conflict resolution (higher = preferred)
        source: Source of mapping ("user", "semantic", "algorithmic")

    """

    original: str
    simplified: str
    semantic: str | None = None
    priority: int = 0
    source: str = "algorithmic"


@dataclass
class RegistrySnapshot:
    """Snapshot of registry state for undo/redo.

    Attributes:
        mappings: List of KeyMapping objects
        timestamp: Snapshot creation timestamp
        description: Human-readable description of change

    """

    mappings: list[KeyMapping]
    timestamp: float
    description: str = ""


class MetadataKeyRegistry:
    """Registry for metadata key mappings with undo/redo and semantic aliases.

    Manages the mapping between original metadata keys, simplified keys, and
    semantic aliases. Supports undo/redo, export/import, and semantic alias loading.

    Example:
        >>> registry = MetadataKeyRegistry()
        >>> registry.load_semantic_aliases()
        >>> registry.add_mapping("EXIF:DateTimeOriginal", "Date Original")
        >>> registry.resolve_key_with_fallback("Creation Date")
        'EXIF:DateTimeOriginal'

    Attributes:
        _mappings: Current key mappings dictionary (original -> KeyMapping)
        _semantic_index: Reverse index (semantic -> list of original keys)
        _history: List of registry snapshots for undo
        _future: List of registry snapshots for redo
        _max_history: Maximum number of snapshots to keep

    """

    # Default semantic aliases (Lightroom-style unified field names)
    DEFAULT_SEMANTIC_ALIASES: ClassVar[dict[str, list[str]]] = {
        "Creation Date": [
            "EXIF:DateTimeOriginal",
            "XMP:CreateDate",
            "IPTC:DateCreated",
            "QuickTime:CreateDate",
        ],
        "Modification Date": [
            "EXIF:ModifyDate",
            "XMP:ModifyDate",
            "File:FileModifyDate",
        ],
        "Camera Model": [
            "EXIF:Model",
            "XMP:Model",
            "MakerNotes:CameraModelName",
        ],
        "Camera Make": ["EXIF:Make", "XMP:Make"],
        "Image Width": [
            "EXIF:ImageWidth",
            "File:ImageWidth",
            "PNG:ImageWidth",
        ],
        "Image Height": [
            "EXIF:ImageHeight",
            "File:ImageHeight",
            "PNG:ImageHeight",
        ],
        "Duration": [
            "QuickTime:Duration",
            "Video:Duration",
            "Audio:Duration",
        ],
        "Frame Rate": [
            "QuickTime:VideoFrameRate",
            "Video:FrameRate",
            "H264:FrameRate",
        ],
        "Audio Codec": [
            "Audio Format Audio Rec Port Audio Codec",
            "QuickTime:AudioFormat",
            "Audio:Codec",
        ],
        "Video Codec": [
            "QuickTime:VideoCodec",
            "Video:Codec",
            "H264:CodecID",
        ],
        "GPS Latitude": [
            "EXIF:GPSLatitude",
            "XMP:GPSLatitude",
            "Composite:GPSLatitude",
        ],
        "GPS Longitude": [
            "EXIF:GPSLongitude",
            "XMP:GPSLongitude",
            "Composite:GPSLongitude",
        ],
        "Copyright": [
            "EXIF:Copyright",
            "XMP:Rights",
            "IPTC:CopyrightNotice",
        ],
        "Artist": [
            "EXIF:Artist",
            "XMP:Creator",
            "IPTC:By-line",
            "ID3:Artist",
        ],
        "Title": [
            "XMP:Title",
            "IPTC:ObjectName",
            "QuickTime:DisplayName",
            "ID3:Title",
        ],
        "ISO": ["EXIF:ISO", "XMP:ISO", "MakerNotes:ISO"],
        "Shutter Speed": [
            "EXIF:ShutterSpeed",
            "XMP:ShutterSpeed",
            "Composite:ShutterSpeed",
        ],
        "Aperture": [
            "EXIF:Aperture",
            "XMP:Aperture",
            "Composite:Aperture",
        ],
        "Focal Length": ["EXIF:FocalLength", "XMP:FocalLength"],
        "Sample Rate": [
            "Audio:SampleRate",
            "QuickTime:AudioSampleRate",
            "RIFF:SampleRate",
        ],
        "Bit Rate": [
            "Audio:BitRate",
            "Video:BitRate",
            "File:AvgBitrate",
        ],
        "Channels": [
            "Audio:Channels",
            "Audio Format Num Of Channel",
            "QuickTime:AudioChannels",
        ],
        "Color Space": [
            "EXIF:ColorSpace",
            "ICC_Profile:ColorSpaceData",
        ],
        "Orientation": ["EXIF:Orientation", "XMP:Orientation"],
    }

    def __init__(self, max_history: int = 50):
        """Initialize metadata key registry.

        Args:
            max_history: Maximum number of undo snapshots to keep

        """
        self._mappings: dict[str, KeyMapping] = {}
        self._semantic_index: dict[str, list[str]] = {}
        self._history: list[RegistrySnapshot] = []
        self._future: list[RegistrySnapshot] = []
        self._max_history = max_history

    def add_mapping(
        self,
        original: str,
        simplified: str,
        semantic: str | None = None,
        priority: int = 0,
        source: str = "user",
        create_snapshot: bool = True,
    ) -> None:
        """Add or update a key mapping.

        Args:
            original: Original metadata key
            simplified: Simplified key
            semantic: Optional semantic alias
            priority: Priority for conflict resolution
            source: Source of mapping ("user", "semantic", "algorithmic")
            create_snapshot: Whether to create undo snapshot

        """
        if create_snapshot:
            self._create_snapshot(f"Add mapping: {original} -> {simplified}")

        mapping = KeyMapping(
            original=original,
            simplified=simplified,
            semantic=semantic,
            priority=priority,
            source=source,
        )
        self._mappings[original] = mapping

        # Update semantic index
        if semantic:
            if semantic not in self._semantic_index:
                self._semantic_index[semantic] = []
            if original not in self._semantic_index[semantic]:
                self._semantic_index[semantic].append(original)

        logger.debug(
            "Added mapping: %s -> %s (semantic: %s, priority: %d)",
            original,
            simplified,
            semantic,
            priority,
        )

    def remove_mapping(
        self, original: str, create_snapshot: bool = True
    ) -> bool:
        """Remove a key mapping.

        Args:
            original: Original metadata key to remove
            create_snapshot: Whether to create undo snapshot

        Returns:
            True if mapping was removed, False if not found

        """
        if original not in self._mappings:
            return False

        if create_snapshot:
            self._create_snapshot(f"Remove mapping: {original}")

        mapping = self._mappings.pop(original)

        # Update semantic index
        if mapping.semantic and mapping.semantic in self._semantic_index:
            self._semantic_index[mapping.semantic] = [
                key
                for key in self._semantic_index[mapping.semantic]
                if key != original
            ]
            # Clean up empty semantic entries
            if not self._semantic_index[mapping.semantic]:
                del self._semantic_index[mapping.semantic]

        logger.debug("Removed mapping: %s", original)
        return True

    def get_mapping(self, original: str) -> KeyMapping | None:
        """Get mapping for an original key.

        Args:
            original: Original metadata key

        Returns:
            KeyMapping or None if not found

        """
        return self._mappings.get(original)

    def resolve_key_with_fallback(
        self, key: str, available_keys: list[str] | None = None
    ) -> str | None:
        """Resolve a key to an available original key with semantic fallback.

        Resolution order:
        1. If key is in available_keys, return it (exact match)
        2. If key is a semantic alias, find first available original
        3. Return None if no match found

        Args:
            key: Key to resolve (can be semantic alias or original key)
            available_keys: List of available original keys in file

        Returns:
            Resolved original key or None

        """
        # If no available keys provided, can't resolve
        if available_keys is None:
            return None

        # Exact match - key is already an original key
        if key in available_keys:
            return key

        # Semantic alias resolution
        if key in self._semantic_index:
            candidates = self._semantic_index[key]
            # Find first candidate that's available, sorted by priority
            mappings_with_priority = [
                (orig, self._mappings.get(orig, KeyMapping(orig, orig)).priority)
                for orig in candidates
                if orig in available_keys
            ]
            if mappings_with_priority:
                # Sort by priority descending
                mappings_with_priority.sort(key=lambda x: x[1], reverse=True)
                resolved = mappings_with_priority[0][0]
                logger.debug(
                    "Resolved semantic alias %s -> %s", key, resolved
                )
                return resolved

        logger.debug("Could not resolve key: %s", key)
        return None

    def get_semantic_name_for_key(self, original_key: str) -> str | None:
        """Get semantic name for an original key.

        Args:
            original_key: Original metadata key

        Returns:
            Semantic name or None if key has no semantic alias

        """
        # Check if this key has a mapping with semantic name
        mapping = self._mappings.get(original_key)
        if mapping and mapping.semantic:
            return mapping.semantic

        # Not in mappings, return None
        return None

    def load_semantic_aliases(
        self, custom_aliases: dict[str, list[str]] | None = None
    ) -> None:
        """Load semantic aliases (default + optional custom).

        Args:
            custom_aliases: Optional custom semantic aliases to merge

        """
        aliases = self.DEFAULT_SEMANTIC_ALIASES.copy()
        if custom_aliases:
            aliases.update(custom_aliases)

        # Clear existing semantic mappings before loading
        self._clear_semantic_mappings()

        for semantic_name, original_keys in aliases.items():
            for idx, original_key in enumerate(original_keys):
                # Higher priority for earlier entries
                priority = len(original_keys) - idx
                self.add_mapping(
                    original=original_key,
                    simplified=semantic_name,
                    semantic=semantic_name,
                    priority=priority,
                    source="semantic",
                    create_snapshot=False,
                )

        logger.info(
            "Loaded %d semantic aliases with %d mappings",
            len(aliases),
            sum(len(keys) for keys in aliases.values()),
        )

    def _clear_semantic_mappings(self) -> None:
        """Clear all semantic-source mappings."""
        to_remove = [
            key
            for key, mapping in self._mappings.items()
            if mapping.source == "semantic"
        ]
        for key in to_remove:
            self.remove_mapping(key, create_snapshot=False)

    def _create_snapshot(self, description: str) -> None:
        """Create a snapshot of current state for undo.

        Args:
            description: Description of the change

        """
        import time

        snapshot = RegistrySnapshot(
            mappings=list(self._mappings.values()),
            timestamp=time.time(),
            description=description,
        )
        self._history.append(snapshot)

        # Trim history if too long
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Clear future (redo stack) when new change is made
        self._future.clear()

        logger.debug("Created snapshot: %s", description)

    def undo(self) -> bool:
        """Undo last change.

        Returns:
            True if undo was successful, False if no history

        """
        if not self._history:
            logger.warning("No history to undo")
            return False

        # Save current state to future
        current = RegistrySnapshot(
            mappings=list(self._mappings.values()),
            timestamp=0,
            description="(redo point)",
        )
        self._future.append(current)

        # Restore previous state
        snapshot = self._history.pop()
        self._restore_snapshot(snapshot)

        logger.info("Undo: %s", snapshot.description)
        return True

    def redo(self) -> bool:
        """Redo last undone change.

        Returns:
            True if redo was successful, False if no future

        """
        if not self._future:
            logger.warning("No future to redo")
            return False

        # Save current state to history
        current = RegistrySnapshot(
            mappings=list(self._mappings.values()),
            timestamp=0,
            description="(undo point)",
        )
        self._history.append(current)

        # Restore future state
        snapshot = self._future.pop()
        self._restore_snapshot(snapshot)

        logger.info("Redo: %s", snapshot.description)
        return True

    def _restore_snapshot(self, snapshot: RegistrySnapshot) -> None:
        """Restore registry state from snapshot.

        Args:
            snapshot: Snapshot to restore

        """
        self._mappings.clear()
        self._semantic_index.clear()

        for mapping in snapshot.mappings:
            self.add_mapping(
                original=mapping.original,
                simplified=mapping.simplified,
                semantic=mapping.semantic,
                priority=mapping.priority,
                source=mapping.source,
                create_snapshot=False,
            )

    def export_to_dict(self) -> dict[str, Any]:
        """Export registry to dictionary for JSON serialization.

        Returns:
            Dictionary with mappings and metadata

        """
        return {
            "version": "1.0",
            "mappings": [
                {
                    "original": m.original,
                    "simplified": m.simplified,
                    "semantic": m.semantic,
                    "priority": m.priority,
                    "source": m.source,
                }
                for m in self._mappings.values()
            ],
        }

    def import_from_dict(
        self, data: dict[str, Any], merge: bool = False
    ) -> None:
        """Import registry from dictionary.

        Args:
            data: Dictionary with mappings
            merge: If True, merge with existing; if False, replace

        """
        if not merge:
            self._mappings.clear()
            self._semantic_index.clear()

        mappings_data = data.get("mappings", [])
        for m_data in mappings_data:
            self.add_mapping(
                original=m_data["original"],
                simplified=m_data["simplified"],
                semantic=m_data.get("semantic"),
                priority=m_data.get("priority", 0),
                source=m_data.get("source", "user"),
                create_snapshot=False,
            )

        logger.info(
            "Imported %d mappings (merge=%s)", len(mappings_data), merge
        )

    def export_to_file(self, filepath: Path | str) -> None:
        """Export registry to JSON file.

        Args:
            filepath: Path to output JSON file

        """
        filepath = Path(filepath)
        data = self.export_to_dict()

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Exported registry to %s", filepath)

    def import_from_file(
        self, filepath: Path | str, merge: bool = False
    ) -> None:
        """Import registry from JSON file.

        Args:
            filepath: Path to input JSON file
            merge: If True, merge with existing; if False, replace

        """
        filepath = Path(filepath)
        if not filepath.exists():
            logger.warning("Import file not found: %s", filepath)
            return

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        self.import_from_dict(data, merge=merge)
        logger.info("Imported registry from %s", filepath)

    def can_undo(self) -> bool:
        """Check if undo is available.

        Returns:
            True if there is history to undo

        """
        return len(self._history) > 0

    def can_redo(self) -> bool:
        """Check if redo is available.

        Returns:
            True if there is future to redo

        """
        return len(self._future) > 0

    def get_history_count(self) -> int:
        """Get number of undo steps available.

        Returns:
            Number of snapshots in history

        """
        return len(self._history)

    def get_mapping_count(self) -> int:
        """Get total number of mappings.

        Returns:
            Number of key mappings

        """
        return len(self._mappings)

    def get_semantic_count(self) -> int:
        """Get number of semantic aliases.

        Returns:
            Number of unique semantic aliases

        """
        return len(self._semantic_index)

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String representation with stats

        """
        return (
            f"MetadataKeyRegistry("
            f"{self.get_mapping_count()} mappings, "
            f"{self.get_semantic_count()} semantic aliases, "
            f"undo: {self.get_history_count()})"
        )
