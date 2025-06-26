# Progress Manager System

## Επισκόπηση

Το νέο ProgressManager σύστημα παρέχει ένα ενοποιημένο API για το progress tracking σε όλες τις file operations της εφαρμογής ONCUTF.

## Αρχιτεκτονική

### ProgressManager Class

Ο `ProgressManager` είναι η κύρια κλάση που ενοποιεί όλες τις progress operations:

```python
from widgets.progress_manager import ProgressManager

# Δημιουργία manager για hash operations
hash_manager = ProgressManager("hash", parent)

# Δημιουργία manager για metadata operations
metadata_manager = ProgressManager("metadata", parent)

# Δημιουργία manager για copy operations (future)
copy_manager = ProgressManager("copy", parent)
```

### Υποστηριζόμενες Operations

- **hash**: Size-based progress με real-time tracking για CRC32 calculations
- **metadata**: Count-based progress με optional size tracking για metadata loading
- **copy**: Size-based progress για file operations (future)

## API Reference

### Constructor

```python
ProgressManager(operation_type: str, parent: Optional[QWidget] = None)
```

**Parameters:**
- `operation_type`: Τύπος operation ("hash", "metadata", "copy")
- `parent`: Parent widget (optional)

### Methods

#### start_tracking()

```python
start_tracking(total_size: int = 0, total_files: int = 0)
```

Ξεκινάει το progress tracking με τα κατάλληλα parameters.

**Parameters:**
- `total_size`: Συνολικό μέγεθος σε bytes (για size-based operations)
- `total_files`: Συνολικός αριθμός αρχείων (για count-based operations)

#### update_progress()

```python
update_progress(file_count: int = 0, total_files: int = 0,
               processed_bytes: int = 0, total_bytes: int = 0,
               filename: str = "", status: str = "")
```

Ενημερώνει το progress με unified API.

**Parameters:**
- `file_count`: Τρέχων αριθμός επεξεργασμένων αρχείων
- `total_files`: Συνολικός αριθμός αρχείων
- `processed_bytes`: Επεξεργασμένα bytes (cumulative)
- `total_bytes`: Συνολικό μέγεθος σε bytes
- `filename`: Τρέχον όνομα αρχείου
- `status`: Status message

#### reset()

```python
reset()
```

Επαναφέρει το progress tracking.

#### get_widget()

```python
get_widget() -> ProgressWidget
```

Επιστρέφει το underlying progress widget.

#### is_tracking()

```python
is_tracking() -> bool
```

Ελέγχει αν το progress tracking είναι ενεργό.

## Factory Functions

Για ευκολία, παρέχονται factory functions:

```python
from widgets.progress_manager import (
    create_hash_progress_manager,
    create_metadata_progress_manager,
    create_copy_progress_manager
)

# Δημιουργία managers
hash_manager = create_hash_progress_manager(parent)
metadata_manager = create_metadata_progress_manager(parent)
copy_manager = create_copy_progress_manager(parent)
```

## Usage Examples

### Hash Operations

```python
# Δημιουργία manager
manager = ProgressManager("hash", parent)

# Ξεκίνημα tracking
manager.start_tracking(total_size=1000000000)  # 1GB

# Ενημέρωση progress
manager.update_progress(
    processed_bytes=500000000,  # 500MB
    filename="large_file.mov",
    status="Calculating CRC32 hash..."
)
```

### Metadata Operations

```python
# Δημιουργία manager
manager = ProgressManager("metadata", parent)

# Ξεκίνημα tracking
manager.start_tracking(total_files=100, total_size=50000000)

# Ενημέρωση progress
manager.update_progress(
    file_count=50,
    total_files=100,
    processed_bytes=25000000,
    filename="photo.jpg",
    status="Loading metadata..."
)
```

### Copy Operations (Future)

```python
# Δημιουργία manager
manager = ProgressManager("copy", parent)

# Ξεκίνημα tracking
manager.start_tracking(total_size=500000000)  # 500MB

# Ενημέρωση progress
manager.update_progress(
    processed_bytes=250000000,  # 250MB
    filename="video.mp4",
    status="Copying file..."
)
```

## Migration Guide

### Από το παλιό σύστημα

**Παλιό:**
```python
from widgets.progress_widget import create_size_based_progress_widget

widget = create_size_based_progress_widget(parent)
widget.start_progress_tracking(total_size)
widget.update_progress(processed_bytes=bytes, total_bytes=total)
```

**Νέο:**
```python
from widgets.progress_manager import create_hash_progress_manager

manager = create_hash_progress_manager(parent)
manager.start_tracking(total_size=total_size)
manager.update_progress(processed_bytes=bytes)
```

### Benefits

1. **Unified API**: Ένα API για όλες τις operations
2. **Automatic Mode Selection**: Αυτόματη επιλογή mode βάσει operation type
3. **Better Error Handling**: Καλύτερο error handling και validation
4. **Future Ready**: Έτοιμο για νέες operations (copy, move, etc.)
5. **Cleaner Code**: Λιγότερος duplicate code

## Implementation Details

### Progress Widget Integration

Ο ProgressManager χρησιμοποιεί το υπάρχον ProgressWidget ως backend:

- **Hash operations**: Χρησιμοποιεί size-based progress mode
- **Metadata operations**: Χρησιμοποιεί count-based progress mode με optional size tracking
- **Copy operations**: Χρησιμοποιεί size-based progress mode

### Throttling

Το throttling γίνεται στο ProgressWidget level για optimal performance:
- 50ms updates για small files
- 100ms updates για large files
- Real-time updates για files >100MB

### Thread Safety

Ο ProgressManager είναι thread-safe και μπορεί να χρησιμοποιηθεί από worker threads.

## Testing

Τα tests βρίσκονται στο `tests/test_progress_manager.py`:

```bash
python -m pytest tests/test_progress_manager.py -v
```

## Future Enhancements

1. **Copy Operations**: Full support για file copy operations
2. **Move Operations**: Support για file move operations
3. **Batch Operations**: Support για batch file operations
4. **Custom Operations**: Support για custom operation types
5. **Progress Persistence**: Save/restore progress state
