"""Quill Media Player's Preferences (Ctrl+,): one searchable place to set it up.

The player's settings were scattered (qc.md X-01): three View check marks, a
Sleep Timer submenu, an output-device window, and the Audio tab and player
controls in the main window. Every other app in the family answers Ctrl+,
with Preferences and a *Find a setting* field; this is the player's.

It is honest about what lasts. Compact mode, Magical mode, Always on top and
the sleep timer have always reset when the player closes, so they sit in a
box labelled **This session only** rather than beside the output device,
which is saved. Nothing here adds a setting or a saved value: each row drives
the same handler its menu row does, and the check marks are kept true.

Settings that live in the main window -- speed, volume and the Audio tab --
stay there. The search reaches them through
:data:`quill.core.app_settings_index.PLAYER_SETTINGS`: choose *Skip silence*
and Preferences closes, the Audio tab comes forward (leaving Compact mode if
it was hiding it), focus lands on the checkbox, and you hear where you are.

Split from :mod:`quill.apps.player`, which is at its GATE-11 ceiling.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.app_settings_index import PLAYER_SETTINGS
from quill.core.settings_finder import SettingEntry, moved_to

__all__ = ["SESSION_GROUP", "go_to_setting", "open_preferences"]

#: The box every reset-on-close row sits in; short, because it is read on entry.
SESSION_GROUP = "This session only"

#: Sleep Timer choices, in the submenu's order: (label, minutes; -1 = chapter end).
_SLEEP = (("Off", 0), ("15 minutes", 15), ("30 minutes", 30), ("60 minutes", 60))
_SLEEP_CHOICES = (*_SLEEP, ("End of chapter", -1))

#: (menu-id key, current-value reader, handler name) per View toggle.
_TOGGLES = (
    ("compact", lambda host: bool(host._compact), "_on_toggle_compact"),
    ("magical", lambda host: bool(host._magical), "_on_toggle_magical"),
    ("on_top", lambda host: _on_top(host), "_on_toggle_ontop"),
)


def _on_top(host: Any) -> bool:
    import wx

    return bool(host.frame.GetWindowStyleFlag() & wx.STAY_ON_TOP)


def _sleep_minutes(host: Any) -> int:
    """The Sleep Timer submenu's checked row, as minutes (0 when none is)."""
    bar = host.frame.GetMenuBar()
    for item_id, minutes in getattr(host, "_sleep_minutes_by_id", {}).items():
        if bar is not None and bar.IsChecked(item_id):
            return int(minutes)
    return 0


def open_preferences(host: Any) -> None:
    """File > Preferences (Ctrl+,)."""
    from quill.ui.app_preferences_dialog import (
        PreferenceAction,
        PreferenceCheckbox,
        PreferenceChoice,
        PreferencesDialog,
    )

    before = [read(host) for _key, read, _handler in _TOGGLES]
    minutes = _sleep_minutes(host)
    sleep_values = [value for _label, value in _SLEEP_CHOICES]
    dialog = PreferencesDialog(
        host.frame,
        app_title="Quill Media Player",
        actions=[
            PreferenceAction(
                "Audio Output &Device...",
                "Audio Output Device: which sound card the book plays out of. "
                "Saved for next time. Opens now.",
                host._choose_output_device,
                key="player.output_device",
            ),
        ],
        checkboxes=[
            PreferenceCheckbox(
                "&Compact mode",
                "Compact mode: hide everything but the player controls. Resets "
                "when the player closes.",
                before[0],
                group=SESSION_GROUP,
                key="player.compact",
            ),
            PreferenceCheckbox(
                "&Magical mode",
                "Magical mode. Resets when the player closes.",
                before[1],
                group=SESSION_GROUP,
                key="player.magical",
            ),
            PreferenceCheckbox(
                "Always on &top",
                "Always on top: keep the player above other windows. Resets when "
                "the player closes.",
                before[2],
                group=SESSION_GROUP,
                key="player.on_top",
            ),
        ],
        choices=[
            PreferenceChoice(
                "&Sleep timer:",
                "Sleep timer: pause after a while, or at the end of the chapter. "
                "Choosing a time starts it when you press OK. Resets when the "
                "player closes.",
                [label for label, _value in _SLEEP_CHOICES],
                sleep_values.index(minutes) if minutes in sleep_values else 0,
                group=SESSION_GROUP,
                key="player.sleep",
            ),
        ],
        announce_cb=host._announce,
        declared=list(PLAYER_SETTINGS),
        go_elsewhere=lambda entry: go_to_setting(host, entry),
    )
    result = dialog.show()
    if result is None:
        return
    checks, (sleep_index,), _texts = result
    # Each handler says what changed, exactly as its menu row does.
    for (key, _read, handler), old, new in zip(_TOGGLES, before, checks, strict=True):
        if new != old:
            _toggle(host, key, handler, new)
    chosen = sleep_values[max(0, sleep_index)]
    if chosen != minutes:
        _set_sleep(host, chosen)


def _toggle(host: Any, key: str, handler: str, value: bool) -> None:
    item_id = getattr(host, "_view_toggle_ids", {}).get(key)
    bar = host.frame.GetMenuBar()
    if item_id is not None and bar is not None:
        bar.Check(int(item_id), value)
    getattr(host, handler)(SimpleNamespace(IsChecked=lambda: value))


def _set_sleep(host: Any, minutes: int) -> None:
    bar = host.frame.GetMenuBar()
    for item_id, value in host._sleep_minutes_by_id.items():
        if value == minutes:
            if bar is not None:
                bar.Check(item_id, True)
            host._on_set_sleep(SimpleNamespace(GetId=lambda i=item_id: i))
            return


def go_to_setting(host: Any, entry: SettingEntry) -> None:
    """Carry focus to a main-window setting, then say where it is."""
    control = _control(host, entry.key)
    if control is None:
        return
    control.SetFocus()
    host._announce(moved_to(entry))


def _control(host: Any, key: str) -> Any:
    transport = host._player
    if key == "player.speed":
        return getattr(transport, "_rate", None)
    if key == "player.volume":
        return getattr(transport, "_volume", None)
    panel = host._dsp_panel
    control = {
        "player.eq_preset": panel._preset,
        "player.eq_bands": panel._band_sliders[0] if panel._band_sliders else None,
        "player.boost": panel._boost,
        "player.normalize": panel._normalize,
        "player.skip_silence": panel._skip_silence,
    }.get(key)
    if control is None:
        return None
    if host._compact:  # Compact mode hides the tabs; the setting must be seen
        _toggle(host, "compact", "_on_toggle_compact", False)
    notebook = host._notebook
    for index in range(notebook.GetPageCount()):
        if notebook.GetPage(index) is panel:
            # ChangeSelection, not SetSelection: the page-changed handler would
            # say "Audio" and then this would say where -- the same fact twice.
            notebook.ChangeSelection(index)
            break
    return control
