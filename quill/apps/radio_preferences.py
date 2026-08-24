"""Quill Radio's Preferences dialog: assembling it, and applying what came back.

Extracted from ``quill/apps/radio.py`` under GATE-11 (extract, never
rebaseline) when the two scheduled-recording wake settings arrived. It is a
coherent unit rather than an arbitrary slice: one function builds every
control, and the same function applies every answer, so the order of the
checkbox list and the order it is unpacked in can never drift apart -- which is
the one bug this dialog's shape makes easy.

Wiring only. Every setting it touches lives in ``core/radio/history.py`` and
every behaviour behind one lives in its own module.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import startup_window


def _open_data_folder(app: Any) -> None:
    from quill.apps.radio import _TITLE
    from quill.ui.data_folder_dialog import open_data_folder_dialog

    open_data_folder_dialog(app, app_title=_TITLE)


def open_preferences(app: Any) -> None:
    """Show Preferences, then apply every answer it came back with."""
    # The app module owns these display tables; imported at call time so this
    # module and quill.apps.radio never import each other at import time.
    from quill.apps.radio import (
        _CLOSE_ACTION_LABELS,
        _CLOSE_ACTION_VALUES,
        _DEFAULT_NOW_PLAYING_TEMPLATE,
        _ENGINE_HELP,
        _ENGINE_LABELS,
        _ENGINE_VALUES,
        _FAVORITES_SORT_LABELS,
        _FAVORITES_SORT_VALUES,
        _NOW_PLAYING_HELP,
        _OUTPUT_DEVICE_HELP,
        _TITLE,
    )
    from quill.core.paths import app_data_dir
    from quill.core.radio import history as radio_history
    from quill.ui.app_preferences_dialog import (
        PreferenceAction,
        PreferenceCheckbox,
        PreferenceChoice,
        PreferencesDialog,
        PreferenceText,
    )
    from quill.ui.radio.mpv_radio_engine import list_audio_devices, output_device_choices

    history = app._radio_history
    close_action_index = _CLOSE_ACTION_VALUES.index(history.close_action)
    device_labels, device_names, device_index = output_device_choices(
        list_audio_devices(), history.output_device
    )
    catalog_interval_labels = [
        "Every 6 hours",
        "Every 12 hours",
        "Every 24 hours (default)",
        "Every 2 days",
        "Manually only",
    ]
    catalog_interval_values = [6, 12, 24, 48, 0]
    try:
        catalog_interval_index = catalog_interval_values.index(
            int(getattr(history, "catalog_refresh_hours", 24))
        )
    except ValueError:
        catalog_interval_index = 2
    episode_limit_labels = [
        "10 newest",
        "25 newest (default)",
        "50 newest",
        "100 newest",
        "All episodes",
    ]
    episode_limit_values = [10, 25, 50, 100, 0]
    try:
        episode_limit_index = episode_limit_values.index(
            int(getattr(history, "subscription_episode_limit", 25))
        )
    except ValueError:
        episode_limit_index = 1
    dialog = PreferencesDialog(
        app.frame,
        app_title=_TITLE,
        checkboxes=[
            PreferenceCheckbox(
                "Resume Last Station on &Launch",
                "Resume Last Station on Launch",
                history.resume_on_launch,
            ),
            PreferenceCheckbox(
                "&Check for updates automatically on launch",
                "Check for updates automatically on launch",
                history.check_updates_on_startup,
            ),
            PreferenceCheckbox(
                "&Announce dialog transitions (more spoken detail)",
                "Announce dialog transitions -- off by default to reduce alert noise",
                history.announce_dialog_transitions,
            ),
            PreferenceCheckbox(
                "&Recover failed streams from the station's website",
                "When a station's stream won't play, scan the station's own "
                "website for a working one -- on by default",
                history.recover_from_website,
            ),
            PreferenceCheckbox(
                "Alt+F&4 minimizes to the system tray",
                "When on, Alt+F4 sends Quill Radio to the system tray, still "
                "playing, instead of closing the window. The titlebar X and "
                "Exit keep the 'When closing the window' behavior",
                history.alt_f4_to_tray,
            ),
            PreferenceCheckbox(
                "Verbose logging (&debug mode)",
                "Write detailed radio diagnostics -- playback, recording, and "
                "stream recovery -- to quill.log, for tracking down a "
                "hard-to-reproduce problem. Off by default (it is chatty)",
                history.debug_mode,
            ),
            PreferenceCheckbox(
                "&Keep the computer awake while playing or recording",
                "Stop Windows from going to sleep while a station is playing "
                "or a recording is running, so the audio does not cut off. "
                "On by default. (The screen may still turn off.)",
                history.prevent_sleep,
            ),
            PreferenceCheckbox(
                "Keep the computer awake &before a scheduled recording",
                "A scheduled recording cannot start on a sleeping computer, "
                "so Quill Radio stops Windows going to sleep for the few "
                "minutes before one is due. On by default.",
                history.keep_awake_before_recording,
            ),
            PreferenceCheckbox(
                "Wa&ke the computer for a scheduled recording",
                "If the computer is already asleep when a recording is due, "
                "ask Windows to wake it a couple of minutes beforehand. This "
                "adds a task to Windows Task Scheduler. On by default; turn "
                "it off to leave your machine's sleep entirely alone.",
                history.wake_for_scheduled_recording,
            ),
            PreferenceCheckbox(
                "Keep a local station catalo&g on this computer",
                "Browse the station directories instantly from a copy kept on "
                "this computer, updated quietly in the background. Turning it "
                "off restores live-only browsing; nothing is stored.",
                history.catalog_enabled,
            ),
            PreferenceCheckbox(
                "Check for station catalog &updates when Quill Radio starts",
                "A quick background check shortly after launch, skipped when "
                "the catalog is already fresh. On by default.",
                history.catalog_refresh_on_startup,
            ),
            PreferenceCheckbox(
                "&Winamp-style playback keys in the Recordings player",
                "The Winamp classic keys in Recordings: X play, C pause, "
                "V stop, B next, Z previous, arrows to seek, T for elapsed "
                "or remaining, J to jump to a recording. On by default; "
                "turn it off to use letter keys for list typeahead instead",
                getattr(history, "winamp_playback_keys", True),
            ),
        ],
        choices=[
            PreferenceChoice(
                "&Open this window at startup:",
                "Which one window Quill Radio opens for you at launch, over "
                "the main window and never instead of it. Everything else "
                "stays closed until you ask for it. None is the default -- an "
                "app that opens a window you did not ask for is an app you "
                "have to close a window to start using",
                [label for _wid, label in startup_window.STARTUP_WINDOWS],
                startup_window.index_of(history.startup_window),
            ),
            PreferenceChoice(
                "When &closing the window:",
                "When closing the window",
                list(_CLOSE_ACTION_LABELS),
                close_action_index,
            ),
            PreferenceChoice(
                "Playback &engine:",
                _ENGINE_HELP,
                list(_ENGINE_LABELS),
                _ENGINE_VALUES.index(history.playback_engine),
            ),
            PreferenceChoice(
                "Radio &output device:",
                _OUTPUT_DEVICE_HELP,
                device_labels,
                device_index,
            ),
            PreferenceChoice(
                "&Favorites sort order:",
                "How your favorites are ordered in the list. Ascending (A to "
                "Z) and Descending (Z to A) sort folders and stations by name "
                "and re-sort when you add one; Unsorted keeps your "
                "hand-arranged Move Up/Down order. A folder can override this "
                "for its own stations from its context menu.",
                list(_FAVORITES_SORT_LABELS),
                _FAVORITES_SORT_VALUES.index(history.favorites_sort),
            ),
            PreferenceChoice(
                "Station catalog update &frequency:",
                "How often the background refresh runs. Sources are checked "
                "one at a time on their own schedules -- a trickle, never a "
                "burst. Station > Update Station Catalog always works.",
                catalog_interval_labels,
                catalog_interval_index,
            ),
            PreferenceChoice(
                "Ep&isodes listed per subscribed podcast:",
                "How many of a show's newest episodes appear under Browse "
                "Stations > Podcasts > Subscriptions. Quill Radio keeps this "
                "simple on purpose; downloads, retention, and the full "
                "archive live in Quill Cast.",
                episode_limit_labels,
                episode_limit_index,
            ),
        ],
        texts=[
            PreferenceText(
                "&What's Playing announcement:",
                _NOW_PLAYING_HELP,
                history.now_playing_template,
            ),
            PreferenceText(
                "&Log folder:",
                "Where quill.log is written; leave blank for the default. "
                "Changing it moves the log immediately.",
                history.log_dir,
            ),
        ],
        actions=[
            PreferenceAction(
                "Reset &All Stations' Sound Enhancements...",
                "Reset all stations' Sound Enhancements to the shared default",
                app._reset_all_sound_enhancements,
            ),
            PreferenceAction(
                "Data Fol&der...",
                "Where every Quill app stores settings, favorites, and "
                "subscriptions. Choose a folder a service like Dropbox or "
                "OneDrive keeps in sync to carry them between computers.",
                lambda: _open_data_folder(app),
            ),
        ],
        announce_cb=app._announce,
    )
    result = dialog.show()
    if result is None:
        return
    checkbox_values, choice_indices, text_values = result
    (
        history.resume_on_launch,
        history.check_updates_on_startup,
        history.announce_dialog_transitions,
        history.recover_from_website,
        history.alt_f4_to_tray,
        history.debug_mode,
        history.prevent_sleep,
        history.keep_awake_before_recording,
        history.wake_for_scheduled_recording,
        history.catalog_enabled,
        history.catalog_refresh_on_startup,
        history.winamp_playback_keys,
    ) = checkbox_values
    # Apply verbose logging immediately (quill-radio #5) so it takes effect
    # this session, not just the next launch.
    from quill.core.radio.radio_logging import set_radio_debug

    set_radio_debug(history.debug_mode)
    history.startup_window = startup_window.from_index(choice_indices[0])
    # Kept in step so a downgrade, or anything still reading the old flag,
    # sees an answer that matches the choice.
    history.open_browse_at_startup = history.startup_window == "browse"
    history.close_action = _CLOSE_ACTION_VALUES[choice_indices[1]]
    chosen_engine = _ENGINE_VALUES[choice_indices[2]]
    if chosen_engine != history.playback_engine:
        history.playback_engine = chosen_engine
        # A playing station reconnects through the newly chosen backend.
        app._radio_controller.set_playback_engine(chosen_engine)
    chosen_device = device_names[choice_indices[3]]
    if chosen_device != history.output_device:
        history.output_device = chosen_device
        # Reconnects a playing station through the right engine; a
        # station already on air moves to the new device immediately.
        app._radio_controller.set_output_device(chosen_device)
    chosen_sort = _FAVORITES_SORT_VALUES[choice_indices[4]]
    history.catalog_refresh_hours = catalog_interval_values[choice_indices[5]]
    history.subscription_episode_limit = episode_limit_values[choice_indices[6]]
    if chosen_sort != history.favorites_sort:
        history.favorites_sort = chosen_sort
        app._reload_favorites_tree()
    new_template = text_values[0].strip()
    history.now_playing_template = new_template or _DEFAULT_NOW_PLAYING_TEMPLATE
    new_log_dir = text_values[1].strip()
    if new_log_dir != history.log_dir:
        history.log_dir = new_log_dir
        # Relocate the live log so new records land in the chosen folder now
        # (quill-radio #5), not just next launch.
        listener = getattr(app, "_log_listener", None)
        if listener is not None:
            from pathlib import Path

            from quill.stability.logging_config import relocate_log

            target = Path(new_log_dir) if new_log_dir else app_data_dir() / "logs"
            relocate_log(listener, target)
    radio_history.save_history(app_data_dir(), history)
    # Apply the Prevent Sleep choice now: acquire the keep-awake lock if a
    # station is already playing, or release it if the user just turned it off.
    app._update_sleep_inhibitor()
    menu_bar = app.frame.GetMenuBar()
    if menu_bar is not None:
        menu_bar.Check(int(app._resume_menu_item_id), history.resume_on_launch)
    app._announce("Preferences saved.")
