"""Where you got to in an episode, as something that can leave this machine.

The gap this closes was named plainly in the Listening Places proposal (§4):
Cast stores an episode's ``position_ms`` inside the monolithic
``podcasts_library.json``, keyed by show id and GUID, and it is **not in the
syncable store at all**. Everything underneath -- the record shape, the merge,
the engine, the folder transport, the crypto -- has been shipped and running for
months, and nothing connected a podcast episode to any of it.

So this is the adapter, and it is work Cast owes itself whether or not any
other app ever participates.

**Identity is the episode's GUID, not the feed plus the GUID.** Two apps
disagree about a feed's URL far more often than one expects: one subscribed
through a FeedBurner redirect and the other through the final host, one has
http and the other https, one carries a tracking prefix. The RSS spec requires
GUIDs to be unique and they survive all of that. This is the one case where
hashing the *file* would be wrong -- a podcast episode has a stable publisher
identity, and two people's downloads of it are not byte-identical.

**Merging is last write, not furthest position.** If you jumped back twenty
minutes to re-hear something and then opened the episode on the laptop, the
furthest position is precisely the wrong answer -- which is why every episode
now carries ``position_updated_at`` and why nothing here compares positions to
decide a winner.

**A pulled position is never playback.** It is written to the library and it
never marks an episode played by itself, never creates a listening session, and
never touches whatever is loaded in the player right now. A position arriving
from another device half a second after somebody pressed play on a restored
mini player must not move them somewhere else.

wx-free, strict-typed, no network. See :mod:`quill.core.sync.listening_places`
for the file format and :mod:`quill.core.sync.places` for the encrypted
machine-to-machine half.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from quill.core.sync.listening_places import PlaceRecord, episode_id

__all__ = [
    "apply_record",
    "collect_records",
    "mark_played",
    "record_for",
    "remember_position",
    "stamp",
]


def stamp() -> str:
    """Now, in the format the record uses: RFC 3339 UTC with a trailing Z.

    Written that way, plain string comparison sorts correctly, so the merge
    needs no date parsing.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def remember_position(episode: Any, position_ms: int) -> None:
    """Move an episode's playhead **and** say when that was decided.

    Every place a position is written goes through here rather than assigning
    ``position_ms`` directly, because a position without a timestamp cannot be
    merged with anything -- and one site that forgets the timestamp is a device
    whose place silently stops travelling.
    """
    episode.position_ms = max(0, int(position_ms))
    episode.position_updated_at = stamp()


def mark_played(episode: Any, played: bool = True) -> None:
    """Mark an episode finished (or not), and stamp the change.

    Finishing zeroes the position, which is how both apps record "done" --
    ``played`` true with ``position_ms`` 0 is what distinguishes "I finished it"
    from "nobody knows where they are".
    """
    episode.played = bool(played)
    if played:
        episode.position_ms = 0
    episode.position_updated_at = stamp()


def record_for(show: Any, episode: Any, *, include_label: bool = True) -> PlaceRecord | None:
    """One episode as a Listening Places record, or ``None`` if it has no place.

    An episode nobody has started and nobody has finished is not a place. Sending
    a record for every episode of every subscribed show would be tens of
    thousands of rows describing nothing.
    """
    entity_id = episode_id(
        str(getattr(episode, "guid", "") or ""), str(getattr(episode, "audio_url", "") or "")
    )
    if not entity_id:
        return None
    position_ms = max(0, int(getattr(episode, "position_ms", 0) or 0))
    played = bool(getattr(episode, "played", False))
    if not position_ms and not played:
        return None
    duration_seconds = int(getattr(episode, "duration_seconds", 0) or 0)
    label = ""
    if include_label:
        show_title = str(getattr(show, "title", "") or "").strip()
        episode_title = str(getattr(episode, "title", "") or "").strip()
        label = f"{show_title}: {episode_title}" if show_title else episode_title
    return PlaceRecord(
        id=entity_id,
        position_ms=position_ms,
        duration_ms=max(0, duration_seconds * 1000),
        played=played,
        updated_at=str(getattr(episode, "position_updated_at", "") or ""),
        label=label,
        feed=str(getattr(show, "feed_url", "") or ""),
    )


def collect_records(library: Any, *, include_labels: bool = True) -> list[PlaceRecord]:
    """Every place this library knows about, ready to write out."""
    records: list[PlaceRecord] = []
    for show in getattr(library, "shows", []) or []:
        for episode in getattr(show, "episodes", []) or []:
            record = record_for(show, episode, include_label=include_labels)
            if record is not None:
                records.append(record)
    return records


def apply_record(library: Any, record: PlaceRecord) -> bool:
    """Apply one incoming record to the library. Returns whether it changed anything.

    An episode the library has never heard of is **not** an error and **not**
    dropped silently by this function -- it simply cannot be applied here, and
    the caller keeps it (see the unmatched backlog in
    :mod:`quill.core.podcasts.radio_listens`, which learned the same lesson the
    hard way). The common case is real: somebody listened on the phone to an
    episode from a feed this machine has not refreshed yet.
    """
    if record.deleted or not record.id.startswith("episode:"):
        return False
    episode = _find_episode(library, record.id)
    if episode is None:
        return False
    local_at = str(getattr(episode, "position_updated_at", "") or "")
    # Ties and missing timestamps resolve to the remote, matching the spec, so
    # behaviour stays predictable when data is incomplete.
    if local_at > record.updated_at:
        return False
    changed = (
        int(getattr(episode, "position_ms", 0) or 0) != record.position_ms
        or bool(getattr(episode, "played", False)) != record.played
    )
    if not changed:
        return False
    episode.position_ms = max(0, record.position_ms)
    episode.played = record.played
    episode.position_updated_at = record.updated_at or stamp()
    return True


def _find_episode(library: Any, entity_id: str) -> Any:
    """The episode whose id hashes to *entity_id*, or ``None``.

    A scan rather than an index: the hash is one-way, so there is nothing to
    look up by. Libraries are thousands of episodes, this runs at most twice per
    sync, and an index would be a second thing to keep in step with the library
    for no measurable gain.
    """
    for show in getattr(library, "shows", []) or []:
        for episode in getattr(show, "episodes", []) or []:
            candidate = episode_id(
                str(getattr(episode, "guid", "") or ""),
                str(getattr(episode, "audio_url", "") or ""),
            )
            if candidate == entity_id:
                return episode
    return None
