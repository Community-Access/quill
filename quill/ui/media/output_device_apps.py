"""How each QuillVille app answers "which sound card do you play through?".

:mod:`quill.ui.media.output_device` owns the picker; this owns the four facts
each app has to supply it with (:class:`~quill.ui.media.output_device.OutputDeviceBinding`):
its name, the engine actually playing, the device it saved last time, and how
to save a new one.

They live together rather than in each app because they are the same short
answer four times over, and because keeping them beside the picker is what
stops the next app from doing what Cast did -- shipping the menu item with no
way to answer it. An app's own module keeps a two-line forwarder, which is also
what keeps GATE-11 honest: this capability grew three modules past their
ceilings at once, and the ceiling is the signal that a shared thing wanted a
shared home.

Every binding asks the app for the engine rather than asking the machine what
it has installed. A computer with libmpv present can still be playing on the
classic ``wx.media`` control, which has no device API at all, and only the live
engine knows which it is.
"""

from __future__ import annotations

from typing import Any

from quill.ui.media.output_device import OutputDeviceBinding

__all__ = ["cast_binding", "media_player_binding", "read_device_pref", "save_device_pref"]

#: The Media Player's own preferences file -- the same one-file shape Audio
#: Studio uses. Only machine-local things live in it, so it is never part of a
#: portable backup: a device id names hardware on THIS computer, and carried
#: elsewhere it names nothing, or something else.
MEDIA_PLAYER_PREFS = "media-player-app.json"

#: The key inside it, matching the name the media config already reserves.
MEDIA_PLAYER_DEVICE_KEY = "media_output_device"


def read_device_pref(filename: str, key: str) -> str:
    """The device saved in a small per-app prefs file ("" when there is none).

    Never raises: an unreadable or half-written prefs file means the system
    default, which is the state every app starts in anyway.
    """
    from quill.core.paths import app_data_dir
    from quill.core.storage import read_json

    try:
        data = read_json(app_data_dir() / filename, {})
    except Exception:  # noqa: BLE001 - unreadable prefs mean the default
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get(key, "") or "")


def save_device_pref(filename: str, key: str, device: str) -> None:
    """Remember *device* for the next launch. Best effort, never raising.

    Reads the file back first so this writes one key rather than replacing
    whatever else the app keeps beside it.
    """
    from quill.core.paths import app_data_dir
    from quill.core.storage import read_json, write_json_atomic

    path = app_data_dir() / filename
    try:
        data = read_json(path, {})
        prefs = dict(data) if isinstance(data, dict) else {}
        prefs[key] = device
        write_json_atomic(path, prefs)
    except Exception:  # noqa: BLE001 - losing a preference beats crashing
        pass


def media_player_binding(app: Any) -> OutputDeviceBinding | None:
    """Quill Media Player: the transport panel holds the engine and the device.

    None while the panel is still being built -- the command then falls through
    to the routes :func:`~quill.ui.media.output_device.choose_output_device`
    already has, rather than costing the listener the keystroke.
    """
    player = getattr(app, "_player", None)
    if player is None:
        return None

    def _save(device: str) -> None:
        save_device_pref(MEDIA_PLAYER_PREFS, MEDIA_PLAYER_DEVICE_KEY, device)
        player.set_output_device(device)

    return OutputDeviceBinding(
        app_name="Quill Media Player",
        engine=player.output_engine(),
        current=player.output_device(),
        save=_save,
    )


def cast_binding(host: Any) -> OutputDeviceBinding | None:
    """QUILL Cast: the podcast controller holds the engine, the library the setting.

    Cast shipped the menu item with no way to answer it -- the engines it played
    through had no device API, so the command could only explain that Windows'
    own Sound settings were the route. Both engines can be pointed at a card
    now (2026-09-29), so the item does what its name says.

    The setting goes through the host's own save path, which knows when a large
    library has to coalesce its writes instead of writing inline.
    """
    controller = getattr(host, "_podcast_controller", None)
    library = getattr(host, "_podcast_library", None)
    if controller is None or library is None:
        return None

    def _save(device: str) -> None:
        library.settings.output_device = device
        host._save_podcast_library()

    return OutputDeviceBinding(
        app_name="QUILL Cast",
        engine=controller.output_engine(),
        current=library.settings.output_device,
        save=_save,
    )
