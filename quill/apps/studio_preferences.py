"""Audio Studio's Preferences dialog: assembling it, and applying what came back.

Split out of :mod:`quill.apps.studio` under GATE-11 (extract, never
rebaseline) when App Sounds Play On... joined it on 2026-10-14. One function
builds every row and applies every answer, so the order of the checkboxes and
the order they are unpacked in sit side by side.
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from typing import Any

from quill.ui import app_sounds, slider_keys


def apply_asio_preference(
    prefs: dict[str, object], environ: MutableMapping[str, str] | None = None
) -> bool:
    """Turn on PortAudio's ASIO build when Use ASIO sound cards is on.

    Read once at launch, because the choice only counts before sounddevice is
    first imported -- which is why the setting says "after restarting Studio".
    Returns whether ASIO was asked for.
    """
    wanted = bool(prefs.get("use_asio"))
    if wanted:
        (os.environ if environ is None else environ)["SD_ENABLE_ASIO"] = "1"
    return wanted


def open_preferences(app: Any) -> None:
    """Studio > Preferences (Ctrl+,)."""
    from quill.apps.studio import (
        _CLOSE_ACTION_LABELS,
        _CLOSE_ACTION_VALUES,
        _TITLE,
        _save_app_prefs,
    )
    from quill.ui.app_preferences_dialog import (
        PreferenceCheckbox,
        PreferenceChoice,
        PreferencesDialog,
    )

    prefs = app._app_prefs
    close_index = _CLOSE_ACTION_VALUES.index(str(prefs["close_action"]))
    dialog = PreferencesDialog(
        app.frame,
        app_title=_TITLE,
        checkboxes=[
            PreferenceCheckbox(
                "&Check for updates automatically on launch",
                "Check for updates automatically on launch",
                bool(prefs["check_updates_on_startup"]),
            ),
            PreferenceCheckbox(
                "Alt+F&4 minimizes to the system tray",
                "When on, Alt+F4 sends the Studio to the system tray with any "
                "narration run still going, instead of closing the window. The "
                "titlebar X and Exit keep the 'When closing the window' behavior",
                bool(prefs["alt_f4_to_tray"]),
            ),
            PreferenceCheckbox(
                "&Speak progress milestones during long runs",
                "During a narration or build run, announce 25, 50, and 75 "
                "percent so you can follow progress without checking the window",
                bool(prefs["announce_run_milestones"]),
            ),
            PreferenceCheckbox(
                "Use AS&IO sound cards (after restarting Studio)",
                "Let recordings and the mixer use professional audio interfaces through "
                "their ASIO drivers, for the lowest delay. Takes effect the next time Studio "
                "starts. Most ASIO drivers allow one program at a time",
                bool(prefs.get("use_asio", False)),
            ),
        ],
        choices=[
            PreferenceChoice(
                "When &closing the window:",
                "What the titlebar X does. 'Ask when work is running' only "
                "prompts while an export is still going; an idle window just "
                "closes",
                list(_CLOSE_ACTION_LABELS),
                close_index,
            ),
        ],
        actions=[app_sounds.preference_action(app), slider_keys.preference_action(app)],
        announce_cb=app._announce,
    )
    result = dialog.show()
    if result is None:
        return
    checkbox_values, choice_indices, _texts = result
    (
        prefs["check_updates_on_startup"],
        prefs["alt_f4_to_tray"],
        prefs["announce_run_milestones"],
        prefs["use_asio"],
    ) = checkbox_values
    prefs["close_action"] = _CLOSE_ACTION_VALUES[choice_indices[0]]
    _save_app_prefs(prefs)
    # Saving preferences is important, but announcing it on close is noisy: the
    # dialog itself already commits the change, and leaving it should return the
    # user to what they were doing without extra speech.
    try:
        app._set_status_quiet("Preferences saved")
    except Exception:
        pass
