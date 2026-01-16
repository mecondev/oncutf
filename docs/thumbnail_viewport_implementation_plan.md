<!-- 
Thumbnail Viewport Implementation Plan

Author: Michael Economou
Date: 2026-01-16

A comprehensive plan for implementing the Thumbnail Viewport as an integrated browsing/ordering UI
alongside the existing file table, with manual ordering support and persistent caching.
-->

# Thumbnail Viewport Implementation Plan

## Overview

Implement a second viewport (alongside the existing table view) that displays files as a grid of thumbnails with integrated manual ordering, selection, and sorting capabilities. The viewport will:

- Display image and video thumbnails in a grid layout
- Support manual drag-reorder with order persistence per folder
- Integrate with existing file table (shared model, synchronized state)
- Cache thumbnails persistently (disk + SQLite DB) for fast folder reload
- Generate thumbnails in background threads without UI freeze

**Status:** Planning  
**Priority:** High  
**Estimated Duration:** 5-7 weeks (phased implementation)

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

### Phase 1: Core Infrastructure (Week 1-2)

#### 1.1 Thumbnail Cache System
- **File:** `oncutf/core/thumbnail/thumbnail_cache.py`
- **Classes:**
  - `ThumbnailCacheConfig` - Settings (size, location, TTL)
  - `ThumbnailDiskCache` - Disk storage management
  - `ThumbnailMemoryCache` - LRU in-memory cache (500 entries max)
  - `ThumbnailCache` - Orchestrator combining both

**Responsibilities:**
- Store/retrieve thumbnails from `~/.cache/oncutf/thumbnails/`
- Maintain file identity: `hash(file_path + mtime + size)` → safe filename
- Invalidate when file modified (mtime check)
- LRU eviction when memory cache exceeds 500 entries

#### 1.2 Thumbnail DB Store
- **File:** `oncutf/core/database/thumbnail_store.py`
- **Table:** `thumbnail_cache` (add via migration)
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
    UNIQUE(file_path, file_mtime)  -- Invalidate on change
  )
  
  CREATE TABLE thumbnail_order (
    id INTEGER PRIMARY KEY,
    folder_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    UNIQUE(folder_path, file_path)
  )
  ```

**Methods:**
- `get_cached_path(file_path, mtime) -> str | None`
- `save_cache_entry(file_path, mtime, size, cache_filename, video_frame_time)`
- `invalidate_entry(file_path)`
- `get_folder_order(folder_path) -> list[file_path]`
- `update_folder_order(folder_path, ordered_paths)`

#### 1.3 Thumbnail Providers (Abstract)
- **File:** `oncutf/core/thumbnail/providers.py`
- **Classes:**
  - `ThumbnailProvider` (ABC)
  - `ImageThumbnailProvider` - QImage reader for image files
  - `VideoThumbnailProvider` - FFmpeg for video frames

**Responsibilities:**
- Load/process file → QPixmap (constrained size)
- Video: Extract frame at t = clamp(duration * 0.35, 2.0, duration - 2.0)
- Quality check: reject frames with luma < 10 or contrast < 5 (fallback to 15%, 50%, 70%)
- Return QPixmap or raise `ThumbnailGenerationError`

---

### Phase 2: Thumbnail Manager & Generation (Week 2-3)

#### 2.1 Thumbnail Manager
- **File:** `oncutf/core/thumbnail/thumbnail_manager.py`
- **Classes:**
  - `ThumbnailRequest` - Queued request (file path, folder, preferred size)
  - `ThumbnailManager` - Orchestrator

**Responsibilities:**
- Accept requests from UI
- Check cache (memory → disk → DB)
- Queue for background generation if missing
- Emit signals: `thumbnail_ready(file_path, pixmap)`, `generation_progress(completed, total)`
- Handle errors gracefully (return placeholder)

#### 2.2 Thumbnail Worker
- **File:** `oncutf/core/thumbnail/thumbnail_worker.py`
- **Worker Thread:** Generate thumbnails asynchronously

**Responsibilities:**
- Process queue of `ThumbnailRequest` objects
- Call appropriate provider (image vs video)
- Save to disk cache + update DB
- Emit `thumbnail_ready` signal to UI
- Batch progress updates (every 10 items)

---

### Phase 3: UI Layer - Thumbnail Viewport (Week 3-4)

#### 3.1 Thumbnail Delegate
- **File:** `oncutf/ui/delegates/thumbnail_delegate.py`
- **Class:** `ThumbnailDelegate(QStyledItemDelegate)`

**Rendering:**
- Rectangle frame (photo slide style, ~3px border)
- Thumbnail centered with aspect ratio fit
- Filename word-wrapped below (Qt.TextWordWrap)
- Color flag circle (top-left, 12px diameter)
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
- QListView (IconMode, QAbstractItemModel view)
- Custom model wrapping `FileTableModel.files`
- Delegate set from Phase 3.1

**Features:**
- **Zoom:** Mouse wheel (Ctrl+wheel if scroll used for pan)
  - Min 64px, Max 256px thumbnail size
  - Save preference to config
- **Pan:** Middle mouse button drag
- **Selection:**
  - Ctrl+Click: Toggle individual thumbnail
  - Shift+Click: Range select
  - Lasso: Drag on empty space draws rectangle, selects intersecting thumbnails
  - Visual sync with FileTable (shared selection model if available)
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
  - File operations (same as table context menu): Open, Rename, Delete, etc.
- **Keyboard Navigation:**
  - Arrow keys: Move selection
  - Home/End: Jump to start/end
  - PageUp/PageDown: Scroll viewport

#### 3.3 Video Preview Dialog
- **File:** `oncutf/ui/dialogs/video_preview_dialog.py`
- **Class:** `VideoPreviewDialog(QDialog)`

**Features:**
- Display video with playback controls (play, pause, seek bar)
- Frame-by-frame stepping (arrow keys or buttons)
- Status bar showing current time / total duration
- Context menu action: "Set This Frame as Thumbnail"
  - On action: Extract frame, save to cache, update DB, re-render viewport thumbnail

---

### Phase 4: Integration & Sync (Week 4-5)

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
- **Default Mode:** Manual order (as loaded from DB or folder scan order)
- **Sort Menu Actions:**
  - **Sort Ascending:** `files.sort(key=lambda f: f.filename.lower())`
  - **Sort Descending:** `files.sort(key=lambda f: f.filename.lower(), reverse=True)`
  - **Sort by Color:** `files.sort(key=lambda f: (f.color == "none", f.color))`
  - **Sort by Folder:** If applicable, group by parent folder
- **After Sort:** Clear manual order DB entry (user switched to deterministic sort)
- **Return to Manual:** Click "Manual Order" → manual mode, load saved order or restore previous

---

### Phase 5: Database Migrations (Week 5-6)

#### 5.1 Migration Script
- **File:** `oncutf/core/database/migrations.py`
- Add migration: v4 → v5
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

### Phase 6: Testing & Polish (Week 6-7)

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
- Lasso selection via custom event handler in viewport
- Zoom via delegate size change + model refresh

**Tradeoff:** Lasso requires more manual implementation vs QGraphicsView

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

- [ ] Single-file thumbnail generation
- [ ] Batch generation (100+ files)
- [ ] Video frame extraction (multiple codecs)
- [ ] Cache hit on second folder open
- [ ] Manual drag-reorder persists
- [ ] Sort modes toggle correctly
- [ ] Selection sync (table ↔ viewport)
- [ ] Color flag display
- [ ] Video duration badge
- [ ] Zoom in/out smoothly
- [ ] Pan navigation responsive
- [ ] Keyboard navigation (arrows, Home, End)
- [ ] Lasso selection
- [ ] Hover tooltip shows full filename
- [ ] Double-click opens file
- [ ] Right-click context menu
- [ ] Video preview dialog
- [ ] Frame-by-frame stepping
- [ ] "Set as Thumbnail" action
- [ ] App restart preserves manual order
- [ ] Folder change clears manual order
- [ ] Theme switching (light/dark)
- [ ] High-DPI rendering
- [ ] Memory usage stays bounded
- [ ] Disk cache cleanup on app exit

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

1. **Conditional branching in graph:** Rule engine for folder-based organizing
2. **Metadata display:** Show exif fields as overlays on thumbnails
3. **Batch editing:** Select thumbnails → edit metadata/rename rules
4. **Slideshow mode:** Auto-advance through thumbnails
5. **Custom frame picker UI:** Visual timeline for video frame selection
6. **GPU rendering:** Use OpenGL for thumbnails (high-performance mode)
7. **Network drive support:** Cache network files locally
8. **Animated GIF thumbnails:** Show first 3 frames in carousel

---

