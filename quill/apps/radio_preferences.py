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

from quill.apps import radio_preferences_listening, radio_preferences_load
from quill.apps import radio_preferences_rows as rows
from quill.apps.radio_preferences_load import PreferencesDataLoad, podcast_schedule_help
from quill.core.radio import main_view, reminders
from quill.ui import app_sounds, slider_keys


def _open_data_folder(app: Any) -> None:
    from quill.apps.radio import _TITLE
    from quill.ui.data_folder_dialog import open_data_folder_dialog

    open_data_folder_dialog(app, app_title=_TITLE)


def _shown_channel() -> str:
    from quill.core.updater.channels import shown_channel, state_for

    return shown_channel(state_for("radio"))


def _open_release_channel(app: Any) -> None:
    from quill.ui.updates.shell import open_for_shell

    open_for_shell(app, "radio")


#: Preference group names (list.md 8.1). Written in the order somebody looks
#: for them, which is what the dialog preserves -- and short, because the box
#: label is read aloud every time focus enters the group.
_PODCASTS = "Podcasts"
_REMINDERS = "Reminders"


# Moved to radio_preferences_rows under GATE-11; the old names stay, because
# tests and the source-reading gates reach for them here.
_startup_checkbox = rows.startup_checkbox
_wake_checkbox = rows.wake_checkbox
PORTABLE_WAKE_HELP = rows.PORTABLE_WAKE_HELP
RESUME_CHOICES = rows.RESUME_CHOICES
_resume_index = rows.resume_index
_lead_index = rows.lead_index


def open_preferences(app: Any) -> None:
    """Show Preferences, then apply every answer it came back with."""
    # The app module owns these display tables; imported at call time so this
    # module and quill.apps.radio never import each other at import time.
    from quill.apps.radio import (
        _CLOSE_ACTION_LABELS,
        _CLOSE_ACTION_VALUES,
        _DEFAULT_NOW_PLAYING_TEMPLATE,
        _ENGINE_HELP,
        _FAVORITES_SORT_LABELS,
        _FAVORITES_SORT_VALUES,
        _NOW_PLAYING_HELP,
        _OUTPUT_DEVICE_HELP,
        _TITLE,
    )
    from quill.core.paths import app_data_dir
    from quill.core.podcasts import refresh_policy
    from quill.core.radio.playback_engine_choices import engine_choices
    from quill.ui.app_preferences_dialog import (
        PreferenceAction,
        PreferenceCheckbox,
        PreferenceChoice,
        PreferencesDialog,
        PreferenceText,
    )
    from quill.ui.audio.audio_engine import windows_engine_routes_devices
    from quill.ui.audio.output_routing import cached_output_devices
    from quill.ui.radio.mpv_radio_engine import (
        mpv_output_device_available,
        output_device_choices,
    )

    history = app._radio_history
    from quill.apps import radio_youtube_signin_prefs as yt_signin
    from quill.ui.radio import media_player_registration as media_player

    fallback_shared_check_minutes = int(getattr(history, "podcast_refresh_minutes", 0) or 0)
    initial_podcast_schedule_index = refresh_policy.interval_index(fallback_shared_check_minutes)
    podcast_schedule_choice_index = 7
    podcast_schedule_options = [label for _minutes, label in refresh_policy.INTERVAL_CHOICES]
    yt_check, yt_choice, yt_file = yt_signin.rows(app)
    timeshift_choice, acoustid_text = radio_preferences_listening.rows(app)
    close_action_index = _CLOSE_ACTION_VALUES.index(history.close_action)
    mpv_present = mpv_output_device_available()
    cached_devices = cached_output_devices()
    device_labels, device_names, device_index = output_device_choices(
        cached_devices or [], history.output_device
    )
    engine_labels, engine_values, engine_index = engine_choices(
        history.playback_engine,
        mpv_present=mpv_present,
        modern_windows_media=windows_engine_routes_devices(),
    )
    output_device_choice_index = 3
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
            _startup_checkbox(),
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
                "Share these choices with my other Quill apps",
                "Announce dialog transitions is kept the same in every Quill app that "
                "also shares. Nothing about keys, focus or your screen reader is shared.",
                history.share_family_prefs,
            ),
            PreferenceCheckbox(
                "&Recover failed streams from the station's website",
                "When a station's stream won't play, scan the station's own "
                "website for a working one -- on by default",
                history.recover_from_website,
            ),
            PreferenceCheckbox(
                "Share play counts with the RadioBrowser director&y",
                "When you play a station from RadioBrowser's community "
                "directory, tell it so -- that count is how the directory ranks "
                "stations, and a directory everyone takes from and nobody gives "
                "back to fills up with dead streams. It sends that station's id "
                "and nothing about you, and only ever for RadioBrowser's own "
                "stations. On by default; turn it off and nothing is sent",
                history.share_play_counts,
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
            _wake_checkbox(history.wake_for_scheduled_recording),
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
            PreferenceCheckbox(
                "Check subscribed &podcast feeds at launch",
                "Runs one check as the app starts, as well as on whatever "
                "cadence is set below. Off by default: a launch that spends "
                "four seconds on feeds is a launch you spend waiting, and it "
                "stays quiet when it finds nothing.",
                history.podcast_refresh_on_launch,
                group=_PODCASTS,
            ),
            PreferenceCheckbox(
                "Play a sound when a re&minder comes due",
                "The reminder earcon -- three rising bell tones, unlike any "
                "other sound in the app. On by default and separate from the "
                "global per-event sound list: somebody who has turned most "
                "earcons off has probably not meant to turn off the one sound "
                "they asked to be interrupted by. The reminder is still "
                "spoken either way.",
                history.reminder_sound,
                group=_REMINDERS,
            ),
            yt_check,
        ],
        choices=[
            PreferenceChoice(
                "&Main window shows:",
                "What the main window itself shows, between the now-playing "
                "line and the volume row -- your favorites, Browse, Search, "
                "Recordings or the Player. The menu bar, the status bar and "
                "the transport stay wherever you put yourself, which is the "
                "point: this replaces opening a second window on top of the "
                "one with the menus on it. Everything is still its own window "
                "on demand, and nothing opens itself at launch. Also on View "
                "> Main Window Shows",
                [label for _vid, label in main_view.MAIN_VIEWS],
                main_view.index_of(history.main_view),
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
                engine_labels,
                engine_index,
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
            PreferenceChoice(
                "Check subscribed podcast &feeds:",
                # The rule from section 3: what it does, then the misreading it
                # prevents. Every misread here has been about the second half.
                podcast_schedule_help(
                    fallback_shared_check_minutes, on_launch=history.podcast_refresh_on_launch
                ),
                podcast_schedule_options,
                initial_podcast_schedule_index,
                group=_PODCASTS,
            ),
            PreferenceChoice(
                "New reminders &start at:",
                "What the lead time opens at when you set a reminder. Every "
                "reminder still asks, and every reminder can differ -- this "
                "only decides what the control starts on, so the usual answer "
                "is one keystroke shorter.",
                [label for _seconds, label in reminders.LEAD_CHOICES],
                _lead_index(history.reminder_default_lead_seconds),
                group=_REMINDERS,
            ),
            PreferenceChoice(
                "Interrup&ted recordings at launch:",
                "A recording cut off because Quill Radio or the computer "
                "stopped is offered again the next time Radio starts, if its "
                "scheduled end has not passed. Ask each time shows the Resume "
                "Recording dialog; the other two answer it for you. Don't ask "
                "me again in that dialog sets this too.",
                [label for _value, label in RESUME_CHOICES],
                _resume_index(history.recording_resume_choice),
            ),
            yt_choice,
            timeshift_choice,
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
            acoustid_text,
        ],
        actions=[
            # Where Quill Radio's own sounds play (ui/app_sounds), one window
            # for the whole family.
            app_sounds.preference_action(app),
            # Which way the arrow keys move a slider, for the whole family.
            slider_keys.preference_action(app),
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
            # Release channels (plan 7.1): shown and changed only through the
            # shared Release Channel window, never by a selection. No access
            # key: this window has no letter left that is not already taken.
            PreferenceAction(
                f"Change Release Channel (now {_shown_channel()})...",
                "Stable, Beta or Dev: which versions Quill Radio offers you. Opens "
                "the Release Channel window, the same one as the Help menu's "
                "Release Channel. Nothing changes until you choose Switch.",
                lambda: _open_release_channel(app),
            ),
            yt_file,
            # Windows and your files (2026-10-04): the editors' group, for music.
            PreferenceAction(
                media_player.BUTTON_LABEL,
                media_player.BUTTON_HELP,
                lambda: media_player.make_media_player(app),
                group=media_player.GROUP_TITLE,
            ),
        ],
        announce_cb=app._announce,
    )

    # The device list and the shared cadence are slow to read, so they arrive
    # after the dialog is up (radio_preferences_load).
    data_load = PreferencesDataLoad(
        app,
        dialog,
        cached_devices=cached_devices,
        mpv_present=mpv_present,
        device_names=device_names,
        output_device_choice_index=output_device_choice_index,
        podcast_schedule_choice_index=podcast_schedule_choice_index,
        fallback_shared_check_minutes=fallback_shared_check_minutes,
    )
    data_load.schedule()

    result = dialog.show()
    if result is None:
        return
    checkbox_values, choice_indices, text_values = result
    (
        history.resume_on_launch,
        launch_at_startup,
        history.check_updates_on_startup,
        history.announce_dialog_transitions,
        history.share_family_prefs,
        history.recover_from_website,
        history.share_play_counts,
        history.alt_f4_to_tray,
        history.debug_mode,
        history.prevent_sleep,
        history.keep_awake_before_recording,
        history.wake_for_scheduled_recording,
        history.catalog_enabled,
        history.catalog_refresh_on_startup,
        history.winamp_playback_keys,
        history.podcast_refresh_on_launch,
        history.reminder_sound,
        youtube_signin_on,
    ) = checkbox_values
    from quill.platform.windows import radio_startup

    startup_said = ""
    if launch_at_startup != radio_startup.is_launch_at_startup_enabled():
        radio_startup.set_launch_at_startup(launch_at_startup)
        actual_startup = radio_startup.is_launch_at_startup_enabled()
        menu_bar = app.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(app._startup_menu_item_id), actual_startup)
        startup_said = (
            "Quill Radio will start with Windows."
            if actual_startup
            else (
                "Quill Radio will not start with Windows."
                if not launch_at_startup
                else "Windows did not allow the startup setting to change."
            )
        )
    youtube_said = yt_signin.apply(youtube_signin_on, choice_indices[10], app=app)
    listening_said = radio_preferences_listening.apply(app, choice_indices[11], text_values[2])
    # Apply verbose logging immediately (quill-radio #5) so it takes effect
    # this session, not just the next launch.
    from quill.core.radio.radio_logging import set_radio_debug

    set_radio_debug(history.debug_mode)
    from quill.ui.family_sharing import after_preferences

    after_preferences(app, "radio", history, {"share_family_prefs": history.share_family_prefs})
    chosen_view = main_view.from_index(choice_indices[0])
    if chosen_view != history.main_view:
        history.main_view = chosen_view
        # Applied now, not at the next launch: a setting that changes where you
        # land and then does not is worse than one never offered.
        host = getattr(app, "_main_view_host", None)
        if host is not None:
            from quill.ui.radio import main_view_menu

            host.show(chosen_view)
            main_view_menu.sync_checkmarks(app)
    # The old keys, kept in step so a downgrade -- or anything still reading
    # them -- sees an answer that matches the choice.
    history.startup_window = "" if chosen_view == main_view.FAVORITES else chosen_view
    history.open_browse_at_startup = history.startup_window == "browse"
    history.close_action = _CLOSE_ACTION_VALUES[choice_indices[1]]
    chosen_engine = engine_values[choice_indices[2]]
    if chosen_engine != history.playback_engine:
        history.playback_engine = chosen_engine
        # A playing station reconnects through the newly chosen backend.
        app._radio_controller.set_playback_engine(chosen_engine)
    chosen_device = device_names[choice_indices[output_device_choice_index]]
    radio_device_changed = chosen_device != history.output_device
    if radio_device_changed:
        history.output_device = chosen_device
        # Reconnects a playing station through the right engine; a
        # station already on air moves to the new device immediately.
        app._radio_controller.set_output_device(chosen_device)
    sound_said = ""
    if radio_device_changed:
        # Sounds that follow the radio follow it here too; one sound on the
        # new card says so (ui/app_sounds).
        if app_sounds.own_device_changed(app):
            sound_said = "App sounds go with it."
    chosen_sort = _FAVORITES_SORT_VALUES[choice_indices[4]]
    history.catalog_refresh_hours = catalog_interval_values[choice_indices[5]]
    history.subscription_episode_limit = episode_limit_values[choice_indices[6]]
    # Into the shared library, which is where both apps read it from since
    # 3.1.0. Radio's own field is kept in step so a downgrade still finds a
    # cadence rather than silently losing one.
    schedule_index = choice_indices[podcast_schedule_choice_index]
    cadence_changed = dialog.choice_was_changed(podcast_schedule_choice_index)
    if data_load.shared_check_minutes_loaded or cadence_changed:
        chosen_minutes = refresh_policy.interval_from_index(schedule_index)
        history.podcast_refresh_minutes = chosen_minutes
        radio_preferences_load.save_shared_check_minutes(chosen_minutes)
    history.reminder_default_lead_seconds = reminders.LEAD_CHOICES[
        min(max(0, choice_indices[8]), len(reminders.LEAD_CHOICES) - 1)
    ][0]
    history.recording_resume_choice = RESUME_CHOICES[choice_indices[9]][0]
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
    from quill.ui.radio.history_save import save_history_async

    save_history_async(app, history)
    # The feed check takes effect now rather than at the next launch, and says
    # what it will do -- a cadence you cannot hear you have changed is one you
    # have to restart the app to believe.
    from quill.apps import radio_podcast_refresh

    schedule_said = radio_podcast_refresh.reapply(app)
    # Apply the Prevent Sleep choice now: acquire the keep-awake lock if a
    # station is already playing, or release it if the user just turned it off.
    app._update_sleep_inhibitor()
    menu_bar = app.frame.GetMenuBar()
    if menu_bar is not None:
        menu_bar.Check(int(app._resume_menu_item_id), history.resume_on_launch)
    said = (startup_said, sound_said, schedule_said, youtube_said, listening_said)
    app._announce(" ".join(["Preferences saved.", *(part for part in said if part)]))
