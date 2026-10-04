"""The Quill Cast command-palette registrations, in one table.

Extracted from ``main_frame_podcast_session`` under GATE-11 (extract, never
rebaseline) when the shared transport joined the palette -- the same shape, and
for the same reason, as Radio's :mod:`quill.ui.radio.palette_commands`. The
table is pure wiring (command id, spoken title, handler) and reads better as one
page than as a tenth of the mixin.
"""

from __future__ import annotations

from typing import Any

__all__ = ["CAST_PALETTE_TITLES", "register_podcast_commands"]

#: QUILL Cast's names for the palette commands the shared podcasts mixin
#: registers (``main_frame_podcasts._register_podcasts_commands``), so the
#: palette says what Cast's menus say: Cast follows rather than subscribes,
#: calls local files Personal Audio, keeps the old Podcast Settings and Skip
#: Settings windows as Preferences sections, and has its places rather than
#: windows. ``None`` drops a command Cast does not have: Open Manager only led
#: back to the Podcasts place. QUILL keeps its own titles; Go To keeps the
#: Podcasts place under its own name.
CAST_PALETTE_TITLES: dict[str, str | None] = {
    "podcasts.open_manager": None,
    "podcasts.acb_media": "Podcasts: Follow ACB Media Podcasts",
    "podcasts.add_local": "Podcasts: Add Personal Audio...",
    "podcasts.settings": "Podcasts: Fetching Preferences...",
    "podcasts.skip_settings": "Podcasts: Playing Preferences...",
    "podcasts.open_queue": "Podcasts: Play Queue",
    "media.continue_listening": "Podcasts: Continue Listening",
}


def register_podcast_commands(host: Any) -> None:
    for command_id, title, handler in (
        ("podcasts.speed_up", "Podcasts: Speed Up", host.podcast_speed_up),
        ("podcasts.speed_down", "Podcasts: Speed Down", host.podcast_speed_down),
        ("podcasts.speed_reset", "Podcasts: Reset Speed to Normal", host.podcast_speed_reset),
        (
            "podcasts.go_to_position",
            "Podcasts: Go to Position...",
            host.podcast_go_to_position,
        ),
        (
            "podcasts.stop_after_episode",
            "Podcasts: Stop After This Episode",
            host.podcast_toggle_stop_after_episode,
        ),
        (
            "podcasts.mark_all_played",
            "Podcasts: Mark All Episodes as Played...",
            host.podcast_mark_all_played,
        ),
        (
            "podcasts.statistics",
            "Podcasts: Listening Statistics...",
            host.open_podcast_statistics,
        ),
        ("podcasts.downloads", "Podcasts: Downloads...", host.open_podcast_downloads),
        ("podcasts.free_space", "Podcasts: Free Up Space", host.podcast_free_up_space),
        (
            "podcasts.quick_actions",
            "Podcasts: Quick Actions...",
            host.open_podcast_quick_actions,
        ),
        ("podcasts.export_data", "Podcasts: Export My Data...", host.podcast_export_data),
        (
            "podcasts.delete_all_data",
            "Podcasts: Clear All Podcast Data from This Computer...",
            host.podcast_delete_all_data,
        ),
        (
            "podcasts.run_maintenance",
            "Podcasts: Run Housekeeping Now",
            host.podcast_run_maintenance,
        ),
        (
            "podcasts.tutorials",
            "Podcasts: Tutorials...",
            host.open_cast_tutorials,
        ),
        # Feed Check (R2).
        ("podcasts.feed_check", "Podcasts: Feed Check...", host.open_cast_feed_check),
        # Refresh Episode Audio (R3): also on the episode's own menu.
        (
            "podcasts.refresh_episode_audio",
            "Podcasts: Refresh Episode Audio...",
            lambda: _refresh_audio(host),
        ),
        # The three verbs Earshot publishes to Siri (R5). No menu row: they are
        # one-press keys whose whole point is not opening a menu, and the palette
        # is where somebody looks for a command by name.
        (
            "podcasts.play_unheard",
            "Podcasts: Play an Unheard Episode (newest)",
            host.podcast_play_unheard,
        ),
        (
            "podcasts.play_unheard_oldest",
            "Podcasts: Play an Unheard Episode (oldest)",
            host.podcast_play_unheard_oldest,
        ),
        ("podcasts.shuffle_queue", "Podcasts: Play Queue Shuffled", host.podcast_shuffle_queue),
        (
            "podcasts.clear_queue",
            "Podcasts: Clear Entire Queue...",
            host.podcast_clear_entire_queue,
        ),
        # The queue run shipped with a submenu and no palette entries, which is a
        # command only somebody who already knows it can find.
        ("podcasts.next_in_queue", "Podcasts: Next in Queue", host.podcast_next_in_queue),
        (
            "podcasts.previous_in_queue",
            "Podcasts: Previous in Queue",
            host.podcast_previous_in_queue,
        ),
        (
            "podcasts.mark_played_and_next",
            "Podcasts: Mark as Played and Next",
            host.podcast_mark_played_and_next,
        ),
        # The Inbox and Personal Audio places, and the Inbox folder scope (R4).
        ("podcasts.inbox", "Podcasts: Inbox", host.open_cast_inbox),
        ("podcasts.personal_audio", "Podcasts: Personal Audio", host.open_cast_personal_audio),
        (
            "podcasts.inbox_folder",
            "Podcasts: Inbox Folder...",
            host.choose_inbox_folder_scope,
        ),
    ):
        host.commands.try_register(
            command_id,
            title,
            handler,
            host._binding_for(command_id),
            feature_id="core.podcasts",
        )

    # ...then the shared transport table, filling only the gaps this app left:
    # the palette could change a setting and could not pause what was playing
    # (2026-08-18). Last on purpose -- register_commands skips any verb this
    # app already listed, so it has to see the table above first.
    from quill.ui.radio import transport_keys

    transport_keys.register_commands(host, prefix="podcasts")


def _refresh_audio(host: Any) -> None:
    from quill.ui.podcasts.refresh_audio_command import refresh_episode_audio

    refresh_episode_audio(host)
