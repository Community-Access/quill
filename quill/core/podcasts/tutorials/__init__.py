"""QUILL Cast's guided tutorials: its tracks, and its lessons assembled.

Twenty-four lessons in five tracks, written against Cast 2.0: one window, a
Places list beside the place you are in, Find, a status bar, and Now Playing
as a window of its own. The engine -- what a step is, how one renders, where
progress is kept -- is shared with Quill Radio, Quill Weather and QUILL in
:mod:`quill.core.tutorials`; this is Cast's content and nothing else.

The shape of the set follows the shape of the problem. The first track is the
window itself, and what to do when something goes wrong in it. Playing a
podcast is easy; *keeping up* with forty of them is the hard part and takes
seven lessons of its own, because the Inbox, the Play Queue, your own audio,
downloads, playlists, Episode Filters and schedules are one system and only
make sense together.

The fourth track exists because almost every complaint a podcast listener has
is about **one podcast behaving differently from the rest**, and the settings
that answer that are a system too.
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
        "Follow a podcast and play it, find your way around the one window, "
        "and know what to do when something goes wrong. Start here.",
    ),
    Track(
        "keeping-up",
        "Keeping up",
        "Playing an episode is easy. Choosing which of the many waiting ones to "
        "play is the hard part, and these lessons help: the Inbox, the queue, "
        "your own audio, downloads, playlists, filters and schedules.",
    ),
    Track(
        "listening",
        "Listening well",
        "For the time you spend listening: the keys, speed and the sleep timer, "
        "chapters, the sound, bookmarks, show notes, and how much you have "
        "listened.",
    ),
    Track(
        "per-podcast",
        "One podcast at a time",
        "Keeping the newest three suits a daily news podcast and not a weekly "
        "interview. Learn how Preferences and one podcast's own settings fit "
        "together, and find the settings worth knowing in your first month.",
    ),
    Track(
        "yours",
        "Making it yours",
        "Tidy a library that has grown, choose what a row says and what Enter "
        "does, and make a backup you will be very glad of one day.",
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
