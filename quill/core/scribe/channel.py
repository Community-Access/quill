"""The Phoenix document channel: start conversions and follow them (PRD 3.5).

Every conversion other than the automatic ``html_stream`` preview starts
**only** here: ``wss://<host>/socket/websocket?vsn=2.0.0&token=...``, topic
``documents:<id>``. Frames are Phoenix's ``[join_ref, ref, topic, event,
payload]``. A heartbeat goes every 30 seconds while QUILL waits (the server
drops a connection silent for about 66). One conversion per document runs at
a time; ``start_conversion`` while one runs answers ``conversion_in_progress``.

If the connection drops, the conversion carries on at Scribe: the runner
opens a new channel on the same document and never uploads again.

**Preview chunks are replayed on join.** QUILL joins with ``replay_chunks``
(as Pneuma's client does since 2026-11-23), so Scribe first sends the
``html_stream`` chunks already streamed: a preview joined after the upload
started, or after a dropped connection, misses none. Each chunk carries an
``index`` counting up from 0; a :class:`ChunkLedger` shared by every channel
one opener makes remembers the last index passed on per document, and a
chunk at or below it (one already shown) is dropped. Servers from before
``index`` send neither the index nor the replay, and their chunks pass as
they always have.

GATE-9: :func:`create_connection` is the one call site that opens the socket.
The token is in the address because that is Phoenix's protocol; the address
is never logged. wx-free; tests hand :class:`DocumentChannel` a scripted
``connector``.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast
from urllib.parse import urlencode, urlsplit, urlunsplit

from quill.core.scribe.errors import (
    ScribeError,
    ScribeOfflineError,
    ScribeSignInError,
    error_from_server,
)

if TYPE_CHECKING:
    from quill.core.scribe.client import ScribeClient

logger = logging.getLogger(__name__)

HEARTBEAT_S = 30.0
_JOIN_TIMEOUT_S = 30.0


class Socket(Protocol):
    def send(self, message: str) -> None: ...
    def recv(self, timeout: float | None = None) -> str: ...
    def close(self) -> None: ...


#: ``connector(url) -> Socket``; raises ``OSError`` when it cannot connect.
Connector = Callable[[str], Socket]


def create_connection(url: str) -> Socket:
    """GATE-9: the WebSocket to Scribe's channel, certificate-checked."""
    from quill.core.net import verified_ssl_context

    try:
        from websockets.sync.client import (  # type: ignore[import-not-found,unused-ignore]
            connect,
        )
    except ImportError as error:  # pragma: no cover - the runtime carries it
        raise ScribeError(
            "Scribe for Documents needs a part that is missing from this copy of QUILL."
        ) from error
    secure = url.startswith("wss://")
    connection = connect(
        url,
        ssl=verified_ssl_context() if secure else None,
        open_timeout=20,
        max_size=None,
        user_agent_header="QUILL (Scribe for Documents)",
    )
    socket = cast("Socket", connection)  # recv() has more overloads than Socket names
    return socket


def channel_url(base_url: str, token: str, locale: str = "") -> str:
    """The socket address: the API host over ``wss`` (``ws`` only for loopback tests)."""
    parts = urlsplit(base_url)
    scheme = "wss" if parts.scheme == "https" else "ws"
    query = {"vsn": "2.0.0", "token": token}
    if locale:
        query["locale"] = locale
    return urlunsplit((scheme, parts.netloc, "/socket/websocket", urlencode(query), ""))


@dataclass(frozen=True, slots=True)
class ChannelEvent:
    """Something the server pushed: ``status``, ``chunk``, ``conversion_complete``,
    ``error`` or ``password_required``. A chunk's *index* is ``-1`` when the
    server sent none."""

    kind: str
    format: str = ""
    stage: str = ""
    progress: float = 0.0
    content: str = ""
    output_id: str = ""
    reason: str = ""
    message: str = ""
    purchase_url: str = ""
    index: int = -1


class ChunkLedger:
    """The last preview chunk passed on, per document, across reconnects.

    A document's entry is forgotten when its preview completes, so a later
    preview of the same document (its indexes start at 0 again) is passed
    on whole rather than dropped as already seen.
    """

    def __init__(self) -> None:
        self._last: dict[str, int] = {}

    def admit(self, document_id: str, event: ChannelEvent) -> bool:
        """True to pass *event* on; False for a chunk already passed on."""
        if event.kind == "conversion_complete" and event.format == "html_stream":
            self._last.pop(document_id, None)
            return True
        if event.kind != "chunk" or event.index < 0:
            return True
        if event.index <= self._last.get(document_id, -1):
            return False
        self._last[document_id] = event.index
        return True


def parse_event(event: str, payload: Any) -> ChannelEvent | None:
    """One pushed frame as a :class:`ChannelEvent`, or ``None`` for others."""
    data = payload if isinstance(payload, dict) else {}
    if event == "status":
        if not data.get("format") or not data.get("stage"):
            return None
        try:
            progress = float(data.get("progress") or 0.0)
        except (TypeError, ValueError):
            progress = 0.0
        return ChannelEvent(
            "status",
            format=str(data["format"]),
            stage=str(data["stage"]),
            progress=max(0.0, min(1.0, progress)),
        )
    if event == "chunk":
        raw_index = data.get("index")
        index = raw_index if isinstance(raw_index, int) and not isinstance(raw_index, bool) else -1
        return ChannelEvent("chunk", content=str(data.get("content") or ""), index=max(-1, index))
    if event == "conversion_complete":
        if not data.get("format"):
            return None
        return ChannelEvent(
            "conversion_complete",
            format=str(data["format"]),
            output_id=str(data.get("output_id") or ""),
        )
    if event == "error":
        return ChannelEvent(
            "error",
            reason=str(data.get("reason") or "server_error"),
            message=str(data.get("message") or ""),
            purchase_url=str(data.get("purchase_url") or ""),
        )
    if event == "password_required":
        return ChannelEvent("password_required")
    return None


class DocumentChannel:
    """A joined ``documents:<id>`` channel. Call :meth:`next_event` while waiting."""

    def __init__(
        self,
        socket: Socket,
        document_id: str,
        *,
        clock: Callable[[], float] = time.monotonic,
        chunk_ledger: ChunkLedger | None = None,
    ) -> None:
        self._socket = socket
        self.document_id = document_id
        self._ledger = chunk_ledger or ChunkLedger()
        self.topic = f"documents:{document_id}"
        self._join_ref = "1"
        self._next_ref = 2
        self._pending: deque[ChannelEvent] = deque()
        self._clock = clock
        self._next_heartbeat = clock() + HEARTBEAT_S

    @classmethod
    def open(
        cls,
        base_url: str,
        token: str,
        document_id: str,
        *,
        connector: Connector | None = None,
        locale: str = "",
        clock: Callable[[], float] = time.monotonic,
        chunk_ledger: ChunkLedger | None = None,
    ) -> DocumentChannel:
        """Connect and join. Raises :class:`ScribeOfflineError` if it cannot connect.

        The join asks for the preview chunks already streamed (``replay_chunks``);
        *chunk_ledger* drops the ones an earlier channel already passed on.
        """
        try:
            url = channel_url(base_url, token, locale)
            socket = create_connection(url) if connector is None else connector(url)
        except OSError as error:
            logger.info("Scribe channel connect failed (%s)", type(error).__name__)
            raise ScribeOfflineError(
                "Couldn't connect to Scribe. Check your connection and try again."
            ) from None
        except ScribeError:
            raise
        except Exception as error:  # noqa: BLE001 - websockets' handshake errors
            status = getattr(getattr(error, "response", None), "status_code", 0)
            if status in (401, 403):
                raise error_from_server("unauthenticated", None, status=401) from None
            raise ScribeOfflineError(
                "Couldn't connect to Scribe. Check your connection and try again."
            ) from None
        channel = cls(socket, document_id, clock=clock, chunk_ledger=chunk_ledger)
        channel._send(
            channel._join_ref, "phx_join", {"replay_chunks": True}, join_ref=channel._join_ref
        )
        channel._await_reply(channel._join_ref, _JOIN_TIMEOUT_S)
        logger.info("Scribe channel joined id=%s", document_id)
        return channel

    # ------------------------------------------------------------------ wire

    def _take_ref(self) -> str:
        ref = str(self._next_ref)
        self._next_ref += 1
        return ref

    def _send(
        self, ref: str, event: str, payload: Any, *, join_ref: str | None, topic: str = ""
    ) -> None:
        frame = [join_ref, ref, topic or self.topic, event, payload]
        try:
            self._socket.send(json.dumps(frame))
        except Exception:  # noqa: BLE001 - any socket failure is "offline"
            raise ScribeOfflineError("The connection to Scribe for Documents was lost.") from None

    def _heartbeat_if_due(self) -> None:
        if self._clock() >= self._next_heartbeat:
            self._next_heartbeat = self._clock() + HEARTBEAT_S
            self._send(self._take_ref(), "heartbeat", {}, join_ref=None, topic="phoenix")

    def _recv_frame(self, timeout: float) -> list[Any] | None:
        """One frame, or ``None`` when *timeout* passed with nothing (heartbeats sent)."""
        deadline = self._clock() + max(0.0, timeout)
        while True:
            self._heartbeat_if_due()
            wait = min(deadline, self._next_heartbeat) - self._clock()
            try:
                raw = self._socket.recv(timeout=max(0.0, wait))
            except TimeoutError:
                if self._clock() >= deadline:
                    return None
                continue
            except Exception:  # noqa: BLE001 - closed or failed: either way, offline
                raise ScribeOfflineError(
                    "The connection to Scribe for Documents was lost."
                ) from None
            try:
                frame = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if isinstance(frame, list) and len(frame) == 5:
                return frame

    def _await_reply(self, ref: str, timeout: float) -> dict[str, Any]:
        deadline = self._clock() + timeout
        while True:
            left = deadline - self._clock()
            if left <= 0:
                raise ScribeOfflineError("Scribe for Documents did not answer in time.")
            frame = self._recv_frame(left)
            if frame is None:
                continue
            _join, frame_ref, topic, event, payload = frame
            if topic != self.topic:
                continue
            if event == "phx_reply" and frame_ref == ref:
                reply: dict[str, Any] = payload if isinstance(payload, dict) else {}
                raw = reply.get("response")
                response: dict[str, Any] = raw if isinstance(raw, dict) else {}
                if reply.get("status") == "ok":
                    return response
                raise error_from_server(
                    str(response.get("reason") or ""),
                    str(response.get("message") or "") or None,
                    purchase_url=str(response.get("purchase_url") or ""),
                )
            if event in ("phx_error", "phx_close"):
                raise ScribeOfflineError("The connection to Scribe for Documents was lost.")
            parsed = parse_event(event, payload)
            if parsed is not None and self._ledger.admit(self.document_id, parsed):
                self._pending.append(parsed)

    # --------------------------------------------------------------- public

    def start_conversion(self, format_id: str, password: str = "") -> str:
        """Start *format_id*; returns its output ID (an existing one if already made).

        Raises the coded error for ``conversion_in_progress``, ``rate_limited``,
        ``needs_purchase``, ``password_required`` and the rest. A wrong password
        is not caught here: an ``invalid_password`` error event follows.
        *password* goes in this one frame and is never kept or logged.
        """
        ref = self._take_ref()
        payload: dict[str, Any] = {"format": format_id}
        if password:
            payload["password"] = password
        self._send(ref, "start_conversion", payload, join_ref=self._join_ref)
        response = self._await_reply(ref, _JOIN_TIMEOUT_S)
        logger.info("Scribe conversion started id=%s format=%s", self.document_id, format_id)
        return str(response.get("output_id") or "")

    def next_event(self, timeout: float = 1.0) -> ChannelEvent | None:
        """The next pushed event, or ``None`` after *timeout* seconds of quiet."""
        self._heartbeat_if_due()
        if self._pending:
            return self._pending.popleft()
        deadline = self._clock() + timeout
        while True:
            left = deadline - self._clock()
            if left <= 0:
                return None
            frame = self._recv_frame(left)
            if frame is None:
                return None
            _join, _ref, topic, event, payload = frame
            if topic != self.topic:
                continue
            if event in ("phx_error", "phx_close"):
                raise ScribeOfflineError("The connection to Scribe for Documents was lost.")
            parsed = parse_event(event, payload)
            if parsed is not None and self._ledger.admit(self.document_id, parsed):
                return parsed

    def close(self) -> None:
        try:
            self._socket.close()
        except Exception:  # noqa: BLE001 - one already lost is fine
            pass


def default_channel_opener(
    connector: Connector | None = None, locale: str = ""
) -> Callable[[ScribeClient, str], DocumentChannel]:
    """Open a document channel with the client's token (refreshed once on refusal).

    Every channel the opener makes shares one :class:`ChunkLedger`, so a
    reconnect's replayed preview chunks are not passed on twice.
    """
    ledger = ChunkLedger()

    def opener(client: ScribeClient, document_id: str) -> DocumentChannel:
        tokens = client._tokens  # noqa: SLF001 - the same session the client uses
        try:
            return DocumentChannel.open(
                client.base_url,
                tokens.access_token(),
                document_id,
                connector=connector,
                locale=locale,
                chunk_ledger=ledger,
            )
        except ScribeSignInError:
            return DocumentChannel.open(
                client.base_url,
                tokens.force_refresh(),
                document_id,
                connector=connector,
                locale=locale,
                chunk_ledger=ledger,
            )

    return opener


__all__ = [
    "default_channel_opener",
    "HEARTBEAT_S",
    "ChannelEvent",
    "ChunkLedger",
    "Connector",
    "DocumentChannel",
    "Socket",
    "channel_url",
    "create_connection",
    "parse_event",
]
