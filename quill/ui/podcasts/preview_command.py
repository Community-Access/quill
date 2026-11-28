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

import logging
import time
from typing import Any

from quill.ui.podcasts.say_status import say_status

__all__ = [
    "current_result_index",
    "podcast_index_credentials",
    "preview_current_row",
    "preview_search_result",
]

logger = logging.getLogger(__name__)

#: Said when Preview is asked for with no row to preview. A sentence, not
#: silence: a press that does nothing is the bug this module keeps meeting.
CHOOSE_FIRST = "Choose a podcast in Results first."


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


def current_result_index(dialog: Any) -> int:
    """The Results row Preview and the row menu act on, or -1.

    The selected row, and failing that the focused one: a screen reader can
    leave the list cursor on a row without selecting it, and a listener on a
    row reasonably expects the row they hear to be the one acted on.
    """
    results = getattr(dialog, "_search_results", None) or []
    ctrl = getattr(dialog, "_results", None)
    if ctrl is None:
        return -1
    for read in ("GetFirstSelected", "GetFocusedItem"):
        getter = getattr(ctrl, read, None)
        index = getter() if callable(getter) else -1
        if 0 <= index < len(results):
            return int(index)
    return -1


def _say(dialog: Any, text: str) -> None:
    """Show *text* and speak it even when the label already says it.

    say_status speaks only a change, and these are answers to a key press: a
    second press with no row, or a third while loading, would otherwise set
    the same words and say nothing -- the "press does nothing" bug again.
    """
    say_status(dialog._status, text, speak=False)
    try:
        dialog._announce(text)
    except Exception:  # noqa: BLE001 - speech must never break the action
        pass


def preview_current_row(dialog: Any) -> None:
    """Preview the current Results row, or say why there is nothing to preview."""
    index = current_result_index(dialog)
    if index < 0:
        _say(dialog, CHOOSE_FIRST)
        return
    preview_search_result(dialog, dialog._search_results[index], index)


#: How long a preview counts as still loading if neither callback ever comes
#: (a task cancelled before it ran calls neither). Well past the feed fetch's
#: own timeout, so a slow feed is never mistaken for a lost one.
BUSY_SECONDS = 60.0


def _loading_title(dialog: Any) -> str:
    """The show a preview is loading for, or "" when none is in flight."""
    busy = getattr(dialog, "_preview_busy", None)
    if not busy:
        return ""
    title, since = busy
    if time.monotonic() - since > BUSY_SECONDS:
        dialog._preview_busy = None
        return ""
    return str(title)


def _focus_back(window: Any) -> None:
    """Put focus back on the control the preview was opened from."""
    if window is None:
        return
    try:
        if window.IsEnabled() and window.IsShownOnScreen():
            window.SetFocus()
    except (AttributeError, RuntimeError):  # gone, or a fake in a test
        return


def _focused_window() -> Any:
    try:
        import wx

        return wx.Window.FindFocus()
    except Exception:  # noqa: BLE001 - no wx, or no focus: nothing to restore
        return None


def _later(func: Any, *args: Any) -> None:
    """After the owner frame has reactivated: on wxMSW ``ShowModal`` returns
    before WM_ACTIVATE restores the frame's own remembered child, which would
    override (or double-announce) a focus set synchronously."""
    try:
        import wx

        wx.CallAfter(func, *args)
    except Exception:  # noqa: BLE001 - no wx loop: do it now
        func(*args)


def preview_search_result(dialog: Any, result: Any, result_index: int) -> None:
    """Fetch *result*'s feed, show it read-only, and subscribe if asked.

    Every path ends in the preview window or a spoken sentence saying why not.
    """
    loading = _loading_title(dialog)
    if loading:
        # A second press while the first is loading. The button stays enabled
        # (disabling the focused button drops focus to nowhere, so the reader
        # goes quiet mid-wait); this is the double-press guard instead. It
        # names the show being loaded, not the row the cursor has moved to.
        _say(dialog, f"Still loading {loading}...")
        return
    dialog._preview_busy = (str(result.title), time.monotonic())
    say_status(dialog._status, f"Loading {result.title}...", dialog._announce)
    feed_url = result.feed_url

    safe_mode = bool(getattr(dialog, "_safe_mode", False))

    def _work(**_kwargs: object) -> Any:
        from quill.core.podcasts import feed_reader

        # fetch_and_parse_feed, not load_feed: there has never been a
        # load_feed, so every Preview raised AttributeError inside the
        # background task, landed in _failed, and set a status label. The
        # button was not doing nothing -- it was failing quietly, which
        # looks identical from outside (reported 2026-09-30).
        return feed_reader.fetch_and_parse_feed(feed_url, safe_mode=safe_mode)

    def _done(_op: str, feed: Any) -> None:
        dialog._preview_busy = None
        say_status(dialog._status, "", speak=False)
        # Where focus is now, just before the window opens -- the button, the
        # row, or wherever the listener moved while it loaded.
        returning_to = _focused_window()
        # Guarded, and spoken: this runs as a task-manager success callback,
        # and call_ui_safely logs and swallows anything it raises. That is how
        # a TypeError building the window made Preview do nothing at all --
        # no window, no sound, a line in a log nobody reads (2026-11-27).
        try:
            from quill.ui.podcasts.feed_preview_dialog import FeedPreviewDialog

            wants = FeedPreviewDialog(dialog.frame, feed=feed, announce_cb=dialog._announce).show()
        except Exception:  # noqa: BLE001 - reported to the listener below
            logger.exception("Preview of %s could not be shown", feed_url)
            _say(
                dialog,
                f"The preview of {result.title} could not be opened. "
                "You can still follow it from Results.",
            )
            return
        if wants:
            dialog._subscribe_to_feed(feed_url, title_hint=result.title, result_index=result_index)
            return
        _later(_focus_back, returning_to)

    def _failed(_op: str, error: object) -> None:
        dialog._preview_busy = None
        # Named, and not fatal: the feed may be down while the directory entry
        # is fine, and following anyway is still a reasonable thing to do.
        # Spoken as well as shown: a status label is silent to a screen
        # reader, which is how Preview's failure went unheard (qc.md 6b item 4).
        from quill.core.podcasts.feed_problems import plain

        # The plain sentence, never the exception text (check.md bug 7).
        message = (
            f"That podcast could not be loaded: {plain(error)}"
            if isinstance(error, BaseException)
            else f"That podcast could not be loaded: {error}"
        )
        say_status(dialog._status, message, speak=False)
        from quill.ui.podcasts.failure_report import report_failure

        report_failure(dialog, message, subject=str(result.title))

    try:
        dialog._task_manager.submit("podcast-preview", _work, on_success=_done, on_failure=_failed)
    except Exception as exc:  # noqa: BLE001 - a refused submit is a failure too
        logger.exception("Preview of %s could not start", feed_url)
        _failed("podcast-preview", exc)
