"""How big each app's window opens, and where that answer is kept.

Every app in the family opened at a size written into its own source and forgot
whatever you did to the window: Quill Radio at 460x360, QUILL at 1000x700,
Beacon at 1100x720, and none of them remembered a thing between launches. Resize
QUILL to fill your screen, close it, open it again -- 1000x700, every time. The
only app that remembered was QUILL Lite, and it is the one this module is
modelled on.

**Maximized is the default, and that is an accessibility decision rather than a
preference.** A small window is where the two failures this codebase keeps
finding come from: text clipped because a control is narrower than its label
(the status-bar truncation JAWS reads back off the screen), and a list showing
four rows where the screen had room for thirty, which a listener pays for in
arrow keys on every visit. Neither is visible to whoever chose the number: they
had a big monitor and a default font. Opening maximized costs a sighted user one
keystroke to undo and is *remembered* when they do; opening small costs
everybody else something on every launch.

**Remembered, not forced.** Somebody who tiles Quill Radio beside their browser
is doing something deliberate, and an app that fights that every launch is worse
than one that opened small. So the rule is: maximized until you say otherwise,
and then whatever you said. A restored size is only recorded while the window is
*not* maximized -- otherwise un-maximizing would restore the full-screen size and
the window would never come back to the size you actually chose.

One store, keyed per app, in the shape ``app_features`` already uses: shared file,
per-app entry, so QUILL's window size can never be Quill Radio's. QUILL Lite is
deliberately absent from it and keeps its geometry in its own settings file, for
the same reason it keeps its abbreviations there: a machine that has never had
QUILL installed must not grow a Quill data folder because somebody opened a text
file.

wx-free. Whether a window *is* maximized is wx's question and is asked in
:mod:`quill.ui.window_state`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "STORE_NAME",
    "WindowGeometry",
    "load_geometry",
    "save_geometry",
]

STORE_NAME = "app_window_geometry.json"

#: No window may be remembered smaller than this. A window restored to 40x30 --
#: from a bad write, a display that has gone away, or a hand-edited file -- is
#: one nobody can find the title bar of, and there is no keyboard route to
#: "make that window usable again".
MIN_WIDTH = 320
MIN_HEIGHT = 240


@dataclass(slots=True)
class WindowGeometry:
    """What an app's main window should open as.

    ``width``/``height`` of zero means "the size this app asks for in its own
    code" -- the value is only meaningful once a user has actually chosen one by
    resizing, and inventing a number before then would override an app's
    considered default with this module's guess.
    """

    maximized: bool = True
    width: int = 0
    height: int = 0

    def restored_size(self, fallback: tuple[int, int]) -> tuple[int, int]:
        """The size to open at, in pixels, honouring *fallback* when unset."""
        if self.width <= 0 or self.height <= 0:
            return fallback
        return (max(MIN_WIDTH, self.width), max(MIN_HEIGHT, self.height))


def _store_path(data_dir: Path) -> Path:
    return data_dir / STORE_NAME


def _read_all(data_dir: Path) -> dict:
    import json

    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def load_geometry(data_dir: Path, app_id: str) -> WindowGeometry:
    """What *app_id*'s window should open as. A missing or broken file is the default.

    Defaults rather than an error, always: a geometry store that cannot be read
    must leave the app openable. The worst case is a window the size the app
    would have used anyway.
    """
    entry = _read_all(data_dir).get(str(app_id))
    if not isinstance(entry, dict):
        return WindowGeometry()
    maximized = entry.get("maximized")
    return WindowGeometry(
        maximized=bool(maximized) if isinstance(maximized, bool) else True,
        width=_positive_int(entry.get("width")),
        height=_positive_int(entry.get("height")),
    )


def _positive_int(value: object) -> int:
    """*value* as a positive int, or 0 for anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    number = int(value)
    return number if number > 0 else 0


def save_geometry(data_dir: Path, app_id: str, geometry: WindowGeometry) -> None:
    """Persist one app's geometry without disturbing the others'."""
    from quill.core.storage import write_json_atomic

    raw = _read_all(data_dir)
    entry: dict[str, object] = {"maximized": bool(geometry.maximized)}
    if geometry.width > 0 and geometry.height > 0:
        entry["width"] = max(MIN_WIDTH, int(geometry.width))
        entry["height"] = max(MIN_HEIGHT, int(geometry.height))
    raw[str(app_id)] = entry
    write_json_atomic(_store_path(data_dir), raw)
