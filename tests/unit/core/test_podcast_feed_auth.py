"""feed_auth: the same-host credential gate for private podcast feeds."""

from __future__ import annotations

import pytest

from quill.core.podcasts import feed_auth
from quill.core.podcasts.models import PodcastShow
from quill.stability.redaction import redact_url_userinfo


def _show(**kwargs: object) -> PodcastShow:
    defaults: dict[str, object] = {
        "id": "show-1",
        "title": "Private Show",
        "feed_url": "https://feeds.example.com/private.rss",
        "feed_username": "member",
    }
    defaults.update(kwargs)
    return PodcastShow(**defaults)  # type: ignore[arg-type]


def _patch_password(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setattr(feed_auth, "load_feed_password", lambda _sid: value)


def test_auth_for_url_same_host_returns_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://feeds.example.com/ep1.mp3") == ("member", "pw")


def test_auth_for_url_host_match_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://FEEDS.EXAMPLE.COM/x") == ("member", "pw")


def test_auth_for_url_different_host_returns_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://cdn.example.com/ep1.mp3") == ("", "")


def test_auth_for_url_subdomain_is_a_different_host(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://media.feeds.example.com/x") == ("", "")


def test_auth_for_url_no_username_returns_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show(feed_username="")
    assert feed_auth.auth_for_url(show, "https://feeds.example.com/x") == ("", "")


def test_auth_for_url_local_show_returns_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show(is_local=True, feed_url="")
    assert feed_auth.auth_for_url(show, "https://feeds.example.com/x") == ("", "")


def test_auth_for_url_no_stored_password_returns_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_password(monkeypatch, "")
    show = _show()
    assert feed_auth.auth_for_url(show, "https://feeds.example.com/x") == ("", "")


def test_auth_header_for_url_builds_basic_header(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    header = feed_auth.auth_header_for_url(show, "https://feeds.example.com/x")
    assert header.startswith("Basic ")
    assert feed_auth.auth_header_for_url(show, "https://cdn.example.com/x") == ""


def test_basic_auth_header_encodes_user_colon_password() -> None:
    import base64

    header = feed_auth.basic_auth_header("member", "pw")
    assert base64.b64decode(header.removeprefix("Basic ")).decode() == "member:pw"


def test_url_with_auth_embeds_percent_encoded_userinfo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_password(monkeypatch, "p w:@")
    show = _show(feed_username="me@site")
    url = feed_auth.url_with_auth(show, "https://feeds.example.com:8443/e.mp3?a=1")
    assert url == "https://me%40site:p%20w%3A%40@feeds.example.com:8443/e.mp3?a=1"


def test_url_with_auth_leaves_other_hosts_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, "pw")
    show = _show()
    url = "https://cdn.example.com/e.mp3"
    assert feed_auth.url_with_auth(show, url) == url


def test_store_roundtrip_uses_credential_store(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: dict[str, str] = {}
    monkeypatch.setattr(
        "quill.platform.windows.credential_store.save_secret",
        lambda name, secret: saved.__setitem__(name, secret),
    )
    monkeypatch.setattr(
        "quill.platform.windows.credential_store.load_secret",
        lambda name: saved.get(name, ""),
    )
    monkeypatch.setattr(
        "quill.platform.windows.credential_store.delete_secret",
        lambda name: saved.pop(name, None) is not None,
    )
    feed_auth.save_feed_password("abc", "sekrit")
    assert saved == {"quill-podcast-feed:abc": "sekrit"}
    assert feed_auth.load_feed_password("abc") == "sekrit"
    feed_auth.delete_feed_password("abc")
    assert feed_auth.load_feed_password("abc") == ""


def test_redact_url_userinfo_strips_credentials() -> None:
    text = "loading https://me:pw@host.example.com/feed.rss now"
    assert redact_url_userinfo(text) == "loading https://host.example.com/feed.rss now"


def test_redact_url_userinfo_leaves_plain_urls_alone() -> None:
    text = "loading https://host.example.com/feed.rss now"
    assert redact_url_userinfo(text) == text


def test_playback_source_prefers_downloaded_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.podcasts.models import PodcastEpisode

    _patch_password(monkeypatch, "pw")
    show = _show()
    episode = PodcastEpisode(
        guid="g",
        title="E",
        audio_url="https://feeds.example.com/e.mp3",
        downloaded_path="C:/pods/e.mp3",
    )
    assert feed_auth.playback_source(show, episode) == "C:/pods/e.mp3"


def test_playback_source_embeds_auth_for_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.podcasts.models import PodcastEpisode

    _patch_password(monkeypatch, "pw")
    show = _show()
    episode = PodcastEpisode(guid="g", title="E", audio_url="https://feeds.example.com/e.mp3")
    assert feed_auth.playback_source(show, episode) == ("https://member:pw@feeds.example.com/e.mp3")
