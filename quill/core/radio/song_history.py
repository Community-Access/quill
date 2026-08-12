"""A rolling log of the songs a station has played, persisted as atomic JSON.

What's Playing (Ctrl+T) is a point in time: it reads the stream's current title
and forgets it. This module is the memory behind it -- every title *change* the
existing thirty-second poll observes is recorded against the station that was
playing, so "what was that song twenty minutes ago?" has an answer.

Design notes that matter:

* **Deduplicated on repeat, not on content.** The poll sees the same song
  roughly six times during a three-minute track. A naive log would therefore be
  five parts noise; :meth:`SongHistory.record` folds a repeat of the station's
  most recent song into that entry, advancing ``last_heard`` and
  ``play_count``. The same song played again an hour later is a genuinely new
  entry, because by then it is no longer the most recent one.
* **Capped per station, not globally.** One station left playing all day must
  not evict another station's afternoon. Each station keeps its own
  :data:`MAX_PER_STATION` newest entries, and the number of stations is capped
  separately.
* **Titles only, never audio.** This records the text a station broadcasts
  about itself. Nothing here touches the stream.

wx-free and strict-typed: every rule above is directly unit-testable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from quill.core.radio.now_playing import NowPlaying, parse_now_playing

__all__ = [
    "SongPlay",
    "SongHistory",
    "MAX_PER_STATION",
    "MAX_STATIONS",
    "load_song_history",
    "save_song_history",
    "build_song_background_prompt",
    "BACKGROUND_DISCLAIMER",
]

_FILE_NAME = "radio_song_history.json"

#: Songs kept per station. About a full day of a three-minute rotation, which is
#: the horizon "what was that earlier?" actually spans.
MAX_PER_STATION = 200

#: Stations kept. The least-recently-heard station is dropped first, so a
#: long-abandoned station cannot hold the file open forever.
MAX_STATIONS = 50

#: Shown wherever model-generated background is displayed. The listener must
#: never mistake a model's recollection of a song for the station's own metadata
#: -- especially here, where the two sit inches apart in the same dialog.
BACKGROUND_DISCLAIMER = (
    "Written by an AI model, not by the station. It may be wrong or out of date."
)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass(slots=True)
class SongPlay:
    """One song heard on one station."""

    title: str
    artist: str = ""
    #: The raw broadcast title, kept verbatim so a listener can see exactly what
    #: the station sent when the parse produced something odd.
    raw: str = ""
    first_heard: str = ""
    last_heard: str = ""
    #: How many separate times this entry has been observed as the current song.
    #: Only bumped while it stays the station's most recent entry (see record).
    play_count: int = 1

    def display(self) -> str:
        """The one-line label for a list control ("Song by Artist")."""
        if self.title and self.artist:
            return f"{self.title} by {self.artist}"
        return self.title or self.artist or self.raw

    def clip_text(self) -> str:
        """The text copied or sent to the Clip Library.

        The display line, never the raw broadcast noise: someone pasting into a
        lyrics or store search wants "YOUR SONG by Elton John", not
        ``title="YOUR SONG",artist="Elton John",url="song_spot=...``.
        """
        return self.display()

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "artist": self.artist,
            "raw": self.raw,
            "first_heard": self.first_heard,
            "last_heard": self.last_heard,
            "play_count": self.play_count,
        }

    @classmethod
    def from_dict(cls, raw: object) -> SongPlay | None:
        if not isinstance(raw, dict):
            return None
        title = str(raw.get("title", "") or "")
        artist = str(raw.get("artist", "") or "")
        raw_text = str(raw.get("raw", "") or "")
        if not (title or artist or raw_text):
            return None
        try:
            count = int(raw.get("play_count", 1) or 1)
        except (TypeError, ValueError):
            count = 1
        return cls(
            title=title,
            artist=artist,
            raw=raw_text,
            first_heard=str(raw.get("first_heard", "") or ""),
            last_heard=str(raw.get("last_heard", "") or ""),
            play_count=max(1, count),
        )


@dataclass(slots=True)
class StationSongs:
    """One station's log, newest first."""

    station_key: str
    station_name: str = ""
    songs: list[SongPlay] = field(default_factory=list)
    #: When this station last had a song recorded -- the eviction order when
    #: MAX_STATIONS is reached.
    last_active: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "station_key": self.station_key,
            "station_name": self.station_name,
            "last_active": self.last_active,
            "songs": [song.to_dict() for song in self.songs],
        }

    @classmethod
    def from_dict(cls, raw: object) -> StationSongs | None:
        if not isinstance(raw, dict):
            return None
        key = str(raw.get("station_key", "") or "")
        if not key:
            return None
        entry = cls(
            station_key=key,
            station_name=str(raw.get("station_name", "") or ""),
            last_active=str(raw.get("last_active", "") or ""),
        )
        songs = raw.get("songs")
        for item in songs if isinstance(songs, list) else []:
            song = SongPlay.from_dict(item)
            if song is not None:
                entry.songs.append(song)
        del entry.songs[MAX_PER_STATION:]
        return entry


def _is_noise(now_playing: NowPlaying, station_name: str) -> bool:
    """Whether this parsed title is worth keeping.

    Plenty of streams send their own station name, a bare "Live", or an advert
    marker as the "current track". Logging those produces a history of the
    station talking about itself, which buries the songs the listener actually
    wants to find again.
    """
    title = now_playing.title.strip()
    artist = now_playing.artist.strip()
    raw = now_playing.raw.strip()
    if not (title or artist or raw):
        return True
    candidate = (title or raw).casefold()
    if station_name and candidate == station_name.strip().casefold():
        return True
    return candidate in {
        "live",
        "unknown",
        "n/a",
        "advertisement",
        "advert",
        "ad break",
        "commercial",
    }


@dataclass(slots=True)
class SongHistory:
    """Every station's song log."""

    stations: list[StationSongs] = field(default_factory=list)

    def find(self, station_key: str) -> StationSongs | None:
        for station in self.stations:
            if station.station_key == station_key:
                return station
        return None

    def record(
        self,
        station_key: str,
        station_name: str,
        stream_title: str,
        *,
        when: str = "",
    ) -> SongPlay | None:
        """Note that *station_key* is currently playing *stream_title*.

        Returns the entry that was created, or ``None`` when nothing was
        recorded -- an empty or noise title, or a repeat of the song already at
        the front of this station's log (whose ``last_heard`` and ``play_count``
        are updated in place instead).
        """
        if not station_key:
            return None
        now_playing = parse_now_playing(stream_title)
        if _is_noise(now_playing, station_name):
            return None
        stamp = when or _now_iso()

        station = self.find(station_key)
        if station is None:
            station = StationSongs(station_key=station_key, station_name=station_name)
            self.stations.append(station)
        elif station_name:
            # A station renamed in the directory should not fork its own log.
            station.station_name = station_name
        station.last_active = stamp

        title = now_playing.title.strip() or now_playing.raw.strip()
        artist = now_playing.artist.strip()
        if station.songs:
            head = station.songs[0]
            if head.title == title and head.artist == artist:
                head.last_heard = stamp
                head.play_count += 1
                self._evict_stations()
                return None

        song = SongPlay(
            title=title,
            artist=artist,
            raw=now_playing.raw.strip(),
            first_heard=stamp,
            last_heard=stamp,
        )
        station.songs.insert(0, song)
        del station.songs[MAX_PER_STATION:]
        self._evict_stations()
        return song

    def _evict_stations(self) -> None:
        """Keep at most MAX_STATIONS, dropping the least recently active."""
        if len(self.stations) <= MAX_STATIONS:
            return
        self.stations.sort(key=lambda s: s.last_active, reverse=True)
        del self.stations[MAX_STATIONS:]

    def songs_for(self, station_key: str) -> list[SongPlay]:
        station = self.find(station_key)
        return list(station.songs) if station is not None else []

    def known_stations(self) -> list[StationSongs]:
        """Stations that have a log, most recently active first."""
        return sorted(
            (s for s in self.stations if s.songs),
            key=lambda s: s.last_active,
            reverse=True,
        )

    def clear_station(self, station_key: str) -> None:
        self.stations = [s for s in self.stations if s.station_key != station_key]

    def clear_all(self) -> None:
        self.stations = []


def build_song_background_prompt(song: SongPlay, station_name: str = "") -> str:
    """The provider-neutral prompt asking for background on one song (pure).

    Deliberately plain and provider-agnostic -- no vendor-specific system-prompt
    conventions -- because the configured provider may be a cloud model or a
    local Ollama one. It also tells the model to say when it does not know,
    which is the difference between a useful answer and a confident invention
    about a song that may be a local band's demo.
    """
    parts = [f"Song: {song.title}" if song.title else ""]
    if song.artist:
        parts.append(f"Artist: {song.artist}")
    if station_name:
        parts.append(f"Heard on the radio station: {station_name}")
    known = "\n".join(part for part in parts if part)
    return (
        "Give a short, friendly background on this song for someone who just "
        "heard it on the radio. Cover the artist, roughly when it came out, the "
        "album if you know it, and one or two genuinely interesting facts.\n\n"
        "Keep it under 150 words and write plain prose with no headings or "
        "bullet points, because it will be read aloud by a screen reader.\n\n"
        "If you are not confident you know this particular song, say so plainly "
        "instead of guessing.\n\n" + known
    )


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_song_history(data_dir: Path) -> SongHistory:
    """Read the song log (an absent or broken file reads as empty)."""
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return SongHistory()
    history = SongHistory()
    entries = raw.get("stations") if isinstance(raw, dict) else None
    for item in entries if isinstance(entries, list) else []:
        station = StationSongs.from_dict(item)
        if station is not None:
            history.stations.append(station)
    del history.stations[MAX_STATIONS:]
    return history


def save_song_history(data_dir: Path, history: SongHistory) -> None:
    """Persist the song log atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        _store_path(data_dir),
        {"stations": [station.to_dict() for station in history.stations]},
    )
