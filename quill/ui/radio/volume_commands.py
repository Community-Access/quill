"""One volume for every station, and the command that turns it on.

The problem this solves: Quill Radio remembers a volume *per favorite*, and that
per-station level wins outright. With twenty favorites each carrying their own
level there was no way to turn them all down -- you had to play each station in
turn and adjust it. Volume Boost, channel mode, night mode and OptiLab are all
listener-level and global; the plain volume was the odd one out.

Turning **Use One Volume for All Stations** on makes ``RadioHistory.volume_percent``
the single level every station plays at, so Volume Up/Down set *it* and turning
the volume down turns everything down.

Two deliberate choices:

* **Per-station levels are kept, never erased.** Turning the setting back off
  restores every station's own level exactly as it was, so trying this out costs
  nothing. ``forget_station_volumes`` exists for the listener who genuinely wants
  them gone, and it asks first.
* **Turning it on adopts what you are hearing.** Whatever the current station is
  playing at becomes the shared level, so the radio does not lurch to some
  half-remembered number the moment you flip the switch.

Lives outside ``main_frame_radio`` so that module stays under its GATE-11 size
budget, the same split ``quick_play`` and ``song_history_commands`` use.
"""

from __future__ import annotations

from typing import Any

from quill.core.paths import app_data_dir
from quill.core.radio import history as radio_history

#: Menu/command label. Carries its own state for the Command Palette, which
#: lists a command's title verbatim and has no checkmark to show it (#1383).
_LABEL = "Internet Radio: Use One Volume for All Stations"


def command_title(host: Any) -> str:
    """The palette label, naming whether the setting is currently on or off."""
    state = "On" if getattr(host._radio_history, "use_global_volume", False) else "Off"
    return f"{_LABEL} (currently {state})"


def _current_volume(host: Any) -> int:
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return -1
    return int(getattr(controller.state, "volume_percent", -1) or -1)


def toggle_global_volume(host: Any) -> None:
    """Flip "one volume for all stations", and say what it now means."""
    history = host._radio_history
    # getattr for the read, so a history object predating the setting flips on
    # from the historical default rather than raising.
    history.use_global_volume = not getattr(history, "use_global_volume", False)

    if history.use_global_volume:
        # Adopt what is playing right now, so nothing jumps.
        playing = _current_volume(host)
        if playing >= 0:
            history.volume_percent = playing
        radio_history.save_history(app_data_dir(), history)
        level = history.volume_percent
        detail = f" Every station now plays at {level} percent." if level >= 0 else ""
        host._announce(f"One volume for all stations, on.{detail}.")
    else:
        radio_history.save_history(app_data_dir(), history)
        host._announce(
            "One volume for all stations, off. Each station goes back to its own remembered volume."
        )

    # Keep the palette entry honest about the new state (#1383).
    commands = getattr(host, "commands", None)
    if commands is not None:
        commands.set_title("radio.toggle_global_volume", command_title(host))
    _sync_menu_check(host, history.use_global_volume)


def _sync_menu_check(host: Any, checked: bool) -> None:
    """Tick or untick the menu item to match the setting.

    wx flips a check item by itself when the *menu* is used, but the Command
    Palette and a rebound chord reach the handler directly -- and then the menu
    would still show the old state. Screen-reader users hear that checkmark, so
    it has to follow however the setting was changed.
    """
    item_id = getattr(host, "_global_volume_item_id", None)
    frame = getattr(host, "frame", None)
    if item_id is None or frame is None:
        return
    try:
        menu_bar = frame.GetMenuBar()
        if menu_bar is None:
            return
        item = menu_bar.FindItemById(item_id)
        if item is not None and item.IsCheckable():
            item.Check(checked)
    except Exception:  # noqa: BLE001 - a menu that will not update is not worth a crash
        return


def forget_station_volumes(host: Any) -> None:
    """Clear every favorite's remembered volume, after confirming.

    The way back to "every station just uses one volume" for someone who set
    thirty per-station levels over the years and wants them gone rather than
    merely bypassed.
    """
    import wx

    store = host._radio_favorites
    remembered = [fav for fav in store.favorites if fav.volume_percent >= 0]
    if not remembered:
        host._announce("No station has its own remembered volume.")
        return
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Forget the remembered volume for {len(remembered)} station(s)?\n\n"
        "They will all follow the one shared volume from now on. Your stations, "
        "folders, and every other setting are untouched.",
        "Forget Station Volumes",
        wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
        host.frame,
    )
    if answer != wx.YES:
        return
    for favorite in remembered:
        # clear_volume, never set_volume(-1): the latter clamps to 0 and would
        # silence every station rather than clearing its preference.
        store.clear_volume(favorite.key)
    host._persist_radio_favorites()
    host._announce(f"Forgot the volume for {len(remembered)} station(s).")
