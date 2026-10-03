"""The Fetching settings: when Cast looks for new episodes (qc.md 5e, Phase 5).

Five definitions, each at every level (the shared default, a folder, a
podcast), stored by id rather than on the dataclass so the settings record
does not grow for them. ``refresh_schedule`` is the JSON string
:mod:`quill.core.podcasts.refresh_schedule` reads and writes; empty means
"not set here", which the legacy ``refresh_minutes`` then answers for, so an
upgrade changes nobody's checking.
"""

from __future__ import annotations

from quill.core.podcasts.settings_types import (
    CATEGORY_ARRIVAL,
    KIND_BOOL,
    KIND_TEXT,
    SettingDef,
    define,
)

__all__ = ["SETTINGS"]

SETTINGS: tuple[SettingDef, ...] = (
    define(
        "refresh_schedule",
        "Check for new episodes:",
        "When this podcast is looked at for new episodes: never on its own, "
        "every so often, at set times, around when it usually publishes, or on "
        "the publisher's own hint. Checking reads the episode list; it does not "
        "download any audio, and a paused podcast is never checked.",
        kind=KIND_TEXT,
        category=CATEGORY_ARRIVAL,
        default="",
        aliases=("schedule", "refresh", "cadence", "interval", "check", "poll", "times"),
        editor="schedule",
    ),
    define(
        "check_on_launch",
        "Check when Cast &opens",
        "Look for new episodes once when Cast starts. It does not keep checking "
        "afterwards unless the schedule says so, and it is skipped on a metered "
        "connection when that switch is on.",
        kind=KIND_BOOL,
        category=CATEGORY_ARRIVAL,
        default=False,
        aliases=("launch", "startup", "open"),
    ),
    define(
        "check_on_resume",
        "Check when the computer &wakes",
        "Look for new episodes once when the computer comes back from sleep. "
        "It never checks while the computer is asleep, and a check already "
        "running is not started twice.",
        kind=KIND_BOOL,
        category=CATEGORY_ARRIVAL,
        default=False,
        aliases=("resume", "wake", "sleep"),
    ),
    define(
        "check_in_quiet_hours",
        "Check during &Quiet Hours",
        "Let scheduled checks run inside Quiet Hours. Off, a check due in Quiet "
        "Hours waits for them to end; nothing is skipped for good, and a manual "
        "Refresh is never held back.",
        kind=KIND_BOOL,
        category=CATEGORY_ARRIVAL,
        default=False,
        aliases=("quiet", "night", "hours"),
    ),
    define(
        "check_burst_after_miss",
        "Catch up on a missed check at the next &launch",
        "If a scheduled check was missed because Cast was closed, check once at "
        "the next launch regardless. It does not check twice when nothing was "
        "missed, and it never downloads audio on its own.",
        kind=KIND_BOOL,
        category=CATEGORY_ARRIVAL,
        default=True,
        aliases=("missed", "catch up", "burst"),
    ),
)
