# oncutf Documentation

This directory contains comprehensive documentation for the oncutf application. The documentation is organized into several categories covering different aspects of the application's functionality and architecture.

## 🚀 Quick Start

- **[Application Workflow](application_workflow.md)** - Complete application flow from startup to rename execution
- **[Database Quick Start](database_quick_start.md)** - Get started with the persistent database system
- **[Progress Manager System](progress_manager_system.md)** - Understanding the unified progress tracking API
- **[Keyboard Shortcuts](keyboard_shortcuts.md)** - Complete keyboard shortcuts reference

## 🔧 Core Systems

### Application Architecture
- **[Application Workflow](application_workflow.md)** - Comprehensive guide to application initialization, file loading, metadata processing, and rename operations

### Database & Storage
- **[Database System](database_system.md)** - Complete technical documentation for SQLite-based persistence
- **[Structured Metadata System](structured_metadata_system.md)** - Advanced metadata organization and processing with categorized storage
- **[Database Quick Start](database_quick_start.md)** - Quick introduction to database features

### Rename Operations
- **[Safe Rename Workflow](safe_rename_workflow.md)** - Enhanced rename process with Qt lifecycle safety
- **[Case-Sensitive Rename Guide](case_sensitive_rename_guide.md)** - Cross-platform case-only file renaming

### Progress & UI
- **[Progress Manager System](progress_manager_system.md)** - Unified API for progress tracking across operations

### Configuration
- **[JSON Config System](json_config_system.md)** - JSON-based configuration management system

## 📚 Reference

- **[oncutf Module Docstrings](oncutf_module_docstrings.md)** - Complete module-level documentation reference

## 🏗️ System Architecture

The oncutf application is built with several interconnected systems:

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
│  ├── JSON Config System (Settings Management)          │
│  └── Case-Sensitive Rename (Cross-platform)            │
├─────────────────────────────────────────────────────────┤
│  📋 Features                                            │
│  ├── Persistent Metadata Storage (Raw + Structured)    │
│  ├── Hash Caching & Duplicate Detection                │
│  ├── Rename History & Undo/Redo                        │
│  ├── Cross-platform Case Renaming                      │
│  ├── Progress Tracking for All Operations              │
│  ├── Debug Reset Features (Database + Config)          │
│  └── Robust Error Handling & Recovery                  │
└─────────────────────────────────────────────────────────┘
```

## 🔗 Documentation Cross-References

### Application Flow
- **Complete Guide**: [Application Workflow](application_workflow.md)
- **Debug Features**: [Application Workflow](application_workflow.md#debug-reset-features)
- **Related**: [Database System](database_system.md), [Structured Metadata](structured_metadata_system.md)

### Database System
- **Core**: [Database System](database_system.md)
- **V3 Schema**: [Structured Metadata System](structured_metadata_system.md)
- **Quick Start**: [Database Quick Start](database_quick_start.md)
- **Related**: [Safe Rename Workflow](safe_rename_workflow.md), [Progress Manager](progress_manager_system.md)

### Metadata Processing
- **Structured System**: [Structured Metadata System](structured_metadata_system.md)
- **Application Flow**: [Application Workflow](application_workflow.md#metadata-loading-system)
- **Related**: [Database System](database_system.md)

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
