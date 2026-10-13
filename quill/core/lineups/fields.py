"""What a rule can ask about each kind of item, and the facts each item carries.

Every source (:mod:`quill.core.lineups.sources`) turns the things it knows into
:class:`ItemFacts`: the reference, what a row says (name, length, source), and a
flat map of *facts* a rule can test. Rules never look at a ``RadioStation`` or a
``PodcastEpisode`` directly, which is what lets one engine serve nine kinds and
two apps, and what lets every rule be tested without either app's models.

A fact is one of four shapes, and :data:`FIELDS` says which per field:

* **text** -- a string; tested with contains, starts with, wildcard and so on.
* **number** -- an ``int`` or ``None``; ``None`` means "the owner did not say",
  and a missing fact never matches a number test (Cast's rule, kept).
* **yes/no** -- a ``bool``.
* **list** -- a tuple of strings (tags, labels); a text test asks about any one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from quill.core.lineups.refs import (
    KIND_EPISODE,
    KIND_LOCAL,
    KIND_PLACE,
    KIND_RECORDING,
    KIND_SHOW,
    KIND_STATION,
    KIND_YT_CHANNEL,
    KIND_YT_PLAYLIST,
    KIND_YT_VIDEO,
    ItemRef,
)

TEXT = "text"
NUMBER = "number"
YESNO = "yesno"
LIST = "list"

Fact = str | int | bool | tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class Field:
    """One thing a rule can test."""

    id: str
    label: str
    type: str
    #: For a number, the unit a value is typed in, said after it: "minutes".
    unit: str = ""


def _f(fid: str, label: str, ftype: str, unit: str = "") -> Field:
    return Field(fid, label, ftype, unit)


_NAME = _f("name", "Name", TEXT)
_TITLE = _f("name", "Title", TEXT)
_LENGTH = _f("length", "Length", NUMBER, "minutes")
_SOURCE = _f("source", "Source", TEXT)

#: Every field, per kind, in the order the rule editor offers them.
FIELDS: dict[str, tuple[Field, ...]] = {
    KIND_EPISODE: (
        _TITLE,
        _f("show", "Podcast", TEXT),
        _f("folder", "Folder", TEXT),
        _f("labels", "Label", LIST),
        _f("age", "Age", NUMBER, "days"),
        _LENGTH,
        _f("played", "Played", YESNO),
        _f("in_progress", "Started but not finished", YESNO),
        _f("percent_heard", "Percent heard", NUMBER, "percent"),
        _f("downloaded", "Downloaded", YESNO),
        _f("season", "Season", NUMBER),
        _f("number", "Episode number", NUMBER),
        _f("episode_type", "Episode type", TEXT),
        _f("days_since_played", "Days since last played", NUMBER, "days"),
    ),
    KIND_SHOW: (
        _TITLE,
        _f("folder", "Folder", TEXT),
        _f("labels", "Label", LIST),
        _f("favorite", "Favorite", YESNO),
        _f("paused", "Paused", YESNO),
        _f("language", "Language", TEXT),
        _f("category", "Category", TEXT),
        _f("unplayed", "Unplayed episodes", NUMBER),
        _f("newest_age", "Newest episode age", NUMBER, "days"),
    ),
    KIND_STATION: (
        _NAME,
        _f("folder", "Favorites folder", TEXT),
        _f("favorite", "In Favorites", YESNO),
        _f("my_tags", "My tag", LIST),
        _f("tags", "Directory tag", LIST),
        _f("country", "Country", TEXT),
        _f("language", "Language", TEXT),
        _f("codec", "Codec", TEXT),
        _f("bitrate", "Bitrate", NUMBER, "kilobits"),
        _SOURCE,
        _f("listened", "Time listened", NUMBER, "minutes"),
        _f("recent", "In recently played", YESNO),
    ),
    KIND_PLACE: (
        _NAME,
        _SOURCE,
        _f("folder", "Favorites folder", TEXT),
    ),
    KIND_YT_VIDEO: (
        _TITLE,
        _f("channel", "Channel", TEXT),
        _LENGTH,
        _f("live", "Live", YESNO),
        _f("saved", "Saved by me", YESNO),
        # No Age: a saved video carries no date, so a test on it could never match.
    ),
    KIND_YT_PLAYLIST: (
        _TITLE,
        _f("channel", "Channel", TEXT),
        _f("count", "Number of videos", NUMBER),
    ),
    KIND_YT_CHANNEL: (
        _NAME,
        _f("alerts", "New-video alerts on", YESNO),
    ),
    KIND_LOCAL: (
        _TITLE,
        _f("artist", "Artist", TEXT),
        _f("album", "Album", TEXT),
        _f("playlist", "Playlist", TEXT),
        _LENGTH,
        _f("added_age", "Days since added", NUMBER, "days"),
        _f("video", "Is a video", YESNO),
    ),
    KIND_RECORDING: (
        _NAME,
        _LENGTH,
        _f("age", "Age", NUMBER, "days"),
        _f("status", "Status", TEXT),
    ),
}

#: The fact a rule's "at most N per ..." cap groups by, per kind. A kind with no
#: entry has no natural grouping and offers no per-group cap.
GROUP_FIELDS: dict[str, tuple[str, str]] = {
    KIND_EPISODE: ("show", "podcast"),
    KIND_YT_VIDEO: ("channel", "channel"),
    KIND_LOCAL: ("album", "album"),
    KIND_STATION: ("folder", "folder"),
}


def fields_for(kind: str) -> tuple[Field, ...]:
    """The fields a rule over *kind* can test; empty for an unknown kind."""
    return FIELDS.get(kind, ())


def field_for(kind: str, field_id: str) -> Field | None:
    """One field of *kind*, or ``None`` when this build does not know it."""
    for candidate in fields_for(kind):
        if candidate.id == field_id:
            return candidate
    return None


@dataclass(frozen=True, slots=True)
class ItemFacts:
    """One item as a source sees it right now.

    ``length_seconds`` of 0 means unknown; ``finished`` is the owner's own record
    (played to the end, watched); ``position_fraction`` is how much of it has
    been heard, 0.0 to 1.0, for "Until finished" with a percentage.
    """

    ref: ItemRef
    name: str
    facts: Mapping[str, Fact] = field(default_factory=dict)
    length_seconds: int = 0
    source: str = ""
    live: bool = False
    finished: bool = False
    position_fraction: float = 0.0
    #: Seconds since the epoch the owner says it appeared (published, added),
    #: or 0 when unknown. Drives "newest first".
    published_at: float = 0.0
    #: What the owner needs to play it (its own serialised form), carried for
    #: kinds the host plays from a record -- a station, a video. Opaque here.
    payload: Mapping[str, object] | None = None

    def fact(self, field_id: str) -> Fact:
        if field_id == "name":
            return self.name
        if field_id == "length":
            return self.length_seconds // 60 if self.length_seconds > 0 else None
        if field_id == "source" and "source" not in self.facts:
            return self.source
        if field_id == "live" and "live" not in self.facts:
            return self.live
        return self.facts.get(field_id)


__all__ = [
    "FIELDS",
    "GROUP_FIELDS",
    "LIST",
    "NUMBER",
    "TEXT",
    "YESNO",
    "Fact",
    "Field",
    "ItemFacts",
    "field_for",
    "fields_for",
]
