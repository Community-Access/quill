from __future__ import annotations

from quill.core.publishing_clients import PublishingRemoteDocument
from quill.core.publishing_compare import build_publishing_comparison


def _remote(**overrides: object) -> PublishingRemoteDocument:
    defaults: dict[str, object] = {
        "provider_id": "wordpress",
        "site_url": "https://example.com",
        "remote_id": "22",
        "remote_url": "https://example.com/about",
        "title": "About page",
        "status": "publish",
        "content_kind": "page",
        "body": "<p>About body</p>",
        "updated_at": "2026-06-18T12:00:00",
    }
    defaults.update(overrides)
    return PublishingRemoteDocument(**defaults)  # type: ignore[arg-type]


def test_build_publishing_comparison_reports_no_differences_when_everything_matches() -> None:
    comparison = build_publishing_comparison(
        _remote(),
        local_title="About page",
        local_body_html="<p>About body</p>",
        local_status="publish",
        last_known_updated_at="2026-06-18T12:00:00",
    )

    assert comparison.title_differs is False
    assert comparison.body_differs is False
    assert comparison.status_differs is False
    assert comparison.remote_changed_since_last_known is False
    assert comparison.provider_id == "wordpress"
    assert comparison.site_url == "https://example.com"
    assert comparison.remote_url == "https://example.com/about"
    assert comparison.content_kind == "page"


def test_build_publishing_comparison_detects_title_difference() -> None:
    comparison = build_publishing_comparison(
        _remote(title="New remote title"),
        local_title="Old local title",
        local_body_html="<p>About body</p>",
        local_status="publish",
        last_known_updated_at="2026-06-18T12:00:00",
    )

    assert comparison.title_differs is True
    assert comparison.body_differs is False
    assert comparison.status_differs is False


def test_build_publishing_comparison_detects_body_difference() -> None:
    comparison = build_publishing_comparison(
        _remote(),
        local_title="About page",
        local_body_html="<p>Edited local body</p>",
        local_status="publish",
        last_known_updated_at="2026-06-18T12:00:00",
    )

    assert comparison.body_differs is True
    assert comparison.title_differs is False


def test_build_publishing_comparison_detects_status_difference() -> None:
    comparison = build_publishing_comparison(
        _remote(status="draft"),
        local_title="About page",
        local_body_html="<p>About body</p>",
        local_status="publish",
        last_known_updated_at="2026-06-18T12:00:00",
    )

    assert comparison.status_differs is True
    assert comparison.local_status == "publish"
    assert comparison.remote_status == "draft"


def test_build_publishing_comparison_detects_remote_changed_since_last_known() -> None:
    comparison = build_publishing_comparison(
        _remote(updated_at="2026-06-20T09:00:00"),
        local_title="About page",
        local_body_html="<p>About body</p>",
        local_status="publish",
        last_known_updated_at="2026-06-18T12:00:00",
    )

    assert comparison.remote_changed_since_last_known is True


def test_build_publishing_comparison_treats_unknown_last_known_as_no_detected_change() -> None:
    comparison = build_publishing_comparison(
        _remote(updated_at="2026-06-20T09:00:00"),
        local_title="About page",
        local_body_html="<p>About body</p>",
        local_status="publish",
        last_known_updated_at="",
    )

    assert comparison.remote_changed_since_last_known is False
