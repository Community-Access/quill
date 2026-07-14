from __future__ import annotations

import pytest

from quill.core.mastodon import client


def test_normalize_instance_url_accepts_bare_host_and_strips_slash() -> None:
    assert client.normalize_instance_url("mastodon.social") == "https://mastodon.social"
    assert client.normalize_instance_url("https://mastodon.social/") == "https://mastodon.social"


def test_normalize_instance_url_rejects_http_and_junk() -> None:
    with pytest.raises(client.MastodonError):
        client.normalize_instance_url("http://mastodon.social")
    with pytest.raises(client.MastodonError):
        client.normalize_instance_url("")
    with pytest.raises(client.MastodonError):
        client.normalize_instance_url("notahost")


def test_authorize_url_targets_oauth_with_read_and_write_scopes() -> None:
    url = client.authorize_url("mastodon.social", "cid")
    assert url.startswith("https://mastodon.social/oauth/authorize?")
    assert "client_id=cid" in url
    # read:accounts (for verify_credentials) + write:statuses (to post).
    assert "scope=read%3Aaccounts+write%3Astatuses" in url
    assert "redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob" in url


def _stub_http(monkeypatch: pytest.MonkeyPatch, response: dict[str, object]) -> list[dict]:
    calls: list[dict] = []

    def _fake(method, url, *, data=None, token=None):
        calls.append({"method": method, "url": url, "data": data, "token": token})
        return response

    monkeypatch.setattr(client, "_http_json", _fake)
    return calls


def test_register_app_posts_quill_client_name(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_http(monkeypatch, {"client_id": "id", "client_secret": "secret"})
    creds = client.register_app("mastodon.social")
    assert (creds.client_id, creds.client_secret) == ("id", "secret")
    assert calls[0]["url"] == "https://mastodon.social/api/v1/apps"
    assert calls[0]["data"]["client_name"] == "QUILL"
    assert calls[0]["data"]["scopes"] == "read:accounts write:statuses"


def test_register_app_raises_when_credentials_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_http(monkeypatch, {})
    with pytest.raises(client.MastodonError):
        client.register_app("mastodon.social")


def test_exchange_code_returns_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_http(monkeypatch, {"access_token": "tok"})
    creds = client.AppCredentials("id", "secret")
    assert client.exchange_code("mastodon.social", creds, " code ") == "tok"
    assert calls[0]["url"] == "https://mastodon.social/oauth/token"
    assert calls[0]["data"]["code"] == "code"  # trimmed
    assert calls[0]["data"]["grant_type"] == "authorization_code"


def test_verify_credentials_builds_full_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_http(monkeypatch, {"username": "alice"})
    assert client.verify_credentials("mastodon.social", "tok") == "@alice@mastodon.social"
    assert calls[0]["token"] == "tok"


def test_post_status_sends_text_and_visibility_with_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_http(monkeypatch, {"url": "https://mastodon.social/@alice/123"})
    url = client.post_status("mastodon.social", "tok", "hello world", "unlisted")
    assert url == "https://mastodon.social/@alice/123"
    assert calls[0]["url"] == "https://mastodon.social/api/v1/statuses"
    assert calls[0]["data"] == {"status": "hello world", "visibility": "unlisted"}
    assert calls[0]["token"] == "tok"


def test_post_status_rejects_empty_text_and_bad_visibility(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_http(monkeypatch, {"url": "x"})
    with pytest.raises(client.MastodonError):
        client.post_status("mastodon.social", "tok", "   ", "public")
    with pytest.raises(client.MastodonError):
        client.post_status("mastodon.social", "tok", "hi", "bogus")
