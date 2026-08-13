"""One definition of "is this the same crash?" (2026-08-13).

QUILL files a crash report from two places, and they hold different things:

* the **excepthook** has a live exception, with a real traceback object;
* the **crash-recovery dialog** has a saved ``crash-*.txt`` from a session
  that has already ended, which is just text.

Both must produce the *same* fingerprint for the same crash, or a crash
reported live and the same crash reported later from its file land on two
issues and the deduplication has bought nothing. That is precisely the case
the 2026-08-12 triage hit: #1386-#1389 were one crash reported four times,
and #1391/#1392 were two more of a crash already fixed in July.

So the two entry points live in one module, next to each other, rather than
one in ``stability/crash_submit.py`` and one in ``core/issue_submit.py`` where
they could quietly drift apart.

The definition itself belongs to ``feedback_hub``, because that is also what
matches an incoming report against an already-open issue -- a second
implementation here would be a second thing to keep in step. This module is
the adapter: it turns QUILL's two shapes into feedback_hub's inputs, and it
never raises.

**An empty return means "do not deduplicate this one."** It is not a
fingerprint that happens to be blank. A caller must file such a report
normally; treating empty as a real value would collapse every unparseable
report onto a single issue, which is far worse than filing duplicates.

wx-free, strict-typed.
"""

from __future__ import annotations

import traceback
from typing import Any


def from_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
) -> str:
    """Fingerprint a live exception, or ``""`` if one cannot be made.

    Returns ``""`` when ``feedback_hub`` is absent (it is an optional extra)
    or when the traceback yields no frames.
    """
    del exc_value  # part of the signature for symmetry; the value is not used
    try:
        from feedback_hub import compute_fingerprint
    except Exception:  # noqa: BLE001 - feedback_hub is an optional extra
        return ""
    try:
        frames = [(frame.filename, frame.name) for frame in traceback.extract_tb(exc_tb)]
        if not frames:
            return ""
        return str(compute_fingerprint(getattr(exc_type, "__name__", "Exception"), frames))
    except Exception:  # noqa: BLE001 - a fingerprint is never worth a crash
        return ""


def from_traceback_text(text: str) -> str:
    """Fingerprint a saved traceback, or ``""`` if one cannot be made.

    Returns ``""`` for text with no recognisable frames -- a crash-recovery
    offer can fire on log evidence alone, and a log tail is not a stable
    identity. Filing that as its own issue is right; merging two unrelated
    crashes because both were log-only would not be.
    """
    if not text:
        return ""
    try:
        from feedback_hub import fingerprint_from_traceback
    except Exception:  # noqa: BLE001 - feedback_hub is an optional extra
        return ""
    try:
        return str(fingerprint_from_traceback(text))
    except Exception:  # noqa: BLE001 - a fingerprint is never worth a failure
        return ""


__all__ = ["from_exception", "from_traceback_text"]
