"""QUILL Cast's guided tutorials: its tracks, and its lessons assembled.

Twenty-four lessons in five tracks. The engine -- what a step is, how one
renders, where progress is kept -- is shared with Quill Radio, Quill Weather
and QUILL in :mod:`quill.core.tutorials`; this is Cast's content and nothing
else.

The shape of the set follows the shape of the problem. Playing a podcast is
easy and takes one track; *keeping up* with forty of them is the hard part and
takes six lessons of its own, because the Inbox, the Play Queue, automatic
downloads, their caps and the rules that stop unwanted episodes arriving at all
are one system and only make sense together.

The fifth track exists for the same reason. Almost every complaint a podcast
listener has is about **one podcast behaving differently from the rest**, and
the settings that answer that are a system too -- a chain of levels, what
arrives, what a row says, and who is allowed to interrupt you.
"""

from __future__ import annotations

from quill.core.podcasts.tutorials import (
    first_hour,
    keeping_up,
    listening_well,
    making_it_yours,
    per_podcast,
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
        "per-podcast",
        "One podcast at a time",
        "Keep the newest three ready is right for a daily news show and wrong "
        "for a weekly interview. How a setting is decided, what arrives and "
        "when, what every row says, how a badly-reading podcast is fixed, and "
        "who is allowed to interrupt you.",
    ),
    Track(
        "yours",
        "Making it yours",
        "A library that has grown, what a row says and what Enter does, the "
        "shared defaults everything starts from, feeds and folders of your own, "
        "and the backup you will be glad of exactly once.",
    ),
)

#: Every QUILL Cast lesson, in teaching order.
CATALOGUE: TutorialSet = build(
    "cast",
    TRACKS,
    first_hour.TUTORIALS,
    keeping_up.TUTORIALS,
    listening_well.TUTORIALS,
    per_podcast.TUTORIALS,
    making_it_yours.TUTORIALS,
)
