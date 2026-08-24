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
from dataclasses import replace
from typing import TYPE_CHECKING, Any, NamedTuple

import wx

from quill.core.audio import exact_optilab
from quill.core.audio.exact_optilab import ExactOptilab
from quill.core.audio_enhance import EnhanceError, EnhanceRelay
from quill.core.optilab import optilab_active
from quill.core.radio.models import RadioStation
from quill.core.sound_events import SoundEvent
from quill.core.spotify.models import is_spotify_uri
from quill.ui.audio.audio_engine import WxMediaEngine
from quill.ui.companion_cues import post_cue
from quill.ui.radio import media_preflight, stream_stall
from quill.ui.radio.mpv_radio_engine import MpvRadioEngine
from quill.ui.radio.playback_state import (
    RESTARTABLE_STATES,
    RUNNING_STATES,
    RadioPlaybackState,
    RadioPlayerState,
)
from quill.ui.radio.player_tracks import PlayerTracksMixin
from quill.ui.radio.youtube_playback import begin_youtube_play, consent_granted, is_youtube_station

if TYPE_CHECKING:
    from quill.ui.spotify.web_player import SpotifyWebEngine

_log = logging.getLogger(__name__)

#: How far into a chapter "previous chapter" restarts it instead of stepping
#: back. Every other player behaves this way, and the alternative -- skipping
#: to the previous chapter from ten minutes into this one -- is never what
#: someone pressing it twice actually wants.
_CHAPTER_RESTART_MS = 3000


class ResolvedEnhancement(NamedTuple):
    """Every Sound Enhancements setting resolved for a station about to play --
    its own per-station override if it is a favorite with one, else the shared
    default. Every field is per-stream as well as global (see the host's
    ``_radio_resolve_enhancement``)."""

    bass_db: float = 0.0
    mid_db: float = 0.0
    treble_db: float = 0.0
    compressor_enabled: bool = False
    channel_mode: str = "stereo"
    night_mode_enabled: bool = False
    optilab_enabled: bool = False
    optilab_mode: str = "off"
    optilab_input_db: float = 0.0
    optilab_auto_adapt: int = 0
    #: Exact OptiLab processing: the real engine instead of the ffmpeg
    #: adaptation. ``optilab_exact`` covers **saved files** (recordings and
    #: conversion) and is what the host reads when it starts a recording;
    #: ``optilab_exact_live`` additionally routes *listening* through the engine,
    #: which costs the gapless preview and adds a short delay, so it is a
    #: separate, deliberate choice rather than a consequence of the first.
    optilab_exact: bool = False
    optilab_exact_live: bool = False


# The state model moved to its own module when BUFFERING and RECONNECTING
# joined it -- see playback_state.py for why. Imported by name rather than
# through a star, so a reader can see what this module consumes and the
# twenty modules that import these from here keep working unchanged.


#: The earcon each playback state gets (#1302). This is the only place that
#: knows a stream reached the air: connecting, playing, stopping and failing
#: are states the app changes through without saying a word (the status bar
#: text updates and nothing is spoken), so a listener had to infer them from
#: silence. PAUSED is deliberately absent -- pausing is a keypress that already
#: announces itself, and a cue there would just double up.
_STATE_SOUNDS: dict[RadioPlayerState, str] = {
    RadioPlayerState.CONNECTING: SoundEvent.RADIO_CONNECTING,
    RadioPlayerState.PLAYING: SoundEvent.RADIO_PLAYING,
    RadioPlayerState.STOPPED: SoundEvent.RADIO_STOPPED,
    RadioPlayerState.ERROR: SoundEvent.RADIO_STREAM_ERROR,
}


class RadioPlayerController(PlayerTracksMixin):
    """Play/pause/stop/mute one internet-radio stream at a time.

    Audio renditions and captions come from :class:`PlayerTracksMixin`, split
    out under GATE-11 when Skip Silence pushed this module past its ceiling.
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        on_state_changed: Callable[[RadioPlaybackState], None] | None = None,
        on_register_click: Callable[[str], None] | None = None,
        before_play: Callable[[], None] | None = None,
        on_enhance_error: Callable[[str], None] | None = None,
        resolve_enhancement: Callable[[RadioStation], ResolvedEnhancement] | None = None,
        resolve_volume: Callable[[RadioStation], int] | None = None,
        output_device: str = "",
        on_output_device_error: Callable[[str], None] | None = None,
        playback_engine: str = "auto",
        on_buffering: Callable[[], None] | None = None,
        spotify_token_provider: Callable[[], str] | None = None,
        resolve_youtube: Callable[[str], Any] | None = None,
        youtube_consent: Callable[[], bool] | None = None,
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
        #: Turns a YouTube page link into a playable stream URL (#1268).
        #: Injected by the host because it needs the listener's one-time
        #: consent and the on-demand yt-dlp install, neither of which belongs
        #: in a playback controller. Called on a worker thread -- the resolve
        #: is a network round trip -- so the UI never freezes on it. None
        #: means YouTube support is unavailable and such a station reports a
        #: clean error instead of loading a web page into the audio engine.
        self._resolve_youtube = resolve_youtube
        #: Asks the listener's one-time YouTube consent, on the UI thread,
        #: *before* the resolve is started. It used to be asked only by Add
        #: Custom Station, so every other way to reach a YouTube row -- a
        #: followed channel's uploads, a saved video, a favorite, a search
        #: result -- refused at play time with a message naming a dialog the
        #: listener was not in. Returning False means they declined and
        #: nothing plays; None (an embedded controller with no host) means
        #: the question cannot be asked, and the resolver's own guard stands.
        self._youtube_consent = youtube_consent
        #: The short-lived URL the engine is actually loading when it differs
        #: from the station's own (a resolved YouTube stream). Kept apart from
        #: ``_state.station`` so favorites, the recorder, and the now-playing
        #: line all keep the durable page URL, and so the one cross-engine
        #: rescue reuses the resolved URL instead of resolving twice.
        self._playback_url_override = ""
        #: Bumped by every play/stop so a YouTube resolve that finishes after
        #: the listener moved on is discarded instead of hijacking playback.
        self._play_token = 0
        #: One cross-engine rescue per play attempt: a stream the current
        #: engine cannot open is retried once on the other engine before an
        #: error is declared (WMP cannot decode Ogg/Opus/HLS; a broken mpv
        #: falls back to WMP). Reset by every play_station.
        self._fallback_attempted = False
        #: The resolved YouTube stream for the current play, when the station
        #: was a YouTube link and the resolver handed back its metadata. This
        #: is what carries the video's length and its published chapters.
        #: None for every ordinary station, and for a live YouTube stream it
        #: reports no duration -- which is the honest answer.
        self._youtube_stream: Any = None
        #: The audio rendition the listener chose for this station, or None
        #: for whichever the resolver picked. Cleared on every new play, so
        #: a described track chosen for one video never silently applies to
        #: the next.
        self._selected_audio_track: Any = None
        #: Playback speed for bounded sources (1.0 = normal). Live radio
        #: ignores it: a broadcast plays at broadcast speed.
        self._playback_rate = 1.0
        #: Skip Silence for bounded playback (11.7). Set from the app's
        #: remembered preference at startup and by the Playback menu toggle;
        #: ignored for live radio, which has no pauses left to skip.
        self._skip_silence = False
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
        #: Spotify Web Playback engine (DRM audio in a hidden WebView), created
        #: lazily the first time a ``spotify:`` station plays. Needs a token
        #: provider injected by the host (which reads the stored OAuth token);
        #: without one, a Spotify station cannot play and selection falls back.
        self._spotify_engine: SpotifyWebEngine | None = None
        self._spotify_token_provider = spotify_token_provider
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
        # OptiLab broadcast-polish (global listener option, like night mode):
        # a bypass flag plus the chosen mode / input trim / auto-adapt.
        self._optilab_enabled = False
        self._optilab_mode = "off"
        self._optilab_input_db = 0.0
        self._optilab_auto_adapt = 0
        #: Route live listening through the real OptiLab engine (opt-in). See
        #: ``_resolve_playback_url``: it forces the relay even on mpv, because
        #: mpv has no way to host someone else's DSP -- the engine is a separate
        #: process and the audio has to physically pass through it.
        self._optilab_exact_live = False
        #: Volume Boost: amplify up to 50% past 100 (mpv engine only; the
        #: wx engine clamps at 100, so it silently does nothing there).
        self._volume_boost = False
        self._pre_mute_volume = 100
        self._state = RadioPlaybackState(
            state=RadioPlayerState.STOPPED, station=None, muted=False, volume_percent=100
        )
        #: Where you stopped, for stations that are recordings rather than live
        #: streams. Created lazily so a controller built in a test without a
        #: data directory never touches the disk.
        self._resume_store: object | None = None
        #: Set when a recording starts with a saved position, and consumed once
        #: the engine reports it is ready to seek.
        self._pending_resume_ms = 0

    @property
    def state(self) -> RadioPlaybackState:
        return self._state

    def play_station(self, station: RadioStation) -> None:
        """Start (or switch to) playing *station*.

        Replaces whatever this controller was playing; the ``before_play``
        hook additionally silences sibling media (the podcast player) so two
        streams never play over each other.

        A YouTube station (#1268) needs a network resolve first, so it takes the
        asynchronous path: state goes to CONNECTING immediately, the resolve runs
        on a worker thread, and playback starts when it lands. Every other
        station plays synchronously, exactly as before.
        """
        if is_youtube_station(station) and not consent_granted(self):
            return  # declined: the ask says so out loud, and nothing changes
        self._play_token += 1
        self._playback_url_override = ""
        # Last play's video facts must not describe this one: a station tuned
        # after a video would otherwise look seekable and carry its chapters.
        self._youtube_stream = None
        if is_youtube_station(station):
            begin_youtube_play(self, station, token=self._play_token)
            return
        self._play_resolved_station(station)

    def _play_resolved_station(self, station: RadioStation) -> None:
        """Play *station* now -- its URL (or ``_playback_url_override``) is playable."""
        if self._before_play is not None:
            try:
                self._before_play()
            except Exception:  # noqa: BLE001 - a sibling-stop must never block play
                pass
        if self._resolve_enhancement is not None:
            resolved = self._resolve_enhancement(station)
            self._eq_bass_db = resolved.bass_db
            self._eq_mid_db = resolved.mid_db
            self._eq_treble_db = resolved.treble_db
            self._compressor_enabled = resolved.compressor_enabled
            self._channel_mode = resolved.channel_mode
            # Night mode and OptiLab are per-stream too (resolved here), each
            # falling back to the shared default when the station has no override.
            self._night_mode_enabled = resolved.night_mode_enabled
            self._optilab_enabled = resolved.optilab_enabled
            self._optilab_mode = resolved.optilab_mode
            self._optilab_input_db = resolved.optilab_input_db
            self._optilab_auto_adapt = resolved.optilab_auto_adapt
            self._optilab_exact_live = resolved.optilab_exact_live
        # Leaving a recording? Keep the place before the station changes.
        self._remember_resume_point()
        self._state.station = station
        self._pending_resume_ms = self._saved_resume_ms(station)
        if self._resolve_volume is not None:
            memorized = self._resolve_volume(station)
            if memorized >= 0:
                self._state.volume_percent = max(0, min(100, int(memorized)))
                self._state.muted = self._state.volume_percent == 0
        self._fallback_attempted = False
        self._selected_audio_track = None
        # A deliberate play is a fresh start: any reconnect count left over
        # from a station the listener has moved on from must not make the next
        # successful load announce "Reconnected".
        from quill.ui.radio import live_reconnect

        live_reconnect.reset(self)
        self._select_engine()
        # Applied before load so a stream's first audible sample is already
        # at the user's level (the loaded callback re-applies it as well).
        self._engine.set_volume(self._effective_volume())
        self._set_state(RadioPlayerState.CONNECTING, message="")
        url = self._resolve_playback_url(station)
        # A spotify: URI can only play on the Spotify engine, so the
        # cross-engine rescue (which retries on wx/mpv) never applies to it.
        if self._is_spotify_station(station):
            if not self._engine.load(url):
                self._set_state(
                    RadioPlayerState.ERROR,
                    message=(
                        "That Spotify item could not be played. "
                        "Spotify Premium sign-in is required."
                    ),
                )
            return
        if not self._engine.load(url) and not self._attempt_engine_fallback():
            # "That stream could not be opened" is true and useless when the
            # real reason is that the container needs libmpv and libmpv is not
            # here: the station is fine, the machine cannot open it, and the
            # next action is a reinstall rather than another station.
            refusal = media_preflight.refusal_for(getattr(station, "name", ""), url)
            self._set_state(
                RadioPlayerState.ERROR,
                message=refusal or "That stream could not be opened.",
            )
            return
        self._declare_source_shape()

    def _declare_source_shape(self) -> None:
        """Tell the engine whether what it just loaded has a timeline.

        A recording can be scrubbed, sped up, navigated by chapter and resumed;
        a live broadcast cannot, because it has no end to measure against.
        Which one a YouTube link is only becomes known when yt-dlp answers --
        after the engine has been chosen -- so the engine is told
        here, immediately after the load, rather than the play path being
        rebuilt to choose an engine later.

        Everything that is not a resolved, finished video is left exactly as
        it was: engines without the capability are skipped, and an ordinary
        station never reaches the bounded branch at all.
        """
        declare = getattr(self._engine, "set_bounded", None)
        if declare is None:
            return
        stream = self._youtube_stream
        # Read the current station defensively: this runs immediately after a
        # load, and a partially-built controller (as the transport tests use)
        # has no state object yet. A missing station simply means "not a
        # recording", which is the safe answer.
        current = getattr(self, "_state", None)
        station = getattr(current, "station", None)
        # Two ways to be bounded, and both are declared here. A YouTube link is
        # only known to be a finished video once yt-dlp answers; everything else
        # says so up front, because the source that produced the row knows what
        # it produced -- an Archive item, a LibriVox chapter and a podcast
        # episode are recordings, and an Icecast mount never is.
        bounded = bool(stream is not None and getattr(stream, "duration_ms", 0) > 0)
        bounded = bounded or bool(station is not None and getattr(station, "is_recording", False))
        declare(bounded)
        if bounded and self._playback_rate != 1.0:
            # Re-apply the chosen speed: load() resets mpv's speed so a video
            # left at 2x cannot carry that into the next live station.
            self._engine.set_rate(self._playback_rate)
        if bounded:
            # The shared library's knowledge for a podcast episode: the show's
            # saved speed, and its Podcasting 2.0 chapters (episode_profile).
            from quill.ui.radio import episode_profile

            episode_profile.apply_profile(self)

    # -- resume: where you stopped in a recording -------------------------------
    # The logic lives in quill/ui/radio/resume_playback.py; this module is at its
    # GATE-11 ceiling and the concern is self-contained.

    def _remember_resume_point(self) -> None:
        """Save where the current recording reached, if it is one."""
        from quill.ui.radio import resume_playback

        resume_playback.remember(self)

    def _saved_resume_ms(self, station: object) -> int:
        """The position to resume *station* at, or 0."""
        from quill.ui.radio import resume_playback

        return resume_playback.saved_position_ms(station)

    def take_pending_resume_ms(self) -> int:
        """The position this playback should start at, consumed once.

        The engine cannot seek until it knows the media's length, which arrives
        after the load; whoever notices that -- the loaded callback -- asks for
        this and seeks. Consumed rather than read so a second load, or a station
        that turns out not to be seekable, cannot resurrect a stale offset.
        """
        pending, self._pending_resume_ms = self._pending_resume_ms, 0
        return pending if self.is_seekable() else 0

    def forget_resume_point(self, station: object | None = None) -> None:
        """Start this recording from the beginning next time."""
        from quill.ui.radio import resume_playback

        resume_playback.forget(self, station)

    # -- bounded playback: seeking, speed, and chapters --------------------------

    def is_seekable(self) -> bool:
        """Whether what is playing has a timeline to move along.

        True for a finished video and for any station a source marked as a
        recording. Every ordinary radio station and every live YouTube stream is
        False, which is what keeps the transport honest rather than offering a
        slider that cannot move.
        """
        probe = getattr(self._engine, "is_bounded", None)
        return bool(probe()) if probe is not None else False

    def duration_ms(self) -> int:
        """Length of what is playing, or 0 when it has none (live)."""
        return int(self._engine.length_ms()) if self.is_seekable() else 0

    def position_ms(self) -> int:
        """Where playback is now, in milliseconds (0 when the engine can't say).

        The public form of what the transport surfaces used to reach into the
        engine for directly (#1344).
        """
        probe = getattr(self._engine, "position_ms", None)
        if not callable(probe):
            return 0
        try:
            return max(0, int(probe()))
        except Exception:  # noqa: BLE001 - a position is never worth an exception
            return 0

    def seek_to(self, ms: int) -> bool:
        """Jump to an absolute position. False when there is nothing to seek."""
        if not self.is_seekable():
            return False
        total = self.duration_ms()
        self._engine.seek(max(0, min(int(ms), total)) if total else max(0, int(ms)))
        return True

    def skip_by(self, ms: int) -> bool:
        """Jump *ms* forward (negative rewinds), clamped to the timeline."""
        if not self.is_seekable():
            return False
        return self.seek_to(int(self._engine.position_ms()) + int(ms))

    def skip_silence(self) -> bool:
        """Whether Skip Silence is on (it applies to bounded playback only)."""
        return self._skip_silence

    def set_skip_silence(self, enabled: bool) -> bool:
        """Turn Skip Silence on or off, heard immediately. Returns the state.

        The filter is part of the same graph Sound Enhancements renders, so
        on the mpv engine this takes effect on what is already playing with
        no interruption -- ``_apply_sound_change`` is the one path either way.
        """
        wanted = bool(enabled)
        if wanted == self._skip_silence:
            return self._skip_silence
        self._skip_silence = wanted
        self._apply_sound_change()
        return self._skip_silence

    def playback_rate(self) -> float:
        """The current speed for bounded sources (1.0 = normal)."""
        return self._playback_rate

    def set_playback_rate(self, rate: float) -> float:
        """Set playback speed, clamped to mpv's usable 0.25x-4x. Returns it.

        Remembered across stations so a listener who prefers 1.5x keeps it,
        and re-applied after each bounded load.
        """
        self._playback_rate = max(0.25, min(4.0, float(rate)))
        if self.is_seekable():
            self._engine.set_rate(self._playback_rate)
        return self._playback_rate

    def go_to_chapter(self, index: int) -> bool:
        """Jump to a chapter by index. False when the index does not exist."""
        chapters = self.chapters()
        if not 0 <= index < len(chapters):
            return False
        return self.seek_to(int(getattr(chapters[index], "start_ms", 0)))

    def go_to_adjacent_chapter(self, delta: int) -> int:
        """Move *delta* chapters from the current one; returns the new index.

        Returns -1 when there is nowhere to go. Previous-chapter deliberately
        restarts the current chapter when the playhead is already well inside
        it, which is what a listener means by "previous" on any other player.
        """
        chapters = self.chapters()
        if not chapters:
            return -1
        current = self.current_chapter_index()
        if delta < 0 and current >= 0:
            start = int(getattr(chapters[current], "start_ms", 0))
            if int(self._engine.position_ms()) - start > _CHAPTER_RESTART_MS:
                return current if self.go_to_chapter(current) else -1
        target = (0 if current < 0 else current) + delta
        target = max(0, min(target, len(chapters) - 1))
        return target if self.go_to_chapter(target) else -1

    def current_playback_url(self) -> str:
        """The URL actually being played -- resolved, if the station needed it.

        The recorder wants this, not ``state.station.stream_url``: for a YouTube
        station those differ, and handing ffmpeg the page URL would record an
        HTML document. "" when nothing is playing.
        """
        station = self._state.station
        if station is None:
            return ""
        return self._playback_url_override or station.stream_url

    @staticmethod
    def _is_spotify_station(station: RadioStation | None) -> bool:
        """True when *station* plays a ``spotify:`` URI (Spotify-engine only)."""
        return station is not None and is_spotify_uri(station.stream_url)

    def _ensure_spotify_engine(self) -> SpotifyWebEngine | None:
        """Lazily create the Spotify Web Playback engine, or None if the host
        provided no token source (Spotify not signed in)."""
        if self._spotify_engine is not None:
            return self._spotify_engine
        if self._spotify_token_provider is None:
            return None
        from quill.ui.spotify.web_player import SpotifyWebEngine

        self._spotify_engine = SpotifyWebEngine(
            self._parent,
            token_provider=self._spotify_token_provider,
            on_playback=self._on_spotify_playback,
            on_error=self._on_error,
        )
        return self._spotify_engine

    def _on_spotify_playback(self, snapshot: object) -> None:
        """Reflect a Spotify SDK snapshot into the shared playback state so the
        status-bar mini-player and tray track play/pause exactly as for a
        stream (the station's own name is already the status label)."""
        if self._engine is not self._spotify_engine:
            return
        is_playing = bool(getattr(snapshot, "is_playing", False))
        if is_playing and self._state.state is not RadioPlayerState.PLAYING:
            self._set_state(RadioPlayerState.PLAYING, message="")
        elif not is_playing and self._state.state is RadioPlayerState.PLAYING:
            self._set_state(RadioPlayerState.PAUSED, message="")

    def _select_engine(self) -> None:
        """Point ``self._engine`` at the backend this station needs.

        The decision lives in :mod:`quill.ui.radio.engine_selection`, with the
        one-per-attempt cross-engine rescue it belongs with; this module is at
        its GATE-11 ceiling and the pair is a self-contained concern.
        """
        from quill.ui.radio import engine_selection

        engine_selection.select(self)

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
        if station is not None and self._state.state in RESTARTABLE_STATES:
            self.play_station(station)

    def _current_filter_graph(self) -> str:
        """The Sound Enhancements ffmpeg graph for the current settings
        ("" = nothing engaged) -- the single source both delivery paths
        (relay and mpv-native ``af``) render from.

        Skip Silence (11.7) rides the same graph, but only for something
        bounded: the filter shortens pauses, and a live broadcast's pauses
        have already gone out. That guard is why the flag is computed here
        rather than stored as part of the enhancement settings.
        """
        from quill.core.audio_enhance import build_filter_graph

        return build_filter_graph(
            self._eq_bass_db,
            self._eq_mid_db,
            self._eq_treble_db,
            compressor_enabled=self._compressor_enabled,
            smart_speed_enabled=self._skip_silence and self.is_seekable(),
            channel_mode=self._channel_mode,
            night_mode_enabled=self._night_mode_enabled,
            optilab_enabled=self._optilab_enabled,
            optilab_mode=self._optilab_mode,
            optilab_input_db=self._optilab_input_db,
            optilab_auto_adapt=self._optilab_auto_adapt,
        )

    def _exact_live_spec(self) -> ExactOptilab | None:
        """The real-engine spec for *live* playback, or None.

        None whenever the listener has not asked for it, has broadcast polish
        bypassed, has no mode chosen, or this build has no OptiLab component --
        in every one of those cases live playback stays on the ffmpeg chain,
        which is also what it does by default.
        """
        if not self._optilab_exact_live:
            return None
        if not optilab_active(self._optilab_enabled, self._optilab_mode):
            return None
        if not exact_optilab.available():
            return None
        return ExactOptilab(
            mode=self._optilab_mode,
            input_db=self._optilab_input_db,
            auto_adapt=self._optilab_auto_adapt,
        )

    def _resolve_playback_url(self, station: RadioStation) -> str:
        """The URL the engine should load: the station's own URL, or a local
        relay URL when Sound Enhancements is active on the wx engine.

        On the mpv engine the graph applies natively (``af``) and the
        station URL is loaded directly -- no relay, no second ffmpeg
        process, no re-encode.

        The one exception is exact OptiLab playback, which **must** relay on
        every engine: the real engine is a separate process, so the audio has to
        physically pass through it, and there is no filter string that can
        express "someone else's DSP" to mpv. That is the whole cost of the
        option, and it is why it is opt-in and off by default."""
        self._enhance_relay.stop()
        graph = self._current_filter_graph()
        station = (
            station
            if not self._playback_url_override
            else replace(station, stream_url=self._playback_url_override)
        )
        exact = self._exact_live_spec()
        if exact is not None:
            if self._is_mpv_active():
                # The engine below is the polish; mpv must not also apply the
                # adaptation of it, or the stream is processed twice.
                try:
                    self._mpv_engine.set_filter_graph("")  # type: ignore[union-attr]
                except Exception:  # noqa: BLE001 - clearing must never block playback
                    _log.exception("mpv filter graph clear failed")
            try:
                return self._enhance_relay.start(
                    station.stream_url,
                    bass_db=self._eq_bass_db,
                    mid_db=self._eq_mid_db,
                    treble_db=self._eq_treble_db,
                    compressor_enabled=self._compressor_enabled,
                    channel_mode=self._channel_mode,
                    night_mode_enabled=self._night_mode_enabled,
                    exact_optilab=exact,
                )
            except EnhanceError as error:
                if self._on_enhance_error is not None:
                    self._on_enhance_error(str(error))
                return station.stream_url
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
                optilab_enabled=self._optilab_enabled,
                optilab_mode=self._optilab_mode,
                optilab_input_db=self._optilab_input_db,
                optilab_auto_adapt=self._optilab_auto_adapt,
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
        radio has no position to lose; a reconnect is the whole cost).

        Exact OptiLab playback always takes the reconnect path, on both engines:
        the engine process is prepared with a mode and a sample rate at start-up
        and cannot be re-parameterised mid-stream, so "hear it as you move the
        control" is precisely the property that option trades away."""
        if self._exact_live_spec() is None and self._is_mpv_active():
            try:
                self._mpv_engine.set_filter_graph(self._current_filter_graph())  # type: ignore[union-attr]
                return
            except Exception:  # noqa: BLE001
                _log.exception("live mpv filter apply failed; reconnecting instead")
        station = self._state.station
        if station is not None and self._state.state in RESTARTABLE_STATES:
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

    def set_sound_options(
        self,
        *,
        channel_mode: str,
        night_mode_enabled: bool,
        optilab_enabled: bool = False,
        optilab_mode: str = "off",
        optilab_input_db: float = 0.0,
        optilab_auto_adapt: int = 0,
        optilab_exact_live: bool = False,
    ) -> None:
        """Change the listener-level sound options (channel mode, night mode,
        and OptiLab broadcast polish); same live-apply/reconnect behavior as
        ``set_enhancement``."""
        new = (
            channel_mode,
            night_mode_enabled,
            optilab_enabled,
            optilab_mode,
            optilab_input_db,
            optilab_auto_adapt,
            optilab_exact_live,
        )
        current = (
            self._channel_mode,
            self._night_mode_enabled,
            self._optilab_enabled,
            self._optilab_mode,
            self._optilab_input_db,
            self._optilab_auto_adapt,
            self._optilab_exact_live,
        )
        if new == current:
            return
        self._channel_mode = channel_mode
        self._night_mode_enabled = night_mode_enabled
        self._optilab_enabled = optilab_enabled
        self._optilab_mode = optilab_mode
        self._optilab_input_db = optilab_input_db
        self._optilab_auto_adapt = optilab_auto_adapt
        self._optilab_exact_live = optilab_exact_live
        self._apply_sound_change()

    def preview_enhancements(
        self,
        *,
        bass_db: float,
        mid_db: float,
        treble_db: float,
        compressor_enabled: bool,
        channel_mode: str,
        night_mode_enabled: bool,
        optilab_enabled: bool = False,
        optilab_mode: str = "off",
        optilab_input_db: float = 0.0,
        optilab_auto_adapt: int = 0,
        optilab_exact_live: bool = False,
    ) -> None:
        """Apply every Sound Enhancements setting at once and make it heard --
        the live-preview path for the dialog, so moving a slider is heard
        immediately (mpv: live ``af``; wx: one reconnect) without pressing OK.

        A single ``_apply_sound_change`` for the whole set (not one per field)
        so a drag never reconnects the wx relay twice for one change."""
        self._eq_bass_db = bass_db
        self._eq_mid_db = mid_db
        self._eq_treble_db = treble_db
        self._compressor_enabled = compressor_enabled
        self._channel_mode = channel_mode
        self._night_mode_enabled = night_mode_enabled
        self._optilab_enabled = optilab_enabled
        self._optilab_mode = optilab_mode
        self._optilab_input_db = optilab_input_db
        self._optilab_auto_adapt = optilab_auto_adapt
        self._optilab_exact_live = optilab_exact_live
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
        """Jump back within the live buffer; how far behind live we now are,
        or None when there is no buffer. See :mod:`quill.ui.radio.live_dvr`."""
        from quill.ui.radio import live_dvr

        return live_dvr.rewind(self, seconds)

    def forward(self, seconds: int = 30) -> float | None:
        """Jump forward toward the live edge, after a rewind."""
        from quill.ui.radio import live_dvr

        return live_dvr.forward(self, seconds)

    def jump_to_live(self) -> bool:
        """Return to the live edge. False when nothing is playing."""
        from quill.ui.radio import live_dvr

        return live_dvr.jump_to_live(self)

    def behind_live_seconds(self) -> float | None:
        """How far behind the live edge playback is, or None when unknown."""
        from quill.ui.radio import live_dvr

        return live_dvr.behind_live_seconds(self)

    def engine_track_title(self) -> str:
        """The engine's own idea of the current track, or "".
        See :mod:`quill.ui.radio.live_dvr`."""
        from quill.ui.radio import live_dvr

        return live_dvr.engine_track_title(self)

    def _attempt_engine_fallback(self) -> bool:
        """One cross-engine rescue per play attempt: retry the current station
        on the other backend. True when a retry was started. See
        :mod:`quill.ui.radio.engine_selection`."""
        from quill.ui.radio import engine_selection

        return engine_selection.attempt_fallback(self)

    def toggle_play_pause(self) -> None:
        # RUNNING_STATES, not PLAYING: pressing Play/Pause during a stall used
        # to pause (a stall stayed PLAYING). Comparing against PLAYING alone
        # would drop it through to the third branch and *restart* the station.
        if self._state.state in RUNNING_STATES:
            # Keep the place *before* pausing, and while the engine can still
            # be asked where it is (11.11's "write on pause"). Pause used to be
            # the one way to leave an episode part-heard that wrote nothing at
            # all, so a listener who paused in Radio and opened Cast was
            # offered the position from whenever they last pressed Stop.
            self._remember_resume_point()
            self._engine.pause()
            self._set_state(RadioPlayerState.PAUSED)
        elif self._state.state is RadioPlayerState.PAUSED:
            self._engine.play()
            self._set_state(RadioPlayerState.PLAYING)
        elif self._state.station is not None:
            self.play_station(self._state.station)

    def stop(self) -> None:
        # Keep the place first: after the engine stops, there is no position to
        # read, and Stop is the most common way to leave a chapter part-heard.
        self._remember_resume_point()
        # A YouTube resolve still in flight must not start playing after the
        # listener pressed Stop, so the token moves on and its result is dropped.
        self._play_token += 1
        self._playback_url_override = ""
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
        if station is not None and self._state.state in RESTARTABLE_STATES:
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
        # Close the Spotify WebView engine if it exists and was not the active
        # engine (tears down the hidden WebView + its localhost page host).
        if self._spotify_engine is not None and self._engine is not self._spotify_engine:
            try:
                self._spotify_engine.close()
            except Exception:  # noqa: BLE001 - never block app close
                _log.exception("Spotify engine close failed during shutdown")
            self._spotify_engine = None
        # Some engines (mpv) keep a live handle after close() for reuse; on the
        # real exit path we must hard-terminate so audio never outlives the app,
        # independent of window-destroy ordering (#1195).
        terminate = getattr(self._engine, "terminate", None)
        if callable(terminate):
            try:
                terminate()
            except Exception:  # noqa: BLE001 - never block app close
                _log.exception("radio engine terminate failed during shutdown")
        try:
            self._enhance_relay.shutdown()
        except Exception:  # noqa: BLE001 - never block app close
            _log.exception("radio enhancement relay shutdown failed")

    # -- engine callbacks -------------------------------------------------

    def _on_loaded(self, _length_ms: int) -> None:
        from quill.ui.radio import live_reconnect

        self._engine.set_volume(self._effective_volume())
        self._engine.play()
        # A load that followed a dropped connection says so, once. Silence
        # after "Reconnecting..." would leave the listener unable to tell a
        # recovered stream from a stalled retry.
        self._set_state(RadioPlayerState.PLAYING, message=live_reconnect.announce_recovery(self))
        station = self._state.station
        if station is not None and station.station_uuid and self._on_register_click:
            uuid = station.station_uuid
            threading.Thread(  # GATE-40-OK: fire-and-forget click-count etiquette ping
                target=self._on_register_click, args=(uuid,), daemon=True
            ).start()

    def _on_finished(self) -> None:
        """Playback reached an end. What that means is ``track_end``'s job."""
        from quill.ui.radio import track_end

        track_end.handle(self)

    def _schedule_later(self, delay_ms: int, work: Callable[[], None]) -> None:
        """Run *work* on the UI thread after *delay_ms*.

        The one wx call the reconnect path needs, kept here so
        ``live_reconnect`` stays wx-free and testable.
        """
        wx.CallLater(delay_ms, work)

    def _on_error(self, message: str) -> None:
        """A load failed. What happens next lives in engine_selection."""
        from quill.ui.radio import engine_selection

        engine_selection.on_load_error(self, message)

    def _handle_buffering(self, active: bool) -> None:
        """The engine's stall report, turned into a state as well as a sentence.

        The rule lives in :mod:`quill.ui.radio.stream_stall`, with the other
        three "what happens to a stream" modules; this is the seam the engine is
        handed in ``engine_selection._build_mpv``.
        """
        stream_stall.handle(self, active)

    # -- internal -----------------------------------------------------------

    def _set_state(
        self,
        state: RadioPlayerState,
        *,
        station: RadioStation | None | Ellipsis = ...,  # type: ignore[valid-type]
        message: str = "",
        cue: bool = True,
    ) -> None:
        # Only a real transition cues (#1302). The retry paths re-enter the
        # state they are already in -- the cross-engine rescue sets CONNECTING
        # a second time, a stalled stream re-announces itself -- so comparing
        # against the state being replaced is what stops one flaky stream from
        # firing the same earcon ten times in a row.
        #
        # ``cue=False`` is for the one transition that is a *return* rather than
        # an event: coming back from BUFFERING to PLAYING. A stream that stalls
        # ten times is genuinely PLAYING ten times, and cueing each one would
        # reintroduce the ten-earcons problem the comment above exists to stop.
        if cue and state is not self._state.state and state in _STATE_SOUNDS:
            post_cue(_STATE_SOUNDS[state])
        if station is not ...:
            self._state.station = station
        self._state.state = state
        self._state.message = message
        self._notify()

    def _notify(self) -> None:
        if self._on_state_changed is not None:
            self._on_state_changed(self._state)
