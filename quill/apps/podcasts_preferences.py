"""QUILL Cast's Preferences: the app's own rows, and the shared defaults (qc.md 13).

The window is :mod:`quill.ui.podcasts.preferences_window`; this mixin is the
frame's side of it -- the table of app rows (the ``PodcastHistory`` record,
one row each, with the sentence a listener hears on F1), how a saved change is
written back, and which section a menu row opens on. Podcast Settings and
Skip Settings are absorbed here: ``_podcast_open_settings`` and
``open_podcast_skip_settings`` open this window on the right section.

**Where to land on launch** (qc.md 4.8) is a library setting rather than an
app one -- it names a place in the library, and it travels with a synced
data folder -- so it is written to ``library.settings.default_launch_view``
rather than to the history record, through the catalogue's own row.
"""

from __future__ import annotations

from typing import Any

from quill.apps.podcasts_close import _CLOSE_ACTION_LABELS, _CLOSE_ACTION_VALUES
from quill.core.action_feedback import ACTION_FEEDBACK_LABELS
from quill.core.podcasts import notices
from quill.core.podcasts.refresh_policy import INTERVAL_CHOICES
from quill.core.podcasts.watched_folders import ORIGINALS, TELLS
from quill.ui.podcasts.preferences_window import AppRow

__all__ = ["CastPreferencesMixin", "app_rows"]


def _shown_channel() -> str:
    from quill.core.updater.channels import shown_channel, state_for

    return shown_channel(state_for("cast"))


def app_rows(host: Any) -> list[AppRow]:
    """The history-backed rows, by section."""
    from quill.core.podcasts.notes_export import FORMAT_LABELS

    rows = [
        AppRow(
            "resume_on_launch",
            "Resume the last episode on &launch",
            "Starts playing where you stopped as soon as Cast opens. Off, Cast "
            "opens quiet and the Now Playing line says what you stopped on; "
            "nothing is downloaded either way.",
            "opens",
        ),
        AppRow(
            "check_updates_on_startup",
            "&Check for updates on launch",
            "Compares your version with the newest release once a day, quietly. "
            "Nothing is installed without you; Help > Check for Updates asks.",
            "opens",
        ),
        AppRow(
            "release_channel",
            f"Change release channel (now {_shown_channel()})...",
            "Stable, Beta or Dev: which versions Cast offers you. Opens the "
            "Release Channel window, the same one as the Help menu's Release "
            "Channel. Nothing changes until you choose Switch there.",
            "opens",
            kind="action",
            action=lambda: host.open_release_channel(),
        ),
        AppRow(
            "winamp_playback_keys",
            "&Winamp playback keys (Z X C V B, arrows to seek)",
            "The classic Winamp letter keys in the lists. Off, those letters go "
            "back to list typeahead; the Episode menu's keys are unchanged.",
            "playing",
        ),
        AppRow(
            "switch_to_now_playing",
            "Switch to Now Playing when playback &starts",
            "Brings the Now Playing window to the front whenever an episode "
            "starts. Off by default: Now Playing is always Ctrl+Alt+2 away, and "
            "a window that takes focus on every Play is one you turn off.",
            "playing",
        ),
        AppRow(
            "notes_copy_format",
            "Copy show notes &as:",
            "What Copy Notes puts on the clipboard: plain text, plain text with "
            "the links written out, Markdown, or formatted text. It does not "
            "change how the notes read on screen.",
            "playing",
            kind="choice",
            options=tuple(FORMAT_LABELS.items()),
        ),
        AppRow(
            "podcast_check_enabled",
            "Look for new episodes on a &schedule",
            "The automatic check, on the schedules under Fetching. Off, feeds are "
            "checked only when you press Refresh; a paused podcast is never "
            "checked either way, and nothing is downloaded by the check itself.",
            "fetching",
        ),
        AppRow(
            "podcast_check_interval_minutes",
            "Look at the schedules &every:",
            "How often Cast wakes to see which podcasts are due under their own "
            "schedules. It is a heartbeat, not a schedule: a podcast is only "
            "checked when its own schedule says so, and Quill Radio never asks a "
            "feed again inside the same round.",
            "fetching",
            kind="choice",
            options=tuple((minutes, label) for minutes, label in INTERVAL_CHOICES if minutes),
        ),
        AppRow(
            "podcast_check_audible_tick",
            "A short sound each time a check &runs",
            "So an ambient thing can be heard to be alive. Off by default: a "
            "sound four times an hour is a sound, and it never says what the "
            "check found.",
            "fetching",
        ),
        AppRow(
            "podcast_check_interrupt_speech",
            "Let what a check found &interrupt speech",
            "New episodes cut across whatever is being spoken. Off by default: "
            "new episodes are news, not an emergency, and Quiet Hours still hold "
            "them back.",
            "fetching",
        ),
        AppRow(
            "launch_digest",
            "One sentence on launch about what &arrived while Cast was closed",
            '"Since yesterday: 4 new episodes from 3 podcasts." Never more than '
            "one sentence, never during Quiet Hours, and never when nothing arrived.",
            "telling",
        ),
        AppRow(
            "toasts_enabled",
            "Desktop &toasts for new episodes and finished downloads",
            "The louder half of a notification. Off, the Notifications list still "
            "keeps the record and the status bar still counts it.",
            "telling",
        ),
        AppRow(
            "wf_default_original",
            "A new watched folder's &original files:",
            "What a newly added watched folder does with the files that land in it. "
            "Each folder can still be set its own way in Watched Folders; folders you "
            "already watch are not changed.",
            "data",
            kind="choice",
            options=ORIGINALS,
        ),
        AppRow(
            "wf_default_tell",
            "When files arrive in a new watched folder, tell me:",
            "How a newly added watched folder tells you about arrivals. Every arrival "
            "is in Notifications whichever you choose. Folders you already watch are not "
            "changed.",
            "data",
            kind="choice",
            options=TELLS,
        ),
        AppRow(
            "wf_default_min_seconds",
            "A new watched folder ignores files shorter than:",
            "So a recorder's accidental two-second file does not become an episode. "
            "Folders you already watch are not changed.",
            "data",
            kind="choice",
            options=(
                (0, "Nothing; take every file"),
                (10, "10 seconds"),
                (30, "30 seconds"),
                (60, "1 minute"),
                (300, "5 minutes"),
            ),
        ),
        AppRow(
            "wf_default_subfolders",
            "A new watched folder includes its subfolders",
            "Also watch every folder inside a newly added one. Folders you already watch "
            "are not changed.",
            "data",
        ),
        AppRow(
            "inbox_personal_audio",
            "New files in watched folders also wait in the Inbox",
            "For triaging everything in one place. Off, they arrive in Personal Audio only.",
            "inbox",
        ),
        AppRow(
            "action_feedback",
            "When a one-key action &works:",
            "What you get when adding to the queue, removing from a place or marking "
            "as played works: a short sound, the words, both, or nothing. A failure "
            "is always said in words.",
            "telling",
            kind="choice",
            options=tuple((mode.value, label) for mode, label in ACTION_FEEDBACK_LABELS),
        ),
        AppRow(
            "announce_up_next",
            "Say what is &up next before an episode ends",
            '"Next: Episode 412 from Accidental Tech Podcast", about ten seconds '
            "before the end, so a new voice never arrives without warning. Never "
            "during Quiet Hours, and never when nothing will follow.",
            "telling",
        ),
        AppRow(
            "announce_dialog_transitions",
            "Announce &dialog transitions (more spoken detail)",
            "Says a window's name as it opens and closes. Off by default to "
            "reduce alert noise; the screen reader still reads the title.",
            "telling",
        ),
        AppRow(
            "share_family_prefs",
            "Share these choices with my other Quill apps",
            "Announce dialog transitions, and in QUILL Cast what a one-key action "
            "answers with, are kept the same in every Quill app that also shares. "
            "Nothing about keys, focus or your screen reader is ever shared, and an "
            "app that has not turned this on is not touched.",
            "window",
        ),
        AppRow(
            "close_action",
            "When c&losing the window:",
            "What the titlebar X, Alt+F4 and Exit do. Ask every time offers Exit "
            "or Minimize to Tray and can remember your answer. Minimize to Tray "
            "keeps playing with the window out of the way. It does not change the "
            "Alt+F4 setting, which acts first when it is on.",
            "window",
            kind="choice",
            options=tuple(zip(_CLOSE_ACTION_VALUES, _CLOSE_ACTION_LABELS, strict=True)),
        ),
        AppRow(
            "alt_f4_to_tray",
            "Alt+F&4 minimizes to the system tray",
            "Alt+F4 sends Cast to the tray, still playing, instead of closing the "
            "window. Off, Alt+F4 follows the closing choice above.",
            "window",
        ),
        AppRow(
            "ai_help_enabled",
            "AI help (sends the show notes you ask about to QUILL's servers) (&J)",
            "Help > AI Features: summarize, explain or ask about the show notes "
            "of the episode you are on, and describe a picture. The notes you ask "
            "about are sent over the internet to QUILL and on to OpenAI, or "
            "straight to OpenAI or Google on your own key or plan. Off until you "
            "turn it on, and the privacy agreement is still asked for before "
            "anything is sent.",
            "window",
        ),
        AppRow(
            "data_folder",
            "Data &Folder...",
            "Where every Quill app stores settings, favorites and podcasts. "
            "Choose a folder a service like Dropbox or OneDrive keeps in sync to "
            "carry them between computers. Nothing is moved until you say so.",
            "data",
            kind="action",
            action=lambda: host.open_cast_data_folder(),
        ),
    ]
    for kind in notices.KINDS:
        rows.append(
            AppRow(
                notices.SWITCH_FIELDS[kind],
                f"Tell me about: {notices.KIND_LABELS[kind].lower()} (&{_letter(kind)})",
                f"Writes a notification when {notices.KIND_LABELS[kind].lower()} happens. "
                "Off, nothing is recorded for it; the episodes still arrive, download "
                "and queue exactly as they would.",
                "telling",
            )
        )
    return rows


def _letter(kind: str) -> str:
    return {
        "new_episode": "N",
        "feed_failed": "F",
        "gone_quiet": "Q",
        "download_finished": "O",
        "sleep_last_minute": "M",
        "import_finished": "P",
    }[kind]


class CastPreferencesMixin:
    """Opens Preferences and writes a saved result back."""

    def _open_preferences(self, *, section: str = "") -> None:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts import history as podcast_history
        from quill.core.podcasts import schedule_policy, settings_catalog
        from quill.core.podcasts.settings_resolver import set_value
        from quill.core.podcasts.settings_types import LEVEL_GLOBAL
        from quill.ui.podcasts.preferences_window import CastPreferencesWindow
        from quill.ui.podcasts.schedule_dialog import change_schedule

        history = self._podcast_history  # type: ignore[attr-defined]
        library = self._podcast_library  # type: ignore[attr-defined]
        window = CastPreferencesWindow(
            self.frame,  # type: ignore[attr-defined]
            library=library,
            history=history,
            app_rows=app_rows(self),
            announce=self._announce,  # type: ignore[attr-defined]
            on_change_schedule=lambda: change_schedule(self, None),
            summary=lambda: schedule_policy.summary(library),
            open_section=section,
        )
        result = window.show()
        if result is None:
            return
        app_changes, default_changes = result
        for key, value in app_changes.items():
            setattr(history, key, value)
        if app_changes:
            podcast_history.save_history(app_data_dir(), history)
            from quill.ui.family_sharing import after_preferences

            after_preferences(self, "cast", history, app_changes)
        written = 0
        for setting_id, value in default_changes.items():
            definition = settings_catalog.definition(setting_id)
            if definition is not None and set_value(library, definition, value, level=LEVEL_GLOBAL):
                written += 1
        if written:
            self._save_podcast_library()  # type: ignore[attr-defined]
        menu_bar = self.frame.GetMenuBar()  # type: ignore[attr-defined]
        if menu_bar is not None and hasattr(self, "_resume_menu_item_id"):
            menu_bar.Check(int(self._resume_menu_item_id), history.resume_on_launch)  # type: ignore[attr-defined]
        monitor = getattr(self, "_podcast_check_monitor", None)
        said = ""
        if monitor is not None and ("podcast_check_enabled" in app_changes or default_changes):
            monitor.apply()
            said = str(monitor.describe())
        count = len(app_changes) + written
        if count:
            self._announce(
                f"Preferences saved: {count} change{'' if count == 1 else 's'}. {said}".strip()
            )  # type: ignore[attr-defined]
        else:
            self._announce("Preferences closed; nothing changed.")  # type: ignore[attr-defined]
        self._refresh_place(keep=True)  # type: ignore[attr-defined]

    def _check_cast_updates(self, *, silent: bool = False) -> None:
        """Help > Check for Updates..., and the quiet once-a-day check at launch.

        Compares the version the *installer* recorded, not the runtime's code
        constant: a sibling's newer runtime must never make this copy look up
        to date (release channels, Phase 0). The channel decides what may be
        offered (``app_shell.check_for_app_updates``).
        """
        from quill.ui.updates.shell import installed_app_version

        self.check_for_app_updates(
            repo_slug="Community-Access/quill",
            current_version=installed_app_version("cast"),
            app_key="cast",
            silent_no_update=silent,
        )

    def open_release_channel(self) -> None:
        """Preferences > Change release channel... (also Help > Release Channel...)."""
        from quill.ui.updates.shell import open_for_shell

        open_for_shell(self, "cast")

    def open_cast_data_folder(self) -> None:
        from quill.ui.data_folder_dialog import open_data_folder_dialog

        open_data_folder_dialog(self, app_title=self._preferences_app_title())  # type: ignore[attr-defined]

    # -- the two absorbed windows ------------------------------------------------- #

    def _podcast_open_settings(self) -> None:
        """Podcast Settings is Preferences > Fetching and the sections beside it."""
        self._open_preferences(section="fetching")

    def open_podcast_skip_settings(self) -> None:
        """Skip Settings is Preferences > Playing; per podcast, Settings for This Podcast."""
        self._open_preferences(section="playing")

    def _toggle_resume_on_launch(self) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts import history as podcast_history

        history = self._podcast_history  # type: ignore[attr-defined]
        history.resume_on_launch = not history.resume_on_launch
        podcast_history.save_history(app_data_dir(), history)
        menu_bar = self.frame.GetMenuBar()  # type: ignore[attr-defined]
        if menu_bar is not None and hasattr(self, "_resume_menu_item_id"):
            menu_bar.Check(int(self._resume_menu_item_id), history.resume_on_launch)  # type: ignore[attr-defined]
        self._announce(  # type: ignore[attr-defined]
            "QUILL Cast will pick up where you left off at launch."
            if history.resume_on_launch
            else "Resume on launch turned off."
        )

    def _preferences_app_title(self) -> str:
        from quill.apps.podcasts_menu import APP_TITLE

        return APP_TITLE
