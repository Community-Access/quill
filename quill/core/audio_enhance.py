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
#: Named presets rather than raw sliders -- kept small and screen-reader
#: friendly (one combo box, not three unlabeled dB sliders per band).
EQ_PRESETS: dict[str, tuple[float, float, float]] = {
    "Flat": (0.0, 0.0, 0.0),
    "Bass Boost": (7.0, 0.0, 1.0),
    "Voice Clarity": (-3.0, 4.0, 2.0),
    "Podcast": (-4.0, 3.0, 0.0),
}
DEFAULT_EQ_PRESET = "Flat"
_EQ_BAND_FREQUENCIES = (100, 1000, 8000)

# threshold/ratio/attack/release/makeup tuned to even out a typical low-bitrate
# internet radio stream without audibly pumping.
_COMPRESSOR_FILTER = "acompressor=threshold=-18dB:ratio=3:attack=20:release=250:makeup=2"

_RELAY_READ_CHUNK = 4096


class EnhanceError(CodedError):
    """Sound Enhancements could not start (ffmpeg missing or failed to launch)."""

    code = "QUILL-RADIO-ENHANCE-FAILED"


def is_enhancement_active(eq_preset: str, *, compressor_enabled: bool) -> bool:
    """True when *eq_preset*/*compressor_enabled* would change the audio at all."""
    return EQ_PRESETS.get(eq_preset, EQ_PRESETS[DEFAULT_EQ_PRESET]) != (0.0, 0.0, 0.0) or (
        compressor_enabled
    )


def build_filter_graph(eq_preset: str, *, compressor_enabled: bool) -> str:
    """Build the ffmpeg ``-af`` filter graph for *eq_preset* + the compressor.

    Pure and unit-tested. Returns ``""`` when nothing is engaged (a caller
    should treat that as "play the stream directly, no relay needed").
    """
    gains = EQ_PRESETS.get(eq_preset, EQ_PRESETS[DEFAULT_EQ_PRESET])
    filters = [
        f"equalizer=f={freq}:t=q:w=1:g={gain}"
        for freq, gain in zip(_EQ_BAND_FREQUENCIES, gains, strict=True)
        if gain
    ]
    if compressor_enabled:
        filters.append(_COMPRESSOR_FILTER)
    return ",".join(filters)


def build_relay_command(
    ffmpeg: str,
    stream_url: str,
    *,
    eq_preset: str,
    compressor_enabled: bool,
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
    filter_graph = build_filter_graph(eq_preset, compressor_enabled=compressor_enabled)
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
        eq_preset: str,
        compressor_enabled: bool,
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
            eq_preset=eq_preset,
            compressor_enabled=compressor_enabled,
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
