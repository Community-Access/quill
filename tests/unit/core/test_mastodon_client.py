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


def _stub_http_by_url(monkeypatch: pytest.MonkeyPatch, by_suffix: dict[str, object]) -> list[str]:
    """Route _http_json responses by URL suffix; record the URLs hit, in order."""
    calls: list[str] = []

    def _fake(method, url, *, data=None, token=None):
        calls.append(url)
        for suffix, response in by_suffix.items():
            if url.endswith(suffix):
                if isinstance(response, Exception):
                    raise response
                return response
        raise client.MastodonError(f"no stub for {url}")

    monkeypatch.setattr(client, "_http_json", _fake)
    return calls


def test_instance_character_limit_falls_back_to_v1_max_toot_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A non-Mastodon fork (GoToSocial/Pleroma) that does NOT implement v2 must
    # still get its real limit via /api/v1/instance -> max_toot_chars.
    client.clear_character_limit_cache()
    calls = _stub_http_by_url(
        monkeypatch,
        {
            "/api/v2/instance": client.MastodonError("404"),
            "/api/v1/instance": {"max_toot_chars": 5000},
        },
    )
    assert client.instance_character_limit("gotosocial.example") == 5000
    assert calls == [
        "https://gotosocial.example/api/v2/instance",
        "https://gotosocial.example/api/v1/instance",
    ]


def test_instance_character_limit_falls_back_to_v1_when_v2_has_no_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # v2 answers but carries no configuration.statuses.max_characters -- try v1.
    client.clear_character_limit_cache()
    _stub_http_by_url(
        monkeypatch,
        {
            "/api/v2/instance": {"domain": "fork.example"},
            "/api/v1/instance": {"max_toot_chars": 2048},
        },
    )
    assert client.instance_character_limit("fork.example") == 2048


def test_instance_character_limit_v1_reads_nested_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Some forks put the limit under configuration.statuses.max_characters on v1
    # rather than a top-level max_toot_chars.
    client.clear_character_limit_cache()
    _stub_http_by_url(
        monkeypatch,
        {
            "/api/v2/instance": client.MastodonError("404"),
            "/api/v1/instance": {"configuration": {"statuses": {"max_characters": 4096}}},
        },
    )
    assert client.instance_character_limit("akkoma.example") == 4096


def test_instance_character_limit_v2_preferred_over_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # When both endpoints answer, the richer v2 value wins.
    client.clear_character_limit_cache()
    calls = _stub_http_by_url(
        monkeypatch,
        {
            "/api/v2/instance": {"configuration": {"statuses": {"max_characters": 9999}}},
            "/api/v1/instance": {"max_toot_chars": 500},
        },
    )
    assert client.instance_character_limit("mastodon.example") == 9999
    assert calls == ["https://mastodon.example/api/v2/instance"]  # v1 never queried


def test_instance_character_limit_both_endpoints_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    # Neither v2 nor v1 available -> default 500, never raise.
    client.clear_character_limit_cache()
    _stub_http_by_url(
        monkeypatch,
        {
            "/api/v2/instance": client.MastodonError("down"),
            "/api/v1/instance": client.MastodonError("down"),
        },
    )
    assert client.instance_character_limit("offline.example") == client.DEFAULT_CHARACTER_LIMIT
