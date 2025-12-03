# Intelligent Column Width Management

## Problem Description

The `target_umid` column (and other columns) when added to the file table did not have the correct width defined in `config.py` and displayed 3 dots (text elision) without wordwrap.

## Root Cause Analysis

1. **Incorrect Width Application**: Columns are configured in `config.py` with specific widths, but when added dynamically, the width may not be applied correctly.

2. **Suspicious Saved Widths**: The column width storage system may have saved incorrect values (e.g., 100px) that cause excessive text elision.

3. **Word Wrap Issues**: Although word wrap is disabled, columns did not have enough width to display content without elision.

4. **Lack of Content-Aware Width Management**: There was no system to analyze the content type of each column to adjust width accordingly.

## Solution Implementation

### 1. Content-Aware Width Analysis

Added the `_analyze_column_content_type()` method that categorizes columns based on their content:

```python
def _analyze_column_content_type(self, column_key: str) -> str:
    """Analyze the content type of a column to determine appropriate width."""
    # Define content types based on column keys
    content_types = {
        # Short content (names, types, codes)
        "type": "short",
        "iso": "short",
        "rotation": "short",
        "duration": "short",
        "video_fps": "short",
        "audio_channels": "short",

        # Medium content (formats, models, sizes)
        "audio_format": "medium",
        "video_codec": "medium",
        "video_format": "medium",
        "white_balance": "medium",
        "compression": "medium",
        "device_model": "medium",
        "device_manufacturer": "medium",
        "image_size": "medium",
        "video_avg_bitrate": "medium",
        "aperture": "medium",
        "shutter_speed": "medium",

        # Long content (filenames, hashes, UMIDs)
        "filename": "long",
        "file_hash": "long",
        "target_umid": "long",
        "device_serial_no": "long",

        # Very long content (dates, file paths)
        "modified": "very_long",
        "file_size": "very_long",
    }

    return content_types.get(column_key, "medium")
```

### 2. Intelligent Width Recommendations

Added the `_get_recommended_width_for_content_type()` method that suggests widths based on content type:

```python
def _get_recommended_width_for_content_type(self, content_type: str, default_width: int, min_width: int) -> int:
    """Get recommended width based on content type."""
    # Define width recommendations for different content types
    width_recommendations = {
        "short": max(80, min_width),      # Short codes, numbers
        "medium": max(120, min_width),    # Formats, models, sizes
        "long": max(200, min_width),      # Filenames, hashes, UMIDs
        "very_long": max(300, min_width), # Dates, file paths
    }

    # Use the larger of default_width, min_width, or content_type recommendation
    recommended = width_recommendations.get(content_type, default_width)
    return max(recommended, default_width, min_width)
```

### 3. Universal Width Validation

Added the general `_ensure_column_proper_width()` method that applies to all columns:

```python
def _ensure_column_proper_width(self, column_key: str, current_width: int) -> int:
    """Ensure column has proper width based on its content type and configuration."""
    from config import FILE_TABLE_COLUMN_CONFIG

    column_config = FILE_TABLE_COLUMN_CONFIG.get(column_key, {})
    default_width = column_config.get("width", 100)
    min_width = column_config.get("min_width", 50)

    # Analyze column content type to determine appropriate width
    content_type = self._analyze_column_content_type(column_key)
    recommended_width = self._get_recommended_width_for_content_type(content_type, default_width, min_width)

    # If current width is suspiciously small (likely from saved config), use recommended width
    if current_width < min_width:
        logger.debug(f"[ColumnWidth] Column '{column_key}' width {current_width}px is below minimum {min_width}px, using recommended {recommended_width}px")
        return recommended_width

    # If current width is reasonable, use it but ensure it's not below minimum
    return max(current_width, min_width)
```

### 4. Integration Points

The general width management was integrated into all column management points:

#### Column Configuration (`_configure_columns_delayed`)
```python
# Apply intelligent width validation for all columns
width = self._ensure_column_proper_width(column_key, width)
```

#### Column Addition (`add_column`)
```python
# Ensure proper width for the newly added column
schedule_ui_update(self._ensure_new_column_proper_width, delay=100, timer_id=f"ensure_column_width_{column_key}")
```

#### Word Wrap Management (`_ensure_no_word_wrap`)
```python
# Ensure all columns have proper width to minimize text elision
self._ensure_all_columns_proper_width()
```

#### Column Reset (`_reset_columns_to_default`)
```python
# Apply intelligent width validation for all columns
final_width = self._ensure_column_proper_width(column_key, default_width)
```

#### Auto-fit (`_auto_fit_columns_to_content`)
```python
# Apply intelligent width validation for all columns
final_width = self._ensure_column_proper_width(column_key, final_width)
```

### 5. Additional Helper Methods

#### `_ensure_all_columns_proper_width()`
Checks and corrects the width of all visible columns to minimize text elision.

#### `_ensure_new_column_proper_width()`
Ensures that new columns have the correct width after being added.

## Configuration

The `target_umid` column has the following settings in `config.py`:

```python
"target_umid": {
    "title": "Target UMID",
    "key": "target_umid",
    "default_visible": False,
    "removable": True,
    "width": 400,        # Default width
    "alignment": "left",
    "min_width": 200,    # Minimum width
},
```

## Content Type Analysis

The system analyzes columns into 4 categories:

1. **Short** (80px+): Codes, numbers, short names
   - `type`, `iso`, `rotation`, `duration`, `video_fps`, `audio_channels`

2. **Medium** (120px+): Formats, models, sizes
   - `audio_format`, `video_codec`, `video_format`, `white_balance`, `compression`, `device_model`, `device_manufacturer`, `image_size`, `video_avg_bitrate`, `aperture`, `shutter_speed`

3. **Long** (200px+): Filenames, hashes, UMIDs
   - `filename`, `file_hash`, `target_umid`, `device_serial_no`

4. **Very Long** (300px+): Dates, file paths
   - `modified`, `file_size`

## Benefits

1. **Content-Aware Width**: Each column gets width appropriate to its content type
2. **Consistent Behavior**: All columns behave consistently
3. **Reduced Elision**: Minimizes text elision with 3 dots
4. **Proper Word Wrap**: Word wrap remains disabled but with sufficient width
5. **Backward Compatibility**: Does not affect existing functionality
6. **Robust Error Handling**: Handles errors and edge cases properly
7. **Extensible**: Easy to add new content types

## Files Modified

- `widgets/file_table_view.py`: Added general column width management
- `docs/target_umid_column_fix.md`: This documentation file

## Future Considerations

1. **Dynamic Content Analysis**: Could add analysis of actual content for even better adaptation
2. **User Preferences**: Could add option for users to customize recommended widths
3. **Performance Optimization**: Could add caching for content analysis
4. **Internationalization**: Could add support for different characters and languages
