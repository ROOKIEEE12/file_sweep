"""
FileSweep Scanner
-----------------
Scans any directory recursively, categorizes every file,
generates a short human-readable summary, and spots duplicates.
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Category map (extension → category) ──────────────────────────────────────
CATEGORIES: dict[str, str] = {
    # Documents
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
    ".odt": "Documents", ".rtf": "Documents", ".txt": "Documents",
    ".md": "Documents", ".rst": "Documents", ".tex": "Documents",
    # Spreadsheets
    ".xls": "Spreadsheets", ".xlsx": "Spreadsheets", ".csv": "Spreadsheets",
    ".ods": "Spreadsheets",
    # Presentations
    ".ppt": "Presentations", ".pptx": "Presentations", ".odp": "Presentations",
    # Images
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
    ".bmp": "Images", ".svg": "Images", ".webp": "Images", ".ico": "Images",
    ".tiff": "Images", ".raw": "Images", ".heic": "Images",
    # Videos
    ".mp4": "Videos", ".mkv": "Videos", ".avi": "Videos", ".mov": "Videos",
    ".wmv": "Videos", ".flv": "Videos", ".webm": "Videos", ".m4v": "Videos",
    # Audio
    ".mp3": "Audio", ".wav": "Audio", ".aac": "Audio", ".flac": "Audio",
    ".ogg": "Audio", ".m4a": "Audio", ".wma": "Audio",
    # Archives
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives",
    ".tar": "Archives", ".gz": "Archives", ".tgz": "Archives",
    ".bz2": "Archives", ".xz": "Archives",
    # Installers
    ".exe": "Installers", ".msi": "Installers", ".dmg": "Installers",
    ".pkg": "Installers", ".deb": "Installers", ".rpm": "Installers",
    ".appimage": "Installers", ".apk": "Installers", ".msix": "Installers",
    ".msixbundle": "Installers", ".appx": "Installers",
    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".jsx": "Code",
    ".tsx": "Code", ".java": "Code", ".c": "Code", ".cpp": "Code",
    ".h": "Code", ".cs": "Code", ".go": "Code", ".rs": "Code",
    ".rb": "Code", ".php": "Code", ".swift": "Code", ".kt": "Code",
    ".sh": "Code", ".ps1": "Code", ".bat": "Code", ".html": "Code",
    ".css": "Code", ".scss": "Code", ".json": "Code", ".xml": "Code",
    ".yaml": "Code", ".yml": "Code", ".toml": "Code", ".ini": "Code",
    # Data / DB
    ".db": "Data", ".sqlite": "Data", ".sql": "Data", ".parquet": "Data",
    ".csv": "Data",
    # Fonts
    ".ttf": "Fonts", ".otf": "Fonts", ".woff": "Fonts", ".woff2": "Fonts",
    # E-books
    ".epub": "eBooks", ".mobi": "eBooks", ".azw": "eBooks",
    # Temp / junk
    ".crdownload": "Temp", ".part": "Temp", ".tmp": "Temp",
    ".download": "Temp", ".opdownload": "Temp",
}

INVOICE_RE = re.compile(r"(invoice|receipt|bill|\binv[-_ ]?\d)", re.I)
SCREENSHOT_RE = re.compile(r"^(screenshot|screen.?shot|snip|capture|screen.?rec)", re.I)
VAGUE_RE = re.compile(
    r"^(document|doc|file|scan|scanned|untitled|download|new|image|img|pdf|copy)?[\s_()\-\d]*$"
    r"|^[0-9a-f]{16,}$",
    re.I,
)


def _human_size(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _age(mtime: float) -> str:
    days = (time.time() - mtime) / 86400
    if days < 1:
        return "today"
    if days < 7:
        return f"{int(days)}d ago"
    if days < 30:
        return f"{int(days/7)}w ago"
    if days < 365:
        return f"{int(days/30)}mo ago"
    return f"{days/365:.1f}y ago"


def _summarize(path: Path, category: str) -> str:
    """Generate a short, human-readable description of a file."""
    ext = path.suffix.lower()
    size = _human_size(path.stat().st_size)
    age = _age(path.stat().st_mtime)
    name = path.stem

    # Invoice / receipt detection
    if INVOICE_RE.search(name):
        return f"📄 Likely an invoice or receipt ({size}, {age})"

    # Screenshot
    if SCREENSHOT_RE.match(name) and ext in {".png", ".jpg", ".jpeg"}:
        return f"📸 Screenshot ({size}, {age})"

    # Vague name
    if VAGUE_RE.match(name):
        return f"⚠️  Vaguely named {category.lower()} file — consider renaming ({size}, {age})"

    # Category-specific summaries
    labels = {
        "Documents": f"📃 Document file ({size}, {age})",
        "Spreadsheets": f"📊 Spreadsheet/data file ({size}, {age})",
        "Presentations": f"📑 Presentation file ({size}, {age})",
        "Images": f"🖼️  Image file ({size}, {age})",
        "Videos": f"🎬 Video file ({size}, {age})",
        "Audio": f"🎵 Audio file ({size}, {age})",
        "Archives": f"📦 Compressed archive — may contain multiple files ({size}, {age})",
        "Installers": f"⚙️  Installer/setup file ({size}, {age})",
        "Code": f"💻 Source code / config file ({size}, {age})",
        "Data": f"🗄️  Database or data file ({size}, {age})",
        "Fonts": f"🔤 Font file ({size}, {age})",
        "eBooks": f"📚 eBook ({size}, {age})",
        "Temp": f"🗑️  Temporary/partial download — safe to delete ({size}, {age})",
    }
    return labels.get(category, f"📁 {category} file ({size}, {age})")


@dataclass
class FileInfo:
    path: Path
    category: str
    summary: str
    size_bytes: int
    modified: float

    @property
    def size_human(self) -> str:
        return _human_size(self.size_bytes)

    @property
    def age(self) -> str:
        return _age(self.modified)

    @property
    def is_vague(self) -> bool:
        return bool(VAGUE_RE.match(self.path.stem))


@dataclass
class ScanResult:
    root: Path
    files: list[FileInfo] = field(default_factory=list)
    by_category: dict[str, list[FileInfo]] = field(default_factory=lambda: defaultdict(list))
    duplicates: list[list[FileInfo]] = field(default_factory=list)
    total_size: int = 0

    @property
    def total_files(self) -> int:
        return len(self.files)


# ── Duplicate detection ───────────────────────────────────────────────────────

def _hash_file(path: Path, limit: Optional[int] = None) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            if limit:
                h.update(f.read(limit))
            else:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
    except (PermissionError, OSError):
        return ""
    return h.hexdigest()


def find_duplicates(files: list[FileInfo]) -> list[list[FileInfo]]:
    """Size → 64KB head hash → full SHA-256. Returns groups of identical files."""
    by_size: dict[int, list[FileInfo]] = defaultdict(list)
    for fi in files:
        by_size[fi.size_bytes].append(fi)

    groups: list[list[FileInfo]] = []
    for size, same in by_size.items():
        if len(same) < 2 or size == 0:
            continue
        by_head: dict[str, list[FileInfo]] = defaultdict(list)
        for fi in same:
            h = _hash_file(fi.path, 65536)
            if h:
                by_head[h].append(fi)
        for cand in by_head.values():
            if len(cand) < 2:
                continue
            by_full: dict[str, list[FileInfo]] = defaultdict(list)
            for fi in cand:
                h = _hash_file(fi.path)
                if h:
                    by_full[h].append(fi)
            for g in by_full.values():
                if len(g) > 1:
                    groups.append(sorted(g, key=lambda f: f.modified))
    return groups


# ── Main scan ─────────────────────────────────────────────────────────────────

def scan(
    root: Path,
    recursive: bool = True,
    skip_hidden: bool = True,
    find_dupes: bool = True,
    max_files: int = 50_000,
) -> ScanResult:
    result = ScanResult(root=root)
    seen = 0

    walker = root.rglob("*") if recursive else root.iterdir()

    for p in walker:
        if seen >= max_files:
            break
        if not p.is_file():
            continue
        if skip_hidden and (p.name.startswith(".") or any(
            part.startswith(".") for part in p.parts
        )):
            continue
        # skip system dirs on Windows
        skip_dirs = {"$recycle.bin", "system volume information", "windows", "appdata"}
        if any(part.lower() in skip_dirs for part in p.parts):
            continue

        try:
            stat = p.stat()
        except (PermissionError, OSError):
            continue

        ext = p.suffix.lower()
        category = CATEGORIES.get(ext, "Other")

        # Override category for special patterns
        if INVOICE_RE.search(p.stem):
            category = "Documents"
        elif SCREENSHOT_RE.match(p.stem) and ext in {".png", ".jpg", ".jpeg"}:
            category = "Images"

        summary = _summarize(p, category)
        fi = FileInfo(
            path=p,
            category=category,
            summary=summary,
            size_bytes=stat.st_size,
            modified=stat.st_mtime,
        )
        result.files.append(fi)
        result.by_category[category].append(fi)
        result.total_size += stat.st_size
        seen += 1

    if find_dupes:
        result.duplicates = find_duplicates(result.files)

    return result
