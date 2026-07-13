"""Owns the one podcast playback engine for the whole app.

Mirrors ``quill/ui/radio/player_controller.py``'s shape: a single
controller lives on ``MainFrame`` for the process's lifetime, so closing the
Podcast Manager dialog never stops playback -- the dialog only drives this
shared controller, it does not own the engine. Playing a new episode always
replaces whatever was previously loaded (:meth:`play_episode` calls
``engine.load`` on the one engine instance), so only one episode ever plays
at a time by construction.

Unlike Radio, podcast episodes are bounded files (even while streaming, the
enclosure URL reports a real ``Content-Length``/duration), so this uses
Audio Studio's normal ``create_engine()`` (mpv-preferred, wx.media
fallback) rather than being restricted to the wx.media-only backend Radio
needs for its infinite live streams.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

import wx

from quill.ui.audio_studio.audio_engine import AudioEngine, create_engine

_log = logging.getLogger(__name__)


class PodcastPlayerState(Enum):
    STOPPED = auto()
    LOADING = auto()
    PLAYING = auto()
    PAUSED = auto()
    ERROR = auto()


@dataclass(slots=True)
class PodcastPlaybackState:
    state: PodcastPlayerState
    show_id: str | None
    episode_guid: str | None
    title: str
    message: str = ""

    @property
    def status_text(self) -> str:
        if self.state is PodcastPlayerState.STOPPED or not self.title:
            return "Podcasts: stopped"
        if self.state is PodcastPlayerState.LOADING:
            return f"Podcasts: loading {self.title}..."
        if self.state is PodcastPlayerState.PLAYING:
            return f"Podcasts: playing {self.title}"
        if self.state is PodcastPlayerState.PAUSED:
            return f"Podcasts: paused - {self.title}"
        if self.state is PodcastPlayerState.ERROR:
            return f"Podcasts: could not play {self.title} - {self.message}"
        return "Podcasts"


class PodcastPlayerController:
    """Play/pause/stop one podcast episode at a time."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        on_state_changed: Callable[[PodcastPlaybackState], None] | None = None,
        on_episode_finished: Callable[[str, str], None] | None = None,
    ) -> None:
        self._on_state_changed = on_state_changed
        #: (show_id, episode_guid) -- fired when an episode plays to the end,
        #: so the caller can mark it played / apply delete-after-play.
        self._on_episode_finished = on_episode_finished
        self._resume_ms = 0
        self._pending_rate = 1.0
        self._volume_percent = 100
        self._engine: AudioEngine | None = create_engine(
            parent,
            on_loaded=self._on_loaded,
            on_finished=self._on_finished,
            on_error=self._on_error,
        )
        self._state = PodcastPlaybackState(
            state=PodcastPlayerState.STOPPED, show_id=None, episode_guid=None, title=""
        )

    @property
    def state(self) -> PodcastPlaybackState:
        return self._state

    def play_episode(
        self,
        *,
        show_id: str,
        episode_guid: str,
        title: str,
        source: str,
        resume_ms: int = 0,
        rate: float = 1.0,
    ) -> None:
        """Start (or switch to) playing one episode; replaces whatever this
        controller was already playing, so only one thing ever plays."""
        self._resume_ms = max(0, int(resume_ms))
        self._pending_rate = rate if rate > 0 else 1.0
        self._state.show_id = show_id
        self._state.episode_guid = episode_guid
        self._state.title = title
        self._set_state(PodcastPlayerState.LOADING)
        if self._engine is None or not self._engine.load(source):
            self._set_state(PodcastPlayerState.ERROR, message="That episode could not be opened.")

    def toggle_play_pause(self) -> None:
        if self._engine is None:
            return
        if self._state.state is PodcastPlayerState.PLAYING:
            self._engine.pause()
            self._set_state(PodcastPlayerState.PAUSED)
        elif self._state.state is PodcastPlayerState.PAUSED:
            self._engine.play()
            self._set_state(PodcastPlayerState.PLAYING)

    def stop(self) -> None:
        if self._engine is not None:
            self._engine.close()
        self._state.show_id = None
        self._state.episode_guid = None
        self._state.title = ""
        self._set_state(PodcastPlayerState.STOPPED)

    def seek(self, ms: int) -> None:
        if self._engine is not None:
            self._engine.seek(ms)

    def set_rate(self, rate: float) -> None:
        if self._engine is not None:
            self._engine.set_rate(rate)

    def set_volume(self, percent: int) -> None:
        self._volume_percent = max(0, min(100, percent))
        if self._engine is not None:
            self._engine.set_volume(self._volume_percent)

    @property
    def volume_percent(self) -> int:
        return self._volume_percent

    def position_ms(self) -> int:
        return self._engine.position_ms() if self._engine is not None else 0

    def length_ms(self) -> int:
        return self._engine.length_ms() if self._engine is not None else 0

    def is_playing(self) -> bool:
        return self._engine.is_playing() if self._engine is not None else False

    def shutdown(self) -> None:
        """Release the engine; called once, from the frame's close path."""
        try:
            if self._engine is not None:
                self._engine.close()
        except Exception:  # noqa: BLE001 - never block app close
            _log.exception("podcast engine close failed during shutdown")

    # -- engine callbacks -------------------------------------------------

    def _on_loaded(self, _length_ms: int) -> None:
        if self._engine is None:
            return
        if self._resume_ms:
            self._engine.seek(self._resume_ms, resume=True)
        else:
            self._engine.play()
        self._engine.set_rate(self._pending_rate)
        self._resume_ms = 0
        self._set_state(PodcastPlayerState.PLAYING)

    def _on_finished(self) -> None:
        show_id, episode_guid = self._state.show_id, self._state.episode_guid
        self._state.show_id = None
        self._state.episode_guid = None
        self._state.title = ""
        self._set_state(PodcastPlayerState.STOPPED)
        if show_id and episode_guid and self._on_episode_finished is not None:
            self._on_episode_finished(show_id, episode_guid)

    def _on_error(self, message: str) -> None:
        self._set_state(PodcastPlayerState.ERROR, message=message)

    # -- internal -----------------------------------------------------------

    def _set_state(self, state: PodcastPlayerState, *, message: str = "") -> None:
        self._state.state = state
        self._state.message = message
        if self._on_state_changed is not None:
            self._on_state_changed(self._state)
