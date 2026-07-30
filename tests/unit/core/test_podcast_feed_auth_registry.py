"""Tests for the Quillin feed-auth provider registry and its use by feed_auth."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from quill.core.podcasts import feed_auth, feed_auth_registry
from quill.core.podcasts.models import PodcastShow


@pytest.fixture(autouse=True)
def _clear_registry() -> Iterator[None]:
    feed_auth_registry.clear_providers()
    yield
    feed_auth_registry.clear_providers()


def _show() -> PodcastShow:
    return PodcastShow(
        id="show-1",
        title="Premium Show",
        feed_url="https://premium.example.com/feed.xml",
    )


def test_provider_supplies_header_for_matching_host() -> None:
    feed_auth_registry.register_provider(
        "ext.p.one", ("premium.example.com",), lambda _feed, _url: "Bearer token-123"
    )
    header = feed_auth_registry.auth_header_from_providers(
        "https://premium.example.com/feed.xml", "https://premium.example.com/ep.mp3"
    )
    assert header == "Bearer token-123"


def test_provider_ignored_for_non_matching_host() -> None:
    feed_auth_registry.register_provider(
        "ext.p.one", ("premium.example.com",), lambda _feed, _url: "Bearer token-123"
    )
    assert (
        feed_auth_registry.auth_header_from_providers(
            "https://premium.example.com/feed.xml", "https://cdn.other.com/ep.mp3"
        )
        == ""
    )


def test_wildcard_host_matches_subdomain() -> None:
    feed_auth_registry.register_provider(
        "ext.p.one", ("*.premium.example.com",), lambda _feed, _url: "Bearer wild"
    )
    assert (
        feed_auth_registry.auth_header_from_providers(
            "https://feeds.premium.example.com/f", "https://cdn.premium.example.com/ep.mp3"
        )
        == "Bearer wild"
    )


def test_faulty_provider_is_skipped() -> None:
    def _boom(_feed: str, _url: str) -> str:
        raise RuntimeError("provider blew up")

    feed_auth_registry.register_provider("ext.p.bad", ("premium.example.com",), _boom)
    feed_auth_registry.register_provider(
        "ext.p.good", ("premium.example.com",), lambda _feed, _url: "Bearer ok"
    )
    assert (
        feed_auth_registry.auth_header_from_providers(
            "https://premium.example.com/f", "https://premium.example.com/ep.mp3"
        )
        == "Bearer ok"
    )


def test_feed_auth_uses_provider_before_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    # A registered provider wins over the built-in per-show Basic path.
    feed_auth_registry.register_provider(
        "ext.p.one", ("premium.example.com",), lambda _feed, _url: "Bearer provider-wins"
    )
    show = _show()
    assert (
        feed_auth.auth_header_for_url(show, "https://premium.example.com/ep.mp3")
        == "Bearer provider-wins"
    )


def test_feed_auth_falls_back_to_basic_when_no_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(feed_auth, "load_feed_password", lambda _show_id: "secret")
    show = PodcastShow(
        id="show-2",
        title="Basic Show",
        feed_url="https://basic.example.com/feed.xml",
        feed_username="alice",
    )
    header = feed_auth.auth_header_for_url(show, "https://basic.example.com/ep.mp3")
    assert header.startswith("Basic ")
