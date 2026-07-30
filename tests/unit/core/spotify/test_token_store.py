"""TokenBundle serialization and construction from a token response."""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.spotify.token_store import TokenBundle


def test_round_trip_json() -> None:
    bundle = TokenBundle(
        access_token="at", refresh_token="rt", expires_at=1234.5, scope="streaming"
    )
    restored = TokenBundle.from_json(bundle.to_json())
    assert restored == bundle


def test_from_json_empty_and_malformed() -> None:
    assert TokenBundle.from_json("").is_empty
    assert TokenBundle.from_json("not json").is_empty
    assert TokenBundle.from_json("[1,2,3]").is_empty  # not an object
    # A bad expires_at falls back to 0.0 rather than raising.
    assert TokenBundle.from_json('{"access_token":"a","expires_at":"soon"}').expires_at == 0.0


def test_is_empty() -> None:
    assert TokenBundle().is_empty
    assert not TokenBundle(access_token="a").is_empty
    assert not TokenBundle(refresh_token="r").is_empty


def test_from_token_response_computes_absolute_expiry() -> None:
    @dataclass
    class FakeResponse:
        access_token: str = "at"
        refresh_token: str = "rt"
        expires_in: int = 3600
        scope: str = "streaming"

    bundle = TokenBundle.from_token_response(FakeResponse(), now=1000.0)
    assert bundle.access_token == "at"
    assert bundle.refresh_token == "rt"
    assert bundle.expires_at == 4600.0  # now + expires_in
    assert bundle.scope == "streaming"
