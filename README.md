# oncutf

**oncutf** is a personal open-source tool for renaming files based on EXIF metadata.
It combines the flexibility of [ExifTool](https://exiftool.org/) with the convenience of a PyQt5 GUI.

Built for creators, photographers, and archivists who want their filenames to reflect real metadata — like capture date, duration, or any embedded tag.

<p align="center">
  <img src="assets/oncut-logo-2024-CIRCLE-(1100X1100)-dark-w-white-BG.png" alt="oncut logo" width="200"/>
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

## 📁 Project Structure

```
oncutf/
├── assets/              # Logos, favicon, screenshots
├── main.py              # Entry point for the application
├── models/              # File data structures
├── modules/             # Rename logic (e.g. counter, EXIF field, etc.)
├── utils/               # Helper tools (e.g. metadata parser)
├── widgets/             # PyQt UI components
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
