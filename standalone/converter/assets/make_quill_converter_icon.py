"""Generate ``quill-converter.ico`` — the Quill Converter tile icon.

The other standalone apps ship a hand-made brand icon; the converter's is drawn
here so it is reproducible and reviewable in source. Run from this folder:

    python make_quill_converter_icon.py

It renders a rounded violet tile with the universal "convert" glyph (two
horizontal arrows swapping direction) at 4x for anti-aliasing, then writes a
multi-resolution ``.ico`` (16/24/32/48/64/128/256) matching the sibling apps.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

_SIZE = 256
_SCALE = 4  # supersample, then downscale for clean edges
_BG = (124, 77, 255, 255)  # violet — distinct from the radio/cast/studio/weather tiles
_BG_DARK = (98, 54, 214, 255)
_FG = (255, 255, 255, 255)


def _rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def _arrow(draw: ImageDraw.ImageDraw, y: int, *, pointing_right: bool, s: int) -> None:
    """One horizontal arrow (shaft + head) centered vertically on *y* (px, @scale)."""
    margin = 56 * s
    x0, x1 = margin, _SIZE * s - margin
    shaft = 20 * s  # shaft thickness
    head = 46 * s  # arrowhead half-height
    tip = 40 * s  # arrowhead length
    if pointing_right:
        draw.rounded_rectangle((x0, y - shaft // 2, x1 - tip, y + shaft // 2), radius=shaft // 2, fill=_FG)
        draw.polygon([(x1 - tip, y - head), (x1, y), (x1 - tip, y + head)], fill=_FG)
    else:
        draw.rounded_rectangle((x0 + tip, y - shaft // 2, x1, y + shaft // 2), radius=shaft // 2, fill=_FG)
        draw.polygon([(x0 + tip, y - head), (x0, y), (x0 + tip, y + head)], fill=_FG)


def render() -> Image.Image:
    s = _SCALE
    img = Image.new("RGBA", (_SIZE * s, _SIZE * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Tile background (subtle two-tone: darker lower half for depth).
    _rounded(draw, (12 * s, 12 * s, (_SIZE - 12) * s, (_SIZE - 12) * s), 48 * s, _BG_DARK)
    _rounded(draw, (12 * s, 12 * s, (_SIZE - 12) * s, (_SIZE - 40) * s), 48 * s, _BG)
    # The convert glyph: top arrow → , bottom arrow ← .
    _arrow(draw, 104 * s, pointing_right=True, s=s)
    _arrow(draw, 156 * s, pointing_right=False, s=s)
    return img.resize((_SIZE, _SIZE), Image.LANCZOS)


def main() -> int:
    icon = render()
    out = Path(__file__).with_name("quill-converter.ico")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(out, format="ICO", sizes=sizes)
    print(f"Wrote {out} ({', '.join(f'{w}x{h}' for w, h in sizes)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
