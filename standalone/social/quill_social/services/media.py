"""Media playback engine and player state machine (PRD 19.2, 19.3, 19.4).

Playback in QUILL Social is screen-reader-first: every control has a
deterministic, inspectable model that works with no audio backend at all. The
PRD recommends libmpv for real playback and FFmpeg/ffprobe for inspection (PRD
19.2), but those are heavy native dependencies. Following the "honest boundary"
pattern used by the network adapters, this module ships:

- :class:`MediaEngine` -- the abstract interface every backend implements
  (play, pause, stop, seek, speed, volume, position, duration).
- :class:`NullMediaEngine` -- a fully deterministic in-memory backend that
  models playback position by advancing a logical clock. It needs no libmpv and
  is the default so the whole player is unit-testable headlessly.
- :class:`MpvMediaEngine` -- a descriptor whose :meth:`available` reports
  whether ``python-mpv`` is importable. It documents exactly where the live
  backend attaches without requiring the dependency to import or test this
  module.
- :class:`PlayerState` -- the higher-level state machine over an engine:
  idle/playing/paused/stopped, per-uri position memory, a sleep timer, an A-B
  loop, repeat, and a playback queue (PRD 19.3).
- :func:`player_status_text` -- a speech-friendly status line (PRD 19.4).

This module is wx-free, has no wall-clock reads (every time-advancing call takes
an explicit millisecond delta), and uses no randomness, so playback behavior is
reproducible in tests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

# Player lifecycle states (PRD 19.3).
STATE_IDLE = "idle"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_STOPPED = "stopped"

# Repeat modes for the queue / A-B loop (PRD 19.3).
REPEAT_OFF = "off"
REPEAT_ONE = "one"
REPEAT_ALL = "all"

_REPEAT_MODES = (REPEAT_OFF, REPEAT_ONE, REPEAT_ALL)


def _clamp(value: int, low: int, high: int) -> int:
    """Clamp ``value`` into ``[low, high]`` (high wins if the range is empty)."""
    if high < low:
        return low
    return max(low, min(high, value))


# -- track ------------------------------------------------------------------


@dataclass
class Track:
    """One playable item in the queue (PRD 19.4 Media Information).

    A lightweight, serializable descriptor. It carries only what the player and
    a screen reader need; the full attachment lives in :class:`quill_social.model.Media`.
    """

    uri: str = ""
    title: str = ""
    creator: str = ""
    kind: str = "audio"  # audio | video | podcast | radio | unknown
    duration_ms: int = 0
    source_item_id: str = ""  # the post this media came from (return to source)
    lang: str = ""
    sensitive: bool = False
    has_transcript: bool = False
    has_captions: bool = False

    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "title": self.title,
            "creator": self.creator,
            "kind": self.kind,
            "duration_ms": self.duration_ms,
            "source_item_id": self.source_item_id,
            "lang": self.lang,
            "sensitive": self.sensitive,
            "has_transcript": self.has_transcript,
            "has_captions": self.has_captions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Track:
        return cls(
            uri=d.get("uri", ""),
            title=d.get("title", ""),
            creator=d.get("creator", ""),
            kind=d.get("kind", "audio"),
            duration_ms=int(d.get("duration_ms", 0) or 0),
            source_item_id=d.get("source_item_id", ""),
            lang=d.get("lang", ""),
            sensitive=bool(d.get("sensitive", False)),
            has_transcript=bool(d.get("has_transcript", False)),
            has_captions=bool(d.get("has_captions", False)),
        )


@dataclass
class Chapter:
    """A named time point inside a track (PRD 19.4 Chapter navigation)."""

    start_ms: int = 0
    title: str = ""

    def to_dict(self) -> dict:
        return {"start_ms": self.start_ms, "title": self.title}

    @classmethod
    def from_dict(cls, d: dict) -> Chapter:
        return cls(start_ms=int(d.get("start_ms", 0) or 0), title=d.get("title", ""))


# -- engine interface -------------------------------------------------------


class MediaEngine(ABC):
    """The backend contract every playback engine implements (PRD 19.2).

    An engine owns exactly one "current" media: its uri, its playing/paused
    flag, and a position in milliseconds. Higher layers (:class:`PlayerState`)
    drive queue, memory, and loops on top of this small surface so a new backend
    never has to reimplement them.
    """

    #: stable backend id
    name: str = "base"

    @abstractmethod
    def load(self, uri: str, duration_ms: int = 0) -> None:
        """Make ``uri`` the current media, reset to position 0, paused."""

    @abstractmethod
    def play(self) -> None:
        """Begin or resume playback of the current media."""

    @abstractmethod
    def pause(self) -> None:
        """Pause playback, keeping the current position."""

    @abstractmethod
    def stop(self) -> None:
        """Stop playback and reset the position to 0."""

    @abstractmethod
    def seek_ms(self, ms: int) -> None:
        """Move the position to ``ms``, clamped to ``[0, duration]``."""

    @abstractmethod
    def set_speed(self, speed: float) -> None:
        """Set the playback rate (1.0 = normal)."""

    @abstractmethod
    def set_volume(self, volume: int) -> None:
        """Set the output volume, clamped to ``[0, 100]``."""

    @abstractmethod
    def position_ms(self) -> int:
        """The current playback position in milliseconds."""

    @abstractmethod
    def duration_ms(self) -> int:
        """The total duration of the current media in milliseconds."""

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Whether the engine is actively advancing."""

    @classmethod
    def available(cls) -> bool:
        """Whether this backend's native dependencies are installed."""
        return True


class NullMediaEngine(MediaEngine):
    """A deterministic, backend-free engine (PRD 19.2 boundary).

    Position advances only when the caller invokes :meth:`advance` with an
    explicit millisecond delta, so there is no wall-clock read and no real audio
    output. This is the default engine and the one every test drives; it models
    the full observable behavior of a real player without libmpv.
    """

    name = "null"

    def __init__(self) -> None:
        self._uri = ""
        self._duration = 0
        self._position = 0
        self._playing = False
        self._speed = 1.0
        self._volume = 100
        self._muted = False

    def load(self, uri: str, duration_ms: int = 0) -> None:
        self._uri = uri
        self._duration = max(0, int(duration_ms))
        self._position = 0
        self._playing = False

    def play(self) -> None:
        if self._uri:
            self._playing = True

    def pause(self) -> None:
        self._playing = False

    def stop(self) -> None:
        self._playing = False
        self._position = 0

    def seek_ms(self, ms: int) -> None:
        self._position = _clamp(int(ms), 0, self._duration)

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.1, float(speed))

    def set_volume(self, volume: int) -> None:
        self._volume = _clamp(int(volume), 0, 100)
        if self._volume > 0:
            self._muted = False

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)

    def position_ms(self) -> int:
        return self._position

    def duration_ms(self) -> int:
        return self._duration

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def is_playing(self) -> bool:
        return self._playing

    def advance(self, delta_ms: int) -> int:
        """Advance the logical clock while playing and return the new position.

        Scales ``delta_ms`` by the current speed. Playback stops advancing at
        the media's end; the caller (:class:`PlayerState`) decides what happens
        then (repeat, next track, stop).
        """
        if not self._playing or delta_ms <= 0:
            return self._position
        step = int(delta_ms * self._speed)
        self._position = _clamp(self._position + step, 0, self._duration)
        if self._duration and self._position >= self._duration:
            self._position = self._duration
            self._playing = False
        return self._position


class MpvMediaEngine(MediaEngine):
    """Descriptor for the recommended libmpv backend (PRD 19.2).

    This class documents exactly where the live engine attaches. It never
    imports ``mpv`` at module load; :meth:`available` probes for it so the UI can
    offer real playback when the ``media`` extra is installed and fall back to
    :class:`NullMediaEngine` otherwise. Constructing it without the dependency
    raises a clear error rather than failing opaquely, mirroring the network
    adapters' boundary.
    """

    name = "mpv"

    _NOT_WIRED = (
        "The libmpv playback backend is not enabled in this build. Install the "
        "'media' extra (python-mpv + libmpv) to enable real audio and video "
        "playback; QUILL Social uses a deterministic in-memory engine until then."
    )

    def __init__(self) -> None:
        if not self.available():
            raise RuntimeError(self._NOT_WIRED)
        raise RuntimeError(self._NOT_WIRED)  # live wiring lands with the media extra

    @classmethod
    def available(cls) -> bool:
        try:
            import mpv  # noqa: F401
        except ImportError:
            return False
        return True

    def load(self, uri: str, duration_ms: int = 0) -> None:
        raise RuntimeError(self._NOT_WIRED)

    def play(self) -> None:
        raise RuntimeError(self._NOT_WIRED)

    def pause(self) -> None:
        raise RuntimeError(self._NOT_WIRED)

    def stop(self) -> None:
        raise RuntimeError(self._NOT_WIRED)

    def seek_ms(self, ms: int) -> None:
        raise RuntimeError(self._NOT_WIRED)

    def set_speed(self, speed: float) -> None:
        raise RuntimeError(self._NOT_WIRED)

    def set_volume(self, volume: int) -> None:
        raise RuntimeError(self._NOT_WIRED)

    def position_ms(self) -> int:
        raise RuntimeError(self._NOT_WIRED)

    def duration_ms(self) -> int:
        raise RuntimeError(self._NOT_WIRED)

    @property
    def is_playing(self) -> bool:
        raise RuntimeError(self._NOT_WIRED)


# -- player state machine ---------------------------------------------------


@dataclass
class ABLoop:
    """An A-B repeat region inside the current track (PRD 19.3 A-B loop)."""

    a_ms: int | None = None
    b_ms: int | None = None

    @property
    def active(self) -> bool:
        return self.a_ms is not None and self.b_ms is not None and self.b_ms > self.a_ms

    def to_dict(self) -> dict:
        return {"a_ms": self.a_ms, "b_ms": self.b_ms}


class PlayerState:
    """High-level player over a :class:`MediaEngine` (PRD 19.3).

    Adds everything the bare engine does not: a playback queue, per-uri position
    memory (resume where you left off), a sleep timer, an A-B loop, repeat
    modes, and chapter navigation. All of it is deterministic -- time only moves
    when :meth:`tick` is called with an explicit delta -- so the whole player is
    unit-testable without any audio backend.
    """

    def __init__(self, engine: MediaEngine | None = None) -> None:
        self.engine: MediaEngine = engine or NullMediaEngine()
        self.state: str = STATE_IDLE
        self.queue: list[Track] = []
        self.index: int = -1
        self.positions: dict[str, int] = {}  # uri -> remembered position
        self.chapters: list[Chapter] = []
        self.ab_loop = ABLoop()
        self.repeat: str = REPEAT_OFF
        self.sleep_remaining_ms: int | None = None
        self.skip_ms: int = 15_000  # configurable skip (PRD 19.3)

    # -- queue ---------------------------------------------------------------

    def set_queue(self, tracks: list[Track], *, start: int = 0) -> None:
        """Replace the queue and load ``start`` without auto-playing."""
        self.queue = list(tracks)
        if not self.queue:
            self.index = -1
            self.state = STATE_IDLE
            return
        self.index = _clamp(start, 0, len(self.queue) - 1)
        self._load_current()

    def enqueue(self, track: Track) -> None:
        """Append a track; load it if the queue was empty."""
        was_empty = not self.queue
        self.queue.append(track)
        if was_empty:
            self.index = 0
            self._load_current()

    @property
    def current(self) -> Track | None:
        if 0 <= self.index < len(self.queue):
            return self.queue[self.index]
        return None

    def _load_current(self) -> None:
        track = self.current
        if track is None:
            self.state = STATE_IDLE
            return
        self.engine.load(track.uri, track.duration_ms)
        self.ab_loop = ABLoop()
        remembered = self.positions.get(track.uri)
        if remembered:
            self.engine.seek_ms(remembered)
        self.state = STATE_STOPPED

    def next_track(self) -> bool:
        """Advance to the next queued track. Returns whether one was loaded."""
        self._remember()
        if self.index + 1 < len(self.queue):
            self.index += 1
        elif self.repeat == REPEAT_ALL and self.queue:
            self.index = 0
        else:
            return False
        self._load_current()
        if self.state != STATE_IDLE:
            self.play()
        return True

    def previous_track(self) -> bool:
        """Go to the previous track (or restart if past the beginning)."""
        self._remember()
        if self.index > 0:
            self.index -= 1
        else:
            self.engine.seek_ms(0)
            return False
        self._load_current()
        if self.state != STATE_IDLE:
            self.play()
        return True

    # -- transport -----------------------------------------------------------

    def play(self) -> None:
        if self.current is None:
            return
        self.engine.play()
        self.state = STATE_PLAYING

    def pause(self) -> None:
        if self.state == STATE_PLAYING:
            self.engine.pause()
            self.state = STATE_PAUSED
            self._remember()

    def toggle(self) -> None:
        if self.state == STATE_PLAYING:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        self._remember()
        self.engine.stop()
        self.state = STATE_STOPPED

    def seek_ms(self, ms: int) -> None:
        self.engine.seek_ms(ms)
        self._remember()

    def skip_forward(self) -> None:
        self.engine.seek_ms(self.engine.position_ms() + self.skip_ms)
        self._remember()

    def skip_back(self) -> None:
        self.engine.seek_ms(self.engine.position_ms() - self.skip_ms)
        self._remember()

    def set_speed(self, speed: float) -> None:
        self.engine.set_speed(speed)

    def set_volume(self, volume: int) -> None:
        self.engine.set_volume(volume)

    # -- position memory -----------------------------------------------------

    def _remember(self) -> None:
        track = self.current
        if track is not None and track.uri:
            self.positions[track.uri] = self.engine.position_ms()

    def remembered_position(self, uri: str) -> int:
        return self.positions.get(uri, 0)

    # -- A-B loop + repeat ---------------------------------------------------

    def set_ab_loop(self, a_ms: int | None, b_ms: int | None) -> None:
        self.ab_loop = ABLoop(a_ms=a_ms, b_ms=b_ms)

    def clear_ab_loop(self) -> None:
        self.ab_loop = ABLoop()

    def set_repeat(self, mode: str) -> None:
        if mode not in _REPEAT_MODES:
            raise ValueError(f"unknown repeat mode: {mode}")
        self.repeat = mode

    # -- sleep timer ---------------------------------------------------------

    def set_sleep_timer(self, ms: int | None) -> None:
        self.sleep_remaining_ms = ms if ms is None or ms > 0 else None

    def cancel_sleep_timer(self) -> None:
        self.sleep_remaining_ms = None

    # -- chapters ------------------------------------------------------------

    def set_chapters(self, chapters: list[Chapter]) -> None:
        self.chapters = sorted(chapters, key=lambda c: c.start_ms)

    def current_chapter(self) -> Chapter | None:
        pos = self.engine.position_ms()
        found: Chapter | None = None
        for ch in self.chapters:
            if ch.start_ms <= pos:
                found = ch
            else:
                break
        return found

    def next_chapter(self) -> bool:
        pos = self.engine.position_ms()
        for ch in self.chapters:
            if ch.start_ms > pos:
                self.seek_ms(ch.start_ms)
                return True
        return False

    def previous_chapter(self) -> bool:
        pos = self.engine.position_ms()
        target: Chapter | None = None
        # a small guard so "previous" from just inside a chapter goes to the one before
        for ch in self.chapters:
            if ch.start_ms < pos - 1000:
                target = ch
            else:
                break
        if target is not None:
            self.seek_ms(target.start_ms)
            return True
        if self.chapters:
            self.seek_ms(self.chapters[0].start_ms)
            return True
        return False

    # -- the clock -----------------------------------------------------------

    def tick(self, delta_ms: int) -> None:
        """Advance logical time by ``delta_ms`` and apply loop/timer/queue rules.

        This is the single place time moves. It works only against
        :class:`NullMediaEngine` (which exposes :meth:`advance`); a live backend
        advances itself, so callers wire ``tick`` only in headless/test mode.
        """
        if delta_ms <= 0:
            return
        # Sleep timer counts down regardless of loop handling.
        if self.sleep_remaining_ms is not None:
            self.sleep_remaining_ms -= delta_ms
            if self.sleep_remaining_ms <= 0:
                self.sleep_remaining_ms = None
                self.pause()
                return
        if self.state != STATE_PLAYING:
            return
        advance = getattr(self.engine, "advance", None)
        if advance is None:
            return
        advance(delta_ms)
        self._remember()
        # A-B loop wins: wrap back to A when we reach B.
        if self.ab_loop.active and self.engine.position_ms() >= self.ab_loop.b_ms:
            self.engine.seek_ms(self.ab_loop.a_ms)
            self._remember()
            return
        # End of track handling.
        if self.engine.duration_ms() and self.engine.position_ms() >= self.engine.duration_ms():
            self._on_track_end()

    def _on_track_end(self) -> None:
        if self.repeat == REPEAT_ONE:
            self.engine.seek_ms(0)
            self.play()
            return
        if not self.next_track():
            self.state = STATE_STOPPED


def _fmt_ms(ms: int) -> str:
    """Format milliseconds as ``m:ss`` or ``h:mm:ss`` for speech (PRD 19.4)."""
    total = max(0, int(ms)) // 1000
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def player_status_text(state: PlayerState) -> str:
    """A screen-reader-friendly one-line player status (PRD 19.4).

    Reports state, media type and title, position and duration, and the current
    chapter -- the fields a listener needs spoken, in a stable order, with no
    visual-only decoration.
    """
    track = state.current
    if track is None or state.state == STATE_IDLE:
        return "Player idle. Nothing loaded."

    verb = {
        STATE_PLAYING: "Playing",
        STATE_PAUSED: "Paused",
        STATE_STOPPED: "Stopped",
    }.get(state.state, "Idle")

    parts: list[str] = [verb]
    title = track.title or track.uri or "untitled"
    parts.append(f"{track.kind} {title}".strip())

    pos = state.engine.position_ms()
    dur = state.engine.duration_ms()
    if dur:
        parts.append(f"{_fmt_ms(pos)} of {_fmt_ms(dur)}")
    else:
        parts.append(f"at {_fmt_ms(pos)}")

    chapter = state.current_chapter()
    if chapter is not None:
        parts.append(f"chapter {chapter.title}".strip())

    if state.repeat != REPEAT_OFF:
        parts.append(f"repeat {state.repeat}")
    if state.ab_loop.active:
        parts.append(f"A-B loop {_fmt_ms(state.ab_loop.a_ms)}-{_fmt_ms(state.ab_loop.b_ms)}")
    if state.sleep_remaining_ms is not None:
        parts.append(f"sleep in {_fmt_ms(state.sleep_remaining_ms)}")

    return ". ".join(parts) + "."
