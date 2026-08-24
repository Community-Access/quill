"""Volume Boost, per podcast (list.md 2.8).

Quill Radio has had a boost for a while, as a switch: on, and the player is
allowed past 100%. That is the right shape for radio, where the thing you are
listening to changes every time you tune somewhere else and one global answer
is the only answer that could keep up.

**A podcast library is the opposite case.** One badly-mastered show among forty
is exactly what a global control cannot fix: turn it up for that show and every
other show is now too loud. So this is per podcast, with a global default --
the same shape speed, the EQ and the compressor already have, and set the same
way (``PodcastLibrary.apply_show_override``).

Four levels rather than a number, deliberately. "Louder" is a judgement, not a
measurement, and a listener choosing between Low and Medium is answering a
question they can actually hold; one choosing between 118% and 126% is being
asked to do the app's job. The steps are wide enough to be audibly different
from each other, which is the only property that makes a four-way choice worth
having.

**The ceiling is real and it is a promise.** Boost multiplies the volume the
listener already set, so High on a player at 100 is 150 -- and no further,
because past about there a spoken-word recording stops getting louder and
starts getting distorted, and an app that let somebody find that edge by
themselves would be an app that damaged their audio on request.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

OFF = "off"
LOW = "low"
MEDIUM = "medium"
HIGH = "high"

#: ``(value, label, multiplier)``. The multiplier is applied to whatever
#: volume the listener already chose, so boost and the volume control compose
#: rather than fighting.
LEVELS: tuple[tuple[str, str, float], ...] = (
    (OFF, "Off", 1.0),
    (LOW, "Low", 1.15),
    (MEDIUM, "Medium", 1.3),
    (HIGH, "High", 1.5),
)

#: The hard ceiling, as a percentage of the system volume. Past this a
#: spoken-word recording stops getting louder and starts getting distorted.
MAX_PERCENT = 150


def normalize(value: object) -> str:
    """A stored level as one of the four, or ``off`` (pure).

    Anything unreadable is off -- the quiet answer, because a typo in a
    settings file should never make somebody's next episode louder than they
    asked for.
    """
    wanted = str(value or "").strip().lower()
    for name, _label, _factor in LEVELS:
        if wanted == name:
            return name
    return OFF


def multiplier(value: object) -> float:
    """What to multiply the chosen volume by (pure). 1.0 when off."""
    wanted = normalize(value)
    for name, _label, factor in LEVELS:
        if name == wanted:
            return factor
    return 1.0


def apply_to(volume: object, level: object) -> int:
    """The volume to send the engine, boosted and capped (pure).

    Capped at :data:`MAX_PERCENT` rather than at 100: the whole point of a
    boost is to go past 100 on an engine that can. An engine that cannot
    clamps it itself, which is why sending the boosted number is safe
    everywhere.
    """
    if isinstance(volume, bool) or not isinstance(volume, (int, float, str)):
        return 0
    try:
        base = max(0, int(float(volume)))
    except (TypeError, ValueError):
        return 0
    return min(MAX_PERCENT, int(round(base * multiplier(level))))


def label(value: object) -> str:
    """The chosen level, in the words the control offers."""
    wanted = normalize(value)
    for name, text, _factor in LEVELS:
        if name == wanted:
            return text
    return "Off"


def index_of(value: object) -> int:
    """Which row of :data:`LEVELS` a stored value is (pure)."""
    wanted = normalize(value)
    for index, (name, _label, _factor) in enumerate(LEVELS):
        if name == wanted:
            return index
    return 0


def from_index(position: object) -> str:
    """The level at *position*, or ``off``. Total for a wx selection."""
    if not isinstance(position, int) or not 0 <= position < len(LEVELS):
        return OFF
    return LEVELS[position][0]


def describe(value: object) -> str:
    """One spoken sentence, for the announcement when it changes."""
    wanted = normalize(value)
    if wanted == OFF:
        return "Volume Boost off. This podcast plays at the volume you set."
    return (
        f"Volume Boost {label(wanted).lower()}. This podcast plays "
        f"{int(round((multiplier(wanted) - 1) * 100))} percent louder than the "
        "volume you set, for this podcast only."
    )


__all__ = [
    "HIGH",
    "LEVELS",
    "LOW",
    "MAX_PERCENT",
    "MEDIUM",
    "OFF",
    "apply_to",
    "describe",
    "from_index",
    "index_of",
    "label",
    "multiplier",
    "normalize",
]
