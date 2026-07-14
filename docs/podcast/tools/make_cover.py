#!/usr/bin/env python3
"""Generate the QUILL Cast cover art (3000x3000 PNG) on-device with Pillow.

No network, no external service -- the cover is drawn from QUILL's brand
palette so it matches the rest of the site. The design layers, back to front:

1. A vertical indigo-to-near-black gradient with a warm radial glow behind the
   title, so the centre reads as the focal point.
2. A faint gold quill watermark, rotated, sitting behind the type as the brand
   mark (QUILL = a quill).
3. A vibrant soundwave band below the title -- the "cast / audio" signal --
   drawn as rounded bars on a teal -> gold -> pink gradient.
4. Stacked poster type: THE / QUILL (gold) / CAST, a short tagline, the two
   host names (Liam and Jessica, the on-device Kokoro voices the show uses),
   and the site address along the bottom.

Output: ``docs/site/podcast/cover.png`` (served by GitHub Pages, referenced by
the RSS ``<image>`` and ``<itunes:image>`` tags written by ``build_feed.py``).

Usage::

    python docs/podcast/tools/make_cover.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
SITE_DIR = HERE.parent.parent.parent / "docs" / "site" / "podcast"
OUT_PATH = SITE_DIR / "cover.png"

SIZE = 3000
CX = CY = SIZE // 2

# Brand palette.
BG_TOP = (27, 31, 92)  # deep indigo
BG_BOTTOM = (10, 8, 23)  # near-black plum
GLOW = (245, 201, 66)  # warm gold
GOLD = (245, 197, 66)
GOLD_HI = (255, 212, 121)
TEAL = (46, 196, 182)
PINK = (255, 107, 157)
WHITE = (255, 255, 255)
LIGHT = (201, 205, 224)
DIM = (138, 143, 171)


def _font(size: int, *, bold: bool = False, black: bool = False) -> ImageFont.FreeTypeFont:
    """Pick a system display font, falling back to PIL's default if absent."""
    candidates = []
    if black:
        candidates += ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/segoeuib.ttf"]
    if bold:
        candidates += [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial Bold.ttf",
        ]
    else:
        candidates += [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/Arial.ttf",
        ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _vertical_gradient(
    size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]
) -> Image.Image:
    """A smooth top->bottom RGB gradient."""
    base = Image.new("RGB", (size, size), top)
    px = base.load()
    for y in range(size):
        t = y / (size - 1)
        r = round(top[0] + (bottom[0] - top[0]) * t)
        g = round(top[1] + (bottom[1] - top[1]) * t)
        b = round(top[2] + (bottom[2] - top[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return base


def _radial_glow(size: int, color: tuple[int, int, int], radius: int, alpha: int) -> Image.Image:
    """A soft radial glow centred on the canvas, as an RGBA layer."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    steps = 120
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(alpha * (1 - i / steps) ** 2)
        draw.ellipse((CX - r, CY - r - 150, CX + r, CY + r - 150), fill=(*color, a))
    return layer.filter(ImageFilter.GaussianBlur(60))


def _quill_watermark(size: int, color: tuple[int, int, int], alpha: int) -> Image.Image:
    """A stylised gold quill, rotated, as a faint brand watermark behind the type."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Draw on an oversize transparent tile so rotation never clips.
    tile = 2200
    quill = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    qd = ImageDraw.Draw(quill)
    cx = cy = tile // 2
    # Shaft (calamus): a long tapered quill running up-left from the writing nib.
    shaft_top = (cx - 520, cy - 560)
    shaft_bot = (cx + 120, cy + 560)
    shaft_left = (cx - 360, cy + 560)
    shaft_right = (cx + 280, cy - 560)
    qd.polygon([shaft_top, shaft_right, shaft_bot, shaft_left], fill=(*color, alpha))
    # Feather barbs fanning off the upper shaft, longer toward the tip.
    for i in range(-9, 10):
        s = i / 9.0
        # Point along the upper shaft where this barb attaches.
        ax = shaft_top[0] + (shaft_right[0] - shaft_top[0]) * (0.5 + 0.5 * s)
        ay = shaft_top[1] + (shaft_right[1] - shaft_top[1]) * (0.5 + 0.5 * s)
        barb_len = 260 * (0.55 + 0.45 * (1 - abs(s)))
        # Mirror barbs either side of the shaft.
        for side in (-1, 1):
            angle = math.radians(-58 + s * 6)
            ex = ax + side * barb_len * math.cos(angle)
            ey = ay + side * barb_len * math.sin(angle)
            qd.line([(ax, ay), (ex, ey)], fill=(*color, alpha), width=46, joint="curve")
    # Writing nib at the lower tip.
    qd.polygon(
        [(cx + 120, cy + 560), (cx + 360, cy + 720), (cx + 120, cy + 700)],
        fill=(*color, alpha),
    )
    rotated = quill.rotate(34, resample=Image.BICUBIC, expand=False)
    # Centre the rotated quill on the cover, sitting high behind the title.
    off = ((size - tile) // 2, (size - tile) // 2 - 240)
    layer.alpha_composite(rotated, off)
    return layer


def _soundwave(
    size: int,
    y: float,
    bars: int,
    bar_w: int,
    gap: int,
    max_h: int,
    colors: list[tuple[int, int, int]],
) -> Image.Image:
    """Rounded vertical bars centred on *y*, heights from a windowed envelope,
    coloured left->right across *colors*."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    total_w = bars * bar_w + (bars - 1) * gap
    x0 = (size - total_w) // 2
    for i in range(bars):
        # Smooth envelope: tallest in the middle, tapered at the ends, with a
        # little variation so it reads as real speech, not a static meter.
        env = math.sin(math.pi * (i + 0.5) / bars)  # 0..1..0
        wobble = 0.55 + 0.45 * math.sin(i * 1.7)
        h = max(bar_w, int(max_h * env * wobble))
        x = x0 + i * (bar_w + gap)
        # Gradient colour across the band.
        t = i / (bars - 1)
        seg = t * (len(colors) - 1)
        lo = colors[int(seg)]
        hi = colors[min(int(seg) + 1, len(colors) - 1)]
        f = seg - int(seg)
        col = tuple(round(lo[k] + (hi[k] - lo[k]) * f) for k in range(3))
        draw.rounded_rectangle(
            (x, y - h / 2, x + bar_w, y + h / 2), radius=bar_w // 2, fill=(*col, 255)
        )
    return layer


def _centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int,
    fill,
    *,
    letter_spacing: int = 0,
) -> int:
    """Draw *text* horizontally centred; return the text width (for stacking)."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + letter_spacing * (len(text) - 1)
    x = (SIZE - total) // 2
    for ch, w in zip(text, widths, strict=True):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + letter_spacing
    return int(total)


def main() -> int:
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    img = _vertical_gradient(SIZE, BG_TOP, BG_BOTTOM).convert("RGBA")
    img.alpha_composite(_radial_glow(SIZE, GLOW, radius=1500, alpha=70))
    img.alpha_composite(_quill_watermark(SIZE, GOLD, alpha=46))

    draw = ImageDraw.Draw(img)

    # Stacked poster type: THE / QUILL / CAST.
    _centered(draw, "THE", _font(150, bold=True), y=430, fill=LIGHT, letter_spacing=42)
    _centered(draw, "QUILL", _font(560, black=True), y=600, fill=GOLD_HI, letter_spacing=18)
    _centered(draw, "CAST", _font(150, bold=True), y=1200, fill=WHITE, letter_spacing=42)

    # Soundwave band beneath the type.
    img.alpha_composite(
        _soundwave(SIZE, y=1760, bars=72, bar_w=34, gap=18, max_h=560, colors=[TEAL, GOLD, PINK])
    )

    draw = ImageDraw.Draw(img)

    # Tagline + hosts + site address.
    _centered(draw, "A screen-reader-first audio course", _font(86, bold=True), y=2140, fill=WHITE)
    _centered(draw, "Liam & Jessica", _font(74), y=2280, fill=GOLD_HI)
    _centered(
        draw, "community-access.github.io/quill", _font(58), y=2760, fill=DIM, letter_spacing=6
    )

    img.convert("RGB").save(OUT_PATH, "PNG", optimize=True)
    print(f"Wrote {OUT_PATH} ({SIZE}x{SIZE})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
