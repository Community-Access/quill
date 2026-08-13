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
from quill.core.optilab import (
    OPTILAB_INPUT_MAX_DB,
    OPTILAB_INPUT_MIN_DB,
    OPTILAB_MODE_LABELS,
    OPTILAB_MODES,
    _db_to_linear,
    clamp_optilab_input,
    optilab_active,
    optilab_filters,
)
from quill.core.speech.ffmpeg import INSTALL_HINT, find_ffmpeg
from quill.stability.redaction import format_args_for_log

#: Re-exported so existing callers keep importing these from here: the Sound
#: Enhancements dialog for the OptiLab surface, and quill.core.audio.dsp for
#: ``_db_to_linear``. The adaptation itself lives in :mod:`quill.core.optilab`,
#: which tracks upstream's releases; this module stays the one import site for
#: everything Sound Enhancements needs.
__all__ = [
    "OPTILAB_MODES",
    "OPTILAB_MODE_LABELS",
    "OPTILAB_INPUT_MIN_DB",
    "OPTILAB_INPUT_MAX_DB",
    "clamp_optilab_input",
    "_db_to_linear",
]

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

_RELAY_READ_CHUNK = 4096


class EnhanceError(CodedError):
    """Sound Enhancements could not start (ffmpeg missing or failed to launch)."""

    code = "QUILL-RADIO-ENHANCE-FAILED"


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
        or optilab_active(optilab_enabled, optilab_mode)
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
    pipeline_stage: str = "",
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
    if optilab_active(optilab_enabled, optilab_mode):
        filters += optilab_filters(optilab_mode, optilab_input_db, optilab_auto_adapt)
    # Audio Studio pipeline steps contributed by enabled Quillins (studio.pipeline).
    # A caller opts in by naming a stage (the Studio export path); radio callers
    # leave it "" so their graph is unchanged. The steps' handlers touch no audio
    # bytes and make no network call -- they return ffmpeg filter fragments the
    # host appends here. The registry is empty when no Quillins / in Safe Mode.
    if pipeline_stage:
        from quill.core.audio_studio import pipeline_registry

        filters += pipeline_registry.filters_for_stage(pipeline_stage)
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
