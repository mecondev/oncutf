# oncutf Documentation

This directory contains comprehensive documentation for the oncutf application. The documentation is organized into several categories covering different aspects of the application's functionality and architecture.

## 📖 Quick Start

- **[Database Quick Start](database_quick_start.md)** - Get started with the persistent database system
- **[Progress Manager System](progress_manager_system.md)** - Understanding the unified progress tracking API

## 🔧 Core Systems

### Database & Storage
- **[Database System](database_system.md)** - Complete technical documentation for SQLite-based persistence
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
│  ├── Database System (SQLite + Caching)                │
│  ├── Safe Rename Workflow (Qt Safety)                  │
│  ├── Progress Manager (Unified Progress API)           │
│  ├── JSON Config System (Settings Management)          │
│  └── Case-Sensitive Rename (Cross-platform)            │
├─────────────────────────────────────────────────────────┤
│  📋 Features                                            │
│  ├── Persistent Metadata Storage                       │
│  ├── Hash Caching & Duplicate Detection                │
│  ├── Rename History & Undo/Redo                        │
│  ├── Cross-platform Case Renaming                      │
│  ├── Progress Tracking for All Operations              │
│  └── Robust Error Handling & Recovery                  │
└─────────────────────────────────────────────────────────┘
```

## 🔗 Documentation Cross-References

### Database System
- **Core**: [Database System](database_system.md)
- **Quick Start**: [Database Quick Start](database_quick_start.md)
- **Related**: [Safe Rename Workflow](safe_rename_workflow.md), [Progress Manager](progress_manager_system.md)

### Rename Operations
- **Safety**: [Safe Rename Workflow](safe_rename_workflow.md)
- **Case Handling**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md)
- **Related**: [Database System](database_system.md), [JSON Config](json_config_system.md)

### User Interface & Experience
- **Progress**: [Progress Manager System](progress_manager_system.md)
- **Configuration**: [JSON Config System](json_config_system.md)
- **Related**: [Database Quick Start](database_quick_start.md)

## 🚀 Key Features Covered

### Data Persistence & Performance
- **SQLite Database**: Persistent storage for metadata, hashes, and history
- **Memory Caching**: High-performance caching with database fallback
- **Connection Pooling**: Thread-safe database operations
- **Automatic Cleanup**: Orphaned record removal and maintenance

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

### Future Development
- Extensible architecture for new features
- Well-documented APIs for external integration
- Modular design supporting independent updates
- Backward compatibility preservation

## 🔧 Troubleshooting

For specific issues, check the relevant documentation:

1. **Database Issues**: [Database System](database_system.md#troubleshooting)
2. **Rename Problems**: [Safe Rename Workflow](safe_rename_workflow.md#troubleshooting)
3. **Case Rename Issues**: [Case-Sensitive Rename Guide](case_sensitive_rename_guide.md#troubleshooting)
4. **Progress Display**: [Progress Manager System](progress_manager_system.md#troubleshooting)
5. **Configuration**: [JSON Config System](json_config_system.md#troubleshooting)

## 📄 Additional Resources

- **Main README**: [../README.md](../README.md) - Project overview and installation
- **Test Suite**: [../tests/](../tests/) - Comprehensive test coverage
- **Examples**: [../examples/](../examples/) - Usage examples and demos
- **Scripts**: [../scripts/](../scripts/) - Utility scripts and tools

---

**Last Updated**: December 2024
**Version**: Compatible with oncutf v2.0+
**Maintained by**: [Michael Economou](https://oncut.gr)
