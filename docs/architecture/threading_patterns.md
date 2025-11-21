# OnCutF Threading Patterns Documentation

## Overview

OnCutF uses a **Qt-only threading model** for all concurrent operations. This document describes the three main threading patterns used throughout the application, their use cases, and implementation guidelines.

**Key Decision:** After comprehensive analysis (see [Concurrency Decision](./concurrency_decision.md)), the application uses Qt's threading primitives exclusively. The unused `AsyncOperationsManager` was removed in Task A5.

---

## Threading Patterns Summary

| Pattern | Use Case | Examples | Thread Management |
|---------|----------|----------|-------------------|
| **QThread Workers** | Long-running background tasks with progress | Hash calculation, metadata loading | Manual lifecycle |
| **ThreadPoolManager** | High-volume parallel work with priority | Batch operations, concurrent processing | Automatic pooling |
| **ThreadPoolExecutor** | Simple parallel batch processing | Batch file operations | Standard library |

---

## Pattern 1: QThread Workers

### Description

Custom `QThread` subclasses for long-running, cancellable background operations with real-time progress reporting.

### When to Use

- **Long-running operations** (>1 second) that need progress updates
- Operations requiring **user cancellation**
- Tasks that benefit from **real-time UI feedback**
- Operations with **complex state management**

### Architecture

```
┌─────────────────┐
│   MainWindow    │
│  (UI Thread)    │
└────────┬────────┘
         │ creates & connects signals
         ▼
┌─────────────────┐
│  QThread Worker │◄─── Implements run()
│  (Worker Thread)│
└────────┬────────┘
         │ emits signals
         ▼
    Qt Event Loop ──► UI Updates
```

### Implementation Examples

#### 1. HashWorker (`core/hash_worker.py`)

**Purpose:** Background CRC32 hash calculation with file-by-file progress tracking.

**Key Features:**
- Supports three operation modes: duplicates, comparison, checksums
- Smart cache checking before calculation
- Batch operations optimization
- Real-time size-based progress (`size_progress` signal)
- Cancellable with periodic checking

**Signals:**
```python
# Progress tracking
progress_updated = pyqtSignal(int, int, str)  # current_file, total_files, filename
size_progress = pyqtSignal("qint64", "qint64")  # bytes_processed, total_bytes

# Results
duplicates_found = pyqtSignal(dict)
checksums_calculated = pyqtSignal(dict)

# Control
finished_processing = pyqtSignal(bool)
error_occurred = pyqtSignal(str)
```

**Usage Pattern:**
```python
# Setup
worker = HashWorker(parent=main_window)
worker.setup_duplicate_scan(file_paths)

# Connect signals
worker.progress_updated.connect(self.update_progress_bar)
worker.duplicates_found.connect(self.handle_duplicates)
worker.finished_processing.connect(self.cleanup)

# Start
worker.start()

# Cancel if needed
worker.cancel()
worker.wait(5000)
```

**Thread Safety:**
- Uses `QMutex` for shared state protection
- `QMutexLocker` for RAII-style locking
- Periodic cancellation checks every N operations

#### 2. MetadataLoader Worker Pattern (`utils/metadata_loader.py`)

**Purpose:** Load EXIF/metadata via ExifTool in background thread.

**Key Features:**
- Persistent ExifTool process (`-stay_open True`)
- Extended scanning support (`-ee` flag)
- Smart caching to skip already-loaded metadata
- Integration with `PersistentMetadataCache`

**Threading Model:**
```python
# Thread creation (in direct_metadata_loader.py)
self._metadata_thread = QThread()
metadata_worker.moveToThread(self._metadata_thread)

# Connect lifecycle
self._metadata_thread.started.connect(metadata_worker.process)
metadata_worker.finished.connect(self._metadata_thread.quit)
metadata_worker.finished.connect(metadata_worker.deleteLater)
self._metadata_thread.finished.connect(lambda: setattr(self, '_metadata_thread', None))

# Start
self._metadata_thread.start()
```

**Important:** Uses `moveToThread()` pattern instead of subclassing `QThread` for simpler worker objects.

---

## Pattern 2: ThreadPoolManager

### Description

Advanced thread pool with priority-based task scheduling, dynamic sizing, and resource monitoring.

### When to Use

- **High-volume parallel work** (many small-to-medium tasks)
- Operations requiring **priority scheduling**
- Workloads needing **dynamic thread allocation**
- Tasks requiring **comprehensive monitoring**

### Architecture

```
┌──────────────────────────────────────────┐
│       ThreadPoolManager (QObject)        │
│  - Priority queue                        │
│  - Worker lifecycle management           │
│  - Resource monitoring                   │
└───────────┬──────────────────────────────┘
            │
            ├─► SmartWorkerThread 1 (QThread)
            ├─► SmartWorkerThread 2 (QThread)
            ├─► SmartWorkerThread 3 (QThread)
            └─► ... (dynamic pool size)
```

### Key Features

**Priority-Based Scheduling:**
```python
class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5
```

**Dynamic Pool Sizing:**
- Min threads: 2 (configurable)
- Max threads: CPU count × 2
- Auto-expand when queue > 10 tasks
- Auto-shrink when idle workers detected

**Resource Monitoring:**
- CPU usage tracking (`psutil`)
- Memory usage monitoring
- Task execution statistics
- Per-worker metrics

### Implementation Details

#### Task Submission

```python
# Get global instance
from core.thread_pool_manager import get_thread_pool_manager

pool = get_thread_pool_manager()

# Submit task with priority
success = pool.submit_task(
    task_id="hash_batch_001",
    function=calculate_batch_hashes,
    args=(file_paths,),
    kwargs={"algorithm": "crc32"},
    priority=TaskPriority.HIGH,
    callback=handle_completion
)
```

#### Monitoring & Statistics

```python
# Get pool statistics
stats = pool.get_stats()
# Returns: ThreadPoolStats(
#   active_threads=4,
#   queued_tasks=12,
#   completed_tasks=150,
#   failed_tasks=2,
#   average_execution_time=0.45,
#   cpu_usage_percent=67.5,
#   memory_usage_mb=245.3
# )

# Get individual worker stats
worker_stats = pool.get_worker_stats()
for worker_stat in worker_stats:
    print(f"Worker {worker_stat['worker_id']}: "
          f"{worker_stat['tasks_processed']} tasks, "
          f"avg {worker_stat['average_execution_time']:.2f}s")
```

#### Health Checking

```python
# Check pool health
health = pool.health_check()
# Returns: {
#   'healthy': True,
#   'total_workers': 4,
#   'active_workers': 3,
#   'queued_tasks': 8,
#   'total_tasks_processed': 450,
#   'failed_tasks': 3,
#   'last_error': None
# }
```

### Lifecycle Management

```python
# Initialization (usually in application startup)
from core.thread_pool_manager import initialize_thread_pool

pool = initialize_thread_pool(min_threads=2, max_threads=8)

# Shutdown (in application cleanup)
pool.shutdown()  # Waits for workers to finish
```

---

## Pattern 3: ThreadPoolExecutor (Standard Library)

### Description

Python's standard `concurrent.futures.ThreadPoolExecutor` for simple batch operations.

### When to Use

- **Simple parallel batch processing**
- No need for priority scheduling
- Standard Python patterns preferred
- Quick prototyping or simple utilities

### Implementation Example

#### BatchProcessor (`core/batch_processor.py`)

**Purpose:** Process large lists in parallel batches with automatic chunking.

```python
class BatchProcessor:
    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def process_batches(self, items: list[Any], processor_func: Callable) -> list[Any]:
        """Process items in batches with parallel execution."""
        batches = self._split_into_batches(items)
        
        # Submit all batches
        future_to_batch = {
            self.executor.submit(processor_func, batch): batch 
            for batch in batches
        }
        
        # Collect results as they complete
        results = []
        for future in as_completed(future_to_batch):
            batch_result = future.result()
            results.extend(batch_result)
        
        return results
```

**Usage:**
```python
processor = BatchProcessor(batch_size=100, max_workers=4)

def process_file_batch(batch):
    return [transform(item) for item in batch]

results = processor.process_batches(all_files, process_file_batch)
```

**Advantages:**
- Simple, familiar API
- Automatic result collection
- Exception handling with `future.result()`
- Standard library (no Qt dependencies)

**Limitations:**
- No priority scheduling
- No Qt signal integration
- Less control over worker lifecycle
- No progress tracking built-in

---

## Threading Pattern Decision Guide

Use this flowchart to choose the appropriate threading pattern:

```
Start
  │
  ├─► Need Qt signals & progress? ──Yes──► QThread Worker
  │                                         (HashWorker, MetadataLoader)
  │
  ├─► Need priority scheduling? ──Yes──► ThreadPoolManager
  │   OR resource monitoring?              (SmartWorkerThread)
  │
  ├─► Simple batch processing? ──Yes──► ThreadPoolExecutor
  │   No Qt integration needed?            (BatchProcessor)
  │
  └─► Default: ThreadPoolManager (most flexible)
```

### Pattern Comparison Matrix

| Criterion | QThread Worker | ThreadPoolManager | ThreadPoolExecutor |
|-----------|----------------|-------------------|--------------------|
| Progress Reporting | ★★★★★ | ★★★☆☆ | ☆☆☆☆☆ |
| Priority Scheduling | ☆☆☆☆☆ | ★★★★★ | ☆☆☆☆☆ |
| Resource Monitoring | ★★☆☆☆ | ★★★★★ | ☆☆☆☆☆ |
| Simplicity | ★★☆☆☆ | ★★★☆☆ | ★★★★★ |
| Qt Integration | ★★★★★ | ★★★★☆ | ☆☆☆☆☆ |
| Cancellation | ★★★★★ | ★★★☆☆ | ★★☆☆☆ |
| Dynamic Scaling | ☆☆☆☆☆ | ★★★★★ | ★★☆☆☆ |

---

## Best Practices & Guidelines

### 1. Thread Safety Rules

**Always protect shared state with QMutex:**
```python
from core.pyqt_imports import QMutex, QMutexLocker

class MyWorker(QThread):
    def __init__(self):
        super().__init__()
        self._mutex = QMutex()
        self._shared_data = []
    
    def safe_append(self, item):
        with QMutexLocker(self._mutex):
            self._shared_data.append(item)
```

**Use RAII-style locking (QMutexLocker):**
- Automatically releases lock when scope exits
- Exception-safe
- Prevents deadlocks from forgotten unlocks

### 2. Signal Usage Patterns

**Connect signals in UI thread:**
```python
# Good: connect in __init__ or setup method
worker.progress_updated.connect(self.update_ui)
worker.start()

# Bad: connecting after start() may miss early signals
worker.start()
worker.progress_updated.connect(self.update_ui)  # May miss signals!
```

**Use Qt::QueuedConnection for cross-thread signals:**
```python
# Automatic with pyqtSignal, but explicit when needed:
worker.finished.connect(self.cleanup, Qt.QueuedConnection)
```

### 3. Worker Lifecycle Management

**Always wait for workers to finish:**
```python
# Good: proper cleanup
worker.cancel()
worker.wait(5000)  # Wait up to 5 seconds
if worker.isRunning():
    worker.terminate()  # Last resort
    worker.wait(1000)

# Bad: immediate deletion
worker.cancel()
del worker  # May cause crashes!
```

**Use deleteLater() for Qt objects:**
```python
worker.finished.connect(worker.deleteLater)
```

### 4. Cancellation Pattern

**Implement cooperative cancellation:**
```python
class MyWorker(QThread):
    def __init__(self):
        super().__init__()
        self._cancelled = False
        self._mutex = QMutex()
    
    def cancel(self):
        with QMutexLocker(self._mutex):
            self._cancelled = True
    
    def run(self):
        for i, item in enumerate(items):
            # Check periodically (every N items)
            if i % 100 == 0:
                with QMutexLocker(self._mutex):
                    if self._cancelled:
                        return
            
            # Process item
            self.process(item)
```

**Never use QThread.terminate() unless absolutely necessary:**
- Can corrupt data
- May cause resource leaks
- Only for hung/frozen workers

### 5. Progress Reporting

**Update UI at reasonable intervals:**
```python
# Good: update every N items or every N milliseconds
if i % 10 == 0 or (time.time() - last_update) > 0.1:
    self.progress_updated.emit(i, total, current_file)

# Bad: update for every item
for item in items:
    self.progress_updated.emit(...)  # UI overload!
```

**Use size-based progress for better UX:**
```python
# Better than file count for mixed file sizes
self.size_progress.emit(bytes_processed, total_bytes)
```

### 6. Error Handling

**Always emit error signals:**
```python
def run(self):
    try:
        self.do_work()
        self.finished.emit(True)
    except Exception as e:
        logger.exception("Worker failed")
        self.error_occurred.emit(str(e))
        self.finished.emit(False)
```

**Handle errors in UI thread:**
```python
worker.error_occurred.connect(self.show_error_dialog)
```

### 7. Resource Management

**Monitor resource usage in long-running operations:**
```python
import psutil

def run(self):
    for i, item in enumerate(items):
        # Check memory periodically
        if i % 1000 == 0:
            memory_mb = psutil.virtual_memory().used / (1024 * 1024)
            if memory_mb > MEMORY_THRESHOLD:
                logger.warning(f"High memory usage: {memory_mb:.1f} MB")
                self.request_pause()
```

### 8. Testing Threading Code

**Use pytest-qt for threaded tests:**
```python
def test_worker_completion(qtbot):
    worker = HashWorker()
    worker.setup_duplicate_scan(test_files)
    
    # Wait for signal with timeout
    with qtbot.waitSignal(worker.finished_processing, timeout=5000):
        worker.start()
    
    # Cleanup
    worker.wait()
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Accessing UI from Worker Thread

**Problem:**
```python
# BAD: Direct UI access from worker thread
def run(self):
    self.parent().status_label.setText("Working...")  # CRASH!
```

**Solution:**
```python
# GOOD: Use signals to update UI
status_updated = pyqtSignal(str)

def run(self):
    self.status_updated.emit("Working...")  # Safe!

# In UI thread:
worker.status_updated.connect(self.status_label.setText)
```

### Pitfall 2: Forgetting to Start QThread

**Problem:**
```python
worker = MyWorker()
# Worker never runs - forgot to call start()!
```

**Solution:**
```python
worker = MyWorker()
worker.start()  # Don't forget!
```

### Pitfall 3: Memory Leaks from Circular References

**Problem:**
```python
worker = MyWorker()
worker.callback = lambda: self.process_result(worker)  # Circular ref!
```

**Solution:**
```python
# Use signals instead of callbacks
worker.result_ready.connect(self.process_result)

# Or use weak references
import weakref
worker.callback = lambda: self.process_result(weakref.ref(worker))
```

### Pitfall 4: Deadlocks from Nested Locking

**Problem:**
```python
def method_a(self):
    with QMutexLocker(self._mutex):
        self.method_b()  # Deadlock if method_b also locks!

def method_b(self):
    with QMutexLocker(self._mutex):
        ...
```

**Solution:**
```python
# Use recursive mutex
self._mutex = QMutex(QMutex.Recursive)

# Or restructure to avoid nested locking
def method_a(self):
    with QMutexLocker(self._mutex):
        data = self._shared_data
    self._method_b_unlocked(data)
```

---

## Performance Optimization Tips

### 1. Batch Small Operations

Instead of creating a thread per file:
```python
# Bad: 10,000 threads for 10,000 files
for file in files:
    worker = Worker(file)
    worker.start()

# Good: Process in batches
batch_size = 100
for i in range(0, len(files), batch_size):
    batch = files[i:i+batch_size]
    worker = Worker(batch)
    worker.start()
```

### 2. Reuse Thread Pools

```python
# Bad: Create new pool for each operation
def operation_a():
    pool = ThreadPoolManager()
    pool.submit_task(...)

def operation_b():
    pool = ThreadPoolManager()
    pool.submit_task(...)

# Good: Use singleton pattern
pool = get_thread_pool_manager()  # Global instance
```

### 3. Tune Worker Count to CPU

```python
import psutil

# CPU-bound tasks: workers = CPU count
cpu_count = psutil.cpu_count(logical=False)

# I/O-bound tasks: workers = CPU count × 2-4
io_workers = psutil.cpu_count() * 2
```

### 4. Profile Thread Contention

```python
# Add timing to identify bottlenecks
import time

def run(self):
    lock_wait_time = 0
    
    for item in items:
        start = time.time()
        with QMutexLocker(self._mutex):
            lock_wait_time += time.time() - start
            # Critical section
    
    logger.info(f"Lock wait time: {lock_wait_time:.2f}s")
```

---

## Migration Guide: Async to Qt Threading

If migrating from asyncio patterns to Qt threading:

| Asyncio Pattern | Qt Threading Equivalent |
|-----------------|------------------------|
| `async def func()` | `QThread.run()` |
| `await asyncio.sleep()` | `QThread.msleep()` |
| `asyncio.create_task()` | `worker.start()` |
| `asyncio.Queue` | `queue.Queue` + QMutex |
| `asyncio.Lock` | `QMutex` |
| Callback | `pyqtSignal` |

**Example Conversion:**

```python
# Before (asyncio)
async def process_files(self):
    for file in files:
        result = await self.process_file(file)
        await self.update_ui(result)

# After (Qt)
class FileWorker(QThread):
    result_ready = pyqtSignal(object)
    
    def run(self):
        for file in self.files:
            result = self.process_file(file)
            self.result_ready.emit(result)  # UI updates in main thread
```

---

## Future Considerations

### Potential Improvements

1. **Work-stealing queue** for better load balancing in ThreadPoolManager
2. **Thread-local storage** for expensive per-thread resources (e.g., ExifTool instances)
3. **Coroutine-style progress** using generators for cleaner progress tracking
4. **Thread pool warm-up** to avoid cold-start latency

### Not Recommended

- **Mixing asyncio and Qt threads** - architectural complexity outweighs benefits
- **Manual threading without Qt primitives** - loses signal integration
- **Subprocess for parallelism** - overhead too high for small tasks

---

## Reference Implementation Checklist

When implementing a new threaded operation, verify:

- [ ] Chose appropriate pattern (QThread/ThreadPool/Executor)
- [ ] All shared state protected with QMutex
- [ ] Signals defined and connected in UI thread
- [ ] Worker cleanup implemented (wait/deleteLater)
- [ ] Cancellation mechanism implemented
- [ ] Progress reporting at reasonable intervals
- [ ] Error handling with error signals
- [ ] No direct UI access from worker thread
- [ ] Resource usage monitored (for long operations)
- [ ] Tests written using pytest-qt

---

## Additional Resources

- **Qt Threading Documentation:** https://doc.qt.io/qt-5/threads-technologies.html
- **PyQt5 Threading Best Practices:** https://www.riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html
- **Python GIL Considerations:** https://realpython.com/python-gil/
- **Concurrency Decision Document:** [concurrency_decision.md](./concurrency_decision.md)
- **Progress Reporting Protocol:** See `core/progress_protocol.py`

---

## Conclusion

OnCutF's Qt-only threading model provides:
- **Consistent patterns** across all concurrent operations
- **Strong Qt integration** with signals and event loop
- **Flexible options** for different workload types
- **Production-tested** patterns with proper lifecycle management

Follow these patterns and guidelines to maintain thread safety, performance, and maintainability throughout the codebase.
