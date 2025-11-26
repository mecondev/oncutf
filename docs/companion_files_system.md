# Companion Files System

## Overview

OnCutF now includes comprehensive support for companion files (also known as sidecar files) - additional files created by cameras and other devices that contain metadata or settings related to your main media files.

## Supported Companion File Types

### Sony Camera Metadata Files
- **Pattern**: `C8227.MP4` → `C8227M01.XML`, `C8227M02.XML`
- **Content**: Video recording metadata, codec settings, creation dates, audio channels
- **Use case**: Professional Sony cameras create XML files with detailed recording parameters

### XMP Sidecar Files  
- **Pattern**: `IMG_1234.CR2` → `IMG_1234.xmp`
- **Content**: Image editing adjustments, keywords, ratings, color corrections
- **Use case**: RAW image processing applications (Lightroom, Capture One, etc.)

### Subtitle Files
- **Pattern**: `movie.mp4` → `movie.srt`, `movie.vtt`, `movie.ass`
- **Content**: Subtitle/caption text with timing information
- **Use case**: Video files with associated subtitles

### LUT Files (Future)
- **Pattern**: `video.mp4` → `video.cube`, `video.3dl`
- **Content**: Color grading lookup tables
- **Use case**: Professional video color correction

## Configuration Options

The companion files system is controlled by several settings in `config.py`:

```python
# Enable/disable companion file detection
COMPANION_FILES_ENABLED = True

# Control display in file table
SHOW_COMPANION_FILES_IN_TABLE = False  # Hide companions by default

# Automatic renaming behavior  
AUTO_RENAME_COMPANION_FILES = True     # Rename companions with main files

# Metadata loading from companions
LOAD_COMPANION_METADATA = True         # Extract metadata from companion files

# Display modes
CompanionFileMode = {
    "HIDE": "hide",           # Hide companion files (default)
    "SHOW": "show",           # Show companions in file list  
    "SHOW_GROUPED": "grouped" # Show grouped with main files (future)
}
```

## User Interface

### Companion Files Settings Widget

A dedicated settings widget (`CompanionFilesWidget`) allows users to control:

1. **Enable/Disable Detection**: Turn companion file handling on/off
2. **Display Options**: 
   - Hide companion files from file table (default)
   - Show companion files in file table
   - Show grouped with main files (planned feature)
3. **Behavior Settings**:
   - Automatically rename companions when main file is renamed
   - Load metadata from companion files for display
4. **Information Panel**: Explains what companion files are and shows examples

### Integration Points

- **File Loading**: Companion files are automatically detected and filtered based on settings
- **Metadata Display**: Companion metadata is merged into the main file's metadata view
- **Rename Operations**: Companion files follow main file renames automatically **even when hidden from UI**
- **File Table**: Companions can be hidden or shown based on user preference

### Invisible Companion Rename Feature

**Important**: Companion files are automatically renamed even when `SHOW_COMPANION_FILES_IN_TABLE = False`.

This behavior mirrors professional applications like Adobe Lightroom:

1. **User Experience**: 
   - User only sees main files (e.g., `C8227.MP4`) in the table
   - User renames main file to `Wedding_Ceremony.MP4`
   - Companion files (`C8227M01.XML`) are **silently renamed** to `Wedding_Ceremony M01.XML`
   - No user intervention required
   
2. **Benefits**:
   - Cleaner UI without visual clutter
   - Guarantees companions stay synchronized with main files
   - Prevents orphaned companion files
   - Professional workflow (similar to Lightroom XMP sidecars)

3. **How It Works**:
   ```
   BEFORE RENAME:
   /Videos/C8227.MP4           (visible in UI)
   /Videos/C8227M01.XML        (hidden from UI)
   
   USER ACTION: Rename C8227.MP4 → Wedding_2024.MP4
   
   AFTER RENAME:
   /Videos/Wedding_2024.MP4        (visible in UI)
   /Videos/Wedding_2024M01.XML     (hidden from UI, auto-renamed)
   ```

4. **Implementation Details**:
   - `UnifiedRenameEngine._build_execution_plan()` checks `AUTO_RENAME_COMPANION_FILES`
   - Companion renames are added to the execution plan automatically
   - The `_build_companion_execution_plan()` method scans folder for companions
   - Rename pairs are generated and executed alongside main file renames
   - No preview shown to user (mimics Lightroom behavior)

5. **Configuration**:
   ```python
   COMPANION_FILES_ENABLED = True         # Must be True
   AUTO_RENAME_COMPANION_FILES = True     # Must be True for invisible rename
   SHOW_COMPANION_FILES_IN_TABLE = False  # Companions hidden from UI
   ```

6. **Edge Cases**:
   - If main file rename fails, companion rename is also skipped
   - Conflict resolution applies to companion files (skip/overwrite)
   - Case-only renames are handled safely for both main and companion files

## Technical Implementation

### Core Components

1. **CompanionFilesHelper** (`utils/companion_files_helper.py`)
   - Pattern matching for different companion file types
   - Metadata extraction from companion files (Sony XML, XMP)
   - Rename pair generation for synchronized operations
   - File grouping and relationship detection

2. **Enhanced Metadata System**
   - `UnifiedMetadataManager.get_enhanced_metadata()`: Merges companion metadata
   - Companion metadata prefixed as `Companion:filename:field`
   - Preserves original metadata while adding companion data

3. **File Loading Integration**
   - `FileLoadManager._filter_companion_files()`: Filters based on settings
   - Automatic detection during folder loading
   - Respects display preferences

4. **Rename Engine Integration**
   - `UnifiedExecutionManager._build_companion_execution_plan()`: Adds companion renames
   - Synchronized renaming of main and companion files
   - Conflict resolution for companion files

### Metadata Extraction

#### Sony XML Files
Extracted fields:
- `duration_frames`: Video duration in frames
- `creation_date`: Recording timestamp
- `video_*`: Codec, frame rate, resolution, aspect ratio
- `audio_channels`: Number of audio channels

#### XMP Sidecar Files  
Extracted fields:
- `title`: Image title
- `description`: Image description  
- `keywords`: Keyword tags array

## Usage Examples

### Basic Usage
```python
# Load folder with companion files
file_paths = ["/path/to/C8227.MP4", "/path/to/C8227M01.XML"]

# Group files automatically
groups = CompanionFilesHelper.group_files_with_companions(file_paths)
# Result: {"/path/to/C8227.MP4": {"companions": ["/path/to/C8227M01.XML"], "type": "group"}}

# Find companions for specific file
companions = CompanionFilesHelper.find_companion_files(
    "/path/to/C8227.MP4", 
    file_paths
)
# Result: ["/path/to/C8227M01.XML"]
```

### Rename Operations
```python
# When renaming main file, companions follow
old_main = "/path/to/C8227.MP4"
new_main = "/path/to/Wedding_Ceremony.MP4" 
companions = ["/path/to/C8227M01.XML"]

rename_pairs = CompanionFilesHelper.get_companion_rename_pairs(
    old_main, new_main, companions
)
# Result: [("/path/to/C8227M01.XML", "/path/to/Wedding_CeremonyM01.XML")]
```

### Metadata Enhancement  
```python
# Enhanced metadata includes companion data
enhanced_metadata = metadata_manager.get_enhanced_metadata(file_item, folder_files)

# Companion fields are prefixed:
# "Companion:C8227M01.XML:duration_frames": "6024"
# "Companion:C8227M01.XML:video_aspectratio": "16:9"
```

## Benefits for Users

1. **Workflow Preservation**: Main and companion files stay synchronized
2. **Rich Metadata**: Access to detailed recording parameters from Sony cameras
3. **Clean Interface**: Companions can be hidden to reduce clutter
4. **Professional Support**: Handles industry-standard sidecar file formats
5. **Automatic Detection**: No manual intervention required
6. **Flexible Display**: Users can choose how companions are shown

## Real-World Example: Sony Camera Workflow

A typical Sony camera recording session produces:
```
C8227.MP4    (765 MB - main video file)
C8227M01.XML (2 KB - metadata: codec, frame rate, audio settings)

C8228.MP4    (906 MB - main video file) 
C8228M01.XML (2 KB - metadata: codec, frame rate, audio settings)

... 210 video files with 210 companion XML files
```

With OnCutF companion files support:
- **Loading**: Only 210 video files shown in table (XMLs hidden)
- **Metadata**: XML data merged into video metadata display
- **Renaming**: Rename "C8227.MP4" → "Wedding_Ceremony.MP4", XML becomes "Wedding_CeremonyM01.XML" automatically
- **Organization**: Both files stay together, maintaining professional workflow

## Future Enhancements

1. **Grouped Display Mode**: Show companions indented under main files
2. **More File Types**: Support for additional companion file formats
3. **Custom Patterns**: User-defined companion file patterns
4. **Batch Operations**: Apply operations to companion files independently
5. **Metadata Editing**: Edit companion file metadata directly
6. **Export Options**: Include/exclude companions in metadata exports

## Testing

Run the companion files test suite:
```bash
python test_companion_files.py
```

This tests:
- Sony XML file detection and parsing
- Pattern matching for various file types  
- Rename pair generation
- Metadata extraction accuracy

## Configuration Best Practices

### For Professional Video Workflows
```python
COMPANION_FILES_ENABLED = True
SHOW_COMPANION_FILES_IN_TABLE = False      # Keep interface clean
AUTO_RENAME_COMPANION_FILES = True         # Maintain sync
LOAD_COMPANION_METADATA = True             # Access technical details
```

### For Photography Workflows
```python  
COMPANION_FILES_ENABLED = True
SHOW_COMPANION_FILES_IN_TABLE = True       # Show XMP files
AUTO_RENAME_COMPANION_FILES = True         # Sync renames
LOAD_COMPANION_METADATA = True             # Access editing data
```

### For Minimal Setups
```python
COMPANION_FILES_ENABLED = False            # Disable if not needed
```

The companion files system provides OnCutF users with professional-grade file management capabilities while maintaining the application's focus on simplicity and efficiency.