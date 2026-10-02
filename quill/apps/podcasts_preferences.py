"""QUILL Cast's Preferences window: what it holds, and how it is saved.

Extracted from ``quill/apps/podcasts.py`` under GATE-11 (extract, never
rebaseline) on 2026-10-01, when the window gained a row: that module sat at its
budget, and Preferences is one subject -- build the rows, read them back, save,
re-apply what changed -- that touches nothing else in the frame.

**Where to land on launch** is the new row (Jeff, 2026-09-30: "make launch place
configurable in settings ... provide question 1 as the default but allow the
user to change it in settings"). The field, ``PodcastSettings.default_launch_view``,
existed for a release with nothing exposing it; ``core/podcasts/launch_place.py``
is its vocabulary. The default is the automatic rule -- what is new -- and every
other choice always lands on that place, which is a different promise and the
one somebody makes on purpose.

The plan also named "Switch to Now Playing when playback starts". It is not
here, deliberately: there is no Now Playing surface to switch to yet, and a
switch for a feature that does not exist is a setting that lies. It lands with
Now Playing (qc.md section 5).
"""

from __future__ import annotations

from quill.apps.podcasts_close import (
    _CLOSE_ACTION_LABELS,
    _close_action_index,
    _close_action_value,
)

__all__ = ["CastPreferencesMixin"]


class CastPreferencesMixin:
    """Preferences... (Ctrl+,). On ``PodcastsAppFrame``."""

    #: Preference group names (list.md 8.1). Short, because a static box
    #: label is read aloud every time focus enters the group.
    _PODCASTS = "Podcasts"

    def _open_preferences(self) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts import history as podcast_history
        from quill.core.podcasts import launch_place, refresh_policy
        from quill.ui.app_preferences_dialog import (
            PreferenceAction,
            PreferenceCheckbox,
            PreferenceChoice,
            PreferencesDialog,
        )
        from quill.ui.data_folder_dialog import open_data_folder_dialog

        history = self._podcast_history
        library_settings = self._podcast_library.settings
        title = self._preferences_app_title()
        dialog = PreferencesDialog(
            self.frame,
            app_title=title,
            actions=[
                PreferenceAction(
                    "&Data Folder...",
                    "Where every Quill app stores settings, favorites, and "
                    "subscriptions. Choose a folder a service like Dropbox or "
                    "OneDrive keeps in sync to carry them between computers.",
                    lambda: open_data_folder_dialog(self, app_title=title),
                ),
            ],
            checkboxes=[
                PreferenceCheckbox(
                    "Resume Last Episode on &Launch",
                    "Resume Last Episode on Launch",
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
                    "Alt+F&4 minimizes to the system tray",
                    "When on, Alt+F4 sends QUILL Cast to the system tray, still "
                    "playing, instead of closing the window",
                    history.alt_f4_to_tray,
                ),
                PreferenceCheckbox(
                    "&Winamp playback keys (Z X C V B, arrows to seek)",
                    "The classic Winamp letter keys in the library and episode "
                    "lists. Turn off to use those letters for list typeahead "
                    "instead. The same keys as Quill Radio's recordings player.",
                    history.winamp_playback_keys,
                ),
                PreferenceCheckbox(
                    "AI help (sends the show notes you ask about to QUILL's servers) (&J)",
                    "Help > AI Features: summarize, explain or ask about the show notes "
                    "of the episode you are on, and describe a picture. The notes you "
                    "ask about are sent over the internet to QUILL and on to OpenAI, or "
                    "straight to OpenAI or Google on your own key or plan. Off until you "
                    "turn it on, and the privacy agreement is still asked for before "
                    "anything is sent.",
                    history.ai_help_enabled,
                    group=self._PODCASTS,
                ),
                PreferenceCheckbox(
                    "Switch to Now Playing when playback &starts",
                    "Bring the Now Playing window to the front whenever an episode "
                    "starts. Off by default: Now Playing is always one keystroke "
                    "away on Ctrl+Alt+2, and a window that takes focus on every Play is "
                    "one you turn off.",
                    history.switch_to_now_playing,
                    group=self._PODCASTS,
                ),
                PreferenceCheckbox(
                    "Check the feeds you follow on a &timer",
                    "Look for new episodes without being asked. Off by default. "
                    "A check reads episode lists only: it starts no downloads by "
                    "itself, skips shows you have paused, and never changes what "
                    "you are playing.",
                    history.podcast_check_enabled,
                    group=self._PODCASTS,
                ),
            ],
            choices=[
                PreferenceChoice(
                    "When c&losing the window:",
                    # Radio has carried these three for as long as it has had a
                    # tray icon. Cast had only the Alt+F4 checkbox above, so the
                    # titlebar X ended playback with no way to say otherwise
                    # (list.md 5.4). Exit stays the shipped answer: an upgrade
                    # that starts asking a question is an upgrade that changed
                    # somebody's Alt+F4 under them.
                    "What the titlebar X, Alt+F4 and Exit do. Ask every time "
                    "offers Exit or Minimize to Tray, and can remember your "
                    "answer. Minimize to Tray keeps playing and downloading "
                    "with the window out of the way; the tray icon brings it "
                    "back. This does not change the Alt+F4 setting above, which "
                    "acts first when it is on.",
                    list(_CLOSE_ACTION_LABELS),
                    _close_action_index(history.close_action),
                ),
                PreferenceChoice(
                    "Check the &feeds you follow:",
                    # The rule from section 3: what it does, then the misreading
                    # it prevents. Every misread here has been the second half.
                    refresh_policy.describe_schedule(
                        history.podcast_check_interval_minutes
                        if history.podcast_check_enabled
                        else 0
                    )
                    + " Quill Radio has its own separate setting; whichever app "
                    "checks first, the other skips that round rather than asking "
                    "the same feeds twice.",
                    [label for _minutes, label in refresh_policy.INTERVAL_CHOICES],
                    refresh_policy.interval_index(history.podcast_check_interval_minutes),
                    group=self._PODCASTS,
                ),
                PreferenceChoice(
                    "Where to land on la&unch:",
                    "Which place in the library has focus when QUILL Cast opens. "
                    "What is new lands on the Inbox when anything is waiting, "
                    "else Continue Listening when anything is half-heard, else the "
                    "top of your podcasts; every other choice always lands on that "
                    "place, even when it is empty.",
                    [label for _value, label in launch_place.CHOICES],
                    launch_place.index_for(library_settings.default_launch_view),
                    group=self._PODCASTS,
                ),
            ],
            announce_cb=self._announce,
        )
        result = dialog.show()
        if result is None:
            return
        checkbox_values, choice_indices, _text_values = result
        (
            history.resume_on_launch,
            history.check_updates_on_startup,
            history.announce_dialog_transitions,
            history.alt_f4_to_tray,
            history.winamp_playback_keys,
            history.ai_help_enabled,
            history.switch_to_now_playing,
            history.podcast_check_enabled,
        ) = checkbox_values
        history.close_action = _close_action_value(choice_indices[0])
        history.podcast_check_interval_minutes = refresh_policy.interval_from_index(
            choice_indices[1]
        )
        podcast_history.save_history(app_data_dir(), history)
        launch_view = launch_place.view_at(choice_indices[2])
        if launch_view != (library_settings.default_launch_view or ""):
            # The field lives on the library's settings, not the history, so
            # it is saved with the library -- and only when it changed, because
            # a library save is the one write here that is not small.
            library_settings.default_launch_view = launch_view
            self._save_podcast_library()
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._resume_menu_item_id), history.resume_on_launch)
        # Re-applied rather than left until the next launch: a cadence you just
        # chose should be the cadence that is running.
        monitor = getattr(self, "_podcast_check_monitor", None)
        said = ""
        if monitor is not None:
            monitor.apply()
            said = str(monitor.describe())
        self._announce(f"Preferences saved. {said}".strip())

    def _toggle_resume_on_launch(self) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts import history as podcast_history

        history = self._podcast_history
        history.resume_on_launch = not history.resume_on_launch
        podcast_history.save_history(app_data_dir(), history)
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            menu_bar.Check(int(self._resume_menu_item_id), history.resume_on_launch)
        self._announce(
            "QUILL Cast will pick up where you left off at launch."
            if history.resume_on_launch
            else "Resume on launch turned off."
        )

    def _preferences_app_title(self) -> str:
        from quill.apps.podcasts_menu import APP_TITLE

        return APP_TITLE
