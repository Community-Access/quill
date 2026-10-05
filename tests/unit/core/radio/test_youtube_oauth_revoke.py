"""Disconnect YouTube Account revokes QUILL's access at Google, then forgets it.

Google's OAuth verification reviewers check that disconnecting really removes
the app's access, not only the local copy of the token. Pinned here, offline:
the exact revoke request, which answers count as revoked, and that the stored
session is wiped whatever Google says -- including when Google says nothing.
"""

from __future__ import annotations

import io
import json
import urllib.error
from urllib.parse import parse_qs

import pytest

from quill.core.auth.token_bundle import TokenBundle
from quill.core.radio import youtube_oauth as oauth


class _Vault:
    """Stands in for the DPAPI secrets vault: one dict, same three calls."""

    def __init__(self) -> None:
        self.values: dict[object, str] = {}

    def get(self, ref: object) -> str | None:
        return self.values.get(ref)

    def set(self, ref: object, value: str) -> None:
        self.values[ref] = value

    def delete(self, ref: object) -> None:
        self.values.pop(ref, None)


@pytest.fixture
def vault(monkeypatch) -> _Vault:
    fake = _Vault()
    monkeypatch.setattr(oauth, "_SECRETS", fake)
    return fake


def _store(access: str = "AT-1", refresh: str = "RT-1") -> None:
    oauth.save_tokens(
        TokenBundle(access_token=access, refresh_token=refresh, expires_at=9e12, scope=oauth.SCOPE)
    )


def _recording(status: int, payload: object = None):
    seen: list[object] = []

    def opener(request):
        seen.append(request)
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        return status, body

    return opener, seen


def test_the_revoke_request_is_a_form_post_of_the_refresh_token(vault) -> None:
    _store()
    opener, seen = _recording(200)
    assert oauth.sign_out(opener=opener) is True
    (request,) = seen
    assert request.full_url == "https://oauth2.googleapis.com/revoke"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/x-www-form-urlencoded"
    assert parse_qs(request.data.decode("utf-8")) == {"token": ["RT-1"]}


def test_the_access_token_is_sent_when_no_refresh_token_is_stored(vault) -> None:
    _store(refresh="")
    opener, seen = _recording(200)
    assert oauth.sign_out(opener=opener) is True
    assert parse_qs(seen[0].data.decode("utf-8")) == {"token": ["AT-1"]}


def test_an_already_revoked_token_counts_as_revoked(vault) -> None:
    _store()
    opener, _seen = _recording(400, {"error": "invalid_token"})
    assert oauth.sign_out(opener=opener) is True
    assert not oauth.is_signed_in()


def test_another_400_is_not_revoked(vault) -> None:
    opener, _seen = _recording(400, {"error": "invalid_request"})
    assert oauth.revoke("RT-1", opener=opener) is False


def test_a_server_error_is_not_revoked_and_still_forgets_the_session(vault) -> None:
    _store()
    opener, _seen = _recording(500)
    assert oauth.sign_out(opener=opener) is False
    assert not oauth.is_signed_in()
    assert vault.values == {}


def test_no_connection_is_not_revoked_and_still_forgets_the_session(vault) -> None:
    _store()

    def offline(_request):
        raise urllib.error.URLError("no route to host")

    assert oauth.sign_out(opener=offline) is False
    assert vault.values == {}


def test_the_real_transport_reads_googles_400_through_httperror(vault, monkeypatch) -> None:
    def urlopen(request, **_kwargs):
        raise urllib.error.HTTPError(
            request.full_url, 400, "Bad Request", {}, io.BytesIO(b'{"error": "invalid_token"}')
        )

    monkeypatch.setattr(oauth.urllib.request, "urlopen", urlopen)
    assert oauth.revoke("RT-1") is True


def test_the_real_transport_treats_a_timeout_as_not_revoked(vault, monkeypatch) -> None:
    def urlopen(_request, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(oauth.urllib.request, "urlopen", urlopen)
    assert oauth.revoke("RT-1") is False


def test_nothing_stored_means_nothing_to_revoke(vault) -> None:
    opener, seen = _recording(500)
    assert oauth.sign_out(opener=opener) is True
    assert seen == []


def test_the_revoke_site_is_a_reviewed_egress_entry() -> None:
    from quill.tools.network_egress_entries_radio import RADIO_EGRESS

    assert "core/radio/youtube_oauth.py::revoke" in RADIO_EGRESS
    assert "core/radio/youtube_oauth.py::_revoke" not in RADIO_EGRESS
