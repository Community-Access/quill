"""Going live against fake Icecast and SHOUTcast servers on this computer.

Nothing leaves the machine: each test starts a tiny server on 127.0.0.1 that
speaks just enough of the protocol, then checks that Studio logs in the way
the real servers expect and that encoded sound arrives. Skipped without FFmpeg.
"""

from __future__ import annotations

import base64
import socket
import threading
import time

import pytest

from quill.core.speech.ffmpeg import find_ffmpeg
from quill.core.streaming import StreamSettings

FFMPEG = find_ffmpeg()
pytestmark = [
    pytest.mark.skipif(FFMPEG is None, reason="FFmpeg is needed"),
    pytest.mark.timeout(120),
]


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class _Server(threading.Thread):
    def __init__(self, port: int, answer):
        super().__init__(daemon=True)
        self.answer = answer
        self.received = b""
        self.listener = socket.socket()
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", port))
        self.listener.listen(1)
        self.listener.settimeout(20)

    def run(self):
        try:
            conn, _ = self.listener.accept()
        except OSError:
            return
        conn.settimeout(5)
        try:
            self.answer(conn, self)
            while len(self.received) < 200_000:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                self.received += chunk
        except OSError:
            pass
        finally:
            conn.close()
            self.listener.close()


def _icecast_answer(conn, server):
    head = b""
    while b"\r\n\r\n" not in head:
        head += conn.recv(4096)
    server.received += head
    conn.sendall(b"HTTP/1.1 200 OK\r\n\r\n")


def _shoutcast_answer(conn, server):
    server.received += conn.recv(256)
    conn.sendall(b"OK2\r\nicy-caps:11\r\n\r\n")


def _run(settings: StreamSettings, server: _Server, seconds: float = 5.0):
    from quill.platform.windows.live_stream import LiveStream

    server.start()
    stream = LiveStream(settings, "s3cret", ffmpeg=FFMPEG, sources=[], on_event=lambda *_a: None)
    stream.start()
    time.sleep(seconds)
    line = stream.status_line()
    stream.stop()
    server.join(10)
    return line


def test_icecast_logs_in_with_basic_auth_and_sends_mp3():
    port = _free_port()
    server = _Server(port, _icecast_answer)
    settings = StreamSettings(
        host="127.0.0.1", port=port, mount="/live", title="Test show", quality="speech"
    )
    line = _run(settings, server)
    head = server.received.split(b"\r\n\r\n", 1)[0].decode("latin-1")
    assert head.startswith("PUT /live")
    token = base64.b64encode(b"source:s3cret").decode()
    assert f"Authorization: Basic {token}" in head
    assert "ice-name: test show" in head.lower()
    assert len(server.received) > len(head) + 1000  # encoded sound arrived
    assert line.startswith("On air")


def test_shoutcast_sends_password_then_headers_then_sound():
    port = _free_port()
    server = _Server(port + 1, _shoutcast_answer)
    settings = StreamSettings(
        kind="shoutcast", host="127.0.0.1", port=port, stream_id=2, title="Test"
    )
    _run(settings, server)
    assert server.received.startswith(b"s3cret:#2\r\n")
    assert b"icy-name:Test" in server.received and b"content-type:audio/mpeg" in server.received
    assert len(server.received) > 2000
