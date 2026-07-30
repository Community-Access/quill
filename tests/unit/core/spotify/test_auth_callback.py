"""The loopback OAuth redirect receiver, driven with a real local socket."""

from __future__ import annotations

import socket
import threading

import pytest

from quill.core.spotify.auth_callback import CallbackServer, SpotifyCallbackError


def _send_redirect(port: int, query: str) -> None:
    request = f"GET /callback?{query} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall(request.encode())
        try:
            sock.recv(1024)  # let the server finish writing its reply
        except OSError:
            pass


def _run_wait(server: CallbackServer, out: dict[str, object], timeout: float = 5.0) -> None:
    try:
        out["code"] = server.wait(timeout=timeout)
    except Exception as error:  # noqa: BLE001 - captured for the assertion
        out["error"] = error


def test_returns_code_on_matching_state() -> None:
    server = CallbackServer("STATE123", port=0)
    out: dict[str, object] = {}
    thread = threading.Thread(target=_run_wait, args=(server, out))
    thread.start()
    _send_redirect(server.port, "code=auth-code-xyz&state=STATE123")
    thread.join(5)
    assert out.get("code") == "auth-code-xyz"


def test_state_mismatch_is_rejected() -> None:
    server = CallbackServer("EXPECTED", port=0)
    out: dict[str, object] = {}
    thread = threading.Thread(target=_run_wait, args=(server, out))
    thread.start()
    _send_redirect(server.port, "code=abc&state=WRONG")
    thread.join(5)
    assert isinstance(out.get("error"), SpotifyCallbackError)


def test_missing_code_is_rejected() -> None:
    server = CallbackServer("STATE", port=0)
    out: dict[str, object] = {}
    thread = threading.Thread(target=_run_wait, args=(server, out))
    thread.start()
    _send_redirect(server.port, "state=STATE")
    thread.join(5)
    assert isinstance(out.get("error"), SpotifyCallbackError)


def test_error_param_is_reported() -> None:
    server = CallbackServer("STATE", port=0)
    out: dict[str, object] = {}
    thread = threading.Thread(target=_run_wait, args=(server, out))
    thread.start()
    _send_redirect(server.port, "state=STATE&error=access_denied")
    thread.join(5)
    assert isinstance(out.get("error"), SpotifyCallbackError)
    assert "access_denied" in str(out["error"])


def test_timeout_raises() -> None:
    server = CallbackServer("STATE", port=0)
    with pytest.raises(SpotifyCallbackError):
        server.wait(timeout=0.3)  # nothing ever arrives
