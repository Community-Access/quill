"""Which way the arrow keys move a slider, for every QUILL app at once. wx-free.

A Windows slider (a trackbar) moves *down* on Up and Page Up and to its start
on Home: to the control, Up is "towards the start", and on a horizontal bar the
start is the left end. QUILL's volume sliders have answered Up with louder
since 2026-09-28, because that is what the Windows volume mixer says every day
-- but some listeners know the trackbar's own keys and expect them, and one
said (2026-10-26) that his full volume read as the bottom of the scale. Both
are reasonable, so both are offered, once, for the whole family:

* :data:`UP_IS_MORE` (the default): Up, Page Up and Home raise the value --
  Home is the top, 100 percent on a volume -- and Down, Page Down and End lower
  it, End being 0.
* :data:`WINDOWS`: the trackbar's own keys -- Down, Page Down and End raise it,
  Up, Page Up and Home lower it.

Right is more and Left is less in both: they already agree.

One file, ``slider_keys.json`` in the shared data folder, rather than a field
in every app's settings: it is one choice about how a kind of control works,
so changing it in Quill Radio changes it in QUILL Cast at the next key press.
Read with a modification-time check, so a key press costs a ``stat``.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = [
    "CHOICES",
    "FILE_NAME",
    "UP_IS_MORE",
    "WINDOWS",
    "current",
    "describe",
    "save",
]

FILE_NAME = "slider_keys.json"

UP_IS_MORE = "up_is_more"
WINDOWS = "windows"

#: ``(value, what the chooser lists)``, the default first.
CHOICES: tuple[tuple[str, str], ...] = (
    (
        UP_IS_MORE,
        "Up is more: Up, Page Up and Home raise it (Home is 100 percent); "
        "Down, Page Down and End lower it (End is 0)",
    ),
    (
        WINDOWS,
        "As Windows sliders: Down, Page Down and End raise it (End is 100 percent); "
        "Up, Page Up and Home lower it (Home is 0)",
    ),
)

_cache: dict[Path, tuple[float, str]] = {}


def _normalize(value: object) -> str:
    return value if value in (UP_IS_MORE, WINDOWS) else UP_IS_MORE  # type: ignore[return-value]


def current(data_dir: Path) -> str:
    """The family's choice; :data:`UP_IS_MORE` when none has been made."""
    path = data_dir / FILE_NAME
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return UP_IS_MORE
    cached = _cache.get(path)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return UP_IS_MORE
    layout = _normalize(raw.get("layout") if isinstance(raw, dict) else None)
    _cache[path] = (stamp, layout)
    return layout


def save(data_dir: Path, layout: str) -> None:
    """Record *layout* for every app. Raises ``OSError``."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(data_dir / FILE_NAME, {"version": 1, "layout": _normalize(layout)})
    _cache.pop(data_dir / FILE_NAME, None)


def describe(layout: str) -> str:
    """The sentence said when *layout* is chosen."""
    if _normalize(layout) == WINDOWS:
        return "Sliders now use the Windows keys: Down and End raise them, Up and Home lower them."
    return "Sliders now use Up is more: Up and Home raise them, Down and End lower them."
