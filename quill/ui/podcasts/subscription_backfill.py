"""Mark requested back-catalogue episodes for download when following a show."""

from __future__ import annotations

from typing import Any


def _apply_backfill(library: Any, show: Any) -> int:
    """Collect this podcast's back catalogue once, if it was asked for (7.2).

    Separate from the automatic download count, which only ever looks forward:
    "fetch the newest 3 from now on" and "when I subscribe, also get the last
    ten" are different questions, and until now only Always Sync -- meaning
    *everything* -- answered the second.

    A one-off, at the one moment it can be: subscribing. It marks episodes for
    download and never plays, queues or deletes anything, and a podcast whose
    setting says "nothing" (the default, and every existing subscription) does
    exactly what it did before.
    """
    try:
        from quill.core.podcasts.show_policy import backfill_episodes

        wanted = backfill_episodes(library, show, show.episodes)
    except Exception:  # noqa: BLE001 - a backfill must never break subscribing
        return 0
    for episode in wanted:
        if not episode.downloaded_path and episode.mode_override != "stream":
            episode.mode_override = "download"
    return len(wanted)
