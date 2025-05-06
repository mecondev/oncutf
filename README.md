# ReNExif

![Docstring Coverage](https://img.shields.io/badge/docstrings-100%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

ReNExif is a modular batch file renaming application designed for photographers, videographers, and digital archivists. It combines a clean, intuitive PyQt5 GUI with powerful rename modules that can be composed dynamically to rename large sets of files based on metadata, custom patterns, or static text.

---

## 🎯 Key Features

- ✅ Modular rename system: combine multiple rename operations in sequence
- 📸 EXIF & file metadata support via ExifTool
- 🔢 Auto-incrementing counters with configurable padding, start, and step
- 🔤 Insert specified static text in filenames
- 📅 Insert file date or custom metadata field
- 👀 Real-time preview of filename changes
- 🧼 Filename validation for cross-platform compatibility
- 🌙 Dark and light themes (QSS-based)
- 🪟 PyQt5 interface, responsive and customizable

---

## 🧩 Rename Modules

Each rename module is independently configurable:

| Module               | Description                       |
|----------------------|-----------------------------------|
| `CounterModule`      | Adds an incrementing number       |
| `SpecifiedTextModule`| Inserts custom static text        |
| `MetadataModule`     | Uses file or EXIF metadata        |

More modules can be added by extending the `modules/` directory.

---

## 🖼️ GUI Overview

The interface is divided into several sections:

- 📁 Folder browser tree
- 📄 File list with checkboxes and validation icons
- 🧠 Metadata info panel
- 🧩 Rename module stack (add/remove/edit modules)
- 🔍 Preview area for original and new filenames
- 🟢 Action buttons for Rename / Reset

---

## 🚀 Getting Started

### Requirements

- Python 3.10+
- `PyQt5`
- `exiftool` installed and available in PATH

### Installation

```bash
git clone https://github.com/mecondev/ReNExif.git
cd ReNExif
pip install -r requirements.txt
```

> You may need to install `exiftool` from https://exiftool.org/

### Run

```bash
python main.py
```

---

## 🗂️ Project Structure

- 📁 [Project Structure with Docstrings](reports/project_structure.md)
- 📄 [Module-Level Docstrings](ReNExif_module_docstrings.md)

---

## 📖 License

MIT License © 2025 Michael Economou
