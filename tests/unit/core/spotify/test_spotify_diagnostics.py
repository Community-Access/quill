"""Spotify diagnostics: the sign-in trace, plain failures, and the setup report."""

from __future__ import annotations

import socket

import pytest

from quill.core.spotify import token_store
from quill.core.spotify.auth import DEFAULT_REDIRECT_URI
from quill.core.spotify.auth_callback import SpotifyCallbackError
from quill.core.spotify.diagnostics import (
    REDIRECT_PORT,
    SignInTrace,
    diagnostic_report,
    plain_failure,
    port_is_free,
)
from quill.core.spotify.token_store import TokenBundle
from quill.ui.spotify.connect_dialog import perform_sign_in


@pytest.fixture(autouse=True)
def vault(monkeypatch):
    """An in-memory credential vault. The real one is Windows Credential
    Manager, which no test may ever write to: a first draft of this file did,
    and left a fake Client ID and fake tokens in a real profile."""
    store: dict[str, str] = {}
    monkeypatch.setattr(token_store, "load_secret", lambda name: store.get(name, ""))
    monkeypatch.setattr(
        token_store, "save_secret", lambda name, value: store.__setitem__(name, value)
    )
    monkeypatch.setattr(
        token_store, "delete_secret", lambda name: store.pop(name, None) is not None
    )
    return store


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    return tmp_path


def test_a_trace_survives_on_disk_and_reads_in_order(tmp_path) -> None:
    ticks = iter(range(1_800_000_000, 1_800_000_100))
    trace = SignInTrace(path=tmp_path / "t.json", clock=lambda: next(ticks))
    trace.step("one")
    trace.step("two")
    trace.finish("Connected.")
    again = SignInTrace.load_last(tmp_path / "t.json")
    lines = again.lines()
    assert lines[1].endswith(": one") and lines[2].endswith(": two")
    assert lines[-1] == "Result: Connected."
    assert SignInTrace.load_last(tmp_path / "missing.json").lines() == [
        "No sign-in has been attempted on this computer yet."
    ]


def test_a_timeout_says_to_check_the_redirect_and_user_management() -> None:
    message = plain_failure(
        SpotifyCallbackError("Timed out waiting for the Spotify sign-in to complete.")
    )
    assert DEFAULT_REDIRECT_URI in message
    assert "User Management" in message


def test_a_port_in_use_is_named() -> None:
    error = OSError(10048, "address in use")
    error.winerror = 10048  # type: ignore[attr-defined]
    assert str(REDIRECT_PORT) in plain_failure(error)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("invalid_client: Invalid client", "Client ID"),
        ("INVALID_CLIENT: Invalid redirect URI", "Client ID"),
        ("access_denied", "cancelled"),
        ("Could not reach Spotify to sign in: timed out", "online"),
    ],
)
def test_other_failures_are_plain(raw, expected) -> None:
    assert expected in plain_failure(Exception(raw))


def test_sign_in_records_how_far_it_got_and_never_a_secret(data) -> None:
    class _Server:
        def __init__(self, _state):
            pass

        def wait(self, _timeout, on_ready):
            on_ready()
            raise SpotifyCallbackError("Timed out waiting for the Spotify sign-in to complete.")

    trace = SignInTrace(path=data / "trace.json")
    with pytest.raises(SpotifyCallbackError):
        perform_sign_in(
            "abcdefgh1234",
            open_browser=lambda _url: True,
            server_factory=_Server,
            trace=trace,
        )
    text = "\n".join(SignInTrace.load_last(data / "trace.json").lines())
    assert "ending in 1234" in text and "abcdefgh" not in text
    assert "Browser opened" in text
    assert "never came back" in text
    assert "code_verifier" not in text and "code=" not in text


def test_the_report_without_a_sign_in(data) -> None:
    report = diagnostic_report(trace_path=data / "none.json")
    assert DEFAULT_REDIRECT_URI in report
    assert "Client ID saved: no" in report
    assert "Signed in: no" in report
    assert "User Management" in report


def test_the_report_with_a_sign_in_names_missing_permissions_and_the_account(data) -> None:
    token_store.save_client_id("clientid9876")
    token_store.save_tokens(
        TokenBundle(
            access_token="a",
            refresh_token="r",
            expires_at=10**12,
            scope="streaming user-read-email",
        )
    )
    report = diagnostic_report(
        account_lookup=lambda: {"product": "free"},
        playback_available=lambda: False,
        trace_path=data / "none.json",
    )
    assert "ending in 9876" in report and "clientid" not in report
    assert "Permissions missing:" in report and "playlist-read-private" in report
    assert "Account type: free. Spotify Premium is needed" in report
    assert "WebView2 runtime" in report
    assert "access_token" not in report


def test_port_check_sees_a_held_port() -> None:
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    port = holder.getsockname()[1]
    try:
        assert port_is_free(port) is False
    finally:
        holder.close()
