"""Every QuillVille app has its own face, and the checked-in icons match source.

The bug this exists to prevent already happened. Until 2026-08-13 **four** of
the apps shipped a byte-identical ``.ico``: Inkwell, Audio Studio and Weather
all wore Quill Radio's broadcast wave, because each new app was scaffolded from
the last one and an icon is easy not to notice. On a desktop that means three
products impersonating a fourth in the taskbar, in Alt+Tab, and in the tray --
where a tray-resident app lives its whole life.

Two guarantees, then:

* **No two apps share an icon.** A hash comparison, so it cannot be argued with.
* **The committed ``.ico`` is what the generator produces.** An icon edited by
  hand would be silently reverted by the next person who runs the script, and a
  generator nobody trusts is worse than no generator.

The rendering itself is checked at ``--preview`` by eye -- an assertion cannot
tell you whether a drawing reads at 16x16. What *is* asserted here is the thing
an eye is bad at: that eight files are eight files.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest

pytest.importorskip("PIL", reason="Pillow is not installed")

import scripts.build_app_icons as icons  # noqa: E402

_ROOT = Path(__file__).resolve().parents[3]


def _ico_bytes(app: icons.App) -> bytes:
    """What the generator would write for *app*, right now."""
    buffer = io.BytesIO()
    edge = icons.CANVAS // icons.SUPERSAMPLE * 2
    tile = icons.render(app).resize((edge, edge), icons.Image.LANCZOS)
    tile.save(buffer, format="ICO", sizes=[(size, size) for size in icons.ICON_SIZES])
    return buffer.getvalue()


# -- the family --------------------------------------------------------------


def test_every_app_that_ships_an_installer_has_an_entry() -> None:
    """The generator is the register of who has a face. An app added to
    ``standalone/`` with an installer but no entry gets PyInstaller's default
    icon, which is how Beacon and Social shipped before this."""
    installers = {path.parent.parent.name for path in _ROOT.glob("standalone/*/installer/*.iss")}
    # radio-mac and weather-ios are not Windows installers; player has none.
    named = {app.key for app in icons.APPS}
    named |= {"audio-studio"}  # studio's installer directory name
    missing = {name for name in installers if name not in named}
    assert not missing, f"these apps ship an installer with no icon entry: {sorted(missing)}"


def test_no_two_apps_share_a_face() -> None:
    """The original defect, stated as an assertion."""
    seen: dict[str, str] = {}
    for app in icons.APPS:
        digest = hashlib.sha256(_ico_bytes(app)).hexdigest()
        assert digest not in seen, (
            f"{app.key} and {seen[digest]} render byte-identical icons -- "
            "give one of them its own glyph"
        )
        seen[digest] = app.key


def test_no_two_apps_share_a_background_colour() -> None:
    """Silhouette is the primary separator, but a repeated colour still reads
    as "these two are the same product" in a taskbar of small tiles."""
    backgrounds = [app.background for app in icons.APPS]
    assert len(set(backgrounds)) == len(backgrounds)


def test_backgrounds_differ_in_lightness_not_only_hue() -> None:
    """A set separated by hue alone is a set some colour-blind users cannot
    tell apart. Perceived lightness must spread too."""

    def luma(colour: tuple[int, int, int, int]) -> float:
        red, green, blue, _ = colour
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    values = sorted(luma(app.background) for app in icons.APPS)
    assert values[-1] - values[0] > 60, "every tile is about equally dark"


def test_every_glyph_is_drawn_and_named() -> None:
    for app in icons.APPS:
        assert app.key in icons._GLYPHS, f"{app.key} has no glyph function"
        assert app.intent, f"{app.key} does not say what its glyph means"


# -- the committed files -----------------------------------------------------


def test_every_icon_exists_where_its_spec_and_installer_look_for_it() -> None:
    for app in icons.APPS:
        assert (_ROOT / app.ico_path).is_file(), app.ico_path


def test_committed_icons_match_the_generator() -> None:
    """``build_app_icons.py --check`` as a test, so a hand-edited icon fails
    here rather than surprising the next person who runs the script."""
    stale = [
        app.ico_path for app in icons.APPS if (_ROOT / app.ico_path).read_bytes() != _ico_bytes(app)
    ]
    assert not stale, f"run python scripts/build_app_icons.py -- stale: {stale}"


def test_each_icon_carries_every_size_windows_asks_for() -> None:
    """A missing 16px entry is the one that shows: Windows scales the nearest
    size down and the result is a smear in the tray."""
    for app in icons.APPS:
        with icons.Image.open(_ROOT / app.ico_path) as image:
            sizes = {size[0] for size in image.info["sizes"]}
        assert set(icons.ICON_SIZES) <= sizes, (
            f"{app.key} is missing {set(icons.ICON_SIZES) - sizes}"
        )
