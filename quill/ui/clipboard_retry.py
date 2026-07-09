"""Bounded retry around Windows clipboard reads (issue: OpenClipboard race).

Windows' clipboard is a shared, single-owner OS resource. A read can transiently
fail with a sharing violation (``CLIPBRD_E_CANT_OPEN`` / HRESULT -2147221040)
when another process -- a clipboard-history manager, Windows' own Win+V
history, or a screen reader polling clipboard content for an announcement --
briefly holds the clipboard open at the exact moment QUILL tries to read it.

wxWidgets' own ``wxClipboard::GetData`` (``src/msw/clipbrd.cpp``) logs this
immediately as a GUI error dialog ("Failed to get data from the clipboard
(error -2147221040: OpenClipboard Failed)"), even though ``wx.TheClipboard
.Open()`` can have already returned success moments earlier -- ``GetData``
does its own additional internal clipboard access and can lose the race on
its own. A single failed attempt therefore surfaced a scary popup for what is
normally a sub-millisecond contention window.

``with_clipboard_read_retry`` retries a whole Open/GetData/Close cycle a
bounded number of times with a brief sleep between attempts, mirroring
``core.storage.retry_on_transient_lock``'s bounded-retry style for a
different transient-lock scenario (Windows file replace). wx's automatic
error dialog is suppressed (``wx.LogNull``) on every attempt but the last, so
a transient failure is retried silently; if every attempt is exhausted, the
final attempt runs with logging enabled so wx's existing error dialog still
appears -- a real, sustained clipboard lock is still worth surfacing.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

# 10 attempts * 20ms = 200ms worst case, comfortably under the ~300ms budget
# for the UI to still feel responsive rather than frozen.
_MAX_ATTEMPTS = 10
_RETRY_DELAY = 0.02


def with_clipboard_read_retry(
    wx: Any,
    action: Callable[[], bool],
    *,
    max_attempts: int = _MAX_ATTEMPTS,
    delay: float = _RETRY_DELAY,
) -> bool:
    """Call ``action`` up to ``max_attempts`` times, retrying on failure.

    ``action`` should perform one full clipboard-read cycle (typically
    ``wx.TheClipboard.Open()`` -> ``GetData(...)`` -> ``Close()``) and return
    ``True`` on success, ``False`` if the attempt should be retried (the
    clipboard could not be opened, or ``GetData`` failed for a format
    ``IsSupported`` already confirmed was present).

    Returns ``True`` as soon as ``action`` succeeds, or ``False`` once every
    attempt has been exhausted. wx's own error dialog is suppressed via
    ``wx.LogNull`` on all but the final attempt; the final attempt is run
    unsuppressed so a genuinely sustained lock still surfaces the existing
    error dialog, unchanged from before this retry loop existed.
    """
    for attempt in range(max_attempts):
        is_last_attempt = attempt == max_attempts - 1
        log_suppressor = None if is_last_attempt else wx.LogNull()
        try:
            if action():
                return True
        finally:
            if log_suppressor is not None:
                del log_suppressor
        if not is_last_attempt:
            time.sleep(delay)
    return False


def read_clipboard_text(
    wx: Any, *, max_attempts: int = _MAX_ATTEMPTS, delay: float = _RETRY_DELAY
) -> str:
    """Return plain text from the clipboard, retrying transient read failures.

    Returns ``""`` if the clipboard has no text data, or if every retry
    attempt failed to open/read the clipboard (in which case wx's own error
    dialog is shown on the final attempt, same as before this helper existed).
    """
    clipboard = getattr(wx, "TheClipboard", None)
    if clipboard is None:
        return ""

    text = ""

    def _attempt() -> bool:
        nonlocal text
        if not clipboard.Open():
            return False
        try:
            data = wx.TextDataObject()
            if clipboard.GetData(data):
                text = str(data.GetText())
                return True
            return False
        finally:
            clipboard.Close()

    with_clipboard_read_retry(wx, _attempt, max_attempts=max_attempts, delay=delay)
    return text
