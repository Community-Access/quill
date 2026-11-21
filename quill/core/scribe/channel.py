"""The Phoenix document channel: start conversions and follow them (PRD 3.5).

Every conversion other than the automatic ``html_stream`` preview starts
**only** here: ``wss://<host>/socket/websocket?vsn=2.0.0&token=...``, topic
``documents:<id>``. Frames are Phoenix's ``[join_ref, ref, topic, event,
payload]``. A heartbeat goes every 30 seconds while QUILL waits (the server
drops a connection silent for about 66). One conversion per document runs at
a time; ``start_conversion`` while one runs answers ``conversion_in_progress``.

If the connection drops, the conversion carries on at Scribe: the runner
opens a new channel on the same document and never uploads again.

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
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit, urlunsplit

from quill.core.scribe.errors import (
    ScribeError,
    ScribeOfflineError,
    error_from_server,
)

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
    socket: Socket = connect(
        url,
        ssl=verified_ssl_context() if secure else None,
        open_timeout=20,
        max_size=None,
        user_agent_header="QUILL (Scribe for Documents)",
    )
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
    ``error`` or ``password_required``."""

    kind: str
    format: str = ""
    stage: str = ""
    progress: float = 0.0
    content: str = ""
    output_id: str = ""
    reason: str = ""
    message: str = ""
    purchase_url: str = ""


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
        return ChannelEvent("chunk", content=str(data.get("content") or ""))
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
    ) -> None:
        self._socket = socket
        self.document_id = document_id
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
    ) -> DocumentChannel:
        """Connect and join. Raises :class:`ScribeOfflineError` if it cannot connect."""
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
        channel = cls(socket, document_id, clock=clock)
        channel._send(channel._join_ref, "phx_join", {}, join_ref=channel._join_ref)
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
                reply = payload if isinstance(payload, dict) else {}
                response = reply.get("response") if isinstance(reply.get("response"), dict) else {}
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
            if parsed is not None:
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
            if parsed is not None:
                return parsed

    def close(self) -> None:
        try:
            self._socket.close()
        except Exception:  # noqa: BLE001 - one already lost is fine
            pass


__all__ = [
    "HEARTBEAT_S",
    "ChannelEvent",
    "Connector",
    "DocumentChannel",
    "Socket",
    "channel_url",
    "create_connection",
    "parse_event",
]
