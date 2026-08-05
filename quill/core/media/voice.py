"""Voice-command parsing for the media player (PRD Section 9.7 / 18).

The pure, testable half of voice control: turn a recognized phrase into a
:class:`VoiceIntent` (an action plus an optional numeric argument). The live mic
capture and speech recognition are wired separately in the UI and feed their
recognized text here; this module has no audio and no engine, so the whole
command grammar is unit-tested.

Every intent maps to a player command that also has a key/menu -- voice is purely
additive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.media.timecode import parse_timecode

_DEFAULT_SKIP_SECONDS = 30

_ONES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60}


@dataclass(frozen=True, slots=True)
class VoiceIntent:
    """A recognized command: an ``action`` and an optional integer ``value``.

    ``value`` is milliseconds for ``skip``/``seek`` and whole minutes for ``sleep``.
    """

    action: str
    value: int = 0


def _words_to_int(text: str) -> int | None:
    """Parse a small number from digits or words (0-99)."""
    text = text.strip().lower()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    total = 0
    matched = False
    for token in text.replace("-", " ").split():
        if token in _TENS:
            total += _TENS[token]
            matched = True
        elif token in _ONES:
            total += _ONES[token]
            matched = True
        elif token.isdigit():
            total += int(token)
            matched = True
    return total if matched else None


_UNIT_SECONDS = {
    "hour": 3600,
    "hours": 3600,
    "minute": 60,
    "minutes": 60,
    "min": 60,
    "second": 1,
    "seconds": 1,
    "sec": 1,
}


def _parse_spoken_time(text: str) -> int | None:
    """Parse a spoken/typed time into milliseconds ('1:23:45', 'one hour twenty')."""
    text = text.strip().lower()
    try:
        return parse_timecode(text)
    except Exception:  # noqa: BLE001 - fall through to the spoken-units form
        pass
    total = 0
    current = 0
    found_unit = False
    for token in re.sub(r"[^a-z0-9\s-]", " ", text).replace("-", " ").split():
        if token in _UNIT_SECONDS:
            total += current * _UNIT_SECONDS[token]
            current = 0
            found_unit = True
        elif token in _TENS:
            current += _TENS[token]
        elif token in _ONES:
            current += _ONES[token]
        elif token.isdigit():
            current += int(token)
    if not found_unit:
        return None
    return total * 1000


def parse_voice_command(text: str) -> VoiceIntent | None:
    """Parse a recognized phrase into a :class:`VoiceIntent`, or ``None``."""
    if not isinstance(text, str):
        return None
    t = " ".join(text.strip().lower().split())
    if not t:
        return None

    # Fixed commands (order matters: check specific before generic).
    if "next chapter" in t or t in {"next", "skip chapter"}:
        return VoiceIntent("next_chapter")
    if "previous chapter" in t or "back a chapter" in t or "last chapter" in t or t == "previous":
        return VoiceIntent("prev_chapter")
    if t in {"play pause", "toggle"}:
        return VoiceIntent("toggle")
    if t in {"play", "resume", "start", "unpause", "continue"}:
        return VoiceIntent("play")
    if t in {"pause", "hold"}:
        return VoiceIntent("pause")
    if t in {"stop", "halt"}:
        return VoiceIntent("stop")
    if "bookmark" in t:
        return VoiceIntent("bookmark")
    if "where am i" in t or "how much" in t or "how far" in t or "time left" in t:
        return VoiceIntent("where_am_i")
    if "mute" in t or "unmute" in t:
        return VoiceIntent("mute")
    if "faster" in t or "speed up" in t:
        return VoiceIntent("faster")
    if "slower" in t or "slow down" in t:
        return VoiceIntent("slower")
    if "volume up" in t or "louder" in t:
        return VoiceIntent("volume_up")
    if "volume down" in t or "quieter" in t or "softer" in t:
        return VoiceIntent("volume_down")
    if "summarize" in t or "summary" in t:
        return VoiceIntent("summarize")
    if "recap" in t or "catch me up" in t:
        return VoiceIntent("recap")

    if "sleep" in t:
        if "off" in t or "cancel" in t or "never" in t:
            return VoiceIntent("sleep", 0)
        if "chapter" in t:
            return VoiceIntent("sleep_eoc")
        minutes = _words_to_int(re.sub(r"[^0-9a-z\s-]", " ", t).replace("sleep", ""))
        if minutes:
            return VoiceIntent("sleep", minutes)
        return None

    skip = re.search(
        r"\b(skip|jump|go|rewind|fast forward)\b.*?\b(back\w*|forward\w*|ahead)\b(.*)", t
    )
    if skip:
        seconds = _words_to_int(skip.group(3)) or _DEFAULT_SKIP_SECONDS
        delta = seconds * 1000 * (-1 if "back" in skip.group(2) else 1)
        return VoiceIntent("skip", delta)
    if "rewind" in t:
        return VoiceIntent("skip", -_DEFAULT_SKIP_SECONDS * 1000)
    if "fast forward" in t or "forward" in t:
        return VoiceIntent("skip", _DEFAULT_SKIP_SECONDS * 1000)

    goto = re.search(r"\b(go to|jump to|seek to|go|jump)\b\s+(.+)", t)
    if goto:
        ms = _parse_spoken_time(goto.group(2))
        if ms is not None:
            return VoiceIntent("seek", ms)

    return None


__all__ = ["VoiceIntent", "parse_voice_command"]
