"""Refresh Episode Audio, on an episode's menu (Earshot parity R3).

Re-reads the podcast's feed off the UI thread, asks once with the one cost
named (the download), then forgets the old file, points the episode at the
address the feed gives now, and downloads it again. Position, played mark,
note and speed are untouched; :mod:`quill.core.podcasts.refresh_audio` decides
and this carries it out.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.podcasts import refresh_audio

__all__ = ["refresh_episode_audio"]

TITLE = "Refresh Episode Audio"


def refresh_episode_audio(host: Any) -> None:
    """The verb: on the selected episode."""
    pair = host._selected_episode()
    if pair is None:
        host._announce("Choose an episode first.")
        return
    show, episode = pair
    first = refresh_audio.plan_for(show, episode, "x")
    if not first.ok and (getattr(show, "is_local", False) or not show.feed_url):
        host._announce(first.message)
        return
    from quill.core.podcasts import feed_auth, feed_reader

    username, password = feed_auth.auth_for_url(show, show.feed_url)
    guid = str(episode.guid)
    host._announce(f"Checking the feed for {episode.title}.")

    def _fetch(**_kwargs: object) -> str:
        info = feed_reader.fetch_and_parse_feed(
            show.feed_url, username=username, password=password, safe_mode=host._safe_mode
        )
        match = next((item for item in info.episodes if str(item.guid) == guid), None)
        return str(getattr(match, "audio_url", "") or "") if match is not None else ""

    def _on_success(_op: str, fresh_url: str) -> None:
        finish(host, show, episode, fresh_url)

    def _on_failure(_op: str, _error: BaseException) -> None:
        from quill.ui.podcasts.failure_report import report_failure

        report_failure(
            host,
            f"Could not read the feed for {show.title}, so {episode.title} was left as it was.",
            subject=show.title,
            kind="feed",
            target=show.feed_url,
            background=False,
            quiet=False,
        )

    host._task_manager.submit(
        "podcast-refresh-audio", _fetch, on_success=_on_success, on_failure=_on_failure
    )


def finish(host: Any, show: Any, episode: Any, fresh_url: str, *, ask: bool = True) -> bool:
    """Ask, then replace the file. Returns whether a new download was started."""
    plan = refresh_audio.plan_for(show, episode, fresh_url)
    if not plan.ok:
        host._announce(plan.message)
        return False
    if ask:
        import wx

        from quill.ui.dialog_contract import show_message_box

        answer = show_message_box(
            refresh_audio.confirm_message(plan),
            TITLE,
            wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION,
            host.frame,
            announce=host._announce,
        )
        if answer != wx.YES:
            host._announce("Left as it was.")
            return False
    old = refresh_audio.removable(plan)
    if old is not None:
        try:
            Path(old).unlink()
        except OSError:
            pass  # a file that will not go is replaced on disk by the new download
    refresh_audio.apply_plan(episode, plan)
    host._save_podcast_library()
    from quill.ui.podcasts.show_actions import enqueue_episode_download

    enqueue_episode_download(
        host._podcast_download_queue,
        host._podcast_download_root(),
        show,
        episode,
        item_id=f"{show.id}:{episode.guid}",
        library=host._podcast_library,
    )
    where = "from its new address" if plan.moved else "again"
    host._announce(f"Downloading {episode.title} {where}.")
    return True
