#!/usr/bin/env python3
"""Create a messy sample directory for demoing the organizer.

Usage: python make_sample.py [DIR]   (default: samples/messy)
"""
import sys
from pathlib import Path

FILES = [
    "holiday.jpg", "logo.PNG", "diagram.svg", "photo.jpeg",
    "report.pdf", "notes.txt", "budget.xlsx", "resume.docx", "slides.pptx",
    "backup.zip", "project.tar.gz", "old_files.7z",
    "song.mp3", "podcast.wav",
    "clip.mp4", "movie.mkv",
    "script.py", "index.html",
    "mystery.xyz", "README_noext",
]


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "samples/messy")
    root.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        (root / name).write_text(f"sample content of {name}\n")
    # Pre-existing organized file, to demonstrate conflict handling:
    (root / "Documents").mkdir(exist_ok=True)
    (root / "Documents" / "report.pdf").write_text("ORIGINAL report already in Documents\n")
    # Two sources that map to the same destination name:
    (root / "inbox").mkdir(exist_ok=True)
    (root / "inbox" / "holiday.jpg").write_text("a different holiday.jpg in a subfolder\n")
    print(f"Created sample files in {root}")


if __name__ == "__main__":
    main()
