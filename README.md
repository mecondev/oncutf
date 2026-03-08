# oncutf

**oncutf** is a comprehensive file renaming tool with an intuitive PyQt5 GUI. Designed for photographers, content creators, and digital archivists who need precise control over their file naming workflows.

<p align="center">
  <img src="assets/oncut_logo_white_w_dark_BG.png" alt="oncut logo" width="150"/>
</p>

---

## 🚀 Quick Links

- **[Architecture Guide](docs/ARCHITECTURE.md)** — System design & layer structure
- **[Master Plan](docs/2025_12_19.md)** — Current status and next steps
- **[Development Roadmap](docs/ROADMAP.md)** — Phase progress and milestones

---

## Key Features

### Modular Rename System

- **Original Name**: Preserve original filename with optional Greek-to-Greeklish conversion
- **Specified Text**: Add custom text with context menu shortcuts and original name insertion
- **Counter**: Sequential numbering with configurable start, step, and padding
- **Metadata**: Extract file dates or metadata fields for filename generation
- **Name Transform**: Apply case transformations (lower, UPPER, Capitalize) and separator styles (snake_case, kebab-case, space)
- **Final Transform**: Post-processing options for case, separator, and Greek-to-Greeklish conversion

### Data Protection & Reliability

- **Automatic Backup System**: Database backups on shutdown and periodic intervals (every 15 minutes)
- **Persistent Storage**: SQLite-based database for metadata, hashes, and rename history
- **Enhanced Stability**: Robust error handling and recovery mechanisms for Qt object lifecycle
- **Data Integrity**: Backup rotation with configurable retention and timestamp naming

### Advanced File Management

- **Drag & Drop Interface**:
  - File tree to table: Import files/folders with modifier-based metadata loading
  - File table to metadata tree: Quick metadata inspection (Shift for extended metadata)
  - Multi-selection support with visual feedback
- **Intelligent Metadata Loading**:
  - Fast metadata scanning for common fields
  - Extended metadata extraction for comprehensive data
  - Smart caching system to avoid redundant operations

### Professional UI/UX

- **Live Preview**: Real-time filename preview before applying changes
- **Visual Feedback**: Professional icons, tooltips, and status indicators
- **Conflict Resolution**: Overwrite/Skip/Cancel options for existing files
- **Responsive Layout**: Splitter-based interface with memory of panel sizes
- **Context Menus**: Rich right-click functionality throughout the interface
- **Configuration Management**: JSON-based settings with automatic backup and cross-platform support

### Metadata Integration

- **File Dates**: Last modified in various formats (ISO, European, US, year-only, etc.)
- **Metadata Fields**: Camera settings, GPS coordinates, creation dates, and technical metadata
- **Dynamic Field Discovery**: Automatically detects available metadata fields from loaded files
- **Metadata Tree View**: Hierarchical display with copy/edit/reset capabilities

---

## Requirements

- **Python 3.12+**
- **[ExifTool](https://exiftool.org/)** - Must be installed and available in system PATH
- **PyQt5** - GUI framework

### Installing ExifTool

**Windows:**

1. Download from [ExifTool website](https://exiftool.org/)
2. Extract to a folder (e.g., `C:\exiftool`)
3. Add the folder to your system PATH

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get install exiftool
```

**macOS:**

```bash
brew install exiftool
```

**Manual Installation:**

1. Download from [ExifTool website](https://exiftool.org/)
2. Extract and add to PATH

**Verify Installation:**

```bash
exiftool -ver
```

---

## Installation & Usage

### Quick Start

```bash
# Clone the repository
git clone https://github.com/mecondev/oncutf.git
cd oncutf

# Install Python dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

> **Note:** The application uses Inter fonts from `resources/fonts/` by default.
> The `scripts/generate_fonts_rc.py` script is only needed for embedded font mode
> (e.g., PyInstaller packaging). See `oncutf/config.py` → `USE_EMBEDDED_FONTS`.

### Alternative Installation

```bash
# Install in development mode
pip install -e .

# Run with specific Python version
python3.12 main.py
```

### Basic Workflow

1. **Load Files**: Drag folders/files into the application or use the browse button
2. **Configure Modules**: Set up rename modules in the desired order
3. **Preview Results**: Review the generated filenames in the preview pane
4. **Apply Changes**: Click "Rename" to execute the file renaming operation

### Keyboard Shortcuts & Modifiers

#### Global Shortcuts (work regardless of focus)

- **Ctrl+O**: Browse for files/folders
- **Ctrl+S**: Save all metadata
- **Ctrl+L**: Show hash results dialog
- **Ctrl+Z**: Undo last operation
- **Ctrl+Shift+Z**: Redo last operation
- **Ctrl+Y**: Show command history dialog
- **Escape**: Cancel drag operations
- **Shift+Escape**: Clear file table

#### Widget-Specific F5 (Refresh)

- **F5 (File Table)**: Reload files from current folder
- **F5 (File Tree)**: Refresh file tree view
- **F5 (Metadata Tree)**: Reload metadata from selection
- **F5 (Preview)**: Refresh preview tables

#### File Table Shortcuts (when file table has focus)

- **Ctrl+A**: Select all files
- **Ctrl+Shift+A**: Clear selection
- **Ctrl+I**: Invert selection
- **Ctrl+M**: Load basic metadata for selected files
- **Ctrl+Shift+M**: Load extended metadata for selected files
- **Ctrl+H**: Calculate hash checksums for selected files
- **Ctrl+T**: Auto-fit columns to content
- **Ctrl+Shift+T**: Reset columns to default widths

#### Column Management Shortcuts (when hovering over column header)

- **Ctrl+Left**: Move hovered column left (columns must be unlocked)
- **Ctrl+Right**: Move hovered column right (columns must be unlocked)

**Note:** Column reordering is hover-based — no need to click the column header. Simply hover over it and press Ctrl+Left/Right. Columns must be unlocked via the header context menu (right-click on any column header).

**Drag & Drop Modifiers:**

- No modifier: Skip metadata loading (folders) / Fast metadata (file-to-metadata)
- **Ctrl**: Load basic metadata
- **Ctrl+Shift**: Load extended metadata
- **Shift**: Extended metadata (file-to-metadata drag only)

---

## Selection & Modifier Behavior (File Table)

### Single Click

- **No Modifier**: Select clicked row, deselect others
- **Ctrl**: Toggle clicked row (add/remove from selection)
- **Shift**: Extend selection from anchor to clicked row

### Drag Operations

- **Drag to Metadata Tree (No Modifier)**: Load fast metadata for selected files
- **Drag to Metadata Tree (Shift)**: Load extended metadata for selected files (requires 3x normal drag distance to prevent accidental triggers)
- **Ctrl+Drag (Lasso)**: Select/deselect rows in range; initial selection XOR dragged range. Compatible with Windows Explorer behavior

### Multi-Selection Behavior

- Clicking on already-selected item (no modifier): Preserves multi-selection for drag. If no drag occurs, converts to single selection
- Anchor row is maintained for Shift+Click range selection
- Selection restored after metadata operations

---

## Project Structure

```tree
oncutf/
├── main.py                  # Slim entry point (delegates to boot/)
├── config.py                # Global configuration constants
├── ui/                      # UI layer (PyQt5 widgets)
│   ├── main_window.py       # Main window wired to controllers
│   ├── behaviors/           # Reusable UI behaviors (column mgmt, drag feedback)
│   ├── delegates/           # Custom item delegates (color, validation)
│   ├── dialogs/             # Dialog windows (metadata edit, history)
│   ├── services/            # UI-specific services
│   └── widgets/             # Custom PyQt5 widgets
├── controllers/             # UI-agnostic orchestration layer
│   ├── file_load_controller.py
│   ├── metadata_controller.py
│   ├── rename_controller.py
│   └── main_window_controller.py
├── core/                    # Business logic (organized subdirectories)
│   ├── cache/               # Cache management (3 modules)
│   ├── database/            # Database operations (2 modules)
│   ├── drag/                # Drag & drop handling (3 modules)
│   ├── events/              # Event handlers (3 modules)
│   ├── hash/                # Hash operations (4 modules)
│   ├── initialization/      # Startup logic (3 modules)
│   ├── metadata/            # Metadata operations (4 modules)
│   ├── rename/              # Rename engine (3 modules)
│   ├── selection/           # Selection state (2 modules)
│   ├── ui_managers/         # UI managers (7 modules)
│   └── ...                  # Other flat modules
├── domain/                  # Pure domain models
├── models/                  # Data models (FileItem, etc.)
├── modules/                 # Rename modules (composable steps)
├── services/                # Service protocols (DI support)
├── utils/                   # Helper utilities
├── docs/                    # Documentation (see docs/README.md)
├── tests/                   # Comprehensive test suite (939 tests)
├── scripts/                 # Tooling (profiling, maintenance)
└── assets/resources/        # Icons, fonts, images
```

---

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Complete Documentation Index](docs/README.md)** — Overview and navigation
- **[Architecture Guide](docs/ARCHITECTURE.md)** — System design and layer structure
- **[Keyboard Shortcuts Reference](docs/keyboard_shortcuts.md)** — Complete keyboard shortcuts guide
- **[Application Workflow](docs/application_workflow.md)** — Complete application flow from startup to rename execution
- **[Database Quick Start](docs/database_quick_start.md)** — Get started with persistent storage
- **[Database System](docs/database_system.md)** — SQLite-based persistence architecture
- **[Structured Metadata System](docs/structured_metadata_system.md)** — Advanced metadata organization and processing
- **[Safe Rename Workflow](docs/safe_rename_workflow.md)** — Enhanced rename operations
- **[Progress Manager System](docs/progress_manager_system.md)** — Unified progress tracking
- **[JSON Config System](docs/json_config_system.md)** — Configuration management

---

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=widgets --cov=modules --cov=utils --cov=core --cov-report=term-missing

# Run specific test modules
pytest tests/test_rename_logic.py -v
```

### Code Quality

The project uses `pyproject.toml` for all tool configuration.

```bash
# Install development dependencies
pip install -e .[dev]

# Run linting (ruff)
ruff check .

# Run type checking (mypy)
mypy .

# Run all tests
pytest tests/ -v
```

**Current Status:**

- **Ruff:** All checks passing
- **MyPy:** Clean (0 errors, 330 source files)
- **Pytest:** 949 tests passing

### Future Enhancements

See [TODO.md](TODO.md) for planned features and improvements:

- Last state restoration (sort column persistence)
- Non-blocking conflict resolution UI
- Metadata database search functionality
- Rename preview profiling

See [docs/REFACTORING_ROADMAP.md](docs/REFACTORING_ROADMAP.md) for technical debt and planned refactoring.

### Development Guidelines

**Canonical Patterns (Single Source of Truth):**

| Domain | Canonical | Legacy/Supporting |
| -------- | ----------- | ------------------- |
| Rename Pipeline | `UnifiedRenameEngine` | `utils/naming/*` (helpers only) |
| Column Management | `UnifiedColumnService` | `ColumnManager` (thin adapter) |
| UI Components | Behaviors (`ui/behaviors/`) | Mixins (no new mixins) |

**Rules:**

- All rename operations go through `UnifiedRenameEngine`
- New code uses Behaviors, not Mixins
- New column logic goes in `UnifiedColumnService`

---

## Technical Highlights

### Performance Optimizations

- **Advanced Cache System**: Multi-tier caching (memory + disk + database) for 500x speedup
- **Persistent ExifTool Process**: Uses `-stay_open` mode for fast metadata extraction
- **Intelligent Caching**: Smart cache invalidation with 90%+ hit rates
- **Threaded Operations**: Non-blocking metadata loading with progress feedback
- **Batch Operations**: Efficient processing of multiple files (10x speedup)
- **Signal Debouncing**: Prevents excessive UI updates during rapid changes
- **Cross-Platform Path Handling**: Normalized path operations for Windows/Linux compatibility

### Data Protection & Backup System

- **Automatic Database Backups**: Scheduled backups every 15 minutes + shutdown backups
- **Backup Rotation**: Configurable backup count with automatic cleanup of old backups
- **Persistent Storage**: SQLite database with WAL mode for better concurrency
- **Data Recovery**: Comprehensive backup system with timestamp-based file naming

### Advanced Drag & Drop System

- **Multi-Selection Aware**: Handles complex selection scenarios with modifier keys
- **Visual Feedback**: Real-time drop zone highlighting and cursor changes
- **Conflict Resolution**: Smart handling of Qt selection conflicts during drag operations
- **Cross-Widget Communication**: Seamless data transfer between file tree, table, and metadata views

### Robust Error Handling

- **Graceful Degradation**: Continues operation even when ExifTool encounters issues
- **User-Friendly Messages**: Clear error reporting without technical jargon
- **Recovery Mechanisms**: Automatic cleanup and state restoration after failures
- **Qt Object Lifecycle Management**: Enhanced tooltip system with proper cleanup and error recovery

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
