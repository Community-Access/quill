"""The Quill Cast command-palette registrations, in one table.

Extracted from ``main_frame_podcast_session`` under GATE-11 (extract, never
rebaseline) when the shared transport joined the palette -- the same shape, and
for the same reason, as Radio's :mod:`quill.ui.radio.palette_commands`. The
table is pure wiring (command id, spoken title, handler) and reads better as one
page than as a tenth of the mixin.
"""

from __future__ import annotations

from typing import Any


def register_podcast_commands(host: Any) -> None:
    for command_id, title, handler in (
        ("podcasts.speed_up", "Podcasts: Speed Up", host.podcast_speed_up),
        ("podcasts.speed_down", "Podcasts: Speed Down", host.podcast_speed_down),
        ("podcasts.speed_reset", "Podcasts: Reset Speed to Normal", host.podcast_speed_reset),
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
            "Podcasts: Delete All Podcast Data...",
            host.podcast_delete_all_data,
        ),
        (
            "podcasts.run_maintenance",
            "Podcasts: Run Housekeeping Now",
            host.podcast_run_maintenance,
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
