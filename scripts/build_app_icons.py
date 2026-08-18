"""Generate every QuillVille app icon from one design system.

Why this is a script and not eight committed drawings
-----------------------------------------------------
Before this, **four** of the apps shipped a byte-identical ``.ico`` -- Inkwell,
Audio Studio and Weather all wore Quill Radio's broadcast wave (same SHA-256) --
and two more, Beacon and Social, shipped installers with no icon at all, so they
wore PyInstaller's generic default. On a desktop that means three products
impersonating a fourth in the taskbar, in Alt+Tab, and in the tray, which is
where a tray-resident app lives its whole life. Nobody chose that; it happened
because each new app was scaffolded from the last one and an icon is easy not to
notice.

A generator makes the design system the source of truth, so the next app cannot
inherit somebody else's face by accident: adding one means adding an entry to
:data:`APPS`, and if you do not, ``tests/unit/scripts/test_app_icons.py`` says
so by name.

The system
----------
* **One tile.** Rounded square, corner radius 22% of the edge, full bleed. The
  silhouette is identical across the family, so they read as siblings.
* **One accent.** The family amber, already used by Radio and Cast.
* **One glyph, white, bold.** Two or three shapes at most. Detail that cannot
  survive 16x16 is detail that only exists in a screenshot.
* **Distinct hue *and* value per app.** Not hue alone: a set separated only by
  hue is a set that colour-blind users cannot tell apart. Each background here
  differs from its neighbours in lightness as well.
* **Distinct silhouette per app.** The strongest test is squinting -- if two
  icons blur to the same shape, the colour is doing all the work, and colour is
  the first thing to go at small sizes and for low-vision users.

Everything is drawn at 8x and downsampled with LANCZOS, which is what gives the
edges their antialiasing; PIL's own drawing primitives are hard-edged.

Run
---
    python scripts/build_app_icons.py            # write every app's .ico
    python scripts/build_app_icons.py --check    # fail if any is stale
    python scripts/build_app_icons.py --preview  # also emit 256/16 PNGs

wx-free; Pillow only.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - the script says so and exits cleanly
    print("Pillow is required: pip install Pillow", file=sys.stderr)
    raise SystemExit(2) from None

#: Draw at this multiple of the final edge, then downsample for clean edges.
SUPERSAMPLE = 8
#: The canvas every glyph is authored against.
CANVAS = 1024
#: Sizes Windows actually asks for, smallest first.
ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)

#: The family accent. Established by Radio and Cast; kept.
AMBER = (245, 197, 66, 255)
WHITE = (255, 255, 255, 255)


@dataclass(frozen=True)
class App:
    """One product: where its icon lives, its colour, and its glyph."""

    key: str
    ico_path: str
    background: tuple[int, int, int, int]
    #: Why this glyph, in one line -- so the next person changing it knows what
    #: it was trying to say.
    intent: str


def _tile(background: tuple[int, int, int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    drawer = ImageDraw.Draw(image)
    drawer.rounded_rectangle(
        [0, 0, CANVAS - 1, CANVAS - 1], radius=int(CANVAS * 0.22), fill=background
    )
    return image, drawer


# -- the glyphs --------------------------------------------------------------
#
# Each returns a finished 1024x1024 tile. Coordinates are literal on purpose:
# these are drawings, and a drawing expressed as arithmetic is a drawing nobody
# can adjust.


def _radio(background):
    """Broadcast: a source, and waves leaving it. Radio's own, unchanged in
    concept -- it was always the one icon that fitted its app."""
    image, drawer = _tile(background)
    drawer.ellipse([196, 430, 396, 630], fill=WHITE)
    # Two arcs, not three, and thicker with a wider gap: at 16x16 three thin
    # arcs merged into one smear. Fewer, bolder strokes survive the downsample.
    for radius in (300, 470):
        drawer.arc(
            [296 - radius, 530 - radius, 296 + radius, 530 + radius],
            start=-56,
            end=56,
            fill=AMBER,
            width=88,
        )
    return image


def _cast(background):
    """A microphone capsule under two waves: recorded speech, not live air.
    The capsule is what separates it from Radio at a glance."""
    image, drawer = _tile(background)
    drawer.rounded_rectangle([420, 452, 604, 828], radius=92, fill=WHITE)
    # Same stroke weight as Radio's arcs -- the two apps are the closest pair in
    # the family, and a thinner line here read as a *different* idea rather than
    # a sibling one.
    for radius in (232, 372):
        drawer.arc(
            [512 - radius, 392 - radius, 512 + radius, 392 + radius],
            start=202,
            end=338,
            fill=AMBER,
            width=84,
        )
    return image


def _converter(background):
    """Two arrows passing in opposite directions: one format becomes another,
    and it goes both ways."""
    image, drawer = _tile(background)
    drawer.rounded_rectangle([246, 392, 668, 484], radius=46, fill=WHITE)
    drawer.polygon([(640, 330), (812, 438), (640, 546)], fill=WHITE)
    drawer.rounded_rectangle([356, 560, 778, 652], radius=46, fill=AMBER)
    drawer.polygon([(384, 506), (212, 606), (384, 714)], fill=AMBER)
    return image


def _inkwell(background):
    """A nib dipped into an inkwell: the app is named for the well, and the
    pot is a silhouette nothing else in the family has. Survives 16px, which
    the alternatives (a bare nib, expanding text lines) did not."""
    image, drawer = _tile(background)
    drawer.polygon([(316, 656), (708, 656), (664, 892), (360, 892)], fill=WHITE)
    drawer.rounded_rectangle([292, 606, 732, 682], radius=38, fill=WHITE)
    drawer.polygon([(628, 148), (742, 262), (516, 618), (446, 566)], fill=AMBER)
    drawer.polygon([(516, 618), (446, 566), (452, 660)], fill=AMBER)
    return image


def _studio(background):
    """A waveform: bars of unequal height. Editing audio, not broadcasting it,
    and the only glyph in the set built from repetition."""
    image, drawer = _tile(background)
    # Three bars, not five: five merged into a solid block at 16x16. Wide gaps
    # are what make a waveform read as separate bars rather than as a slab.
    heights = (210, 400, 280)
    for index, half in enumerate(heights):
        left = 286 + index * 190
        colour = AMBER if index == 1 else WHITE
        drawer.rounded_rectangle([left, 512 - half, left + 120, 512 + half], radius=60, fill=colour)
    return image


def _weather(background):
    """Sun behind cloud. The one glyph in the family that is a picture of a
    thing rather than a diagram, because weather is the one app whose subject
    is a thing."""
    image, drawer = _tile(background)
    drawer.ellipse([382, 214, 682, 514], fill=AMBER)
    for angle in range(0, 360, 45):
        radian = math.radians(angle)
        cx, cy = 532, 364
        x1, y1 = cx + math.cos(radian) * 178, cy + math.sin(radian) * 178
        x2, y2 = cx + math.cos(radian) * 240, cy + math.sin(radian) * 240
        drawer.line([(x1, y1), (x2, y2)], fill=AMBER, width=42)
    drawer.ellipse([232, 556, 512, 800], fill=WHITE)
    drawer.ellipse([404, 500, 700, 780], fill=WHITE)
    drawer.rounded_rectangle([256, 654, 796, 806], radius=76, fill=WHITE)
    return image


def _beacon(background):
    """A place-marker with a hole through it. Beacon saves *places within
    things*, and a pin is the one shape in the family with a point -- it cannot
    be confused with anything else here even as a blur."""
    image, drawer = _tile(background)
    drawer.ellipse([300, 196, 724, 620], fill=WHITE)
    drawer.polygon([(370, 552), (654, 552), (512, 872)], fill=WHITE)
    drawer.ellipse([432, 328, 592, 488], fill=background)
    drawer.ellipse([456, 352, 568, 464], fill=AMBER)
    return image


def _social(background):
    """Two speech bubbles, overlapping. Quill Social is feeds and conversations
    from several places at once, which is the overlap; a single bubble would
    say "messaging"."""
    image, drawer = _tile(background)
    drawer.rounded_rectangle([196, 236, 700, 596], radius=96, fill=WHITE)
    drawer.polygon([(272, 570), (272, 760), (424, 590)], fill=WHITE)
    drawer.rounded_rectangle([368, 396, 836, 720], radius=88, fill=background)
    drawer.rounded_rectangle([396, 424, 808, 692], radius=76, fill=AMBER)
    drawer.polygon([(736, 666), (736, 838), (600, 686)], fill=AMBER)
    return image


def _runtime(background):
    """A hub with three spokes to smaller nodes: one shared engine, many apps
    drawing from it. The QuillVille Runtime is the only "app" here that is
    infrastructure, and the only glyph built around connection itself."""
    image, drawer = _tile(background)
    for angle in (90, 210, 330):
        radian = math.radians(angle)
        x = 512 + math.cos(radian) * 300
        y = 512 + math.sin(radian) * 300
        drawer.line([(512, 512), (x, y)], fill=AMBER, width=64)
        drawer.ellipse([x - 108, y - 108, x + 108, y + 108], fill=WHITE)
    drawer.ellipse([368, 368, 656, 656], fill=WHITE)
    drawer.ellipse([440, 440, 584, 584], fill=AMBER)
    return image


_GLYPHS = {
    "radio": _radio,
    "cast": _cast,
    "converter": _converter,
    "inkwell": _inkwell,
    "studio": _studio,
    "weather": _weather,
    "beacon": _beacon,
    "social": _social,
    "runtime": _runtime,
}


#: Backgrounds are spread across hue *and* lightness -- see the module
#: docstring on why hue alone is not enough.
APPS: tuple[App, ...] = (
    App(
        "radio",
        "standalone/radio/assets/quill-radio.ico",
        (43, 47, 126, 255),
        "broadcast waves leaving a source",
    ),
    App(
        "cast",
        "standalone/cast/assets/quill-cast.ico",
        (18, 102, 94, 255),
        "a microphone capsule under waves",
    ),
    App(
        "converter",
        "standalone/converter/assets/quill-converter.ico",
        (107, 63, 228, 255),
        "two arrows passing in opposite directions",
    ),
    App(
        "inkwell",
        "standalone/inkwell/assets/quill-inkwell.ico",
        (168, 69, 42, 255),
        "a nib dipped into an inkwell",
    ),
    App(
        "studio",
        "standalone/studio/assets/quill-audio-studio.ico",
        (55, 71, 79, 255),
        "an audio waveform",
    ),
    App(
        "weather",
        "standalone/weather/assets/quill-weather.ico",
        (30, 136, 199, 255),
        "sun behind cloud",
    ),
    App(
        "beacon",
        "standalone/beacon/assets/quill-beacon.ico",
        (155, 32, 60, 255),
        "a place-marker pin",
    ),
    App(
        "social",
        "standalone/social/assets/quill-social.ico",
        (124, 40, 110, 255),
        "two overlapping speech bubbles",
    ),
    App(
        "runtime",
        "standalone/runtime/assets/quillville-runtime.ico",
        (94, 110, 30, 255),
        "a hub with spokes to smaller nodes: one shared engine, many apps",
    ),
)


def render(app: App) -> Image.Image:
    """The finished 1024x1024 tile for *app*."""
    return _GLYPHS[app.key](app.background)


def write_ico(app: App, root: Path) -> Path:
    """Write *app*'s multi-resolution ``.ico``. Returns the path written."""
    tile = render(app)
    target = root / app.ico_path
    target.parent.mkdir(parents=True, exist_ok=True)
    largest = tile.resize((CANVAS // SUPERSAMPLE * 2, CANVAS // SUPERSAMPLE * 2), Image.LANCZOS)
    largest.save(target, format="ICO", sizes=[(size, size) for size in ICON_SIZES])
    return target


def write_previews(app: App, out_dir: Path) -> None:
    """256px and a magnified 16px, for eyeballing legibility before shipping."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tile = render(app).resize((256, 256), Image.LANCZOS)
    tile.save(out_dir / f"{app.key}_256.png")
    tile.resize((16, 16), Image.LANCZOS).resize((160, 160), Image.NEAREST).save(
        out_dir / f"{app.key}_16.png"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the QuillVille app icons.")
    parser.add_argument("--check", action="store_true", help="fail if any icon is stale")
    parser.add_argument("--preview", action="store_true", help="also write preview PNGs")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    if args.check:
        import io

        stale: list[str] = []
        for app in APPS:
            target = root / app.ico_path
            if not target.is_file():
                stale.append(f"{app.ico_path} (missing)")
                continue
            buffer = io.BytesIO()
            tile = render(app).resize(
                (CANVAS // SUPERSAMPLE * 2, CANVAS // SUPERSAMPLE * 2), Image.LANCZOS
            )
            tile.save(buffer, format="ICO", sizes=[(size, size) for size in ICON_SIZES])
            if buffer.getvalue() != target.read_bytes():
                stale.append(app.ico_path)
        if stale:
            print("Icons are stale; run python scripts/build_app_icons.py:", file=sys.stderr)
            for name in stale:
                print(f"  {name}", file=sys.stderr)
            return 1
        print(f"App icons: OK ({len(APPS)} up to date).")
        return 0

    for app in APPS:
        written = write_ico(app, root)
        print(f"  {app.key:<10} {written.relative_to(root)}  -- {app.intent}")
        if args.preview:
            write_previews(app, root / "build" / "_icons")
    print(f"Wrote {len(APPS)} app icons.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
