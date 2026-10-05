"""How a value read from QUILL Lite's settings file is made safe to use.

Moved out of :mod:`quill.core.lite.settings` on 2026-10-04 (GATE-11): that
module is the dataclass, and these are the three rules every field is read
through. The loader is deliberately tolerant -- a hand-edited file with a wrong
type in it costs the person that one field, never the ability to start.
"""

from __future__ import annotations

from typing import Any

__all__ = ["MAX_SPELL_MS", "MIN_SPELL_MS", "clamp_ms", "coerce", "suffix_list"]

#: Bounds for the spell-aloud pauses. The ceiling is deliberately generous: a
#: listener on a slow synthesiser genuinely waits longer than three seconds to
#: hear a word out, and the number that makes the feature usable for them should
#: not be un-typeable.
MIN_SPELL_MS = 100
MAX_SPELL_MS = 5000


def clamp_ms(
    value: Any, fallback: int, *, low: int = MIN_SPELL_MS, high: int = MAX_SPELL_MS
) -> int:
    """A millisecond field forced into range, falling back on nonsense."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def coerce(current: Any, value: Any) -> Any | None:
    """*value* if it can stand in for *current*, else ``None`` (keep the default).

    ``bool`` is checked before ``int`` because ``isinstance(True, int)`` is true
    in Python, and a ``word_wrap`` of ``3`` should not be accepted as truthy.
    """
    if isinstance(current, bool):
        return value if isinstance(value, bool) else None
    if isinstance(current, int):
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    if isinstance(current, str):
        return value if isinstance(value, str) else None
    if isinstance(current, list):
        if not isinstance(value, list):
            return None
        # The element type comes from the default, because the two kinds of list
        # this store holds are not interchangeable: the recent-files lists are
        # strings and the print margins are numbers, and coercing everything to
        # str silently turned four saved margins into four strings the
        # validator then threw away (bad.md F13).
        if current and isinstance(current[0], int) and not isinstance(current[0], bool):
            return [int(item) for item in value if isinstance(item, int)]
        return [str(item) for item in value]
    return None


def suffix_list(value: Any) -> list[str]:
    """Lower-case file suffixes, each with its dot, without repeats.

    The same cleaning QUILL gives its copy of the two remembered-answer lists,
    so ``"DOCX"`` and ``".docx"`` are one answer in either editor.
    """
    cleaned: list[str] = []
    for item in value if isinstance(value, list) else []:
        suffix = str(item).strip().lower()
        if suffix and not suffix.startswith("."):
            suffix = f".{suffix}"
        if suffix and suffix not in cleaned:
            cleaned.append(suffix)
    return cleaned
