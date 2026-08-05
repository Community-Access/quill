"""Unit tests for ``quill.core.auth.token_manager.TokenManager``.

Uses an in-memory secrets backend, an injected fake poster, and an injected
clock so every refresh branch is deterministic and no network or OS vault is
touched.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest

from quill.core.auth import (
    REFRESH_FAILED,
    SIGNED_OUT,
    OAuthProvider,
    ProviderRegistry,
    ProviderUnknownError,
    TokenBundle,
    TokenManager,
    TokenUnavailableError,
)
from quill.core.secrets import SecretRef, SecretsManager


class FakeBackend:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def load(self, cred_name: str) -> str:
        return self.store.get(cred_name, "")

    def save(self, cred_name: str, value: str) -> None:
        if value:
            self.store[cred_name] = value
        else:
            self.store.pop(cred_name, None)

    def delete(self, cred_name: str) -> bool:
        return self.store.pop(cred_name, None) is not None


class Poster:
    def __init__(self, handler: Callable[[str, dict[str, str]], dict[str, Any]]) -> None:
        self._handler = handler
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, fields: dict[str, str]) -> dict[str, Any]:
        self.calls.append((url, dict(fields)))
        return self._handler(url, dict(fields))


def _provider() -> OAuthProvider:
    return OAuthProvider(
        name="bard",
        authorize_url="https://auth.test/authorize",
        token_url="https://auth.test/token",
        revoke_url="https://auth.test/revoke",
        client_id="quill-desktop",
        redirect_uri="http://127.0.0.1:0/callback",
        scopes=("search",),
    )


def _make(handler: Callable[[str, dict[str, str]], dict[str, Any]], *, t: float = 1_000.0):
    secrets = SecretsManager(backend=FakeBackend())
    registry = ProviderRegistry()
    registry.register(_provider())
    manager = TokenManager(secrets, registry, Poster(handler), now=lambda: t)
    return manager, secrets


def _store(secrets: SecretsManager, bundle: TokenBundle) -> None:
    secrets.set(SecretRef("bard", "tokens"), bundle.to_json())


def test_none_when_not_signed_in() -> None:
    manager, _ = _make(lambda url, f: {})
    assert manager.get_access_token("bard") is None
    assert manager.is_signed_in("bard") is False


def test_unknown_provider_raises() -> None:
    manager, _ = _make(lambda url, f: {})
    with pytest.raises(ProviderUnknownError):
        manager.get_access_token("nope")


def test_returns_token_when_fresh() -> None:
    manager, secrets = _make(lambda url, f: pytest.fail("should not refresh"))
    _store(secrets, TokenBundle(access_token="good", refresh_token="r", expires_at=9_999.0))
    assert manager.get_access_token("bard") == "good"


def test_refreshes_when_expired_and_merges_refresh_token() -> None:
    manager, secrets = _make(lambda url, f: {"access_token": "new", "expires_in": 3600})
    _store(secrets, TokenBundle(access_token="old", refresh_token="r", expires_at=0.0))

    assert manager.get_access_token("bard") == "new"

    stored = manager.bundle("bard")
    assert stored is not None
    assert stored.access_token == "new"
    assert stored.refresh_token == "r"  # response omitted it -> kept
    assert stored.expires_at == 4_600.0


def test_refresh_sends_expected_fields() -> None:
    poster_calls: list[dict[str, str]] = []

    def handler(url: str, fields: dict[str, str]) -> dict[str, Any]:
        poster_calls.append(fields)
        return {"access_token": "new", "expires_in": 60}

    manager, secrets = _make(handler)
    _store(secrets, TokenBundle(access_token="old", refresh_token="r", expires_at=0.0))
    manager.get_access_token("bard")

    assert poster_calls[0]["grant_type"] == "refresh_token"
    assert poster_calls[0]["refresh_token"] == "r"
    assert poster_calls[0]["client_id"] == "quill-desktop"


def test_invalid_grant_wipes_and_returns_none() -> None:
    events = []
    manager, secrets = _make(lambda url, f: {"error": "invalid_grant"})
    manager.subscribe(events.append)
    _store(secrets, TokenBundle(access_token="old", refresh_token="r", expires_at=0.0))

    assert manager.get_access_token("bard") is None
    assert manager.is_signed_in("bard") is False
    assert [e.kind for e in events] == [REFRESH_FAILED]


def test_network_failure_when_expired_raises() -> None:
    def boom(url: str, fields: dict[str, str]) -> dict[str, Any]:
        raise OSError("dns down")

    manager, secrets = _make(boom)
    _store(secrets, TokenBundle(access_token="old", refresh_token="r", expires_at=0.0))
    with pytest.raises(TokenUnavailableError):
        manager.get_access_token("bard")


def test_network_failure_but_still_valid_returns_current() -> None:
    def boom(url: str, fields: dict[str, str]) -> dict[str, Any]:
        raise OSError("blip")

    # expires within the 60s refresh skew (needs_refresh) but not yet truly expired
    manager, secrets = _make(boom, t=1_000.0)
    _store(secrets, TokenBundle(access_token="old", refresh_token="r", expires_at=1_030.0))
    assert manager.get_access_token("bard") == "old"


def test_single_flight_refreshes_once() -> None:
    barrier = threading.Barrier(5)
    call_count = 0
    lock = threading.Lock()

    def handler(url: str, fields: dict[str, str]) -> dict[str, Any]:
        nonlocal call_count
        with lock:
            call_count += 1
        return {"access_token": "fresh", "expires_in": 3600}

    manager, secrets = _make(handler)
    _store(secrets, TokenBundle(access_token="old", refresh_token="r", expires_at=0.0))

    results: list[str | None] = []
    results_lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        token = manager.get_access_token("bard")
        with results_lock:
            results.append(token)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert call_count == 1
    assert results == ["fresh"] * 5


def test_sign_out_revokes_wipes_and_emits() -> None:
    revoke_calls: list[str] = []

    def handler(url: str, fields: dict[str, str]) -> dict[str, Any]:
        revoke_calls.append(url)
        return {}

    events = []
    manager, secrets = _make(handler)
    manager.subscribe(events.append)
    _store(secrets, TokenBundle(access_token="a", refresh_token="r", expires_at=9_999.0))

    manager.sign_out("bard")

    assert revoke_calls == ["https://auth.test/revoke"]
    assert manager.is_signed_in("bard") is False
    assert [e.kind for e in events] == [SIGNED_OUT]


def test_unsubscribe_stops_events() -> None:
    events = []
    manager, secrets = _make(lambda url, f: {})
    unsubscribe = manager.subscribe(events.append)
    unsubscribe()
    _store(secrets, TokenBundle(access_token="a", refresh_token="r", expires_at=9_999.0))
    manager.sign_out("bard")
    assert events == []
