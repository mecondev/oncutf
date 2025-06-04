# oncutf

**oncutf** is a personal open-source tool for renaming files based on EXIF metadata.
It combines the flexibility of [ExifTool](https://exiftool.org/) with the convenience of a PyQt5 GUI.

Built for creators, photographers, and archivists who want their filenames to reflect real metadata — like capture date, duration, or any embedded tag.

<p align="center">
  <img src="assets/oncut_logo_white_w_dark_BG.png" alt="oncut logo" width="150"/>
</p>

---

## ✨ Features

- Rename files using EXIF tags (e.g. `CreateDate`, `Duration`, etc.)
- Modular rename system (add prefix, counter, EXIF fields, etc.)
- Clean PyQt5-based GUI
- Live preview before renaming
- Overwrite / Skip / Cancel logic
- EXIF reading via subprocess (ExifTool)
- Multi-platform ready (Windows, Linux, macOS)

---

## 🛠 Requirements

- Python 3.9+
- [ExifTool](https://exiftool.org/) — must be installed and available in system path
- PyQt5

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

```bash
python main.py
```

1. Select a folder with media files.
2. Choose which files to rename.
3. Configure rename modules (e.g. prefix, counter, EXIF tag).
4. Preview the result.
5. Click **Rename**.

---

## 🧪 Development

### Running Tests

The project includes comprehensive test coverage for core functionality:

```bash
# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=widgets --cov=modules --cov=utils --cov=main_window --cov-report=term-missing

# Run specific test modules
pytest tests/test_custom_msgdialog.py -v
```

### Code Quality

The project uses `pyproject.toml` for configuration. Note that **linting is disabled for PyQt5 projects** in CI due to numerous false positives with type hints and Qt attribute resolution.

For local development, you can run:

```bash
# Install development dependencies
pip install -e .[dev]

# Run pylint (configured to ignore PyQt5 false positives)
pylint main_window.py --rcfile=.pylintrc

# Run mypy (configured in pyproject.toml)
mypy main_window.py
```

**Note**: PyQt5 generates many false positive warnings with static analysis tools. The configurations in `pyproject.toml` and `.pylintrc` are specifically tuned to ignore these known issues while maintaining useful code quality checks.

---

## 📁 Project Structure

```
oncutf/
├── assets/              # Logos, favicon, screenshots
├── main.py              # Entry point for the application
├── models/              # File data structures
├── modules/             # Rename logic (e.g. counter, EXIF field, etc.)
├── utils/               # Helper tools (e.g. metadata parser)
├── widgets/             # PyQt UI components
├── tests/               # Test suite
├── pyproject.toml       # Project configuration
└── README.md
```

---

## 🌐 Project & Creator

**oncutf** is created by [Michael Economou](https://oncut.gr),
as a personal non-commercial tool to support creative video & photo workflows.

### 🔗 Links

- 🌍 Website: [oncut.gr](https://oncut.gr)
- 📷 Instagram: [@oncut.gr](https://instagram.com/oncut.gr)
- 📘 Facebook: [Oncut](https://facebook.com/oncut.gr)

> This is a hobbyist project. Not affiliated with or endorsed by ExifTool or PyQt5.

---

## 🪪 License

This project is licensed under the MIT License.
See the [LICENSE](LICENSE) file for full details.

---

## 🙏 Acknowledgments

- [ExifTool](https://exiftool.org/) by Phil Harvey
- PyQt5 by Riverbank Computing
- The open-source community
