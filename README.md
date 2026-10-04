# 🧹 FileSweep

**FileSweep** is a powerful command-line tool to scan, summarize, and organize your files — right from the terminal. It categorizes every file, detects duplicates, flags vague filenames, and shows you exactly where your disk space is going.

---

## ✨ Features

- 📂 **Smart Categorization** — Automatically sorts files into categories: Documents, Images, Videos, Audio, Code, Archives, Installers, Temp, and more
- 🔍 **Duplicate Detection** — Uses a fast 3-stage hashing strategy (size → 64KB head hash → full SHA-256) to find exact duplicate files and show wasted space
- ⚠️ **Vague Name Detection** — Flags files with meaningless names like `document1.pdf`, `untitled.png`, or hex-named files
- 📊 **Summary Table** — Shows a quick breakdown of file counts and sizes per category with a visual bar
- 🏆 **Top Largest Files** — Instantly find the biggest space hogs in any folder
- 🔎 **File Finder & Opener** — Search for any file by name and open it with one command
- 🎨 **Color-coded Output** — Rich ANSI-colored terminal output (auto-disabled when not supported)
- ⚡ **Fast** — Handles up to 50,000 files per scan, skips system/hidden directories automatically

---

## 📦 Installation

### Requirements
- Python 3.8+

### Install from source

```bash
git clone https://github.com/ROOKIEEE12/file_sweep.git
cd file_sweep
pip install .
```

After installation, the `filesweep` command will be available globally.

---

## 🚀 Usage

### `scan` — Scan and summarize a folder

```bash
# Scan your home directory (default)
filesweep scan

# Scan a specific folder
filesweep scan C:\Users\amitg\Documents

# Show individual files per category
filesweep scan --detail

# Show files for a specific category only
filesweep scan --category Images

# Scan top-level only (no subdirectories)
filesweep scan --shallow

# Show full file paths
filesweep scan --detail --full-path

# Limit files shown per category (default: 15)
filesweep scan --detail --limit 30

# Skip duplicate detection (faster scan)
filesweep scan --no-dupes
```

**Example output:**
```
============================================================
  FileSweep  --  C:\Users\amitg
============================================================

  SUMMARY
  ----------------------------------------
  Images                    412 files      1.2 GB  ||||||||||||||||||||
  Documents                 210 files    340.5 MB  ||||||||||||||||||||
  Videos                     38 files      8.4 GB  ||||||||||||||||||||
  Code                      124 files     15.2 MB  ||||||||||||||||
  ...

  Total files : 1024
  Total size  : 12.3 GB
  Duplicates  : 7 groups  (230.4 MB wasted)
```

---

### `dupes` — Find duplicate files

```bash
# Find duplicates in home directory
filesweep dupes

# Find duplicates in a specific folder
filesweep dupes C:\Users\amitg\Downloads

# Shallow scan (top-level only)
filesweep dupes --shallow
```

**Example output:**
```
  7 duplicate groups -- 230.4 MB wasted space

  Group 1  (45.2 MB each -- 2 copies)
    OK KEEP  C:\Users\amitg\Photos\holiday.jpg  2mo ago
    !! DUPE  C:\Users\amitg\Downloads\holiday.jpg  3mo ago
```

---

### `open` — Find and open a file by name

```bash
# Search for a file and open it
filesweep open report

# Search in a specific folder
filesweep open budget --path C:\Users\amitg\Documents
```

If multiple matches are found, it shows a numbered list and lets you pick which one to open.

---

### `top` — Show the largest files

```bash
# Show top 20 largest files in home directory
filesweep top

# Show top 10 largest files in a specific folder
filesweep top C:\Users\amitg\Downloads --n 10

# Shallow scan
filesweep top --shallow
```

---

## 📁 Project Structure

```
file_sweep/
├── filesweep/
│   ├── __init__.py       # Package entry
│   ├── cli.py            # CLI commands, argument parsing, colored output
│   └── scanner.py        # Core scanner: categorization, dedup, summaries
├── pyproject.toml        # Build config & package metadata
├── .gitignore
└── README.md
```

---

## 🗂️ Supported File Categories

| Category      | Extensions |
|---------------|------------|
| Documents     | `.pdf`, `.doc`, `.docx`, `.txt`, `.md`, `.odt`, `.rtf`, `.tex`, `.rst` |
| Spreadsheets  | `.xls`, `.xlsx`, `.csv`, `.ods` |
| Presentations | `.ppt`, `.pptx`, `.odp` |
| Images        | `.jpg`, `.png`, `.gif`, `.svg`, `.webp`, `.heic`, `.raw`, and more |
| Videos        | `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, and more |
| Audio         | `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, and more |
| Archives      | `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, and more |
| Installers    | `.exe`, `.msi`, `.dmg`, `.deb`, `.apk`, and more |
| Code          | `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.html`, `.json`, and more |
| Data          | `.db`, `.sqlite`, `.sql`, `.parquet` |
| Fonts         | `.ttf`, `.otf`, `.woff`, `.woff2` |
| eBooks        | `.epub`, `.mobi`, `.azw` |
| Temp          | `.tmp`, `.crdownload`, `.part`, `.download` |

---

## ⚙️ How Duplicate Detection Works

FileSweep uses a **3-stage strategy** for fast and accurate duplicate detection:

1. **Size filter** — Only files with the same size are candidates
2. **Head hash** — Reads the first 64KB and computes SHA-256 to quickly eliminate non-matches
3. **Full hash** — Full SHA-256 of confirmed candidates to guarantee exact matches

This approach is efficient even on large directories.

---

## 🪟 Windows Notes

- ANSI color output is automatically enabled on Windows 10+ via VT100 mode
- Set the `NO_COLOR` environment variable to disable colors entirely
- System directories like `AppData`, `Windows`, and `$Recycle.Bin` are automatically skipped

---

## 📄 License

MIT License. Feel free to use, modify, and distribute.

---

> Built with ❤️ using pure Python — no external dependencies required.
