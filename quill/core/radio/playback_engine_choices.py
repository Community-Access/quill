"""The Playback engine dropdown, honest about what is on this computer.

Preferences offered three rows regardless -- Automatic (recommended), Windows
Media (classic), mpv -- and Jeff's reading of it on a machine without libmpv
(2026-09-29): "if mpv is not available then Windows Media should be selected
or automatic, that is confusing." A row for an engine that is not installed is
a choice that does nothing, and Automatic that never says which engine it
resolves to leaves the listener to guess. So the rows are built from what is
present, and Automatic says what it means today. wx-free and pure.
"""

from __future__ import annotations

__all__ = ["engine_choices"]

_WINDOWS_MEDIA = "Windows Media (classic)"


def engine_choices(current: str, *, mpv_present: bool) -> tuple[list[str], list[str], int]:
    """``(labels, values, selected index)`` for the Playback engine dropdown.

    With mpv present: Automatic (uses mpv), Windows Media (classic), mpv.
    Without it: Automatic (uses Windows Media; mpv is not installed) and
    Windows Media (classic) -- no row for an engine that is not there, and a
    saved "mpv" preference lands on Automatic, which is what it resolves to.
    """
    if mpv_present:
        labels = ["Automatic (recommended, uses mpv)", _WINDOWS_MEDIA, "mpv"]
        values = ["auto", "wx", "mpv"]
    else:
        labels = ["Automatic (uses Windows Media; mpv is not installed)", _WINDOWS_MEDIA]
        values = ["auto", "wx"]
    current = (current or "auto").strip()
    index = values.index(current) if current in values else 0
    return labels, values, index
