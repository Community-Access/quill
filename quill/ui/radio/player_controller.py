"""Owns the one internet-radio playback engine for the whole app.

A single ``RadioPlayerController`` lives on ``MainFrame`` for the process's
lifetime; the status bar cell, the tray menu, and the station browser dialog
all read/drive it and subscribe to its state changes, so "listen in the
background while editing" falls out of it being one shared object rather than
needing any new non-modal-panel machinery -- the station browser dialog is an
ordinary modal picker (like the emoji picker); closing it does not stop
playback, because playback lives here, not in the dialog.

Deliberately **always uses the wx.media (WMP) backend**, never libmpv, even
when libmpv is installed for the Audio Studio. ``MpvAudioEngine._on_poll``
(``quill/ui/audio_studio/mpv_engine.py``) only flips its internal "loaded"
flag once ``duration`` reports a positive value, which a live stream never
does -- so ``play()``/``pause()``/``is_playing()`` (all gated on that flag)
would silently no-op forever for radio. ``WxMediaEngine`` has no such gate
problem: ``EVT_MEDIA_LOADED`` fires normally for a live stream once the WMP
backend has enough buffered to start, which is all radio needs (there is no
seek bar or chapter list to populate). Giving radio a working mpv path too is
a real, separately-scoped follow-up (it needs its own live-stream-aware
polling logic, validated against real streams) -- not something to improvise
by touching the shared engine used by the shipped audiobook/podcast player.
wx required (UI layer); no import from here reaches into ``quill/core``
except the plain-data radio models.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

import wx

from quill.core.audio_enhance import (
    EnhanceError,
    EnhanceRelay,
    is_enhancement_active,
)
from quill.core.radio.models import RadioStation
from quill.ui.audio_studio.audio_engine import WxMediaEngine

_log = logging.getLogger(__name__)


class RadioPlayerState(Enum):
    STOPPED = auto()
    CONNECTING = auto()
    PLAYING = auto()
    PAUSED = auto()
    ERROR = auto()


@dataclass(slots=True)
class RadioPlaybackState:
    """A snapshot handed to every subscriber on every change."""

    state: RadioPlayerState
    station: RadioStation | None
    muted: bool
    volume_percent: int
    message: str = ""

    @property
    def status_text(self) -> str:
        """One line for the status bar / tray tooltip."""
        if self.state is RadioPlayerState.STOPPED or self.station is None:
            return "Radio: stopped"
        label = self.station.name
        if self.state is RadioPlayerState.CONNECTING:
            return f"Radio: connecting to {label}..."
        if self.state is RadioPlayerState.PLAYING:
            muted_suffix = " (muted)" if self.muted else ""
            return f"Radio: playing {label}{muted_suffix}"
        if self.state is RadioPlayerState.PAUSED:
            return f"Radio: paused - {label}"
        if self.state is RadioPlayerState.ERROR:
            return f"Radio: could not play {label} - {self.message}"
        return "Radio"


class RadioPlayerController:
    """Play/pause/stop/mute one internet-radio stream at a time."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        on_state_changed: Callable[[RadioPlaybackState], None] | None = None,
        on_register_click: Callable[[str], None] | None = None,
        before_play: Callable[[], None] | None = None,
        on_enhance_error: Callable[[str], None] | None = None,
        resolve_enhancement: Callable[[RadioStation], tuple[float, float, float, bool]]
        | None = None,
    ) -> None:
        self._on_state_changed = on_state_changed
        #: Best-effort RadioBrowser click-vote hook; injected so this module
        #: never has to know about Safe Mode or the network layer itself.
        self._on_register_click = on_register_click
        #: Runs before every play_station: the host stops sibling media (the
        #: podcast player) here so two streams never play over each other.
        self._before_play = before_play
        #: Told about a Sound Enhancements failure (ffmpeg missing, relay
        #: could not start) so the host can announce it; playback still
        #: proceeds unenhanced rather than failing outright.
        self._on_enhance_error = on_enhance_error
        #: Resolves (bass_db, mid_db, treble_db, compressor_enabled) for the
        #: station about to play -- the host looks up that station's own
        #: RadioFavoritesStore override if it has one, else RadioHistory's
        #: shared default. One injection point instead of threading these
        #: through every play_station call site (station browser, favorites
        #: tree, tray, recent/favorites submenus, ...).
        self._resolve_enhancement = resolve_enhancement
        self._engine = WxMediaEngine(
            parent,
            on_loaded=self._on_loaded,
            on_finished=self._on_finished,
            on_error=self._on_error,
        )
        #: Sound Enhancements (3-band EQ + compressor): off by default, so
        #: normal playback never spawns the ffmpeg relay. See set_enhancement.
        self._enhance_relay = EnhanceRelay()
        self._eq_bass_db = 0.0
        self._eq_mid_db = 0.0
        self._eq_treble_db = 0.0
        self._compressor_enabled = False
        self._pre_mute_volume = 100
        self._state = RadioPlaybackState(
            state=RadioPlayerState.STOPPED, station=None, muted=False, volume_percent=100
        )

    @property
    def state(self) -> RadioPlaybackState:
        return self._state

    def play_station(self, station: RadioStation) -> None:
        """Start (or switch to) playing *station*.

        Replaces whatever this controller was playing; the ``before_play``
        hook additionally silences sibling media (the podcast player) so two
        streams never play over each other.
        """
        if self._before_play is not None:
            try:
                self._before_play()
            except Exception:  # noqa: BLE001 - a sibling-stop must never block play
                pass
        if self._resolve_enhancement is not None:
            (
                self._eq_bass_db,
                self._eq_mid_db,
                self._eq_treble_db,
                self._compressor_enabled,
            ) = self._resolve_enhancement(station)
        self._state.station = station
        self._set_state(RadioPlayerState.CONNECTING, message="")
        url = self._resolve_playback_url(station)
        if not self._engine.load(url):
            self._set_state(RadioPlayerState.ERROR, message="That stream could not be opened.")

    def _resolve_playback_url(self, station: RadioStation) -> str:
        """The URL the engine should load: the station's own URL, or a local
        relay URL when Sound Enhancements (EQ/compressor) is active."""
        self._enhance_relay.stop()
        if not is_enhancement_active(
            self._eq_bass_db,
            self._eq_mid_db,
            self._eq_treble_db,
            compressor_enabled=self._compressor_enabled,
        ):
            return station.stream_url
        try:
            return self._enhance_relay.start(
                station.stream_url,
                bass_db=self._eq_bass_db,
                mid_db=self._eq_mid_db,
                treble_db=self._eq_treble_db,
                compressor_enabled=self._compressor_enabled,
            )
        except EnhanceError as error:
            if self._on_enhance_error is not None:
                self._on_enhance_error(str(error))
            return station.stream_url

    def set_enhancement(
        self, *, bass_db: float, mid_db: float, treble_db: float, compressor_enabled: bool
    ) -> None:
        """Change the 3-band EQ / compressor and, if something is playing,
        reconnect through the new setting. Live radio has no position to
        lose, so a reconnect is the whole cost of switching."""
        self._eq_bass_db = bass_db
        self._eq_mid_db = mid_db
        self._eq_treble_db = treble_db
        self._compressor_enabled = compressor_enabled
        station = self._state.station
        if station is not None and self._state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.CONNECTING,
            RadioPlayerState.PAUSED,
        ):
            self.play_station(station)

    def toggle_play_pause(self) -> None:
        if self._state.state is RadioPlayerState.PLAYING:
            self._engine.pause()
            self._set_state(RadioPlayerState.PAUSED)
        elif self._state.state is RadioPlayerState.PAUSED:
            self._engine.play()
            self._set_state(RadioPlayerState.PLAYING)
        elif self._state.station is not None:
            self.play_station(self._state.station)

    def stop(self) -> None:
        self._engine.close()
        self._enhance_relay.stop()
        self._set_state(RadioPlayerState.STOPPED, message="")

    def toggle_mute(self) -> None:
        if self._state.muted:
            self._engine.set_volume(self._pre_mute_volume)
            self._state.muted = False
        else:
            self._pre_mute_volume = self._state.volume_percent
            self._engine.set_volume(0)
            self._state.muted = True
        self._notify()

    def set_volume(self, percent: int) -> None:
        """Internet Radio's own stream volume -- independent of the system
        volume mixer and of screen-reader speech volume; this only scales
        what QUILL itself is playing (``wx.media.MediaCtrl.SetVolume``)."""
        percent = max(0, min(100, int(percent)))
        self._state.volume_percent = percent
        self._state.muted = percent == 0
        self._engine.set_volume(percent)
        self._notify()

    def volume_up(self, step: int = 10) -> None:
        if self._state.muted:
            self._state.muted = False
        self.set_volume(self._state.volume_percent + step)

    def volume_down(self, step: int = 10) -> None:
        if self._state.muted:
            self._state.muted = False
        self.set_volume(self._state.volume_percent - step)

    def shutdown(self) -> None:
        """Release the engine; called once, from the frame's close path."""
        try:
            self._engine.close()
        except Exception:  # noqa: BLE001 - never block app close
            _log.exception("radio engine close failed during shutdown")
        try:
            self._enhance_relay.shutdown()
        except Exception:  # noqa: BLE001 - never block app close
            _log.exception("radio enhancement relay shutdown failed")

    # -- engine callbacks -------------------------------------------------

    def _on_loaded(self, _length_ms: int) -> None:
        self._engine.set_volume(0 if self._state.muted else self._state.volume_percent)
        self._engine.play()
        self._set_state(RadioPlayerState.PLAYING, message="", keep_volume=True)
        station = self._state.station
        if station is not None and station.station_uuid and self._on_register_click:
            uuid = station.station_uuid
            threading.Thread(target=self._on_register_click, args=(uuid,), daemon=True).start()

    def _on_finished(self) -> None:
        # A live stream reaching "finished" means the connection dropped.
        self._set_state(
            RadioPlayerState.STOPPED, message="The stream ended or disconnected.", keep_volume=True
        )

    def _on_error(self, message: str) -> None:
        self._set_state(RadioPlayerState.ERROR, message=message, keep_volume=True)

    # -- internal -----------------------------------------------------------

    def _set_state(
        self,
        state: RadioPlayerState,
        *,
        station: RadioStation | None | Ellipsis = ...,  # type: ignore[valid-type]
        message: str = "",
        keep_volume: bool = False,
    ) -> None:
        if station is not ...:
            self._state.station = station
        self._state.state = state
        self._state.message = message
        if not keep_volume:
            self._state.volume_percent = 100
        self._notify()

    def _notify(self) -> None:
        if self._on_state_changed is not None:
            self._on_state_changed(self._state)
