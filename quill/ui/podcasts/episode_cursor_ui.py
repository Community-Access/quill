"""The episode cursor (:mod:`quill.core.podcasts.episode_cursor`) for both podcast windows.

QUILL's Podcast Manager and QUILL Cast's one window each call three things:
:func:`remember_episode` when the selection moves in one podcast's episode
list, :func:`remembered_row` when that list is (re)filled, and
:func:`flush_cursor` when the window closes. The file is written at most once
a second while you arrow, through a restarting timer, so walking a long list
is not a disk write per key; :func:`flush_cursor` writes what is pending.

Nothing here speaks: landing on the remembered row is a selection change, which
the screen reader already reads (GATE-13).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.podcasts.episode_cursor import EpisodeCursor

__all__ = ["flush_cursor", "remember_episode", "remember_feed_cursor", "remembered_row"]

_SAVE_DELAY_MS = 1000


def _cursor(host: Any) -> EpisodeCursor:
    cursor = getattr(host, "_episode_cursor", None)
    if cursor is None:
        from quill.core.paths import app_data_dir

        try:
            cursor = EpisodeCursor.load(app_data_dir())
        except Exception:  # noqa: BLE001 - a broken profile is an empty memory
            cursor = EpisodeCursor()
        host._episode_cursor = cursor
    return cursor


def remember_episode(host: Any, show: Any, episode: Any) -> None:
    """Note *episode* as where the listener is in *show*; save shortly after."""
    if show is None or episode is None:
        return
    if not _cursor(host).remember(show, episode):
        return
    timer = getattr(host, "_episode_cursor_timer", None)
    try:
        import wx

        if timer is not None and timer.IsRunning():
            timer.Stop()
        host._episode_cursor_timer = wx.CallLater(_SAVE_DELAY_MS, _cursor(host).save)
    except Exception:  # noqa: BLE001 - no event loop (tests): write now
        _cursor(host).save()


def remember_feed_cursor(host: Any) -> None:
    """QUILL Cast: note the selected episode, only in one podcast's own list.

    A cross-podcast list (New Episodes, the Inbox) is not a place in any one
    feed, and moving through it must not move each feed's own cursor.
    """
    show = getattr(host, "_current_show", None)
    if show is None or not getattr(host, "_place_opened_show_id", ""):
        return
    selected = getattr(host, "_selected_episode", None)
    pair = selected() if callable(selected) else None
    if pair is not None and pair[0] is show:
        remember_episode(host, show, pair[1])


def remembered_row(host: Any, show: Any, episodes: Sequence[Any]) -> int:
    """The row to select in *show*'s freshly filled list: remembered, else the first."""
    if show is None:
        return 0
    row = _cursor(host).row_for(show, episodes)
    return 0 if row is None else row


def flush_cursor(host: Any) -> None:
    """Write any pending cursor now (the window is closing)."""
    timer = getattr(host, "_episode_cursor_timer", None)
    try:
        if timer is not None and timer.IsRunning():
            timer.Stop()
    except Exception:  # noqa: BLE001 - a timer from a dead event loop
        pass
    cursor = getattr(host, "_episode_cursor", None)
    if cursor is not None:
        cursor.save()
