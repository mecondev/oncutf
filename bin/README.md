# External Tools Binaries

This directory contains platform-specific binaries for external tools bundled with oncutf when packaged as a standalone executable using PyInstaller.

## Directory Structure

```tree
bin/
├── windows/    # Windows binaries (.exe)
├── macos/      # macOS binaries (universal)
└── linux/      # Linux binaries (x86_64)
```

## Required Tools

> **Note:** Metadata extraction is handled by the **exopsis** Python package
> (no binary needed — bundled automatically by PyInstaller with the application).

### FFmpeg + FFprobe (required for video thumbnails)

**Purpose:** Video frame extraction for thumbnail generation

**Note:** Both `ffmpeg` AND `ffprobe` must be present. The app checks for both at boot;
if either is missing, the thumbnail viewport is disabled.

**Download Links:**

- **Windows:** [ffmpeg.org](https://ffmpeg.org/download.html#build-windows) - Download static build, extract `ffmpeg.exe` and `ffprobe.exe` from `bin/`
- **macOS:** [ffmpeg.org](https://ffmpeg.org/download.html#build-mac) or `brew install ffmpeg`, then copy both binaries
- **Linux:** Download static build from [johnvansickle.com/ffmpeg](https://johnvansickle.com/ffmpeg/) (includes both `ffmpeg` and `ffprobe`).

  Quick install script:

  ```bash
  curl -s https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg-static.tar.xz
  tar -xJf /tmp/ffmpeg-static.tar.xz -C /tmp/
  FFMPEG_DIR=$(ls -d /tmp/ffmpeg-*-amd64-static)
  cp "$FFMPEG_DIR/ffmpeg" "$FFMPEG_DIR/ffprobe" bin/linux/
  chmod +x bin/linux/ffmpeg bin/linux/ffprobe
  ```

**File Names:**

- Windows: `ffmpeg.exe`, `ffprobe.exe`
- macOS: `ffmpeg`, `ffprobe` (universal binaries for Intel + Apple Silicon)
- Linux: `ffmpeg`, `ffprobe`

## Installation Instructions

### For Development (optional)

Place binaries in the appropriate platform directories to test bundled tool detection:

```bash
# Example for Windows development
cp ffmpeg.exe bin/windows/
cp ffprobe.exe bin/windows/
```

### For PyInstaller Packaging

1. Download platform-specific binaries (see links above)
2. Place them in the corresponding `bin/` subdirectories
3. PyInstaller will automatically bundle them when building the executable
4. The application will prefer bundled binaries over system PATH installations

## Runtime Behavior

The application uses `oncutf/utils/external_tools.py` to detect and use tools:

1. **Check bundled binaries first** (in `bin/<platform>/`)
2. **Fallback to system PATH** if bundled binaries not found
3. **Graceful degradation** if not available:
   - Metadata features disabled if exopsis package is missing
   - Video features disabled if FFmpeg missing
   - User notified via UI about missing capabilities

## Platform-Specific Notes

### Windows

- Download `.exe` binaries directly
- Ensure binaries are 64-bit for PyInstaller compatibility

### macOS

- Use **universal binaries** (Intel + Apple Silicon) when possible
- Create universal binaries with `lipo`: `lipo -create ffmpeg-intel ffmpeg-arm64 -output ffmpeg`
- Code-sign binaries for macOS distribution: `codesign -s "Developer ID" ffmpeg`

### Linux

- Use x86_64 binaries
- Ensure binaries have execute permissions: `chmod +x ffmpeg ffprobe`
- Consider AppImage packaging as alternative to PyInstaller

## Size Considerations

Typical binary sizes (compressed):

- FFmpeg: ~50-100 MB (full build with codecs)

**Recommendation:** FFmpeg can be optional or user-downloadable to keep installer size small.
Metadata extraction (exopsis) adds no binary weight — it is a Python package.

## License Compliance

When distributing bundled binaries:

- **FFmpeg:** LGPL / GPL (depending on build) - check build configuration
- **exopsis:** See package license (Python dependency, no binary distribution required)

Include license files in distribution package:

- `bin/LICENSE-ffmpeg.txt`

## Testing Bundled Tools

Test tool detection:

```bash
# Run from project root
python -c "from oncutf.utils.shared.external_tools import *; print(get_tool_path(ToolName.FFMPEG))"
python -c "from oncutf.utils.shared.external_tools import *; print(is_tool_available(ToolName.FFMPEG))"

# Test exopsis availability
python -c "from exopsis import extract; print('exopsis OK')"
```

## Maintenance

- **Keep tools updated:** Check for security updates regularly
- **Test after updates:** Ensure compatibility with oncutf workflows
- **Document versions:** Track which tool versions are tested/supported
