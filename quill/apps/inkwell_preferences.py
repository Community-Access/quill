"""Quill Inkwell's Preferences (Ctrl+,): every switch in one window, searchable.

Inkwell's settings were all real and all saved, but they lived as check marks
in the Options menu, where nothing could search them and a screen-reader user
had to walk the menu to learn what was there (qc.md X-01). Every app in the
family answers Ctrl+, with Preferences and a *Find a setting* field; this is
Inkwell's. The menu rows stay -- they are the quick way -- and both routes
change the same saved values, so the check marks are kept true here.

Rows are keyed to :data:`quill.core.app_settings_index.INKWELL_SETTINGS`, so
the search matches the words people use ("tray", "startup", "clipboard"),
not only the label. Split out of :mod:`quill.apps.inkwell` under GATE-11.
"""

from __future__ import annotations

from typing import Any

from quill.core.app_settings_index import INKWELL_SETTINGS

__all__ = ["open_preferences"]


def open_preferences(host: Any) -> None:
    """Options > Preferences (Ctrl+,)."""
    from quill.ui.app_preferences_dialog import (
        PreferenceAction,
        PreferenceCheckbox,
        PreferencesDialog,
    )

    settings = host._settings
    startup = host._launch_at_startup_enabled()
    dialog = PreferencesDialog(
        host.frame,
        app_title="Quill Inkwell",
        checkboxes=[
            PreferenceCheckbox(
                "&Expand in other applications",
                "Expand in other applications. Off pauses expansion everywhere "
                "but QUILL; your abbreviations are kept.",
                bool(settings.expansion_enabled),
                key="inkwell.expansion_enabled",
            ),
            PreferenceCheckbox(
                "Start Quill Inkwell with &Windows",
                "Start Quill Inkwell with Windows, in the tray, so expansion is "
                "ready when you sign in.",
                startup,
                key="inkwell.start_with_windows",
            ),
            PreferenceCheckbox(
                "Start &minimized to the tray",
                "Start minimized to the tray: open with no window, only the tray icon.",
                bool(settings.start_in_tray),
                key="inkwell.start_in_tray",
            ),
            PreferenceCheckbox(
                "&Close button keeps expanding",
                "Close button keeps expanding: closing the window leaves Inkwell "
                "running in the tray. Off, closing exits.",
                bool(settings.close_to_tray),
                key="inkwell.close_to_tray",
            ),
            PreferenceCheckbox(
                "Insert by &pasting (for apps that drop typed text)",
                "Insert by pasting: borrow the clipboard to insert, then restore "
                "it. Only for programs that drop typed text.",
                settings.injection_mode == "paste",
                key="inkwell.paste",
            ),
            PreferenceCheckbox(
                "&Announce every expansion",
                "Announce every expansion with a short spoken confirmation.",
                bool(settings.announce_expansions),
                key="inkwell.announce_expansions",
            ),
        ],
        actions=[
            PreferenceAction(
                "E&xcluded Applications...",
                "Excluded Applications: programs where expansion never runs, on "
                "top of the password managers that are always left alone. Opens now.",
                host.edit_exclusions,
                key="inkwell.excluded_processes",
            ),
        ],
        announce_cb=host._announce,
        declared=list(INKWELL_SETTINGS),
    )
    result = dialog.show()
    if result is None:
        return
    (expand, start_windows, start_tray, close_tray, paste, announce), _c, _t = result
    # Each setter that changes something says so; the quiet ones are gathered
    # into one sentence, so a save is never silent and never says a thing twice.
    quiet_changes = 0
    if expand != bool(settings.expansion_enabled):
        host.set_expansion_enabled(expand)
    if start_windows != startup:
        host._set_launch_at_startup(start_windows)
    if paste != (settings.injection_mode == "paste"):
        host._set_injection_mode(paste)
    for name, value in (
        ("start_in_tray", start_tray),
        ("close_to_tray", close_tray),
        ("announce_expansions", announce),
    ):
        if value != bool(getattr(settings, name)):
            host._set_pref(name, value)
            quiet_changes += 1
    _sync_menu(host)
    if quiet_changes:
        host._announce("Preferences saved.")


def _sync_menu(host: Any) -> None:
    """Keep the Abbreviations and Options check marks true to the saved values."""
    bar = host.frame.GetMenuBar()
    if bar is None:
        return
    settings = host._settings
    for attribute, value in (
        ("_pause_item_id", settings.expansion_enabled),
        ("_startup_item_id", host._launch_at_startup_enabled()),
        ("_start_tray_item_id", settings.start_in_tray),
        ("_close_tray_item_id", settings.close_to_tray),
        ("_paste_item_id", settings.injection_mode == "paste"),
        ("_announce_item_id", settings.announce_expansions),
    ):
        item_id = getattr(host, attribute, None)
        if item_id is not None:
            bar.Check(int(item_id), bool(value))
