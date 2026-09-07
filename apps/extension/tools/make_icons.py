#!/usr/bin/env python3
"""Generate the Alfred icon set — no Pillow, no npm, no design tool.

The mark is an angular ascending step, cut from a single stroke. It reads as
both a chevron (code) and a climb (progress) — the product being that hints are
rungs you take only as far as you need. It survives 16 pixels, which rules out
anything more literal: at favicon size a wordmark or a padlock is mud.

Deliberately adjacent to the coding-site visual family — dark tile, warm amber
mark, angular geometry — without reproducing anyone's logo. The shape is a
stepped chevron, which is common visual vocabulary rather than anyone's mark.

Flat fills, no gradient: the surrounding UI dropped gradients for a minimal
developer-tool look, and an icon that glows next to a flat panel looks like it
came from somewhere else.

Chrome requires PNG for action icons (Firefox would take SVG, but one format for
both keeps the build honest), so this writes PNGs directly: a pixel buffer,
4x supersampling for antialiasing, then zlib into the PNG container. Keeping the
generator in the repo means the icon is editable by changing numbers here rather
than by owning a copy of Illustrator.

    python tools/make_icons.py
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src" / "icons"
SIZES = (16, 32, 48, 128)
SS = 4  # supersampling factor

# Flat warm-charcoal tile with the Ember accent (tokens.css --brand / --ink-0).
# Kept in sync with the panel by hand rather than generated from the token
# file: a PNG toolbar icon can't read a CSS variable, so if the palette moves
# again this constant has to move with it or the toolbar and the panel drift
# apart the same way the amber-on-neutral combination did before Ember.
TILE = (0x17, 0x13, 0x10)
MARK = (0xE0, 0x39, 0x2A)

# Geometry as fractions of the tile, so every size is the same drawing.
CORNER_R = 0.235
# Three steps climbing left-to-right, each a short bar plus the riser joining
# it to the next. Drawn as overlapping rectangles so it stays one solid stroke.
STEP_XS = (0.195, 0.395, 0.595)
STEP_YS = (0.596, 0.456, 0.316)
TREAD_W = 0.210
STROKE = 0.088
MARK_R = 0.030


def _rounded_rect(x, y, x0, y0, x1, y1, r) -> bool:
    """Is (x, y) inside the rounded rectangle [x0,x1] x [y0,y1]?"""
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def _sample(u: float, v: float):
    """Colour at normalized (u, v), or None for transparent."""
    if not _rounded_rect(u, v, 0.0, 0.0, 1.0, 1.0, CORNER_R):
        return None

    for i, (x, y) in enumerate(zip(STEP_XS, STEP_YS)):
        # the tread
        if _rounded_rect(u, v, x, y, x + TREAD_W, y + STROKE, MARK_R):
            return MARK
        # the riser up to the next tread
        if i + 1 < len(STEP_XS):
            rx = x + TREAD_W - STROKE
            if _rounded_rect(u, v, rx, STEP_YS[i + 1], rx + STROKE, y + STROKE, MARK_R):
                return MARK

    return TILE


def render(size: int) -> bytes:
    """Render one icon as raw RGBA rows."""
    rows = bytearray()
    hi = size * SS
    for py in range(size):
        rows.append(0)  # PNG filter byte: none
        for px in range(size):
            r = g = b = a = 0
            for sy in range(SS):
                for sx in range(SS):
                    u = (px * SS + sx + 0.5) / hi
                    v = (py * SS + sy + 0.5) / hi
                    c = _sample(u, v)
                    if c is not None:
                        r += c[0]
                        g += c[1]
                        b += c[2]
                        a += 255
            n = SS * SS
            if a == 0:
                rows += bytes(4)
            else:
                # Average the covered samples only, so edge pixels keep their
                # colour and vary in alpha instead of darkening toward black.
                cov = a // 255
                rows += bytes((r // cov, g // cov, b // cov, a // n))
    return bytes(rows)


def write_png(path: Path, size: int, raw: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", header)
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        path = OUT / f"icon-{size}.png"
        write_png(path, size, render(size))
        print(f"  wrote {path.relative_to(OUT.parent.parent)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
