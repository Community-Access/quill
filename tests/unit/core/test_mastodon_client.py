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


def test_post_status_omits_language_when_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # #922: language=None (the compose dialog's "Default (instance)") must NOT
    # add a language field, so the instance keeps its own default preset.
    calls = _stub_http(monkeypatch, {"url": "x"})
    client.post_status("mastodon.social", "tok", "hi", "public", language=None)
    assert "language" not in calls[0]["data"]


def test_post_status_sends_language_when_given(monkeypatch: pytest.MonkeyPatch) -> None:
    # #922: an explicit ISO 639-1 code is sent as the post's language so a post
    # written in Italian is filed under the Italian preset, not the account default.
    calls = _stub_http(monkeypatch, {"url": "x"})
    client.post_status("mastodon.social", "tok", "ciao", "public", language="it")
    assert calls[0]["data"]["language"] == "it"


def test_instance_character_limit_reads_v2_instance_max(monkeypatch: pytest.MonkeyPatch) -> None:
    # #922: poliversity.it allows 9999; the compose counter must reflect that.
    client.clear_character_limit_cache()
    _stub_http(
        monkeypatch,
        {"configuration": {"statuses": {"max_characters": 9999}}},
    )
    assert client.instance_character_limit("poliversity.it") == 9999


def test_instance_character_limit_falls_back_on_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # #922: a failed lookup must never block posting -- fall back to the default.
    client.clear_character_limit_cache()

    def _fail(*_a, **_k):
        raise client.MastodonError("unreachable")

    monkeypatch.setattr(client, "_http_json", _fail)
    assert client.instance_character_limit("broken.example") == client.DEFAULT_CHARACTER_LIMIT


def test_instance_character_limit_caches_per_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    # #922: the second lookup for the same instance must reuse the cached value
    # and NOT hit the network again (the counter refreshes on every keystroke
    # indirectly via account switches; the fetch itself is one-time).
    client.clear_character_limit_cache()
    calls = _stub_http(
        monkeypatch,
        {"configuration": {"statuses": {"max_characters": 9999}}},
    )
    client.instance_character_limit("poliversity.it")
    client.instance_character_limit("poliversity.it")
    client.instance_character_limit("poliversity.it")
    # One normalized base URL -> one network call across three lookups.
    assert len(calls) == 1


def test_instance_character_limit_falls_back_on_missing_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #922: an instance response without the configuration.statuses object must
    # fall back to the default rather than raise or return a nonsense limit.
    client.clear_character_limit_cache()
    _stub_http(monkeypatch, {"domain": "weird.example"})
    assert client.instance_character_limit("weird.example") == client.DEFAULT_CHARACTER_LIMIT
