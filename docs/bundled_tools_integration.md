<!-- 
Bundled Tools Integration - Technical Documentation

Author: Michael Economou
Date: 2026-01-16

Documentation for bundled exiftool/ffmpeg integration with PyInstaller support.
-->

# Bundled Tools Integration

## Overview

Η εφαρμογή χρησιμοποιεί **bundled binaries** για exiftool και ffmpeg αντί να βασίζεται στο system PATH. Αυτό επιτρέπει:

- **Standalone distribution**: Η εφαρμογή λειτουργεί χωρίς εξαρτήσεις
- **Cross-platform consistency**: Ελεγχόμενες εκδόσεις εργαλείων
- **PyInstaller compatibility**: Αυτόματο bundling σε installers

---

## Architecture

### Tool Resolution Priority

1. Bundled binaries (bin/<platform>/)
   ↓ (if not found)
2. System PATH
   ↓ (if not found)
3. FileNotFoundError

### File Structure

```tree
oncutf/
├── bin/
│   ├── linux/
│   │   ├── exiftool
│   │   └── ffmpeg
│   ├── macos/
│   │   ├── exiftool        # Universal binary
│   │   └── ffmpeg
│   └── windows/
│       ├── exiftool.exe
│       └── ffmpeg.exe
│
├── oncutf/
│   └── utils/
│       └── shared/
│           └── external_tools.py  # Tool detection & path resolution
│
└── oncutf/
    ├── core/
    │   └── thumbnail/
    │       └── providers.py       # VideoThumbnailProvider (uses ffmpeg)
    └── utils/
        └── shared/
            └── exiftool_wrapper.py  # ExifToolWrapper (uses exiftool)
```

---

## Integration Points

### 1. ExifToolWrapper (Metadata Extraction)

**File:** `oncutf/utils/shared/exiftool_wrapper.py`

**Changes:**

```python
def __init__(self) -> None:
    # OLD: Hardcoded "exiftool"
    # self.process = subprocess.Popen(["exiftool", ...])
    
    # NEW: Use bundled tool
    from oncutf.utils.shared.external_tools import ToolName, get_tool_path
    
    exiftool_path = get_tool_path(ToolName.EXIFTOOL, prefer_bundled=True)
    self.process = subprocess.Popen([exiftool_path, ...])
    self._exiftool_path = exiftool_path  # Store for subprocess.run calls
```

**All subprocess calls updated:**

- `_get_metadata_fast()` → uses `self._exiftool_path`
- `_get_metadata_extended()` → uses `self._exiftool_path`
- `get_metadata_batch()` → uses `self._exiftool_path`
- `write_metadata()` → uses `self._exiftool_path`

### 2. VideoThumbnailProvider (Thumbnail Generation)

**File:** `oncutf/core/thumbnail/providers.py`

**Changes:**

```python
def __init__(self, max_size: int = 256, ffmpeg_path: str | None = None):
    # OLD: Hardcoded "ffmpeg"
    # self.ffmpeg_path = "ffmpeg"
    
    # NEW: Auto-detect bundled ffmpeg
    if ffmpeg_path is None:
        from oncutf.utils.shared.external_tools import ToolName, get_tool_path
        
        try:
            self.ffmpeg_path = get_tool_path(ToolName.FFMPEG, prefer_bundled=True)
        except FileNotFoundError:
            logger.warning("FFmpeg not found, video thumbnails will fail")
            self.ffmpeg_path = "ffmpeg"  # Graceful fallback
    else:
        self.ffmpeg_path = ffmpeg_path
```

---

## External Tools Module

### API Reference

**File:** `oncutf/utils/shared/external_tools.py`

#### Core Functions

```python
from oncutf.utils.shared.external_tools import (
    ToolName,
    get_tool_path,
    get_bundled_tool_path,
    get_system_tool_path,
    is_tool_available,
    get_tool_version,
)

# Get tool path (bundled or system)
exiftool = get_tool_path(ToolName.EXIFTOOL, prefer_bundled=True)
# Returns: "/path/to/oncutf/bin/linux/exiftool" (bundled)
#      or: "/usr/bin/exiftool" (system PATH)
# Raises: FileNotFoundError if not found

# Check availability without raising exception
if is_tool_available(ToolName.FFMPEG):
    ffmpeg = get_tool_path(ToolName.FFMPEG)

# Get version
version = get_tool_version(ToolName.EXIFTOOL)
# Returns: "12.70" or None
```

#### Platform Detection

```python
def get_bundled_tool_path(tool_name: ToolName) -> Path | None:
    """Locate bundled binary based on platform.
    
    Maps:
    - Windows → bin/windows/exiftool.exe
    - macOS → bin/macos/exiftool (universal or arm64/x86_64)
    - Linux → bin/linux/exiftool
    
    Returns Path or None if not found.
    """
```

---

## PyInstaller Integration

### Development Mode

```bash
# No binaries in bin/ → uses system PATH
python main.py

# Binaries in bin/linux/ → uses bundled
cp /usr/bin/exiftool bin/linux/
python main.py
```

### Production Build

**File:** `oncutf.spec` (PyInstaller spec file)

```python
# Add bundled binaries to distribution
datas = [
    ('bin/linux/exiftool', 'bin/linux'),
    ('bin/linux/ffmpeg', 'bin/linux'),
]

a = Analysis(
    ['main.py'],
    datas=datas,
    # ...
)
```

**At runtime:**

- PyInstaller extracts binaries to `sys._MEIPASS/bin/linux/`
- `AppPaths.get_bundled_tools_dir()` returns `_MEIPASS/bin`
- `get_tool_path()` finds bundled binaries automatically

---

## Paths Module Integration

### AppPaths Class

**File:** `oncutf/utils/paths.py`

```python
class AppPaths:
    @classmethod
    def get_bundled_tools_dir(cls) -> Path:
        """Get bundled tools directory.
        
        Development: <project_root>/bin
        Frozen: <_MEIPASS>/bin
        
        Returns:
            Path to bin/ directory
        """
        if getattr(sys, "frozen", False):
            # PyInstaller frozen executable
            base_path = Path(sys._MEIPASS)
        else:
            # Development mode
            base_path = Path(__file__).parent.parent.parent  # -> project root
        
        return base_path / "bin"
```

---

## Error Handling

### Graceful Degradation

```python
# ExifToolWrapper raises RuntimeError if exiftool not found
try:
    wrapper = ExifToolWrapper()
except RuntimeError as e:
    logger.error("ExifTool not available: %s", e)
    # Disable metadata features
    from oncutf.config.features import FeatureAvailability
    FeatureAvailability.update_availability(exiftool=False)

# VideoThumbnailProvider logs warning but continues
provider = VideoThumbnailProvider()  # ffmpeg_path auto-detected
# If ffmpeg not found: logs warning, returns placeholder thumbnails
```

### User-Facing Messages

```python
raise FileNotFoundError(
    f"{tool_name.value} not found. "
    f"Please install it or place it in the bin/{platform.system().lower()} directory. "
    f"Download from: {download_url}"
)
```

---

## Testing

### Unit Tests

```python
def test_bundled_tool_detection():
    """Test that bundled tools are detected before system PATH."""
    # Place mock binary in bin/linux/
    bundled_path = AppPaths.get_bundled_tools_dir() / "linux" / "exiftool"
    bundled_path.parent.mkdir(parents=True, exist_ok=True)
    bundled_path.write_text("#!/bin/bash\necho 12.70")
    bundled_path.chmod(0o755)
    
    # Verify bundled tool is found
    path = get_tool_path(ToolName.EXIFTOOL, prefer_bundled=True)
    assert "bin/linux/exiftool" in str(path)
```

### Manual Testing

```bash
# Test bundled tool detection
python -c "
from oncutf.utils.shared.external_tools import *
print('ExifTool:', get_tool_path(ToolName.EXIFTOOL))
print('FFmpeg:', get_tool_path(ToolName.FFMPEG))
"

# Expected output (development with bundled binaries):
# ExifTool: /path/to/oncutf/bin/linux/exiftool
# FFmpeg: /path/to/oncutf/bin/linux/ffmpeg

# Expected output (development without bundled binaries):
# ExifTool: /usr/bin/exiftool
# FFmpeg: /usr/bin/ffmpeg
```

---

## Distribution Checklist

### For Linux Installer

- [ ] Download exiftool from <https://exiftool.org/>
- [ ] Download ffmpeg from <https://ffmpeg.org/download.html>
- [ ] Copy to `bin/linux/`
- [ ] Make executable: `chmod +x bin/linux/{exiftool,ffmpeg}`
- [ ] Test: `python -c "from oncutf.utils.shared.external_tools import *; print(get_tool_path(ToolName.EXIFTOOL))"`
- [ ] Update `oncutf.spec` datas list
- [ ] Build with PyInstaller: `pyinstaller oncutf.spec`
- [ ] Test frozen executable: `./dist/oncutf/oncutf`

### For Windows Installer

- [ ] Download `exiftool.exe` from <https://exiftool.org/>
- [ ] Download `ffmpeg.exe` static build
- [ ] Copy to `bin/windows/`
- [ ] Update `oncutf.spec` datas list
- [ ] Build with PyInstaller
- [ ] Test frozen executable

### For macOS Installer

- [ ] Download universal binaries or use `lipo` to combine Intel + ARM
- [ ] Copy to `bin/macos/`
- [ ] Code-sign binaries: `codesign -s "Developer ID" bin/macos/exiftool`
- [ ] Update `oncutf.spec` datas list
- [ ] Build with PyInstaller
- [ ] Test frozen executable

---

## License Compliance

### ExifTool

- **License:** GPL / Artistic License
- **Requirement:** Include `bin/LICENSE-exiftool.txt`
- **Attribution:** Required in About dialog

### FFmpeg

- **License:** LGPL / GPL (depends on build)
- **Requirement:** Include `bin/LICENSE-ffmpeg.txt`
- **Attribution:** Required in About dialog
- **Note:** Ensure static build is LGPL-compliant

---

## Migration Notes

### Before (Hardcoded Paths)

```python
# ExifToolWrapper
self.process = subprocess.Popen(["exiftool", ...])

# VideoThumbnailProvider
def __init__(self, ffmpeg_path: str = "ffmpeg"):
    self.ffmpeg_path = ffmpeg_path
```

**Problems:**

- Relied on system PATH
- No bundled binary support
- Failed on systems without exiftool/ffmpeg installed

### After (Bundled Tools)

```python
# ExifToolWrapper
exiftool_path = get_tool_path(ToolName.EXIFTOOL, prefer_bundled=True)
self.process = subprocess.Popen([exiftool_path, ...])
self._exiftool_path = exiftool_path

# VideoThumbnailProvider
def __init__(self, ffmpeg_path: str | None = None):
    if ffmpeg_path is None:
        self.ffmpeg_path = get_tool_path(ToolName.FFMPEG, prefer_bundled=True)
    else:
        self.ffmpeg_path = ffmpeg_path
```

**Benefits:**

- ✅ Bundled binaries preferred
- ✅ System PATH fallback
- ✅ PyInstaller compatible
- ✅ Graceful error handling

---

## Future Work

### Planned Enhancements

1. **Automatic Binary Download**
   - Download missing binaries on first run
   - Cache in user data directory
   - Verify checksums for security

2. **Version Management**
   - Check for updates on startup
   - Auto-upgrade binaries
   - Rollback on errors

3. **Platform-Specific Optimization**
   - GPU acceleration for ffmpeg (CUDA/Metal)
   - ARM64 optimized builds for Apple Silicon
   - Static linking for smaller binaries

4. **Testing Infrastructure**
   - Mock binaries for CI/CD
   - Docker images with bundled tools
   - Automated installer testing

---

## Related Documentation

- [bin/README.md](../../bin/README.md) - Binary installation guide
- [DEVELOPMENT.md](../../DEVELOPMENT.md) - Development setup
- [oncutf.spec](../../oncutf.spec) - PyInstaller configuration
- [oncutf/utils/paths.py](../oncutf/utils/paths.py) - Path management
- [oncutf/utils/shared/external_tools.py](../oncutf/utils/shared/external_tools.py) - Tool detection

---

## Contact

**Author:** Michael Economou  
**Date:** 2026-01-16  
**Status:** Implemented (Phase 2)
