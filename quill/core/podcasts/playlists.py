"""Saved playlists (Phase 5): resolving a Smart Playlist's rules against the
library, and resolving a manual Playlist's stored episode references.
Mirrors ``podcasts.queue``'s split from ``models.py`` (data class there,
operations here) and reuses ``podcasts.sorting``'s private sort-key builder
so a Smart Playlist orders its results exactly like every other episode
list in the app. wx-free, strict-typed.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from quill.core.podcasts.models_playlists import PlaylistRules
from quill.core.podcasts.sorting import _episode_sort_key, _parse_published

if TYPE_CHECKING:
    from quill.core.podcasts.models import Playlist, PodcastEpisode, PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary


def new_playlist_id() -> str:
    return uuid.uuid4().hex


def resolve_playlist(
    library: PodcastLibrary, playlist: Playlist
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """The playlist's current episode list: resolved live from ``rules``
    for a Smart Playlist, or the stored ``items`` (self-healing -- a
    reference to a since-unsubscribed show or vanished episode simply drops
    out) for a manual one."""
    if playlist.kind == "smart":
        return _resolve_smart(library, playlist)
    return _resolve_manual(library, playlist)


def _resolve_manual(
    library: PodcastLibrary, playlist: Playlist
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    result: list[tuple[PodcastShow, PodcastEpisode]] = []
    for item in playlist.items:
        show = library.find_show(item.show_id)
        if show is None:
            continue
        episode = show.find_episode(item.episode_guid)
        if episode is None:
            continue
        result.append((show, episode))
    return result


def _predicates(rules: PlaylistRules) -> list[Callable[[PodcastShow, PodcastEpisode], bool]]:
    """One callable per rule the listener actually set.

    Built as a list rather than a chain of ``continue`` statements because the
    match mode decides how they combine, and ``all()`` or ``any()`` over a list
    of predicates is the whole of that decision. A rule left at its "does not
    narrow" value contributes no predicate at all -- which is what makes
    ``any`` mode behave: an unset rule that quietly matched everything would
    make every ``any`` playlist match every episode.
    """
    checks: list = []

    if rules.episode_status == "unplayed":
        checks.append(lambda _show, episode: not episode.played)
    elif rules.episode_status == "played":
        checks.append(lambda _show, episode: bool(episode.played))
    elif rules.episode_status == "in_progress":
        checks.append(lambda _show, episode: episode.position_ms > 0 and not episode.played)

    if rules.progress == "unstarted":
        checks.append(lambda _show, episode: not episode.position_ms and not episode.played)
    elif rules.progress == "started":
        checks.append(lambda _show, episode: episode.position_ms > 0)
    elif rules.progress == "finished":
        checks.append(lambda _show, episode: bool(episode.played))

    if rules.download_state == "downloaded":
        checks.append(lambda _show, episode: bool(episode.downloaded_path))
    elif rules.download_state == "not_downloaded":
        checks.append(lambda _show, episode: not episode.downloaded_path)

    min_seconds = rules.min_duration_minutes * 60
    if min_seconds > 0:
        checks.append(lambda _show, episode: episode.duration_seconds >= min_seconds)
    max_seconds = rules.max_duration_minutes * 60
    if max_seconds > 0:
        checks.append(lambda _show, episode: 0 < episode.duration_seconds <= max_seconds)

    if rules.published_within_days > 0:
        cutoff = (datetime.now(UTC) - timedelta(days=rules.published_within_days)).timestamp()

        def _recent(_show: PodcastShow, episode: PodcastEpisode) -> bool:
            published = _parse_published(episode.published)
            return published > 0 and published >= cutoff

        checks.append(_recent)

    needle = rules.text_contains.strip().casefold()
    if needle:

        def _mentions(_show: PodcastShow, episode: PodcastEpisode) -> bool:
            haystack = f"{episode.title} {episode.description}".casefold()
            return needle in haystack

        checks.append(_mentions)

    if rules.has_note in ("has_note", "no_note"):
        # The note store is read **once**, not per episode: it is a file, and a
        # rule evaluated over a library of thousands would otherwise open it
        # thousands of times.
        wanted = rules.has_note == "has_note"
        try:
            from quill.core.podcasts.episode_notes import load_episode_notes

            noted = {(note.show_id, note.episode_guid) for note in load_episode_notes()}
        except Exception:  # noqa: BLE001 - an unreadable store means nothing is noted
            noted = set()

        def _noted(show: PodcastShow, episode: PodcastEpisode) -> bool:
            return ((str(show.id), str(episode.guid)) in noted) is wanted

        checks.append(_noted)

    return checks


def _in_scope(library: PodcastLibrary, rules: PlaylistRules, show: PodcastShow) -> bool:
    """Whether *show* is one of the ones this playlist is even about.

    Scope is always AND, whatever the match mode says. "Any of these rules, but
    only within these shows" is what somebody naming a folder means; a folder
    that ORed with the other rules would pull in the whole library the moment a
    second rule matched anything.
    """
    if rules.show_ids and show.id in set(rules.show_ids):
        return True
    if rules.folder_ids:
        from quill.core.podcasts.folder_actions import subtree_show_ids

        for folder_id in rules.folder_ids:
            if show.id in set(subtree_show_ids(library, folder_id)):
                return True
    return not (rules.show_ids or rules.folder_ids)


def _resolve_smart(
    library: PodcastLibrary, playlist: Playlist
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """Re-ask the playlist's question. Sorted, then limited -- in that order.

    "The ten newest" has to be the ten newest, not ten arbitrary matches that
    were afterwards sorted.
    """
    rules = playlist.rules
    checks = _predicates(rules)
    combine = any if rules.match_mode == "any" else all
    pairs: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show in library.shows:
        if not _in_scope(library, rules, show):
            continue
        for episode in show.episodes:
            # No rules set at all matches everything, under either mode: an
            # empty ``any()`` is False, which would make a brand-new playlist
            # look broken rather than unfiltered.
            if checks and not combine(check(show, episode) for check in checks):
                continue
            pairs.append((show, episode))
    key, reverse = _episode_sort_key(rules.sort_mode)
    ordered = sorted(pairs, key=lambda pair: key(pair[1]), reverse=reverse)
    return ordered[: rules.item_limit] if rules.item_limit > 0 else ordered


#: Five smart playlists worth having on day one, as ``(name, rules)``.
#:
#: They exist because a rule builder is a blank page, and a blank page is where
#: most people stop. Each of these is a question somebody actually asks, and
#: each one **arrives editable** -- they are made as ordinary playlists on first
#: run rather than built in, so renaming one, retuning it, or deleting it works
#: exactly the way it does for a playlist somebody wrote themselves. A built-in
#: that cannot be changed is a decision imposed on somebody's library.
STARTERS: tuple[tuple[str, dict[str, object]], ...] = (
    (
        "Continue Listening",
        {"progress": "started", "sort_mode": "date_newest"},
    ),
    (
        "New This Week",
        {
            "published_within_days": 7,
            "episode_status": "unplayed",
            "sort_mode": "date_newest",
        },
    ),
    (
        "Quick Listens",
        {
            "max_duration_minutes": 20,
            "episode_status": "unplayed",
            "sort_mode": "date_newest",
        },
    ),
    (
        "Downloaded and Unplayed",
        {"download_state": "downloaded", "episode_status": "unplayed"},
    ),
    (
        "Long Reads",
        {
            "min_duration_minutes": 60,
            "episode_status": "unplayed",
            "sort_mode": "duration_longest",
        },
    ),
)


def add_starter_playlists(library: PodcastLibrary) -> list[str]:
    """Create any starter playlist the library does not already have.

    Returns the names actually added, so the caller can say what happened. A
    name already present is left completely alone -- including one somebody has
    edited beyond recognition, because the name is theirs now.
    """
    from quill.core.podcasts.models import Playlist
    from quill.core.podcasts.models_playlists import PlaylistRules

    existing = {playlist.name.casefold() for playlist in library.playlists}
    added: list[str] = []
    for name, rules in STARTERS:
        if name.casefold() in existing:
            continue
        library.playlists.append(
            Playlist(
                id=new_playlist_id(),
                name=name,
                kind="smart",
                rules=PlaylistRules.from_dict(dict(rules)),
            )
        )
        added.append(name)
    return added
