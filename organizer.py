#!/usr/bin/env python3
"""File Organizer: sort files in a directory into subfolders by file type.

Usage:
    python organizer.py SOURCE [--target TARGET] [--dry-run] [--log FILE]
                        [--config CONFIG] [--recursive]

Guarantees:
  * Existing files are never overwritten.
  * Name conflicts are resolved deterministically: "name.ext" becomes
    "name (1).ext", "name (2).ext", ... (first free number wins). Files are
    processed in sorted order, so the same input always yields the same output.
  * --dry-run prints every planned move and changes nothing.
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
               ".webp", ".svg", ".heic", ".ico", ".raw"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls",
                  ".xlsx", ".csv", ".ppt", ".pptx", ".md", ".epub"],
    "Archives": [".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"],
    "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "Code": [".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs",
             ".html", ".css", ".json", ".sh"],
}
FALLBACK_CATEGORY = "Others"

log = logging.getLogger("organizer")


@dataclass(frozen=True)
class Move:
    src: Path
    dst: Path
    category: str
    renamed: bool


def load_categories(config_path: Path | None) -> tuple[dict[str, list[str]], str]:
    """Return (category -> extensions, fallback folder name)."""
    if config_path is None:
        return DEFAULT_CATEGORIES, FALLBACK_CATEGORY
    with config_path.open(encoding="utf-8") as fh:
        cfg = json.load(fh)
    cats = cfg.get("categories", DEFAULT_CATEGORIES)
    return cats, cfg.get("fallback", FALLBACK_CATEGORY)


def build_ext_map(categories: dict[str, list[str]]) -> dict[str, str]:
    ext_map: dict[str, str] = {}
    for category, exts in categories.items():
        for ext in exts:
            ext = ext.lower() if ext.startswith(".") else "." + ext.lower()
            ext_map.setdefault(ext, category)  # first category wins
    return ext_map


def categorize(path: Path, ext_map: dict[str, str], fallback: str) -> str:
    return ext_map.get(path.suffix.lower(), fallback)


def unique_destination(dst: Path, reserved: set[Path]) -> Path:
    """Return dst, or "stem (N).ext" with the smallest free N.

    `reserved` holds destinations already claimed earlier in this run, so
    dry-run and real run produce identical names.
    """
    if not dst.exists() and dst not in reserved:
        return dst
    n = 1
    while True:
        candidate = dst.with_name(f"{dst.stem} ({n}){dst.suffix}")
        if not candidate.exists() and candidate not in reserved:
            return candidate
        n += 1


def iter_files(source: Path, recursive: bool, skip_dirs: set[Path]):
    walker = source.rglob("*") if recursive else source.iterdir()
    for p in sorted(walker, key=lambda x: str(x).lower()):
        if not p.is_file() or p.is_symlink():
            continue
        if any(parent in skip_dirs for parent in p.parents):
            continue  # already organized
        yield p


def plan_moves(source: Path, target: Path, categories: dict[str, list[str]],
               fallback: str, recursive: bool = False) -> list[Move]:
    ext_map = build_ext_map(categories)
    category_dirs = {(target / c).resolve() for c in [*categories, fallback]}
    reserved: set[Path] = set()
    moves: list[Move] = []
    for f in iter_files(source, recursive, category_dirs):
        category = categorize(f, ext_map, fallback)
        wanted = target / category / f.name
        if wanted.resolve() == f.resolve():
            continue  # already in place
        final = unique_destination(wanted, reserved)
        reserved.add(final)
        moves.append(Move(f, final, category, final != wanted))
    return moves


def execute(moves: list[Move], dry_run: bool) -> int:
    done = 0
    for m in moves:
        note = "  [renamed: name conflict]" if m.renamed else ""
        verb = "WOULD MOVE" if dry_run else "MOVE"
        log.info("%s  %s  ->  %s%s", verb, m.src, m.dst, note)
        if dry_run:
            continue
        m.dst.parent.mkdir(parents=True, exist_ok=True)
        if m.dst.exists():  # last-line safety net; should be unreachable
            log.error("SKIP  %s: destination exists: %s", m.src, m.dst)
            continue
        shutil.move(str(m.src), str(m.dst))
        done += 1
    return done


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sort files into subfolders (Images, Documents, ...) by type.")
    p.add_argument("source", type=Path, help="directory whose files will be sorted")
    p.add_argument("-t", "--target", type=Path, default=None,
                   help="base directory for the category folders (default: SOURCE)")
    p.add_argument("-c", "--config", type=Path, default=None,
                   help="JSON config with custom categories (see config.example.json)")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="list planned moves without performing them")
    p.add_argument("-l", "--log", type=Path, default=None,
                   help="also write the log to this file")
    p.add_argument("-r", "--recursive", action="store_true",
                   help="also sort files found in subfolders of SOURCE")
    return p.parse_args(argv)


def setup_logging(log_file: Path | None) -> None:
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    if log_file:
        fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_logging(args.log)

    source = args.source.expanduser().resolve()
    if not source.is_dir():
        log.error("Source is not a directory: %s", source)
        return 2
    target = (args.target or source).expanduser().resolve()
    if args.config and not args.config.is_file():
        log.error("Config file not found: %s", args.config)
        return 2

    categories, fallback = load_categories(args.config)
    mode = "DRY RUN" if args.dry_run else "LIVE"
    log.info("Organizer started (%s) source=%s target=%s", mode, source, target)

    moves = plan_moves(source, target, categories, fallback, args.recursive)
    if not moves:
        log.info("Nothing to do.")
        return 0

    done = execute(moves, args.dry_run)
    renamed = sum(m.renamed for m in moves)
    summary = {}
    for m in moves:
        summary[m.category] = summary.get(m.category, 0) + 1
    log.info("Summary: %s", ", ".join(f"{k}={v}" for k, v in sorted(summary.items())))
    if args.dry_run:
        log.info("Dry run complete: %d planned moves (%d renamed). No files changed.",
                 len(moves), renamed)
    else:
        log.info("Done: %d files moved (%d renamed to avoid conflicts).", done, renamed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
