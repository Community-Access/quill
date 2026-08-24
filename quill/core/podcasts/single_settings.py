"""One per-show setting, on its own, reachable in one keystroke (list.md 5.7).

Cast's ``show_settings`` quick action opens the whole per-show dialog: a window
of two dozen controls, of which somebody wanted one. For a setting people
change often -- how many episodes to keep, how long a queued episode waits, how
fast this particular host talks -- the difference is a dialog, a Tab press or
six, and a hunt for the right control every time. Earshot opens the editor for
that one setting with focus already on it, and it is the kind of small thing
that decides whether a feature gets used.

**Why a model rather than three dialogs.** Each of these is "a label, a
control, a sentence saying what it does, and one value to write back", and the
part worth getting right is the *sentence*, not the wx. Keeping the three
descriptions here means they can be read together, tested without a window,
and reused verbatim by the full settings dialog if it ever wants them.

**Every editor reads the effective value, not the override.** A show with no
override of its own inherits the library default, and opening its editor has
to show what is actually in force -- not zero, and not a blank. Otherwise the
first thing the editor does is misreport the setting it exists to change.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "KEEP_EPISODES",
    "PLAYBACK_SPEED",
    "QUEUE_AGE",
    "SINGLE_SETTINGS",
    "SingleSetting",
    "describe_keep",
    "describe_queue_age",
    "describe_speed",
    "setting",
]

KEEP_EPISODES = "keep_episodes"
QUEUE_AGE = "queue_age"
PLAYBACK_SPEED = "speed"


@dataclass(frozen=True, slots=True)
class SingleSetting:
    """One setting worth reaching directly: what to call it, and what it means."""

    id: str
    #: The menu row. Carries its own ellipsis because it opens a window.
    label: str
    #: The window title, and what a screen reader announces on entry.
    title: str
    #: The control's own label, with its access key.
    field_label: str
    #: What this does, in the house form: what it does, then the misreading it
    #: prevents. Read aloud when focus lands on the control.
    help: str


SINGLE_SETTINGS: tuple[SingleSetting, ...] = (
    SingleSetting(
        KEEP_EPISODES,
        "Episodes to &Keep...",
        "Episodes to Keep",
        "&Keep how many downloaded episodes:",
        "How many downloaded episodes of this podcast to keep before the "
        "oldest are deleted. Zero keeps all of them. This is about the "
        "downloaded audio only -- the episode list itself is untouched, so "
        "nothing disappears from the show.",
    ),
    SingleSetting(
        QUEUE_AGE,
        "&Queue Expiry...",
        "Queue Expiry",
        "&Drop queued episodes after how many days:",
        "How long an episode of this podcast waits in the Play Queue before "
        "it drops out. Zero means it waits indefinitely. Dropping out of the "
        "queue does not delete the episode or mark it played -- it is still "
        "in the show, where you can queue it again.",
    ),
    SingleSetting(
        PLAYBACK_SPEED,
        "Playback &Speed...",
        "Playback Speed",
        "&Speed for this podcast:",
        "How fast this podcast plays, from half speed to five times. It "
        "applies to this show only and is remembered between episodes, so a "
        "host who talks slowly stays sped up without setting it each time.",
    ),
)

_BY_ID = {item.id: item for item in SINGLE_SETTINGS}


def setting(setting_id: str) -> SingleSetting | None:
    return _BY_ID.get(setting_id)


def describe_keep(count: int) -> str:
    """What "keep N" means, said back after it is set.

    Zero is the interesting case and the one worth spelling out: it reads as
    "none" to anybody who has met a limit field before, and it means the
    opposite.
    """
    if count <= 0:
        return "Keeping every downloaded episode of this podcast."
    return f"Keeping the {count} newest downloaded episode{'' if count == 1 else 's'}."


def describe_queue_age(days: int) -> str:
    if days <= 0:
        return "Queued episodes of this podcast wait indefinitely."
    return f"Queued episodes of this podcast drop out after {days} day{'' if days == 1 else 's'}."


def describe_speed(speed: float) -> str:
    """``1.0`` reads as "normal speed", not as "1.0 times"."""
    if abs(speed - 1.0) < 0.005:
        return "This podcast plays at normal speed."
    trimmed = f"{speed:.2f}".rstrip("0").rstrip(".")
    return f"This podcast plays at {trimmed} times speed."
