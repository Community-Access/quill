"""Podcasts (future work — not wired to any UI, command, or menu yet).

Deliberately just data shapes, sketched while building Internet Radio
(`quill/core/radio/`) so the two features can share conventions later without
a rewrite. See `docs/planning/radio.md` §3 for the actual requirements
(folders of shows, OPML import/export, playlists generated from a folder) —
that needs its own design pass before any of this is built out, since a real
folder hierarchy is a bigger data-model change than radio's flat favorites
list. Nothing here is imported by any UI code; these are notes-as-code, not a
half-finished feature. wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PodcastEpisode:
    """One episode of a subscribed show (sketch only — not yet persisted)."""

    title: str
    audio_url: str
    guid: str = ""
    published: str = ""
    duration_seconds: int = 0
    description: str = ""
    downloaded_path: str = ""


@dataclass(slots=True)
class PodcastShow:
    """One subscribed feed (sketch only — not yet persisted)."""

    title: str
    feed_url: str
    homepage: str = ""
    artwork_url: str = ""
    episodes: list[PodcastEpisode] = field(default_factory=list)


@dataclass(slots=True)
class PodcastFolder:
    """A user-organized group of shows (sketch only — not yet persisted).

    The eventual on-disk shape should follow ``core/radio/favorites.py``'s
    atomic-JSON pattern once this is actually built.
    """

    name: str
    shows: list[PodcastShow] = field(default_factory=list)
