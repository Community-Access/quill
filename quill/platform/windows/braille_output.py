"""Send announcements to a braille display, not just to speech (#1283).

Reported by a braille user: "many status and informational messages that are
spoken by a screen reader are not displayed in braille" -- What's Playing, a
finished weather refresh, a Radio Reading Services update. The diagnosis was
blunt: **QUILL never sent anything to a braille display.** Every announcement
path spoke; none brailled. Not a JAWS-vs-NVDA difference, not specific to one
command -- a whole output channel was missing for every app.

Both bridges QUILL already depends on can braille:

* **Prism** exposes ``Backend.braille(text)`` and advertises the capability with
  ``features.supports_braille``.
* **accessible_output2** implements it per reader -- JAWS through its
  ``BrailleString`` scripting call, NVDA through ``nvdaController_brailleMessage``.

This module holds the dispatch so it can be tested on its own and so
``prism_bridge`` keeps its shape. Three rules shape it:

1. **Braille must never cost speech.** Every call is guarded; a display that was
   unplugged mid-session, a reader that rejects the call, a bridge without the
   capability -- all of it degrades to "spoke but did not braille", never to
   silence. The error is recorded once for diagnostics rather than raised.
2. **No truncation.** A braille display is narrow, but both JAWS and NVDA let
   the reader pan a long flash message. Clipping to display width would quietly
   drop the end of a track title, which is exactly the information the user
   asked for.
3. **Do not steal the display for the same text twice.** A braille flash
   replaces whatever the user is reading under their fingers. Radio's
   now-playing poller can re-announce an identical title, so an identical
   message inside a short window is skipped.

Windows-shaped (the two bridges are Windows), but nothing here imports Windows
APIs, so it stays importable and testable everywhere. wx-free.
"""

from __future__ import annotations

import logging
import time
from typing import Any

_log = logging.getLogger(__name__)

#: How long an identical message is suppressed, in seconds. Long enough to
#: absorb a repeated poll, short enough that a genuine repeat ("Recording
#: started" twice) still reaches the display.
DUPLICATE_WINDOW_SECONDS = 2.0

#: Set by :func:`braille_message`; read by the tests and by diagnostics.
_last_message: str = ""
_last_sent_at: float = 0.0


def reset_duplicate_state() -> None:
    """Forget the last brailled message. Test-only helper."""
    global _last_message, _last_sent_at
    _last_message = ""
    _last_sent_at = 0.0


def _is_duplicate(message: str, now: float) -> bool:
    return (
        bool(_last_message)
        and message == _last_message
        and (now - _last_sent_at) < (DUPLICATE_WINDOW_SECONDS)
    )


def _remember(message: str, now: float) -> None:
    global _last_message, _last_sent_at
    _last_message = message
    _last_sent_at = now


def prism_supports_braille(backend: Any) -> bool:
    """True when a Prism backend advertises braille support.

    A backend that does not advertise it is left alone rather than probed:
    calling an unsupported method would raise on every single announcement.
    """
    features = getattr(backend, "features", None)
    return bool(getattr(features, "supports_braille", False))


def braille_via_prism(backend: Any, message: str, *, now: float | None = None) -> str:
    """Braille *message* through a Prism backend. Returns "" or an error string.

    Deliberately ``backend.braille()`` and not ``backend.output()``: ``output()``
    couples speech and braille into one call, so a braille failure would take the
    speech with it -- the opposite of the rule above.
    """
    text = (message or "").strip()
    if not text:
        return ""
    if not prism_supports_braille(backend):
        return ""
    braille = getattr(backend, "braille", None)
    if not callable(braille):
        return ""
    stamp = time.monotonic() if now is None else now
    if _is_duplicate(text, stamp):
        return ""
    try:
        braille(text)
    except Exception as exc:  # noqa: BLE001 - never let braille break speech
        _log.debug("Prism braille failed: %s", exc)
        return f"Braille output failed: {exc}"
    _remember(text, stamp)
    return ""


def braille_via_accessible_output2(output: Any, message: str, *, now: float | None = None) -> str:
    """Braille *message* through one concrete accessible_output2 output.

    The concrete output, never the ``Auto`` wrapper: ``Auto.output()`` in the
    shipped version speaks twice and never brailles, so routing through it would
    double-speak every message and still leave the display blank.
    """
    text = (message or "").strip()
    if not text:
        return ""
    braille = getattr(output, "braille", None)
    if not callable(braille):
        return ""
    stamp = time.monotonic() if now is None else now
    if _is_duplicate(text, stamp):
        return ""
    try:
        braille(text)
    except Exception as exc:  # noqa: BLE001 - never let braille break speech
        _log.debug("accessible_output2 braille failed: %s", exc)
        return f"Braille output failed: {exc}"
    _remember(text, stamp)
    return ""
