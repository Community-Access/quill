"""Spotify OAuth PKCE sign-in: PKCE, authorize URL, token exchange/refresh."""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

import pytest

from quill.core.spotify import auth


def _expected_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def test_pkce_pair_is_s256_of_the_verifier() -> None:
    verifier, challenge = auth.build_pkce_pair()
    assert 43 <= len(verifier) <= 128
    assert "=" not in challenge  # padding stripped, base64url
    assert challenge == _expected_challenge(verifier)
    # Fresh entropy each call.
    assert auth.build_pkce_pair()[0] != verifier


def test_build_authorization_encodes_pkce_scopes_and_state() -> None:
    request = auth.build_authorization("my-client-id")
    parsed = urlparse(request.url)
    assert parsed.scheme == "https"
    assert parsed.path.endswith("/authorize")
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    assert params["client_id"] == "my-client-id"
    assert params["response_type"] == "code"
    assert params["redirect_uri"] == auth.DEFAULT_REDIRECT_URI
    assert params["code_challenge_method"] == "S256"
    assert params["code_challenge"] == _expected_challenge(request.code_verifier)
    assert params["state"] == request.state
    # Every requested scope made it into the space-delimited scope param.
    granted = set(params["scope"].split())
    assert set(auth.DEFAULT_SCOPES).issubset(granted)


def test_build_authorization_state_is_unique_per_call() -> None:
    assert auth.build_authorization("cid").state != auth.build_authorization("cid").state


def test_build_authorization_rejects_blank_client_id() -> None:
    with pytest.raises(auth.SpotifyAuthError):
        auth.build_authorization("   ")


def test_exchange_code_posts_form_and_parses_tokens() -> None:
    seen: dict[str, object] = {}

    def opener(request: Request) -> tuple[int, bytes]:
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["ctype"] = request.headers.get("Content-type")
        seen["body"] = request.data
        return 200, (
            b'{"access_token":"at","refresh_token":"rt","expires_in":3600,"scope":"streaming"}'
        )

    result = auth.exchange_code("the-code", "the-verifier", "cid", opener=opener)

    assert result.access_token == "at"
    assert result.refresh_token == "rt"
    assert result.expires_in == 3600
    assert result.scope == "streaming"
    assert seen["url"] == auth.TOKEN_URL
    assert seen["method"] == "POST"
    assert seen["ctype"] == "application/x-www-form-urlencoded"
    body = parse_qs(seen["body"].decode())  # type: ignore[union-attr]
    assert body["grant_type"] == ["authorization_code"]
    assert body["code"] == ["the-code"]
    assert body["code_verifier"] == ["the-verifier"]
    assert body["client_id"] == ["cid"]
    assert body["redirect_uri"] == [auth.DEFAULT_REDIRECT_URI]


def test_refresh_backfills_missing_refresh_token() -> None:
    # Spotify may omit refresh_token from a refresh reply; the old one is kept.
    def opener(request: Request) -> tuple[int, bytes]:
        assert b"grant_type=refresh_token" in (request.data or b"")
        return 200, b'{"access_token":"new","expires_in":3600,"scope":"streaming"}'

    result = auth.refresh("keep-me", "cid", opener=opener)
    assert result.access_token == "new"
    assert result.refresh_token == "keep-me"


def test_refresh_keeps_new_refresh_token_when_present() -> None:
    def opener(request: Request) -> tuple[int, bytes]:
        return 200, b'{"access_token":"new","refresh_token":"rotated","expires_in":10}'

    assert auth.refresh("old", "cid", opener=opener).refresh_token == "rotated"


def test_token_error_body_raises_clean_error() -> None:
    def opener(request: Request) -> tuple[int, bytes]:
        return 400, b'{"error":"invalid_grant","error_description":"Bad code"}'

    with pytest.raises(auth.SpotifyAuthError) as excinfo:
        auth.exchange_code("bad", "v", "cid", opener=opener)
    assert "Bad code" in str(excinfo.value)


def test_missing_access_token_is_an_error() -> None:
    def opener(request: Request) -> tuple[int, bytes]:
        return 200, b"{}"

    with pytest.raises(auth.SpotifyAuthError):
        auth.exchange_code("c", "v", "cid", opener=opener)


def test_refuse_in_safe_mode() -> None:
    with pytest.raises(auth.SpotifyAuthError):
        auth.refuse_in_safe_mode(True)
    auth.refuse_in_safe_mode(False)  # no raise
