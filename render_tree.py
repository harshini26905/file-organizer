#!/usr/bin/env python3
"""Render a directory tree as a terminal-style PNG (used for README screenshots).

Usage: python render_tree.py DIR OUT.png "Title"
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def tree_lines(root: Path) -> list[str]:
    lines = [f"{root.name}/"]

    def walk(d: Path, prefix: str) -> None:
        entries = sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        for i, e in enumerate(entries):
            last = i == len(entries) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{e.name}{'/' if e.is_dir() else ''}")
            if e.is_dir():
                walk(e, prefix + ("    " if last else "│   "))

    walk(root, "")
    return lines


def main() -> None:
    root, out, title = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    font = next((ImageFont.truetype(p, 16) for p in FONT_PATHS if Path(p).exists()),
                ImageFont.load_default())
    lines = tree_lines(root)
    lh, pad = 22, 24
    width = max(int(font.getlength(l)) for l in [*lines, title]) + pad * 2
    height = lh * (len(lines) + 2) + pad * 2
    img = Image.new("RGB", (max(width, 520), height), "#1e1e2e")
    d = ImageDraw.Draw(img)
    d.text((pad, pad), title, font=font, fill="#f9e2af")
    y = pad + lh * 2
    for l in lines:
        color = "#89b4fa" if l.endswith("/") else "#cdd6f4"
        d.text((pad, y), l, font=font, fill=color)
        y += lh
    img.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
