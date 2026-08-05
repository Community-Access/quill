"""Unit tests for ``quill.core.auth.flows`` (sign-in flow logic, no sockets)."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from quill.core.auth import (
    AuthError,
    AuthRedirect,
    FlowStateMismatchError,
    FlowTimeoutError,
    OAuthProvider,
    PkcePair,
    build_authorization_url,
    exchange_code,
    run_authorization_code_flow,
    run_device_code_flow,
)


def _provider(**kw: Any) -> OAuthProvider:
    base: dict[str, Any] = {
        "name": "bard",
        "authorize_url": "https://auth.test/authorize",
        "token_url": "https://auth.test/token",
        "client_id": "quill-desktop",
        "redirect_uri": "http://127.0.0.1:8765/callback",
        "scopes": ("search", "download"),
    }
    base.update(kw)
    return OAuthProvider(**base)


# -- build_authorization_url -------------------------------------------------


def test_build_authorization_url_params() -> None:
    url = build_authorization_url(_provider(), challenge="CHAL", state="STATE")
    query = parse_qs(urlparse(url).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["quill-desktop"]
    assert query["code_challenge"] == ["CHAL"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == ["STATE"]
    assert query["scope"] == ["search download"]


def test_build_authorization_url_respects_existing_query() -> None:
    url = build_authorization_url(
        _provider(authorize_url="https://auth.test/authorize?foo=1"),
        challenge="C",
        state="S",
    )
    assert "?foo=1&" in url


# -- exchange_code -----------------------------------------------------------


def test_exchange_code_success() -> None:
    def poster(url: str, fields: dict[str, str]) -> dict[str, Any]:
        assert fields["grant_type"] == "authorization_code"
        assert fields["code_verifier"] == "verifier"
        return {"access_token": "a", "refresh_token": "r", "expires_in": 3600}

    bundle = exchange_code(_provider(), poster, code="c", code_verifier="verifier", now=1_000.0)
    assert bundle.access_token == "a"
    assert bundle.expires_at == 4_600.0


def test_exchange_code_error_raises() -> None:
    def poster(url: str, fields: dict[str, str]) -> dict[str, Any]:
        return {"error": "invalid_grant"}

    with pytest.raises(AuthError):
        exchange_code(_provider(), poster, code="c", code_verifier="v", now=1_000.0)


def test_exchange_code_uses_broker_when_set() -> None:
    seen: list[str] = []

    def poster(url: str, fields: dict[str, str]) -> dict[str, Any]:
        seen.append(url)
        return {"access_token": "a", "expires_in": 60}

    exchange_code(
        _provider(broker_url="https://broker.quill.test/bard/token"),
        poster,
        code="c",
        code_verifier="v",
        now=1_000.0,
    )
    assert seen == ["https://broker.quill.test/bard/token"]


# -- run_authorization_code_flow --------------------------------------------


def _pkce() -> PkcePair:
    return PkcePair(verifier="verifier", challenge="challenge")


def test_authorization_code_flow_success() -> None:
    opened: list[str] = []

    def opener(url: str) -> None:
        opened.append(url)

    def waiter(auth_url: str, redirect_uri: str, timeout: float) -> AuthRedirect:
        state = parse_qs(urlparse(auth_url).query)["state"][0]
        return AuthRedirect(code="the-code", state=state)

    def poster(url: str, fields: dict[str, str]) -> dict[str, Any]:
        assert fields["code"] == "the-code"
        return {"access_token": "a", "refresh_token": "r", "expires_in": 3600}

    bundle = run_authorization_code_flow(
        _provider(), poster, waiter=waiter, opener=opener, now=lambda: 1_000.0, pkce=_pkce()
    )
    assert bundle.access_token == "a"
    assert len(opened) == 1


def test_authorization_code_flow_state_mismatch() -> None:
    def waiter(auth_url: str, redirect_uri: str, timeout: float) -> AuthRedirect:
        return AuthRedirect(code="c", state="WRONG")

    with pytest.raises(FlowStateMismatchError):
        run_authorization_code_flow(
            _provider(),
            lambda url, f: {},
            waiter=waiter,
            opener=lambda url: None,
            state="EXPECTED",
            pkce=_pkce(),
        )


def test_authorization_code_flow_error_redirect() -> None:
    def waiter(auth_url: str, redirect_uri: str, timeout: float) -> AuthRedirect:
        return AuthRedirect(error="access_denied")

    with pytest.raises(AuthError):
        run_authorization_code_flow(
            _provider(), lambda url, f: {}, waiter=waiter, opener=lambda url: None, pkce=_pkce()
        )


def test_authorization_code_flow_no_code_times_out() -> None:
    def waiter(auth_url: str, redirect_uri: str, timeout: float) -> AuthRedirect:
        return AuthRedirect()

    with pytest.raises(FlowTimeoutError):
        run_authorization_code_flow(
            _provider(), lambda url, f: {}, waiter=waiter, opener=lambda url: None, pkce=_pkce()
        )


# -- run_device_code_flow ----------------------------------------------------


def _device_provider() -> OAuthProvider:
    return _provider(device_code_url="https://auth.test/device")


class DeviceScript:
    """A poster that returns the device authorization, then a scripted poll sequence."""

    def __init__(self, poll_sequence: list[dict[str, Any]]) -> None:
        self._polls = list(poll_sequence)
        self.calls: list[dict[str, str]] = []

    def __call__(self, url: str, fields: dict[str, str]) -> dict[str, Any]:
        self.calls.append(dict(fields))
        if url.endswith("/device"):
            return {
                "device_code": "dev",
                "user_code": "WXYZ-1234",
                "verification_uri": "https://auth.test/activate",
                "interval": 1,
            }
        return self._polls.pop(0)


def test_device_flow_success_after_pending() -> None:
    poster = DeviceScript([
        {"error": "authorization_pending"},
        {"access_token": "a", "refresh_token": "r", "expires_in": 3600},
    ])
    slept: list[float] = []
    shown: list[tuple[str, str]] = []

    bundle = run_device_code_flow(
        _device_provider(),
        poster,
        lambda code, uri: shown.append((code, uri)),
        now=lambda: 1_000.0,
        sleep=slept.append,
        max_seconds=900.0,
    )
    assert bundle.access_token == "a"
    assert shown == [("WXYZ-1234", "https://auth.test/activate")]
    assert len(slept) == 2  # one wait per poll


def test_device_flow_slow_down_increases_interval() -> None:
    poster = DeviceScript([
        {"error": "slow_down"},
        {"access_token": "a", "expires_in": 60},
    ])
    slept: list[float] = []
    run_device_code_flow(
        _device_provider(),
        poster,
        lambda code, uri: None,
        now=lambda: 1_000.0,
        sleep=slept.append,
    )
    assert slept == [1.0, 6.0]  # interval bumped by 5 after slow_down


def test_device_flow_expired_token_times_out() -> None:
    poster = DeviceScript([{"error": "expired_token"}])
    with pytest.raises(FlowTimeoutError):
        run_device_code_flow(
            _device_provider(),
            poster,
            lambda code, uri: None,
            now=lambda: 1_000.0,
            sleep=lambda s: None,
        )


def test_device_flow_deadline_times_out() -> None:
    # now() advances past the deadline immediately, so the poll loop never runs.
    times = iter([1_000.0, 2_000.0, 2_000.0, 2_000.0])
    poster = DeviceScript([{"error": "authorization_pending"}])
    with pytest.raises(FlowTimeoutError):
        run_device_code_flow(
            _device_provider(),
            poster,
            lambda code, uri: None,
            now=lambda: next(times),
            sleep=lambda s: None,
            max_seconds=100.0,
        )
