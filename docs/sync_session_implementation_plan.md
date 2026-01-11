# oncutf Sync Session Implementation Plan

**Author:** Michael Economou  
**Date:** 2026-01-11  
**Status:** Draft  
**Target:** MVP -> v1 -> v2  

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Sync Pipeline Design](#2-sync-pipeline-design)
3. [Timeline UI Plan](#3-timeline-ui-plan)
4. [Manual Anchor UI and Logic](#4-manual-anchor-ui-and-logic)
5. [Export Plan (MVP)](#5-export-plan-mvp)
6. [Testing Plan](#6-testing-plan)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Do Not Do Now List](#8-do-not-do-now-list)

---

## 1. Architecture Overview

### 1.1 Package/Module Layout

All sync-related code will reside under `oncutf/sync/` with clear separation of concerns:

```
oncutf/
  sync/
    __init__.py                     # Public API exports (brand: oncut)
    
    # --- Domain Models ---
    domain/
      __init__.py
      clip.py                       # Clip dataclass
      device.py                     # Device dataclass
      track.py                      # Track dataclass
      session_segment.py            # SessionSegment (cluster) dataclass
      match_edge.py                 # MatchEdge (sync relationship) dataclass
      sync_result.py                # SyncResult container dataclass
      anchor.py                     # Anchor definitions (clip-to-clip, explicit)
      timeline_position.py          # TimelinePosition helper dataclass
    
    # --- Core Sync Engine ---
    engine/
      __init__.py
      sync_orchestrator.py          # Main orchestration (pipeline controller)
      ingest_service.py             # Metadata ingestion and normalization
      cluster_service.py            # Time-based clustering
      alignment_service.py          # Rough alignment from metadata
      audio_matcher.py              # Audio-based sync refinement
      confidence_scorer.py          # Confidence scoring and thresholds
      timeline_builder.py           # Builds final timeline from matches
      device_identifier.py          # Device identity from path/folder
    
    # --- Audio Processing (Plugin-Ready) ---
    audio/
      __init__.py
      audio_processor.py            # Abstract base / interface
      python_audio_processor.py     # Pure Python MVP implementation
      audio_feature_extractor.py    # Transient/fingerprint extraction
      audio_normalizer.py           # Level normalization, downmix
      audio_resampler.py            # Resampling to common rate
      candidate_window.py           # Candidate window generation
    
    # --- Exporters ---
    exporters/
      __init__.py
      base_exporter.py              # Abstract base class
      aaf_exporter.py               # Avid AAF linked export (MVP)
      report_exporter.py            # JSON/CSV report export
      # Future: fcpxml_exporter.py, resolve_exporter.py
    
    # --- UI Components ---
    ui/
      __init__.py
      sync_session_widget.py        # Main container widget
      timeline_viewport.py          # Timeline graphics view (QGraphicsView)
      timeline_scene.py             # Timeline graphics scene
      timeline_track_item.py        # Track lane graphics item
      timeline_clip_item.py         # Clip rectangle graphics item
      timeline_ruler.py             # Time ruler widget
      sync_toolbar.py               # Sync action toolbar
      anchor_dialog.py              # Manual anchor input dialog
      sync_settings_dialog.py       # Sync settings/preferences
      unknown_placement_menu.py     # Placement mode selector
    
    # --- Controller ---
    controller/
      __init__.py
      sync_controller.py            # Main sync controller (UI-agnostic)
      anchor_controller.py          # Anchor management controller
      export_controller.py          # Export workflow controller
    
    # --- Utilities ---
    utils/
      __init__.py
      timecode_parser.py            # HH:MM:SS:FF parsing
      time_converter.py             # Seconds <-> frames conversion
      filename_analyzer.py          # Sequence anomaly detection
```

### 1.2 Data Model Definitions

#### 1.2.1 Clip (oncutf/sync/domain/clip.py)

```python
@dataclass
class Clip:
    """Represents a single media clip in the sync session."""
    
    # Identity
    clip_id: str                          # Unique identifier (UUID)
    file_path: str                        # Absolute filesystem path
    filename: str                         # Basename for display
    
    # Temporal metadata (best-effort)
    metadata_start_time: datetime | None  # Wall-clock start from metadata
    duration_seconds: float               # Clip duration in seconds
    duration_frames: int                  # Duration in project frames
    
    # Device association
    device_id: str | None                 # Device identifier
    device_name: str                      # Human-readable device name
    
    # Folder color (from oncutf color flags)
    color_hex: str                        # Hex color string or "none"
    
    # Media properties
    media_type: str                       # "video" or "audio"
    sample_rate: int | None               # Audio sample rate (if audio)
    frame_rate: float | None              # Video frame rate
    has_audio: bool                       # Whether clip has audio track
    
    # Sync state
    sync_status: str                      # "unprocessed", "matched", "unmatched"
    match_confidence: float               # 0.0 to 1.0
    timeline_position: float | None       # Position in timeline (seconds)
    track_index: int | None               # Assigned track index
    
    # Sequence info
    sequence_number: int | None           # Extracted from filename if present
    sequence_anomaly: bool                # True if out-of-order detected
```

#### 1.2.2 Device (oncutf/sync/domain/device.py)

```python
@dataclass
class Device:
    """Represents a recording device (camera or audio recorder)."""
    
    device_id: str                        # Unique identifier
    device_name: str                      # Human-readable name
    device_type: str                      # "camera" or "recorder"
    
    # Source identification
    source_folder: str                    # Primary folder path
    color_hex: str                        # Folder color from oncutf
    
    # Time offset
    time_offset_seconds: float            # Offset from master reference
    offset_confidence: float              # Confidence in offset
    offset_source: str                    # "metadata", "audio", "anchor"
    
    # Associated clips
    clip_ids: list[str]                   # List of clip IDs for this device
    
    # Track assignment
    assigned_track: int | None            # Track index in timeline
```

#### 1.2.3 Track (oncutf/sync/domain/track.py)

```python
@dataclass
class Track:
    """Represents a track lane in the timeline."""
    
    track_id: str                         # Unique identifier
    track_index: int                      # Zero-based track index
    track_name: str                       # Display name (e.g., "V1", "A1")
    track_type: str                       # "video" or "audio"
    
    # Device association
    device_id: str | None                 # Associated device (if any)
    color_hex: str                        # Track color (from device)
    
    # Clips on track
    clip_ids: list[str]                   # Ordered list of clips
    
    # Layout hints
    is_overflow_track: bool               # True for unmatched overflow tracks
```

#### 1.2.4 SessionSegment (oncutf/sync/domain/session_segment.py)

```python
@dataclass
class SessionSegment:
    """Represents a cluster of related clips (e.g., ceremony, reception)."""
    
    segment_id: str                       # Unique identifier
    segment_name: str                     # User-facing name
    
    # Temporal bounds (in timeline seconds)
    start_time: float                     # Segment start
    end_time: float                       # Segment end
    
    # Contained clips
    clip_ids: list[str]                   # Clips in this segment
    
    # Clustering metadata
    cluster_reason: str                   # "time_overlap", "audio_link", "manual"
    has_audio_recorder: bool              # Whether segment has recorder
    master_device_id: str | None          # Reference device for segment
```

#### 1.2.5 MatchEdge (oncutf/sync/domain/match_edge.py)

```python
@dataclass
class MatchEdge:
    """Represents a sync relationship between two clips."""
    
    edge_id: str                          # Unique identifier
    clip_a_id: str                        # First clip
    clip_b_id: str                        # Second clip
    
    # Match details
    match_type: str                       # "audio", "anchor", "metadata"
    confidence: float                     # 0.0 to 1.0
    
    # Offset
    offset_seconds: float                 # B relative to A (positive = B is later)
    offset_samples: int | None            # Sample-accurate offset (if audio)
    
    # Quality indicators
    snr_estimate: float | None            # Signal-to-noise ratio
    correlation_peak: float | None        # Cross-correlation peak value
    ambiguity_flag: bool                  # True if multiple peaks detected
    
    # Reason codes for diagnostics
    reason_codes: list[str]               # e.g., ["low_audio", "noisy_env"]
```

#### 1.2.6 SyncResult (oncutf/sync/domain/sync_result.py)

```python
@dataclass
class SyncResult:
    """Container for complete sync session results."""
    
    session_id: str                       # Unique session identifier
    created_at: datetime                  # Session creation timestamp
    project_fps: float                    # Project timebase
    
    # Domain objects
    clips: dict[str, Clip]                # clip_id -> Clip
    devices: dict[str, Device]            # device_id -> Device
    tracks: list[Track]                   # Ordered track list
    segments: list[SessionSegment]        # Segment clusters
    match_edges: list[MatchEdge]          # All sync relationships
    
    # Timeline bounds
    timeline_start: float                 # Earliest position (seconds)
    timeline_end: float                   # Latest position (seconds)
    
    # Statistics
    total_clips: int
    matched_clips: int
    unmatched_clips: int
    average_confidence: float
    
    # Diagnostics
    warnings: list[str]                   # Warning messages
    anomalies: list[str]                  # Detected anomalies
```

### 1.3 Integration Points with Existing oncutf Components

| oncutf Component | Integration Point | Usage |
|------------------|-------------------|-------|
| File Table Selection | `table_manager.get_selected_files()` | Get user-selected FileItem list |
| Metadata Cache | `unified_metadata_manager` | Retrieve cached file metadata |
| Folder Color Flags | `FileItem.color` attribute | Timeline rectangle colors |
| TooltipHelper | `TooltipHelper.setup_tooltip()` | Hover tooltips on timeline clips |
| TimerManager | `get_timer_manager().schedule()` | Delayed UI updates, debouncing |
| ApplicationContext | `get_application_context()` | Global state access |
| Database Manager | `get_database_manager()` | Persist sync session data |
| Logger Factory | `get_cached_logger(__name__)` | Consistent logging |
| CustomMessageDialog | `CustomMessageDialog` | User notifications |
| Wait Cursor | `wait_cursor()` context manager | Long operations |

### 1.4 Component Diagram (Simplified)

```
+-------------------------------------------------------------------+
|                         MainWindow                                 |
|   +---------------------+    +--------------------------------+   |
|   | FileTableView       |    | SyncSessionWidget              |   |
|   | (selection source)  |--->| +----------------------------+ |   |
|   +---------------------+    | | TimelineViewport           | |   |
|                              | | (QGraphicsView)            | |   |
|                              | +----------------------------+ |   |
|                              | | SyncToolbar | AnchorDialog | |   |
|                              +--------------------------------+   |
+-------------------------------------------------------------------+
           |                              |
           v                              v
+-------------------+        +-------------------------+
| SyncController    |<------>| SyncOrchestrator        |
| (UI-agnostic)     |        | (pipeline coordinator)  |
+-------------------+        +-------------------------+
                                        |
          +-----------------------------+-----------------------------+
          |              |              |              |              |
          v              v              v              v              v
   +------------+ +------------+ +------------+ +------------+ +------------+
   | Ingest     | | Cluster    | | Alignment  | | Audio      | | Timeline   |
   | Service    | | Service    | | Service    | | Matcher    | | Builder    |
   +------------+ +------------+ +------------+ +------------+ +------------+
                                                      |
                                                      v
                                        +-------------------------+
                                        | AudioProcessor          |
                                        | (plugin-ready interface)|
                                        +-------------------------+
                                                      |
                                                      v
                                        +-------------------------+
                                        | PythonAudioProcessor    |
                                        | (MVP implementation)    |
                                        +-------------------------+

Export Layer:
+-------------------+
| AAFExporter       | --> Linked AAF (absolute paths)
| ReportExporter    | --> JSON/CSV reports
+-------------------+
```

---

## 2. Sync Pipeline Design

### 2.1 Pipeline Overview

The sync pipeline consists of the following sequential stages:

```
INGEST --> NORMALIZE --> CLUSTER --> ROUGH_ALIGN --> AUDIO_REFINE --> SCORE --> BUILD --> EXPORT
```

### 2.2 Stage 1: Ingest

**Module:** `oncutf/sync/engine/ingest_service.py`

**Purpose:** Extract and normalize metadata from selected files.

**Inputs:**
- List of `FileItem` objects from table selection

**Outputs:**
- List of `Clip` domain objects with populated metadata

**Steps:**

1. For each selected file:
   - Create `Clip` instance with basic file info
   - Extract duration from cached metadata or re-read via UnifiedMetadataManager
   - Extract best-effort wall-clock start time:
     - Primary: `CreateDate` or `DateTimeOriginal` from EXIF
     - Fallback: File modification time
   - Extract media properties (sample rate, frame rate, has_audio)
   - Extract sequence number from filename using regex patterns
   - Copy folder color from `FileItem.color`

2. Validate all clips have valid duration (reject zero-duration files)

3. Log ingest summary with clip count and any warnings

**Code Sketch:**

```python
class IngestService:
    """Ingests file metadata and creates Clip domain objects."""
    
    def __init__(self, metadata_manager: UnifiedMetadataManager) -> None:
        self._metadata_manager = metadata_manager
        self._logger = get_cached_logger(__name__)
    
    def ingest_files(self, file_items: list[FileItem]) -> list[Clip]:
        """Convert FileItems to Clip domain objects."""
        clips: list[Clip] = []
        for item in file_items:
            clip = self._create_clip_from_item(item)
            if clip.duration_seconds > 0:
                clips.append(clip)
            else:
                self._logger.warning("Skipped zero-duration: %s", item.filename)
        return clips
```

### 2.3 Stage 2: Normalize

**Module:** `oncutf/sync/engine/ingest_service.py` (part of ingest)

**Purpose:** Normalize extracted timestamps to a common reference.

**Approach:**
- Convert all timestamps to UTC if timezone info available
- If no timezone, assume local time consistently
- Compute relative offsets from earliest timestamp
- Handle missing timestamps by flagging clips as "time_unknown"

**Outputs:**
- Clips with normalized `metadata_start_time` (or None if unavailable)

### 2.4 Stage 3: Cluster

**Module:** `oncutf/sync/engine/cluster_service.py`

**Purpose:** Group clips into logical segments based on time proximity.

**Algorithm:**

1. Sort all clips by `metadata_start_time` (clips with None go to separate pool)

2. Initialize first cluster with first clip

3. For each subsequent clip:
   - If clip overlaps or is within CLUSTER_GAP_THRESHOLD (e.g., 5 minutes) of any clip in current cluster, add to cluster
   - Otherwise, start new cluster

4. For clips without timestamps:
   - Use filename sequence analysis to suggest cluster assignment
   - Or place in "unknown_cluster" for manual resolution

5. Assign master device per cluster:
   - If audio recorder present, recorder is master
   - Otherwise, camera with most clips is master

**Outputs:**
- List of `SessionSegment` objects

**Code Sketch:**

```python
class ClusterService:
    """Groups clips into temporal segments."""
    
    CLUSTER_GAP_THRESHOLD_SECONDS = 300  # 5 minutes
    
    def cluster_clips(self, clips: list[Clip]) -> list[SessionSegment]:
        """Create segments from time-based clustering."""
        # Sort by timestamp, handling None values
        timed_clips = [c for c in clips if c.metadata_start_time]
        untimed_clips = [c for c in clips if not c.metadata_start_time]
        
        timed_clips.sort(key=lambda c: c.metadata_start_time)
        segments = self._build_segments(timed_clips)
        
        # Handle untimed clips via filename heuristics
        self._assign_untimed_clips(untimed_clips, segments)
        return segments
```

### 2.5 Stage 4: Rough Alignment

**Module:** `oncutf/sync/engine/alignment_service.py`

**Purpose:** Establish initial device offsets from metadata timestamps.

**Algorithm:**

1. For each segment:
   - Identify master device (recorder or primary camera)
   - For each other device in segment:
     - Find overlapping time windows between devices
     - Compute rough offset as difference in start times
     - Store as `Device.time_offset_seconds` with `offset_source="metadata"`

2. For clips without metadata time:
   - Use filename sequence to estimate position relative to adjacent clips

**Outputs:**
- Devices with rough `time_offset_seconds` populated

### 2.6 Stage 5: Audio Refine

**Module:** `oncutf/sync/engine/audio_matcher.py`

**Purpose:** Refine offsets using audio cross-correlation.

**Candidate Window Strategy (CRITICAL - No Brute Force):**

1. Use rough alignment to define search windows:
   - Center: rough offset from metadata
   - Width: +/- CANDIDATE_WINDOW_HALF (e.g., +/- 30 seconds)

2. For long clips, use segmented approach:
   - Divide clips into 30-second chunks
   - Match chunk-by-chunk within candidate windows
   - Aggregate results with drift detection

3. Prioritize transient-rich sections:
   - Detect audio transients (claps, loud sounds)
   - Weight transient regions higher in matching

**Audio Preprocessing:**

```python
class AudioProcessor(ABC):
    """Abstract interface for audio processing (plugin-ready)."""
    
    @abstractmethod
    def load_audio(self, file_path: str) -> np.ndarray:
        """Load audio file and return mono float32 array."""
        pass
    
    @abstractmethod
    def extract_features(self, audio: np.ndarray) -> np.ndarray:
        """Extract matching features from audio."""
        pass
    
    @abstractmethod
    def cross_correlate(
        self, 
        features_a: np.ndarray, 
        features_b: np.ndarray,
        window_start: int,
        window_end: int
    ) -> tuple[int, float]:
        """Find best offset within window. Returns (offset_samples, confidence)."""
        pass
```

**Python MVP Implementation:**

```python
class PythonAudioProcessor(AudioProcessor):
    """Pure Python audio processor for MVP."""
    
    INTERNAL_SAMPLE_RATE = 8000  # Downsample for speed
    
    def load_audio(self, file_path: str) -> np.ndarray:
        """Load and preprocess audio."""
        # Use soundfile or similar library
        audio, sr = sf.read(file_path, dtype='float32')
        audio = self._to_mono(audio)
        audio = self._resample(audio, sr, self.INTERNAL_SAMPLE_RATE)
        audio = self._normalize(audio)
        return audio
```

**Matching Algorithm:**

1. Load audio from both clips (only sections within candidate window)
2. Extract features (energy envelope or chromagram)
3. Compute cross-correlation using FFT-based approach
4. Find peak correlation and verify:
   - Peak must exceed MIN_CORRELATION_THRESHOLD
   - Peak must be unambiguous (no close secondary peaks)
5. Return offset in samples and confidence score

**Handling Difficult Cases:**

| Scenario | Handling Strategy |
|----------|-------------------|
| Low scratch audio | Use energy envelope, accept lower confidence |
| Loud music/noisy | Band-pass filter to speech frequencies |
| Very quiet environment | Flag as low-confidence, suggest manual anchor |
| Long drift | Phase 2 feature (detect and segment) |

### 2.7 Stage 6: Confidence Scoring

**Module:** `oncutf/sync/engine/confidence_scorer.py`

**Purpose:** Assign confidence scores and apply thresholds.

**Scoring Factors:**

| Factor | Weight | Description |
|--------|--------|-------------|
| Correlation peak | 0.4 | Raw correlation value |
| Peak sharpness | 0.2 | Ratio of peak to second-highest |
| Audio quality | 0.2 | SNR estimate |
| Metadata agreement | 0.2 | How close audio offset matches metadata |

**Confidence Thresholds (User-Configurable via "Strictness" Setting):**

| Strictness | Min Confidence | Effect |
|------------|----------------|--------|
| Low | 0.3 | Accept more matches, higher false positive risk |
| Medium (default) | 0.5 | Balanced |
| High | 0.7 | Stricter, more clips may be unmatched |

**Outputs:**
- `MatchEdge` objects with confidence scores
- Clips marked as "matched" or "unmatched"

### 2.8 Stage 7: Build Timeline

**Module:** `oncutf/sync/engine/timeline_builder.py`

**Purpose:** Construct final timeline structure from matches.

**Algorithm:**

1. Create tracks:
   - One video track per camera device
   - One audio track per recorder device
   - Extra overflow tracks for unmatched clips (if using near-gap mode)

2. Place matched clips:
   - Use device offsets to compute timeline position
   - Respect segment boundaries

3. Place unmatched clips based on mode:

   **Mode 1: Near-Gap Stack (Default)**
   - Analyze filename sequence within device
   - Find logical position based on surrounding matched clips
   - Place on overflow track at estimated position
   - Mark with UNMATCHED status

   **Mode 2: Tail Bin**
   - Append all unmatched clips at timeline end
   - Maintain device grouping
   - Mark with UNMATCHED status

4. Compute timeline bounds (start, end)

5. Generate SyncResult container

**Code Sketch:**

```python
class TimelineBuilder:
    """Builds timeline structure from sync matches."""
    
    def build_timeline(
        self,
        clips: list[Clip],
        devices: list[Device],
        edges: list[MatchEdge],
        segments: list[SessionSegment],
        placement_mode: str,  # "near_gap" or "tail_bin"
    ) -> SyncResult:
        """Construct complete timeline."""
        tracks = self._create_tracks(devices)
        self._place_matched_clips(clips, devices, tracks)
        self._place_unmatched_clips(clips, tracks, placement_mode)
        return self._build_result(clips, devices, tracks, segments, edges)
```

### 2.9 Stage 8: Export

**Module:** `oncutf/sync/exporters/aaf_exporter.py`

**Purpose:** Export to Avid AAF format.

(Detailed in Section 5)

---

## 3. Timeline UI Plan

### 3.1 Widget/Class Structure

```
SyncSessionWidget (QWidget)
  |
  +-- QVBoxLayout
        |
        +-- SyncToolbar (QToolBar)
        |     - Run Sync button
        |     - Export button
        |     - Settings button
        |     - Zoom controls
        |     - Placement mode dropdown
        |
        +-- QSplitter (vertical)
              |
              +-- TimelineViewport (QGraphicsView)
              |     - Contains TimelineScene
              |     - Handles zoom/scroll
              |
              +-- TimelineRuler (QWidget)
                    - Time scale display
                    - Playhead position (visual only)
```

### 3.2 Painting Strategy: QGraphicsView

**Rationale:**

QGraphicsView is chosen over custom QWidget painting for several reasons:

1. **Built-in transformation support**: Zoom and scroll are handled natively via `scale()` and `translate()` transforms

2. **Efficient large-scene handling**: QGraphicsScene uses spatial indexing for efficient rendering of visible items only

3. **Item-level interaction**: Each clip is a QGraphicsItem with its own mouse events, making selection and tooltips straightforward

4. **Precedent in oncutf**: The node editor (`oncutf/ui/widgets/node_editor/`) already uses QGraphicsView successfully

5. **GPU acceleration**: QGraphicsView can leverage OpenGL viewport for better performance

**Scene Structure:**

```
TimelineScene (QGraphicsScene)
  |
  +-- Track background items (TimelineTrackItem)
  |     - One per track
  |     - Draws track lane background
  |
  +-- Clip items (TimelineClipItem)
  |     - One per clip
  |     - Draws colored rectangle with filename
  |     - Handles hover for tooltips
  |
  +-- Time grid lines (QGraphicsLineItem)
        - Vertical lines at regular intervals
```

### 3.3 TimelineViewport Implementation

**File:** `oncutf/sync/ui/timeline_viewport.py`

```python
class TimelineViewport(QGraphicsView):
    """Graphics view for sync timeline display."""
    
    # Zoom configuration
    ZOOM_FACTOR = 1.25
    ZOOM_MIN = 0.01   # Very zoomed out
    ZOOM_MAX = 100.0  # Very zoomed in
    
    # Layout constants
    TRACK_HEIGHT = 60
    TRACK_SPACING = 4
    PIXELS_PER_SECOND_DEFAULT = 10
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = TimelineScene(self)
        self.setScene(self._scene)
        
        self._current_zoom = 1.0
        self._pixels_per_second = self.PIXELS_PER_SECOND_DEFAULT
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize view settings."""
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
```

### 3.4 Zoom and Scroll Design

**Zoom Implementation:**

- Mouse wheel with Ctrl modifier triggers zoom
- Zoom anchor point is under mouse cursor
- Zoom level clamped to [ZOOM_MIN, ZOOM_MAX]
- Zoom affects horizontal scale only (time axis)
- Vertical scale remains constant (track height fixed)

```python
def wheelEvent(self, event: QWheelEvent) -> None:
    """Handle zoom with mouse wheel + Ctrl."""
    if event.modifiers() & Qt.ControlModifier:
        # Zoom
        factor = self.ZOOM_FACTOR if event.angleDelta().y() > 0 else 1 / self.ZOOM_FACTOR
        new_zoom = self._current_zoom * factor
        
        if self.ZOOM_MIN <= new_zoom <= self.ZOOM_MAX:
            self._current_zoom = new_zoom
            self.scale(factor, 1.0)  # Scale X only
    else:
        # Scroll
        super().wheelEvent(event)
```

**Scroll Implementation:**

- Horizontal scroll via scroll bar or middle-mouse drag
- Vertical scroll via scroll bar
- Arrow keys for fine scroll control
- Home key jumps to timeline start
- End key jumps to timeline end

**Coordinate Mapping:**

```python
def time_to_x(self, time_seconds: float) -> float:
    """Convert timeline time to X coordinate."""
    return time_seconds * self._pixels_per_second

def x_to_time(self, x: float) -> float:
    """Convert X coordinate to timeline time."""
    return x / self._pixels_per_second

def track_to_y(self, track_index: int) -> float:
    """Convert track index to Y coordinate."""
    return track_index * (self.TRACK_HEIGHT + self.TRACK_SPACING)
```

**Performance Considerations for Large Clip Counts:**

1. **Lazy item creation**: Only create visible items, use placeholders for off-screen
2. **Level-of-detail rendering**: At low zoom, simplify clip visuals (no text)
3. **Item caching**: Enable `QGraphicsItem.ItemCoordinateCache` for clip items
4. **Scene rect management**: Set explicit scene rect to avoid expensive auto-calculation
5. **Viewport culling**: QGraphicsView handles this automatically

### 3.5 Visual Design Rules

**Matched Clips:**

- Solid rectangle fill with folder color (from `FileItem.color`)
- 1px solid border (darker shade of fill color)
- Filename text centered (white or black depending on fill luminance)
- Clip duration shown in bottom-right corner (small font)

**Unmatched Clips:**

- Same fill color as matched
- 2px DASHED border (red or orange)
- "UNMATCHED" label overlaid (semi-transparent red background)
- Filename text still visible

**Visual Specification:**

```
+--------------------------------------------------+
|  [Color Fill based on folder color]              |
|                                                  |
|  filename.mp4                                    |
|                           UNMATCHED (if status)  |
|                                       00:02:15   |
+--------------------------------------------------+
   ^- Dashed border if unmatched
```

**Track Lanes:**

- Alternating subtle background colors (light gray / slightly darker gray)
- Track label on left side ("V1", "V2", "A1", etc.)
- Device name shown in track header

**Time Grid:**

- Major grid lines every second at high zoom
- Major grid lines every 10 seconds at medium zoom
- Major grid lines every minute at low zoom
- Minor grid lines at subdivision intervals

### 3.6 Tooltip Integration

**Using oncutf TooltipHelper (REQUIRED):**

```python
from oncutf.utils.ui.tooltip_helper import TooltipHelper, TooltipType

class TimelineClipItem(QGraphicsRectItem):
    """Graphics item representing a clip on the timeline."""
    
    def __init__(self, clip: Clip, parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        self._clip = clip
        self._setup_tooltip()
    
    def _setup_tooltip(self) -> None:
        """Configure tooltip for this clip."""
        tooltip_text = self._build_tooltip_text()
        # TooltipHelper requires a QWidget, use scene's parent view
        # Tooltip setup will be done when item is added to scene
    
    def _build_tooltip_text(self) -> str:
        """Build tooltip content."""
        lines = [
            f"File: {self._clip.filename}",
            f"Device: {self._clip.device_name}",
            f"Duration: {self._format_duration(self._clip.duration_seconds)}",
            f"Status: {self._clip.sync_status}",
        ]
        if self._clip.match_confidence > 0:
            lines.append(f"Confidence: {self._clip.match_confidence:.0%}")
        if self._clip.sync_status == "unmatched":
            lines.append("Reason: No audio match found")
        return "\n".join(lines)
```

**Note:** Since QGraphicsItem is not a QWidget, tooltip handling will use a custom approach:
- Override `hoverEnterEvent` on clip items
- Show tooltip via TooltipHelper attached to the viewport widget
- Position tooltip near the hovered item

---

## 4. Manual Anchor UI and Logic

### 4.1 Anchor Modes

**Mode A: Clip-to-Clip Assist**

User selects two clips and declares them approximately aligned. System refines using audio.

**Mode B: Explicit Time Mapping**

User specifies exact frame positions in two clips that should align.

### 4.2 UI Flow: Clip-to-Clip Assist

1. User selects two clips in timeline (Ctrl+click or drag selection)

2. User clicks "Create Anchor" button in toolbar

3. System validates:
   - Exactly two clips selected
   - Clips are from different devices
   - Clips have overlapping time (per metadata or within reasonable range)

4. Dialog appears:
   ```
   +-----------------------------------------------+
   | Create Clip Anchor                            |
   +-----------------------------------------------+
   | Clip A: CAM1_0101.MP4 (Camera 1)              |
   | Clip B: CAM2_0222.MP4 (Camera 2)              |
   |                                               |
   | [x] Refine using audio matching               |
   |                                               |
   | [ Create Anchor ]  [ Cancel ]                 |
   +-----------------------------------------------+
   ```

5. On confirm:
   - If audio refine enabled: Run audio matching between clips
   - Compute device offset from result
   - Store anchor in session

### 4.3 UI Flow: Explicit Time Mapping

1. User selects two clips

2. User clicks "Create Anchor" > "Explicit Time Map"

3. Dialog appears:
   ```
   +-----------------------------------------------+
   | Explicit Time Mapping                         |
   +-----------------------------------------------+
   | Clip A: CAM1_0101.MP4                         |
   | Time in Clip A: [00:00:41:18] (HH:MM:SS:FF)   |
   |                                               |
   | Clip B: CAM2_0222.MP4                         |
   | Time in Clip B: [00:01:23:12] (HH:MM:SS:FF)   |
   |                                               |
   | Project FPS: 25                               |
   |                                               |
   | [ Create Anchor ]  [ Cancel ]                 |
   +-----------------------------------------------+
   ```

4. On confirm:
   - Parse timecodes according to project FPS
   - Compute frame-accurate offset
   - Store anchor

### 4.4 Timecode Parsing

**Module:** `oncutf/sync/utils/timecode_parser.py`

```python
class TimecodeParser:
    """Parses HH:MM:SS:FF timecode strings."""
    
    PATTERN = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2}):(\d{2})$")
    
    @classmethod
    def parse(cls, timecode: str, fps: float) -> float:
        """Parse timecode string to seconds.
        
        Args:
            timecode: String in format HH:MM:SS:FF
            fps: Frames per second for FF interpretation
            
        Returns:
            Time in seconds as float
            
        Raises:
            ValueError: If timecode format is invalid
        """
        match = cls.PATTERN.match(timecode.strip())
        if not match:
            raise ValueError(f"Invalid timecode format: {timecode}")
        
        hours, minutes, seconds, frames = map(int, match.groups())
        
        if frames >= fps:
            raise ValueError(f"Frame number {frames} exceeds FPS {fps}")
        
        total_seconds = (
            hours * 3600 +
            minutes * 60 +
            seconds +
            frames / fps
        )
        return total_seconds
```

### 4.5 How Anchors Modify Device Offsets

**Data Structure:**

```python
@dataclass
class Anchor:
    """User-defined sync anchor between clips."""
    
    anchor_id: str
    clip_a_id: str
    clip_b_id: str
    anchor_type: str                    # "clip_to_clip" or "explicit_time"
    
    # For explicit time mapping
    time_in_a_seconds: float | None     # Position in clip A
    time_in_b_seconds: float | None     # Position in clip B
    
    # Computed offset
    offset_seconds: float               # B relative to A
    
    # Refinement
    audio_refined: bool
    refined_offset_seconds: float | None
```

**Offset Computation:**

For explicit time mapping:
```
offset = (clip_a_start + time_in_a) - (clip_b_start + time_in_b)
```

The anchor offset is propagated to the device:
```
device_b.time_offset_seconds = anchor.offset_seconds
device_b.offset_source = "anchor"
```

**Re-Sync Using Anchors:**

When user clicks "Re-sync":

1. Clear all previous match edges for affected devices
2. Apply anchor offsets as initial device offsets
3. Re-run audio matching with narrower windows (anchor provides better estimate)
4. Rebuild timeline

---

## 5. Export Plan (MVP)

### 5.1 AAF Linked Export Strategy

**Target:** Avid Media Composer compatible AAF with linked (not embedded) media

**Module:** `oncutf/sync/exporters/aaf_exporter.py`

**Dependencies:**
- `pyaaf2` library for AAF file creation

### 5.2 AAF Structure

```
AAF File
  |
  +-- Header
  |     - Creation timestamp
  |     - Application info
  |
  +-- Content Storage
        |
        +-- Composition Mob (Main sequence)
        |     +-- TimelineMobSlot (V1)
        |     |     +-- SourceClip -> MasterMob -> FileSourceMob
        |     +-- TimelineMobSlot (V2)
        |     +-- TimelineMobSlot (A1)
        |     ...
        |
        +-- MasterMobs (one per clip)
        |     +-- Reference to FileSourceMob
        |
        +-- FileSourceMobs (one per clip)
              +-- FileDescriptor
                    +-- Locator (ABSOLUTE file path)
```

### 5.3 Mapping Timeline to AAF

| Timeline Concept | AAF Element |
|------------------|-------------|
| Track | TimelineMobSlot |
| Clip | SourceClip |
| Clip position | SourceClip start time in edit units |
| Clip duration | SourceClip length in edit units |
| Gap | Filler component |
| Media file | FileSourceMob with Locator |

### 5.4 Absolute Path Handling

**Requirements:**
- All media paths MUST be absolute
- Paths must use platform-native separators
- No relative paths or path variables

**Implementation:**

```python
def _create_file_locator(self, file_path: str) -> aaf2.mobs.Locator:
    """Create AAF locator with absolute path."""
    # Ensure absolute path
    abs_path = os.path.abspath(file_path)
    
    # Use platform-appropriate separator
    if sys.platform == "win32":
        # Windows: keep backslashes
        locator_path = abs_path
    else:
        # Unix: use forward slashes
        locator_path = abs_path
    
    # Create URLLocator with file:// URI scheme
    locator = self._aaf_file.create.Locator()
    locator["URLString"].value = f"file:///{locator_path}"
    
    return locator
```

### 5.5 Edit Rate and Timecode

- Use project FPS as AAF edit rate
- Convert all positions from seconds to edit units:
  ```python
  edit_units = int(seconds * project_fps)
  ```
- Start timecode defaults to 00:00:00:00 (configurable)

### 5.6 Export Workflow

```python
class AAFExporter:
    """Exports sync result to Avid AAF format."""
    
    def export(self, sync_result: SyncResult, output_path: str) -> bool:
        """Export timeline to AAF file.
        
        Args:
            sync_result: Complete sync session result
            output_path: Destination AAF file path
            
        Returns:
            True if export succeeded
        """
        try:
            with aaf2.open(output_path, "w") as f:
                self._aaf_file = f
                self._create_header(sync_result)
                self._create_master_mobs(sync_result)
                self._create_composition(sync_result)
            return True
        except Exception as e:
            self._logger.error("AAF export failed: %s", e)
            return False
```

### 5.7 Validation Steps for Avid Import

Before marking export complete:

1. Verify AAF file is valid (can be read by pyaaf2)
2. Verify all locator paths exist on filesystem
3. Log any missing files as warnings
4. Generate summary report of exported clips

**Post-Export User Instructions:**

```
Export complete: /path/to/output.aaf

Contains:
- 24 video clips across 3 tracks
- 5 audio clips on 1 track
- 2 unmatched clips on overflow track

To import in Avid:
1. File > Import > AAF
2. Select the exported file
3. Choose "Link to media" when prompted
4. Relink any missing media if paths have changed
```

---

## 6. Testing Plan

### 6.1 Unit Tests for Core Algorithms

**Test Location:** `tests/sync/`

#### 6.1.1 Normalization Tests

**File:** `tests/sync/test_ingest_service.py`

```python
class TestIngestService:
    """Unit tests for IngestService."""
    
    def test_create_clip_from_valid_file(self):
        """Test clip creation from valid FileItem."""
        pass
    
    def test_skip_zero_duration_file(self):
        """Test that zero-duration files are skipped."""
        pass
    
    def test_extract_sequence_number_from_filename(self):
        """Test sequence extraction: CAM1_0101.MP4 -> 101."""
        pass
    
    def test_timestamp_normalization_with_timezone(self):
        """Test UTC normalization when timezone present."""
        pass
    
    def test_timestamp_normalization_without_timezone(self):
        """Test handling of naive datetime values."""
        pass
```

#### 6.1.2 Clustering Tests

**File:** `tests/sync/test_cluster_service.py`

```python
class TestClusterService:
    """Unit tests for ClusterService."""
    
    def test_single_cluster_overlapping_clips(self):
        """Test clips within threshold form single cluster."""
        pass
    
    def test_multiple_clusters_separated_clips(self):
        """Test clips beyond threshold form separate clusters."""
        pass
    
    def test_untimed_clips_assigned_by_filename(self):
        """Test clips without timestamp use filename heuristics."""
        pass
    
    def test_master_device_selection_with_recorder(self):
        """Test recorder is selected as master when present."""
        pass
    
    def test_master_device_selection_without_recorder(self):
        """Test most-clips camera selected when no recorder."""
        pass
```

#### 6.1.3 Candidate Window Tests

**File:** `tests/sync/test_candidate_window.py`

```python
class TestCandidateWindow:
    """Unit tests for candidate window generation."""
    
    def test_window_from_metadata_offset(self):
        """Test window centered on metadata-derived offset."""
        pass
    
    def test_window_bounds_clamped_to_clip_duration(self):
        """Test window does not exceed clip bounds."""
        pass
    
    def test_no_window_for_non_overlapping_clips(self):
        """Test no candidate window when clips cannot overlap."""
        pass
```

#### 6.1.4 Anchor Mapping Tests

**File:** `tests/sync/test_anchor_controller.py`

```python
class TestAnchorController:
    """Unit tests for anchor creation and offset computation."""
    
    def test_explicit_time_anchor_offset_calculation(self):
        """Test offset from explicit time mapping."""
        # At 00:00:41:18 in A == 00:01:23:12 in B (25fps)
        # Expected offset computation
        pass
    
    def test_clip_to_clip_anchor_with_audio_refine(self):
        """Test anchor with audio refinement enabled."""
        pass
    
    def test_anchor_propagates_to_device_offset(self):
        """Test anchor offset is applied to device."""
        pass
```

#### 6.1.5 Timecode Parser Tests

**File:** `tests/sync/test_timecode_parser.py`

```python
class TestTimecodeParser:
    """Unit tests for timecode parsing."""
    
    @pytest.mark.parametrize("tc,fps,expected", [
        ("00:00:00:00", 25, 0.0),
        ("00:00:01:00", 25, 1.0),
        ("00:00:00:12", 25, 0.48),
        ("01:00:00:00", 25, 3600.0),
        ("00:01:30:15", 30, 90.5),
    ])
    def test_parse_valid_timecodes(self, tc, fps, expected):
        """Test parsing various valid timecodes."""
        assert TimecodeParser.parse(tc, fps) == pytest.approx(expected)
    
    def test_reject_invalid_format(self):
        """Test rejection of malformed timecode."""
        with pytest.raises(ValueError):
            TimecodeParser.parse("00:00:00", 25)
    
    def test_reject_frame_exceeds_fps(self):
        """Test rejection when frame >= fps."""
        with pytest.raises(ValueError):
            TimecodeParser.parse("00:00:00:25", 25)
```

### 6.2 Test Fixtures Design

**File:** `tests/sync/conftest.py`

```python
@pytest.fixture
def sample_clip_metadata():
    """Sample metadata dict for testing."""
    return {
        "CreateDate": "2025:06:15 14:30:00",
        "Duration": "00:02:15",
        "VideoFrameRate": 25.0,
        "AudioSampleRate": 48000,
    }

@pytest.fixture
def sample_file_item(tmp_path):
    """Create a sample FileItem for testing."""
    test_file = tmp_path / "CAM1_0101.MP4"
    test_file.write_bytes(b"dummy")  # Placeholder
    return FileItem.from_path(str(test_file))

@pytest.fixture
def sample_clips():
    """Create a set of sample Clip objects for testing."""
    return [
        Clip(
            clip_id="clip_001",
            file_path="/test/cam1/CAM1_0101.MP4",
            filename="CAM1_0101.MP4",
            metadata_start_time=datetime(2025, 6, 15, 14, 30, 0),
            duration_seconds=135.0,
            # ... other fields
        ),
        # ... more clips
    ]

@pytest.fixture
def sample_audio_data():
    """Generate sample audio data for matching tests."""
    import numpy as np
    sr = 8000
    duration = 5.0
    t = np.linspace(0, duration, int(sr * duration))
    # Sine wave with some noise
    audio = np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.randn(len(t))
    return audio.astype(np.float32)
```

### 6.3 Exporter Smoke Tests

**File:** `tests/sync/test_aaf_exporter.py`

```python
class TestAAFExporter:
    """Smoke tests for AAF export."""
    
    def test_export_creates_valid_aaf_file(self, tmp_path, sample_sync_result):
        """Test that export creates a readable AAF file."""
        output_path = tmp_path / "test_export.aaf"
        exporter = AAFExporter()
        
        result = exporter.export(sample_sync_result, str(output_path))
        
        assert result is True
        assert output_path.exists()
        
        # Verify file can be opened
        with aaf2.open(str(output_path), "r") as f:
            assert f.header is not None
    
    def test_export_contains_expected_tracks(self, tmp_path, sample_sync_result):
        """Test exported AAF has correct track count."""
        output_path = tmp_path / "test_export.aaf"
        exporter = AAFExporter()
        exporter.export(sample_sync_result, str(output_path))
        
        with aaf2.open(str(output_path), "r") as f:
            comp = next(f.content.compositionmobs())
            slots = list(comp.slots)
            assert len(slots) == sample_sync_result.total_tracks
    
    def test_export_uses_absolute_paths(self, tmp_path, sample_sync_result):
        """Test all media locators use absolute paths."""
        output_path = tmp_path / "test_export.aaf"
        exporter = AAFExporter()
        exporter.export(sample_sync_result, str(output_path))
        
        with aaf2.open(str(output_path), "r") as f:
            for mob in f.content.mastermobs():
                # Check locator paths are absolute
                pass  # Implementation detail
```

### 6.4 Test Markers

Add sync-specific test markers in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "sync: sync session related tests",
    "sync_audio: sync audio processing tests (may require audio files)",
    "sync_export: sync export tests",
]
```

---

## 7. Implementation Roadmap

### 7.1 Phase MVP (4-6 weeks)

**Goal:** Basic working sync with timeline display and AAF export

#### Week 1-2: Foundation

| Task | Complexity | Risk |
|------|------------|------|
| Create `oncutf/sync/` package structure (brand: oncutf) | Low | Low |
| Implement domain models (Clip, Device, Track, etc.) | Low | Low |
| Implement IngestService | Medium | Low |
| Implement ClusterService (basic time clustering) | Medium | Medium |
| Write unit tests for ingest and clustering | Medium | Low |

**Acceptance Criteria:**
- [ ] Can create Clip objects from selected FileItems
- [ ] Clips are grouped into segments by time proximity
- [ ] All domain model unit tests pass

#### Week 2-3: Audio Engine MVP

| Task | Complexity | Risk |
|------|------------|------|
| Implement AudioProcessor interface | Low | Low |
| Implement PythonAudioProcessor (load, resample, normalize) | Medium | Medium |
| Implement basic cross-correlation matching | High | High |
| Implement candidate window generation | Medium | Medium |
| Implement confidence scoring | Medium | Low |
| Write audio matching unit tests | Medium | Medium |

**Acceptance Criteria:**
- [ ] Can load audio from MP4/MOV/WAV files
- [ ] Cross-correlation finds correct offset for test cases
- [ ] Confidence scores reflect match quality

#### Week 3-4: Timeline Builder

| Task | Complexity | Risk |
|------|------------|------|
| Implement TimelineBuilder | Medium | Medium |
| Implement device offset propagation | Medium | Medium |
| Implement unmatched clip placement (both modes) | Medium | Low |
| Build SyncOrchestrator to coordinate pipeline | Medium | Medium |
| Write integration tests for full pipeline | High | Medium |

**Acceptance Criteria:**
- [ ] Complete pipeline runs on test data
- [ ] Matched clips positioned correctly
- [ ] Unmatched clips placed according to selected mode

#### Week 4-5: Timeline UI

| Task | Complexity | Risk |
|------|------------|------|
| Implement TimelineViewport (QGraphicsView) | Medium | Low |
| Implement TimelineScene | Medium | Low |
| Implement TimelineClipItem with visual styling | Medium | Low |
| Implement zoom and scroll | Medium | Low |
| Integrate TooltipHelper for clip tooltips | Low | Low |
| Implement SyncSessionWidget container | Medium | Low |
| Integrate with MainWindow | Medium | Medium |

**Acceptance Criteria:**
- [ ] Timeline displays clips as colored rectangles
- [ ] Unmatched clips have dashed border and UNMATCHED label
- [ ] Zoom and scroll work smoothly
- [ ] Tooltips show clip details on hover

#### Week 5-6: AAF Export

| Task | Complexity | Risk |
|------|------------|------|
| Implement AAFExporter | High | High |
| Test AAF import in Avid (if available) | Medium | High |
| Implement export validation | Medium | Low |
| Write exporter smoke tests | Medium | Low |

**Acceptance Criteria:**
- [ ] AAF file is created and readable by pyaaf2
- [ ] AAF contains correct track structure
- [ ] All media paths are absolute
- [ ] (Stretch) AAF imports successfully in Avid

### 7.2 Phase v1 (4 weeks after MVP)

**Goal:** Manual anchors, settings UI, improved UX

| Task | Complexity | Risk |
|------|------------|------|
| Implement AnchorDialog (both modes) | Medium | Low |
| Implement AnchorController | Medium | Medium |
| Implement SyncSettingsDialog | Medium | Low |
| Add "Strictness" setting to UI | Low | Low |
| Implement SyncToolbar with all actions | Medium | Low |
| Add progress feedback during sync | Medium | Low |
| Implement JSON/CSV report export | Medium | Low |
| Add filename anomaly detection and display | Medium | Low |
| Performance optimization for large clip counts | High | Medium |

**Acceptance Criteria:**
- [ ] Users can create anchors via UI
- [ ] Anchors affect sync results correctly
- [ ] Settings dialog configures strictness
- [ ] Progress shown during long operations
- [ ] Reports exportable

### 7.3 Phase v2 (Future)

**Goal:** Advanced features, performance, additional exports

| Task | Complexity | Risk |
|------|------------|------|
| C++ audio accelerator (pybind11) | Very High | High |
| Drift detection for long takes | High | High |
| FCPXML export | High | Medium |
| Resolve export | High | Medium |
| LTC audio timecode support | Very High | High |
| Multi-channel WAV support | Medium | Medium |
| Waveform caching and display | High | Medium |

---

## 8. Do Not Do Now List

The following features are explicitly deferred and MUST NOT be implemented in MVP:

| Feature | Reason | Target Phase |
|---------|--------|--------------|
| LTC audio timecode extraction | Complex, requires specialized decoding | v2+ |
| Embedded camera timecode | Device-specific, needs hardware testing | v2+ |
| Advanced drift correction | Complex algorithm, needs long-take test data | v2 |
| Multi-channel WAV (4/6/8ch) | Edge case, MVP handles mono/stereo | v2 |
| Proxy generation | Not required for sync, adds complexity | Never (manual) |
| Waveform display in timeline | Nice-to-have, not core functionality | v2 |
| Video playback | Out of scope, timeline is viewport only | Never |
| Audio playback | Out of scope, timeline is viewport only | Never |
| FCPXML export | Secondary NLE target | v1+ |
| Resolve export | Secondary NLE target | v1+ |
| EDL export | Limited metadata support | v2+ |
| Cloud/AI services | Commercial reasons, local-only | Never |
| Automatic project-wide sync | Only selected files, not folder scan | Never |

---

## Appendix A: oncutf Integration Checklist

Before implementing each component, verify (Brand: oncut / Product: oncutf):

- [ ] Uses `get_cached_logger(__name__)` for logging
- [ ] Uses `wait_cursor()` context manager for long operations
- [ ] Uses `TimerManager.schedule()` instead of QTimer.singleShot
- [ ] Uses `TooltipHelper.setup_tooltip()` for tooltips
- [ ] Uses `CustomMessageDialog` instead of QMessageBox
- [ ] Follows type annotation conventions
- [ ] Has module-level docstring with Author/Date
- [ ] Has docstrings for all public classes/methods
- [ ] Does not use emojis or non-ASCII characters
- [ ] Integrates with ApplicationContext where appropriate

---

## Appendix B: File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Module | snake_case | `audio_matcher.py` |
| Class | PascalCase | `AudioMatcher` |
| Function | snake_case | `match_audio_clips` |
| Constant | UPPER_SNAKE | `ZOOM_FACTOR` |
| Test file | test_<module> | `test_audio_matcher.py` |
| Test class | Test<Class> | `TestAudioMatcher` |
| Test method | test_<behavior> | `test_finds_correct_offset` |

---

## Appendix C: Dependencies

**New dependencies required:**

| Package | Purpose | License |
|---------|---------|---------|
| `pyaaf2` | AAF file creation | MIT |
| `soundfile` | Audio file I/O | BSD |
| `numpy` | Array operations | BSD |
| `scipy` | Signal processing (cross-correlation) | BSD |

**Optional for performance (v2):**

| Package | Purpose |
|---------|---------|
| `pybind11` | C++ bindings for audio accelerator |
| `numba` | JIT compilation for Python audio code |

---

END OF IMPLEMENTATION PLAN
