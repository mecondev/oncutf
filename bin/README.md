# External Tools Binaries

This directory contains platform-specific binaries for external tools bundled with oncutf when packaged as a standalone executable using PyInstaller.

## Directory Structure

```
bin/
├── windows/    # Windows binaries (.exe)
├── macos/      # macOS binaries (universal)
└── linux/      # Linux binaries (x86_64)
```

## Required Tools

### ExifTool
**Purpose:** EXIF/metadata reading and writing for image/video files

**Download Links:**
- **Windows:** [exiftool.org](https://exiftool.org/) - Download `exiftool-12.xx.zip`, extract `exiftool(-k).exe` and rename to `exiftool.exe`
- **macOS:** [exiftool.org](https://exiftool.org/) - Download `ExifTool-XX.dmg` or use `brew install exiftool`, then copy binary
- **Linux:** Download `Image-ExifTool-XX.tar.gz` from [exiftool.org](https://exiftool.org/), extract and copy both `exiftool` and `lib/` into `bin/linux/`.
  The Perl script uses `lib/` from the same directory, so both must be present.

  Quick install script:
  ```bash
  LATEST=$(curl -s https://exiftool.org/ | grep -oP 'Image-ExifTool-[\d.]+\.tar\.gz' | head -1)
  curl -s "https://exiftool.org/$LATEST" -o /tmp/exiftool.tar.gz
  tar -xzf /tmp/exiftool.tar.gz -C /tmp/
  cp /tmp/Image-ExifTool-*/exiftool bin/linux/
  cp -r /tmp/Image-ExifTool-*/lib bin/linux/
  chmod +x bin/linux/exiftool
  ```

**File Names:**
- Windows: `exiftool.exe`
- macOS: `exiftool` (universal binary for Intel + Apple Silicon)
- Linux: `exiftool` + `lib/` subdirectory

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
cp exiftool.exe bin/windows/
cp ffmpeg.exe bin/windows/
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
3. **Graceful degradation** if neither available:
   - Metadata features disabled if ExifTool missing
   - Video features disabled if FFmpeg missing
   - User notified via UI about missing capabilities

## Platform-Specific Notes

### Windows
- Download `.exe` binaries directly
- Ensure binaries are 64-bit for PyInstaller compatibility

### macOS
- Use **universal binaries** (Intel + Apple Silicon) when possible
- Create universal binaries with `lipo`: `lipo -create exiftool-intel exiftool-arm64 -output exiftool`
- Code-sign binaries for macOS distribution: `codesign -s "Developer ID" exiftool`

### Linux
- Use x86_64 binaries
- Ensure binaries have execute permissions: `chmod +x exiftool ffmpeg`
- Consider AppImage packaging as alternative to PyInstaller

## Size Considerations

Typical binary sizes (compressed):
- ExifTool: ~1-3 MB (Perl script + runtime)
- FFmpeg: ~50-100 MB (full build with codecs)

**Recommendation:** Only bundle ExifTool by default. FFmpeg can be optional or user-downloadable.

## License Compliance

When distributing bundled binaries:

- **ExifTool:** GPL / Artistic License - requires attribution
- **FFmpeg:** LGPL / GPL (depending on build) - check build configuration

Include license files in distribution package:
- `bin/LICENSE-exiftool.txt`
- `bin/LICENSE-ffmpeg.txt`

## Testing Bundled Tools

Test tool detection:
```bash
# Run from project root
python -c "from oncutf.utils.shared.external_tools import *; print(get_tool_path(ToolName.EXIFTOOL))"
python -c "from oncutf.utils.shared.external_tools import *; print(is_tool_available(ToolName.FFMPEG))"
```

## Maintenance

- **Keep tools updated:** Check for security updates regularly
- **Test after updates:** Ensure compatibility with oncutf workflows
- **Document versions:** Track which tool versions are tested/supported
