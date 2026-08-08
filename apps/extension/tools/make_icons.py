#!/usr/bin/env python3
"""Generate the LeetLearn icon set — no Pillow, no npm, no design tool.

The mark is a rising three-rung ladder on a rounded tile. The ladder is the
product: hints are rungs you climb only as far as you need, and the whole
premise is that you get there yourself. It also survives being 16 pixels wide,
which rules out anything more literal — at favicon size a wordmark or a lock is
mud, but three ascending bars still read as progress.

The tile uses LeetCode's own orange so the extension looks like it belongs
beside the site rather than pasted on top of it.

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

# LeetCode's brand orange, warmed toward the bottom so the tile has some depth.
TOP = (0xFF, 0xB0, 0x2E)
BOTTOM = (0xF8, 0x8B, 0x00)
RUNG = (0xFF, 0xFF, 0xFF)

# Geometry as fractions of the tile, so every size is the same drawing.
CORNER_R = 0.235
RUNG_XS = (0.250, 0.435, 0.620)
RUNG_W = 0.130
RUNG_HS = (0.230, 0.395, 0.560)
RUNG_BASE = 0.775
RUNG_R = 0.055


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

    for x0, h in zip(RUNG_XS, RUNG_HS):
        if _rounded_rect(u, v, x0, RUNG_BASE - h, x0 + RUNG_W, RUNG_BASE, RUNG_R):
            return RUNG

    t = v  # vertical gradient
    return tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))


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
