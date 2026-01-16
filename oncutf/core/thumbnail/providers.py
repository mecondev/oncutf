"""Module: providers.py

Author: Michael Economou
Date: 2026-01-16

Abstract thumbnail providers for image and video file types.

Provides:
- ThumbnailProvider: Abstract base class for thumbnail generation
- ImageThumbnailProvider: Thumbnail generation for image files
- VideoThumbnailProvider: Frame extraction for video files (FFmpeg)

Usage:
    provider = ImageThumbnailProvider(max_size=256)
    pixmap = provider.generate(file_path)

Note: VideoThumbnailProvider requires FFmpeg installed on system.
"""

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from oncutf.core.pyqt_imports import QImage, QPixmap, Qt
from oncutf.utils.logging.logger_factory import get_cached_logger

logger = get_cached_logger(__name__)


class ThumbnailGenerationError(Exception):
    """Raised when thumbnail generation fails."""



class ThumbnailProvider(ABC):
    """Abstract base class for thumbnail generation.

    Subclasses must implement:
    - generate(file_path) -> QPixmap
    - supports(file_path) -> bool

    Attributes:
        max_size: Maximum thumbnail dimension (width/height)

    """

    def __init__(self, max_size: int = 256):
        """Initialize provider with size constraint.

        Args:
            max_size: Maximum thumbnail dimension in pixels

        """
        self.max_size = max_size

    @abstractmethod
    def generate(self, file_path: str) -> QPixmap:
        """Generate thumbnail for file.

        Args:
            file_path: Absolute file path

        Returns:
            QPixmap thumbnail scaled to max_size

        Raises:
            ThumbnailGenerationError: If generation fails

        """

    @abstractmethod
    def supports(self, file_path: str) -> bool:
        """Check if provider supports this file type.

        Args:
            file_path: Absolute file path

        Returns:
            True if provider can handle this file

        """


class ImageThumbnailProvider(ThumbnailProvider):
    """Thumbnail generation for image files using Qt image readers.

    Supports: JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC (if Qt supports).

    Thread-safe: Can be used from worker threads.

    """

    SUPPORTED_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".heic",
        ".heif",
    }

    def supports(self, file_path: str) -> bool:
        """Check if file is a supported image format.

        Args:
            file_path: Absolute file path

        Returns:
            True if extension is in SUPPORTED_EXTENSIONS

        """
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def generate(self, file_path: str) -> QPixmap:
        """Generate thumbnail for image file.

        Args:
            file_path: Absolute file path to image

        Returns:
            QPixmap scaled to max_size with aspect ratio preserved

        Raises:
            ThumbnailGenerationError: If image cannot be loaded

        """
        if not Path(file_path).exists():
            raise ThumbnailGenerationError(f"File not found: {file_path}")

        # Load image
        image = QImage(file_path)
        if image.isNull():
            raise ThumbnailGenerationError(f"Failed to load image: {file_path}")

        # Scale to thumbnail size (preserve aspect ratio)
        scaled_image = image.scaled(
            self.max_size,
            self.max_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        pixmap = QPixmap.fromImage(scaled_image)
        if pixmap.isNull():
            raise ThumbnailGenerationError(f"Failed to create pixmap: {file_path}")

        logger.debug(
            "[ImageThumbnailProvider] Generated thumbnail: %s (%dx%d)",
            Path(file_path).name,
            pixmap.width(),
            pixmap.height(),
        )

        return pixmap


class VideoThumbnailProvider(ThumbnailProvider):
    """Thumbnail generation for video files using FFmpeg.

    Extracts frame at optimal timestamp (default: 35% of duration).
    Falls back to alternative timestamps if frame is too dark/flat.

    Requires: FFmpeg installed and in system PATH.

    Thread-safe: Can be used from worker threads.

    """

    SUPPORTED_EXTENSIONS = {
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".3gp",
    }

    # Frame extraction heuristic
    DEFAULT_FRAME_RATIO = 0.35  # 35% of duration
    MIN_FRAME_TIME = 2.0  # Skip first 2 seconds (black leader)
    MAX_OFFSET_FROM_END = 2.0  # Stay 2 seconds before end

    # Quality thresholds for frame validation
    MIN_LUMA_THRESHOLD = 10  # Reject frames with avg brightness < 10 (0-255)
    MIN_CONTRAST_THRESHOLD = 5  # Reject frames with low contrast

    def __init__(self, max_size: int = 256, ffmpeg_path: str | None = None):
        """Initialize video thumbnail provider.

        Args:
            max_size: Maximum thumbnail dimension in pixels
            ffmpeg_path: Path to ffmpeg executable (None = auto-detect bundled/system)

        """
        super().__init__(max_size)

        # Auto-detect ffmpeg path if not provided
        if ffmpeg_path is None:
            from oncutf.utils.shared.external_tools import ToolName, get_tool_path

            try:
                self.ffmpeg_path = get_tool_path(ToolName.FFMPEG, prefer_bundled=True)
                logger.debug("Using ffmpeg at: %s", self.ffmpeg_path)
            except FileNotFoundError:
                logger.warning(
                    "FFmpeg not found. Video thumbnail generation will fail. "
                    "Install ffmpeg or place it in bin/ directory."
                )
                self.ffmpeg_path = "ffmpeg"  # Fallback (will fail gracefully)
        else:
            self.ffmpeg_path = ffmpeg_path

    def supports(self, file_path: str) -> bool:
        """Check if file is a supported video format.

        Args:
            file_path: Absolute file path

        Returns:
            True if extension is in SUPPORTED_EXTENSIONS

        """
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def generate(self, file_path: str) -> QPixmap:
        """Generate thumbnail for video file.

        Args:
            file_path: Absolute file path to video

        Returns:
            QPixmap scaled to max_size with aspect ratio preserved

        Raises:
            ThumbnailGenerationError: If frame extraction fails

        """
        if not Path(file_path).exists():
            raise ThumbnailGenerationError(f"File not found: {file_path}")

        # Get video duration
        duration = self._get_video_duration(file_path)
        if duration is None or duration <= 0:
            raise ThumbnailGenerationError(f"Failed to get video duration: {file_path}")

        # Try extraction at optimal timestamps
        frame_times = self._calculate_frame_times(duration)

        for frame_time in frame_times:
            try:
                pixmap = self._extract_frame(file_path, frame_time)

                # Validate frame quality (skip dark/flat frames)
                if self._is_valid_frame(pixmap):
                    logger.debug(
                        "[VideoThumbnailProvider] Generated thumbnail: %s at %.2fs",
                        Path(file_path).name,
                        frame_time,
                    )
                    return pixmap

                logger.debug(
                    "[VideoThumbnailProvider] Frame at %.2fs failed quality check, trying next",
                    frame_time,
                )

            except ThumbnailGenerationError as e:
                logger.debug(
                    "[VideoThumbnailProvider] Frame extraction failed at %.2fs: %s",
                    frame_time,
                    e,
                )
                continue

        raise ThumbnailGenerationError(f"All frame extraction attempts failed: {file_path}")

    def _get_video_duration(self, file_path: str) -> float | None:
        """Get video duration in seconds using FFprobe.

        Args:
            file_path: Absolute file path to video

        Returns:
            Duration in seconds, or None if probe fails

        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            duration = float(result.stdout.strip())
            logger.debug(
                "[VideoThumbnailProvider] Duration: %.2fs for %s",
                duration,
                Path(file_path).name,
            )
            return duration

        except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired) as e:
            logger.warning("[VideoThumbnailProvider] Failed to get duration: %s", e)
            return None

    def _calculate_frame_times(self, duration: float) -> list[float]:
        """Calculate optimal frame extraction timestamps with fallbacks.

        Args:
            duration: Video duration in seconds

        Returns:
            List of timestamps to try (in order of preference)

        """
        # Primary: 35% of duration (clamped)
        primary_time = min(
            max(duration * self.DEFAULT_FRAME_RATIO, self.MIN_FRAME_TIME),
            duration - self.MAX_OFFSET_FROM_END,
        )

        # Fallbacks: 15%, 50%, 70% (also clamped)
        fallback_times = [
            min(
                max(duration * ratio, self.MIN_FRAME_TIME),
                duration - self.MAX_OFFSET_FROM_END,
            )
            for ratio in [0.15, 0.50, 0.70]
        ]

        # Return unique times only
        all_times = [primary_time] + [t for t in fallback_times if t != primary_time]
        return all_times

    def _extract_frame(self, file_path: str, timestamp: float) -> QPixmap:
        """Extract single frame from video at timestamp using FFmpeg.

        Args:
            file_path: Absolute file path to video
            timestamp: Time position in seconds

        Returns:
            QPixmap of extracted frame

        Raises:
            ThumbnailGenerationError: If extraction fails

        """
        try:
            # Use FFmpeg to extract frame to stdout as PNG
            cmd = [
                self.ffmpeg_path,
                "-ss",
                str(timestamp),
                "-i",
                file_path,
                "-vframes",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "-",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=15,
                check=True,
            )

            # Load image from bytes
            image = QImage.fromData(result.stdout, "PNG")
            if image.isNull():
                raise ThumbnailGenerationError("Failed to decode frame PNG data")

            # Scale to thumbnail size
            scaled_image = image.scaled(
                self.max_size,
                self.max_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

            pixmap = QPixmap.fromImage(scaled_image)
            if pixmap.isNull():
                raise ThumbnailGenerationError("Failed to create pixmap from frame")

            return pixmap

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise ThumbnailGenerationError(f"FFmpeg extraction failed: {e}") from e

    def _is_valid_frame(self, pixmap: QPixmap) -> bool:
        """Check if frame meets quality thresholds (not too dark/flat).

        Args:
            pixmap: Frame to validate

        Returns:
            True if frame quality is acceptable

        """
        # Convert to QImage for pixel access
        image = pixmap.toImage()
        if image.isNull():
            return False

        # Sample center region (avoid letterboxing/pillarboxing)
        width = image.width()
        height = image.height()
        sample_size = min(width, height) // 4  # 25% of smaller dimension

        center_x = width // 2
        center_y = height // 2

        # Calculate average brightness and contrast
        luma_values = []
        for y in range(center_y - sample_size, center_y + sample_size, 4):
            for x in range(center_x - sample_size, center_x + sample_size, 4):
                if 0 <= x < width and 0 <= y < height:
                    pixel = image.pixel(x, y)
                    # Convert RGB to luma (ITU-R BT.601)
                    r = (pixel >> 16) & 0xFF
                    g = (pixel >> 8) & 0xFF
                    b = pixel & 0xFF
                    luma = 0.299 * r + 0.587 * g + 0.114 * b
                    luma_values.append(luma)

        if not luma_values:
            return False

        avg_luma = sum(luma_values) / len(luma_values)
        contrast = max(luma_values) - min(luma_values)

        # Check thresholds
        is_valid = (
            avg_luma >= self.MIN_LUMA_THRESHOLD and contrast >= self.MIN_CONTRAST_THRESHOLD
        )

        if not is_valid:
            logger.debug(
                "[VideoThumbnailProvider] Frame rejected: luma=%.1f, contrast=%.1f",
                avg_luma,
                contrast,
            )

        return is_valid
