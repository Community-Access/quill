"""The MediaController: transport, seeking, and chapter logic over an engine.

Pure ``quill.core`` (wx-free), UI-thread-affine, and driven by an injected
:class:`~quill.core.media.engine.PlaybackEngine` so every branch is unit-testable
with a fake engine and no audio device. This is Phase 1 of ``player.md`` Section
16: the state machine, precise seeking (including the H:M:S "go to position"),
chapter navigation, and the event stream the UI observes. DSP, DAISY, library,
and the wx shell build on top in later phases.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.media.engine import PlaybackEngine
from quill.core.media.errors import EngineUnavailableError, NoMediaLoadedError
from quill.core.media.events import (
    CHAPTER_CHANGED,
    ENDED,
    LOADED,
    SEEKED,
    STATE_CHANGED,
    PlayerEvent,
    PlayerListener,
)
from quill.core.media.models import MediaChapter, MediaItem, PlayerState
from quill.core.media.timecode import parse_timecode

#: Pressing "previous chapter" within this many ms of the current chapter's start
#: jumps to the previous chapter; later than this, it restarts the current one.
_PREV_CHAPTER_THRESHOLD_MS = 3000

_MIN_RATE = 0.5
_MAX_RATE = 4.0


def clamp_position(ms: int, duration_ms: int) -> int:
    """Clamp a requested position to ``[0, duration_ms]`` (no upper bound if unknown).

    Pure helper shared by the controller and the "Go to Position" dialog so the
    seek math is tested in one place.
    """
    target = max(0, int(ms))
    if duration_ms > 0:
        target = min(target, duration_ms)
    return target


class MediaController:
    """Owns transport state and chapter position for one playback session."""

    def __init__(self, engine: PlaybackEngine) -> None:
        self._engine = engine
        self._item: MediaItem | None = None
        self._state = PlayerState.STOPPED
        self._speed = 1.0
        self._volume = 100
        self._last_chapter_index = -1
        self._listeners: list[PlayerListener] = []

    # -- events --------------------------------------------------------------

    def subscribe(self, listener: PlayerListener) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    def _emit(self, kind: str, value: object = None) -> None:
        event = PlayerEvent(kind, value)
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:  # noqa: BLE001 - a bad listener must not break playback
                pass

    # -- loading & transport -------------------------------------------------

    def load(self, item: MediaItem, *, resume_ms: int = 0, autoplay: bool = False) -> None:
        """Load ``item``, optionally resuming at ``resume_ms`` and/or autoplaying."""
        if not self._engine.load(item.path):
            raise EngineUnavailableError(f"could not load {item.path!r}")
        self._item = item
        self._last_chapter_index = -1
        self._engine.set_volume(self._volume)
        self._engine.set_rate(self._speed)
        if resume_ms > 0:
            self._engine.seek(self._clamp(resume_ms))
        self._emit(LOADED, item)
        if autoplay:
            self.play()
        else:
            self._set_state(PlayerState.PAUSED)
        self._refresh_chapter()

    def play(self) -> None:
        self._require_item()
        self._engine.play()
        self._set_state(PlayerState.PLAYING)

    def pause(self) -> None:
        self._require_item()
        self._engine.pause()
        self._set_state(PlayerState.PAUSED)

    def toggle(self) -> None:
        if self._state is PlayerState.PLAYING:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        self._engine.stop()
        self._set_state(PlayerState.STOPPED)

    def mark_ended(self) -> None:
        """The engine reached the end (UI wires this to the engine's finished callback)."""
        self._set_state(PlayerState.ENDED)
        self._emit(ENDED)

    # -- position & seeking --------------------------------------------------

    def position_ms(self) -> int:
        return self._engine.position_ms()

    def duration_ms(self) -> int:
        return self._engine.length_ms()

    def seek_to(self, ms: int) -> None:
        """Seek to an absolute position, clamped to the media bounds."""
        self._require_item()
        target = self._clamp(ms)
        self._engine.seek(target)
        self._emit(SEEKED, target)
        self._refresh_chapter()

    def skip(self, delta_ms: int) -> None:
        """Skip forward (positive) or back (negative) by ``delta_ms``."""
        self.seek_to(self.position_ms() + delta_ms)

    def go_to_timecode(self, text: str) -> int:
        """Seek to a timecode string (h:mm:ss / mm:ss / seconds / 1h2m3s).

        Returns the clamped landing position in ms. Raises
        :class:`~quill.core.media.errors.InvalidTimecodeError` on a bad string.
        """
        target = self._clamp(parse_timecode(text))
        self.seek_to(target)
        return target

    def go_to_percent(self, percent: float) -> int:
        """Seek to a percentage (0-100) of the duration; returns the landing ms."""
        pct = max(0.0, min(100.0, percent))
        target = int(self.duration_ms() * pct / 100.0)
        self.seek_to(target)
        return target

    def _clamp(self, ms: int) -> int:
        return clamp_position(ms, self.duration_ms())

    # -- chapters ------------------------------------------------------------

    def chapters(self) -> tuple[MediaChapter, ...]:
        return self._item.chapters if self._item else ()

    def current_chapter_index(self) -> int:
        """Index of the chapter containing the current position, or -1 if none."""
        return self._chapter_index_at(self.position_ms())

    def current_chapter(self) -> MediaChapter | None:
        index = self.current_chapter_index()
        chapters = self.chapters()
        return chapters[index] if 0 <= index < len(chapters) else None

    def next_chapter(self) -> None:
        chapters = self.chapters()
        if not chapters:
            return
        position = self.position_ms()
        for chapter in chapters:
            if chapter.start_ms > position:
                self.seek_to(chapter.start_ms)
                return
        # Already in the last chapter: no-op.

    def prev_chapter(self) -> None:
        chapters = self.chapters()
        if not chapters:
            self.seek_to(0)
            return
        index = self.current_chapter_index()
        position = self.position_ms()
        if index > 0 and (position - chapters[index].start_ms) <= _PREV_CHAPTER_THRESHOLD_MS:
            self.seek_to(chapters[index - 1].start_ms)
        else:
            self.seek_to(chapters[index].start_ms if index >= 0 else 0)

    def go_to_chapter(self, index: int) -> None:
        chapters = self.chapters()
        if not chapters:
            return
        clamped = max(0, min(len(chapters) - 1, index))
        self.seek_to(chapters[clamped].start_ms)

    def refresh_chapter(self) -> None:
        """Recompute the current chapter and emit if it changed.

        The UI's position timer calls this during continuous playback so a chapter
        crossing is announced without the user seeking.
        """
        self._refresh_chapter()

    def _chapter_index_at(self, position: int) -> int:
        index = -1
        for i, chapter in enumerate(self.chapters()):
            if chapter.start_ms <= position:
                index = i
            else:
                break
        return index

    def _refresh_chapter(self) -> None:
        index = self.current_chapter_index()
        if index != self._last_chapter_index:
            self._last_chapter_index = index
            self._emit(CHAPTER_CHANGED, index)

    # -- rate & volume -------------------------------------------------------

    def set_speed(self, rate: float) -> float:
        """Set playback speed (clamped to 0.5-4.0); returns the applied rate."""
        self._speed = max(_MIN_RATE, min(_MAX_RATE, float(rate)))
        self._engine.set_rate(self._speed)
        return self._speed

    def speed(self) -> float:
        return self._speed

    def set_volume(self, percent: int) -> int:
        """Set volume (clamped to 0-100); returns the applied value."""
        self._volume = max(0, min(100, int(percent)))
        self._engine.set_volume(self._volume)
        return self._volume

    def volume(self) -> int:
        return self._volume

    # -- state ---------------------------------------------------------------

    def state(self) -> PlayerState:
        return self._state

    def item(self) -> MediaItem | None:
        return self._item

    def _set_state(self, new: PlayerState) -> None:
        if new is not self._state:
            self._state = new
            self._emit(STATE_CHANGED, new)

    def _require_item(self) -> None:
        if self._item is None:
            raise NoMediaLoadedError("no media is loaded")


__all__ = ["MediaController", "clamp_position"]
