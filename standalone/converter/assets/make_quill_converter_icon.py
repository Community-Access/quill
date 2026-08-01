"""Render the Quill Converter tile icon (``quill-converter.ico``).

Run from anywhere; it writes next to this file:

    python standalone/converter/assets/make_quill_converter_icon.py

The QuillVille apps share one silhouette -- a rounded square tile, a white
glyph, and the family gold accent -- and differ only by hue, so a user picking
QUILL, Quill Radio, Quill Cast, and Quill Converter out of a taskbar or Start
menu can tell them apart at 16 px. Quill Radio and Audio Studio are navy, Quill
Cast is teal; the converter is plum.

The glyph is deliberately blunt: gold waveform bars on the left, a heavy white
arrow pointing right. "Sound goes in, a different format comes out" survives
being drawn 16 pixels wide, which a pair of curved recycle arrows does not.

Everything is drawn at 8x and downsampled, so edges stay smooth at every size
without shipping hand-tuned bitmaps. Pillow is a base UI dependency, so this
needs nothing extra installed.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

#: Emitted .ico sizes. Matches the sibling product icons (Explorer, the taskbar,
#: Alt+Tab, and the Start tile all pick different ones).
SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)

#: Supersampling factor -- draw big, then downsample for antialiased edges.
SCALE = 8

#: Quill Converter's family hue (plum), the shared gold accent, and white.
TILE = (104, 40, 96, 255)
ACCENT = (255, 209, 84, 255)
GLYPH = (255, 255, 255, 255)


def render(size: int = 256) -> Image.Image:
    """Draw the tile at ``size`` px square (RGBA)."""
    canvas = size * SCALE
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = canvas * 0.04
    radius = canvas * 0.22
    draw.rounded_rectangle(
        (margin, margin, canvas - margin, canvas - margin),
        radius=radius,
        fill=TILE,
    )

    # Gold waveform bars: the "before" side of the conversion.
    bar_width = canvas * 0.055
    bar_gap = canvas * 0.045
    left = canvas * 0.20
    center_y = canvas * 0.5
    for index, half_height in enumerate((0.10, 0.17, 0.13)):
        x0 = left + index * (bar_width + bar_gap)
        draw.rounded_rectangle(
            (x0, center_y - canvas * half_height, x0 + bar_width, center_y + canvas * half_height),
            radius=bar_width / 2,
            fill=ACCENT,
        )

    # White arrow: shaft plus head, pointing at the "after" side.
    shaft_top = center_y - canvas * 0.055
    shaft_bottom = center_y + canvas * 0.055
    shaft_left = canvas * 0.46
    shaft_right = canvas * 0.68
    draw.rectangle((shaft_left, shaft_top, shaft_right, shaft_bottom), fill=GLYPH)
    draw.polygon(
        [
            (shaft_right - canvas * 0.01, center_y - canvas * 0.16),
            (canvas * 0.82, center_y),
            (shaft_right - canvas * 0.01, center_y + canvas * 0.16),
        ],
        fill=GLYPH,
    )

    return image.resize((size, size), Image.LANCZOS)


def main() -> int:
    target = Path(__file__).resolve().parent / "quill-converter.ico"
    master = render(max(SIZES))
    master.save(target, format="ICO", sizes=[(size, size) for size in SIZES])
    print(f"wrote {target} ({', '.join(str(size) for size in SIZES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
