# Structured Metadata System

## Overview

The Structured Metadata System is a comprehensive solution for organizing, storing, and managing metadata in a structured format. It provides categorized metadata storage with proper field definitions, data types, and formatting capabilities.

## Architecture

### Database Schema

The system uses three main database tables:

#### 1. `metadata_categories`
Stores metadata categories (groups) for organizing related fields:
- `id`: Primary key
- `category_name`: Unique category identifier
- `display_name`: Human-readable category name
- `description`: Optional category description
- `sort_order`: Display order
- `created_at`: Creation timestamp

#### 2. `metadata_fields`
Stores individual metadata field definitions:
- `id`: Primary key
- `field_key`: Unique field identifier (e.g., "EXIF:Make")
- `field_name`: Human-readable field name (e.g., "Camera Make")
- `category_id`: Reference to metadata category
- `data_type`: Field data type (text, number, size, datetime, duration, coordinate)
- `is_editable`: Whether field can be edited
- `is_searchable`: Whether field can be searched
- `display_format`: Optional formatting hint (e.g., "mm", "pixels", "f/")
- `sort_order`: Display order within category
- `created_at`: Creation timestamp

#### 3. `file_metadata_structured`
Stores actual metadata values for files:
- `id`: Primary key
- `path_id`: Reference to file path
- `field_id`: Reference to metadata field
- `field_value`: Stored value (as text)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- Unique constraint on (path_id, field_id)

### Default Categories

The system initializes with the following default categories:

1. **File Information** (`file_basic`)
   - Basic file properties and information
   - Fields: Filename, File Size, Modified Date, Created Date, File Type, MIME Type

2. **Image Properties** (`image`)
   - Image-specific metadata and properties
   - Fields: Image Width, Image Height, Orientation, Color Space, Bits Per Sample, Compression

3. **Camera & Device** (`camera`)
   - Camera settings and device information
   - Fields: Camera Make, Model, Lens Model, ISO, F-Number, Exposure Time, Focal Length, White Balance, Flash

4. **Video Properties** (`video`)
   - Video-specific metadata and properties
   - Fields: Video Width, Video Height, Duration, Frame Rate, Video Codec, Average Bitrate

5. **Audio Properties** (`audio`)
   - Audio-specific metadata and properties
   - Fields: Audio Channels, Sample Rate, Audio Format, Audio Bitrate

6. **Location & GPS** (`location`)
   - GPS coordinates and location information
   - Fields: Latitude, Longitude, Altitude, Map Datum

7. **Technical Details** (`technical`)
   - Technical metadata and processing information
   - Fields: ExifTool Version, File Permissions

## Core Components

### 1. DatabaseManager (Enhanced)

Extended with new methods for structured metadata:

- `create_metadata_category()`: Create new category
- `get_metadata_categories()`: Retrieve all categories
- `create_metadata_field()`: Create new field definition
- `get_metadata_fields()`: Retrieve field definitions
- `get_metadata_field_by_key()`: Get field by key
- `store_structured_metadata()`: Store structured field value
- `get_structured_metadata()`: Retrieve structured metadata
- `initialize_default_metadata_schema()`: Initialize default schema

### 2. StructuredMetadataManager

New manager class for handling structured metadata operations:

**Key Methods:**
- `process_and_store_metadata()`: Convert raw metadata to structured format
- `get_structured_metadata()`: Retrieve categorized metadata
- `get_field_value()`: Get specific field value
- `update_field_value()`: Update field value
- `add_custom_field()`: Add custom metadata field
- `get_available_fields()`: Get available field definitions
- `get_available_categories()`: Get available categories

**Features:**
- Automatic data type formatting
- Field validation and editing permissions
- Caching for performance
- Error handling and logging

### 3. MetadataManager (Enhanced)

Enhanced with structured metadata processing:

- `_process_structured_metadata()`: Process metadata after loading
- Integration with existing metadata workflow
- Automatic structured metadata creation

### 4. MetadataTreeView (Enhanced)

Enhanced with structured metadata display:

- `_try_structured_metadata_loading()`: Load structured metadata
- `display_structured_metadata()`: Display structured metadata
- `_flatten_structured_metadata()`: Convert to tree format
- `_format_structured_field_value()`: Format values for display
- `get_structured_field_value()`: Get field value
- `update_structured_field_value()`: Update field value

## Data Type Handling

The system supports various data types with appropriate formatting:

### Text (`text`)
- Default string representation
- Optional display format appending

### Number (`number`)
- Integer/float handling
- Display format support (e.g., "f/2.8", "400 ISO")
- Unit formatting (pixels, Hz, fps, kbps, etc.)

### Size (`size`)
- Byte size formatting
- Automatic unit conversion (B, KB, MB, GB)

### DateTime (`datetime`)
- Date and time representation
- Future: Custom date formatting

### Duration (`duration`)
- Time duration formatting
- Seconds, minutes:seconds, hours:minutes:seconds

### Coordinate (`coordinate`)
- GPS coordinate formatting
- Decimal degrees with precision

## Usage Examples

### Basic Usage

```python
from core.structured_metadata_manager import get_structured_metadata_manager

# Get manager instance
sm = get_structured_metadata_manager()

# Process raw metadata
raw_metadata = {
    'EXIF:Make': 'Canon',
    'EXIF:Model': 'EOS 5D',
    'EXIF:ISO': '400',
    'System:FileSize': '8388608'
}

success = sm.process_and_store_metadata('/path/to/file.jpg', raw_metadata)

# Retrieve structured metadata
structured = sm.get_structured_metadata('/path/to/file.jpg')
for category_name, category_data in structured.items():
    print(f"Category: {category_data['display_name']}")
    for field_key, field_data in category_data['fields'].items():
        print(f"  {field_data['field_name']}: {field_data['value']}")
```

### Custom Field Creation

```python
# Add custom field
success = sm.add_custom_field(
    field_key='Custom:Rating',
    field_name='Photo Rating',
    category_name='image',
    data_type='number',
    is_editable=True,
    is_searchable=True
)

# Update field value
success = sm.update_field_value('/path/to/file.jpg', 'Custom:Rating', '5')
```

### Field Value Retrieval

```python
# Get specific field value
iso_value = sm.get_field_value('/path/to/file.jpg', 'EXIF:ISO')
print(f"ISO: {iso_value}")

# Get all available fields for a category
camera_fields = sm.get_available_fields('camera')
for field in camera_fields:
    print(f"{field['field_name']}: {field['field_key']}")
```

## Integration with Existing System

The structured metadata system integrates seamlessly with the existing metadata workflow:

1. **Metadata Loading**: When metadata is loaded, it's automatically processed and stored in structured format
2. **Tree View Display**: The metadata tree view can display structured metadata with proper categorization
3. **Field Editing**: Editable fields support updates through the structured system
4. **Column Management**: File table columns can be populated from structured metadata

## Migration and Compatibility

- **Database Migration**: Automatic migration from schema v2 to v3
- **Backward Compatibility**: Existing metadata cache system continues to work
- **Gradual Migration**: Raw metadata is converted to structured format on demand

## Performance Considerations

- **Caching**: Field definitions and categories are cached for performance
- **Indexing**: Proper database indexes for fast queries
- **Lazy Loading**: Structured metadata is loaded only when needed
- **Batch Processing**: Efficient batch operations for multiple files

## Future Enhancements

- **Search Functionality**: Full-text search across metadata fields
- **Custom Categories**: User-defined metadata categories
- **Field Validation**: Advanced field validation rules
- **Metadata Templates**: Predefined metadata templates for different file types
- **Export/Import**: Metadata export/import functionality
- **Metadata Synchronization**: Sync metadata across multiple files

## Error Handling

The system includes comprehensive error handling:
- Database connection errors
- Field validation errors
- Data type conversion errors
- Missing field definitions
- Logging for debugging and monitoring

## Configuration

The system can be configured through:
- Default field definitions
- Category organization
- Data type formatting rules
- Field editing permissions
- Display formatting options

This structured metadata system provides a robust foundation for advanced metadata management while maintaining compatibility with existing functionality.
