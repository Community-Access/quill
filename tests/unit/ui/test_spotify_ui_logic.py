"""Offline tests for the Spotify UI logic cores: the token session, the
sign-in orchestrator, and the browse-results builder. No wx, no WebView, no
network, and no Spotify account are touched -- every dependency is faked."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.spotify import auth, consent, token_store
from quill.core.spotify.session import SpotifySession
from quill.core.spotify.token_store import TokenBundle
from quill.ui.spotify.browse_dialog import BrowseItem, build_browse_items
from quill.ui.spotify.connect_dialog import perform_sign_in

# --- SpotifySession -----------------------------------------------------------


def test_session_returns_stored_token_while_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = TokenBundle(access_token="fresh", refresh_token="r", expires_at=1000.0, scope="s")
    monkeypatch.setattr(token_store, "load_tokens", lambda: bundle)
    refreshed: list[bool] = []
    monkeypatch.setattr(auth, "refresh", lambda *a, **k: refreshed.append(True))
    session = SpotifySession(clock=lambda: 500.0)  # 500s left, well within margin
    assert session.access_token() == "fresh"
    assert refreshed == [], "a still-fresh token must not be refreshed"


def test_session_refreshes_and_persists_when_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = TokenBundle(access_token="old", refresh_token="r0", expires_at=100.0, scope="s")
    saved: list[TokenBundle] = []
    monkeypatch.setattr(token_store, "load_tokens", lambda: bundle)
    monkeypatch.setattr(token_store, "load_client_id", lambda: "client-123")
    monkeypatch.setattr(token_store, "save_tokens", lambda b: saved.append(b))
    monkeypatch.setattr(
        auth,
        "refresh",
        lambda refresh_token, client_id, *, opener=None: SimpleNamespace(
            access_token="new", refresh_token="r0", expires_in=3600, scope="s"
        ),
    )
    session = SpotifySession(clock=lambda: 200.0)  # past expiry (100)
    assert session.access_token() == "new"
    assert saved and saved[-1].access_token == "new"


def test_session_empty_when_not_signed_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_store, "load_tokens", lambda: TokenBundle())
    assert SpotifySession().access_token() == ""


# --- perform_sign_in ----------------------------------------------------------


class _FakeServer:
    def __init__(self, state: str) -> None:
        self.state = state

    def wait(self, _timeout: float, *, on_ready=None) -> str:
        if on_ready is not None:
            on_ready()  # the real server fires this to open the browser
        return "auth-code-xyz"


def test_perform_sign_in_exchanges_and_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    saved_tokens: list[TokenBundle] = []
    saved_client: list[str] = []
    monkeypatch.setattr(consent, "save_spotify_consent_complete", lambda: None)
    monkeypatch.setattr(
        auth,
        "exchange_code",
        lambda code, verifier, client_id, *a, **k: SimpleNamespace(
            access_token="A", refresh_token="R", expires_in=3600, scope="user-read"
        ),
    )
    monkeypatch.setattr(token_store, "save_tokens", lambda b: saved_tokens.append(b))
    monkeypatch.setattr(token_store, "save_client_id", lambda c: saved_client.append(c))

    result = perform_sign_in(
        "my-client-id",
        open_browser=opened.append,
        server_factory=_FakeServer,
        clock=lambda: 1000.0,
    )
    assert result  # truthy scope
    assert opened and opened[0].startswith("https://accounts.spotify.com/authorize")
    assert saved_tokens and saved_tokens[-1].access_token == "A"
    assert saved_client == ["my-client-id"]


def test_perform_sign_in_requires_client_id() -> None:
    with pytest.raises(auth.SpotifyAuthError):
        perform_sign_in("   ", server_factory=_FakeServer)


def test_perform_sign_in_refuses_in_safe_mode() -> None:
    with pytest.raises(auth.SpotifyAuthError):
        perform_sign_in("cid", safe_mode=True, server_factory=_FakeServer)


# --- build_browse_items -------------------------------------------------------


def _track(uri: str, name: str, artist: str):
    return SimpleNamespace(uri=uri, name=name, artist=artist)


def _episode(uri: str, name: str, show: str):
    return SimpleNamespace(uri=uri, name=name, show_name=show)


class _FakeClient:
    def __init__(self, results) -> None:
        self._results = results

    def search(self, _query: str, *, types=()):
        return self._results


def test_browse_radio_builds_track_items() -> None:
    results = SimpleNamespace(
        tracks=[_track("spotify:track:1", "Song", "Band")], shows=[], episodes=[]
    )
    items = build_browse_items(_FakeClient(results), "song", kind="radio")
    assert items == [BrowseItem("Song - Band", "spotify:track:1")]


def test_browse_cast_builds_episode_items() -> None:
    results = SimpleNamespace(
        tracks=[], shows=[], episodes=[_episode("spotify:episode:9", "Ep 1", "My Show")]
    )
    items = build_browse_items(_FakeClient(results), "show", kind="cast")
    assert items[0] == BrowseItem("Ep 1 - My Show", "spotify:episode:9")


def test_browse_skips_items_with_no_uri() -> None:
    results = SimpleNamespace(tracks=[_track("", "No URI", "X")], shows=[], episodes=[])
    assert build_browse_items(_FakeClient(results), "x", kind="radio") == []
