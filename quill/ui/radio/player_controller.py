"""Owns the one internet-radio playback engine for the whole app.

A single ``RadioPlayerController`` lives on ``MainFrame`` for the process's
lifetime; the status bar cell, the tray menu, and the station browser dialog
all read/drive it and subscribe to its state changes, so "listen in the
background while editing" falls out of it being one shared object rather than
needing any new non-modal-panel machinery -- the station browser dialog is an
ordinary modal picker (like the emoji picker); closing it does not stop
playback, because playback lives here, not in the dialog.

**Engine choice (#1076):** two backends. ``MpvRadioEngine``
(``mpv_radio_engine.py``, a radio-specific live-stream-aware libmpv engine
-- the shared ``MpvAudioEngine`` gates "loaded" on a positive ``duration``,
which a live stream never reports, so it cannot be reused here) is
preferred whenever libmpv is present (``RadioHistory.playback_engine`` =
"auto", the same philosophy as the podcast/Audio Studio ``create_engine``):
it is what delivers output-device routing, live pause/rewind (DVR), Volume
Boost, native no-relay Sound Enhancements, engine-level track titles,
buffering announcements, and Ogg Vorbis/Opus/HLS stations. ``WxMediaEngine``
(wx.media / WMP) remains the zero-dependency fallback and the "Windows
Media (classic)" escape hatch in Preferences. Either direction gets one
silent cross-engine rescue per play attempt: a stream the current engine
cannot open is retried once on the other before an error is declared --
WMP simply cannot decode Ogg/Opus/HLS, and a broken libmpv must never take
playback away. ICY What's Playing (an out-of-band side connection, with an
engine-native ``media-title`` fallback) and recording (a separate ffmpeg
process) are engine-agnostic. wx required (UI layer); no import from here
reaches into ``quill/core`` except the plain-data radio models and the
shared Sound Enhancements graph builder.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

import wx

from quill.core.audio_enhance import EnhanceError, EnhanceRelay
from quill.core.radio.models import RadioStation
from quill.ui.audio_studio.audio_engine import WxMediaEngine
from quill.ui.radio.mpv_radio_engine import MpvRadioEngine, mpv_output_device_available

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
        resolve_enhancement: Callable[[RadioStation], tuple[float, float, float, bool, str]]
        | None = None,
        resolve_volume: Callable[[RadioStation], int] | None = None,
        output_device: str = "",
        on_output_device_error: Callable[[str], None] | None = None,
        playback_engine: str = "auto",
        on_buffering: Callable[[], None] | None = None,
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
        #: Resolves the memorized volume (0-100) for the station about to
        #: play, or -1 for "no preference recorded" -- the host looks up
        #: that station's RadioFavoritesStore.volume_percent. Mirrors
        #: resolve_enhancement's injection point. When -1, play_station
        #: leaves the current volume alone rather than forcing a default,
        #: so a volume set just before pressing play is honored.
        self._resolve_volume = resolve_volume
        #: The mpv audio-device name playback routes to ("" = system
        #: default; needs the mpv engine). Told about a device/engine
        #: failure so the host can announce the fallback; playback still
        #: proceeds on wx.media.
        self._output_device = output_device.strip()
        self._on_output_device_error = on_output_device_error
        #: "auto" (mpv when installed, else wx.media), "wx", or "mpv" --
        #: see RadioHistory.playback_engine. Auto is what lights up device
        #: routing, live pause/rewind, Volume Boost, and Ogg/Opus/HLS
        #: stations for everyone once libmpv ships in the app.
        self._playback_engine = (
            playback_engine if playback_engine in ("auto", "wx", "mpv") else "auto"
        )
        #: Announces a mid-stream rebuffer (mpv engine) instead of dead air.
        self._on_buffering = on_buffering
        #: One cross-engine rescue per play attempt: a stream the current
        #: engine cannot open is retried once on the other engine before an
        #: error is declared (WMP cannot decode Ogg/Opus/HLS; a broken mpv
        #: falls back to WMP). Reset by every play_station.
        self._fallback_attempted = False
        self._parent = parent
        self._wx_engine = WxMediaEngine(
            parent,
            on_loaded=self._on_loaded,
            on_finished=self._on_finished,
            on_error=self._on_error,
        )
        #: Created lazily on the first play that opts into a device; kept
        #: for the process's lifetime like the wx engine.
        self._mpv_engine: MpvRadioEngine | None = None
        self._engine = self._wx_engine
        #: Sound Enhancements (3-band EQ + compressor + mono + night mode):
        #: off by default, so normal playback never spawns the ffmpeg relay.
        #: On the mpv engine the same filter graph applies natively (af),
        #: with no relay at all. See set_enhancement / set_sound_options.
        self._enhance_relay = EnhanceRelay()
        self._eq_bass_db = 0.0
        self._eq_mid_db = 0.0
        self._eq_treble_db = 0.0
        self._compressor_enabled = False
        self._channel_mode = "stereo"
        self._night_mode_enabled = False
        #: Volume Boost: amplify up to 50% past 100 (mpv engine only; the
        #: wx engine clamps at 100, so it silently does nothing there).
        self._volume_boost = False
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
                self._channel_mode,
            ) = self._resolve_enhancement(station)
        self._state.station = station
        if self._resolve_volume is not None:
            memorized = self._resolve_volume(station)
            if memorized >= 0:
                self._state.volume_percent = max(0, min(100, int(memorized)))
                self._state.muted = self._state.volume_percent == 0
        self._fallback_attempted = False
        self._select_engine()
        # Applied before load so a stream's first audible sample is already
        # at the user's level (the loaded callback re-applies it as well).
        self._engine.set_volume(self._effective_volume())
        self._set_state(RadioPlayerState.CONNECTING, message="")
        url = self._resolve_playback_url(station)
        if not self._engine.load(url) and not self._attempt_engine_fallback():
            self._set_state(RadioPlayerState.ERROR, message="That stream could not be opened.")

    def _select_engine(self) -> None:
        """Point ``self._engine`` at the backend the playback-engine
        preference (and the output-device choice) calls for, closing
        whichever engine is being switched away from.

        "auto" prefers mpv whenever libmpv is present (the same philosophy
        as the podcast/Audio Studio ``create_engine``) -- that is what
        delivers device routing, live pause/rewind, Volume Boost, and
        Ogg/Opus/HLS stations to everyone once libmpv ships in the app.
        "wx" is the classic escape hatch; "mpv" insists (with a spoken
        fallback when absent). A chosen output device also pulls in mpv
        even under "wx"-less auto, since no other backend can route it.
        """
        mpv_present = mpv_output_device_available()
        if self._playback_engine == "wx":
            wanted_mpv = False
        elif self._playback_engine == "mpv":
            wanted_mpv = mpv_present
        else:  # auto
            wanted_mpv = mpv_present
        # #5 observability: why a given backend was chosen for this station.
        _log.debug(
            "Radio engine selection: preference=%s, mpv_present=%s -> %s",
            self._playback_engine,
            mpv_present,
            "mpv" if wanted_mpv else "wx.media",
        )
        if wanted_mpv:
            if self._mpv_engine is None:
                try:
                    self._mpv_engine = MpvRadioEngine(
                        self._parent,
                        on_loaded=self._on_loaded,
                        on_finished=self._on_finished,
                        on_error=self._on_error,
                        audio_device=self._output_device,
                        on_buffering=self._on_buffering,
                    )
                except Exception:  # noqa: BLE001 - fall back, never fail playback
                    _log.exception("mpv radio engine unavailable; using wx.media")
            else:
                try:
                    self._mpv_engine.set_audio_device(self._output_device)
                except Exception:  # noqa: BLE001
                    _log.exception("audio-device switch failed")
        if wanted_mpv and self._mpv_engine is not None:
            if self._engine is not self._mpv_engine:
                self._engine.close()
                self._engine = self._mpv_engine
            return
        if self._on_output_device_error is not None:
            if bool(self._output_device) and self._playback_engine != "wx":
                self._on_output_device_error(
                    "The chosen radio output device could not be used; playing "
                    "through the system default instead."
                )
            elif self._playback_engine == "mpv":
                self._on_output_device_error(
                    "The mpv playback engine is not available; using Windows Media instead."
                )
        # Switch away only from the mpv engine (never from a test-injected
        # fake): in production the engine is always one of the two.
        if self._mpv_engine is not None and self._engine is self._mpv_engine:
            self._engine.close()
            self._engine = self._wx_engine

    def set_output_device(self, device: str) -> None:
        """Change the output device ("" = system default) and, if something
        is on, reconnect through the right engine -- live radio has no
        position to lose, so a reconnect is the whole cost (the same shape
        as ``set_enhancement``)."""
        device = device.strip()
        if device == self._output_device:
            return
        self._output_device = device
        station = self._state.station
        if station is not None and self._state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.CONNECTING,
            RadioPlayerState.PAUSED,
        ):
            self.play_station(station)

    def _current_filter_graph(self) -> str:
        """The Sound Enhancements ffmpeg graph for the current settings
        ("" = nothing engaged) -- the single source both delivery paths
        (relay and mpv-native ``af``) render from."""
        from quill.core.audio_enhance import build_filter_graph

        return build_filter_graph(
            self._eq_bass_db,
            self._eq_mid_db,
            self._eq_treble_db,
            compressor_enabled=self._compressor_enabled,
            channel_mode=self._channel_mode,
            night_mode_enabled=self._night_mode_enabled,
        )

    def _resolve_playback_url(self, station: RadioStation) -> str:
        """The URL the engine should load: the station's own URL, or a local
        relay URL when Sound Enhancements is active on the wx engine.

        On the mpv engine the graph applies natively (``af``) and the
        station URL is loaded directly -- no relay, no second ffmpeg
        process, no re-encode."""
        self._enhance_relay.stop()
        graph = self._current_filter_graph()
        if self._is_mpv_active():
            try:
                self._mpv_engine.set_filter_graph(graph)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001 - filtering must never block playback
                _log.exception("mpv filter graph apply failed")
            return station.stream_url
        if not graph:
            return station.stream_url
        try:
            return self._enhance_relay.start(
                station.stream_url,
                bass_db=self._eq_bass_db,
                mid_db=self._eq_mid_db,
                treble_db=self._eq_treble_db,
                compressor_enabled=self._compressor_enabled,
                channel_mode=self._channel_mode,
                night_mode_enabled=self._night_mode_enabled,
            )
        except EnhanceError as error:
            if self._on_enhance_error is not None:
                self._on_enhance_error(str(error))
            return station.stream_url

    def _is_mpv_active(self) -> bool:
        return self._mpv_engine is not None and self._engine is self._mpv_engine

    def _apply_sound_change(self) -> None:
        """Make a changed EQ/compressor/mono/night-mode setting heard.

        mpv engine: applied live via ``af`` -- no interruption at all.
        wx engine: the relay can only be restarted, so reconnect (live
        radio has no position to lose; a reconnect is the whole cost)."""
        if self._is_mpv_active():
            try:
                self._mpv_engine.set_filter_graph(self._current_filter_graph())  # type: ignore[union-attr]
                return
            except Exception:  # noqa: BLE001
                _log.exception("live mpv filter apply failed; reconnecting instead")
        station = self._state.station
        if station is not None and self._state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.CONNECTING,
            RadioPlayerState.PAUSED,
        ):
            self.play_station(station)

    def set_enhancement(
        self, *, bass_db: float, mid_db: float, treble_db: float, compressor_enabled: bool
    ) -> None:
        """Change the 3-band EQ / compressor. On the mpv engine the change
        is heard immediately with no interruption; on the wx engine a
        playing stream reconnects through the new relay."""
        self._eq_bass_db = bass_db
        self._eq_mid_db = mid_db
        self._eq_treble_db = treble_db
        self._compressor_enabled = compressor_enabled
        self._apply_sound_change()

    def set_sound_options(self, *, channel_mode: str, night_mode_enabled: bool) -> None:
        """Change the listener-level sound options (channel mode, night mode);
        same live-apply/reconnect behavior as ``set_enhancement``."""
        if (channel_mode, night_mode_enabled) == (self._channel_mode, self._night_mode_enabled):
            return
        self._channel_mode = channel_mode
        self._night_mode_enabled = night_mode_enabled
        self._apply_sound_change()

    def set_volume_boost(self, enabled: bool) -> bool:
        """Turn Volume Boost (amplify up to 50% past 100) on or off; the
        new level applies immediately. True when the boost can actually
        take effect (mpv engine active) -- the caller announces the
        difference."""
        self._volume_boost = enabled
        if not self._state.muted:
            self._engine.set_volume(self._effective_volume())
        return self._is_mpv_active()

    def _effective_volume(self) -> int:
        """What the engine should be told, honoring mute and Volume Boost
        (boost is only meaningful past 100 on the mpv engine; the wx engine
        clamps at 100, so sending the boosted value is safe everywhere)."""
        if self._state.muted:
            return 0
        percent = self._state.volume_percent
        return min(150, percent * 3 // 2) if self._volume_boost else percent

    # -- live DVR (mpv engine): pause is upstream; rewind/forward/live here --

    def rewind(self, seconds: int = 30) -> float | None:
        """Jump back within the live buffer. Returns how far behind live
        playback now is (seconds), or None when unavailable (wx engine or
        nothing playing) -- the caller announces either way."""
        return self._dvr_seek(-abs(seconds))

    def forward(self, seconds: int = 30) -> float | None:
        """Jump forward toward the live edge (after a rewind)."""
        return self._dvr_seek(abs(seconds))

    def _dvr_seek(self, seconds: int) -> float | None:
        if not self._is_mpv_active():
            return None
        engine = self._mpv_engine
        if engine is None or not engine.seek_relative(float(seconds)):
            return None
        return engine.behind_live_seconds()

    def jump_to_live(self) -> bool:
        """Return to the live edge. Prefers an in-cache seek; a stream
        whose cache cannot say where "live" is reconnects instead (a fresh
        connection is always live). False when nothing is playing."""
        station = self._state.station
        if station is None or self._state.state is RadioPlayerState.STOPPED:
            return False
        if self._is_mpv_active() and self._mpv_engine is not None:
            if self._mpv_engine.jump_to_live():
                return True
        self.play_station(station)
        return True

    def behind_live_seconds(self) -> float | None:
        """How far behind the live edge playback is, or None when unknown."""
        if not self._is_mpv_active() or self._mpv_engine is None:
            return None
        return self._mpv_engine.behind_live_seconds()

    def engine_track_title(self) -> str:
        """The engine's own idea of the current track (mpv ``media-title``)
        -- the fallback when the out-of-band ICY tap gets nothing. "" when
        unavailable."""
        if not self._is_mpv_active() or self._mpv_engine is None:
            return ""
        try:
            return self._mpv_engine.now_playing_title()
        except Exception:  # noqa: BLE001
            return ""

    def _attempt_engine_fallback(self) -> bool:
        """One cross-engine rescue per play attempt: retry the current
        station on the other backend. WMP cannot decode Ogg Vorbis, Opus,
        or HLS streams -- mpv rescues those; a broken mpv falls back to
        WMP. Returns True when a retry was started."""
        station = self._state.station
        if self._fallback_attempted or station is None:
            return False
        self._fallback_attempted = True
        if self._is_mpv_active():
            target = self._wx_engine
        elif mpv_output_device_available():
            if self._mpv_engine is None:
                try:
                    self._mpv_engine = MpvRadioEngine(
                        self._parent,
                        on_loaded=self._on_loaded,
                        on_finished=self._on_finished,
                        on_error=self._on_error,
                        audio_device=self._output_device,
                        on_buffering=self._on_buffering,
                    )
                except Exception:  # noqa: BLE001
                    _log.exception("mpv fallback engine unavailable")
                    return False
            target = self._mpv_engine
        else:
            return False
        _log.info("Retrying stream on the %s engine", "wx" if target is self._wx_engine else "mpv")
        self._engine.close()
        self._engine = target
        self._engine.set_volume(self._effective_volume())
        self._set_state(RadioPlayerState.CONNECTING, message="")
        url = self._resolve_playback_url(station)
        return bool(self._engine.load(url))

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
            self._state.muted = False
            # volume_percent was never zeroed by muting, so effective
            # volume restores the pre-mute level (boost-aware).
            self._engine.set_volume(self._effective_volume())
        else:
            self._pre_mute_volume = self._state.volume_percent
            self._state.muted = True
            self._engine.set_volume(0)
        self._notify()

    def set_volume(self, percent: int) -> None:
        """Internet Radio's own stream volume -- independent of the system
        volume mixer and of screen-reader speech volume; this only scales
        what QUILL itself is playing. The 0-100 user scale is preserved;
        Volume Boost multiplies it on the way to the engine."""
        percent = max(0, min(100, int(percent)))
        self._state.volume_percent = percent
        self._state.muted = percent == 0
        self._engine.set_volume(self._effective_volume())
        self._notify()

    def set_playback_engine(self, mode: str) -> None:
        """Change the engine preference ("auto"/"wx"/"mpv"); a playing
        station reconnects through the newly selected backend."""
        mode = mode if mode in ("auto", "wx", "mpv") else "auto"
        if mode == self._playback_engine:
            return
        self._playback_engine = mode
        station = self._state.station
        if station is not None and self._state.state in (
            RadioPlayerState.PLAYING,
            RadioPlayerState.CONNECTING,
            RadioPlayerState.PAUSED,
        ):
            self.play_station(station)

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
        self._engine.set_volume(self._effective_volume())
        self._engine.play()
        self._set_state(RadioPlayerState.PLAYING, message="")
        station = self._state.station
        if station is not None and station.station_uuid and self._on_register_click:
            uuid = station.station_uuid
            threading.Thread(target=self._on_register_click, args=(uuid,), daemon=True).start()

    def _on_finished(self) -> None:
        # A live stream reaching "finished" means the connection dropped.
        self._set_state(RadioPlayerState.STOPPED, message="The stream ended or disconnected.")

    def _on_error(self, message: str) -> None:
        # Before giving up, try the one cross-engine rescue: a stream WMP
        # cannot decode (Ogg/Opus/HLS) often plays fine on mpv, and vice
        # versa a misbehaving mpv falls back to WMP.
        if self._state.state is RadioPlayerState.CONNECTING and self._attempt_engine_fallback():
            return
        self._set_state(RadioPlayerState.ERROR, message=message)

    # -- internal -----------------------------------------------------------

    def _set_state(
        self,
        state: RadioPlayerState,
        *,
        station: RadioStation | None | Ellipsis = ...,  # type: ignore[valid-type]
        message: str = "",
    ) -> None:
        if station is not ...:
            self._state.station = station
        self._state.state = state
        self._state.message = message
        self._notify()

    def _notify(self) -> None:
        if self._on_state_changed is not None:
            self._on_state_changed(self._state)
