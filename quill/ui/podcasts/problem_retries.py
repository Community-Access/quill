"""What QUILL Cast knows how to try again, from Recent Problems (11.5).

Registered per problem *kind*, not stored on the row (see
:mod:`quill.ui.problems_dialog`), so a failure recorded last Tuesday is still
retryable by today's handler. Cast claims two kinds:

* **feed** -- the target is the show id, so retrying is the same manual
  Refresh Feed the context menu offers, which is deliberately the path that
  ignores pause (0.7).
* **download** -- the target is ``<show id>|<episode guid>``, which is exactly
  what the download queue needs to be handed the episode again.
"""

from __future__ import annotations

from typing import Any

from quill.core import problem_log


def register(host: Any) -> None:
    """Teach Recent Problems what QUILL Cast can retry."""
    from quill.ui import problems_dialog

    def _retry_feed(problem: problem_log.Problem) -> str:
        show = host._podcast_library.find_show(problem.target)
        if show is None:
            return "That podcast is no longer in your library."
        host.refresh_podcast_feed(show.id)
        return f"Refreshing {show.title}..."

    def _retry_download(problem: problem_log.Problem) -> str:
        show_id, _sep, guid = problem.target.partition(problem_log.TARGET_SEP)
        show = host._podcast_library.find_show(show_id)
        episode = show.find_episode(guid) if show is not None else None
        if show is None or episode is None:
            return "That episode is no longer in your library."
        from quill.ui.podcasts.show_actions import enqueue_episode_download

        enqueue_episode_download(
            host._podcast_download_queue,
            host._podcast_download_root(),
            show,
            episode,
        )
        return f"Queued {episode.title or 'that episode'} again."

    problems_dialog.register_retry(problem_log.KIND_FEED, _retry_feed)
    problems_dialog.register_retry(problem_log.KIND_DOWNLOAD, _retry_download)
