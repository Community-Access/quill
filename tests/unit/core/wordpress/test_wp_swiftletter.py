"""SwiftLetter Phase 1 against QUILL's existing WordPress HTTP client."""

from __future__ import annotations

import io
import json
from dataclasses import replace
from urllib.error import HTTPError
from urllib.parse import urlparse

import pytest

from quill.core.wordpress import swiftletter
from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi, WordPressApiError

_VERSION = '"' + "1" * 64 + '"'
_NEXT_VERSION = '"' + "2" * 64 + '"'
_NAMESPACE = "/wp-json/swiftletter/v1"
_ARTICLE = "/wp-json/wp/v2/swl-articles/4"
_SAVE = f"{_NAMESPACE}/articles/4/save"


class _Site:
    def __init__(self):
        self.routes = {
            ("GET", "/wp-json/"): {"namespaces": ["wp/v2", "swiftletter/v1"]},
            ("GET", _NAMESPACE): {
                "swiftletter": {
                    "api_version": "1.0",
                    "article_rest_base": "swl-articles",
                    "capabilities": {"read": True},
                    "features": {"browse": True, "article_save": True},
                }
            },
            ("GET", f"{_NAMESPACE}/newsletters"): [{"id": 9, "title": "December"}],
            ("GET", f"{_NAMESPACE}/newsletters/9"): {
                "articles": [
                    {"id": 4, "title": "Draft", "review_confirmed": False},
                    {"id": 2, "title": "Ready", "review_confirmed": True},
                ]
            },
            ("GET", _ARTICLE): {
                "id": 4,
                "title": {"raw": "Draft"},
                "content": {"raw": "<p>Keep this markup.</p>"},
                "swiftletter": {
                    "review_state": "not_reviewed",
                    "newsletters": [{"id": 9, "title": "December"}],
                    "edit_version": _VERSION,
                },
            },
            ("POST", _SAVE): {"id": 4, "edit_version": _NEXT_VERSION},
        }
        self.requests = []

    def __call__(self, request, **_options):
        self.requests.append(request)
        answer = self.routes[request.get_method(), urlparse(request.full_url).path]
        if isinstance(answer, Exception):
            raise answer
        response = io.BytesIO(json.dumps(answer).encode())
        response.headers = {"X-WP-TotalPages": "1"}
        return response

    def api(self, url="https://example.org"):
        return WordPressApi(
            SiteAddress(url), SiteAuth("app_password", "test", "fixture"), opener=self
        )


def test_browse_open_and_explicit_save_use_the_same_site_client():
    site = _Site()
    api = site.api()
    assert swiftletter.discover(api) == swiftletter.Discovery(can_browse=True, can_save=True)
    assert list(swiftletter.newsletters(api)) == [swiftletter.Newsletter(9, "December")]
    assert [row.id for row in swiftletter.articles(api, 9)] == [4, 2]
    article = swiftletter.open_article(api, 4)
    assert article.newsletter_ids == (9,)
    assert article.content == "<p>Keep this markup.</p>"
    assert site.requests[-1].full_url.endswith("?context=edit")
    assert all(request.get_method() == "GET" for request in site.requests)

    assert (
        swiftletter.save_article(api, article, title="Edit", content="<p>Text</p>") == _NEXT_VERSION
    )
    request = site.requests[-1]
    assert request.get_method() == "POST"
    assert request.get_header("Authorization").startswith("Basic ")
    assert request.get_header("If-match") == _VERSION
    assert json.loads(request.data) == {"title": "Edit", "content": "<p>Text</p>"}


def test_site_without_swiftletter_never_requests_its_namespace():
    site = _Site()
    site.routes["GET", "/wp-json/"] = {"namespaces": ["wp/v2"]}
    assert swiftletter.discover(site.api()) is None
    assert len(site.requests) == 1


def test_dashboard_only_version_does_not_discover_as_an_editor_client():
    site = _Site()
    site.routes["GET", _NAMESPACE] = {"namespace": "swiftletter/v1", "routes": {}}
    assert swiftletter.discover(site.api()) is None


def test_older_discovery_can_browse_without_advertising_save():
    site = _Site()
    site.routes["GET", _NAMESPACE]["swiftletter"]["features"]["article_save"] = False
    assert swiftletter.discover(site.api()) == swiftletter.Discovery(
        can_browse=True, can_save=False
    )


def test_unsupported_api_major_version_fails_without_reading_editorial_content():
    site = _Site()
    site.routes["GET", _NAMESPACE]["swiftletter"]["api_version"] = "2.0"
    with pytest.raises(WordPressApiError, match="does not support"):
        swiftletter.discover(site.api())
    assert len(site.requests) == 2


def test_stale_save_has_an_actionable_message_and_no_automatic_retry():
    site = _Site()
    api = site.api()
    article = swiftletter.open_article(api, 4)
    site.routes["POST", _SAVE] = HTTPError(
        f"https://example.org{_SAVE}",
        412,
        "Precondition Failed",
        {},
        io.BytesIO(b'{"code":"swiftletter_precondition_failed"}'),
    )
    with pytest.raises(WordPressApiError, match="Compare it with the current article") as exc:
        swiftletter.save_article(api, article, title="Edit", content="Text")
    assert exc.value.status == 412
    assert [request.get_method() for request in site.requests] == ["GET", "POST"]


def test_wrong_site_or_missing_version_cannot_send_a_write():
    site = _Site()
    api = site.api()
    article = swiftletter.open_article(api, 4)
    with pytest.raises(WordPressApiError, match="original WordPress site"):
        swiftletter.save_article(
            site.api("https://elsewhere.example"), article, title="Edit", content=""
        )
    with pytest.raises(WordPressApiError, match="Reopen it before saving"):
        swiftletter.save_article(api, replace(article, edit_version=None), title="Edit", content="")
    assert [request.get_method() for request in site.requests] == ["GET"]
