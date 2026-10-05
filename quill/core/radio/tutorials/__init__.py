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
    downloads_and_video,
    extras,
    favorites_and_rows,
    first_hour,
    first_hour_unstuck,
    keys_and_settings,
    living_care,
    living_daily,
    local_media,
    own_sources,
    pick_up_and_help,
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
        "Start here. By the end of this track you will have found a station and "
        "kept it, you will know the player keys that work in every window, and "
        "you will know how to get yourself unstuck.",
    ),
    Track(
        "finding",
        "Finding something to listen to",
        "Lots of ways to find something you will love: browsing, searching "
        "every directory at once, adding stations of your own, and the station "
        "list on your computer that works even without the internet.",
    ),
    Track(
        "yours",
        "Making it yours",
        "Folders, your own order, what each row says, your own keys, and the "
        "handful of settings that make Quill Radio feel like yours.",
    ),
    Track(
        "recording",
        "Recording",
        "From one key that records what is on, to a show that records itself "
        "every Tuesday while you are out, and what happens if the connection "
        "drops.",
    ),
    Track(
        "beyond",
        "More than radio",
        "Podcasts, audiobooks, YouTube, television and the ACB Media schedule. "
        "They all live in Browse Stations and play with the keys you already "
        "know.",
    ),
    Track(
        "living",
        "Living with it",
        "The things you will want after your first week: what was that song, "
        "keeping a moment, sleep timers, your listening statistics, and where "
        "to look when something goes wrong.",
    ),
)

#: Every Quill Radio lesson, in teaching order.
CATALOGUE: TutorialSet = build(
    "radio",
    TRACKS,
    first_hour.TUTORIALS,
    first_hour_unstuck.TUTORIALS,
    browsing.TUTORIALS,
    own_sources.TUTORIALS,
    favorites_and_rows.TUTORIALS,
    keys_and_settings.TUTORIALS,
    recording_basics.TUTORIALS,
    recording_more.TUTORIALS,
    beyond_podcasts.TUTORIALS,
    beyond_tv.TUTORIALS,
    local_media.TUTORIALS,
    downloads_and_video.TUTORIALS,
    living_daily.TUTORIALS,
    living_care.TUTORIALS,
    pick_up_and_help.TUTORIALS,
    extras.TUTORIALS,
)
