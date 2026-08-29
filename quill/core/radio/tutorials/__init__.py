"""Quill Radio's guided tutorials: its tracks, and its lessons assembled.

The content lives in one module per half-track, so no single file grows past
the size a person can hold in their head, and so a lesson can be found by the
name of the thing it teaches rather than by scrolling. This module is the only
thing anything else imports: it declares Radio's tracks and hands back one
:class:`~quill.core.tutorials.model.TutorialSet`.

The engine -- what a step is, how one renders, where progress is kept -- is
shared with QUILL Cast, Quill Weather and QUILL in
:mod:`quill.core.tutorials`.

Track order is teaching order, and the contents tree reads it top to bottom,
so it runs from "you have never opened this app" to "you have relied on it for
a month".
"""

from __future__ import annotations

from quill.core.radio.tutorials import (
    beyond_podcasts,
    beyond_tv,
    browsing,
    extras,
    favorites_and_rows,
    first_hour,
    keys_and_settings,
    living_care,
    living_daily,
    own_sources,
    recording_basics,
    recording_more,
)
from quill.core.tutorials.model import Track, TutorialSet, build

#: Radio's tracks, in teaching order. A track is not a category -- it is a
#: claim about what you can do by the end of it.
TRACKS: tuple[Track, ...] = (
    Track(
        "first-hour",
        "Your first hour",
        "Start here. By the end of this track you can find a station, keep it, "
        "work the player from any window, and get yourself unstuck without "
        "asking anybody.",
    ),
    Track(
        "finding",
        "Finding something to listen to",
        "Several ways in: the tree, the search across every directory at once, "
        "addresses of your own, and the catalog on your own disk that answers "
        "when the internet does not.",
    ),
    Track(
        "yours",
        "Making it yours",
        "Folders, order, columns, keys, and the handful of settings that "
        "change how the app feels rather than what it can do.",
    ),
    Track(
        "recording",
        "Recording",
        "From one keypress to a show that records itself every Tuesday while "
        "you are out -- and what happens when the connection does not hold.",
    ),
    Track(
        "beyond",
        "More than radio",
        "Podcasts, audiobooks, YouTube, television and the ACB Media schedule "
        "all arrive through the same tree and play with the same keys.",
    ),
    Track(
        "living",
        "Living with it",
        "The parts you meet after the first week: what was that song, keeping "
        "a moment, sleeping, statistics, and where to look when something "
        "goes wrong.",
    ),
)

#: Every Quill Radio lesson, in teaching order.
CATALOGUE: TutorialSet = build(
    "radio",
    TRACKS,
    first_hour.TUTORIALS,
    browsing.TUTORIALS,
    own_sources.TUTORIALS,
    favorites_and_rows.TUTORIALS,
    keys_and_settings.TUTORIALS,
    recording_basics.TUTORIALS,
    recording_more.TUTORIALS,
    beyond_podcasts.TUTORIALS,
    beyond_tv.TUTORIALS,
    living_daily.TUTORIALS,
    living_care.TUTORIALS,
    extras.TUTORIALS,
)
