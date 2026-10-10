"""Quill Converter's Preferences (Ctrl+,): the family's door to its settings.

Every other app in the family answers Ctrl+, with a Preferences window whose
first field is *Find a setting*; Converter had neither (qc.md X-01). Most of
what Converter can be set to do is on its main window, in the same place as
the job it shapes, and stays there -- a second copy of the format list in
another window would be two places to set up one conversion. So this window
holds the two app-level switches that until now lived only in menus, and its
search reaches everything else through the declarative index in
:mod:`quill.core.app_settings_index`: choose *Bit rate* and Preferences
closes, Advanced Options is shown if it was hidden, focus lands on Bit rate,
and you hear where it was.

Split from :mod:`quill.apps.converter` (GATE-11: that module is at its cap).
"""

from __future__ import annotations

from typing import Any

from quill.core.app_settings_index import CONVERTER_SETTINGS
from quill.core.settings_finder import SettingEntry, moved_to

__all__ = ["go_to_setting", "open_preferences"]

#: Main-window settings -> the attribute holding the control.
_MAIN_CONTROLS = {
    "converter.format": "_format",
    "converter.preset": "_preset",
    "converter.effect": "_effect",
    "converter.chapters": "_chapters",
    "converter.dest_dir": "_dest",
}

#: Settings inside the Custom Effects window, which opens on its own focus.
_EFFECTS_WINDOW = frozenset({"converter.custom_effects", "converter.trim"})


def open_preferences(host: Any) -> None:
    """File > Preferences (Ctrl+,)."""
    from quill.ui.app_preferences_dialog import PreferenceCheckbox, PreferencesDialog

    settings = host._settings
    dialog = PreferencesDialog(
        host.frame,
        app_title="Quill Converter",
        checkboxes=[
            PreferenceCheckbox(
                "&Open the output folder when a conversion finishes",
                "Open the output folder when a conversion finishes. The same "
                "switch as Convert, Open Output Folder When Done.",
                bool(settings.open_folder_when_done),
                key="converter.open_folder_when_done",
            ),
            PreferenceCheckbox(
                "&Show Advanced Options in the main window",
                "Show Advanced Options in the main window: bit rate, sample "
                "rate, channels and the rest. The same switch as View, Advanced Options.",
                bool(settings.show_advanced),
                key="converter.show_advanced",
            ),
        ],
        announce_cb=host._announce,
        declared=list(CONVERTER_SETTINGS),
        go_elsewhere=lambda entry: go_to_setting(host, entry),
    )
    result = dialog.show()
    if result is None:
        return
    (open_when_done, show_advanced), _choices, _texts = result
    # Only what changed is applied, and each change says itself; an OK that
    # changed nothing says nothing, because nothing happened.
    if open_when_done != bool(settings.open_folder_when_done):
        host.set_open_when_done(open_when_done)
        _check_menu(host, "_open_when_done_item", open_when_done)
    if show_advanced != bool(settings.show_advanced):
        host.set_advanced_visible(show_advanced)
        _check_menu(host, "_advanced_item", show_advanced)
        host._announce("Advanced Options shown." if show_advanced else "Advanced Options hidden.")


def _check_menu(host: Any, attribute: str, value: bool) -> None:
    item_id = getattr(host, attribute, None)
    bar = host.frame.GetMenuBar()
    if item_id is not None and bar is not None:
        bar.Check(int(item_id), bool(value))


def go_to_setting(host: Any, entry: SettingEntry) -> None:
    """Carry focus to a setting outside Preferences, then say where it is."""
    if entry.key in _EFFECTS_WINDOW:
        # A window: the reader says its title, and the window focuses itself.
        host._on_custom_effects(None)
        return
    control = _main_window_control(host, entry)
    if control is None:
        return
    if not control.IsEnabled():
        host._announce(f"{entry.label} is unavailable in this build.")
        return
    control.SetFocus()
    host._announce(moved_to(entry))


def _main_window_control(host: Any, entry: SettingEntry) -> Any:
    attribute = _MAIN_CONTROLS.get(entry.key)
    if attribute is not None:
        return getattr(host, attribute, None)
    field = entry.key.removeprefix("converter.")
    if field == "recurse" or field in getattr(host, "_advanced_choices", {}):
        if not host._settings.show_advanced:
            from quill.apps import converter_advanced

            converter_advanced.reveal_for_navigation(host)
        if field == "recurse":
            return host._recurse
        return host._advanced_choices[field][0]
    return None
