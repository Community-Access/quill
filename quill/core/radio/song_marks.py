"""Song marks in the time-shift buffer: where each song starts, by title.

Every time the station's title changes while the buffer is running, the point
in the buffer where it changed is marked with that title. The marks turn the
buffer into a list of songs, so a listener can go back to the start of the
song they are in (or the one before), skip ahead to the next one, ask which
song they are hearing and how far behind live that is, and save one song --
or every song still in the buffer -- to a file of its own.

The idea, and the shape of the rules, come from BlindRadio by serrebidev (MIT),
``crates/blindradio-core/src/segments.rs``: blank titles mark nothing, a
repeat of the current title is the same song, a first title that arrives soon
after tuning in names the audio before it too, Previous goes to the start of
the song you are well into and to the one before when it has only just begun,
and Next past the last song goes back to live. No code is copied; the
positions here are mpv's stream timeline rather than a decoder's frames.

Two things are Quill Radio's own:

* **Noise titles mark nothing.** "Live", "Advertisement" or the station's own
  name between two songs is the station talking about itself, exactly as the
  song history and the recorder's song splitter already treat it
  (:func:`quill.core.radio.song_history.is_noise_title`); the song before it
  keeps the air until a real title arrives.
* **Two sightings of one song merge, and the earlier wins.** A title can reach
  Quill Radio twice: from mpv, in step with what you hear (mpv's ICY and HLS
  metadata are timed to the playhead), and from the out-of-band title reader,
  which sees the live edge up to a poll late. Both are claims about where the
  same song starts, and a song cannot start later than somebody first saw its
  title, so the earlier position is kept.

Positions are seconds on mpv's stream timeline (``time-pos``): the playhead,
the live edge (``demuxer-cache-time``) and the oldest audio still buffered all
use the same axis, so a mark stays on its song whatever the wall clock did.

wx-free, strict-typed, pure. Marks live for one session of one station; the
engine clears them whenever a new stream loads.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from enum import Enum

from quill.core.radio.song_history import is_noise_title

#: A first title this close to the buffer's start names the audio before it:
#: tuning in lands mid-song and the title follows within seconds (BlindRadio's
#: FIRST_TITLE_MS).
FIRST_TITLE_SECONDS = 15.0

#: Previous this far into a song goes to its start, as a media player's
#: Previous does; sooner, it goes to the song before (BlindRadio's RESTART_MS).
RESTART_SECONDS = 3.0

#: Two sightings of one title this close together are one song start. Wider
#: than the out-of-band title poll (30 seconds), so its late sighting merges
#: with mpv's timed one rather than starting a second copy of the song.
MERGE_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class SongMark:
    """Where one title started, on the stream timeline."""

    position: float
    title: str


@dataclass(frozen=True, slots=True)
class Song:
    """One song still in the buffer: its title and where it starts and ends."""

    title: str
    start: float
    end: float

    @property
    def length(self) -> float:
        return max(0.0, self.end - self.start)


class Which(Enum):
    """Which song, relative to the playhead."""

    PREVIOUS = "previous"
    CURRENT = "current"
    NEXT = "next"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class Jump:
    """Where a song jump lands: a song, the live edge, or nowhere."""

    song: Song | None = None
    live: bool = False

    @property
    def nowhere(self) -> bool:
        return self.song is None and not self.live


class SongMarks:
    """The titles heard in this buffer, oldest first."""

    def __init__(self, station_name: str = "") -> None:
        self.station_name = station_name
        self._marks: list[SongMark] = []

    # -- recording what was heard ----------------------------------------------

    def clear(self) -> None:
        """Forget every mark: a new stream, so a new buffer."""
        self._marks.clear()

    def reset(self, station_name: str) -> None:
        """A new station: forget the marks and learn its name for noise checks."""
        self.station_name = station_name
        self.clear()

    @property
    def marks(self) -> tuple[SongMark, ...]:
        return tuple(self._marks)

    def __len__(self) -> int:
        return len(self._marks)

    def mark(self, title: str, position: float, *, buffer_start: float | None = None) -> bool:
        """Note that *title* was heard at *position*. True when the marks changed.

        A blank or noise title marks nothing. A title the marks already give
        to *position* is not news. A second sighting of a title already marked
        nearby (:data:`MERGE_SECONDS`) moves that mark earlier when it is
        earlier, and is otherwise ignored. The very first title, when it
        arrives within :data:`FIRST_TITLE_SECONDS` of the buffer's start, is
        marked at the start, so the song you tuned in to has a name.
        """
        title = (title or "").strip()
        if not title or is_noise_title(title, self.station_name):
            return False
        position = max(0.0, float(position))
        if buffer_start is not None:
            position = max(position, float(buffer_start))
        for index, existing in enumerate(self._marks):
            if existing.title != title or abs(existing.position - position) > MERGE_SECONDS:
                continue
            if position >= existing.position:
                return False
            floor = self._marks[index - 1].position if index > 0 else float("-inf")
            if position <= floor:
                return False
            self._marks[index] = SongMark(position, title)
            return True
        if self.title_at(position) == title:
            return False
        if (
            not self._marks
            and buffer_start is not None
            and position - float(buffer_start) <= FIRST_TITLE_SECONDS
        ):
            position = float(buffer_start)
        at = bisect.bisect_right([m.position for m in self._marks], position)
        self._marks.insert(at, SongMark(position, title))
        return True

    def forget_before(self, buffer_start: float) -> None:
        """Drop marks whose song has left the buffer entirely.

        Only the mark the oldest buffered audio falls under is still needed;
        everything older names audio that is gone.
        """
        while len(self._marks) > 1 and self._marks[1].position <= buffer_start:
            self._marks.pop(0)

    # -- reading it back ---------------------------------------------------------

    def title_at(self, position: float) -> str:
        """The title of the song playing at *position*, or "" before the first."""
        found = ""
        for mark in self._marks:
            if mark.position > position:
                break
            found = mark.title
        return found

    def songs(self, buffer_start: float, live_edge: float) -> list[Song]:
        """The songs still in the buffer, oldest first.

        The newest runs to *live_edge*; the oldest starts where the buffer
        does, however long ago its title arrived. A song with no audio left
        is not a song.
        """
        out: list[Song] = []
        for index, mark in enumerate(self._marks):
            following = self._marks[index + 1].position if index + 1 < len(self._marks) else None
            end = live_edge if following is None else min(following, live_edge)
            start = max(mark.position, buffer_start)
            if start < end:
                out.append(Song(mark.title, start, end))
        return out


def _index_at(songs: list[Song], playhead: float) -> int | None:
    """The song holding *playhead*; ``None`` before the first."""
    found: int | None = None
    for index, song in enumerate(songs):
        if song.start <= playhead:
            found = index
    return found


def pick(songs: list[Song], playhead: float, which: Which) -> list[Song]:
    """The songs *which* names, relative to *playhead*. Empty when none.

    ``ALL`` is every song in the buffer; the others are at most one.
    """
    if which is Which.ALL:
        return list(songs)
    at = _index_at(songs, playhead)
    if which is Which.CURRENT:
        return [songs[at]] if at is not None else []
    if which is Which.PREVIOUS:
        return [songs[at - 1]] if at is not None and at > 0 else []
    following = 0 if at is None else at + 1
    return [songs[following]] if following < len(songs) else []


def jump(songs: list[Song], playhead: float, *, forward: bool, behind_live: bool) -> Jump:
    """Where Previous Song or Next Song should land.

    Previous restarts the song it is well into (:data:`RESTART_SECONDS`) and
    otherwise goes to the one before. Next past the last song goes back to
    live -- when there is a live edge to go back to (*behind_live*).
    """
    if forward:
        found = pick(songs, playhead, Which.NEXT)
    else:
        current = pick(songs, playhead, Which.CURRENT)
        if current and playhead - current[0].start > RESTART_SECONDS:
            found = current
        else:
            found = pick(songs, playhead, Which.PREVIOUS)
    if found:
        return Jump(song=found[0])
    if forward and behind_live:
        return Jump(live=True)
    return Jump()


def describe_offset(seconds: float) -> str:
    """A spoken length: 12 seconds, 1 minute 5 seconds, 1 hour 2 minutes (pure)."""
    total = max(0, int(round(seconds)))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)

    def unit(count: int, word: str) -> str:
        return f"{count} {word}{'' if count == 1 else 's'}"

    if hours:
        return unit(hours, "hour") + (f" {unit(minutes, 'minute')}" if minutes else "")
    if minutes:
        return unit(minutes, "minute") + (f" {unit(secs, 'second')}" if secs else "")
    return unit(secs, "second")


#: Quill Radio's keys for the song-mark commands, spread into
#: ``APP_KEYMAPS["radio"]`` (kept here so app_keymaps.py stays under its size
#: cap). Alt+Shift+Left/Right step by song, the bigger brother of Rewind and
#: Forward on Ctrl+Shift+Left/Right; W is "where", like Where Am I on
#: Ctrl+Shift+W; the saves take Ctrl+Alt+F5-F8 in BlindRadio's order (all,
#: previous, next, current), since Ctrl+F5 and Ctrl+F8 were taken; T is the
#: once-in-a-while time-shift length for one station (rule 9).
SONG_MARK_KEYS: dict[str, str] = {
    "radio.previous_song": "Alt+Shift+Left",
    "radio.next_song": "Alt+Shift+Right",
    "radio.which_song": "Alt+Shift+W",
    "radio.save_all_songs": "Ctrl+Alt+F5",
    "radio.save_previous_song": "Ctrl+Alt+F6",
    "radio.save_next_song": "Ctrl+Alt+F7",
    "radio.save_current_song": "Ctrl+Alt+F8",
    "radio.station_timeshift": "Alt+Shift+T",
}


#: mpv's ``audio-codec-name`` -> the extension mpv's stream writer (``dump-cache``)
#: picks a container from. The audio goes out exactly as the station sent it.
_EXTENSION_BY_CODEC: dict[str, str] = {
    "mp3": ".mp3",
    "mp3float": ".mp3",
    "mp2": ".mp2",
    "aac": ".aac",
    "aac_latm": ".aac",
    "aac_fixed": ".aac",
    "opus": ".opus",
    "libopus": ".opus",
    "vorbis": ".ogg",
    "libvorbis": ".ogg",
    "flac": ".flac",
}


def extension_for_codec(codec: str) -> str:
    """The file extension a song in *codec* is saved with (pure).

    Anything unrecognised goes into Matroska audio, which holds every codec a
    station could send, rather than into a container that would refuse it.
    """
    return _EXTENSION_BY_CODEC.get((codec or "").strip().casefold(), ".mka")


__all__ = [
    "FIRST_TITLE_SECONDS",
    "MERGE_SECONDS",
    "RESTART_SECONDS",
    "SONG_MARK_KEYS",
    "Jump",
    "Song",
    "SongMark",
    "SongMarks",
    "Which",
    "describe_offset",
    "extension_for_codec",
    "jump",
    "pick",
]
