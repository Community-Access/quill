"""Fetch a feed, show what it is, and subscribe only if asked.

The half of "preview before subscribing" that touches the network. Kept out of
``add_podcast_dialog`` because that dialog is close to its ceiling and because
this is a genuinely separate job: fetching a feed off the UI thread, and turning
the result into a window.

**The fetch runs on the task manager**, like every other fetch in Cast: a feed
can take seconds, and a dialog that freezes while it waits is a dialog a screen
reader user cannot tell is still alive.

Also holds the Podcast Index credential read, for the same reason: the dialog
should not know what a credential store is.
"""

from __future__ import annotations

from typing import Any

__all__ = ["podcast_index_credentials", "preview_search_result"]


def podcast_index_credentials() -> tuple[str, str]:
    """The Podcast Index key and secret to search with, or two empty strings.

    The listener's own pair from the platform credential store if they set one
    -- never from a settings file; they are secrets, and they are treated the
    way every other secret in QUILL is -- and the application credential the
    build carries otherwise. Resolution lives in the client
    (:func:`quill.core.podcasts.podcast_index.credentials`) so every surface
    asks the same question and gets the same answer.

    Two empty strings is not an error: it is a directory that cannot be
    searched, which the caller reports as a missing option rather than a
    failure.
    """
    try:
        from quill.core.podcasts.podcast_index import credentials
    except ImportError:
        return ("", "")
    try:
        return credentials()
    except OSError:  # pragma: no cover - platform dependent
        return ("", "")


def preview_search_result(dialog: Any, result: Any, result_index: int) -> None:
    """Fetch *result*'s feed, show it read-only, and subscribe if asked."""
    dialog._status.SetLabel(f"Loading {result.title}...")
    dialog._preview_btn.Enable(False)
    feed_url = result.feed_url

    def _work(**_kwargs: object) -> Any:
        from quill.core.podcasts import feed_reader

        return feed_reader.load_feed(feed_url)

    def _done(_op: str, feed: Any) -> None:
        dialog._preview_btn.Enable(True)
        dialog._status.SetLabel("")
        from quill.ui.podcasts.feed_preview_dialog import FeedPreviewDialog

        wants = FeedPreviewDialog(dialog.dialog, feed=feed, announce_cb=dialog._announce).show()
        if wants:
            dialog._subscribe_to_feed(feed_url, title_hint=result.title, result_index=result_index)

    def _failed(_op: str, error: object) -> None:
        dialog._preview_btn.Enable(True)
        # Named, and not fatal: the feed may be down while the directory entry
        # is fine, and subscribing anyway is still a reasonable thing to do.
        dialog._status.SetLabel(f"That podcast could not be loaded: {error}")

    dialog._task_manager.submit("podcast-preview", _work, on_success=_done, on_failure=_failed)
