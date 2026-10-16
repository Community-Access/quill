"""Recorded fakes for the cloud speech providers: no test touches the network.

``install(monkeypatch)`` replaces the two openers in
``quill.core.windows_dictation.cloud.transport`` and returns a :class:`Wire`
that records every request and socket and answers from a script.
"""

from __future__ import annotations

import io
import json
import queue
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError

from quill.core.windows_dictation.cloud import transport


class FakeResponse(io.BytesIO):
    def __init__(self, body: Any = b"", status: int = 200) -> None:
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode("utf-8")
        super().__init__(bytes(body))
        self.status = status

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()


def http_error(url: str, status: int, body: bytes = b"{}") -> HTTPError:
    return HTTPError(url, status, "refused", {}, io.BytesIO(body))  # type: ignore[arg-type]


class FakeSocket:
    """A WebSocket whose answers come from *react(message) -> [replies]*."""

    def __init__(self, react: Callable[[Any], list[Any]] | None = None) -> None:
        self.sent: list[Any] = []
        self.closed = False
        self._react = react or (lambda _message: [])
        self._inbox: queue.Queue[Any] = queue.Queue()

    def push(self, *messages: Any) -> None:
        for message in messages:
            if not isinstance(message, (str, bytes)):
                message = json.dumps(message)
            self._inbox.put(message)

    def send(self, message: Any) -> None:
        if self.closed:
            raise OSError("closed")
        self.sent.append(message)
        self.push(*self._react(message))

    def recv(self, timeout: float | None = None) -> Any:
        del timeout
        while not self.closed:
            try:
                return self._inbox.get(timeout=0.05)
            except queue.Empty:
                continue
        raise OSError("closed")

    def close(self) -> None:
        self.closed = True

    def text_sent(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for message in self.sent:
            if isinstance(message, str):
                try:
                    out.append(json.loads(message))
                except ValueError:
                    out.append({"raw": message})
        return out

    def binary_sent(self) -> list[bytes]:
        return [message for message in self.sent if isinstance(message, bytes)]


class Wire:
    """Every request and socket a test caused, and the answers to give."""

    def __init__(self) -> None:
        self.requests: list[Any] = []
        self.sockets: list[tuple[str, dict[str, str], FakeSocket]] = []
        self.answers: list[Any] = []
        self.socket_factory: Callable[[str, dict[str, str]], FakeSocket] = lambda _url, _headers: (
            FakeSocket()
        )

    def answer(self, *answers: Any) -> None:
        """Queue answers: a dict/bytes body, a FakeResponse, or an exception."""
        self.answers.extend(answers)

    def urlopen(self, request: Any, *, timeout: float = 30.0) -> Any:
        del timeout
        self.requests.append(request)
        answer = self.answers.pop(0) if self.answers else {}
        if isinstance(answer, BaseException):
            raise answer
        return answer if isinstance(answer, FakeResponse) else FakeResponse(answer)

    def create_connection(self, url: str, headers: Any = None) -> FakeSocket:
        socket = self.socket_factory(url, dict(headers or {}))
        self.sockets.append((url, dict(headers or {}), socket))
        return socket

    @property
    def calls(self) -> int:
        return len(self.requests) + len(self.sockets)


def install(monkeypatch: Any) -> Wire:
    wire = Wire()
    monkeypatch.setattr(transport, "urlopen", wire.urlopen)
    monkeypatch.setattr(transport, "create_connection", wire.create_connection)
    return wire


class MemoryBackend:
    """A credential store in a dictionary, and a folder for protected files."""

    def __init__(self, folder: Any) -> None:
        self.secrets: dict[str, str] = {}
        self._folder = folder

    def install(self, monkeypatch: Any) -> MemoryBackend:
        from quill.core.windows_dictation.cloud import credentials

        monkeypatch.setattr(
            credentials,
            "backend",
            credentials.Backend(
                load=lambda target: self.secrets.get(target, ""),
                save=lambda target, value: self.secrets.__setitem__(target, value),
                delete=lambda target: self.secrets.pop(target, None),
                protect=lambda text: "protected:" + text[::-1],
                unprotect=lambda text: text.removeprefix("protected:")[::-1],
                folder=lambda: self._folder,
            ),
        )
        return self
