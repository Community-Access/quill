"""A headless Edge or Chrome, driven over the DevTools protocol (wordpress.md 9.4).

Check This Page needs what a visitor gets -- the theme, the menus, the footer
and the content together -- so it loads the public page in the browser already
on the computer and asks it questions. Nothing is downloaded: when neither
Edge nor Chrome is installed, :func:`find_browser` says so and the check
explains why it cannot run.

The DevTools protocol is JSON over a WebSocket on the loopback address. The
standard library has no WebSocket client, so :class:`LoopbackSocket` is the
small part of RFC 6455 the protocol needs (text frames, fragments, ping and
close) and nothing else. It refuses any host but the loopback one: the
browser this module starts is the only thing it ever talks to.

The browser is started through :func:`quill.stability.safe_subprocess.spawn_subprocess_safely`
from a fixed list of install locations, never from a path in settings, so
nothing a document or a settings file says can choose what runs.

Stdlib only, no wx.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from quill.core.error_codes import CodedError

__all__ = [
    "BROWSER_BASENAMES",
    "BrowserMissingError",
    "CdpConnection",
    "CdpError",
    "HeadlessBrowser",
    "LoopbackSocket",
    "browser_candidates",
    "find_browser",
]

#: The only programs Check This Page will start. Matched on the file name, so
#: a candidate list cannot be widened into "run anything".
BROWSER_BASENAMES = frozenset({"msedge.exe", "chrome.exe", "msedge", "google-chrome", "chrome"})

_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
_START_TIMEOUT = 20.0


class CdpError(CodedError):
    """The browser could not be reached or answered with an error."""

    code = "QUILL-WP-AUDIT-BROWSER-FAILED"


class BrowserMissingError(CodedError):
    """Neither Edge nor Chrome is installed where QUILL looks."""

    code = "QUILL-WP-AUDIT-NO-BROWSER"


# --------------------------------------------------------------------------- #
# Finding the browser


def browser_candidates(environ: dict[str, str] | None = None) -> list[Path]:
    """Where Edge and Chrome install themselves on Windows, Edge first."""
    env = os.environ if environ is None else environ
    roots = [
        env.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        env.get("PROGRAMFILES", r"C:\Program Files"),
        env.get("LOCALAPPDATA", ""),
    ]
    found: list[Path] = []
    for root in roots:
        if root:
            found.append(Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    for root in roots:
        if root:
            found.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
    return found


def find_browser(candidates: Iterable[Path] | None = None) -> Path | None:
    """The first installed Edge or Chrome, or None. Never downloads one."""
    for path in browser_candidates() if candidates is None else candidates:
        if path.name.lower() in BROWSER_BASENAMES and path.is_file():
            return path
    return None


# --------------------------------------------------------------------------- #
# The WebSocket, loopback only


class LoopbackSocket:
    """Just enough RFC 6455 for the DevTools protocol, to the loopback address only."""

    def __init__(self, url: str, *, timeout: float = 30.0, sock: Any = None) -> None:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.scheme != "ws" or host not in _LOOPBACK:
            raise CdpError("QUILL only talks to a browser it started on this computer.")
        port = parsed.port or 80
        self._sock = sock or socket.create_connection((host, port), timeout=timeout)
        self._sock.settimeout(timeout)
        self._buffer = b""
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = parsed.path or "/"
        handshake = (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self._sock.sendall(handshake.encode("ascii"))
        head = self._read_until(b"\r\n\r\n")
        status = head.split(b"\r\n", 1)[0]
        if b" 101 " not in status + b" ":
            raise CdpError("The browser refused QUILL's connection.")

    def settimeout(self, seconds: float) -> None:
        self._sock.settimeout(max(0.1, seconds))

    def _fill(self) -> None:
        chunk = self._sock.recv(65536)
        if not chunk:
            raise CdpError("The browser closed the connection.")
        self._buffer += chunk

    def _read_until(self, marker: bytes) -> bytes:
        while marker not in self._buffer:
            self._fill()
        head, self._buffer = self._buffer.split(marker, 1)
        return head

    def _read_exact(self, size: int) -> bytes:
        while len(self._buffer) < size:
            self._fill()
        data, self._buffer = self._buffer[:size], self._buffer[size:]
        return data

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        header = bytes([0x80 | opcode])
        size = len(payload)
        if size < 126:
            header += bytes([0x80 | size])
        elif size < 1 << 16:
            header += bytes([0x80 | 126]) + struct.pack("!H", size)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", size)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self._sock.sendall(header + mask + masked)

    def send_text(self, text: str) -> None:
        self._send_frame(0x1, text.encode("utf-8"))

    def recv_text(self) -> str:
        parts: list[bytes] = []
        while True:
            first, second = self._read_exact(2)
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            size = second & 0x7F
            if size == 126:
                size = struct.unpack("!H", self._read_exact(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if second & 0x80 else b""
            payload = self._read_exact(size)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise CdpError("The browser closed the connection.")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            parts.append(payload)
            if fin:
                return b"".join(parts).decode("utf-8", errors="replace")

    def close(self) -> None:
        try:
            self._send_frame(0x8, b"")
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# The protocol


class CdpConnection:
    """Commands and events over one DevTools WebSocket."""

    def __init__(self, socket_: Any, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._ws = socket_
        self._next_id = 0
        self._events: list[dict[str, Any]] = []
        self._clock = clock

    def _receive(self, deadline: float) -> dict[str, Any]:
        remaining = deadline - self._clock()
        if remaining <= 0:
            raise CdpError("The page took too long to answer.")
        self._ws.settimeout(remaining)
        try:
            raw = self._ws.recv_text()
        except TimeoutError as exc:
            raise CdpError("The page took too long to answer.") from exc
        message = json.loads(raw)
        return message if isinstance(message, dict) else {}

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        session_id: str = "",
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        self._next_id += 1
        request: dict[str, Any] = {"id": self._next_id, "method": method, "params": params or {}}
        if session_id:
            request["sessionId"] = session_id
        self._ws.send_text(json.dumps(request))
        deadline = self._clock() + timeout
        while True:
            message = self._receive(deadline)
            if message.get("id") == self._next_id:
                if "error" in message:
                    error = message["error"]
                    text = error.get("message", "") if isinstance(error, dict) else str(error)
                    raise CdpError(f"The browser could not do that: {text}")
                result = message.get("result")
                return result if isinstance(result, dict) else {}
            if "method" in message:
                self._events.append(message)

    def wait_event(self, method: str, *, session_id: str = "", timeout: float = 30.0) -> None:
        def matches(event: dict[str, Any]) -> bool:
            return event.get("method") == method and (
                not session_id or event.get("sessionId") == session_id
            )

        for event in self._events:
            if matches(event):
                self._events.remove(event)
                return
        deadline = self._clock() + timeout
        while True:
            message = self._receive(deadline)
            if matches(message):
                return
            if "method" in message:
                self._events.append(message)


class HeadlessBrowser:
    """Start Edge or Chrome hidden, with a throwaway profile, and connect to it.

    A context manager: the browser and its profile folder are gone when the
    ``with`` block ends, whatever happened inside it.
    """

    def __init__(self, executable: Path, *, timeout: float = _START_TIMEOUT) -> None:
        if executable.name.lower() not in BROWSER_BASENAMES:
            raise BrowserMissingError("QUILL only starts Microsoft Edge or Google Chrome.")
        self.executable = executable
        self.timeout = timeout
        self._process: Any = None
        self._profile = ""
        self._socket: LoopbackSocket | None = None
        self.connection: CdpConnection | None = None

    def __enter__(self) -> CdpConnection:
        from quill.stability.safe_subprocess import spawn_subprocess_safely

        self._profile = tempfile.mkdtemp(prefix="quill-check-page-")
        args = [
            str(self.executable),
            "--headless=new",
            "--remote-debugging-port=0",
            f"--user-data-dir={self._profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-sync",
            "--mute-audio",
            "about:blank",
        ]
        try:
            self._process = spawn_subprocess_safely(args)
        except OSError as exc:
            self._cleanup()
            raise CdpError(f"{self.executable.name} would not start: {exc}") from exc
        try:
            port, path = self._devtools_address()
            self._socket = LoopbackSocket(f"ws://127.0.0.1:{port}{path}")
        except BaseException:
            self._cleanup()
            raise
        self.connection = CdpConnection(self._socket)
        return self.connection

    def _devtools_address(self) -> tuple[int, str]:
        marker = Path(self._profile) / "DevToolsActivePort"
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise CdpError(f"{self.executable.name} stopped as soon as it started.")
            if marker.is_file():
                lines = marker.read_text(encoding="utf-8").split()
                if len(lines) >= 2 and lines[0].isdigit():
                    return int(lines[0]), lines[1]
            time.sleep(0.1)
        raise CdpError(f"{self.executable.name} did not get ready in time.")

    def __exit__(self, *_exc: object) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._process is not None:
            try:
                self._process.kill()
                self._process.wait(timeout=10)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
            for stream in (self._process.stdin, self._process.stdout, self._process.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except OSError:
                    pass
            self._process = None
        if self._profile:
            shutil.rmtree(self._profile, ignore_errors=True)
            self._profile = ""
