# Concurrency Components Inventory

**Date:** November 21, 2025
**Purpose:** Complete inventory of all threading, async, worker and timer components in oncutf

---

## 1. Qt Thread-Based Components

### 1.1 Thread Pool Manager
**File:** `core/thread_pool_manager.py` (577 lines)

**Key Classes:**
- `ThreadPoolManager` - Main thread pool coordinator
- `WorkerTask` - Task representation with priority
- `PriorityQueue` - Priority-based task scheduling
- `ThreadPoolStats` - Performance metrics

**Features:**
- Dynamic thread pool sizing based on workload
- Priority-based task scheduling (CRITICAL, HIGH, NORMAL, LOW, BACKGROUND)
- Resource-aware thread allocation using psutil
- Work stealing for load balancing
- Thread pool monitoring and statistics
- QMutex/QMutexLocker for synchronization

**Signals:**
- `task_completed(task_id, result)`
- `task_failed(task_id, error)`

**Current State:** Primary concurrency model, well-implemented

---

### 1.2 Hash Worker
**File:** `core/hash_worker.py`

**Purpose:** Calculate file hashes (CRC32) in background thread

**Pattern:** QThread-based worker
- Extends QObject for signal/slot communication
- Runs in separate QThread
- Reports progress via signals

**Signals:**
- `progress(current, total)`
- `finished(results)`
- `error(message)`

**Used By:** Hash calculation operations, duplicate detection

**Current State:** Stable, follows Qt pattern

---

### 1.3 Metadata Worker
**File:** `widgets/metadata_worker.py`

**Purpose:** Load metadata from ExifTool in background

**Pattern:** QThread-based worker
- Similar to hash_worker pattern
- Integrates with ExifToolWrapper
- Progress reporting with file count and byte size

**Signals:**
- `progress(current, total)` - File count progress
- `size_progress(processed_bytes, total_bytes)` - Size progress
- `finished()`
- `error(message)`

**Used By:** Metadata loading operations triggered by drag/drop or user actions

**Current State:** Functional, but multiple metadata loading paths exist

---

### 1.4 Metadata Loader (Utility)
**File:** `utils/metadata_loader.py`

**Purpose:** High-level metadata loading with threading

**Pattern:** Creates and manages metadata workers
- Factory for metadata workers
- Handles progress dialogs
- Integrates with persistent cache

**Features:**
- Batch metadata loading
- Progress tracking
- Error handling
- Cache integration

**Current State:** Overlaps with metadata_worker.py, potential consolidation opportunity

---

## 2. Asyncio-Based Components

### 2.1 Async Operations Manager
**File:** `core/async_operations_manager.py`

**Key Classes:**
- `AsyncOperationsManager` - Main asyncio coordinator
- Runs asyncio event loop in separate Python thread (not QThread)

**Features:**
- Dedicated event loop in background thread
- Task management with cancellation support
- Integration with Qt signals for results
- Executor for CPU/IO-bound tasks

**Methods:**
- `run_async_task(coro, callback)`
- `run_batch_async(tasks, batch_size, callback)`
- `cancel_all_tasks()`
- `shutdown(timeout)`

**Signals:**
- `task_completed(task_id, result)`
- `task_failed(task_id, error)`
- `progress_update(current, total)`

**Current Usage:** Underutilized - unclear which operations actually use it

**Issues:**
- Separate from Qt thread model
- Complex shutdown coordination required
- Mixing Qt signals with asyncio adds complexity

**Current State:** Present but not heavily used, candidate for removal/simplification

---

## 3. Timer Management

### 3.1 Timer Manager
**File:** `utils/timer_manager.py`

**Purpose:** Centralized QTimer management with consolidation

**Key Classes:**
- `TimerManager` - Singleton timer coordinator
- `TimerType` - Enum for timer categorization
- `TimerPriority` - Priority levels

**Features:**
- Timer consolidation (prevents duplicate timers for same operation)
- Priority-based scheduling
- Automatic cleanup
- Statistics tracking
- Cancellation by type or all

**Timer Types:**
- `GENERIC` - General purpose
- `UI_UPDATE` - UI refresh operations
- `PREVIEW_UPDATE` - Preview regeneration
- `METADATA_LOAD` - Metadata operations
- `FILE_OPERATION` - File system operations
- `DRAG_CLEANUP` - Drag & drop cleanup
- `SCROLL_ADJUST` - Scroll position adjustments
- `COLUMN_RESIZE` - Column width persistence (7-second delay)

**Usage Pattern:**
```python
from utils.timer_manager import get_timer_manager, TimerType
get_timer_manager().schedule(callback, delay=100, timer_type=TimerType.UI_UPDATE)
```

**Current State:** Well-designed, prevents UI flooding, widely used

---

## 4. ExifTool Process Management

### 4.1 ExifTool Wrapper
**File:** `utils/exiftool_wrapper.py` (530 lines)

**Purpose:** Manage persistent ExifTool process with `-stay_open` mode

**Pattern:** Process-based concurrency
- `subprocess.Popen` with persistent process
- Threading lock for thread-safe access
- Batch operations for efficiency

**Features:**
- Persistent process for fast repeated calls
- Thread-safe operation (threading.Lock)
- Batch metadata extraction (10x faster)
- Fallback to one-shot subprocess for extended metadata
- Automatic cleanup on destruction

**Key Methods:**
- `get_metadata(file_path, use_extended)` - Single file
- `get_metadata_batch(file_paths, use_extended)` - Batch processing
- `close()` - Graceful shutdown
- `force_cleanup_all_exiftool_processes()` - Emergency cleanup (static)

**Issues:**
- No health check mechanism
- Process restart not automatic on failure
- Timeout handling exists but could be improved

**Current State:** Critical component, needs health monitoring

---

## 5. Preview & Caching Components

### 5.1 Preview Manager
**File:** `core/preview_manager.py` (324 lines)

**Purpose:** Generate preview names with caching

**Concurrency Aspects:**
- Caching with TTL (100ms) to reduce computation
- Per-key timestamps for cache validity
- Sequential file processing (potential parallelization opportunity)

**Current State:** No threading, runs on main thread, relies on caching for performance

---

### 5.2 Unified Rename Engine
**File:** `core/unified_rename_engine.py`

**Concurrency Aspects:**
- SmartCacheManager with TTL-based caching
- BatchQueryManager for efficient database queries
- Sequential processing (no threading)

**Current State:** Main thread only, could benefit from parallel processing for large file sets

---

## 6. Manager Components with Threading Implications

### 6.1 Metadata Manager
**File:** `core/metadata_manager.py` (980 lines)

**Threading Usage:**
- Creates metadata workers (QThread-based)
- Manages worker lifecycle
- Coordinates with dialogs and progress reporting

**Key Attributes:**
- `metadata_thread` - QThread instance
- `metadata_worker` - Worker instance
- `_metadata_cancelled` - Cancellation flag

**Cleanup Pattern:**
```python
def cleanup(self):
    # 1. Cancel any ongoing operations
    # 2. Stop and wait for thread
    # 3. Clean up worker
    # 4. Close ExifTool wrapper
    # 5. Force cleanup as last resort
```

**Current State:** Complex cleanup logic, multiple code paths

---

### 6.2 File Load Manager
**File:** `core/file_load_manager.py`

**Threading Implications:**
- Triggers metadata loading (which uses threads)
- Coordinates with drag operations
- Manages progress dialogs

**Current State:** Orchestrator, delegates threading to metadata components

---

## 7. Database Components

### 7.1 Database Manager
**File:** `core/database_manager.py`

**Threading Aspects:**
- Thread-local connections via `get_connection()`
- SQLite with WAL mode for concurrency
- Connection pooling

**Pattern:** Thread-safe database access
```python
def get_connection(self):
    thread_id = threading.get_ident()
    # Return thread-local connection
```

**Current State:** Properly handles multi-threaded access

---

## 8. Shutdown Sequence Analysis

### Current Shutdown Flow

**main.py:**
```python
# On exit (atexit.register)
def cleanup_on_exit():
    ExifToolWrapper.force_cleanup_all_exiftool_processes()
```

**main_window.py:**
```python
# closeEvent() or application exit
1. metadata_manager.cleanup()
2. ExifToolWrapper cleanup
3. app.quit()
```

### Issues Identified:
1. **No coordinated shutdown** - Each component cleans up independently
2. **No timeout handling** - Waits indefinitely for threads
3. **No order guarantee** - Parallel shutdowns may conflict
4. **Limited visibility** - No logging of shutdown progress

### Proposed Shutdown Order:
1. Cancel all pending timers (TimerManager)
2. Cancel async tasks if keeping asyncio (AsyncOperationsManager)
3. Request thread pool shutdown (ThreadPoolManager)
4. Wait for workers with timeout (metadata, hash)
5. Close database connections (DatabaseManager)
6. Terminate ExifTool processes (ExifToolWrapper)
7. Final cleanup verification

---

## 9. Concurrency Patterns Summary

### Active Patterns:

1. **Qt Thread Pool (Primary)**
   - Used for: CPU-intensive operations
   - Implementation: `ThreadPoolManager`
   - State: Well-implemented, primary pattern

2. **QThread Workers**
   - Used for: Metadata loading, hash calculation
   - Implementations: `metadata_worker.py`, `hash_worker.py`
   - State: Functional, standard Qt pattern

3. **Asyncio Event Loop (Underutilized)**
   - Used for: Unclear, minimal usage found
   - Implementation: `AsyncOperationsManager`
   - State: Candidate for removal/simplification

4. **Process-Based (ExifTool)**
   - Used for: External tool integration
   - Implementation: `exiftool_wrapper.py`
   - State: Critical, needs health monitoring

5. **Timer Consolidation**
   - Used for: UI updates, debouncing
   - Implementation: `TimerManager`
   - State: Well-designed, prevents flooding

### Anti-Patterns Identified:

1. **Multiple Loader Paths**
   - `metadata_loader.py` vs `direct_metadata_loader.py` vs worker creation in managers
   - Recommendation: Consolidate to single pattern

2. **Dual Concurrency Models**
   - Qt threads AND asyncio increases complexity
   - Recommendation: Standardize on Qt threads

3. **No Health Monitoring**
   - Workers and processes can fail silently
   - Recommendation: Add health check APIs

4. **Complex Shutdown**
   - No coordinator, each component independent
   - Recommendation: Create shutdown coordinator

---

## 10. Recommendations Summary

### High Priority:
1. ✅ Create shutdown coordinator (`core/shutdown_coordinator.py`)
2. ✅ Add health check APIs to critical components
3. ✅ Decide on asyncio usage (keep or remove)
4. ✅ Consolidate metadata loading paths

### Medium Priority:
5. ✅ Standardize progress reporting interface
6. ✅ Document threading patterns
7. ✅ Add timeout handling to all waits

### Low Priority:
8. ✅ Consider parallel preview generation for large file sets
9. ✅ Add performance monitoring for thread pool

---

## 11. Metrics & Statistics

### Current Thread Usage Estimate:
- Main UI thread: 1
- Thread pool workers: 2-8 (dynamic, based on CPU cores)
- Metadata worker threads: 0-1 (on demand)
- Hash worker threads: 0-1 (on demand)
- Asyncio event loop thread: 0-1 (if async_operations_manager active)
- ExifTool process: 1 (persistent subprocess)

**Total: 5-13 threads/processes** (depends on active operations)

### Timer Usage:
- Active timers: Varies, typically 0-5
- Timer types: 8 categories
- Consolidation prevents timer explosion

### Database Connections:
- Thread-local connections
- WAL mode supports concurrent reads
- Single writer at a time

---

## Conclusion

The oncutf application uses a **dual concurrency model** with Qt threads as primary and asyncio as secondary (underutilized). Key findings:

**Strengths:**
- Well-designed ThreadPoolManager
- Proper signal/slot communication
- Timer consolidation prevents UI flooding
- Thread-safe database access

**Weaknesses:**
- Dual concurrency models add complexity
- No coordinated shutdown
- No health monitoring
- Multiple overlapping loader implementations

**Next Steps:** Proceed to Task A2 (Health Check API)
