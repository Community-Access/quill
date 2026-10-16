"""One WebSocket streaming session, shared by every streaming provider (D-35).

Connect, send 16 kHz 16-bit PCM as it is heard, read provisional and final
words, close at stop. Each provider is a small :class:`SocketAdapter` that
says what to send first, how one block of audio is wrapped, what asks the
provider to finish the phrase now, and what each message it sends back means.

**QUILL finds the pause, not the provider.** At the pause the recogniser calls
:meth:`SocketSession.commit`, which sends the adapter's "finish now" messages
(where the provider has one) and waits for the phrase's final words: until a
final has arrived and nothing provisional is left, or for
:attr:`SocketAdapter.settle_seconds`. Provisional words go only to the live
preview (``on_delta``), through :mod:`~quill.core.windows_dictation.preview`'s
committed-and-tentative contract, so nothing provisional is ever typed.

The opener is :func:`quill.core.windows_dictation.cloud.transport.create_connection`,
called by each provider at its own call site (one egress entry each) and
handed in here as *connect*.

wx-free.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.windows_dictation.cloud.errors import CloudNetworkError, CloudSpeechError
from quill.core.windows_dictation.cloud.transport import failure

__all__ = ["Heard", "SocketAdapter", "SocketSession", "pcm16"]

_RATE = 16_000


def pcm16(samples: Any, rate: int = _RATE) -> bytes:
    """Float samples (-1..1, 16 kHz) as little-endian 16-bit PCM at *rate*."""
    from quill.core.windows_dictation.openai_transcribe import pcm16 as _pcm16

    return _pcm16(samples, rate)


@dataclass(frozen=True, slots=True)
class Heard:
    """What one message from the provider meant."""

    #: The phrase's provisional words so far (replacing the last), or None.
    partial: str | None = None
    #: Words the provider will not change again, or None.
    final: str | None = None
    #: A sentence when the provider reported a problem, or "".
    error: str = ""
    #: The provider says everything for the phrase has now arrived.
    settled: bool = False


class SocketAdapter:
    """What one streaming provider says and means. Subclass per provider."""

    #: The provider's name, for sentences.
    name: str = ""
    #: The field a refused handshake points at.
    auth_field: str = "Key"
    #: How long :meth:`SocketSession.commit` waits for the final words.
    settle_seconds: float = 4.0
    #: Sample rate the provider is told.
    rate: int = _RATE
    #: The smallest block of audio the provider accepts, in milliseconds;
    #: smaller blocks are gathered first (AssemblyAI wants 50 to 1,000).
    min_chunk_ms: int = 0
    #: Send :meth:`keepalive` after this many seconds without sending anything
    #: (between phrases nothing else goes); 0 for never.
    keepalive_seconds: float = 0.0

    def keepalive(self) -> str | bytes:
        """What keeps an idle connection open: a tenth of a second of silence,
        unless the provider has a message for it."""
        return self.audio(bytes(self.rate // 10 * 2))

    def opening(self) -> Sequence[str | bytes]:
        """Messages sent right after connecting (configuration)."""
        return ()

    def audio(self, pcm: bytes) -> str | bytes:
        """One block of audio as the provider wants it (raw bytes by default)."""
        return pcm

    def finish_phrase(self) -> Sequence[str | bytes]:
        """Messages asking for the phrase's final words now (none by default)."""
        return ()

    def closing(self) -> Sequence[str | bytes]:
        """Messages sent before the socket closes."""
        return ()

    def hear(self, message: str | bytes) -> Heard:
        """What *message* means. JSON text by default, handed to :meth:`hear_json`."""
        if isinstance(message, bytes):
            message = message.decode("utf-8", errors="replace")
        try:
            event = json.loads(message)
        except ValueError:
            return Heard()
        return self.hear_json(event) if isinstance(event, dict) else Heard()

    def hear_json(self, event: dict[str, Any]) -> Heard:
        return Heard()


class SocketSession:
    """A streaming session with the shape the recogniser drives (LiveSession)."""

    def __init__(
        self,
        adapter: SocketAdapter,
        connect: Callable[[], Any],
        *,
        on_delta: Callable[[str], None] | None = None,
    ) -> None:
        self._adapter = adapter
        self._connect = connect
        self._on_delta = on_delta
        self._socket: Any = None
        self._lock = threading.Lock()
        self._settled = threading.Event()
        self._finals: list[str] = []
        self._partial = ""
        self._error: CloudSpeechError | None = None
        self._reader: threading.Thread | None = None
        self._buffer = bytearray()
        self._min_bytes = adapter.rate * 2 * adapter.min_chunk_ms // 1000
        self._last_send = time.monotonic()
        self._closed = threading.Event()
        self._send_lock = threading.Lock()  # the worker and the keep-alive both send

    # -- the LiveSession verbs ---------------------------------------------- #

    def open(self) -> None:
        """Connect and configure. Raises :class:`CloudSpeechError` with a sentence."""
        name = self._adapter.name
        try:
            self._socket = self._connect()
        except CloudSpeechError:
            raise
        except Exception as error:  # noqa: BLE001 - one sentence, never the key
            raise failure(name, error, auth_field=self._adapter.auth_field) from None
        for message in self._adapter.opening():
            self._send(message)
        self._reader = threading.Thread(
            target=self._read, name=f"dictation-{name.lower().replace(' ', '-')}", daemon=True
        )
        self._reader.start()
        if self._adapter.keepalive_seconds > 0:
            threading.Thread(
                target=self._keep_alive, name="dictation-keepalive", daemon=True
            ).start()

    def append(self, samples: Any) -> None:
        self._buffer += pcm16(samples, self._adapter.rate)
        if len(self._buffer) >= self._min_bytes:
            self._flush()

    def _flush(self) -> None:
        if not self._buffer:
            return
        if len(self._buffer) < self._min_bytes:  # the phrase's tail: pad with silence
            self._buffer += bytes(self._min_bytes - len(self._buffer))
        block, self._buffer = bytes(self._buffer), bytearray()
        self._send(self._adapter.audio(block))

    def commit(self, timeout: float = 15.0) -> str:
        """The phrase's final words, once the provider has settled them."""
        with self._lock:
            # Everything already final and nothing provisional: no need to wait.
            ready = bool(self._finals) and not self._partial
            if not ready:
                self._settled.clear()
        if not ready:
            self._flush()
            for message in self._adapter.finish_phrase():
                self._send(message)
            self._settled.wait(min(timeout, self._adapter.settle_seconds))
        with self._lock:
            error, self._error = self._error, None
            text = " ".join(part for part in self._finals if part)
            if not text:
                text = self._partial  # better the provisional words than none
            self._finals, self._partial = [], ""
            self._settled.clear()
        if error is not None:
            raise error
        return " ".join(text.split())

    def clear(self) -> None:
        """Forget what was heard since the last commit (Escape)."""
        with self._lock:
            self._finals, self._partial = [], ""
            self._settled.clear()
        self._buffer = bytearray()

    def close(self) -> None:
        self._closed.set()
        socket, self._socket = self._socket, None
        if socket is not None:
            for message in self._adapter.closing():
                try:
                    socket.send(message)
                except Exception:  # noqa: BLE001 - it is closing either way
                    break
            try:
                socket.close()
            except Exception:  # noqa: BLE001
                pass
        self._settled.set()

    # -- the wire ------------------------------------------------------------- #

    def _send(self, message: str | bytes) -> None:
        socket = self._socket
        if socket is None:
            raise CloudNetworkError(f"The connection to {self._adapter.name} has closed.")
        try:
            with self._send_lock:
                socket.send(message)
        except Exception:  # noqa: BLE001
            raise CloudNetworkError(f"The connection to {self._adapter.name} was lost.") from None
        self._last_send = time.monotonic()

    def _keep_alive(self) -> None:
        interval = self._adapter.keepalive_seconds
        while not self._closed.wait(min(1.0, interval)):
            if self._socket is None:
                return
            if time.monotonic() - self._last_send >= interval:
                try:
                    self._send(self._adapter.keepalive())
                except CloudSpeechError:
                    return

    def _read(self) -> None:
        while self._socket is not None:
            try:
                message = self._socket.recv()
            except Exception:  # noqa: BLE001 - closed, or the network went
                if self._socket is not None:
                    with self._lock:
                        self._error = CloudNetworkError(
                            f"The connection to {self._adapter.name} was lost."
                        )
                self._settled.set()
                return
            if message:
                self._take(self._adapter.hear(message))

    def _take(self, heard: Heard) -> None:
        delta = None
        with self._lock:
            if heard.error:
                self._error = CloudSpeechError(heard.error)
                self._settled.set()
                return
            if heard.final is not None:
                if heard.final.strip():
                    self._finals.append(heard.final.strip())
                self._partial = ""
            if heard.partial is not None:
                self._partial = heard.partial.strip()
                if self._partial:
                    self._settled.clear()  # more is coming for this phrase
            if heard.final is not None or heard.partial is not None:
                delta = " ".join([*self._finals, self._partial]).strip()
            if heard.settled or (heard.final is not None and not self._partial):
                self._settled.set()
        if delta and self._on_delta is not None:
            self._on_delta(delta)
