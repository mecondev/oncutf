<!-- 
Thumbnail Viewport Implementation Plan

Author: Michael Economou
Date: 2026-01-16
Last Updated: 2026-01-18

A comprehensive plan for implementing the Thumbnail Viewport as an integrated browsing/ordering UI
alongside the existing file table, with manual ordering support and persistent caching.

ARCHIVING POLICY:
- This document will be moved to docs/_archive/ upon Phase 6 completion
- Deferred features (lasso selection, video preview) remain in TODO.md
- Core implementation details (architecture, DB schema) remain in ARCHITECTURE.md
-->

# Thumbnail Viewport Implementation Plan

## Overview

Implement a second viewport (alongside the existing table view) that displays files as a grid of thumbnails with integrated manual ordering, selection, and sorting capabilities. The viewport will:

- Display image and video thumbnails in a grid layout
- Support manual drag-reorder with order persistence per folder
- Integrate with existing file table (shared model, synchronized state)
- Cache thumbnails persistently (disk + SQLite DB) for fast folder reload
- Generate thumbnails in background threads without UI freeze

**Status:** In Progress - Phase 2 Complete  
**Priority:** High  
**Estimated Duration:** 5-7 weeks (phased implementation)  
**Time Elapsed:** 2 weeks (as of 2026-01-16)  
**Completion:** 40% (Phase 1-2 done, bundled tools integration complete)

---

## Progress Summary

### Completed Work (Weeks 1-2)

**Phase 1: Core Infrastructure [COMPLETE]**
- ThumbnailCache system (memory LRU + disk persistence)
- ThumbnailProvider abstract classes (Image + Video)
- ThumbnailStore database operations
- Database migration v4->v5 (thumbnail_cache, thumbnail_order tables)
- All code quality checks passing (ruff + mypy)
- 2032 lines of code added

**Phase 2: Thumbnail Manager & Generation [COMPLETE]**
- ThumbnailManager orchestrator (request queue, worker coordination)
- ThumbnailWorker background thread (async generation)
- Progress signals and error handling
- 650 lines of code added

**Bonus: Bundled Tools Integration [COMPLETE]**
- ExifToolWrapper: Uses bundled exiftool (bin/<platform>/)
- VideoThumbnailProvider: Auto-detects bundled ffmpeg
- PyInstaller-ready architecture
- Standalone distribution support
- 472 lines of code + documentation

**Total Progress:**
- Lines of code: 3154+
- Files created: 11
- Files modified: 8
- Commits: 3 (pushed to GitHub)
- Test coverage: Unit tests pending (Phase 6)

### Remaining Work (Weeks 3-7)

**Phase 3: UI Layer (Week 3-4)** [IN PROGRESS NEXT]
- ThumbnailDelegate (rendering with overlays)
- ThumbnailViewportWidget (QListView with lasso selection)
- FileTableModel.order_mode extension
- VideoPreviewDialog

**Phase 4: Integration & Sync (Week 4-5)**
- Viewport toggle (details <-> thumbs)
- Model synchronization (shared FileTableModel)
- Color flag integration
- Sorting integration (manual <-> sorted modes)

**Phase 5: Database Migrations** [DONE - completed in Phase 1]

**Phase 6: Testing & Polish (Week 6-7)**
- Unit tests for all phases
- Performance optimization
- Edge case handling
- Documentation updates

---

## Architecture Overview

### Data Flow

```
File Load (FileLoadController)
  ↓
File List (FileTableModel.files) ← Shared Model
  ↓
Manual Order Lookup (ThumbnailOrderStore in DB)
  ↓
ThumbnailManager
  ├─ Check Cache (LRU + DB)
  ├─ Queue for Generation (if not cached)
  └─ Return Path/Placeholder
  ↓
ThumbnailViewportWidget (QListView + Delegate)
  ├─ Render Thumbnails (with overlays)
  ├─ Handle Selection (Ctrl/Shift/Lasso)
  └─ Emit Order Changes
  ↓
Model Updated + Sync to FileTable
```

### Key Principles

1. **Single Source of Truth:** File list is in `FileTableModel.files` (not duplicated in viewport)
2. **Shared Selection State:** Both viewport and table share selection (via `SelectionStore` if exists)
3. **Shared Color Flags:** Colors are already in `FileItem.color` (loaded from DB)
4. **Manual Order Persistence:** Stored in SQLite as `(folder_path, file_path, order_index)` tuples
5. **Background Generation:** Thumbnails generated in worker threads with progress reporting
6. **Performance:** Virtual scrolling (QListView built-in), LRU memory cache, persistent disk cache

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2) [COMPLETE]

**Status:** COMPLETE (2026-01-16)  
**Deliverables:** ThumbnailCache, ThumbnailProvider, ThumbnailStore, DB migration v4→v5

#### 1.1 Thumbnail Cache System [COMPLETE] [COMPLETE]
- **File:** `oncutf/core/thumbnail/thumbnail_cache.py`
- **Classes:**
  - `ThumbnailCacheConfig` - Settings (size, location, TTL)
  - `ThumbnailDiskCache` - Disk storage management
  - `ThumbnailMemoryCache` - LRU in-memory cache (500 entries max)
  - `ThumbnailCache` - Orchestrator combining both

**Implementation Status:**
- [DONE] LRU memory cache with OrderedDict (thread-safe with RLock)
- [DONE] Disk cache with SHA256 hash-based filenames
- [DONE] generate_cache_key(file_path, mtime, size) method
- [DONE] get/put/invalidate/clear operations
- [DONE] AppPaths.get_thumbnails_dir() integration

**Responsibilities:**
- Store/retrieve thumbnails from `~/.cache/oncutf/thumbnails/`
- Maintain file identity: `hash(file_path + mtime + size)` → safe filename
- Invalidate when file modified (mtime check)
- LRU eviction when memory cache exceeds 500 entries

#### 1.2 Thumbnail DB Store [COMPLETE]
- **File:** `oncutf/core/database/thumbnail_store.py`
- **Tables:** `thumbnail_cache`, `thumbnail_order` (added via migration v4→v5)

**Implementation Status:**
- [DONE] ThumbnailStore class with all CRUD operations
- [DONE] Database migration v4→v5 (oncutf/core/database/migrations.py)
- [DONE] Schema with normalized rows (not JSON blobs)
- [DONE] Indexes for performance: idx_thumbnail_cache_folder, idx_thumbnail_order_folder
- [DONE] Integration with DatabaseManager (delegation methods)

**Schema (v5):**
```sql
  CREATE TABLE thumbnail_cache (
    id INTEGER PRIMARY KEY,
    folder_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_mtime REAL NOT NULL,
    file_size INTEGER NOT NULL,
    cache_filename TEXT NOT NULL,  -- Safe disk filename
    video_frame_time REAL,          -- Timestamp if video
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_path, file_mtime, file_size)  -- File identity fingerprint
  )
  CREATE INDEX idx_thumbnail_cache_folder ON thumbnail_cache(folder_path)
  
  CREATE TABLE thumbnail_order (
    id INTEGER PRIMARY KEY,
    folder_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    UNIQUE(folder_path, file_path)
  )
  CREATE INDEX idx_thumbnail_order_folder ON thumbnail_order(folder_path, order_index)
```
  CREATE INDEX idx_thumbnail_order_folder ON thumbnail_order(folder_path, order_index)
  ```

**Design Decision: Normalized Rows**
- Each file = 1 row with order_index
- Incremental updates: only affected files change
- No JSON blob rewrites on every drag
- Easier consistency when files added/removed
- One-shot load: `SELECT file_path FROM thumbnail_order WHERE folder_path=? ORDER BY order_index`

**Methods:**
- `get_cached_path(file_path, mtime, size) -> str | None`
- `save_cache_entry(folder_path, file_path, mtime, size, cache_filename, video_frame_time)`
  - Uses UPSERT: INSERT OR REPLACE for same (file_path, mtime, size)
- `invalidate_entry(file_path)`
  - Deletes all cache entries for file_path (any mtime/size)
- `get_folder_order(folder_path) -> list[tuple[file_path, order_index]]`
  - Returns: `[(file_path, order_index), ...]` sorted by order_index
- `update_folder_order(folder_path, ordered_files: list[tuple[file_path, order_index]])`
  - Batch UPSERT: `INSERT OR REPLACE INTO thumbnail_order (folder_path, file_path, order_index) VALUES ...`
  - Deletes orphaned entries: files not in new order list
- `clear_folder_order(folder_path)`
  - `DELETE FROM thumbnail_order WHERE folder_path=?`

#### 1.3 Thumbnail Providers (Abstract) [COMPLETE]
- **File:** `oncutf/core/thumbnail/providers.py`
- **Classes:**
  - `ThumbnailProvider` (ABC)
  - `ImageThumbnailProvider` - QImage reader for image files
  - `VideoThumbnailProvider` - FFmpeg for video frames

**Implementation Status:**
- [DONE] Abstract base with generate(file_path) and supports(file_path)
- [DONE] ImageThumbnailProvider: JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC support
- [DONE] VideoThumbnailProvider: FFmpeg integration with bundled binary support
- [DONE] Smart frame heuristic: t = clamp(duration * 0.35, 2.0s, duration - 2.0s)
- [DONE] Quality validation: luma > 10, contrast > 5
- [DONE] Fallback frames: 15%, 50%, 70% if primary frame rejected

**Responsibilities:**
- Load/process file → QPixmap (constrained size)
- Video: Extract frame at t = clamp(duration * 0.35, 2.0, duration - 2.0)
- Quality check: reject frames with luma < 10 or contrast < 5 (fallback to 15%, 50%, 70%)
- Return QPixmap or raise `ThumbnailGenerationError`

---

### Phase 2: Thumbnail Manager & Generation (Week 2-3) [COMPLETE]

**Status:** COMPLETE (2026-01-16)  
**Deliverables:** ThumbnailManager orchestrator, ThumbnailWorker thread, bundled tools integration

#### 2.1 Thumbnail Manager [COMPLETE] [COMPLETE]
- **File:** `oncutf/core/thumbnail/thumbnail_manager.py`
- **Classes:**
  - `ThumbnailRequest` - Queued request (file path, folder, preferred size)
  - `ThumbnailManager` - Orchestrator

**Implementation Status:**
- [DONE] Thread-safe queue.Queue for requests
- [DONE] Cache lookup: memory → disk → DB
- [DONE] Worker coordination (2 threads default)
- [DONE] Signals: thumbnail_ready(file_path, pixmap), generation_progress(completed, total)
- [DONE] Lazy placeholder loading (avoids QGuiApplication requirement at import)
- [DONE] get_thumbnail() returns placeholder immediately, emits signal when ready
- [DONE] Statistics: get_cache_stats() with queue size, worker count

**Responsibilities:**
- Accept requests from UI
- Check cache (memory → disk → DB)
- Queue for background generation if missing
- Emit signals: `thumbnail_ready(file_path, pixmap)`, `generation_progress(completed, total)`
- Handle errors gracefully (return placeholder)

#### 2.2 Thumbnail Worker [COMPLETE]
- **File:** `oncutf/core/thumbnail/thumbnail_worker.py`
- **Worker Thread:** Generate thumbnails asynchronously

**Implementation Status:**
- [DONE] QThread-based worker with request queue processing
- [DONE] Provider selection by file extension (image vs video)
- [DONE] Disk cache save + DB update after generation
- [DONE] Error handling with graceful fallbacks
- [DONE] Signals: thumbnail_ready, generation_error
- [DONE] Clean shutdown with request_stop() method

#### 2.3 Bundled Tools Integration [COMPLETE - BONUS]

**Extra work completed for installer preparation:**

- **ExifToolWrapper:** Updated to use bundled exiftool
  - File: `oncutf/utils/shared/exiftool_wrapper.py`
  - Uses `external_tools.get_tool_path(ToolName.EXIFTOOL)`
  - All subprocess calls updated (Popen + run)
  - Stores path in `self._exiftool_path`

- **VideoThumbnailProvider:** Auto-detects bundled ffmpeg
  - File: `oncutf/core/thumbnail/providers.py`
  - Uses `external_tools.get_tool_path(ToolName.FFMPEG)` by default
  - Falls back to system PATH if bundled not found

- **Tool Resolution Strategy:**
  1. Check `bin/<platform>/` for bundled binaries
  2. Fallback to system PATH
  3. Raise FileNotFoundError with download instructions

- **PyInstaller Ready:**
  - `AppPaths.get_bundled_tools_dir()` returns `_MEIPASS/bin` when frozen
  - Binaries auto-extracted from installer
  - No system dependencies required

- **Documentation:**
  - Created `docs/bundled_tools_integration.md`
  - Distribution checklist, testing procedures, license compliance

---

### Phase 3: UI Layer - Thumbnail Viewport (Week 3-4) [NOT STARTED]

**Status:** NOT STARTED  
**Next Steps:** Implement ThumbnailDelegate (with 2-circle indicators from theme + frame tinting), ThumbnailViewportWidget (with multipurpose progress widget + zoom slider), FileTableModel.order_mode, Lasso Selection (Phase 3.4)

**Note:** Phase 3 includes lasso selection (3.4) - budget extra time for edge cases.

#### 3.1 Thumbnail Delegate
- **File:** `oncutf/ui/delegates/thumbnail_delegate.py`
- **Class:** `ThumbnailDelegate(QStyledItemDelegate)`

**Rendering:**
- Rectangle frame (photo slide style, ~3px border)
  - **Color flag tinting:** Frame border and background tinted with FileItem.color (if set)
  - Non-colored files: default theme border (neutral gray/white)
  - Colored files: border color matches flag, background subtle tint (~10% opacity)
- Thumbnail centered with aspect ratio fit
- Filename word-wrapped below (Qt.TextWordWrap)
- **Metadata/Hash indicators (top-left, 2 circles, 12px diameter each):**
  - **First circle (left): Metadata status**
    - No metadata: `#404040` (dark gray) - `METADATA_ICON_COLORS["none"]`
    - Fast metadata loaded: `#51cf66` (green) - `METADATA_ICON_COLORS["loaded"]`
    - Extended metadata loaded: `#fabf65` (yellowish-orange) - `EXTENDED_METADATA_COLOR`
  - **Second circle (right): Hash status**
    - No hash: `#404040` (dark gray) - `METADATA_ICON_COLORS["none"]`
    - Hash cached: `#ce93d8` (pink-purple) - `METADATA_ICON_COLORS["hash"]`
  - Same visual design as FileTable status columns (12px circles with 2px white border)
  - Tooltip on hover: "Metadata: Extended" / "Hash: Cached"
  - Spacing: 4px between circles, 8px margin from top-left corner
- **Star rating overlay (top-right, 5 stars, 0-5 rating)** [FUTURE]
  - Display: 12px gold stars, semi-transparent background
  - **Note:** Requires `FileItem.rating` field + DB storage (not yet implemented)
  - **Sync:** Rating changes must update both thumbnail_cache AND file_table
  - Visual: Filled stars for rating value, empty/outlined for remainder
  - **Status:** Deferred to Phase 6 or later (storage layer first)
- Video duration badge (bottom-right, semi-transparent, "HH:MM:SS")
- Loading spinner while generating
- Placeholder (folder icon + "Loading...") for failed thumbnails

**Interactions:**
- Hover: Highlight border + show full filename in tooltip
- Selected: Distinct border glow (theme color) + semi-transparent background
- Double-click: Emit `file_activated(file_path)`

#### 3.2 Thumbnail Viewport Widget
- **File:** `oncutf/ui/widgets/thumbnail_viewport.py`
- **Class:** `ThumbnailViewportWidget(QWidget)`

**Layout:**
- **Main Layout (QVBoxLayout):**
  - Top: **Existing status label widget** (already exists, no changes)
    - Same widget used for FileTable (managed by StatusManager)
    - Updates automatically when viewport changes (same as FileTable)
    - No new implementation needed - just connect signals
  - Center: QListView (IconMode)
    - Uses **same FileTableModel** as table view (not a wrapper)
    - FileTableModel provides `order_mode` property: "manual" | "sorted"
    - Delegate set from Phase 3.1
  - Bottom: Toolbar (QWidget with QHBoxLayout)
    - **Left side: Multipurpose widget area**
      - Initially: Thumbnail generation progress (QProgressBar)
      - Format: "Generating thumbnails: 45/128 (35%)"
      - Hides when generation complete
      - Future: Can be reused for other operations (batch rename preview, etc.)
    - **Right side: Zoom Slider**
      - Icon (zoom-out, 16px) | QSlider (Qt.Horizontal, 64-256px range) | Icon (zoom-in, 16px)
      - **NO label** - use tooltip instead: "Thumbnail Size: 128px" (updates on hover)
      - Saves preference to config on change
      - Connects to: `self._list_view.setIconSize(QSize(value, value))`

**Model Integration:**
- Viewport and table share the same model instance
- Order changes in viewport update FileTableModel.files directly
- Model emits dataChanged → both views update automatically

**Features:**
- **Zoom:** Mouse wheel (Ctrl+wheel if scroll used for pan)
  - Min 64px, Max 256px thumbnail size
  - Save preference to config
- **Pan:** Middle mouse button drag
- **Selection:**
  - Ctrl+Click: Toggle individual thumbnail
  - Shift+Click: Range select
  - **Lasso Selection (Complex):**
    - QRubberBand on drag in empty space
    - Calculate item rects with `visualRect(index)`
    - Intersect with rubber band rect
    - Call `selectionModel().select()` with QItemSelection
    - Edge cases: scroll during selection, item layout changes
    - Requires custom eventFilter on viewport
  - Visual sync with FileTable (shared QItemSelectionModel)
- **Drag Arrange (Manual Mode Only):**
  - Drag thumbnail to new position
  - Visual feedback: insertion line or target highlight
  - Drop: Reorder in model + emit signal
  - Auto-save to DB via ThumbnailOrderStore
- **Context Menu:**
  - Sort Ascending (A-Z filename)
  - Sort Descending (Z-A filename)
  - Sort by Color Flag
  - Sort by Folder Path (if multi-folder view)
  - Manual Order (toggle back from sort)
  - ---
  - **[FUTURE] Set Rating:** Submenu with 0-5 stars
  - **[FUTURE] Sort by Rating:** High to Low / Low to High
  - **[FUTURE] Hide/Show Filters:** Unrated, Below 1-4 stars
  - ---
  - File operations (same as table context menu): Open, Rename, Delete, etc.

**Rating Implementation Prerequisites:**
- Add `rating INTEGER DEFAULT 0` to `file_table` schema
- Add `rating` field to `FileItem` dataclass
- Implement rating sync: thumbnail → file_table → metadata write
- Add rating column to FileTableView (optional, hidden by default)
- **Keyboard Navigation:**
  - Arrow keys: Move selection
  - Home/End: Jump to start/end
  - PageUp/PageDown: Scroll viewport
  - **0-5 keys: Set star rating** [FUTURE - requires rating storage]
  - **R key: Clear rating** [FUTURE]

#### 3.3 FileTableModel Order Mode Extension

**File:** `oncutf/models/file_table/file_table_model.py`

**New Properties:**
```python
class FileTableModel:
    order_mode: Literal["manual", "sorted"] = "manual"
    sort_key: str | None = None  # "filename", "color", "rating", etc.
    sort_reverse: bool = False
    
    def set_order_mode(self, mode, key=None, reverse=False):
        """Change order mode and trigger re-sort if needed."""
        self.order_mode = mode
        if mode == "sorted":
            self.sort_key = key
            self.sort_reverse = reverse
            self._apply_sort()
            # Clear manual order from DB
            self._clear_manual_order_db()
        else:  # manual
            self._load_manual_order_db()
        
        self.dataChanged.emit(...)  # Notify views
```

#### 3.4 Lasso Selection (Complex)

**File:** `oncutf/ui/widgets/thumbnail_viewport.py` (event filter extension)

**Implementation:**
```python
class ThumbnailViewport:
    def __init__(self):
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self._rubber_band_origin = None
        self.viewport().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            # Check if click on empty space (not on item)
            index = self.indexAt(event.pos())
            if not index.isValid() and event.button() == Qt.LeftButton:
                self._rubber_band_origin = event.pos()
                self._rubber_band.setGeometry(QRect(self._rubber_band_origin, QSize()))
                self._rubber_band.show()
        
        elif event.type() == QEvent.MouseMove and self._rubber_band.isVisible():
            # Update rubber band rect
            self._rubber_band.setGeometry(QRect(
                self._rubber_band_origin, event.pos()
            ).normalized())
            
            # Calculate intersecting items
            rubber_rect = self._rubber_band.geometry()
            selection = QItemSelection()
            
            for row in range(self.model().rowCount()):
                index = self.model().index(row, 0)
                item_rect = self.visualRect(index)
                
                if rubber_rect.intersects(item_rect):
                    selection.append(QItemSelectionRange(index))
            
            # Apply selection
            self.selectionModel().select(
                selection, 
                QItemSelectionModel.ClearAndSelect
            )
        
        elif event.type() == QEvent.MouseButtonRelease:
            self._rubber_band.hide()
            self._rubber_band_origin = None
        
        return super().eventFilter(obj, event)
```

**Edge Cases to Test:**
- Scroll during lasso (item rects change)
- Item layout changes mid-drag
- Lasso + Ctrl modifier (additive selection)
- Performance with 1000+ items visible

---

### Phase 4: Integration & Sync (Week 4-5) [NOT STARTED]

**Status:** NOT STARTED  
**Dependencies:** Phase 3 complete

#### 4.1 Viewport Toggle
- **Integration:** Use existing `viewport_button_group` infrastructure
- Add signal handler in `SignalController` (or new controller)
- Connect: `viewport_button_group.buttonClicked` → `_on_viewport_changed(button_id)`

**Logic:**
- If button "details": Show FileTableView
- If button "thumbs": Show ThumbnailViewportWidget
- Use QStackedWidget in center panel or toggle visibility

#### 4.2 Model Synchronization
- **Shared File List:** Both views display `FileTableModel.files` (no duplication)
- **Manual Order Lookup:**
  - On file load: Query `ThumbnailOrderStore.get_folder_order(folder_path)`
  - If exists: Reorder `FileTableModel.files` to match
  - If not exists: Keep current order (ascending by filename)
- **Order Update on Drag:**
  - Thumbnail drag → reorder in model
  - Emit `files_reordered` signal
  - FileTable updates immediately (both views same list)
  - Save to DB via `ThumbnailOrderStore.update_folder_order()`
- **Selection Sync:**
  - Viewport selection → update shared selection store
  - Table selection → update shared selection store
  - Both views reflect same selection (via selection model signals)

#### 4.3 Color Flag & File Properties
- Color flag already loaded in `FileItem.color`
- Thumbnail delegate displays without modification
- No new storage needed

#### 4.4 Sorting Integration

**FileTableModel.order_mode Property:**
- `Literal["manual", "sorted"]` - determines drag reorder behavior
- When `sorted`: drag reorder disabled (Qt sort active)
- When `manual`: drag reorder enabled, updates DB on drop

**Sort Menu Actions:**
- **Sort Ascending:** `model.set_order_mode("sorted", key="filename", reverse=False)`
  - Calls `files.sort(key=lambda f: f.filename.lower())`
  - Clears DB manual order: `DELETE FROM thumbnail_order WHERE folder_path=?`
  - Disables drag reorder in viewport

- **Sort Descending:** `model.set_order_mode("sorted", key="filename", reverse=True)`

- **Sort by Color:** `model.set_order_mode("sorted", key="color")`
  - Sort key: `(f.color == "none", f.color)` (None last)

- **Sort by Rating:** `model.set_order_mode("sorted", key="rating", reverse=True/False)`
  - High to Low: `reverse=True`
  - Low to High: `reverse=False`

- **Manual Order (Return to Manual):**
  - `model.set_order_mode("manual")`
  - Load from DB: `SELECT file_path FROM thumbnail_order WHERE folder_path=? ORDER BY order_index`
  - If no DB order: keep current order (from last sort)
  - Enables drag reorder in viewport

**Drag Reorder Behavior:**
```python
if model.order_mode == "manual":
    # Allow drop, update model + DB
    model.beginMoveRows(parent, src_row, src_row, parent, dest_row)
    # ... reorder files list ...
    model.endMoveRows()
    store.update_folder_order(folder, [(path, idx) for idx, path in enumerate(files)])
else:
    # Reject drop (sorted mode active)
    event.ignore()
```

---

### Phase 5: Database Migrations (Week 5-6) [COMPLETE - Done in Phase 1]

**Status:** COMPLETE (completed during Phase 1)  
**Note:** Migration v4→v5 already implemented and deployed.

#### 5.1 Migration Script [COMPLETE] [COMPLETE]
- **File:** `oncutf/core/database/migrations.py`
- **Migration:** v4 → v5 (DEPLOYED)

**Implementation Status:**
- [DONE] Added thumbnail_cache table with indexes
- [DONE] Added thumbnail_order table with indexes
- [DONE] SCHEMA_VERSION = 5 in migrations.py and database_manager.py
- [DONE] Automatic migration on app startup
- [DONE] Backward compatible: old databases auto-upgrade

**Code:**
  ```python
  def migrate_v4_to_v5(connection):
      """Add thumbnail cache tables."""
      cursor = connection.cursor()
      
      # Thumbnail cache index
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS thumbnail_cache (
              id INTEGER PRIMARY KEY,
              folder_path TEXT NOT NULL,
              file_path TEXT NOT NULL,
              file_mtime REAL NOT NULL,
              file_size INTEGER NOT NULL,
              cache_filename TEXT NOT NULL,
              video_frame_time REAL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(file_path, file_mtime)
          )
      """)
      
      # Thumbnail order (manual arrange)
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS thumbnail_order (
              id INTEGER PRIMARY KEY,
              folder_path TEXT NOT NULL,
              file_path TEXT NOT NULL,
              order_index INTEGER NOT NULL,
              UNIQUE(folder_path, file_path)
          )
      """)
      
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_cache_folder ON thumbnail_cache(folder_path)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_thumbnail_order_folder ON thumbnail_order(folder_path)")
      
      connection.commit()
  ```

#### 5.2 Update DatabaseManager
- Inject `ThumbnailStore` into `DatabaseManager.__init__()`
- Expose methods: `get_thumbnail_cache_path()`, `update_thumbnail_order()`, etc.

---

### Phase 6: Testing & Polish (Week 6-7) [NOT STARTED]

**Status:** NOT STARTED  
**Dependencies:** Phase 3-4 complete

#### 6.1 Unit Tests
- `tests/unit/thumbnail/test_thumbnail_cache.py`
- `tests/unit/thumbnail/test_thumbnail_manager.py`
- `tests/unit/thumbnail/test_providers.py`

#### 6.2 Integration Tests
- `tests/integration/test_thumbnail_viewport.py`
- `tests/integration/test_thumbnail_sync.py`
- `tests/integration/test_video_preview.py`

#### 6.3 Performance Benchmarks
- Startup time with thumbnail background generation
- Memory usage with large file sets
- Disk cache hit rate

#### 6.4 Polish & Refinement
- QSS styling for thumbnail frames, badges
- Theme integration (light/dark modes)
- Accessibility (keyboard navigation tested)
- Error handling & fallbacks

---

## File Structure & Ownership

### New Files

```
oncutf/core/thumbnail/
├── __init__.py
├── thumbnail_cache.py          # ThumbnailCache, ThumbnailMemoryCache, ThumbnailDiskCache
├── thumbnail_manager.py         # ThumbnailManager, ThumbnailRequest
├── thumbnail_worker.py          # ThumbnailWorker (QThread)
├── providers.py                 # ThumbnailProvider (ABC), ImageThumbnailProvider, VideoThumbnailProvider
└── video_frame_extractor.py     # Video frame extraction logic (FFmpeg wrapper)

oncutf/ui/widgets/
├── thumbnail_viewport.py        # ThumbnailViewportWidget (QListView + custom model)
└── thumbnail_model.py           # Thin wrapper around FileTableModel for viewport

oncutf/ui/delegates/
└── thumbnail_delegate.py        # ThumbnailDelegate (QStyledItemDelegate)

oncutf/ui/dialogs/
└── video_preview_dialog.py      # VideoPreviewDialog with frame stepping

oncutf/core/database/
└── thumbnail_store.py           # ThumbnailStore (DB operations for cache + order)

tests/unit/thumbnail/
├── test_thumbnail_cache.py
├── test_thumbnail_manager.py
└── test_providers.py

tests/integration/
├── test_thumbnail_viewport.py
├── test_thumbnail_sync.py
└── test_video_preview.py
```

### Modified Files

```
oncutf/ui/viewport_specs.py                     # Update VIEWPORT_SPECS if needed
oncutf/controllers/ui/layout_controller.py      # Add ThumbnailViewportWidget to center panel (QStackedWidget)
oncutf/core/database/database_manager.py        # Inject ThumbnailStore
oncutf/core/database/migrations.py              # Add v4→v5 migration
oncutf/models/file_table/file_table_model.py    # Add method: reorder_by_manual_order()
```

---

## Database Schema Changes

### New Table: `thumbnail_cache`

```sql
CREATE TABLE thumbnail_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_mtime REAL NOT NULL,
    file_size INTEGER NOT NULL,
    cache_filename TEXT NOT NULL,      -- Safe disk filename
    video_frame_time REAL,              -- Frame time if video (seconds)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_path, file_mtime)
);

CREATE INDEX idx_thumbnail_cache_folder ON thumbnail_cache(folder_path);
```

### New Table: `thumbnail_order`

```sql
CREATE TABLE thumbnail_order (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL UNIQUE,
    file_paths TEXT NOT NULL,          -- JSON list of file paths in order
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_thumbnail_order_folder ON thumbnail_order(folder_path);
```

---

## Configuration

### New Config Keys (JSON)

```json
{
  "thumbnail": {
    "size_px": 128,                    # Current thumbnail size (64-256)
    "cache_location": "~/.cache/oncutf/thumbnails",
    "memory_cache_limit": 500,         # LRU max entries
    "video_frame_time_ratio": 0.35,    # Default: 35% of duration
    "quality_check_enabled": true,     # Skip dark/flat frames
    "background_generation": true      # Generate in worker thread
  }
}
```

---

## Key Design Decisions

### 1. QListView vs QGraphicsView
**Decision:** QListView (IconMode) with QStyledItemDelegate

**Rationale:**
- Native virtual scrolling (performance with 10k+ files)
- Built-in multi-select (Ctrl/Shift handling)
- Simpler to integrate with Qt models
- Lasso selection via QRubberBand + item rect intersection
- Zoom via delegate size change + model refresh

**Tradeoff:** Lasso requires manual item rect calculation and QItemSelection handling

### 0. Core Architecture Decisions

**Model Sharing:**
- Viewport and table use **same FileTableModel instance**
- No data duplication, no sync issues
- Order changes update model → both views update via signals

**Order Mode:**
- `FileTableModel.order_mode: Literal["manual", "sorted"]`
- Manual: drag reorder enabled, DB persistence
- Sorted: drag disabled, Qt sort active

**Database Design:**
- `thumbnail_order`: Normalized rows (folder, file, index)
  - Pros: Incremental updates, no JSON rewrites, consistency
  - Cons: More rows (acceptable for <10k files per folder)
- `thumbnail_cache`: One entry per (file_path, mtime, size)
  - UPDATE on file change, not INSERT (simpler)

**Rating System:**
- Deferred to Phase 6+ (requires DB schema + sync layer)
- Must coordinate: thumbnail UI → FileItem → file_table → metadata write

### 2. Manual Order Persistence
**Decision:** Store in SQLite (per folder) + restore on load

**Rationale:**
- Fast folder reload (no regeneration needed)
- Survives app restart
- Single source of truth (DB)
- Can be cleared per-folder without affecting others

**Alternative:** JSON file per folder (rejected: harder to query, less atomic)

### 3. Video Frame Heuristic
**Decision:** t = clamp(duration × 0.35, 2.0s, duration - 2.0s)

**Rationale:**
- 35% avoids black leader/credits (common at 0% and 100%)
- Clamp ensures 2-second margin for safety
- Fallback to 15%, 50%, 70% if frame too dark
- Simple to compute, good UX

### 4. Memory Cache with LRU
**Decision:** Max 500 entries (~50-100 MB depending on size)

**Rationale:**
- Balances performance (no reload) vs memory usage
- 500 is ~4 folders of 128 thumbnails each
- LRU eviction prevents unbounded growth
- Disk cache is persistent fallback

### 5. Color Flag Reuse
**Decision:** No new color system, use existing `FileItem.color`

**Rationale:**
- Already loaded in FileItem
- User-defined colors, unlimited palette
- No redundant storage
- Simpler implementation

---

## Error Handling

### Thumbnail Generation Failures
- **Dark/flat frames:** Try fallback times (15%, 50%, 70%)
- **FFmpeg not found:** Log warning, show placeholder
- **Disk full:** Log error, skip caching, show pixmap in memory only
- **Corrupt file:** Show error placeholder, allow retry

### Cache Invalidation
- **File modified (mtime changed):** Remove cache entry, regenerate
- **File deleted:** Remove cache entry from DB
- **Folder moved:** Cache entries become orphans (gc on startup)

### Selection Sync Failures
- **Model mismatch:** Fall back to individual sync per file
- **Selection model null:** Use row indices directly

---

## Performance Targets

- **Startup:** No UI freeze (thumbnail generation in background)
- **Viewport scroll:** 60 FPS (virtual scrolling + delegate caching)
- **Folder reload:** <500ms for cached thumbnails (DB lookup + pixmap load)
- **First thumbnail:** Generated within 100ms (FFmpeg extract)
- **Memory:** <100 MB for 500 cached thumbnails + app overhead
- **Disk cache:** < 500 MB for typical use (configurable)

---

## Backward Compatibility

- No changes to existing FileTableModel API
- Thumbnail viewport is opt-in (toggle button)
- Existing projects work without thumbnails (feature is additive)
- DB migration is automatic (v4 → v5)
- Old database remains functional (new tables don't affect existing data)

---

## Testing Checklist

### Phase 1-2: Core Infrastructure
- [ ] Single-file thumbnail generation
- [ ] Batch generation (100+ files)
- [ ] Video frame extraction (multiple codecs)
- [ ] Cache hit on second folder open
- [ ] Cache invalidation on file modification (mtime/size change)
- [ ] Normalized DB order: incremental updates work
- [ ] UPSERT logic: same file, different mtime → updates row

### Phase 3: UI & Interactions
- [ ] Manual drag-reorder persists to DB
- [ ] Sort modes toggle correctly (manual → sorted → manual)
- [ ] **Order mode flag:** drag disabled in sorted mode
- [ ] **Order mode flag:** drag enabled in manual mode
- [ ] Selection sync (table ↔ viewport)
- [ ] Color flag display
- [ ] Video duration badge
- [ ] Zoom in/out smoothly (64-256px)
- [ ] Pan navigation responsive
- [ ] Keyboard navigation (arrows, Home, End)
- [ ] **Lasso selection:** basic rectangle drag
- [ ] **Lasso selection:** scroll during lasso
- [ ] **Lasso selection:** layout change mid-drag
- [ ] **Lasso selection:** Ctrl+lasso (additive)
- [ ] Hover tooltip shows full filename
- [ ] Double-click opens file
- [ ] Right-click context menu

### Phase 3: UI Rendering & Interaction
- [ ] Status label updates from both viewports (FileTable + Thumbs)
- [ ] Metadata circle colors match theme: none=#404040, loaded=#51cf66 (green), extended=#fabf65 (orange)
- [ ] Hash circle colors match theme: none=#404040, hash=#ce93d8 (pink-purple)
- [ ] 2-circle spacing and positioning correct (8px margin, 4px apart)
- [ ] Color flag tints frame border and background
- [ ] Colored vs non-colored files visually distinct
- [ ] Multipurpose progress widget shows thumbnail generation
- [ ] Progress widget hides when generation complete
- [ ] Zoom slider functional (64-256px range)
- [ ] Zoom slider tooltip updates (no label)
- [ ] Zoom slider saves preference to config

### Phase 4-5: Integration & Persistence
- [ ] App restart preserves manual order
- [ ] Folder change clears manual order (or loads new folder's order)
- [ ] Theme switching (light/dark)
- [ ] High-DPI rendering (2x, 3x scales)
- [ ] Memory usage stays bounded (<100 MB for 500 thumbnails)
- [ ] Disk cache cleanup on app exit

### Phase 6: Future - Rating System
- [ ] **[DEFERRED]** Star rating display (0-5 stars, top-right overlay)
- [ ] **[DEFERRED]** Star rating keyboard shortcuts (0-5 keys, R to clear)
- [ ] **[DEFERRED]** Star rating context menu (submenu with 0-5 options)
- [ ] **[DEFERRED]** Sort by rating (high to low / low to high)
- [ ] **[DEFERRED]** Hide/show filters (unrated, below 1-4 stars)
- [ ] **[DEFERRED]** Rating sync: thumbnail UI → FileItem → file_table → metadata write

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| FFmpeg not installed | Graceful fallback (placeholder), clear user message in docs |
| Large video files slow extraction | Cache aggressively, allow user to skip generation, show progress |
| Unbounded disk cache | Cleanup on app exit, config max size, manual clear action |
| Model desynchronization | Sync both views on each file operation, unit tests for edge cases |
| Selection model null | Fallback to row indices, defensive checks |
| Memory leak (worker threads) | Worker thread cleanup in destructor, test with valgrind/heapdump |

---

## Future Enhancements (Out of Scope)

1. **Video Preview Dialog (Deferred from Phase 3):**
   - **File:** `oncutf/ui/dialogs/video_preview_dialog.py`
   - **Features:**
     - Display video with playback controls (play, pause, seek bar)
     - Frame-by-frame stepping (arrow keys or buttons)
     - Status bar showing current time / total duration
     - Context menu action: "Set This Frame as Thumbnail"
     - On action: Extract frame, save to cache, update DB, re-render viewport thumbnail
   - **Estimated effort:** 3-5 days
   - **Priority:** Medium (nice-to-have, not critical for Phase 3)

2. **Star Rating System (Phase 6+):**
   - Requires DB schema changes: `file_table.rating INTEGER DEFAULT 0`
   - FileItem dataclass extension: `rating: int = 0`
   - UI components: star overlay, shortcuts (0-5, R), context menu
   - Sync layer: thumbnail → FileItem → file_table → metadata write
   - Sort/filter by rating
   - **Estimated effort:** 1-2 weeks (storage + UI + sync)

3. **Conditional branching in graph:** Rule engine for folder-based organizing
4. **Metadata display:** Show exif fields as overlays on thumbnails (beyond star rating)
5. **Batch editing:** Select thumbnails → edit metadata/rename rules
6. **Slideshow mode:** Auto-advance through thumbnails
7. **Custom frame picker UI:** Visual timeline for video frame selection (enhanced version of #1)
8. **GPU rendering:** Use OpenGL for thumbnails (high-performance mode)
9. **Network drive support:** Cache network files locally
10. **Animated GIF thumbnails:** Show first 3 frames in carousel
11. **Half-star ratings:** 0.5 increments for more granular rating (requires rating system first)
12. **Tag-based filtering:** Combine rating filters with color flags (e.g., "3+ stars AND red flag")

---

