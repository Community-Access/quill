"""Every QUILL app's "App sounds play on" choice, in one small file. wx-free.

One file for the whole family, ``app_sounds.json`` in the shared data folder,
rather than a field in each of eleven settings stores. Each app reads and
writes only its own entry, so the choices stay separate; but one file means one
loader, one format, one gate, and one place where "keep my apps in step" can
work -- which it does through the family's existing sharing switch
(core/family_preferences): an app that shares copies its choice to every other
app that shares.

Shape::

    {"version": 1,
     "apps": {"radio": {"choice": "follow", "remembered": ""}, ...}}

``choice`` is a value from :mod:`quill.core.app_sound_route`; ``remembered``
is what the on/off key (Alt+Shift+M) turned off, so turning the sounds back on
puts them back where they were -- ``null`` when there is nothing to go back to,
because ``""`` is a real place (the system default).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quill.core import app_sound_route

__all__ = ["AppSoundChoice", "FILE_NAME", "load", "save"]

FILE_NAME = "app_sounds.json"


class AppSoundChoice:
    """One app's answer, already normalised for that app."""

    __slots__ = ("choice", "remembered")

    def __init__(self, choice: str, remembered: str | None = None) -> None:
        self.choice = choice
        self.remembered = remembered

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, AppSoundChoice)
            and other.choice == self.choice
            and other.remembered == self.remembered
        )

    def __repr__(self) -> str:
        return f"AppSoundChoice({self.choice!r}, {self.remembered!r})"


def _read(data_dir: Path) -> dict[str, tuple[str, str | None]]:
    """``{app: (choice, remembered)}`` for every app that has saved one."""
    try:
        raw = json.loads((data_dir / FILE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    apps = raw.get("apps") if isinstance(raw, dict) else None
    if not isinstance(apps, dict):
        return {}
    return {
        str(app): (
            entry["choice"],
            entry["remembered"] if isinstance(entry.get("remembered"), str) else None,
        )
        for app, entry in apps.items()
        if isinstance(entry, dict) and isinstance(entry.get("choice"), str)
    }


def load(data_dir: Path, app: str, *, has_own_audio: bool) -> AppSoundChoice:
    """*app*'s choice, or its default when it has never made one."""
    saved = _read(data_dir).get(app)
    if saved is None:
        return AppSoundChoice(app_sound_route.default_for(has_own_audio))
    choice = app_sound_route.normalize(saved[0], has_own_audio=has_own_audio)
    remembered = (
        None
        if saved[1] is None
        else app_sound_route.normalize(saved[1], has_own_audio=has_own_audio)
    )
    if remembered == app_sound_route.NONE:
        remembered = None
    return AppSoundChoice(choice, remembered)


def save(
    data_dir: Path,
    app: str,
    value: AppSoundChoice,
    *,
    share_with: list[str] | tuple[str, ...] = (),
) -> None:
    """Write *app*'s choice, and the same choice for every app in *share_with*.

    A shared "Same as the app's audio" lands on an app with no audio of its own
    as written, and that app's :func:`load` reads it as the system default --
    the nearest thing it has.
    """
    from quill.core.storage import write_json_atomic

    record: dict[str, Any] = {
        name: {"choice": choice, "remembered": remembered}
        for name, (choice, remembered) in _read(data_dir).items()
    }
    for name in (app, *share_with):
        record[name] = {"choice": value.choice, "remembered": value.remembered}
    write_json_atomic(data_dir / FILE_NAME, {"version": 1, "apps": record})
