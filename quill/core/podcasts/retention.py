"""Retention policy: what happens to a downloaded episode's file over time.

Applied after every successful download (``keep_last_n`` pruning) and when
an episode finishes playing (``delete_after_play``) -- see
``docs/planning/podcasts.md`` §4. Pure/wx-free so the policy logic is
testable without a real download or a real file.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow


def _delete_file(path_str: str) -> None:
    if not path_str:
        return
    try:
        Path(path_str).unlink(missing_ok=True)
    except OSError:
        pass


def apply_keep_last_n(show: PodcastShow, settings: PodcastSettings) -> list[PodcastEpisode]:
    """For ``retention == "keep_last_n"``, delete the oldest downloaded
    episodes beyond ``retention_count``; returns the episodes pruned."""
    if settings.retention != "keep_last_n":
        return []
    downloaded = [e for e in show.episodes if e.downloaded_path]
    if len(downloaded) <= settings.retention_count:
        return []
    downloaded.sort(key=lambda e: e.published, reverse=True)
    to_prune = downloaded[settings.retention_count :]
    for episode in to_prune:
        _delete_file(episode.downloaded_path)
        episode.downloaded_path = ""
    return to_prune


def apply_delete_after_play(episode: PodcastEpisode, settings: PodcastSettings) -> bool:
    """For ``retention == "delete_after_play"``, remove *episode*'s local
    file now that it has played; returns True if a file was removed."""
    if settings.retention != "delete_after_play" or not episode.downloaded_path:
        return False
    _delete_file(episode.downloaded_path)
    episode.downloaded_path = ""
    return True


__all__ = ["apply_delete_after_play", "apply_keep_last_n"]
