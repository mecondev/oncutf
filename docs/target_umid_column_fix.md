# Intelligent Column Width Management

## Problem Description

Η στήλη `target_umid` (και άλλες στήλες) όταν προστίθενται στον πίνακα αρχείων δεν είχαν το σωστό μήκος που ορίζεται στο `config.py` και εμφάνιζαν 3 τελείες (text elision) χωρίς wordwrap.

## Root Cause Analysis

1. **Incorrect Width Application**: Οι στήλες έχουν ρυθμιστεί στο `config.py` με συγκεκριμένα πλάτη, αλλά όταν προστίθενται δυναμικά, μπορεί να μην εφαρμόζεται σωστά το πλάτος.

2. **Suspicious Saved Widths**: Το σύστημα αποθήκευσης πλάτους στηλών μπορεί να έχει αποθηκεύσει εσφαλμένες τιμές (π.χ. 100px) που προκαλούν υπερβολικό text elision.

3. **Word Wrap Issues**: Αν και το word wrap είναι απενεργοποιημένο, οι στήλες δεν είχαν αρκετό πλάτος για να εμφανίσουν το περιεχόμενο χωρίς elision.

4. **Lack of Content-Aware Width Management**: Δεν υπήρχε σύστημα που να αναλύει τον τύπο περιεχομένου κάθε στήλης για να προσαρμόσει το πλάτος ανάλογα.

## Solution Implementation

### 1. Content-Aware Width Analysis

Προστέθηκε η μέθοδος `_analyze_column_content_type()` που κατηγοριοποιεί τις στήλες βάσει του περιεχομένου τους:

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

Προστέθηκε η μέθοδος `_get_recommended_width_for_content_type()` που προτείνει πλάτη βάσει του τύπου περιεχομένου:

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

Προστέθηκε η γενική μέθοδος `_ensure_column_proper_width()` που εφαρμόζεται σε όλες τις στήλες:

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

Η γενική διαχείριση πλάτους ενσωματώθηκε σε όλα τα σημεία διαχείρισης στηλών:

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
Ελέγχει και διορθώνει το πλάτος όλων των ορατών στηλών για να ελαχιστοποιήσει το text elision.

#### `_ensure_new_column_proper_width()`
Εξασφαλίζει ότι οι νέες στήλες έχουν το σωστό πλάτος μετά την προσθήκη.

## Configuration

Η στήλη `target_umid` έχει τις εξής ρυθμίσεις στο `config.py`:

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

Το σύστημα αναλύει τις στήλες σε 4 κατηγορίες:

1. **Short** (80px+): Κωδικοί, αριθμοί, σύντομα ονόματα
   - `type`, `iso`, `rotation`, `duration`, `video_fps`, `audio_channels`

2. **Medium** (120px+): Μορφές, μοντέλα, μεγέθη
   - `audio_format`, `video_codec`, `video_format`, `white_balance`, `compression`, `device_model`, `device_manufacturer`, `image_size`, `video_avg_bitrate`, `aperture`, `shutter_speed`

3. **Long** (200px+): Ονόματα αρχείων, hashes, UMIDs
   - `filename`, `file_hash`, `target_umid`, `device_serial_no`

4. **Very Long** (300px+): Ημερομηνίες, διαδρομές αρχείων
   - `modified`, `file_size`

## Benefits

1. **Content-Aware Width**: Κάθε στήλη παίρνει πλάτος ανάλογα με τον τύπο περιεχομένου της
2. **Consistent Behavior**: Όλες οι στήλες συμπεριφέρονται με συνέπεια
3. **Reduced Elision**: Ελαχιστοποιείται το text elision με τις 3 τελείες
4. **Proper Word Wrap**: Το word wrap παραμένει απενεργοποιημένο αλλά με αρκετό πλάτος
5. **Backward Compatibility**: Δεν επηρεάζει υπάρχουσα λειτουργικότητα
6. **Robust Error Handling**: Χειρίζεται σωστά σφάλματα και edge cases
7. **Extensible**: Εύκολα μπορεί να προστεθούν νέοι τύποι περιεχομένου

## Files Modified

- `widgets/file_table_view.py`: Προσθήκη γενικής διαχείρισης πλάτους στηλών
- `docs/target_umid_column_fix.md`: Αυτό το documentation file

## Future Considerations

1. **Dynamic Content Analysis**: Μπορεί να προστεθεί ανάλυση του πραγματικού περιεχομένου για ακόμα καλύτερη προσαρμογή
2. **User Preferences**: Μπορεί να προστεθεί επιλογή για χρήστες να προσαρμόσουν τα προτεινόμενα πλάτη
3. **Performance Optimization**: Μπορεί να προστεθεί caching για την ανάλυση περιεχομένου
4. **Internationalization**: Μπορεί να προστεθεί υποστήριξη για διαφορετικά γράμματα και γλώσσες
