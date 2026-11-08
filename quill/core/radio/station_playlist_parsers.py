"""Parsers for the station playlists in :mod:`quill.core.radio.station_playlist`.

One pure function per source, each turning that service's answer into
:class:`PlayedSong` rows, newest first, and each tolerant of junk: a reply that
is not the expected shape yields no rows, never an exception. Split from
``station_playlist`` under GATE-11.

The source list and its edge cases come from BlindRadio by serrebidev (MIT),
crates/blindradio-core/src/sources/played.rs; the parsing was written against
live responses fetched on 2026-11-07, not copied.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from quill.core import safe_xml


@dataclass(frozen=True, slots=True)
class PlayedSong:
    """One song from a station's published list."""

    title: str
    artist: str = ""
    #: When it started, in UTC, when the source says.
    started_at: datetime | None = None
    #: The source's own words for when, kept when it gives no clock time (the
    #: BBC's "3 Minutes Ago"); ``started_at`` is then only an estimate.
    when_label: str = ""
    #: True for the row the source marks as on the air now.
    is_current: bool = False

    def display(self) -> str:
        """The row's words, "Title by Artist", the same shape as Song History's."""
        if self.title and self.artist:
            return f"{self.title} by {self.artist}"
        return self.title or self.artist

    def clip_text(self) -> str:
        """What Copy and the Clip Library keep: the display line."""
        return self.display()


# --- times (pure) -----------------------------------------------------------

_TIME_RE = re.compile(
    r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d):(\d\d)(?:\.\d+)?\s*(Z|[+-]\d\d:?\d\d)?$"
)


def parse_time(text: object) -> datetime | None:
    """A UTC time from the shapes these APIs use, or None (pure).

    ``2026-11-08 02:41:56.848+00:00`` (Live365), ``2026-11-08 03:19:26 +0100``
    (laut.fm), ``2026-11-07T18:42:15-08:00`` (KEXP); no zone means UTC.
    """
    match = _TIME_RE.match(str(text or "").strip())
    if not match:
        return None
    year, month, day, hour, minute, second = (int(match.group(i)) for i in range(1, 7))
    zone = match.group(7) or "Z"
    offset = timedelta(0)
    if zone != "Z":
        digits = zone[1:].replace(":", "")
        offset = timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        if zone.startswith("-"):
            offset = -offset
    try:
        moment = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except ValueError:
        return None
    return moment - offset


def _from_epoch(value: object, *, millis: bool) -> datetime | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    try:
        return datetime.fromtimestamp(number / 1000 if millis else number, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


_BBC_AGO = re.compile(r"^(\d+)\s+(minute|hour)s?\s+ago$", re.IGNORECASE)


def _bbc_when(label: str, now: datetime) -> tuple[datetime | None, str, bool]:
    """(estimated start, phrase to show, is it on now) from the BBC's label."""
    text = " ".join(label.split())
    if text.lower() == "now playing":
        return now, "", True
    match = _BBC_AGO.match(text)
    if not match:
        return None, text.lower(), False
    count = int(match.group(1))
    delta = (
        timedelta(minutes=count) if match.group(2).lower() == "minute" else timedelta(hours=count)
    )
    return now - delta, text.lower(), False


# --- parsers (pure) ---------------------------------------------------------


def _text(value: object) -> str:
    return " ".join(str(value or "").split()) if value is not None else ""


def _song(
    title: object,
    artist: object,
    *,
    started_at: datetime | None = None,
    when_label: str = "",
    is_current: bool = False,
) -> PlayedSong | None:
    """A row, or None when the source gave no title (a break, a station id)."""
    clean_title, clean_artist = _text(title), _text(artist)
    if not clean_title:
        return None
    return PlayedSong(
        title=clean_title,
        artist=clean_artist,
        started_at=started_at,
        when_label=when_label,
        is_current=is_current,
    )


def _json(payload: str) -> object:
    try:
        return json.loads(payload)
    except (TypeError, ValueError):
        return None


def _newest_first(songs: list[PlayedSong]) -> tuple[PlayedSong, ...]:
    """Newest first by start time; rows with no time keep the source's order."""
    floor = datetime.min.replace(tzinfo=UTC)
    indexed = list(enumerate(songs))
    indexed.sort(key=lambda pair: (pair[1].started_at or floor, -pair[0]), reverse=True)
    if all(song.started_at is None for song in songs):
        return tuple(songs)
    return tuple(song for _index, song in indexed)


def parse_azuracast(payload: str, shortcode: str) -> tuple[PlayedSong, ...]:
    """``now_playing`` then ``song_history`` from AzuraCast's now-playing answer.

    Empty unless the answer describes the station asked about: a server that
    is not AzuraCast, or one that maps the path differently, says nothing.
    """
    data = _json(payload)
    if not isinstance(data, dict):
        return ()
    station = data.get("station")
    if not isinstance(station, dict):
        return ()
    if str(station.get("shortcode") or "").lower() != shortcode.lower():
        return ()
    rows: list[tuple[object, bool]] = []
    current = data.get("now_playing")
    if isinstance(current, dict):
        rows.append((current, True))
    history = data.get("song_history")
    if isinstance(history, list):
        rows.extend((entry, False) for entry in history)
    songs: list[PlayedSong] = []
    for entry, is_current in rows:
        if not isinstance(entry, dict) or not isinstance(entry.get("song"), dict):
            continue
        song = entry["song"]
        title, artist = song.get("title"), song.get("artist")
        if not _text(title):
            # Some stations send only the combined "Artist - Title" text.
            title, artist = song.get("text"), ""
        played = _song(
            title,
            artist,
            started_at=_from_epoch(entry.get("played_at"), millis=False),
            is_current=is_current,
        )
        if played is not None:
            songs.append(played)
    return _newest_first(songs)


def parse_kexp(payload: str) -> tuple[PlayedSong, ...]:
    """KEXP's plays: track plays only, airbreaks and the like skipped."""
    data = _json(payload)
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return ()
    songs: list[PlayedSong] = []
    for entry in results:
        if not isinstance(entry, dict) or entry.get("play_type") != "trackplay":
            continue
        played = _song(
            entry.get("song"), entry.get("artist"), started_at=parse_time(entry.get("airdate"))
        )
        if played is not None:
            songs.append(played)
    return _newest_first(songs)


def parse_bbc(payload: str, *, now: datetime | None = None) -> tuple[PlayedSong, ...]:
    """The BBC's latest music segments. ``primary`` is the artist, ``secondary``
    the title; the time is only ever a phrase, kept as the row's when-label."""
    data = _json(payload)
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return ()
    moment = now or datetime.now(tz=UTC)
    songs: list[PlayedSong] = []
    for entry in rows:
        if not isinstance(entry, dict) or entry.get("segment_type") != "music":
            continue
        titles = entry.get("titles")
        offset = entry.get("offset")
        if not isinstance(titles, dict):
            continue
        if not isinstance(offset, dict):
            offset = {}
        started, label, on_now = _bbc_when(_text(offset.get("label")), moment)
        played = _song(
            titles.get("secondary"),
            titles.get("primary"),
            started_at=started,
            when_label=label,
            is_current=on_now or offset.get("now_playing") is True,
        )
        if played is not None:
            songs.append(played)
    return tuple(songs)  # already newest first, and the times are estimates


def parse_radio_paradise(payload: str) -> tuple[PlayedSong, ...]:
    """Radio Paradise's ``nowplaying_list_v2022``: ``play_time`` is milliseconds."""
    data = _json(payload)
    rows = data.get("song") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return ()
    songs: list[PlayedSong] = []
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        played = _song(
            entry.get("title"),
            entry.get("artist"),
            started_at=_from_epoch(entry.get("play_time"), millis=True),
        )
        if played is not None:
            songs.append(played)
    return _newest_first(songs)


#: Live365 lists its own inserts as tracks by "Live365" ("120 Second Ad Break").
_LIVE365_HOUSE_ARTIST = "live365"


def parse_live365(payload: str) -> tuple[PlayedSong, ...]:
    """Live365's ``current-track`` then ``last-played``, its ad breaks left out."""
    data = _json(payload)
    if not isinstance(data, dict):
        return ()
    rows: list[tuple[object, bool]] = []
    if isinstance(data.get("current-track"), dict):
        rows.append((data["current-track"], True))
    last = data.get("last-played")
    if isinstance(last, list):
        rows.extend((entry, False) for entry in last)
    songs: list[PlayedSong] = []
    for entry, is_current in rows:
        if not isinstance(entry, dict):
            continue
        if _text(entry.get("artist")).lower() == _LIVE365_HOUSE_ARTIST:
            continue
        played = _song(
            entry.get("title"),
            entry.get("artist"),
            started_at=parse_time(entry.get("start")),
            is_current=is_current,
        )
        if played is not None:
            songs.append(played)
    return _newest_first(songs)


def parse_laut_fm(payload: str) -> tuple[PlayedSong, ...]:
    """laut.fm's ``last_songs``: a list, the artist nested under ``artist.name``."""
    data = _json(payload)
    if not isinstance(data, list):
        return ()
    songs: list[PlayedSong] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        artist = entry.get("artist")
        played = _song(
            entry.get("title"),
            artist.get("name") if isinstance(artist, dict) else "",
            started_at=parse_time(entry.get("started_at")),
        )
        if played is not None:
            songs.append(played)
    return _newest_first(songs)


def parse_triton(payload: str) -> tuple[PlayedSong, ...]:
    """Triton's ``<nowplaying-info-list>``: ``cue_title``, ``track_artist_name``
    and ``cue_time_start`` (milliseconds) as ``<property name=...>`` rows."""
    try:
        root = safe_xml.fromstring(payload)
    except (safe_xml.ParseError, safe_xml.UnsafeXMLError):
        return ()
    songs: list[PlayedSong] = []
    for info in root.iter():
        if info.tag.rsplit("}", 1)[-1] != "nowplaying-info":
            continue
        fields: dict[str, str] = {}
        for prop in info:
            if prop.tag.rsplit("}", 1)[-1] == "property":
                fields.setdefault(prop.get("name", ""), (prop.text or "").strip())
        played = _song(
            fields.get("cue_title"),
            fields.get("track_artist_name"),
            started_at=_from_epoch(fields.get("cue_time_start"), millis=True),
        )
        if played is not None:
            songs.append(played)
    return _newest_first(songs)
