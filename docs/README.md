# oncutf Documentation

This directory contains comprehensive documentation for the oncutf application, a PyQt5 desktop app for advanced batch file renaming with EXIF/metadata support.

## 📢 Status Update

**Phase 0 Complete** (2025-12-15): All application code successfully migrated to `oncutf/` package structure. See [ROADMAP.md](ROADMAP.md) for details.

## 🚀 Quick Start

- **[ROADMAP](ROADMAP.md)** - Development roadmap and phase tracking
- **[ARCHITECTURE](ARCHITECTURE.md)** - System architecture overview
- **[Keyboard Shortcuts](keyboard_shortcuts.md)** - Complete keyboard shortcuts reference
- **[Database Quick Start](database_quick_start.md)** - Get started with the persistent database system

## 📋 Planning & Architecture

### Development Planning
- **[ARCH_REFACTOR_PLAN.md](ARCH_REFACTOR_PLAN.md)** - Detailed Phase 0-3 refactoring plan
- **[EXECUTION_ROADMAP.md](EXECUTION_ROADMAP.md)** - Step-by-step execution tracking
- **[ROADMAP.md](ROADMAP.md)** - Current development status and next steps
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - High-level architecture overview

### Core Systems Documentation
- **[Application Workflow](application_workflow.md)** - Complete application flow from startup to rename execution
- **[Database System](database_system.md)** - SQLite-based persistence architecture
- **[Structured Metadata System](structured_metadata_system.md)** - Metadata organization and processing
- **[Progress Manager System](progress_manager_system.md)** - Unified progress tracking API
- **[Safe Rename Workflow](safe_rename_workflow.md)** - Enhanced rename process with Qt safety
- **[JSON Config System](json_config_system.md)** - Configuration management

## 🔧 System Architecture

The oncutf application follows a layered package structure:

```
oncutf/
├── __init__.py
├── __main__.py              # Module entry point (python -m oncutf)
├── config.py                # Central configuration
├── models/                  # Data models
│   ├── file_entry.py
│   ├── file_item.py
│   ├── file_table_model.py
│   ├── metadata_entry.py
│   └── results_table_model.py
├── modules/                 # Rename modules
│   ├── base_module.py
│   ├── counter_module.py
│   ├── metadata_module.py
│   ├── name_transform_module.py
│   ├── original_name_module.py
│   ├── specified_text_module.py
│   └── text_removal_module.py
├── utils/                   # Utility functions (55 files)
│   ├── exiftool_wrapper.py
│   ├── path_utils.py
│   ├── timer_manager.py
│   └── ...
├── core/                    # Core business logic (60 files)
│   ├── application_context.py
│   ├── unified_rename_engine.py
│   ├── file_load_manager.py
│   ├── database_manager.py
│   └── ...
└── ui/                      # User interface
    ├── main_window.py
    ├── widgets/             # UI components (40 files)
    ├── mixins/              # UI mixins (7 files)
    ├── delegates/           # Item delegates
    └── dialogs/             # Dialog windows
```

### Core Features

```
┌─────────────────────────────────────────────────────────┐
│                    oncutf Application                   │
├─────────────────────────────────────────────────────────┤
│  🎯 Core Systems                                        │
│  ├── Application Workflow (Startup → Rename)           │
│  ├── Database System (SQLite + V3 Schema)              │
│  ├── Structured Metadata (Categorized + Typed)         │
│  ├── Safe Rename Workflow (Qt Safety)                  │
│  ├── Progress Manager (Unified Progress API)           │
│  └── JSON Config System (Settings Management)          │
├─────────────────────────────────────────────────────────┤
│  📋 Features                                            │
│  ├── Persistent Metadata Storage (Raw + Structured)    │
│  ├── Hash Caching & Duplicate Detection                │
│  ├── Rename History & Undo/Redo                        │
│  ├── Cross-platform Compatibility (Linux/Windows/macOS)│
│  ├── Progress Tracking for All Operations              │
│  ├── Debug Reset Features (Database + Config)          │
│  └── Robust Error Handling & Recovery                  │
└─────────────────────────────────────────────────────────┘
```

### Rename Operations
- **Safety**: [Safe Rename Workflow](safe_rename_workflow.md)
- **Case Handling**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md)
- **Application Flow**: [Application Workflow](application_workflow.md#rename-system-architecture)
- **Related**: [Database System](database_system.md), [JSON Config](json_config_system.md)

### User Interface & Experience
- **Progress**: [Progress Manager System](progress_manager_system.md)
- **Configuration**: [JSON Config System](json_config_system.md)
- **Related**: [Database Quick Start](database_quick_start.md)

## 🚀 Key Features Covered

### Data Persistence & Performance
- **SQLite Database V3**: Persistent storage with structured metadata support
- **Categorized Metadata**: Organized metadata with 7 default categories and 37 fields
- **Memory Caching**: High-performance caching with database fallback
- **Connection Pooling**: Thread-safe database operations
- **Automatic Cleanup**: Orphaned record removal and maintenance

### Application Architecture
- **Modular Design**: Separate managers for file loading, metadata, rename operations
- **Debug Features**: Database and config reset capabilities for development
- **Cache Systems**: Persistent metadata and hash caching between sessions
- **Error Resilience**: Robust error handling and recovery mechanisms

### Rename Safety & Reliability
- **Qt Lifecycle Safety**: Prevents crashes during UI updates
- **Two-Step Case Rename**: Windows NTFS case-insensitive handling
- **Error Recovery**: Comprehensive error handling and rollback
- **Undo/Redo Support**: Complete operation history with validation

### User Experience
- **Unified Progress API**: Consistent progress tracking across all operations
- **Real-time Feedback**: Live updates during long-running operations
- **Cross-platform Support**: Windows, Linux, and macOS compatibility
- **Persistent Settings**: JSON-based configuration with automatic backup

## 📝 Developer Notes

### Code Standards
- All documentation is in English for GitHub compatibility
- Code examples include type hints and proper error handling
- Cross-references between related systems and features
- Comprehensive API documentation with usage examples

### Testing Coverage
Each system includes:
- Unit tests for core functionality
- Integration tests for system interactions
- Performance benchmarks where applicable
- Error condition testing and recovery scenarios

### Debug & Development
- **Debug Reset Features**: Fresh database and config on startup
- **Comprehensive Logging**: Debug, info, warning, and error levels
- **Testing Framework**: Unit and integration tests with mock objects

### Future Development
- Extensible architecture for new features
- Well-documented APIs for external integration
- Modular design supporting independent updates
- Backward compatibility preservation

## 🔧 Troubleshooting

For specific issues, check the relevant documentation:

1. **Application Flow**: [Application Workflow](application_workflow.md#error-handling--logging)
2. **Database Issues**: [Database System](database_system.md#troubleshooting)
3. **Metadata Problems**: [Structured Metadata System](structured_metadata_system.md#troubleshooting)
4. **Rename Problems**: [Safe Rename Workflow](safe_rename_workflow.md#troubleshooting)
5. **Case Rename Issues**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md#troubleshooting)
6. **Progress Display**: [Progress Manager System](progress_manager_system.md#troubleshooting)
7. **Configuration**: [JSON Config System](json_config_system.md#troubleshooting)

## 📄 Additional Resources

- **Main README**: [../README.md](../README.md) - Project overview and installation
- **Test Suite**: [../tests/](../tests/) - Comprehensive test coverage
- **Examples**: [../examples/](../examples/) - Usage examples and demos
- **Scripts**: [../scripts/](../scripts/) - Utility scripts and tools

---

**Last Updated**: December 2024
**Version**: Compatible with oncutf v2.0+
**Maintained by**: [Michael Economou](https://oncut.gr)
