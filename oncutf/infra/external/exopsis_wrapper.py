"""Module: exopsis_wrapper.py.

Author: Michael Economou
Date: 2025-05-23

Lightweight metadata wrapper using the Exopsis Python package.
Preserves the existing public API while delegating extraction to Exopsis.

Always uses frame_sample='first' — stops at the first video frame for
fast extraction (Sony XAVC and other multi-frame containers).
"""

from __future__ import annotations

import contextlib
import threading
import time
from pathlib import Path
from typing import Any, cast

from oncutf.utils.filesystem.path_normalizer import normalize_path
from oncutf.utils.logging.logger_factory import get_cached_logger

MetadataDict = dict[str, Any]

logger = get_cached_logger(__name__)


class ExopsisWrapper:
    """Metadata wrapper backed by Exopsis.

    Preserves the existing public API while delegating extraction to Exopsis.
    All extractions use frame_sample='first' — no fast/extended distinction.

    Attributes:
        lock: Thread lock for safe concurrent access.
        counter: Unique tag counter for operations.

    """

    def __init__(self) -> None:
        """Initialize the wrapper."""
        self.process = None
        self.lock = threading.Lock()
        self.counter = 0
        self._last_error: str | None = None
        self._last_health_check: float | None = None
        self._consecutive_errors: int = 0

    def __del__(self) -> None:
        """Destructor to ensure any resources are cleaned up."""
        with contextlib.suppress(Exception):
            self.close()

    @staticmethod
    def is_available() -> bool:
        """Check if Exopsis is available for metadata extraction."""
        import importlib.util

        try:
            if importlib.util.find_spec("exopsis") is None:
                logger.warning("Exopsis package not available")
                return False
        except Exception as e:
            logger.warning("Error checking Exopsis availability: %s", e)
            return False

        logger.debug("Exopsis version detected")
        return True

    def get_metadata(
        self,
        file_path: str,
        cancellation_check: Any | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Get metadata for a single file using Exopsis."""
        try:
            return self._extract(file_path, cancellation_check)
        except Exception:
            logger.exception("[ExopsisWrapper] Error getting metadata for %s", file_path)
            return {}

    def _extract(
        self,
        file_path: str,
        cancellation_check: Any | None = None,
    ) -> dict[str, Any]:
        """Extract metadata from a single file via Exopsis.

        MUST pass ExtractOptions(frame_sample='first') explicitly: the option's
        dataclass default is 'first', but that only applies when an options
        object is passed. Calling extract(path) with no options lets the Sony
        XAVC extractor fall back to frame_sample='all', which reads every RTMD
        timed-metadata frame (hundreds), scattered across the mdat box — turning
        an O(1) read into one that scales with file size (cold ~340ms vs ~6ms
        for a 134 MB clip). 'first' reads only the first frame for the
        per-capture values (fnumber, ISO, shutter).
        """
        from exopsis import ExtractOptions, extract

        file_path = normalize_path(file_path)
        if not Path(file_path).is_file():
            logger.warning("[ExopsisWrapper] File not found: %s", file_path)
            return {}

        try:
            if cancellation_check and cancellation_check():
                logger.info(
                    "[ExopsisWrapper] Extraction cancelled before start: %s", file_path
                )
                return {}

            result = extract(file_path, options=ExtractOptions(frame_sample="first"))
            raw_metadata = cast("dict[str, Any]", result.to_dict())
            metadata = self._normalize_exopsis_metadata(raw_metadata)
            self._consecutive_errors = 0
        except Exception as e:
            logger.exception(
                "[ExopsisWrapper] Error extracting metadata for %s", file_path
            )
            self._last_error = str(e)
            self._consecutive_errors += 1
            return {}
        else:
            return metadata

    @staticmethod
    def _normalize_exopsis_metadata(raw_metadata: dict[str, Any]) -> dict[str, Any]:
        """Normalize Exopsis metadata output for oncutf compatibility."""

        def normalize_value(value: Any) -> Any:
            if isinstance(value, dict):
                return {key: normalize_value(sub_value) for key, sub_value in value.items()}
            if isinstance(value, (list, tuple)):
                if not value:
                    return []
                if all(not isinstance(item, (dict, list, tuple)) for item in value):
                    return normalize_value(value[0])
                return [normalize_value(item) for item in value]
            return value

        # timed_metadata can contain thousands of per-frame entries — we only
        # need the first (capture-start values). Truncate before normalization
        # to avoid iterating all frames in pure Python.
        timed = raw_metadata.get("timed_metadata")
        if isinstance(timed, list) and len(timed) > 1:
            raw_metadata = {**raw_metadata, "timed_metadata": timed[:1]}

        normalized_metadata = {key: normalize_value(value) for key, value in raw_metadata.items()}
        ExopsisWrapper._add_exopsis_aliases(normalized_metadata)
        ExopsisWrapper._flatten_metadata_groups(normalized_metadata)
        ExopsisWrapper._inject_exopsis_version(normalized_metadata)
        return normalized_metadata

    @staticmethod
    def _add_exopsis_aliases(metadata: dict[str, Any]) -> None:
        """Add legacy EXIF-style aliases for common Exopsis fields."""
        capture = metadata.get("capture")
        capture_dt = capture.get("datetime_original") if isinstance(capture, dict) else None

        file_info = metadata.get("file_info")
        if isinstance(file_info, dict):
            created_dt = file_info.get("created_dt")
            modified_dt = file_info.get("modified_dt")

            # Capture date = when the shot was taken (capture.datetime_original).
            # Fall back to filesystem created_dt only when there is no capture
            # metadata. The rename "metadata date" module reads these keys, so
            # they must carry the real capture time — not the filesystem copy
            # time, which previously leaked in here.
            capture_date = capture_dt or created_dt
            if capture_date is not None:
                metadata.setdefault("DateTimeOriginal", capture_date)
                metadata.setdefault("CreateDate", capture_date)
                metadata.setdefault("creation_date", capture_date)
                metadata.setdefault("date", capture_date)

            # Filesystem timestamps — kept distinct and clearly labeled so they
            # are not confused with the capture date.
            if created_dt is not None:
                metadata.setdefault("FileCreateDate", created_dt)
            if modified_dt is not None:
                metadata.setdefault("FileModifyDate", modified_dt)
                metadata.setdefault("ModifyDate", modified_dt)

            path = file_info.get("path")
            if path is not None:
                metadata.setdefault("SourceFile", path)

            extension = file_info.get("extension")
            if extension is not None:
                metadata.setdefault("FileTypeExtension", extension)

            size_bytes = file_info.get("size_bytes")
            if size_bytes is not None:
                metadata.setdefault("FileSize", size_bytes)

            media_kind = file_info.get("media_kind")
            if media_kind is not None:
                metadata.setdefault("MediaType", media_kind)

        # Lens / focal length — surfaced when exopsis provides them (many bodies
        # report no lens data, e.g. manual/adapted glass, in which case these
        # stay absent rather than showing as empty rows).
        device = metadata.get("device")
        if isinstance(device, dict):
            lens_model = device.get("lens_model")
            if lens_model:
                metadata.setdefault("LensModel", lens_model)
                metadata.setdefault("Lens", lens_model)
        if isinstance(capture, dict):
            focal = capture.get("focal_length_mm")
            if focal:
                metadata.setdefault("FocalLength", focal)

        container = metadata.get("container")
        if isinstance(container, dict):
            format_name = container.get("format_name")
            if format_name is not None:
                metadata.setdefault("Format", format_name)
                metadata.setdefault("FileType", format_name)

            duration = container.get("duration_sec")
            if duration is not None:
                metadata.setdefault("Duration", duration)
                metadata.setdefault("MediaDuration", duration)

        video = metadata.get("video")
        if isinstance(video, dict):
            rotation_deg = video.get("rotation_deg")
            if rotation_deg is not None:
                metadata.setdefault("Rotation", rotation_deg)

            codec = video.get("codec")
            if codec is not None:
                metadata.setdefault("VideoCodec", codec)

            avg_bitrate_kbps = video.get("avg_bitrate_kbps")
            if avg_bitrate_kbps is not None:
                metadata.setdefault("AvgBitrate", avg_bitrate_kbps)
                metadata.setdefault("BitRate", avg_bitrate_kbps)

            width = video.get("width")
            if width is not None:
                metadata.setdefault("ImageWidth", width)

            height = video.get("height")
            if height is not None:
                metadata.setdefault("ImageHeight", height)

        audio = metadata.get("audio")
        if isinstance(audio, dict):
            sample_rate_hz = audio.get("sample_rate_hz")
            if sample_rate_hz is not None:
                metadata.setdefault("AudioSampleRate", sample_rate_hz)

            channels = audio.get("channels")
            if channels is not None:
                metadata.setdefault("AudioChannels", channels)
                metadata.setdefault("Channels", channels)

            codec = audio.get("codec")
            if codec is not None:
                metadata.setdefault("AudioCodec", codec)

    @staticmethod
    def _flatten_metadata_groups(metadata: dict[str, Any]) -> None:
        """Flatten top-level metadata groups into top-level keys for legacy compatibility."""
        for group_name in (
            "file_info",
            "container",
            "video",
            "audio",
            "device",
            "capture",
            "static_metadata",
        ):
            group = metadata.get(group_name)
            if not isinstance(group, dict):
                continue
            for key, value in group.items():
                metadata.setdefault(key, value)
            del metadata[group_name]

        # timed_metadata is per-frame sensor data — not useful for display.
        # hdr/ilst/id3v2/diagnostics/schema_version are known exopsis groups we
        # do not surface (redundant with flattened fields, or non-display data).
        # vendor_raw is intentionally NOT flattened: it duplicates the structured
        # fields (codec/camera/gamma/ltc/…) and adds container-internal date
        # variants (create_date/modify_date in a different timezone), which only
        # bloats the metadata tree with redundant rows.
        for known in (
            "timed_metadata",
            "vendor_raw",
            "hdr",
            "ilst",
            "id3v2",
            "diagnostics",
            "schema_version",
        ):
            metadata.pop(known, None)

        # Drop any *unexpected* remaining nested structures, with a warning so a
        # genuinely new exopsis group surfaces instead of being silently dropped.
        for key in [k for k, v in metadata.items() if isinstance(v, (dict, list))]:
            logger.warning("[Exopsis] Dropping unrecognized nested value: %s", key)
            del metadata[key]

        # Drop None-valued keys — exopsis emits many absent fields as None
        # (lens_model, gps_*, focal_length_mm, datetime_utc, …); showing them as
        # empty rows just clutters the metadata tree.
        for key in [k for k, v in metadata.items() if v is None]:
            del metadata[key]

    @staticmethod
    def _inject_exopsis_version(metadata: dict[str, Any]) -> None:
        """Inject the installed exopsis package version into the metadata dict."""
        try:
            from importlib.metadata import version

            exopsis_version = version("exopsis")
        except Exception:
            exopsis_version = "unknown"
        metadata.setdefault("Exopsis:ExopsisVersion", exopsis_version)

    def get_metadata_batch(
        self,
        file_paths: list[str],
        cancellation_check: Any | None = None,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Load metadata for multiple files using Exopsis."""
        if not file_paths:
            return []

        results: list[dict[str, Any]] = []
        for file_path in file_paths:
            if cancellation_check and cancellation_check():
                logger.info("[ExopsisWrapper] Batch extraction cancelled")
                results.extend([{} for _ in file_paths[len(results) :]])
                break
            metadata = self._extract(file_path, cancellation_check)
            results.append(metadata or {})
        return results

    def write_metadata(self, file_path: str, metadata_changes: dict[str, Any]) -> bool:
        """Write metadata changes to disk.

        Writing via Exopsis is not supported by the current wrapper implementation.
        """
        logger.warning("[ExopsisWrapper] Metadata writing is not implemented for Exopsis wrapper")
        return False

    def close(
        self,
        *,
        try_graceful: bool = False,
        graceful_wait_s: float = 0.2,
        terminate_wait_s: float = 0.2,
        kill_wait_s: float = 0.1,
    ) -> None:
        """Shut down the wrapper. No-op for Exopsis."""
        del try_graceful, graceful_wait_s, terminate_wait_s, kill_wait_s
        self.process = None

    @staticmethod
    def force_cleanup(*args: Any, **kwargs: Any) -> int:
        """No-op — Exopsis runs in-process; no external processes to clean up."""
        del args, kwargs
        logger.debug(
            "[ExopsisWrapper] force_cleanup called (no-op for Exopsis)",
            extra={"dev_only": True},
        )
        return 0

    def is_healthy(self) -> bool:
        """Check whether the wrapper is healthy."""
        return self._consecutive_errors <= 5

    def last_error(self) -> str | None:
        """Get the last error message."""
        return self._last_error

    def health_check(self) -> dict[str, Any]:
        """Perform a lightweight health check."""
        self._last_health_check = time.time()
        return {
            "healthy": self.is_healthy(),
            "process_alive": False,
            "process_status": "exopsis-python",
            "last_error": self._last_error,
            "consecutive_errors": self._consecutive_errors,
            "last_check": self._last_health_check,
        }

    @staticmethod
    def cleanup_orphaned_processes() -> None:
        """No-op — Exopsis runs in-process; no orphaned processes possible."""
        logger.debug(
            "[ExopsisWrapper] cleanup_orphaned_processes called (no-op for Exopsis)",
            extra={"dev_only": True},
        )


