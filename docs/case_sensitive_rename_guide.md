# Case-Sensitive Rename Support

## Problem on Windows

On Windows, the file system (NTFS) is case-insensitive, which means it considers files like `DOCUMENT.txt` and `document.txt` as the same file. This creates problems when we want to change only the case of letters.

## Application Solution

The oncutf application fully supports case-only renames through an intelligent two-step process:

### Automatic Detection
- The application automatically recognizes when a change affects only the case
- No special configuration required from the user

### Two-Step Process (Windows)
1. **Step 1**: Rename to temporary name
   - `DOCUMENT.txt` → `_temp_rename_123456.tmp`

2. **Step 2**: Rename to final name
   - `_temp_rename_123456.tmp` → `document.txt`

### Safety and Reliability
- **Cleanup**: In case of error, the application restores the original file
- **Unique temp names**: Uses hash for unique temporary names
- **Cross-platform**: Works correctly on Windows, Linux, and macOS

## Usage Examples

### Greek Files
```
ΕΡΓΑΣΙΑ.docx → εργασία.docx
ΦΩΤΟΓΡΑΦΊΑ.jpg → Φωτογραφία.jpg
ΜΟΥΣΙΚΗ.mp3 → μουσική.mp3
```

### English Files
```
DOCUMENT.pdf → document.pdf
FILE.TXT → File.txt
IMAGE.PNG → image.png
```

### Mixed Case
```
MyDocument.docx → mydocument.docx
TestFile.txt → TESTFILE.TXT
Project_2024.xlsx → project_2024.xlsx
```

## Supported Systems

| System | Support | Method |
|--------|---------|--------|
| Windows 10/11 | ✅ | Two-step |
| Linux | ✅ | Direct |
| macOS | ✅ | Direct |

## Logging and Debugging

The application logs all case-only operations:

```
[INFO] Successfully completed case-only rename: DOCUMENT.txt -> document.txt
[DEBUG] Case rename step 1: DOCUMENT.txt -> _temp_rename_123456.tmp
[DEBUG] Case rename step 2: _temp_rename_123456.tmp -> document.txt
```

## Technical Details

### Case-Only Change Detection
```python
def is_case_only_change(old: str, new: str) -> bool:
    return old.lower() == new.lower() and old != new
```

### Platform Detection
- Automatic operating system detection
- Special handling only for Windows
- Fallback to regular rename for other systems

## Usage with Rename Modules

Case-sensitive rename works with all rename modules:

- **Name Transform Module**: Case changes (uppercase, lowercase, title case)
- **Metadata Module**: Using metadata containing different case
- **Counter Module**: Combination with counters
- **Specified Text Module**: Text replacement with different case

## Tips

1. **Preview**: Always check the preview before renaming
2. **Backup**: Keep backups of important files
3. **Testing**: Test first with a few files
4. **Logs**: Check logs in case of problems

## Troubleshooting

### If Rename Fails
1. Check if the file is in use
2. Ensure you have write permissions
3. Check logs for errors
4. Try with a smaller batch of files

### Known Limitations
- Does not work if the file is open in another application
- Requires write permissions to the folder
- Temporary file is created in the same folder

## How It Works

### Normal Rename vs Case-Only Rename

**Normal Rename (file1.txt → file2.txt)**:
```
os.rename(src_path, dst_path)  # Works directly
```

**Case-Only Rename (FILE.txt → file.txt)**:
```
# Windows: Two-step process
os.rename("FILE.txt", "_temp_rename_123456.tmp")
os.rename("_temp_rename_123456.tmp", "file.txt")

# Linux/macOS: Direct rename (case-sensitive filesystem)
os.rename("FILE.txt", "file.txt")  # Works directly
```

### Error Recovery

If something goes wrong during the two-step process:

1. **Step 1 fails**: Original file remains unchanged
2. **Step 2 fails**: Application attempts to restore original file from temp
3. **Complete failure**: Logs error and marks operation as failed

## Integration with Batch Operations

The case-sensitive rename feature integrates seamlessly with:

- **Batch rename operations**: Handles mixed case-only and regular renames
- **Conflict resolution**: Case-only changes don't trigger conflict dialogs
- **Undo functionality**: Supports undoing case-only renames
- **Progress tracking**: Shows progress for large batches

## Performance Considerations

- **Speed**: Case-only renames are slightly slower on Windows due to two-step process
- **Safety**: Extra steps ensure data integrity
- **Memory**: Minimal additional memory usage
- **Logging**: Detailed logging for debugging without performance impact

## Related Documentation

- **Database System**: [Database Quick Start](database_quick_start.md) | [Database System](database_system.md)
- **Safe Operations**: [Safe Rename Workflow](safe_rename_workflow.md)
- **Progress Tracking**: [Progress Manager System](progress_manager_system.md)
- **Configuration**: [JSON Config System](json_config_system.md)
- **Module Reference**: [oncutf Module Docstrings](oncutf_module_docstrings.md)
