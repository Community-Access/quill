"""What an item in a Lineup *is*: a kind and the key its owner already uses.

A Lineup never copies a station or an episode. It stores a reference, and the
reference is the identity that thing already has somewhere in Radio or Cast --
the Favorites key for a station, the browse ``node_id`` for a place, the
``(show_id, guid)`` pair Cast's Play Queue uses for an episode. Inventing a new
identity would mean a second way for the same thing to be "the same", which is
how lists end up with duplicates nobody can explain.

Resolving a reference answers one of three things, and the difference between
the last two is the most important rule in the whole feature: an item whose
owner *could not be asked* is never treated as gone (see
:mod:`quill.core.lineups.merge`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# -- kinds ------------------------------------------------------------------------

KIND_STATION = "station"
KIND_PLACE = "place"
KIND_SHOW = "show"
KIND_EPISODE = "episode"
KIND_YT_VIDEO = "yt_video"
KIND_YT_PLAYLIST = "yt_playlist"
KIND_YT_CHANNEL = "yt_channel"
KIND_LOCAL = "local"
KIND_RECORDING = "recording"

KINDS: tuple[str, ...] = (
    KIND_STATION,
    KIND_PLACE,
    KIND_SHOW,
    KIND_EPISODE,
    KIND_YT_VIDEO,
    KIND_YT_PLAYLIST,
    KIND_YT_CHANNEL,
    KIND_LOCAL,
    KIND_RECORDING,
)

#: The kind as a row says it, lower case because it follows the name:
#: "BBC Radio 4, station".
KIND_LABELS: dict[str, str] = {
    KIND_STATION: "station",
    KIND_PLACE: "place",
    KIND_SHOW: "podcast",
    KIND_EPISODE: "episode",
    KIND_YT_VIDEO: "YouTube video",
    KIND_YT_PLAYLIST: "YouTube playlist",
    KIND_YT_CHANNEL: "YouTube channel",
    KIND_LOCAL: "local media",
    KIND_RECORDING: "recording",
}

#: The kind as a rule's sentence starts: "Podcast episodes in the News folder".
KIND_PLURALS: dict[str, str] = {
    KIND_STATION: "Radio stations",
    KIND_PLACE: "Saved places",
    KIND_SHOW: "Podcasts I follow",
    KIND_EPISODE: "Podcast episodes",
    KIND_YT_VIDEO: "YouTube videos",
    KIND_YT_PLAYLIST: "YouTube playlists",
    KIND_YT_CHANNEL: "YouTube channels",
    KIND_LOCAL: "Local media",
    KIND_RECORDING: "Recordings",
}

#: Kinds whose items are heard to an end, so "Until finished" can mean something.
FINISHABLE_KINDS: frozenset[str] = frozenset({
    KIND_EPISODE,
    KIND_YT_VIDEO,
    KIND_LOCAL,
    KIND_RECORDING,
})

#: The separator inside a composite key (episode, local media). A tab cannot
#: occur in a Cast show id, a feed guid or a playlist id.
KEY_SEPARATOR = "\t"


@dataclass(frozen=True, slots=True, order=True)
class ItemRef:
    """A reference to one thing Radio or Cast already knows about."""

    kind: str
    key: str

    @property
    def token(self) -> str:
        """The reference as one string, ``kind:key``, for logs and stored maps."""
        return f"{self.kind}:{self.key}"

    @classmethod
    def from_token(cls, token: str) -> ItemRef | None:
        """The reference a :attr:`token` came from, or ``None`` for nonsense."""
        kind, sep, key = str(token or "").partition(":")
        if not sep or not key or kind not in KINDS:
            return None
        return cls(kind, key)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "key": self.key}

    @classmethod
    def from_dict(cls, data: object) -> ItemRef | None:
        """A stored reference, or ``None`` when the entry is not one.

        An unknown kind is *kept*: a newer build may know it, and dropping it
        would rewrite somebody's order on a downgrade.
        """
        if not isinstance(data, dict):
            return None
        kind = str(data.get("kind", "") or "").strip()
        key = str(data.get("key", "") or "")
        if not kind or not key:
            return None
        return cls(kind, key)


def episode_ref(show_id: str, guid: str) -> ItemRef:
    """The reference for a Cast episode: the same pair Cast's queue uses."""
    return ItemRef(KIND_EPISODE, f"{show_id}{KEY_SEPARATOR}{guid}")


def split_key(ref: ItemRef) -> tuple[str, str]:
    """A composite key's two halves; the second is ``""`` for a simple key."""
    first, _sep, second = ref.key.partition(KEY_SEPARATOR)
    return first, second


def local_ref(playlist_id: str, item_id: int) -> ItemRef:
    """The reference for a Local Media item: its playlist id and stable item id."""
    return ItemRef(KIND_LOCAL, f"{playlist_id}{KEY_SEPARATOR}{int(item_id)}")


# -- resolution -----------------------------------------------------------------


class Presence(Enum):
    """What asking an item's owner about it answered."""

    #: It exists and its facts are known.
    PRESENT = "present"
    #: Its owner says it no longer exists (unfollowed, deleted).
    MISSING = "missing"
    #: Its owner could not be asked (a file unreadable, a store not loaded).
    UNAVAILABLE = "unavailable"
    #: Its kind has no complete list to look in -- a station found in a directory
    #: search, a video from a search result -- so "not found" proves nothing.
    #: Treated like present for keeping, played from the row's own play data.
    UNLISTED = "unlisted"


__all__ = [
    "FINISHABLE_KINDS",
    "KEY_SEPARATOR",
    "KINDS",
    "KIND_EPISODE",
    "KIND_LABELS",
    "KIND_LOCAL",
    "KIND_PLACE",
    "KIND_PLURALS",
    "KIND_RECORDING",
    "KIND_SHOW",
    "KIND_STATION",
    "KIND_YT_CHANNEL",
    "KIND_YT_PLAYLIST",
    "KIND_YT_VIDEO",
    "ItemRef",
    "Presence",
    "episode_ref",
    "local_ref",
    "split_key",
]
