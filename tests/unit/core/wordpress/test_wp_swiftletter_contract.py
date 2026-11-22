"""QUILL's SwiftLetter client against SwiftLetter's own Phase 1 contract fixtures.

The JSON under ``tests/fixtures/swiftletter_contract/`` is copied unchanged from
SwiftLetter's shared contract (see the README there for the commit). Each test
replays a fixture's ``example`` response, or an exact error body, through the
real client, so the fake and the plugin cannot drift apart unnoticed.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse

import pytest

from quill.core.wordpress import swiftletter, swiftletter_errors
from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "swiftletter_contract"
_IDS = {"articles.garden.id": 4, "articles.market.id": 5, "newsletters.gazette.id": 9}
_PLACEHOLDER = re.compile(r"\{\{([a-z_.]+)\}\}")


def _fixture(name: str) -> dict[str, Any]:
    data = json.loads((_FIXTURES / f"{name}.json").read_bytes())
    assert data["contract_version"] == 1, "a new contract version needs QUILL's review first"
    return data


_SEED = _fixture("seed")


def _value(path: str) -> Any:
    if path in _IDS:
        return _IDS[path]
    if path.startswith(("captures.", "body.")):  # values the live run captures
        return f"<{path}>"
    group, key, field = path.split(".")
    return _SEED[group][key][field]


def _resolve(value: Any) -> Any:
    """Fill ``{{...}}`` placeholders from the seed; a lone placeholder keeps its type."""
    if isinstance(value, dict):
        return {key: _resolve(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item) for item in value]
    if isinstance(value, str):
        whole = _PLACEHOLDER.fullmatch(value)
        if whole:
            return _value(whole.group(1))
        return _PLACEHOLDER.sub(lambda found: str(_value(found.group(1))), value)
    return value


def _step(scenario: str, step_id: str) -> dict[str, Any]:
    found = [s for s in _fixture(scenario)["steps"] if s["id"] == step_id]
    assert len(found) == 1, step_id
    return _resolve(found[0])


class _Site:
    """Answers each route with what a fixture step says, and records what was sent."""

    def __init__(self) -> None:
        self.answers: dict[tuple[str, str], tuple[int, Any]] = {}
        self.requests: list[Any] = []

    def answer(self, step: dict[str, Any], body: Any = None) -> None:
        request, response = step["request"], step["response"]
        route = "/wp-json" + request["route"]
        payload = response.get("example", response.get("body")) if body is None else body
        self.answers[request["method"], route] = (response["status"], payload)

    def __call__(self, request: Any, **_options: Any) -> Any:
        self.requests.append(request)
        status, payload = self.answers[request.get_method(), urlparse(request.full_url).path]
        raw = io.BytesIO(json.dumps(payload).encode())
        if status >= 400:
            raise HTTPError(request.full_url, status, "Refused", {}, raw)  # type: ignore[arg-type]
        raw.headers = {}  # type: ignore[attr-defined]
        return raw

    def api(self) -> WordPressApi:
        return WordPressApi(
            SiteAddress("https://example.org"),
            SiteAuth("app_password", "t", "fixture"),
            opener=self,
        )


def _opened(site: _Site) -> swiftletter.Article:
    site.answer(_step("article-context", "editor-opens-article"))
    return swiftletter.open_article(site.api(), 4)


def test_the_discovery_example_offers_browse_open_and_save():
    site = _Site()
    site.answers["GET", "/wp-json/"] = (200, {"namespaces": ["wp/v2", "swiftletter/v1"]})
    site.answer(_step("discovery", "editor-discovers-features"))
    found = swiftletter.discover(site.api())
    assert found is not None and found.can_browse and found.can_open and found.can_save


def test_the_edit_context_example_opens_as_a_working_copy():
    site = _Site()
    article = _opened(site)
    assert article.title == _SEED["articles"]["garden"]["title"]
    assert article.content == _SEED["articles"]["garden"]["content"]
    assert article.newsletter_ids == (9,)
    assert article.review_state == "reviewed"
    assert site.requests[-1].full_url.endswith("?context=edit")


def test_the_save_example_is_read_and_sends_title_content_and_if_match_only():
    site = _Site()
    article = _opened(site)
    step = _step("article-save", "save-current-version")
    site.answer(step)
    sent = step["request"]["json"]
    saved = swiftletter.save_article_stored(
        site.api(), article, title=sent["title"], content=sent["content"]
    )
    assert saved.edit_version == step["response"]["example"]["edit_version"]
    assert not saved.returned_stored  # this build answers id and edit_version only
    request = site.requests[-1]
    assert json.loads(request.data) == sent
    assert request.get_header("If-match") == article.edit_version


@pytest.mark.parametrize(
    ("step_id", "kind"),
    [
        ("save-without-version", swiftletter_errors.SwiftLetterVersionRequired),
        ("save-with-wildcard-version", swiftletter_errors.SwiftLetterInvalidVersion),
        ("save-cannot-publish", swiftletter_errors.SwiftLetterInvalidSave),
        ("replaying-old-version-is-refused", swiftletter_errors.SwiftLetterConflict),
        ("stale-save-after-wordpress-edit-is-refused", swiftletter_errors.SwiftLetterConflict),
    ],
)
def test_each_contract_refusal_is_said_in_swiftletters_exact_words(step_id, kind):
    site = _Site()
    article = _opened(site)
    step = _step("article-save", step_id)
    site.answer(step)
    with pytest.raises(kind) as refused:
        swiftletter.save_article(site.api(), article, title="Edit", content="Text")
    assert refused.value.plain == step["response"]["body"]["message"]
    assert [r.get_method() for r in site.requests] == ["GET", "POST"]  # never retried


def test_kses_rewriting_an_image_on_a_contributor_save_counts_as_wordpress_changing_it():
    # SwiftLetter's CI found WordPress stores a contributor's `"/>` as `" />`.
    site = _Site()
    article = _opened(site)
    step = _step("article-save", "save-current-version")
    sent = step["request"]["json"]
    stored = sent["content"].replace('"/>', '" />')
    assert stored != sent["content"]
    answer = {**step["response"]["example"], "title": sent["title"], "content": stored}
    site.answer(step, body=answer)
    saved = swiftletter.save_article_stored(
        site.api(), article, title=sent["title"], content=sent["content"]
    )
    assert saved.stored_differs and saved.content_changed and not saved.title_changed
    # The site's text becomes the baseline for the next If-Match; the caller keeps the
    # person's own copy and tells them, rather than replacing it.
    assert saved.baseline(article).content == stored
    assert saved.sent_content == sent["content"]
