# oncutf

**oncutf** is a comprehensive file renaming tool that combines the power of [ExifTool](https://exiftool.org/) with an intuitive PyQt5 GUI. Designed for photographers, content creators, and digital archivists who need precise control over their file naming workflows.

<p align="center">
  <img src="assets/oncut_logo_white_w_dark_BG.png" alt="oncut logo" width="150"/>
</p>

---

## Key Features

### Modular Rename System
- **Original Name**: Preserve original filename with optional Greek-to-Greeklish conversion
- **Specified Text**: Add custom text with context menu shortcuts and original name insertion
- **Counter**: Sequential numbering with configurable start, step, and padding
- **Metadata**: Extract file dates or EXIF/metadata fields for filename generation
- **Name Transform**: Apply case transformations (lower, UPPER, Capitalize) and separator styles (snake_case, kebab-case, space)

### Advanced File Management
- **Drag & Drop Interface**:
  - File tree to table: Import files/folders with modifier-based metadata loading
  - File table to metadata tree: Quick metadata inspection (Shift for extended metadata)
  - Multi-selection support with visual feedback
- **Intelligent Metadata Loading**:
  - Fast metadata scanning for common fields
  - Extended metadata extraction for comprehensive EXIF data
  - Persistent ExifTool process for optimal performance
  - Smart caching system to avoid redundant operations

### Professional UI/UX
- **Live Preview**: Real-time filename preview before applying changes
- **Visual Feedback**: Professional icons, tooltips, and status indicators
- **Conflict Resolution**: Overwrite/Skip/Cancel options for existing files
- **Responsive Layout**: Splitter-based interface with memory of panel sizes
- **Context Menus**: Rich right-click functionality throughout the interface

### Metadata Integration
- **File Dates**: Last modified in various formats (ISO, European, US, year-only, etc.)
- **EXIF Data**: Camera settings, GPS coordinates, creation dates, and technical metadata
- **Dynamic Field Discovery**: Automatically detects available metadata fields from loaded files
- **Metadata Tree View**: Hierarchical display with copy/edit/reset capabilities

---

## Requirements

- **Python 3.9+**
- **[ExifTool](https://exiftool.org/)** - Must be installed and available in system PATH
- **PyQt5** - GUI framework

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Installation & Usage

```bash
# Clone the repository
git clone https://github.com/mecondev/oncutf.git
cd oncutf

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Basic Workflow

1. **Load Files**: Drag folders/files into the application or use the browse button
2. **Configure Modules**: Set up rename modules in the desired order
3. **Preview Results**: Review the generated filenames in the preview pane
4. **Apply Changes**: Click "Rename" to execute the file renaming operation

### Keyboard Shortcuts & Modifiers

- **Ctrl+A**: Select all files
- **Ctrl+D**: Clear selection
- **Ctrl+I**: Invert selection
- **Ctrl+R**: Force reload current folder
- **F5**: Load basic metadata for selected files
- **Ctrl+F5**: Load extended metadata for selected files

**Drag & Drop Modifiers:**
- No modifier: Skip metadata loading (folders) / Fast metadata (file-to-metadata)
- **Ctrl**: Load basic metadata
- **Ctrl+Shift**: Load extended metadata
- **Shift**: Extended metadata (file-to-metadata drag only)

---

## Development

### Project Architecture

```
oncutf/
├── main.py                 # Application entry point
├── main_window.py          # Main window and core logic
├── models/                 # Data structures (FileItem, etc.)
├── modules/                # Rename logic modules
│   ├── base_module.py      # Base class with signal optimization
│   ├── counter_module.py   # Sequential numbering
│   ├── specified_text_module.py  # Custom text insertion
│   ├── metadata_module.py  # File dates and EXIF extraction
│   └── name_transform_module.py   # Case and separator transforms
├── widgets/                # PyQt5 UI components
│   ├── file_tree_view.py   # Folder navigation with drag support
│   ├── file_table_view.py  # File list with multi-selection
│   ├── metadata_tree_view.py      # Hierarchical metadata display
│   ├── rename_modules_area.py     # Module container and management
│   └── preview_tables_view.py     # Before/after filename preview
├── utils/                  # Helper utilities
│   ├── exiftool_wrapper.py # Persistent ExifTool integration
│   ├── metadata_loader.py  # Threaded metadata processing
│   ├── metadata_cache.py   # Intelligent caching system
│   └── drag_visual_manager.py     # Advanced drag & drop feedback
└── tests/                  # Comprehensive test suite
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=widgets --cov=modules --cov=utils --cov=main_window --cov-report=term-missing

# Run specific test modules
pytest tests/test_custom_msgdialog.py -v
```

### Code Quality

The project uses `pyproject.toml` for configuration. **Linting is disabled for PyQt5 projects** in CI due to numerous false positives with type hints and Qt attribute resolution.

For local development:

```bash
# Install development dependencies
pip install -e .[dev]

# Run pylint (configured to ignore PyQt5 false positives)
pylint main_window.py --rcfile=.pylintrc

# Run mypy (configured in pyproject.toml)
mypy main_window.py
```

**Note**: PyQt5 generates many false positive warnings with static analysis tools. The configurations are specifically tuned to ignore these known issues while maintaining useful code quality checks.

---

## Technical Highlights

### Performance Optimizations
- **Persistent ExifTool Process**: Uses `-stay_open` mode for fast metadata extraction
- **Intelligent Caching**: Avoids redundant metadata reads with smart cache invalidation
- **Threaded Operations**: Non-blocking metadata loading with progress feedback
- **Signal Debouncing**: Prevents excessive UI updates during rapid changes

### Advanced Drag & Drop System
- **Multi-Selection Aware**: Handles complex selection scenarios with modifier keys
- **Visual Feedback**: Real-time drop zone highlighting and cursor changes
- **Conflict Resolution**: Smart handling of Qt selection conflicts during drag operations
- **Cross-Widget Communication**: Seamless data transfer between file tree, table, and metadata views

### Robust Error Handling
- **Graceful Degradation**: Continues operation even when ExifTool encounters issues
- **User-Friendly Messages**: Clear error reporting without technical jargon
- **Recovery Mechanisms**: Automatic cleanup and state restoration after failures

---

## Project & Creator

**oncutf** is created by [Michael Economou](https://oncut.gr) as a personal tool to support creative video and photo workflows. The project emphasizes reliability, performance, and user experience over feature bloat.

### Links

- **Website**: [oncut.gr](https://oncut.gr)
- **Instagram**: [@oncut.gr](https://instagram.com/oncut.gr)
- **Facebook**: [Oncut](https://facebook.com/oncut.gr)
- **GitHub**: [mecondev/oncutf](https://github.com/mecondev/oncutf)

> This is a hobbyist project. Not affiliated with or endorsed by ExifTool or PyQt5.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full details.

---

## Acknowledgments

- **[ExifTool](https://exiftool.org/)** by Phil Harvey - The backbone of metadata extraction
- **PyQt5** by Riverbank Computing - Robust GUI framework
- **The open-source community** - For inspiration and best practices
