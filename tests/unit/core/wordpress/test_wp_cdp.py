"""The loopback WebSocket and DevTools protocol client, with a fake socket (9.4)."""

from __future__ import annotations

import json
import struct

import pytest

from quill.core.wordpress import cdp


def _frame(opcode: int, payload: bytes, *, fin: bool = True) -> bytes:
    head = bytes([(0x80 if fin else 0) | opcode])
    if len(payload) < 126:
        return head + bytes([len(payload)]) + payload
    return head + bytes([126]) + struct.pack("!H", len(payload)) + payload


class FakeSocket:
    def __init__(self, incoming: bytes, *, status: bytes = b"101") -> None:
        self.incoming = b"HTTP/1.1 " + status + b" Switching Protocols\r\n\r\n" + incoming
        self.sent: list[bytes] = []
        self.timeout = None

    def settimeout(self, seconds):
        self.timeout = seconds

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def recv(self, size: int) -> bytes:
        chunk, self.incoming = self.incoming[:size], self.incoming[size:]
        return chunk

    def close(self) -> None:
        pass


def _unmask(frame: bytes) -> tuple[int, bytes]:
    size = frame[1] & 0x7F
    offset = 2
    if size == 126:
        size = struct.unpack("!H", frame[2:4])[0]
        offset = 4
    mask = frame[offset : offset + 4]
    body = frame[offset + 4 : offset + 4 + size]
    return frame[0] & 0x0F, bytes(b ^ mask[i % 4] for i, b in enumerate(body))


def test_only_the_loopback_address_is_allowed() -> None:
    with pytest.raises(cdp.CdpError):
        cdp.LoopbackSocket("ws://radio.example:9222/devtools", sock=FakeSocket(b""))
    with pytest.raises(cdp.CdpError):
        cdp.LoopbackSocket("ws://127.0.0.1:9222/x", sock=FakeSocket(b"", status=b"403"))


def test_frames_fragments_ping_and_masked_sends() -> None:
    long = b"x" * 300
    incoming = (
        _frame(0x9, b"hi") + _frame(0x1, b"he", fin=False) + _frame(0x0, b"llo") + _frame(0x1, long)
    )
    sock = FakeSocket(incoming)
    ws = cdp.LoopbackSocket("ws://127.0.0.1:9222/devtools/browser/abc", sock=sock)
    assert sock.sent[0].startswith(b"GET /devtools/browser/abc HTTP/1.1")
    assert ws.recv_text() == "hello"
    assert _unmask(sock.sent[1]) == (0xA, b"hi")  # the ping was answered
    assert ws.recv_text() == "x" * 300
    ws.send_text("é" * 70)
    assert _unmask(sock.sent[-1]) == (0x1, ("é" * 70).encode())


def test_a_close_frame_is_an_error() -> None:
    ws = cdp.LoopbackSocket("ws://127.0.0.1:1/", sock=FakeSocket(_frame(0x8, b"")))
    with pytest.raises(cdp.CdpError):
        ws.recv_text()


class ScriptedSocket:
    def __init__(self, replies: list[dict]) -> None:
        self.replies = [json.dumps(r) for r in replies]
        self.sent: list[dict] = []

    def settimeout(self, _s):
        pass

    def send_text(self, text: str) -> None:
        self.sent.append(json.loads(text))

    def recv_text(self) -> str:
        if not self.replies:
            raise TimeoutError
        return self.replies.pop(0)


def test_calls_keep_events_for_later_and_report_errors() -> None:
    socket_ = ScriptedSocket([
        {"method": "Page.loadEventFired", "sessionId": "S"},
        {"id": 1, "result": {"ok": True}},
        {"id": 2, "error": {"message": "No target"}},
    ])
    connection = cdp.CdpConnection(socket_)
    assert connection.call("Page.enable", session_id="S") == {"ok": True}
    assert socket_.sent[0] == {"id": 1, "method": "Page.enable", "params": {}, "sessionId": "S"}
    connection.wait_event("Page.loadEventFired", session_id="S")  # already seen: no wait
    with pytest.raises(cdp.CdpError, match="No target"):
        connection.call("Target.closeTarget")


def test_a_silent_browser_times_out_in_words() -> None:
    connection = cdp.CdpConnection(ScriptedSocket([]))
    with pytest.raises(cdp.CdpError, match="too long"):
        connection.wait_event("Page.loadEventFired", timeout=1)
