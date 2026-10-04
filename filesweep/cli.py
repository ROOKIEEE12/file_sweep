"""
FileSweep CLI
-------------
Usage:
  filesweep scan [PATH] [OPTIONS]
  filesweep dupes [PATH]
  filesweep open <NAME>
  filesweep top [PATH] [--n N]

Run `filesweep --help` for full help.
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows if possible
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from . import scanner as sc

# ── ANSI colours (auto-disable on non-TTY / Windows without ANSI support) ────
def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if sys.platform == "win32":
        # Enable VT100 on Windows 10+
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            kernel.SetConsoleMode(kernel.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_COLOR = _supports_color()

def _c(code: str, text: str) -> str:
    if not _COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def bold(t: str) -> str:    return _c("1", t)
def dim(t: str) -> str:     return _c("2", t)
def green(t: str) -> str:   return _c("32", t)
def yellow(t: str) -> str:  return _c("33", t)
def cyan(t: str) -> str:    return _c("36", t)
def red(t: str) -> str:     return _c("31", t)
def magenta(t: str) -> str: return _c("35", t)


CATEGORY_COLORS = {
    "Documents": cyan,
    "Spreadsheets": green,
    "Presentations": yellow,
    "Images": magenta,
    "Videos": magenta,
    "Audio": magenta,
    "Archives": yellow,
    "Installers": red,
    "Code": cyan,
    "Data": cyan,
    "Fonts": dim,
    "eBooks": cyan,
    "Temp": red,
    "Other": dim,
}

def _cat_label(cat: str) -> str:
    fn = CATEGORY_COLORS.get(cat, dim)
    return fn(f"[{cat}]")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_path(p: str | None) -> Path:
    if p is None:
        return Path.home()
    return Path(p).expanduser().resolve()


def _print_header(title: str):
    print()
    print(bold("=" * 60))
    print(bold(f"  {title}"))
    print(bold("=" * 60))


def _print_summary_table(result: sc.ScanResult):
    print()
    print(bold("  SUMMARY"))
    print(dim("  " + "-" * 40))
    cats = sorted(result.by_category.items(), key=lambda x: -len(x[1]))
    for cat, files in cats:
        total_size = sc._human_size(sum(f.size_bytes for f in files))
        bar_len = min(20, len(files))
        bar = "|" * bar_len
        fn = CATEGORY_COLORS.get(cat, dim)
        print(f"  {fn(cat):<28}  {len(files):>5} files   {total_size:>10}  {dim(bar)}")
    print()
    print(f"  {bold('Total files :')} {result.total_files}")
    print(f"  {bold('Total size  :')} {sc._human_size(result.total_size)}")
    if result.duplicates:
        wasted = sum(
            sum(f.size_bytes for f in g[1:]) for g in result.duplicates
        )
        print(f"  {bold('Duplicates  :')} {red(str(len(result.duplicates)) + ' groups')}  "
              f"{dim('(' + sc._human_size(wasted) + ' wasted)')}")
    print()


def _print_file_list(files: list[sc.FileInfo], show_path: bool = False, limit: int = 0):
    shown = files[:limit] if limit else files
    for fi in shown:
        label = _cat_label(fi.category)
        name = fi.path.name if not show_path else str(fi.path)
        print(f"  {label:<30}  {name}")
        print(f"  {dim(' ' * 12)}  {dim(fi.summary)}")
    if limit and len(files) > limit:
        print(dim(f"  ... and {len(files) - limit} more"))


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_scan(args):
    root = _resolve_path(args.path)
    if not root.exists():
        print(red(f"Error: Path does not exist: {root}"))
        sys.exit(1)

    _print_header(f"FileSweep  --  {root}")
    print(dim(f"  Scanning {'recursively' if not args.shallow else 'top-level only'}, please wait..."))

    t0 = time.time()
    result = sc.scan(
        root,
        recursive=not args.shallow,
        find_dupes=not args.no_dupes,
    )
    elapsed = time.time() - t0

    _print_summary_table(result)

    # Per-category detail
    if args.detail or args.category:
        cats_to_show = (
            [args.category]
            if args.category
            else sorted(result.by_category.keys())
        )
        for cat in cats_to_show:
            if cat not in result.by_category:
                continue
            files = result.by_category[cat]
            fn = CATEGORY_COLORS.get(cat, dim)
            print(fn(f"  ── {cat} ({len(files)}) ──"))
            _print_file_list(files, show_path=args.full_path, limit=args.limit)
            print()

    # Vague names
    vague = [f for f in result.files if f.is_vague]
    if vague:
        print(yellow(f"  WARNING: {len(vague)} files have vague/meaningless names:"))
        for f in vague[:10]:
            print(f"    -> {f.path.name}  {dim(str(f.path.parent))}")
        if len(vague) > 10:
            print(dim(f"    ... and {len(vague) - 10} more"))
        print()

    # Duplicates
    if not args.no_dupes and result.duplicates:
        print(red(f"  DUPLICATES found: {len(result.duplicates)} groups"))
        for i, grp in enumerate(result.duplicates[:5], 1):
            print(f"    {bold(f'Group {i}')}  ({sc._human_size(grp[0].size_bytes)} each)")
            for fi in grp:
                marker = green("  KEEP ->") if fi == grp[0] else red("  DUPE ->")
                print(f"    {marker}  {fi.path}")
        if len(result.duplicates) > 5:
            print(dim(f"    ... and {len(result.duplicates) - 5} more groups. Run `filesweep dupes` for full list."))
        print()

    print(dim(f"  Scan completed in {elapsed:.2f}s"))
    print()


def cmd_dupes(args):
    root = _resolve_path(args.path)
    _print_header(f"Duplicate Finder  --  {root}")
    print(dim("  Scanning and hashing files, please wait..."))

    t0 = time.time()
    result = sc.scan(root, recursive=not args.shallow, find_dupes=True)
    elapsed = time.time() - t0

    if not result.duplicates:
        print(green("  No duplicates found!"))
    else:
        wasted = sum(sum(f.size_bytes for f in g[1:]) for g in result.duplicates)
        print(f"  {red(str(len(result.duplicates)) + ' duplicate groups')} -- "
              f"{yellow(sc._human_size(wasted))} wasted space\n")
        for i, grp in enumerate(result.duplicates, 1):
            size = sc._human_size(grp[0].size_bytes)
            print(bold(f"  Group {i}  ({size} each -- {len(grp)} copies)"))
            for j, fi in enumerate(grp):
                marker = green("  OK KEEP") if j == 0 else red("  !! DUPE")
                print(f"  {marker}  {fi.path}  {dim(fi.age)}")
            print()

    print(dim(f"  Completed in {elapsed:.2f}s"))
    print()


def cmd_open(args):
    """Search for a file by name and open it."""
    query = args.name.lower()
    root = _resolve_path(args.path)

    print(dim(f"  Searching for '{args.name}' in {root}..."))
    matches: list[Path] = []

    try:
        for p in root.rglob("*"):
            if p.is_file() and query in p.name.lower():
                matches.append(p)
                if len(matches) >= 20:
                    break
    except KeyboardInterrupt:
        pass

    if not matches:
        print(red(f"  No file found matching '{args.name}'"))
        sys.exit(1)

    if len(matches) == 1:
        target = matches[0]
    else:
        print(bold(f"\n  Found {len(matches)} matches:\n"))
        for i, m in enumerate(matches, 1):
            print(f"  {bold(str(i))}.  {m.name}  {dim(str(m.parent))}")
        print()
        choice = input("  Enter number to open (or Enter to cancel): ").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(matches)):
            print(dim("  Cancelled."))
            return
        target = matches[int(choice) - 1]

    print(green(f"  Opening: {target}"))
    if sys.platform == "win32":
        os.startfile(str(target))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(target)])
    else:
        subprocess.run(["xdg-open", str(target)])


def cmd_top(args):
    """Show the largest files in a directory."""
    root = _resolve_path(args.path)
    n = args.n or 20

    _print_header(f"Top {n} Largest Files  --  {root}")
    print(dim("  Scanning..."))

    result = sc.scan(root, recursive=not args.shallow, find_dupes=False)
    top = sorted(result.files, key=lambda f: -f.size_bytes)[:n]

    print()
    for i, fi in enumerate(top, 1):
        size = bold(sc._human_size(fi.size_bytes))
        cat = _cat_label(fi.category)
        print(f"  {dim(str(i).rjust(2))}.  {size:<14}  {cat:<30}  {fi.path}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="filesweep",
        description=(
            "FileSweep — Scan, summarize, and organize your files from the command line.\n\n"
            "Examples:\n"
            "  filesweep scan                        # scan your home folder\n"
            "  filesweep scan C:\\Users\\amitg\\Docs   # scan a specific folder\n"
            "  filesweep scan --detail --category Images\n"
            "  filesweep dupes C:\\Users\\amitg       # find duplicate files\n"
            "  filesweep open report                # find & open a file by name\n"
            "  filesweep top                        # show 20 largest files\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # ── scan ──────────────────────────────────────────────────────────────────
    p_scan = sub.add_parser("scan", help="Scan a folder and show a categorized summary")
    p_scan.add_argument("path", nargs="?", default=None,
                        help="Folder to scan (default: your home directory)")
    p_scan.add_argument("--shallow", action="store_true",
                        help="Only scan top-level files (no subdirectories)")
    p_scan.add_argument("--detail", action="store_true",
                        help="Show individual files per category")
    p_scan.add_argument("--category", "-c", metavar="CAT",
                        help="Show detail for a specific category only (e.g. Images)")
    p_scan.add_argument("--full-path", action="store_true",
                        help="Show full file paths instead of just filenames")
    p_scan.add_argument("--limit", type=int, default=15,
                        help="Max files to show per category in detail mode (default: 15)")
    p_scan.add_argument("--no-dupes", action="store_true",
                        help="Skip duplicate detection (faster)")

    # ── dupes ─────────────────────────────────────────────────────────────────
    p_dupes = sub.add_parser("dupes", help="Find duplicate files")
    p_dupes.add_argument("path", nargs="?", default=None,
                         help="Folder to scan (default: home)")
    p_dupes.add_argument("--shallow", action="store_true",
                         help="Only scan top-level")

    # ── open ──────────────────────────────────────────────────────────────────
    p_open = sub.add_parser("open", help="Find and open a file by name")
    p_open.add_argument("name", help="File name or partial name to search for")
    p_open.add_argument("--path", "-p", default=None,
                        help="Where to search (default: home)")

    # ── top ───────────────────────────────────────────────────────────────────
    p_top = sub.add_parser("top", help="Show the largest files")
    p_top.add_argument("path", nargs="?", default=None)
    p_top.add_argument("--n", type=int, default=20, help="How many to show (default: 20)")
    p_top.add_argument("--shallow", action="store_true")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "dupes":
        cmd_dupes(args)
    elif args.command == "open":
        cmd_open(args)
    elif args.command == "top":
        cmd_top(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
