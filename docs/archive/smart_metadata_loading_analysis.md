# Smart Metadata Loading Analysis - Phase 4

## 🎯 Objective
Optimize metadata loading by requesting only relevant fields based on file type, manufacturer, and model.
Instead of loading ALL metadata fields, we intelligently select what matters for each file.

## 📊 Current State Analysis

### How Metadata is Loaded Now
```bash
# Current exiftool call loads EVERYTHING:
exiftool -json -charset filename=UTF8 <file>

# Returns 100+ fields for a photo:
- EXIF data (50+ fields)
- XMP data (30+ fields)  
- IPTC data (20+ fields)
- Maker Notes (manufacturer-specific, 20-100 fields)
- File info (10+ fields)
```

### Problems with Current Approach
1. **Unnecessary data**: Loading GPS for studio photos, video codec for images
2. **Slow parsing**: JSON parsing 100+ fields when we need 10-15
3. **Memory waste**: Caching unused data
4. **Network overhead**: If metadata comes from network locations
5. **exiftool overhead**: Processing all groups even if unused

---

## 💡 Smart Loading Strategy

### Phase 4A: File Type Detection (Fast Pre-scan)
**Goal**: Detect file type BEFORE loading full metadata

```python
# Step 1: Quick file type detection (10-20ms)
exiftool -FileType -MIMEType -s3 <file>

# Results:
# Images: FileType=JPEG, MIMEType=image/jpeg
# Videos: FileType=MP4, MIMEType=video/mp4  
# Audio: FileType=MP3, MIMEType=audio/mpeg
```

### Phase 4B: Smart Field Selection by File Type

#### Image Files (JPEG, PNG, TIFF, RAW)
```python
ESSENTIAL_IMAGE_FIELDS = [
    # Basic Info
    "-FileType", "-MIMEType", "-ImageWidth", "-ImageHeight",
    
    # Camera Info (for rename operations)
    "-Make", "-Model", "-LensModel",
    
    # Capture Settings (commonly used)
    "-DateTimeOriginal", "-CreateDate",
    "-ISO", "-FNumber", "-ExposureTime", "-FocalLength",
    
    # Orientation (critical for display)
    "-Orientation",
    
    # Descriptive (user-editable fields)
    "-Title", "-Description", "-Keywords",
    "-Artist", "-Copyright",
]

# Only load extended if user specifically requests
EXTENDED_IMAGE_FIELDS = [
    "-GPSLatitude", "-GPSLongitude",  # Only if GPS is relevant
    "-Flash", "-WhiteBalance", "-ColorSpace",
    # Manufacturer-specific based on Make/Model
]
```

#### Video Files (MP4, MOV, AVI, MKV)
```python
ESSENTIAL_VIDEO_FIELDS = [
    # Basic Info
    "-FileType", "-MIMEType", "-Duration",
    "-ImageWidth", "-ImageHeight", "-FrameRate",
    
    # Camera/Device
    "-Make", "-Model",
    
    # Dates
    "-CreateDate", "-ModifyDate",
    
    # Codec info (useful for compatibility)
    "-VideoCodec", "-AudioCodec",
    
    # Descriptive
    "-Title", "-Description", "-Artist",
]
```

#### Audio Files (MP3, FLAC, WAV)
```python
ESSENTIAL_AUDIO_FIELDS = [
    # Basic Info
    "-FileType", "-MIMEType", "-Duration",
    
    # Audio Quality
    "-SampleRate", "-BitsPerSample", "-AudioBitrate",
    
    # ID3 Tags
    "-Title", "-Artist", "-Album", "-Year",
    "-Genre", "-TrackNumber", "-AlbumArtist",
]
```

#### Documents (PDF, DOCX)
```python
ESSENTIAL_DOCUMENT_FIELDS = [
    "-FileType", "-MIMEType",
    "-Title", "-Author", "-Subject", "-Keywords",
    "-Creator", "-Producer",
    "-CreateDate", "-ModifyDate",
    "-PageCount",  # For PDFs
]
```

### Phase 4C: Manufacturer-Specific Optimization

```python
MANUFACTURER_PROFILES = {
    "Canon": {
        "useful_fields": [
            "-CanonModelID", "-CanonFirmwareVersion",
            "-AFPointsUsed", "-WhiteBalance", "-PictureStyle",
        ],
        "skip_fields": [
            "-CanonCustomFunctions",  # Rarely useful, 50+ subfields
            "-CanonVRDInfo",  # DPP-specific, not needed
        ]
    },
    
    "Sony": {
        "useful_fields": [
            "-SonyModelID", "-LensType",
            "-CreativeStyle", "-DynamicRangeOptimizer",
        ],
        "skip_fields": [
            "-SonyPrivateData",  # Undocumented, large
        ]
    },
    
    "Nikon": {
        "useful_fields": [
            "-ShutterCount", "-LensID",
            "-ActiveDLighting", "-PictureControlName",
        ],
        "skip_fields": [
            "-NikonCaptureOffsets",  # Internal use only
        ]
    },
    
    "Apple": {  # iPhone photos
        "useful_fields": [
            "-RunTimeValue",  # Live photo identifier
            "-ContentIdentifier",
        ],
        "skip_fields": [
            "-ApplePrivateData",
        ]
    },
    
    "DJI": {  # Drone photos/videos
        "useful_fields": [
            "-FlightYawDegree", "-FlightPitchDegree",
            "-GimbalYawDegree", "-RelativeAltitude",
        ],
        "skip_fields": []
    }
}
```

---

## 🚀 Implementation Plan

### Step 1: Create Smart Metadata Selector
```python
# File: core/smart_metadata_selector.py

class SmartMetadataSelector:
    """Intelligently selects metadata fields based on file characteristics."""
    
    def get_fields_for_file(self, file_path: str) -> list[str]:
        """
        Returns optimized field list for a file.
        
        Process:
        1. Quick type detection (FileType + MIMEType only)
        2. Select base fields for that type
        3. If image with Make/Model, add manufacturer fields
        4. Return complete field list
        """
        
    def detect_file_type_fast(self, file_path: str) -> tuple[str, str]:
        """Fast detection: FileType + MIMEType only (10-20ms)."""
        
    def get_base_fields(self, file_type: str, mime_type: str) -> list[str]:
        """Get base fields for file type."""
        
    def get_manufacturer_fields(self, make: str, model: str) -> list[str]:
        """Get manufacturer-specific useful fields."""
```

### Step 2: Optimize ExifTool Calls
```python
# Instead of:
exiftool -json -charset filename=UTF8 <file>

# Use specific fields:
exiftool -json -charset filename=UTF8 \
    -FileType -MIMEType -ImageWidth -ImageHeight \
    -Make -Model -DateTimeOriginal -ISO -FNumber \
    <file>
```

### Step 3: Two-Stage Loading
```python
class TwoStageMetadataLoader:
    """Load metadata in two stages for optimal performance."""
    
    def load_metadata(self, file_path: str, extended: bool = False):
        # Stage 1: Fast type detection (10-20ms)
        file_type, mime_type = self.detect_type(file_path)
        
        # Stage 2: Targeted field loading (30-50ms)
        fields = self.selector.get_fields_for_file(file_type, mime_type)
        metadata = self.load_specific_fields(file_path, fields)
        
        # Stage 3 (optional): Extended loading
        if extended and user_requested:
            extended_fields = self.get_extended_fields(file_type, metadata)
            extended_data = self.load_specific_fields(file_path, extended_fields)
            metadata.update(extended_data)
            
        return metadata
```

---

## 📈 Expected Performance Gains

### Scenario 1: Mixed Photo Collection (100 files)
```
Current:
- 100 files × 150ms (full metadata) = 15 seconds
- JSON parsing: 100+ fields per file
- Memory: ~2MB cached data

Smart Loading:
- 100 files × 50ms (targeted fields) = 5 seconds
- JSON parsing: 15-20 fields per file
- Memory: ~500KB cached data

**Improvement: 3x faster, 75% less memory**
```

### Scenario 2: Video Files (20 files)
```
Current:
- 20 files × 200ms (full metadata + codecs) = 4 seconds
- Many unused image fields loaded

Smart Loading:
- 20 files × 80ms (video-specific only) = 1.6 seconds

**Improvement: 2.5x faster**
```

### Scenario 3: Mixed Collection (Photos, Videos, Audio)
```
Current:
- Uniform loading regardless of type
- Lots of N/A fields

Smart Loading:
- Type-aware loading
- Only relevant fields per type

**Improvement: 2-3x faster average**
```

---

## 🔍 Additional Optimizations

### A. Parallel Loading with Smart Batching
```python
# Group files by type for efficient parallel loading
images_batch = [f for f in files if is_image(f)]
videos_batch = [f for f in files if is_video(f)]

# Load in parallel with type-specific fields
with ThreadPoolExecutor() as executor:
    image_futures = [executor.submit(load_image_metadata, f) for f in images_batch]
    video_futures = [executor.submit(load_video_metadata, f) for f in videos_batch]
```

### B. Progressive Field Loading
```python
# Load essential fields first (for UI display)
essential_data = load_essential(file)  # 20ms
update_ui(essential_data)

# Load full data in background (for operations)
threading.Thread(target=load_full, args=(file,)).start()  # 50ms background
```

### C. Caching Strategy
```python
# Cache structure:
{
    "file_path": {
        "type": "image",
        "essential": {...},  # Always cached
        "extended": {...},   # Only if loaded
        "manufacturer": "Canon",
        "last_accessed": timestamp
    }
}

# Smart cache eviction:
# - Keep essential data (small footprint)
# - Evict extended data after 5 min of no access
# - LRU for essential data with 1000 file limit
```

---

## ✅ Success Metrics

1. **Loading Speed**
   - Target: 2-3x faster for typical collections
   - Measure: Average ms per file for 100-file batch

2. **Memory Usage**
   - Target: 50-70% reduction in cached metadata size
   - Measure: Total cache size for 1000 files

3. **User Experience**
   - Target: < 100ms to show basic info (filename, type, dimensions)
   - Target: < 500ms for full metadata (for rename operations)

4. **Accuracy**
   - Target: 100% of rename-relevant fields captured
   - No loss of functionality

---

## 🛠 Implementation Phases

### Phase 4.1: Analysis & Design (30 min)
- ✅ Analyze current metadata usage patterns
- ✅ Design field selection strategy
- ✅ Document manufacturer profiles

### Phase 4.2: Smart Selector Implementation (1-2 hours)
- Create `SmartMetadataSelector` class
- Implement file type detection
- Add manufacturer profiles
- Write field selection logic

### Phase 4.3: Optimize ExifTool Wrapper (1 hour)
- Add targeted field loading
- Implement two-stage loading
- Update caching strategy

### Phase 4.4: Integration & Testing (1 hour)
- Integrate with existing loaders
- Test with various file types
- Performance benchmarking
- Ensure all rename operations still work

### Phase 4.5: Documentation & Refinement (30 min)
- Document new approach
- Add configuration options
- Profile-based customization

**Total Estimated Time: 3-4 hours**

---

## 🎓 Key Insights

1. **File type matters**: A photo and video need different metadata
2. **Manufacturer matters**: Canon and Sony have different useful fields
3. **Context matters**: Renaming needs different fields than viewing
4. **Speed vs Completeness**: Load essentials fast, full data later
5. **Cache smartly**: Keep small essential data, evict large extended data

---

## 🚦 Next Steps

1. Create `SmartMetadataSelector` class
2. Add file type detection to `ExifToolWrapper`
3. Implement targeted field loading
4. Test with real-world files
5. Measure performance improvements
6. Iterate based on results
