"""How hard the dynamic-range compressor works: Light, Balanced or Strong.

QUILL Cast's compressor was on or off, with one fixed setting. Earshot offers
Off, Light, Balanced and Strong (1.2.5, earshot.md E6), because how much a
compressor should even out speech depends on the recording and on where you are
listening -- a quiet room and a car want different amounts. The three levels
use Earshot's values, so a listener who moves between the two apps hears the
same thing for the same word:

========  =========  =====  ==========================
Level     Threshold  Ratio  Make-up gain
========  =========  =====  ==========================
Light     -24 dB     2:1    +2 dB (ffmpeg factor 1.26)
Balanced  -30 dB     3:1    +4 dB (ffmpeg factor 1.58)
Strong    -36 dB     4:1    +6 dB (ffmpeg factor 2.00)
========  =========  =====  ==========================

ffmpeg's ``acompressor`` takes make-up gain as a linear factor, not decibels,
which is why the third column is converted.

**One value, two shapes.** Every enhancement builder takes a ``compressor``
argument that Quill Radio passes as ``True``/``False`` -- its single fixed
compressor, unchanged -- and Cast passes as a level name. Threading a second
argument through the six functions that build an ffmpeg graph would mean six
places that could forget it.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

__all__ = [
    "COMPRESSION_LEVELS",
    "COMPRESSION_LEVEL_LABELS",
    "DEFAULT_LEVEL",
    "LEGACY_COMPRESSOR_FILTER",
    "compressor_filters",
    "compressor_value",
]

#: Quill Radio's compressor, and what ``True`` still means.
LEGACY_COMPRESSOR_FILTER = "acompressor=threshold=-18dB:ratio=3:attack=20:release=250:makeup=2"

COMPRESSION_LEVELS: dict[str, str] = {
    "light": "acompressor=threshold=-24dB:ratio=2:attack=20:release=250:makeup=1.26",
    "balanced": "acompressor=threshold=-30dB:ratio=3:attack=20:release=250:makeup=1.58",
    "strong": "acompressor=threshold=-36dB:ratio=4:attack=20:release=250:makeup=2",
}

#: Words for a chooser, in order.
COMPRESSION_LEVEL_LABELS: tuple[tuple[str, str], ...] = (
    ("light", "Light"),
    ("balanced", "Balanced"),
    ("strong", "Strong"),
)

#: The gentlest, so turning compression on never surprises anybody.
DEFAULT_LEVEL = "light"


def compressor_filters(compressor: bool | str) -> list[str]:
    """The ffmpeg filter(s) for *compressor*: ``[]`` when it is off."""
    if compressor is True:
        return [LEGACY_COMPRESSOR_FILTER]
    if isinstance(compressor, str) and compressor in COMPRESSION_LEVELS:
        return [COMPRESSION_LEVELS[compressor]]
    return []


def compressor_value(enabled: bool, level: str) -> bool | str:
    """What a podcast passes to the builders: ``False``, or the level's name."""
    if not enabled:
        return False
    return level if level in COMPRESSION_LEVELS else DEFAULT_LEVEL
