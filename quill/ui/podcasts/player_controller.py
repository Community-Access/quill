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

Sound Enhancements (EQ preset + compressor, see ``core/audio_enhance.py``)
reuses the same ffmpeg relay Radio uses, with one extra wrinkle: episodes
support seeking and a duration/scrub bar, which a live one-way relay has
neither of natively. Seeking while enhanced restarts the relay with an
ffmpeg ``-ss`` offset (:meth:`seek` falls through to a fresh
:meth:`play_episode`-shaped reload rather than the engine's own instant
seek); the reported duration comes from an independent ``ffprobe`` call
(:func:`~quill.core.audio_enhance.probe_source_duration_ms`) rather than the
engine, since the relay's own MP3 output never declares one.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import wx

from quill.core.audio.channel_mode import normalize as normalize_channel_mode
from quill.core.audio_enhance import (
    EnhanceError,
    EnhanceRelay,
    is_enhancement_active,
    probe_source_duration_ms,
)
from quill.core.spotify.models import is_spotify_uri
from quill.ui.audio.audio_engine import AudioEngine, create_engine

if TYPE_CHECKING:
    from quill.ui.spotify.web_player import SpotifyWebEngine

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
        on_position_checkpoint: Callable[[str, str, int], None] | None = None,
        before_play: Callable[[], None] | None = None,
        on_enhance_error: Callable[[str], None] | None = None,
        spotify_token_provider: Callable[[], str] | None = None,
    ) -> None:
        self._on_state_changed = on_state_changed
        #: Runs before every play_episode: the host stops sibling media (the
        #: radio player) here so two streams never play over each other.
        self._before_play = before_play
        #: (show_id, episode_guid) -- fired when an episode plays to the end,
        #: so the caller can mark it played / apply delete-after-play.
        self._on_episode_finished = on_episode_finished
        #: (show_id, episode_guid, position_ms) -- fired with the *outgoing*
        #: episode's position at pause/stop/switch/shutdown (never on natural
        #: finish; that is on_episode_finished's job). The fix for a real gap:
        #: episode.position_ms was read to resume but never written.
        self._on_position_checkpoint = on_position_checkpoint
        #: Told about a Sound Enhancements failure (ffmpeg missing, relay
        #: could not start) so the host can announce it; playback still
        #: proceeds unenhanced rather than failing outright.
        self._on_enhance_error = on_enhance_error
        self._resume_ms = 0
        self._pending_rate = 1.0
        self._pending_play_after_load = True
        self._volume_percent = 100
        self._muted = False
        self._pre_mute_volume = 100
        #: Live playback gain (Phase 4): scales what the engine hears without
        #: touching volume_percent, which the sleep timer restores -- boosting
        #: must never make "restore the volume" restore a boosted number.
        self._volume_boost = 1.0
        #: Sound Enhancements (3-band EQ + compressor + Smart Speed): off by
        #: default, so normal playback never spawns the ffmpeg relay. See
        #: set_enhancement.
        self._enhance_relay = EnhanceRelay()
        self._eq_bass_db = 0.0
        self._eq_mid_db = 0.0
        self._eq_treble_db = 0.0
        self._compressor_enabled = False
        self._smart_speed_enabled = False
        #: Where the audio comes out (stereo / mono / left / right). Shared
        #: vocabulary with Quill Radio -- see quill.core.audio.channel_mode.
        #: This is an accessibility setting before it is a sound one: mono
        #: keeps hard-panned content audible to someone listening with one
        #: ear, and the single-ear modes leave the other ear free for a
        #: screen reader.
        self._channel_mode = "stereo"
        #: The raw (unfiltered) source of whatever is loaded, so a seek or an
        #: enhancement change can restart the relay from the same episode.
        self._enhanced_source = ""
        #: The engine's own position is relative to wherever the current
        #: relay was started (an ffmpeg -ss offset), not the episode start.
        self._enhanced_offset_ms = 0
        #: Probed independently via ffprobe -- the relay's own MP3 output
        #: never declares a duration for the engine to compute one from.
        self._enhanced_duration_ms = 0
        self._engine: AudioEngine | None = create_engine(
            parent,
            on_loaded=self._on_loaded,
            on_finished=self._on_finished,
            on_error=self._on_error,
        )
        #: The mpv/wx stream engine stays the default; a spotify:episode: URI
        #: swaps ``self._engine`` to the Spotify Web Playback engine for the
        #: duration of that episode (DRM audio the stream engines cannot play).
        self._stream_engine = self._engine
        self._spotify_engine: SpotifyWebEngine | None = None
        self._spotify_token_provider = spotify_token_provider
        self._parent = parent
        self._state = PodcastPlaybackState(
            state=PodcastPlayerState.STOPPED, show_id=None, episode_guid=None, title=""
        )
        #: Auto-skip outro (PodcastSettings.auto_skip_outro_seconds, per-show):
        #: ends the episode that many ms before its own true end, exactly as
        #: if it had finished naturally (auto-advance, delete-after-play, ...
        #: all still fire via the same _on_finished path). A 1-second poll,
        #: not an engine event -- neither backend has a "N ms before the end"
        #: notification. _outro_fired guards against polling past the point
        #: _on_finished has already reset state for this episode.
        self._auto_skip_outro_ms = 0
        self._outro_fired = False
        self._outro_poll_timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._on_outro_poll, self._outro_poll_timer)
        self._outro_poll_timer.Start(1000)

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
        bass_db: float | None = None,
        mid_db: float | None = None,
        treble_db: float | None = None,
        compressor_enabled: bool | None = None,
        smart_speed_enabled: bool | None = None,
        channel_mode: str | None = None,
        auto_skip_intro_ms: int = 0,
        auto_skip_outro_ms: int = 0,
    ) -> None:
        """Start (or switch to) playing one episode; replaces whatever this
        controller was already playing, so only one thing ever plays. The
        ``before_play`` hook additionally silences sibling media (the radio
        player). The enhancement kwargs are optional and, when given
        (callers resolve them from ``PodcastLibrary.effective_settings``),
        make this show's own Sound Enhancements take effect for this
        episode -- omitted, playback keeps whatever ``set_enhancement`` last
        applied. ``auto_skip_intro_ms`` only applies to a fresh start
        (``resume_ms <= 0``) -- resuming a checkpointed position must never
        jump past where you actually left off."""
        if self._before_play is not None:
            try:
                self._before_play()
            except Exception:  # noqa: BLE001 - a sibling-stop must never block play
                pass
        self._checkpoint_current()
        if bass_db is not None:
            self._eq_bass_db = bass_db
        if mid_db is not None:
            self._eq_mid_db = mid_db
        if treble_db is not None:
            self._eq_treble_db = treble_db
        if compressor_enabled is not None:
            self._compressor_enabled = compressor_enabled
        if smart_speed_enabled is not None:
            self._smart_speed_enabled = smart_speed_enabled
        if channel_mode is not None:
            self._channel_mode = normalize_channel_mode(channel_mode)
        self._pending_rate = rate if rate > 0 else 1.0
        self._pending_play_after_load = True
        self._state.show_id = show_id
        self._state.episode_guid = episode_guid
        self._state.title = title
        self._set_state(PodcastPlayerState.LOADING)
        self._enhanced_source = source
        self._enhanced_duration_ms = probe_source_duration_ms(source) if self._is_enhanced() else 0
        self._auto_skip_outro_ms = max(0, int(auto_skip_outro_ms))
        self._outro_fired = False
        start_ms = max(0, int(resume_ms))
        if start_ms <= 0 and auto_skip_intro_ms > 0:
            start_ms = int(auto_skip_intro_ms)
        self._start_load(source, start_ms=start_ms)

    def _start_load(self, source: str, *, start_ms: int) -> None:
        self._resume_ms = start_ms
        # A spotify:episode: URI is DRM audio only the Spotify Web Playback
        # engine can play; load the URI directly (no relay/enhancement) and
        # never fall through to the stream engine.
        if is_spotify_uri(source):
            spotify = self._select_spotify_engine()
            if spotify is None or not spotify.load(source):
                self._set_state(
                    PodcastPlayerState.ERROR,
                    message=(
                        "That Spotify episode could not be played. "
                        "Spotify Premium sign-in is required."
                    ),
                )
            return
        self._select_stream_engine()
        url = self._resolve_playback_url(source, start_ms=start_ms)
        if self._engine is None or not self._engine.load(url):
            self._set_state(PodcastPlayerState.ERROR, message="That episode could not be opened.")

    def _ensure_spotify_engine(self) -> SpotifyWebEngine | None:
        """Lazily create the Spotify engine, or None if no token source (not
        signed in to Spotify)."""
        if self._spotify_engine is not None:
            return self._spotify_engine
        if self._spotify_token_provider is None:
            return None
        from quill.ui.spotify.web_player import SpotifyWebEngine

        self._spotify_engine = SpotifyWebEngine(
            self._parent,
            token_provider=self._spotify_token_provider,
            on_error=self._on_error,
        )
        return self._spotify_engine

    def _select_spotify_engine(self) -> SpotifyWebEngine | None:
        """Make the Spotify engine the active engine (stream engine stays alive
        for the next non-Spotify episode)."""
        spotify = self._ensure_spotify_engine()
        if spotify is not None:
            self._engine = spotify
        return spotify

    def _select_stream_engine(self) -> None:
        """Restore the mpv/wx stream engine as the active engine when leaving a
        Spotify episode. Only swaps back *from* the Spotify engine, so any other
        active engine (including a test-injected fake) is left in place."""
        if self._spotify_engine is not None and self._engine is self._spotify_engine:
            self._engine = self._stream_engine

    def _is_enhanced(self) -> bool:
        return is_enhancement_active(
            self._eq_bass_db,
            self._eq_mid_db,
            self._eq_treble_db,
            compressor_enabled=self._compressor_enabled,
            smart_speed_enabled=self._smart_speed_enabled,
            channel_mode=self._channel_mode,
        )

    def _resolve_playback_url(self, source: str, *, start_ms: int) -> str:
        """The URL the engine should load: *source* itself, or a local relay
        URL when Sound Enhancements is active (started at *start_ms*, since
        a relay can only be resumed by restarting it at a new ffmpeg -ss
        offset -- there is no way to seek within one already running)."""
        self._enhance_relay.stop()
        self._enhanced_offset_ms = 0
        if not self._is_enhanced():
            return source
        try:
            url = self._enhance_relay.start(
                source,
                bass_db=self._eq_bass_db,
                mid_db=self._eq_mid_db,
                treble_db=self._eq_treble_db,
                compressor_enabled=self._compressor_enabled,
                smart_speed_enabled=self._smart_speed_enabled,
                channel_mode=self._channel_mode,
                start_seconds=start_ms / 1000.0,
            )
            self._enhanced_offset_ms = start_ms
            return url
        except EnhanceError as error:
            if self._on_enhance_error is not None:
                self._on_enhance_error(str(error))
            return source

    def set_enhancement(
        self,
        *,
        bass_db: float,
        mid_db: float,
        treble_db: float,
        compressor_enabled: bool,
        smart_speed_enabled: bool = False,
        channel_mode: str | None = None,
    ) -> None:
        """Change the 3-band EQ / compressor / Smart Speed / channel mode and,
        if an episode is loaded, reload it (through the new relay state, or
        straight from the source if turned off) at the position it was just
        at."""
        current_position = self.position_ms()
        was_playing = self._state.state is PodcastPlayerState.PLAYING
        source = self._enhanced_source
        self._eq_bass_db = bass_db
        self._eq_mid_db = mid_db
        self._eq_treble_db = treble_db
        self._compressor_enabled = compressor_enabled
        self._smart_speed_enabled = smart_speed_enabled
        if channel_mode is not None:
            self._channel_mode = normalize_channel_mode(channel_mode)
        if not source or self._state.show_id is None:
            return
        self._enhanced_duration_ms = probe_source_duration_ms(source) if self._is_enhanced() else 0
        self._pending_play_after_load = was_playing
        self._set_state(PodcastPlayerState.LOADING)
        self._start_load(source, start_ms=current_position)

    def channel_mode(self) -> str:
        """Where the audio is currently coming out (stereo/mono/left/right)."""
        return self._channel_mode

    def set_channel_mode(self, mode: str) -> str:
        """Change only the channel mode, keeping your place. Returns it.

        Changing it means restarting the ffmpeg relay -- there is no way to
        alter a running one -- so this reloads at the current position rather
        than from the top. Someone forty minutes into an episode who switches
        to mono must not be sent back to the beginning to get there.
        """
        resolved = normalize_channel_mode(mode)
        if resolved == self._channel_mode:
            return resolved
        self.set_enhancement(
            bass_db=self._eq_bass_db,
            mid_db=self._eq_mid_db,
            treble_db=self._eq_treble_db,
            compressor_enabled=self._compressor_enabled,
            smart_speed_enabled=self._smart_speed_enabled,
            channel_mode=resolved,
        )
        return resolved

    def toggle_play_pause(self) -> None:
        if self._engine is None:
            return
        if self._state.state is PodcastPlayerState.PLAYING:
            self._checkpoint_current()
            self._engine.pause()
            self._set_state(PodcastPlayerState.PAUSED)
        elif self._state.state is PodcastPlayerState.PAUSED:
            self._engine.play()
            self._set_state(PodcastPlayerState.PLAYING)

    def stop(self) -> None:
        self._checkpoint_current()
        if self._engine is not None:
            self._engine.close()
        self._enhance_relay.stop()
        self._state.show_id = None
        self._state.episode_guid = None
        self._state.title = ""
        self._enhanced_source = ""
        self._enhanced_duration_ms = 0
        self._set_state(PodcastPlayerState.STOPPED)

    def seek(self, ms: int) -> None:
        if self._engine is None:
            return
        if not self._is_enhanced():
            self._engine.seek(ms)
            return
        # Enhanced: there is no seeking within an already-running relay, so
        # scrubbing restarts it at the new offset -- an async reload (fires
        # _on_loaded), not the engine's normal instant seek.
        self._pending_play_after_load = self._state.state is PodcastPlayerState.PLAYING
        self._set_state(PodcastPlayerState.LOADING)
        self._start_load(self._enhanced_source, start_ms=max(0, ms))

    def set_rate(self, rate: float) -> None:
        if self._engine is not None:
            self._engine.set_rate(rate)

    def set_volume(self, percent: int) -> None:
        self._muted = False
        self._volume_percent = max(0, min(100, percent))
        self._apply_engine_volume()

    def toggle_mute(self) -> None:
        """Mirrors ``RadioPlayerController.toggle_mute``: silence without
        losing the level, restored exactly on the next toggle."""
        if self._muted:
            self._muted = False
            self._volume_percent = self._pre_mute_volume
        else:
            self._pre_mute_volume = self._volume_percent
            self._muted = True
            self._volume_percent = 0
        self._apply_engine_volume()

    @property
    def muted(self) -> bool:
        return self._muted

    def set_volume_boost(self, factor: float) -> None:
        """Live playback gain (0.5x - 3.0x, clamped) for quiet audio; scales
        the engine volume only. ``volume_percent`` keeps reporting the
        unboosted value so the sleep timer's restore stays honest."""
        self._volume_boost = max(0.5, min(3.0, float(factor)))
        self._apply_engine_volume()

    def _apply_engine_volume(self) -> None:
        if self._engine is not None:
            boosted = round(self._volume_percent * self._volume_boost)
            self._engine.set_volume(min(100, boosted))

    @property
    def volume_percent(self) -> int:
        return self._volume_percent

    def position_ms(self) -> int:
        if self._engine is None:
            return 0
        if self._is_enhanced():
            return self._enhanced_offset_ms + self._engine.position_ms()
        return self._engine.position_ms()

    def length_ms(self) -> int:
        if self._is_enhanced() and self._enhanced_duration_ms:
            return self._enhanced_duration_ms
        return self._engine.length_ms() if self._engine is not None else 0

    def is_playing(self) -> bool:
        return self._engine.is_playing() if self._engine is not None else False

    @property
    def rate(self) -> float:
        """The playback speed in force (1.0 = normal).

        Read from the pending rate rather than the engine: the engine only
        learns the rate once media is loaded, so asking it during a load
        reports 1.0 for an episode the listener set to 1.5.
        """
        return float(self._pending_rate or 1.0)

    def shutdown(self) -> None:
        """Release the engine; called once, from the frame's close path."""
        self._checkpoint_current()
        try:
            if self._engine is not None:
                self._engine.close()
        except Exception:  # noqa: BLE001 - never block app close
            _log.exception("podcast engine close failed during shutdown")
        # Close the Spotify WebView engine if it exists and was not the active
        # engine just closed above (tears down the hidden WebView + page host).
        if self._spotify_engine is not None and self._engine is not self._spotify_engine:
            try:
                self._spotify_engine.close()
            except Exception:  # noqa: BLE001 - never block app close
                _log.exception("Spotify engine close failed during shutdown")
        self._spotify_engine = None
        try:
            self._enhance_relay.shutdown()
        except Exception:  # noqa: BLE001 - never block app close
            _log.exception("podcast enhancement relay shutdown failed")
        self._outro_poll_timer.Stop()

    def _checkpoint_current(self) -> None:
        """Report the current episode's position to the checkpoint callback
        (no-op when nothing is loaded or nothing listens)."""
        if self._on_position_checkpoint is None:
            return
        show_id, episode_guid = self._state.show_id, self._state.episode_guid
        if not show_id or not episode_guid or self._engine is None:
            return
        self._on_position_checkpoint(show_id, episode_guid, self.position_ms())

    def _on_outro_poll(self, _event: object) -> None:
        """Auto-skip outro: ends the episode auto_skip_outro_ms early, exactly
        as if it had reached its own true end -- see play_episode's
        auto_skip_outro_ms docstring."""
        if self._outro_fired or self._auto_skip_outro_ms <= 0:
            return
        if self._state.state is not PodcastPlayerState.PLAYING:
            return
        length = self.length_ms()
        if length <= 0 or self.position_ms() < length - self._auto_skip_outro_ms:
            return
        self._outro_fired = True
        if self._engine is not None:
            self._engine.close()
        self._enhance_relay.stop()
        self._on_finished()

    # -- engine callbacks -------------------------------------------------

    def _on_loaded(self, _length_ms: int) -> None:
        if self._engine is None:
            return
        if self._is_enhanced():
            # The relay already started at the right offset via ffmpeg -ss;
            # nothing to seek, just play or pause per the caller's intent.
            self._engine.play() if self._pending_play_after_load else self._engine.pause()
        elif self._resume_ms:
            # resume=<intent>, not hardcoded True: a seek/enhancement-toggle
            # reload while paused must land back on PAUSED, not force play.
            self._engine.seek(self._resume_ms, resume=self._pending_play_after_load)
        elif self._pending_play_after_load:
            self._engine.play()
        else:
            self._engine.pause()
        self._resume_ms = 0
        self._engine.set_rate(self._pending_rate)
        self._set_state(
            PodcastPlayerState.PLAYING
            if self._pending_play_after_load
            else PodcastPlayerState.PAUSED
        )

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
