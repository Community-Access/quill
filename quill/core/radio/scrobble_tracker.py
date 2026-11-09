"""Which songs the listener actually heard, and for how long: the scrobble rule.

Scrobbling sends the songs you hear to ListenBrainz, last.fm or Libre.fm. This
module decides *what counts as heard*. Nothing here touches the network.

**The rule is one minute.** last.fm's own rule is "longer than 30 seconds, and
played for half its length or four minutes, whichever comes first", and
ListenBrainz asks for the same. Both rules need the song's length, and a radio
station almost never says how long a song is. So Quill Radio uses BlindRadio's
rule instead: a song counts once you have heard a minute of it. That is
shorter than four minutes and longer than thirty seconds, so it never sends a
song last.fm would call too short, and it never waits for a length nobody knows.

**Heard, not broadcast.** A station's title changes when the song is *sent*.
With the time-shift buffer, you may hear it ten minutes later, or pause halfway
through. So titles are kept as a broadcast timeline, and the clock that counts
is the *playhead*: the moment in that timeline you are hearing now, which is
"now" minus how far behind live you are. Time only counts while the playhead
moves forward inside one song, so a pause adds nothing, rewinding adds
nothing, and jumping ahead adds no more than the real time that passed. The
listen is stamped with the moment you started hearing the song, not the moment
the station played it.

**Not every title is a song.** Station names, "Live", advert markers
(:func:`quill.core.radio.song_history.is_noise_title`) and titles with no artist
are never sent. A noise title still *ends* the song before it.

The idea, and the one-minute rule, come from BlindRadio by serrebidev (MIT),
``crates/blindradio-core/src/scrobble.rs`` and its use in the app; no code was
copied. wx-free, strict-typed, and every rule runs against a fake clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.radio.now_playing import parse_now_playing
from quill.core.radio.song_history import is_noise_title

#: Seconds of a song that must be heard before it is sent. See the module text
#: for why this is not last.fm's half-or-four-minutes rule.
MIN_HEARD_SECONDS = 60.0

#: How far back the broadcast timeline is kept: past the longest time-shift
#: buffer Preferences offers (five hours), so a song paused at the far end of
#: the buffer still has its title when you get back to it.
TIMELINE_SECONDS = 6 * 60 * 60

#: And never more segments than this, whatever the clock says.
MAX_SEGMENTS = 400


@dataclass(frozen=True, slots=True)
class Listen:
    """One song heard, in the shape every scrobbling service needs."""

    artist: str
    title: str
    #: Unix seconds: when the listener started hearing it.
    listened_at: int
    album: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "artist": self.artist,
            "title": self.title,
            "listened_at": self.listened_at,
            "album": self.album,
        }

    @classmethod
    def from_dict(cls, raw: object) -> Listen | None:
        if not isinstance(raw, dict):
            return None
        artist = str(raw.get("artist", "") or "").strip()
        title = str(raw.get("title", "") or "").strip()
        try:
            when = int(raw.get("listened_at", 0) or 0)
        except (TypeError, ValueError):
            return None
        if not (artist and title and when > 0):
            return None
        return cls(artist, title, when, str(raw.get("album", "") or "").strip())


def song_from_title(stream_title: str, station_name: str = "") -> Listen | None:
    """The artist and title in a stream title, or None when it is not a song.

    ``listened_at`` is 0 here; the tracker stamps it. Pure.
    """
    if not stream_title.strip() or is_noise_title(stream_title, station_name):
        return None
    parsed = parse_now_playing(stream_title)
    artist = parsed.artist.strip()
    title = parsed.title.strip()
    if not (artist and title):
        return None
    return Listen(artist, title, 0, parsed.extras.get("album", "").strip())


@dataclass(slots=True)
class _Segment:
    #: Wall-clock seconds the station started sending this title.
    start: float
    #: The song, or None for a title that is not one (it still ends the last).
    song: Listen | None


@dataclass(slots=True)
class _Hearing:
    segment: _Segment
    started_at: float
    last_wall: float
    last_playhead: float
    heard: float = 0.0
    sent: bool = False


@dataclass(slots=True)
class Tick:
    """What one tick found: songs now heard long enough, and a new song begun."""

    heard: list[Listen] = field(default_factory=list)
    #: The song that just started being heard, for "now playing"; else None.
    started: Listen | None = None


class HeardTracker:
    """The broadcast timeline of one station, and the song under the playhead.

    Two inputs, both from the UI thread: :meth:`note_title` whenever the
    station's title changes, and :meth:`tick` every few seconds while it plays.
    """

    def __init__(self) -> None:
        self._station = ""
        self._segments: list[_Segment] = []
        self._hearing: _Hearing | None = None

    @property
    def station(self) -> str:
        return self._station

    def reset(self, station_key: str = "") -> None:
        """Forget everything: a new station, or nothing playing."""
        self._station = station_key
        self._segments = []
        self._hearing = None

    def note_title(
        self, station_key: str, stream_title: str, *, now: float, station_name: str = ""
    ) -> None:
        """The station started sending *stream_title* at *now*."""
        if station_key != self._station:
            self.reset(station_key)
        song = song_from_title(stream_title, station_name)
        if self._segments:
            last = self._segments[-1].song
            if last == song:
                return
        self._segments.append(_Segment(start=now, song=song))
        self._prune(now)

    def _prune(self, now: float) -> None:
        horizon = now - TIMELINE_SECONDS
        keep_from = 0
        # A segment can go once the one after it began before the horizon.
        for index in range(len(self._segments) - 1):
            if self._segments[index + 1].start <= horizon:
                keep_from = index + 1
        keep_from = max(keep_from, len(self._segments) - MAX_SEGMENTS)
        if keep_from:
            del self._segments[:keep_from]

    def _segment_at(self, playhead: float) -> _Segment | None:
        found: _Segment | None = None
        for segment in self._segments:
            if segment.start <= playhead:
                found = segment
            else:
                break
        return found

    def tick(
        self, station_key: str, *, now: float, behind: float | None, audible: bool = True
    ) -> Tick:
        """Advance the clock. *behind* is seconds behind live (None means live).

        *audible* is False while the player is stopped, paused or connecting:
        the clock moves on, but nothing counts as heard, whatever *behind* says
        (an engine that cannot report it would otherwise look live and moving).
        """
        result = Tick()
        if station_key != self._station:
            self.reset(station_key)
            return result
        playhead = now - max(0.0, float(behind or 0.0))
        segment = self._segment_at(playhead)
        hearing = self._hearing
        if segment is None:
            self._hearing = None
            return result
        if not audible:
            if hearing is not None:
                hearing.last_wall = now
                hearing.last_playhead = playhead
            return result
        if hearing is None or hearing.segment is not segment:
            self._hearing = _Hearing(
                segment=segment, started_at=now, last_wall=now, last_playhead=playhead
            )
            if segment.song is not None:
                result.started = _stamped(segment.song, now)
            return result
        wall = max(0.0, now - hearing.last_wall)
        moved = playhead - hearing.last_playhead
        hearing.heard += min(max(0.0, moved), wall)
        hearing.last_wall = now
        hearing.last_playhead = playhead
        song = segment.song
        if song is not None and not hearing.sent and hearing.heard >= MIN_HEARD_SECONDS:
            hearing.sent = True
            result.heard.append(_stamped(song, hearing.started_at))
        return result


def _stamped(song: Listen, when: float) -> Listen:
    return Listen(song.artist, song.title, int(when), song.album)


__all__ = [
    "MIN_HEARD_SECONDS",
    "HeardTracker",
    "Listen",
    "Tick",
    "song_from_title",
]
