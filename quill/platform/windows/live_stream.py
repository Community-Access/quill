"""Going live: the stream mix, the server connection and the saved copy (roadmap S1 to S15).

The **stream mix** is built here, live: each source the presenter turned on
for the stream is captured with the recording sources' own classes, and a
mixing thread sums 20-millisecond blocks at each source's stream level into
48 kHz stereo PCM. Only those sources can reach listeners; Studio's own cues
come from Studio's process, which is never a source. *Mute everything
public* sends silence without disconnecting.

The PCM goes to FFmpeg, which encodes it and sends it to Icecast itself, or
hands the encoded bytes to Studio's SHOUTcast source client (FFmpeg cannot
do SHOUTcast's login). A saved copy, when chosen, is a second FFmpeg fed the
same mix, so it keeps recording through a reconnect. A dropped connection is
retried with growing pauses, said once, and marked.
"""

from __future__ import annotations

import logging
import socket
import ssl
import subprocess
import threading
import time
from collections import deque
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

logger = logging.getLogger(__name__)

_RATE = 48_000
_BLOCK = 960  # 20 ms
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
Event = Callable[[str, bool], None]


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


class StreamMixer:
    """Sum the stream's sources, at their levels, into one stereo PCM stream."""

    def __init__(self, levels: dict[str, float], outputs: list[Callable[[bytes], None]]) -> None:
        import numpy as np

        self._np = np
        self.gains = {key: 10 ** (db / 20) for key, db in levels.items()}
        self.outputs = outputs
        self.queues: dict[str, deque[Any]] = {key: deque() for key in levels}
        self.public_muted = False
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="stream-mixer")
        self.blocks = 0

    def push(self, source_id: str, payload: bytes, channels: int) -> None:
        np = self._np
        samples = np.frombuffer(payload, dtype=np.int16).astype(np.float32)
        if channels == 1:
            samples = np.repeat(samples, 2)
        with self._lock:
            queue = self.queues.get(source_id)
            if queue is not None:
                queue.append(samples)
                # Never more than two seconds behind: a stalled mixer drops the oldest.
                while sum(len(chunk) for chunk in queue) > _RATE * 4:
                    queue.popleft()

    def _take(self, source_id: str, count: int) -> Any:
        np = self._np
        queue = self.queues[source_id]
        out = np.zeros(count, dtype=np.float32)
        filled = 0
        while filled < count and queue:
            chunk = queue[0]
            take = min(count - filled, len(chunk))
            out[filled : filled + take] = chunk[:take]
            filled += take
            if take == len(chunk):
                queue.popleft()
            else:
                queue[0] = chunk[take:]
        return out

    def mix_block(self) -> bytes:
        np = self._np
        count = _BLOCK * 2
        total = np.zeros(count, dtype=np.float32)
        with self._lock:
            for source_id, gain in self.gains.items():
                total += self._take(source_id, count) * gain
        if self.public_muted:
            total[:] = 0
        return np.clip(total, -32768, 32767).astype(np.int16).tobytes()

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        period = _BLOCK / _RATE
        next_at = time.perf_counter()
        while not self._stop.is_set():
            block = self.mix_block()
            for output in list(self.outputs):
                try:
                    output(block)
                except Exception:  # noqa: BLE001 - one broken output never stops the others
                    logger.debug("Stream output failed", exc_info=True)
            self.blocks += 1
            next_at += period
            delay = next_at - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            else:
                next_at = time.perf_counter()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(2)


class LiveStream:
    """One live show: sources, mixer, connection, saved copy, now-playing title."""

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
        self._captures: list[Any] = []
        self._encoder: subprocess.Popen[bytes] | None = None
        self._archive: subprocess.Popen[bytes] | None = None
        self._socket: socket.socket | None = None
        self._stop = threading.Event()
        levels = {source.source_id: source.level_db for source in sources}
        self.mixer = StreamMixer(levels, [self._to_encoder, self._to_archive])

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
        self._connect()
        self.started = time.time()
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
        shoutcast = self.settings.kind == "shoutcast"
        if shoutcast:
            self._socket = self._shoutcast_login()
        self._encoder = self._popen(command, stdout=shoutcast)
        if shoutcast:
            threading.Thread(target=self._pump, daemon=True, name="shoutcast-pump").start()
        self.connected = True

    def _shoutcast_login(self) -> socket.socket:
        login, headers = shoutcast_handshake(self.settings, self._password)
        address = (self.settings.host, shoutcast_source_port(self.settings))
        try:
            sock = socket.create_connection(address, timeout=10)
            if self.settings.secure:
                sock = ssl.create_default_context().wrap_socket(
                    sock, server_hostname=self.settings.host
                )
            sock.sendall(login)
            reply = sock.recv(256).decode("utf-8", "replace")
            if not reply.startswith("OK"):
                sock.close()
                raise StreamingError(
                    "The SHOUTcast server refused the password."
                    if "invalid" in reply.lower()
                    else f"The SHOUTcast server answered: {reply.strip() or 'nothing'}"
                )
            sock.sendall(headers)
            sock.settimeout(None)
            return sock
        except OSError as error:
            raise StreamingError(f"The SHOUTcast server could not be reached: {error}") from error

    def _pump(self) -> None:
        encoder, sock = self._encoder, self._socket
        if encoder is None or encoder.stdout is None or sock is None:
            return
        try:
            while not self._stop.is_set():
                chunk = encoder.stdout.read(4096)
                if not chunk:
                    break
                sock.sendall(chunk)
        except OSError:
            pass
        self.connected = False

    def _to_encoder(self, block: bytes) -> None:
        encoder = self._encoder
        if encoder is not None and encoder.stdin is not None and encoder.poll() is None:
            encoder.stdin.write(block)

    def _to_archive(self, block: bytes) -> None:
        archive = self._archive
        if archive is not None and archive.stdin is not None and archive.poll() is None:
            archive.stdin.write(block)

    def _watch(self) -> None:
        wait = 2.0
        while not self._stop.wait(1.0):
            encoder = self._encoder
            alive = (
                encoder is not None
                and encoder.poll() is None
                and (self.settings.kind != "shoutcast" or self.connected)
            )
            if alive:
                wait = 2.0
                continue
            self.connected = False
            if self.reconnects >= self.settings.reconnect_tries:
                self.on_event(
                    "The stream could not reconnect and has stopped. The saved copy continues.",
                    True,
                )
                return
            self.on_event(f"The stream dropped; trying again in {int(wait)} seconds.", True)
            self._close_connection()
            if self._stop.wait(wait):
                return
            wait = min(30.0, wait * 2)
            self.reconnects += 1
            try:
                self._connect()
                self.on_event("The stream is back on air.", False)
            except StreamingError as error:
                self.on_event(str(error), True)

    def _close_connection(self) -> None:
        encoder, self._encoder = self._encoder, None
        if encoder is not None:
            try:
                if encoder.stdin is not None:
                    encoder.stdin.close()
                encoder.wait(5)
            except (OSError, subprocess.TimeoutExpired):
                encoder.kill()
        sock, self._socket = self._socket, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def set_public_muted(self, muted: bool) -> None:
        self.mixer.public_muted = muted

    def update_title(self, title: str) -> str:
        """Set the now-playing title; ``""`` on success, else why not."""
        from urllib.error import URLError
        from urllib.request import Request, urlopen

        url, headers = metadata_request(self.settings, self._password, title)
        try:
            with urlopen(Request(url, headers=headers), timeout=10):
                return ""
        except (URLError, OSError) as error:
            return f"The title could not be updated: {error}"

    def status_line(self) -> str:
        from quill.core.demo_recording import format_timestamp

        state = "On air" if self.connected else "Reconnecting"
        if self.mixer.public_muted:
            state += ", public sound muted"
        parts = [f"{state}, {format_timestamp(time.time() - self.started)[:-2]}"]
        parts.append(f"{len(self._captures)} sound source{'s' if len(self._captures) != 1 else ''}")
        if self.reconnects:
            parts.append(f"{self.reconnects} reconnect{'s' if self.reconnects != 1 else ''}")
        if self.archive_path:
            parts.append("saving a copy")
        return "; ".join(parts) + "."

    def stop(self) -> None:
        self._stop.set()
        self.mixer.stop()
        for capture in self._captures:
            capture.close()
        self._close_connection()
        archive, self._archive = self._archive, None
        if archive is not None:
            try:
                if archive.stdin is not None:
                    archive.stdin.close()
                archive.wait(10)
            except (OSError, subprocess.TimeoutExpired):
                archive.kill()
        self.connected = False


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
    if "401" in detail or "Unauthorized" in detail:
        return "The server refused the user name or password."
    return f"The server did not accept the test: {detail}"
