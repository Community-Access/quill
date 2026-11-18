"""Write down what QUILL meant to say and did not (from EdSharp, 2026-11).

An announcement can go unspoken for a good reason -- Quiet or Meeting Mode,
the same message a moment ago, a speech backend that failed -- and the
listener cannot tell that apart from QUILL having nothing to say. EdSharp
writes each one to its log with the reason; so does QUILL now, in the session
log a diagnostic bundle carries (which redacts it like everything else), with
whether QUILL was the window in front at the time, because a screen reader
may not voice an application that is not.
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger("quill.unspoken")

#: Long messages are cut in the log; the reason is what a report needs.
_LIMIT = 200


def log_unspoken(frame: Any, message: str, reason: str) -> None:
    """Log *message* as not spoken, because of *reason*. Never raises."""
    try:
        active = bool(frame.IsActive()) if frame is not None else True
    except Exception:  # noqa: BLE001 - a dead frame is simply "not in front"
        active = False
    text = message if len(message) <= _LIMIT else message[: _LIMIT - 3] + "..."
    where = "" if active else ", while QUILL was not the window in front"
    _log.info("Not spoken (%s%s): %s", reason, where, text)
