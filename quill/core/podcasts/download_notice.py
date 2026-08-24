"""Telling somebody a download finished, without becoming the thing that
wakes them (list.md 2.5).

A download that finishes while the window is behind something else is
invisible. There is already an earcon, and an earcon says *something* happened
rather than *what* -- fine when you are looking at the Downloads window, no use
at all when you started a forty-episode batch and went to make lunch.

Three rules, and every one of them is a reason this is a module rather than an
``if`` in the completion handler:

* **Off by default.** A desktop notification is an interruption somebody else
  chose for you. The earcon stays exactly as it is either way.
* **Local only.** Nothing leaves the computer -- this is the OS notification
  centre, not a service, not an account, not a token.
* **Through quiet hours, as the ``download`` kind.** Otherwise this is the
  first thing in the family that wakes somebody at three in the morning, which
  is exactly what a forty-episode overnight batch would have done.

The batch is the other half. Forty finished downloads are forty completions,
and forty toasts is not information -- it is a fault with a friendly icon. So
what gets announced is **the queue going quiet**: one notice, at the end,
counting what landed.

wx-free, strict-typed, pure. The counting is the caller's tally; this decides
and phrases.
"""

from __future__ import annotations

from typing import Any


def wants_notice(settings: Any) -> bool:
    """Whether the listener asked to be told. Off unless they did (pure)."""
    return bool(getattr(settings, "download_notify", False))


def should_notify(settings: Any, *, still_downloading: int, finished: int) -> bool:
    """Whether *this* completion is the one worth a notification (pure).

    Only when the queue has gone quiet: a batch is one event to a listener,
    however many rows it had, and one notice per episode would make the
    feature indistinguishable from a stuck loop.
    """
    if not wants_notice(settings):
        return False
    if finished < 1:
        return False
    return int(still_downloading) < 1


TITLE = "QUILL Cast"


def notice(finished: int, last_title: str = "", show_title: str = "") -> str:
    """What the notification says (pure).

    One episode is named, because the name is the whole content of the news.
    Several are counted, because a list of forty titles in a toast is a list
    nobody reads and a screen reader has to be interrupted to escape.
    """
    count = max(0, int(finished))
    if count == 1:
        named = str(last_title or "").strip()
        if named and str(show_title or "").strip():
            return f"Downloaded {named} -- {show_title}."
        if named:
            return f"Downloaded {named}."
        return "One episode finished downloading."
    return f"{count} episodes finished downloading."


__all__ = ["TITLE", "notice", "should_notify", "wants_notice"]
