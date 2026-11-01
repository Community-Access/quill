"""Going live: the stream mix, the server connection and the saved copy (roadmap S1 to S15).

The **stream mix** is built here, live: each source the presenter turned on
for the stream is captured with the recording sources' own classes, and a
mixing thread sums 20-millisecond blocks at each source's stream level into
48 kHz stereo PCM (``live_stream_mix``). Only those sources can reach
listeners; Studio's own cues come from Studio's process, which is never a
source. *Mute everything public* sends silence without disconnecting.

The PCM goes to FFmpeg, which encodes it and sends it to Icecast itself, or
hands the encoded bytes to Studio's SHOUTcast source client (FFmpeg cannot
do SHOUTcast's login). A saved copy, when chosen, is a second FFmpeg fed the
same mix through its **own** queue and writer thread, so it keeps recording
through a dropped connection *and* through a slow one: only the stream's
queue can overflow (BCAST-026). "On air" is said only once the server has
taken two seconds of encoded audio, and a refused password stops the retries
at any attempt (BCAST-027, ``live_stream_air``). A dropped connection is
retried with growing pauses and marked.
"""

from __future__ import annotations

import logging
import socket
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

from quill.core.demo_recording import SoundSource
from quill.core.streaming import (
    StreamingError,
    StreamSettings,
    metadata_request,
    shoutcast_handshake,
    shoutcast_source_port,
    stream_command,
)
from quill.platform.windows.live_stream_air import (
    ACCEPTED_SECONDS,
    BACK_ON_AIR,
    ON_AIR,
    REFUSED,
    SILENT_CONNECTION_SECONDS,
    STALLED_SECONDS,
    EncoderProgress,
    StreamRefused,
    is_auth_refusal,
)
from quill.platform.windows.live_stream_mix import BLOCK, RATE, BlockWriter, StreamMixer

logger = logging.getLogger(__name__)

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_BLOCK_SECONDS = BLOCK / RATE
Event = Callable[[str, bool], None]

__all__ = ["LiveStream", "StreamMixer", "test_connection"]


class _MixerInput:
    """Stands where a recording source's WAV stream would, feeding the mixer."""

    def __init__(self, mixer: StreamMixer, source_id: str, channels: int) -> None:
        self.mixer = mixer
        self.source_id = source_id
        self.channels = channels
        self.muted = False
        self.first_time: float | None = None

    def write(self, payload: bytes, captured_at: float) -> None:
        if self.first_time is None:
            self.first_time = captured_at
        if not self.muted:
            self.mixer.push(self.source_id, payload, self.channels)

    def finish(self, _end_time: float | None = None) -> None:
        return None


class LiveStream:
    """One live show: sources, mixer, connection, saved copy, now-playing title."""

    #: The first pause before a reconnect; it doubles up to 30 seconds.
    _first_wait = 2.0
    #: How often the connection is looked at.
    _tick = 1.0
    #: A half-speed link drops nothing for this long, while listeners fall behind.
    _stream_queue_seconds = 30.0
    #: Listeners this far behind are told about, once.
    _lag_after_seconds = 5.0
    #: The saved copy's queue: only a stalled disk could fill it.
    _archive_queue_seconds = 120.0

    def __init__(
        self,
        settings: StreamSettings,
        password: str,
        *,
        ffmpeg: str,
        sources: list[SoundSource],
        on_event: Event,
        archive_path: str = "",
        studio_pid: int = 0,
    ) -> None:
        self.settings = settings
        self._password = password
        self.ffmpeg = ffmpeg
        self.on_event = on_event
        self.archive_path = archive_path
        self.studio_pid = studio_pid
        self.sources = sources
        self.started = 0.0
        self.reconnects = 0
        self.connected = False
        #: True once the server has taken ACCEPTED_SECONDS on this connection.
        self.on_air = False
        #: Why the stream stopped for good, while the show (and saved copy) goes on.
        self.ended = ""
        self._ever_on_air = False
        self._connected_at = 0.0
        self._silence_said = False
        #: Accepted seconds the current on-air count starts from (after a stall).
        self._air_from = 0.0
        self._last_accepted = 0.0
        self._moved_at = 0.0
        self._air_lock = threading.Lock()
        self._progress = EncoderProgress()
        self._reader: threading.Thread | None = None
        self._captures: list[Any] = []
        self._encoder: subprocess.Popen[bytes] | None = None
        self._archive: subprocess.Popen[bytes] | None = None
        self._socket: socket.socket | None = None
        self._stream_out: BlockWriter | None = None
        self._archive_out: BlockWriter | None = None
        self._stop = threading.Event()
        levels = {source.source_id: source.level_db for source in sources}
        # The microphone clocks the mix when it is in the stream (live_stream_mix).
        reference = next((s.source_id for s in sources if s.kind == "microphone"), "")
        self.mixer = StreamMixer(levels, [], reference=reference)

    # -- life -----------------------------------------------------------------------

    def start(self) -> None:
        from quill.platform.windows.demo_audio import make_source

        problems = []
        for source in self.sources:
            capture = make_source(source, self._source_event, studio_pid=self.studio_pid)
            error = capture.open()
            if error:
                problems.append(f"{source.label}: {error}")
                continue
            channels = getattr(capture, "channels", 2)
            capture.stream = _MixerInput(self.mixer, source.source_id, channels)
            self._captures.append(capture)
        if problems and not self._captures:
            raise StreamingError("No sound could be opened for the stream. " + "; ".join(problems))
        for problem in problems:
            self.on_event(f"Left out of the stream: {problem}", True)
        if self.archive_path:
            self._archive = self._popen(self._archive_command(), stdout=False)
            self._archive_out = BlockWriter(
                "stream-archive-writer",
                self._to_archive,
                capacity=int(self._archive_queue_seconds / _BLOCK_SECONDS),
                on_overflow=self._archive_overflow,
            )
        self._connect()
        self._stream_out = BlockWriter(
            "stream-encoder-writer",
            self._to_encoder,
            capacity=int(self._stream_queue_seconds / _BLOCK_SECONDS),
            on_overflow=self._stream_overflow,
            lag_after=self._lag_after_seconds,
            on_lag=self._stream_lag,
        )
        self.mixer.outputs.append(self._stream_out.put)
        if self._archive_out is not None:
            self.mixer.outputs.append(self._archive_out.put)
        self.started = time.monotonic()
        self.mixer.start()
        threading.Thread(target=self._watch, daemon=True, name="stream-watch").start()

    def _source_event(self, sentence: str, failure: bool) -> None:
        self.on_event(sentence, failure)

    def _popen(self, command: list[str], *, stdout: bool) -> subprocess.Popen[bytes]:
        return subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if stdout else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=_NO_WINDOW,
        )

    def _archive_command(self) -> list[str]:
        codec = "flac" if self.archive_path.endswith(".flac") else "pcm_s16le"
        if self.archive_path.endswith((".mp3", ".m4a")):
            codec = "libmp3lame" if self.archive_path.endswith(".mp3") else "aac"
        return [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-i",
            "pipe:0",
            "-c:a",
            codec,
            self.archive_path,
        ]

    def _connect(self) -> None:
        command = stream_command(self.ffmpeg, self.settings, self._password)
        # Progress as key=value lines on stderr: how much audio has gone out.
        command[1:1] = ["-nostats", "-progress", "pipe:2"]
        shoutcast = self.settings.kind == "shoutcast"
        if shoutcast:
            self._socket = self._shoutcast_login()
        progress = EncoderProgress()
        with self._air_lock:
            self._progress = progress
            self.on_air = False
            self._air_from = 0.0
        encoder = self._popen(command, stdout=shoutcast)
        self._encoder = encoder
        self._reader = threading.Thread(
            target=self._read_progress,
            args=(encoder, progress),
            daemon=True,
            name="stream-progress",
        )
        self._reader.start()
        # Connected before the pump starts, so a pump that ends at once is seen.
        self.connected = True
        self._connected_at = time.monotonic()
        self._silence_said = False
        if shoutcast:
            threading.Thread(
                target=self._pump,
                args=(encoder, self._socket, progress),
                daemon=True,
                name="shoutcast-pump",
            ).start()

    def _shoutcast_login(self) -> socket.socket:
        login, headers = shoutcast_handshake(self.settings, self._password)
        address = (self.settings.host, shoutcast_source_port(self.settings))
        try:
            sock = socket.create_connection(address, timeout=10)
            if self.settings.secure:
                from quill.core.net import verified_ssl_context

                sock = verified_ssl_context().wrap_socket(sock, server_hostname=self.settings.host)
            sock.sendall(login)
            reply = sock.recv(256).decode("utf-8", "replace")
            if not reply.startswith("OK"):
                sock.close()
                if "invalid" in reply.lower():
                    raise StreamRefused("The SHOUTcast server refused the password.")
                raise StreamingError(f"The SHOUTcast server answered: {reply.strip() or 'nothing'}")
            sock.sendall(headers)
            sock.settimeout(None)
            return sock
        except OSError as error:
            raise StreamingError(f"The SHOUTcast server could not be reached: {error}") from error

    def _read_progress(self, encoder: Any, progress: EncoderProgress) -> None:
        stream = encoder.stderr
        if stream is None:
            return
        try:
            for raw in iter(stream.readline, b""):
                progress.feed(raw.decode("utf-8", "replace"))
                if raw.startswith(b"progress="):
                    self._check_on_air(progress)
        except (OSError, ValueError):
            pass

    def _check_on_air(self, progress: EncoderProgress) -> None:
        shoutcast = self.settings.kind == "shoutcast"
        with self._air_lock:
            if progress is not self._progress or self.on_air or self._stop.is_set():
                return
            accepted = progress.accepted_seconds(counted_bytes=shoutcast)
            if accepted - self._air_from < ACCEPTED_SECONDS:
                return
            self.on_air = True
            self._moved_at, self._last_accepted = time.monotonic(), accepted
            sentence = BACK_ON_AIR if self._ever_on_air else ON_AIR
            self._ever_on_air = True
            self._silence_said = True  # this connection has carried sound
        self.on_event(sentence, False)

    def _pump(self, encoder: Any, sock: socket.socket | None, progress: EncoderProgress) -> None:
        if encoder is None or encoder.stdout is None or sock is None:
            return
        try:
            while not self._stop.is_set():
                chunk = encoder.stdout.read(4096)
                if not chunk:
                    break
                sock.sendall(chunk)
                progress.sent_bytes += len(chunk)
                self._check_on_air(progress)
        except OSError:
            pass
        if encoder is self._encoder:
            self.connected = False

    def _to_encoder(self, block: bytes) -> None:
        encoder = self._encoder
        if encoder is not None and encoder.stdin is not None and encoder.poll() is None:
            encoder.stdin.write(block)
            encoder.stdin.flush()

    def _to_archive(self, block: bytes) -> None:
        archive = self._archive
        if archive is not None and archive.stdin is not None and archive.poll() is None:
            archive.stdin.write(block)
            archive.stdin.flush()

    # -- said once ------------------------------------------------------------------

    def _copy_note(self, sentence: str) -> str:
        return f"{sentence} The saved copy continues." if self.archive_path else sentence

    def _stream_overflow(self) -> None:
        self.on_event(
            self._copy_note(
                "The connection is too slow for this quality, so listeners are losing sound."
            ),
            True,
        )

    def _stream_lag(self, backlog: float) -> None:
        self.on_event(
            f"The connection is slow: listeners are now {int(backlog)} seconds behind.", True
        )

    def _archive_overflow(self) -> None:
        self.on_event("The saved copy cannot keep up with the disk and has lost some sound.", True)

    # -- staying connected ----------------------------------------------------------

    def _watch(self) -> None:
        wait = self._first_wait
        while not self._stop.wait(self._tick):
            encoder = self._encoder
            alive = (
                encoder is not None
                and encoder.poll() is None
                and (self.settings.kind != "shoutcast" or self.connected)
            )
            if alive:
                if self.on_air:
                    wait = self._first_wait
                    self._check_still_moving()
                elif (
                    not self._silence_said
                    and time.monotonic() - self._connected_at >= SILENT_CONNECTION_SECONDS
                ):
                    self._silence_said = True
                    self.on_event("Connected, but the server has taken no sound yet.", True)
                continue
            refused = self._refused(encoder)
            with self._air_lock:
                self.on_air = False
            self.connected = False
            if refused:
                self._give_up(REFUSED)
                return
            if self.reconnects >= self.settings.reconnect_tries:
                self._give_up("The stream could not reconnect.")
                return
            self.on_event(f"The stream dropped; trying again in {int(wait)} seconds.", True)
            self._close_connection()
            if self._stop.wait(wait):
                return
            wait = min(30.0, wait * 2)
            self.reconnects += 1
            try:
                self._connect()
            except StreamRefused as error:
                self._give_up(str(error))
                return
            except StreamingError as error:
                self.on_event(str(error), True)

    def _check_still_moving(self) -> None:
        """On air means audio is moving: a server that stops taking it is off air.

        The buffers between Studio and the server hold several seconds, so a
        server that answers and then reads nothing looks on air until they fill;
        after that the encoder's output stops advancing, and that is said once.
        Two more seconds taken puts the show back on air.
        """
        shoutcast = self.settings.kind == "shoutcast"
        now = time.monotonic()
        with self._air_lock:
            accepted = self._progress.accepted_seconds(counted_bytes=shoutcast)
            if accepted > self._last_accepted:
                self._moved_at, self._last_accepted = now, accepted
                return
            if now - self._moved_at < STALLED_SECONDS:
                return
            self.on_air = False
            self._air_from = accepted
        self.on_event("The server has stopped taking sound.", True)

    def _refused(self, encoder: Any) -> bool:
        """Whether the encoder that just ended said the server refused the login."""
        if encoder is None:
            return False
        reader = self._reader
        if reader is not None:
            reader.join(1.0)  # its last words arrive just after it exits
        return is_auth_refusal(self._progress.tail)

    def _give_up(self, reason: str) -> None:
        self.ended = reason
        self._close_connection()
        self.on_event(self._copy_note(f"{reason} The stream has stopped."), True)

    def _close_connection(self, *, graceful: bool = False) -> None:
        encoder, self._encoder = self._encoder, None
        if encoder is not None:
            if graceful and encoder.poll() is None:
                try:
                    if encoder.stdin is not None:
                        encoder.stdin.close()
                    encoder.wait(5)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    encoder.kill()
            else:
                # The connection is gone: a writer may be blocked on this pipe,
                # and ending the process is what frees it.
                try:
                    encoder.kill()
                    encoder.wait(5)
                except (OSError, subprocess.TimeoutExpired):
                    pass
                try:
                    if encoder.stdin is not None:
                        encoder.stdin.close()
                except (OSError, ValueError):
                    pass
        sock, self._socket = self._socket, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        if self._stream_out is not None:
            self._stream_out.clear()  # a new connection starts live, not late

    def set_public_muted(self, muted: bool) -> None:
        self.mixer.public_muted = muted

    def update_title(self, title: str) -> str:
        """Set the now-playing title; ``""`` on success, else why not."""
        from urllib.error import URLError
        from urllib.request import Request, urlopen

        url, headers = metadata_request(self.settings, self._password, title)
        try:
            from quill.core.net import context_for

            with urlopen(Request(url, headers=headers), timeout=10, context=context_for(url)):
                return ""
        except (URLError, OSError) as error:
            return f"The title could not be updated: {error}"

    def status_line(self) -> str:
        from quill.core.demo_recording import format_timestamp

        if self.ended:
            state = "Stream stopped"
        elif self.on_air:
            state = "On air"
        elif self.connected and self._air_from:
            state = "Off air, the server is not taking sound"
        else:
            state = "Reconnecting" if self._ever_on_air else "Connecting"
        if self.mixer.public_muted:
            state += ", public sound muted"
        elapsed = time.monotonic() - self.started if self.started else 0.0
        parts = [f"{state}, {format_timestamp(elapsed)[:-2]}"]
        parts.append(f"{len(self._captures)} sound source{'s' if len(self._captures) != 1 else ''}")
        if self.reconnects:
            parts.append(f"{self.reconnects} reconnect{'s' if self.reconnects != 1 else ''}")
        gaps, trims = self.mixer.gaps, self.mixer.trims
        if gaps:
            parts.append(f"{gaps} short gap{'s' if gaps != 1 else ''} in a source")
        if trims:
            parts.append(f"delay trimmed {trims} time{'s' if trims != 1 else ''}")
        for writer, what in ((self._stream_out, "the stream"), (self._archive_out, "the copy")):
            if writer is not None and writer.dropped:
                parts.append(f"{writer.dropped * _BLOCK_SECONDS:.1f} seconds lost from {what}")
        if self.archive_path:
            parts.append("saving a copy")
        return "; ".join(parts) + "."

    def stop(self) -> None:
        self._stop.set()
        self.mixer.stop()
        for capture in self._captures:
            capture.close()
        stuck = False
        if self._stream_out is not None:
            stuck = not self._stream_out.close(drain=False, timeout=2)
        self._close_connection(graceful=not stuck)
        if self._archive_out is not None:
            self._archive_out.close(drain=True, timeout=10)
        archive, self._archive = self._archive, None
        if archive is not None:
            try:
                if archive.stdin is not None:
                    archive.stdin.close()
                archive.wait(10)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                archive.kill()
        self.connected = False
        with self._air_lock:
            self.on_air = False


def test_connection(settings: StreamSettings, password: str, ffmpeg: str) -> str:
    """A private two-second test: ``""`` when the server accepted it, else why not."""
    if settings.kind == "shoutcast":
        stream = LiveStream(
            settings, password, ffmpeg=ffmpeg, sources=[], on_event=lambda *_a: None
        )
        try:
            stream._shoutcast_login().close()
        except StreamingError as error:
            return str(error)
        return ""
    from quill.core.streaming import encode_args, icecast_output

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "lavfi",
        "-t",
        "2",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        *encode_args(settings),
        *icecast_output(settings, password),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30, creationflags=_NO_WINDOW
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"The test could not run: {error}"
    if result.returncode == 0:
        return ""
    lines = (result.stderr or "").strip().splitlines()
    detail = lines[-1] if lines else f"exit code {result.returncode}"
    if is_auth_refusal([detail]):
        return REFUSED
    return f"The server did not accept the test: {detail}"
