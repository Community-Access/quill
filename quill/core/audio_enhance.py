"""Sound Enhancements: optional EQ presets + a compressor for radio and
podcast playback.

Both players' engines (Radio's ``WxMediaEngine``, Podcasts' mpv-preferred
``AudioEngine``) can only open a URL -- neither has a filter graph of its
own. Rather than adding a second, heavier audio backend (e.g. BASS_FX)
purely to get an equalizer and a compressor, this reuses the ffmpeg
dependency radio recording already requires (``quill.core.speech.ffmpeg``):
ffmpeg reads the source (a live stream or a podcast episode file/URL),
applies the filter graph, and re-encodes to MP3 on its stdout; a small
loopback-only HTTP relay (:class:`EnhanceRelay`) hands those bytes to
whichever client connects, so the existing engine can just load a
``http://127.0.0.1:<port>/...`` URL instead of the source's own URL. When no
enhancement is active, playback never touches this module at all -- the
engine loads the source URL directly, exactly as before.

Deliberately not BASS/BASS_FX: BASS requires a paid license for anything but
a non-revenue app, which is a determination this module sidesteps entirely
by building on ffmpeg, a dependency QUILL already has cleared (see
``quill/core/speech/ffmpeg.py``'s licensing note -- QUILL never bundles or
redistributes it, only launches a copy already on the system).

Radio is an infinite live stream (no seek, no duration); podcast episodes
are bounded, so their controller additionally uses ``start_seconds`` (an
ffmpeg ``-ss`` restart is how "seek while enhanced" works -- there is no way
to seek within an already-running relay, only start a new one at a new
offset) and :func:`probe_source_duration_ms` (the relay's own output has no
upfront length for the engine to compute a scrub bar from).

wx-free, strict-typed.
"""

from __future__ import annotations

import functools
import http.server
import logging
import os
import subprocess
import threading
from typing import IO

from quill.core.error_codes import CodedError
from quill.core.speech.ffmpeg import INSTALL_HINT, find_ffmpeg
from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)

#: (bass gain, mid gain, treble gain) in dB, centered at 100 Hz / 1 kHz / 8 kHz.
#: Quick-select shortcuts for the three adjustable band sliders below --
#: picking one just sets the three gains to these values; the bands stay
#: freely adjustable afterward (a preset is a starting point, not a locked
#: mode).
EQ_PRESETS: dict[str, tuple[float, float, float]] = {
    "Flat": (0.0, 0.0, 0.0),
    "Bass Boost": (7.0, 0.0, 1.0),
    "Voice Clarity": (-3.0, 4.0, 2.0),
    "Podcast": (-4.0, 3.0, 0.0),
    # Compensates small laptop/phone-dock speakers that physically cannot
    # reproduce lows: lift the bass they starve, brighten slightly.
    "Small Speakers": (6.0, 0.0, 2.0),
    # Softer top end for late-night listening at low volume (pairs well
    # with Even Out Loudness, but that toggle stays the listener's call).
    "Late Night": (2.0, 0.0, -3.0),
}
_EQ_BAND_FREQUENCIES = (100, 1000, 8000)
#: Slider range for each band, in dB. wx.Slider is integer-only, so gains
#: are whole dB steps -- plenty of resolution for a 3-band EQ (real mixing
#: consoles rarely offer finer than 1 dB per notch either).
EQ_BAND_MIN_DB = -12.0
EQ_BAND_MAX_DB = 12.0


def clamp_eq_gain(value: float) -> float:
    """Clamp a single band's gain to the slider's supported range."""
    return max(EQ_BAND_MIN_DB, min(EQ_BAND_MAX_DB, value))


# threshold/ratio/attack/release/makeup tuned to even out a typical low-bitrate
# internet radio stream without audibly pumping.
_COMPRESSOR_FILTER = "acompressor=threshold=-18dB:ratio=3:attack=20:release=250:makeup=2"

# Smart Speed (podcasts only -- see build_filter_graph): trims silence longer
# than stop_duration below stop_threshold anywhere in the audio
# (stop_periods=-1), not just leading/trailing -- the gaps between sentences
# a spoken-word episode is full of. Deliberately not exposed for radio: a
# live stream has no fixed content to trim ahead of time, and "silence" in
# music is often intentional.
_SMART_SPEED_FILTER = "silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-40dB"

# Channel mode: accessibility routing for single-sided hearing or a single
# earbud, and for listening to the radio in one ear while a screen reader (or
# anything else) uses the other. "mono" blends both channels into both outputs
# (so hard-panned content never disappears). "left"/"right" blend the WHOLE
# stereo field into a single output channel and silence the other, so the
# listener hears all of the audio in just their left (or right) ear, leaving the
# other ear free. "stereo" (the default) engages no filter.
_CHANNEL_FILTERS = {
    "mono": "pan=mono|c0=0.5*c0+0.5*c1",
    "left": "pan=stereo|c0=0.5*c0+0.5*c1|c1=0*c0",
    "right": "pan=stereo|c0=0*c0|c1=0.5*c0+0.5*c1",
}
CHANNEL_MODES = ("stereo", "mono", "left", "right")

# Night mode: real-time loudness normalization (dynaudnorm) -- lifts quiet
# program material toward a consistent level, the "boost the quiet parts"
# complement to the compressor's "tame the loud parts". frame length /
# gaussian window tuned for music-safe smoothing without audible pumping.
_NIGHT_MODE_FILTER = "dynaudnorm=f=250:g=15:p=0.9"

# -- OptiLab broadcast-polish modes --------------------------------------------
#
# Three one-touch "broadcast polish" chains adapted from OptiLab Core by
# dgl1984 (https://github.com/dgl1984/optilab, Apache-2.0), with thanks and
# attribution. OptiLab itself is a GUI-only plugin (JSFX/CLAP/Winamp DSP) with
# no library to call and a Windows-64-only binary, so rather than embedding it
# we reproduce the *shape* of its three modes -- Podcast Leveler, Stream Polish,
# Smooth Limiter -- as ffmpeg filter chains that ride the same graph everywhere
# Sound Enhancements already reaches (mpv-native live, the relay, recordings)
# and so work cross-platform and preview live. This is a faithful adaptation,
# not a bit-for-bit port of OptiLab's custom multiband/AGC/limiter DSP.
#
# Each mode maps OptiLab's three controls onto ffmpeg: Mode picks the chain,
# Input is a front-end gain (``volume``, 0 dB by default), and Auto-Adapt
# (0-100%) scales the leveling/density toward a more assertive setting, the way
# OptiLab interpolates its internal stages.
OPTILAB_MODES = ("off", "podcast", "stream", "limiter")
OPTILAB_MODE_LABELS = {
    "off": "Off",
    "podcast": "Podcast Leveler (speech)",
    "stream": "Stream Polish (music)",
    "limiter": "Smooth Limiter (mastering)",
}
#: Input trim range (dB); 0 (no change) is the default, per product choice.
OPTILAB_INPUT_MIN_DB = -12.0
OPTILAB_INPUT_MAX_DB = 18.0


def _db_to_linear(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def clamp_optilab_input(value: float) -> float:
    """Clamp OptiLab's Input trim to its supported range."""
    return max(OPTILAB_INPUT_MIN_DB, min(OPTILAB_INPUT_MAX_DB, value))


def _optilab_filters(mode: str, input_db: float, auto_adapt: int) -> list[str]:
    """The ffmpeg filter chain for an OptiLab mode (empty for ``"off"``).

    Adapted from OptiLab Core (dgl1984, Apache-2.0): a leveling -> density ->
    tone -> lookahead-limiter chain per mode, with Auto-Adapt (0-100%) leaning
    the leveling/density more assertive. ``input_db`` is a front-end trim
    (0 = unchanged).
    """
    if mode not in ("podcast", "stream", "limiter"):
        return []
    depth = max(0.0, min(1.0, auto_adapt / 100.0))
    filters: list[str] = []
    trim = clamp_optilab_input(input_db)
    if trim:
        filters.append(f"volume={trim:.2f}dB")
    if mode == "podcast":
        # Speech: subsonic HPF, speech leveling (AGC), gentle density, a small
        # 65 Hz bass tame, then a lookahead limiter near -1.5 dBFS.
        expansion = 6.25 + 6.25 * depth
        ratio = 3.0 + 1.0 * depth
        filters.append("highpass=f=30")
        filters.append(f"speechnorm=e={expansion:.2f}:r=0.0005:l=1")
        filters.append(
            f"acompressor=threshold=-17dB:ratio={ratio:.2f}:attack=20:release=250:makeup=2"
        )
        filters.append("equalizer=f=65:t=q:w=1.4:g=-2")
        filters.append(f"alimiter=limit={_db_to_linear(-1.5):.4f}:attack=5:release=50")
    elif mode == "stream":
        # Music: broadband leveling, denser compression, a touch of presence,
        # then a lookahead limiter near -0.8 dBFS.
        peak = 0.90 + 0.05 * depth
        ratio = 2.5 + 0.7 * depth
        filters.append(f"dynaudnorm=f=200:g=15:p={peak:.2f}")
        filters.append(
            f"acompressor=threshold=-15dB:ratio={ratio:.2f}:attack=10:release=200:makeup=1.5"
        )
        filters.append("equalizer=f=12000:t=q:w=1:g=1.5")
        filters.append(f"alimiter=limit={_db_to_linear(-0.8):.4f}:attack=5:release=50")
    else:  # limiter
        # Clean mastering-style peak control: a light compressor then a
        # transparent lookahead limiter near -2.0 dBFS.
        ratio = 2.0 + 1.0 * depth
        filters.append(
            f"acompressor=threshold=-12dB:ratio={ratio:.2f}:attack=5:release=150:makeup=1"
        )
        filters.append(f"alimiter=limit={_db_to_linear(-2.0):.4f}:attack=5:release=60")
    return filters


_RELAY_READ_CHUNK = 4096


class EnhanceError(CodedError):
    """Sound Enhancements could not start (ffmpeg missing or failed to launch)."""

    code = "QUILL-RADIO-ENHANCE-FAILED"


def _optilab_active(optilab_enabled: bool, optilab_mode: str) -> bool:
    """True when the OptiLab chain should apply (enabled and a real mode)."""
    return bool(optilab_enabled) and optilab_mode in ("podcast", "stream", "limiter")


def is_enhancement_active(
    bass_db: float,
    mid_db: float,
    treble_db: float,
    *,
    compressor_enabled: bool,
    smart_speed_enabled: bool = False,
    channel_mode: str = "stereo",
    night_mode_enabled: bool = False,
    optilab_enabled: bool = False,
    optilab_mode: str = "off",
) -> bool:
    """True when these settings would change the audio at all."""
    return (
        bool(bass_db or mid_db or treble_db)
        or compressor_enabled
        or smart_speed_enabled
        or channel_mode in _CHANNEL_FILTERS
        or night_mode_enabled
        or _optilab_active(optilab_enabled, optilab_mode)
    )


def build_filter_graph(
    bass_db: float,
    mid_db: float,
    treble_db: float,
    *,
    compressor_enabled: bool,
    smart_speed_enabled: bool = False,
    channel_mode: str = "stereo",
    night_mode_enabled: bool = False,
    optilab_enabled: bool = False,
    optilab_mode: str = "off",
    optilab_input_db: float = 0.0,
    optilab_auto_adapt: int = 0,
) -> str:
    """Build the ffmpeg ``-af`` filter graph for the three-band equalizer
    (Bass/Mid/Treble, in dB, each clamped to ``EQ_BAND_MIN_DB``..
    ``EQ_BAND_MAX_DB``) + the compressor + Smart Speed (silence trimming,
    podcasts only -- radio callers never pass ``smart_speed_enabled=True``)
    + mono downmix + night mode (loudness normalization) + the OptiLab
    broadcast-polish chain.

    Filter order matters and is deliberate: mono first (everything after
    hears the blended signal), then EQ, then the compressor, then night
    mode, and the OptiLab chain *last* -- its own lookahead limiter guards
    the final output. The OptiLab chain only applies when ``optilab_enabled``
    is true and ``optilab_mode`` is a real mode, so the checkbox is a true
    bypass that leaves the chosen mode remembered.

    Pure and unit-tested. Returns ``""`` when nothing is engaged (a caller
    should treat that as "play the stream directly, no relay needed").
    The same graph drives all three delivery paths -- the ffmpeg relay
    (wx.media playback), mpv's native ``af`` (no relay needed), and
    recordings with "Apply Sound Enhancements" -- so every option behaves
    identically everywhere.
    """
    gains = (clamp_eq_gain(bass_db), clamp_eq_gain(mid_db), clamp_eq_gain(treble_db))
    filters = [_CHANNEL_FILTERS[channel_mode]] if channel_mode in _CHANNEL_FILTERS else []
    filters += [
        f"equalizer=f={freq}:t=q:w=1:g={gain}"
        for freq, gain in zip(_EQ_BAND_FREQUENCIES, gains, strict=True)
        if gain
    ]
    if compressor_enabled:
        filters.append(_COMPRESSOR_FILTER)
    if smart_speed_enabled:
        filters.append(_SMART_SPEED_FILTER)
    if night_mode_enabled:
        filters.append(_NIGHT_MODE_FILTER)
    if _optilab_active(optilab_enabled, optilab_mode):
        filters += _optilab_filters(optilab_mode, optilab_input_db, optilab_auto_adapt)
    return ",".join(filters)


def build_relay_command(
    ffmpeg: str,
    stream_url: str,
    *,
    bass_db: float,
    mid_db: float,
    treble_db: float,
    compressor_enabled: bool,
    smart_speed_enabled: bool = False,
    channel_mode: str = "stereo",
    night_mode_enabled: bool = False,
    optilab_enabled: bool = False,
    optilab_mode: str = "off",
    optilab_input_db: float = 0.0,
    optilab_auto_adapt: int = 0,
    start_seconds: float = 0.0,
) -> list[str]:
    """Build the ffmpeg argv that filters *stream_url* and writes MP3 to stdout.

    Pure and unit-tested. Mirrors ``recording.py``'s ``build_record_command``:
    the same HTTP reconnect flags, so a network hiccup is ridden out here
    exactly as it is during a recording. A positive ``start_seconds`` adds an
    input ``-ss`` (fast, before ``-i``) -- how "seek while enhanced" works
    for a bounded source (a podcast episode): there is no way to seek within
    an already-running relay, only start a new one at a new offset.
    """
    args = [ffmpeg, "-hide_banner", "-loglevel", "error"]
    if stream_url.lower().startswith(("http://", "https://")):
        args.extend(["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "10"])
    if start_seconds > 0:
        args.extend(["-ss", f"{start_seconds:.3f}"])
    args.extend(["-i", stream_url, "-vn"])
    filter_graph = build_filter_graph(
        bass_db,
        mid_db,
        treble_db,
        compressor_enabled=compressor_enabled,
        smart_speed_enabled=smart_speed_enabled,
        channel_mode=channel_mode,
        night_mode_enabled=night_mode_enabled,
        optilab_enabled=optilab_enabled,
        optilab_mode=optilab_mode,
        optilab_input_db=optilab_input_db,
        optilab_auto_adapt=optilab_auto_adapt,
    )
    if filter_graph:
        args.extend(["-af", filter_graph])
    args.extend(["-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", "pipe:1"])
    return args


def probe_source_duration_ms(source: str, *, timeout_seconds: float = 15.0) -> int:
    """Best-effort total duration of *source* (a local path or a URL) via
    ffprobe; ``0`` if unknown. Used to report a real duration/scrub-bar
    length for a bounded source (a podcast episode) while Sound
    Enhancements relays it through a live filter -- the relay's own MP3
    output has no upfront length for the engine to compute a duration from.
    Not used by radio, which has no duration to report either way.
    """
    from quill.core.speech.ffmpeg import find_ffprobe
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffprobe = find_ffprobe()
    if ffprobe is None:
        return 0
    args = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        source,
    ]
    try:
        completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
    except OSError:
        return 0
    try:
        return int(round(float((completed.stdout or "").strip()) * 1000))
    except (TypeError, ValueError):
        return 0


class _RelayHTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class _RelayHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Streams ``source``'s bytes to the one client that connects.

    ``source`` is ffmpeg's stdout pipe -- a single, one-shot byte stream, so
    only one connection is served at a time (a second connection attempt
    gets a 409, never interleaved/garbled audio from two readers on the same
    pipe).
    """

    def __init__(
        self, *args: object, source: IO[bytes] | None, read_lock: threading.Lock, **kwargs: object
    ) -> None:
        self._source = source
        self._read_lock = read_lock
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        pass  # BaseHTTPRequestHandler defaults to writing every request to stderr

    def do_GET(self) -> None:
        if self._source is None or not self._read_lock.acquire(blocking=False):
            self.send_error(409, "Sound Enhancements relay is already in use")
            return
        try:
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            while True:
                chunk = self._source.read(_RELAY_READ_CHUNK)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self._read_lock.release()


class EnhanceRelay:
    """Owns at most one active ffmpeg filter + local HTTP relay.

    The player engine only knows how to open a URL, so the filtered audio
    has to arrive as one; this is that URL's source. Loopback-only
    (``127.0.0.1``, OS-assigned port) -- never reachable off the machine.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._server: _RelayHTTPServer | None = None
        self._server_thread: threading.Thread | None = None

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._process is not None

    def start(
        self,
        stream_url: str,
        *,
        bass_db: float = 0.0,
        mid_db: float = 0.0,
        treble_db: float = 0.0,
        compressor_enabled: bool,
        smart_speed_enabled: bool = False,
        channel_mode: str = "stereo",
        night_mode_enabled: bool = False,
        optilab_enabled: bool = False,
        optilab_mode: str = "off",
        optilab_input_db: float = 0.0,
        optilab_auto_adapt: int = 0,
        start_seconds: float = 0.0,
    ) -> str:
        """Start relaying *stream_url* through the filter graph; returns the
        local URL to hand to the player engine instead of *stream_url*. A
        positive ``start_seconds`` begins the relay partway through a
        bounded source (see :func:`build_relay_command`).

        Raises :class:`EnhanceError` if ffmpeg is unavailable or the relay
        could not be started. Stops any previous relay first.
        """
        self.stop()
        ffmpeg = find_ffmpeg()
        if ffmpeg is None:
            raise EnhanceError(f"ffmpeg is not installed. {INSTALL_HINT}")
        args = build_relay_command(
            ffmpeg,
            stream_url,
            bass_db=bass_db,
            mid_db=mid_db,
            treble_db=treble_db,
            compressor_enabled=compressor_enabled,
            smart_speed_enabled=smart_speed_enabled,
            channel_mode=channel_mode,
            night_mode_enabled=night_mode_enabled,
            optilab_enabled=optilab_enabled,
            optilab_mode=optilab_mode,
            optilab_input_db=optilab_input_db,
            optilab_auto_adapt=optilab_auto_adapt,
            start_seconds=start_seconds,
        )
        extra_kwargs: dict = {}
        if os.name == "nt":
            extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        logger.info("Starting Sound Enhancements relay: %s", format_args_for_log(args))
        try:
            process = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                **extra_kwargs,
            )
        except OSError as exc:
            raise EnhanceError(f"Could not start ffmpeg: {exc}") from exc
        read_lock = threading.Lock()
        handler = functools.partial(_RelayHTTPHandler, source=process.stdout, read_lock=read_lock)
        try:
            server = _RelayHTTPServer(("127.0.0.1", 0), handler)
        except OSError as exc:
            process.kill()
            raise EnhanceError(f"Could not start the Sound Enhancements relay: {exc}") from exc
        thread = threading.Thread(
            target=server.serve_forever, daemon=True, name="quill-radio-enhance-relay"
        )
        thread.start()
        with self._lock:
            self._process = process
            self._server = server
            self._server_thread = thread
        port = server.server_address[1]
        return f"http://127.0.0.1:{port}/enhanced.mp3"

    def stop(self) -> None:
        """Stop any active relay; a no-op if idle."""
        with self._lock:
            process = self._process
            server = self._server
            self._process = None
            self._server = None
            self._server_thread = None
        if server is not None:
            try:
                server.shutdown()
                server.server_close()
            except Exception:  # noqa: BLE001 - stopping must never raise
                logger.exception("Sound Enhancements relay server shutdown failed")
        if process is not None:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()

    def shutdown(self) -> None:
        """Called once, from the frame's close path."""
        self.stop()
