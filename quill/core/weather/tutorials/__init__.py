"""Quill Weather's guided tutorials: its tracks, and its lessons assembled.

Eleven lessons in three tracks. The engine -- what a step is, how one renders,
where progress is kept -- is shared with Quill Radio, QUILL Cast and QUILL in
:mod:`quill.core.tutorials`; this is Weather's content and nothing else.

The middle track is the one that matters. Quill Weather is a small app with
one serious job, and "being warned" is that job: everything in track one exists
so that track two has somewhere to send its alerts.
"""

from __future__ import annotations

from quill.core.tutorials.model import Track, TutorialSet, build
from quill.core.weather.tutorials import being_warned, getting_started, making_it_yours

#: Weather's tracks, in teaching order.
TRACKS: tuple[Track, ...] = (
    Track(
        "start",
        "Your first ten minutes",
        "Add a place, read everything the app knows about it, and learn the one "
        "key that answers without opening anything.",
    ),
    Track(
        "watch",
        "Being warned",
        "The reason this app exists: a watch that speaks a warning the moment it "
        "is issued, tuned so that you leave it on, and running whether or not "
        "anything else is.",
    ),
    Track(
        "yours",
        "Making it yours",
        "Several places rather than one, the settings that decide how long a "
        "reading takes to speak, and living beside the rest of the family.",
    ),
)

#: Every Quill Weather lesson, in teaching order.
CATALOGUE: TutorialSet = build(
    "weather",
    TRACKS,
    getting_started.TUTORIALS,
    being_warned.TUTORIALS,
    making_it_yours.TUTORIALS,
)
