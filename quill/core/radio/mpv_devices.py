"""What mpv says about sound cards, as the Preferences dropdown needs it.

Split from ``quill/ui/radio/mpv_radio_engine.py`` under GATE-11 (extract, never
rebaseline) when the time-shift buffer moved to disk. Pure and wx-free: the two
functions here only read mpv's JSON and build the dropdown model; enumerating
the devices still happens in the engine module, which owns libmpv.
"""

from __future__ import annotations

import json


def parse_audio_device_list(raw: str) -> list[tuple[str, str]]:
    """``(name, description)`` pairs out of mpv's ``audio-device-list`` JSON.

    Pure and unit-tested; malformed input yields ``[]`` rather than raising.
    The *name* (e.g. ``wasapi/{guid}``) is the stable value to persist and
    hand back to ``audio-device``; the *description* is the human label
    ("Speakers (Realtek High Definition Audio)").

    mpv's list includes pseudo-entries that are not sound cards: ``auto``
    (what "System default" already means) and bare driver fallbacks with no
    device part (``openal``, ``sdl``). Both are dropped so the Preferences
    dropdown lists only real, pickable devices.
    """
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    devices: list[tuple[str, str]] = []
    if not isinstance(data, list):
        return []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name or name == "auto" or "/" not in name:
            continue
        description = str(entry.get("description", "")).strip() or name
        devices.append((name, description))
    return devices


#: The always-first dropdown entry (device name ""): keeps radio on the
#: wx.media engine, byte-for-byte today's path.
SYSTEM_DEFAULT_DEVICE_LABEL = "System default"


def output_device_choices(
    devices: list[tuple[str, str]], current: str
) -> tuple[list[str], list[str], int]:
    """The Preferences dropdown model: labels, parallel device names, and
    the selected index (pure, unit-tested).

    "System default" is always first (name ""). A saved device that is not
    currently connected still appears -- marked, at the end -- so opening
    Preferences never silently resets the choice just because a USB sound
    card is unplugged today.
    """
    labels = [SYSTEM_DEFAULT_DEVICE_LABEL]
    names = [""]
    for name, description in devices:
        labels.append(description)
        names.append(name)
    current = current.strip()
    if current and current not in names:
        labels.append(f"{current} (not currently available)")
        names.append(current)
    return labels, names, names.index(current) if current in names else 0
