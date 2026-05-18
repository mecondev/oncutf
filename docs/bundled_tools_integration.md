<!--
Bundled Tools Integration - Technical Documentation

Author: Michael Economou
Date: 2026-01-16

Documentation for bundled binary (ffmpeg) and Python package (exopsis) integration
with PyInstaller support.
-->

# Bundled Tools Integration

## Overview

The application uses **bundled binaries** for ffmpeg and the **exopsis Python package** for metadata extraction. This enables:

- **Standalone distribution**: The application runs without system PATH dependencies
- **Cross-platform consistency**: Controlled tool versions across environments
- **PyInstaller compatibility**: Automatic bundling in packaged installers

---

## Architecture

### Tool Resolution Priority

**Metadata (exopsis):**

- Python package, resolved by the import system
- PyInstaller bundles it automatically with the rest of the application

**FFmpeg:**

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
│   │   └── ffmpeg          # + ffprobe
│   ├── macos/
│   │   └── ffmpeg          # Universal binary
│   └── windows/
│       └── ffmpeg.exe      # + ffprobe.exe
│
├── oncutf/
│   └── utils/
│       └── shared/
│           └── external_tools.py  # Tool detection & path resolution (FFmpeg)
│
└── oncutf/
    ├── core/
    │   └── thumbnail/
    │       └── providers.py       # VideoThumbnailProvider (uses ffmpeg)
    └── infra/
        └── external/
            └── exopsis_wrapper.py   # ExopsisWrapper (delegates to exopsis)
```

---

## Integration Points

### 1. ExopsisWrapper (Metadata Extraction via Exopsis)

**File:** `oncutf/infra/external/exopsis_wrapper.py`

The `ExopsisWrapper` class delegates entirely to the **exopsis** Python package
in-process — no subprocess or binary path management needed.

```python
from exopsis import ExtractOptions, extract

def _extract_metadata(self, file_path: str, use_extended: bool = False) -> dict | None:
    options = ExtractOptions(frame_sample="all" if use_extended else "first")
    result = extract(file_path, options=options)
    return result
```

`exopsis.extract()` runs in-process; PyInstaller bundles the package automatically.

### 2. VideoThumbnailProvider (Thumbnail Generation)

**File:** `oncutf/core/thumbnail/providers.py`

```python
def __init__(self, max_size: int = 256, ffmpeg_path: str | None = None):
    # Auto-detect bundled ffmpeg
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

Used exclusively for **FFmpeg** binary detection (exopsis needs no path resolution).

```python
from oncutf.utils.shared.external_tools import (
    ToolName,
    get_tool_path,
    get_bundled_tool_path,
    get_system_tool_path,
    is_tool_available,
    get_tool_version,
)

# Check availability without raising exception
if is_tool_available(ToolName.FFMPEG):
    ffmpeg = get_tool_path(ToolName.FFMPEG)

# Get version
version = get_tool_version(ToolName.FFMPEG)
# Returns: "7.1.1" or None
```

#### Platform Detection

```python
def get_bundled_tool_path(tool_name: ToolName) -> Path | None:
    """Locate bundled binary based on platform.

    Maps:
    - Windows → bin/windows/ffmpeg.exe
    - macOS → bin/macos/ffmpeg (universal or arm64/x86_64)
    - Linux → bin/linux/ffmpeg

    Returns Path or None if not found.
    """
```

---

## PyInstaller Integration

### Development Mode

```bash
# No binaries in bin/ → uses system PATH for ffmpeg
# Exopsis is always available as a Python package
python main.py

# FFmpeg binaries in bin/linux/ → uses bundled
cp /usr/bin/ffmpeg bin/linux/
cp /usr/bin/ffprobe bin/linux/
python main.py
```

### Production Build

**File:** `oncutf.spec` (PyInstaller spec file)

```python
# Add bundled FFmpeg binaries to distribution
# (exopsis is bundled automatically as a Python package)
datas = [
    ('bin/linux/ffmpeg', 'bin/linux'),
    ('bin/linux/ffprobe', 'bin/linux'),
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
- `get_tool_path()` finds bundled FFmpeg automatically
- Exopsis is available as a regular Python import (no special handling)

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
# ExopsisWrapper raises RuntimeError if exopsis is not installed
try:
    wrapper = ExopsisWrapper()
except RuntimeError as e:
    logger.error("Exopsis not available: %s", e)
    # Disable metadata features
    from oncutf.config.features import FeatureAvailability
    FeatureAvailability.update_availability(exopsis=False)

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
    """Test that bundled FFmpeg is detected before system PATH."""
    bundled_path = AppPaths.get_bundled_tools_dir() / "linux" / "ffmpeg"
    bundled_path.parent.mkdir(parents=True, exist_ok=True)
    bundled_path.write_text("#!/bin/bash\necho 7.1.1")
    bundled_path.chmod(0o755)

    path = get_tool_path(ToolName.FFMPEG, prefer_bundled=True)
    assert "bin/linux/ffmpeg" in str(path)
```

### Manual Testing

```bash
# Test FFmpeg bundled tool detection
python -c "
from oncutf.utils.shared.external_tools import *
print('FFmpeg:', get_tool_path(ToolName.FFMPEG))
"

# Test exopsis availability
python -c "from exopsis import extract; print('exopsis OK')"

# Expected output (development with bundled FFmpeg):
# FFmpeg: /path/to/oncutf/bin/linux/ffmpeg
```

---

## Distribution Checklist

### For Linux Installer

- [ ] Download ffmpeg + ffprobe static builds from <https://johnvansickle.com/ffmpeg/>
- [ ] Copy to `bin/linux/`
- [ ] Make executable: `chmod +x bin/linux/{ffmpeg,ffprobe}`
- [ ] Ensure exopsis is in `requirements.txt` / `pyproject.toml` (auto-bundled by PyInstaller)
- [ ] Test: `python -c "from oncutf.utils.shared.external_tools import *; print(get_tool_path(ToolName.FFMPEG))"`
- [ ] Update `oncutf.spec` datas list (ffmpeg only)
- [ ] Build with PyInstaller: `pyinstaller oncutf.spec`
- [ ] Test frozen executable: `./dist/oncutf/oncutf`

### For Windows Installer

- [ ] Download `ffmpeg.exe` + `ffprobe.exe` static build
- [ ] Copy to `bin/windows/`
- [ ] Update `oncutf.spec` datas list
- [ ] Build with PyInstaller
- [ ] Test frozen executable

### For macOS Installer

- [ ] Download universal FFmpeg + FFprobe binaries or use `lipo` to combine Intel + ARM
- [ ] Copy to `bin/macos/`
- [ ] Code-sign binaries: `codesign -s "Developer ID" bin/macos/ffmpeg`
- [ ] Update `oncutf.spec` datas list
- [ ] Build with PyInstaller
- [ ] Test frozen executable

---

## License Compliance

### Exopsis

- **License:** See exopsis package license
- **Requirement:** Include in `requirements.txt`; PyInstaller bundles automatically
- **Attribution:** No binary distribution required

### FFmpeg

- **License:** LGPL / GPL (depends on build)
- **Requirement:** Include `bin/LICENSE-ffmpeg.txt`
- **Attribution:** Required in About dialog
- **Note:** Ensure static build is LGPL-compliant

---

## Future Work

### Planned Enhancements

1. **FFmpeg Version Management**
   - Check for updates on startup
   - Verify checksums for security

2. **Platform-Specific Optimization**
   - GPU acceleration for ffmpeg (CUDA/Metal)
   - ARM64 optimized builds for Apple Silicon
   - Static linking for smaller binaries

3. **Testing Infrastructure**
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
**Status:** Implemented
