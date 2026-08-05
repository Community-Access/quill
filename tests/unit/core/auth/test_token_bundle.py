"""Unit tests for ``quill.core.auth.token_bundle.TokenBundle``."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from quill.core.auth import TokenBundle


def test_empty_bundle() -> None:
    b = TokenBundle()
    assert b.is_empty
    assert b.token_type == "Bearer"


def test_non_empty_when_any_token_present() -> None:
    assert not TokenBundle(access_token="a").is_empty
    assert not TokenBundle(refresh_token="r").is_empty


def test_is_expired_at_skew_boundary() -> None:
    now = 1_000.0
    # expires exactly at now+skew -> considered expired (<=)
    assert TokenBundle(access_token="a", expires_at=1_060.0).is_expired(now, skew=60.0)
    # expires one second later -> still valid
    assert not TokenBundle(access_token="a", expires_at=1_061.0).is_expired(now, skew=60.0)


def test_unknown_expiry_is_expired() -> None:
    assert TokenBundle(access_token="a", expires_at=0.0).is_expired(1_000.0)


def test_needs_refresh_requires_refresh_token() -> None:
    now = 1_000.0
    expired = TokenBundle(access_token="a", expires_at=0.0)
    assert not expired.needs_refresh(now)  # no refresh token
    with_refresh = TokenBundle(access_token="a", refresh_token="r", expires_at=0.0)
    assert with_refresh.needs_refresh(now)


def test_needs_refresh_false_when_fresh() -> None:
    now = 1_000.0
    fresh = TokenBundle(access_token="a", refresh_token="r", expires_at=9_999.0)
    assert not fresh.needs_refresh(now)


@dataclass
class _Resp:
    access_token: str = ""
    refresh_token: str = ""
    expires_in: int = 0
    scope: str = ""
    token_type: str = ""


def test_from_token_response_converts_relative_expiry() -> None:
    b = TokenBundle.from_token_response(
        _Resp(access_token="a", refresh_token="r", expires_in=3600, scope="read"),
        now=1_000.0,
    )
    assert b.access_token == "a"
    assert b.refresh_token == "r"
    assert b.expires_at == 4_600.0
    assert b.scope == "read"
    assert b.token_type == "Bearer"  # default when server omits it


def test_from_token_response_unknown_expiry_is_zero() -> None:
    b = TokenBundle.from_token_response(_Resp(access_token="a", expires_in=0), now=1_000.0)
    assert b.expires_at == 0.0


@pytest.mark.smoke
def test_json_roundtrip() -> None:
    b = TokenBundle("a", "r", 4_600.0, "read write", "Bearer")
    assert TokenBundle.from_json(b.to_json()) == b


def test_from_json_malformed_is_empty() -> None:
    assert TokenBundle.from_json("not json{{{").is_empty
    assert TokenBundle.from_json("").is_empty


def test_from_json_non_object_is_empty() -> None:
    assert TokenBundle.from_json("[1, 2, 3]").is_empty


def test_from_json_bad_expires_at_coerces_to_zero() -> None:
    b = TokenBundle.from_json('{"access_token": "a", "expires_at": "oops"}')
    assert b.access_token == "a"
    assert b.expires_at == 0.0
