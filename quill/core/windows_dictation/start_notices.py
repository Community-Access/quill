"""The one sentence dictation may say as it starts, beyond "Dictation on".

At most one, in this order, because each is said as the microphone opens:

1. a downloaded model that gave way to the built-in engine (the recogniser's
   ``fallback_notice``) -- never silently, and said every time it happens;
2. a saved model that was removed from the catalogue, once across the family
   (:mod:`removed_models`);
3. a far better Spanish model this computer can run, once across the family
   (:mod:`spanish_tip`).

A notice that waits its turn is not lost: the once-only ones are recorded only
when they are said.

wx-free.
"""

from __future__ import annotations

from typing import Any

__all__ = ["start_notice"]


def start_notice(recognizer: Any, preferences: Any) -> str:
    """The sentence to say as dictation starts with *recognizer*, or ``""``."""
    notice = str(getattr(recognizer, "fallback_notice", "") or "")
    if notice:
        return notice
    from quill.core.windows_dictation.removed_models import take_notice

    removed = take_notice()
    if removed:
        return removed
    from quill.core.windows_dictation.spanish_tip import take_tip

    return take_tip(
        str(getattr(preferences, "engine", "") or ""),
        str(getattr(preferences, "speech_language", "") or ""),
    )
