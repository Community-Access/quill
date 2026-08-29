"""QUILL Cast's guided tutorials: its tracks, and its lessons assembled.

Nineteen lessons in four tracks. The engine -- what a step is, how one
renders, where progress is kept -- is shared with Quill Radio, Quill Weather
and QUILL in :mod:`quill.core.tutorials`; this is Cast's content and nothing
else.

The shape of the set follows the shape of the problem. Playing a podcast is
easy and takes one track; *keeping up* with forty of them is the hard part and
takes five lessons of its own, because the Inbox, the Play Queue, automatic
downloads and their caps are one system and only make sense together.
"""

from __future__ import annotations

from quill.core.podcasts.tutorials import (
    first_hour,
    keeping_up,
    listening_well,
    making_it_yours,
)
from quill.core.tutorials.model import Track, TutorialSet, build

#: Cast's tracks, in teaching order.
TRACKS: tuple[Track, ...] = (
    Track(
        "first-hour",
        "Your first hour",
        "Subscribe to something, play it, learn the keys that work while it is "
        "playing, and meet the Podcast Manager.",
    ),
    Track(
        "keeping-up",
        "Keeping up",
        "The hard part of podcasting is not playing an episode; it is deciding "
        "which of the four hundred waiting ones you will play. The Inbox, the "
        "queue, automatic downloads, and the rules that keep all three bounded.",
    ),
    Track(
        "listening",
        "Listening well",
        "The hour itself: skipping what you did not come for, shaping the "
        "sound, keeping a moment, reading what the publisher sent, and how much "
        "of your life this has taken.",
    ),
    Track(
        "yours",
        "Making it yours",
        "A library that has grown, what a row says and what Enter does, the "
        "settings that differ per show, feeds and folders of your own, and the "
        "backup you will be glad of exactly once.",
    ),
)

#: Every QUILL Cast lesson, in teaching order.
CATALOGUE: TutorialSet = build(
    "cast",
    TRACKS,
    first_hour.TUTORIALS,
    keeping_up.TUTORIALS,
    listening_well.TUTORIALS,
    making_it_yours.TUTORIALS,
)
