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
from quill.core.wordpress.workbench_load import SiteContext, load
from quill.core.wordpress.workbench_plugin_branches import shows
from quill.core.wordpress.workbench_tree import WORDPRESS_TREE

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
        response.headers = dict(self.headers)
        return response

    headers = {"X-WP-TotalPages": "1"}

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
    with pytest.raises(WordPressApiError, match="needs a newer QUILL"):
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


@pytest.fixture(autouse=True)
def _fresh_discovery():
    from quill.core.wordpress.workbench_swiftletter import forget_discovery

    forget_discovery()
    yield
    forget_discovery()


def test_workbench_branch_follows_the_index_like_every_plugin_branch():
    # Until the index is read the branch shows, as Shop, Forms and the others do, so a
    # remembered place survives and an unreachable site still explains itself.
    assert shows("swiftletter", None)
    assert not shows("swiftletter", ["wp/v2"])
    assert shows("swiftletter", ["wp/v2", "swiftletter/v1"])
    assert shows("swiftletter", ["wp/v2", "/swiftletter/v1/"])
    root = WORDPRESS_TREE.template_node("site", "swiftletter")
    child = WORDPRESS_TREE.template_node("site", "swiftletter_newsletter")
    assert child.parent == root.key and child.dynamic


def test_discovery_matches_namespaces_the_way_the_branch_does():
    site = _Site()
    found = swiftletter.discover(site.api(), namespaces=["wp/v2", "/swiftletter/v1/"])
    assert found == swiftletter.Discovery(can_browse=True, can_save=True)


def test_workbench_loaders_preserve_order_and_present_review_state_in_words():
    site = _Site()
    ctx = SiteContext("Test", site.api())
    newsletters = load(ctx, "swiftletter:newsletters", {}, {})
    assert [(row.title, row.key) for row in newsletters] == [("December", "9")]
    rows = load(ctx, "swiftletter:articles", {}, {}, dynamic="9")
    assert [(row.title, row.cell("review"), row.cell("position")) for row in rows] == [
        ("Draft", "Not reviewed", "1 of 2"),
        ("Ready", "Reviewed", "2 of 2"),
    ]
    assert all(row.raw["newsletter_id"] == 9 for row in rows)
    assert all(request.get_method() == "GET" for request in site.requests)


def test_changed_since_review_is_said_in_words_when_the_site_sends_it():
    site = _Site()
    site.routes["GET", f"{_NAMESPACE}/newsletters/9"]["articles"][0]["review_state"] = "changed"
    rows = load(SiteContext("Test", site.api()), "swiftletter:articles", {}, {}, dynamic="9")
    assert rows[0].cell("review") == "Changed since review"
    assert rows[0].raw["review_state"] == "changed"
    assert swiftletter.review_words("needs_edits") == "Needs edits"


def test_newsletter_rows_say_count_and_when_and_name_repeated_titles():
    site = _Site()
    site.routes["GET", f"{_NAMESPACE}/newsletters"] = [
        {"id": 9, "title": "December", "article_count": 2, "modified_gmt": "2026-11-20T15:04:00"},
        {"id": 12, "title": "December", "article_count": 1},
    ]
    rows = load(SiteContext("Test", site.api()), "swiftletter:newsletters", {}, {})
    assert [row.title for row in rows] == ["December (newsletter 9)", "December (newsletter 12)"]
    assert rows[0].cell("articles") == "2"
    assert rows[1].cell("articles") == "1"
    assert "1 article." in rows[1].detail
    assert rows[0].cell("changed") == "20 November 2026, 3:04 PM"
    assert rows[0].detail.endswith("Last changed 20 November 2026, 3:04 PM.")


def test_article_details_add_the_newsletter_and_site():
    site = _Site()
    site.routes["GET", f"{_NAMESPACE}/newsletters/9"]["title"] = "December"
    rows = load(SiteContext("Test", site.api()), "swiftletter:articles", {}, {}, dynamic="9")
    assert rows[0].detail == "Draft. Not reviewed. Article 1 of 2 in December, on Test."


def test_discovery_is_read_once_per_site_not_on_every_list_load():
    site = _Site()
    ctx = SiteContext("Test", site.api())
    load(ctx, "swiftletter:newsletters", {}, {})
    load(ctx, "swiftletter:newsletters", {}, {})
    asked = [urlparse(request.full_url).path for request in site.requests]
    assert asked.count(_NAMESPACE) == 1


def test_refusals_name_the_site_and_carry_swiftletter_codes():
    site = _Site()
    site.routes["GET", _NAMESPACE]["swiftletter"]["capabilities"]["read"] = False
    with pytest.raises(swiftletter.SwiftLetterForbidden) as refused:
        load(SiteContext("Test", site.api()), "swiftletter:newsletters", {}, {})
    assert str(refused.value.plain) == (
        "Your account on Test is not allowed to browse SwiftLetter newsletters."
    )
    assert refused.value.code == "QUILL-SWIFTLETTER-API-FORBIDDEN"

    old = _Site()
    old.routes["GET", _NAMESPACE] = {"namespace": "swiftletter/v1", "routes": {}}
    with pytest.raises(swiftletter.SwiftLetterError, match="SwiftLetter on Test does not offer"):
        load(SiteContext("Test", old.api("https://old.example")), "swiftletter:newsletters", {}, {})


def test_a_new_major_version_is_refused_with_its_own_code():
    site = _Site()
    site.routes["GET", _NAMESPACE]["swiftletter"]["api_version"] = "2.0"
    with pytest.raises(swiftletter.SwiftLetterVersionError, match="version 2.0") as refused:
        swiftletter.discover(site.api())
    assert refused.value.code == "QUILL-SWIFTLETTER-API-VERSION"


def test_a_site_without_swiftletter_says_so_rather_than_asking_for_an_update():
    site = _Site()
    site.routes["GET", "/wp-json/"] = {"namespaces": ["wp/v2"]}
    with pytest.raises(swiftletter.SwiftLetterError, match="SwiftLetter is not active on Test"):
        load(SiteContext("Test", site.api()), "swiftletter:newsletters", {}, {})
    assert [urlparse(r.full_url).path for r in site.requests] == ["/wp-json/"]


def test_forgetting_a_site_reads_swiftletter_again():
    from quill.core.wordpress.workbench_site_stamp import forget_site

    site = _Site()
    ctx = SiteContext("Test", site.api())
    load(ctx, "swiftletter:newsletters", {}, {})
    forget_site(ctx.api)
    load(ctx, "swiftletter:newsletters", {}, {})
    asked = [urlparse(request.full_url).path for request in site.requests]
    assert asked.count(_NAMESPACE) == 2


# -- Michael's answers, 2026-11-22 ------------------------------------------------------


def _refusal(status, code, message=None):
    body = {"code": code, "data": {"status": status}}
    if message is not None:
        body["message"] = message
    raw = io.BytesIO(json.dumps(body).encode())
    return HTTPError(f"https://example.org{_SAVE}", status, "Refused", {}, raw)


@pytest.mark.parametrize(
    ("status", "code", "kind", "quill_code"),
    [
        (428, "swiftletter_version_required", "SwiftLetterVersionRequired", "VERSION-REQUIRED"),
        (400, "swiftletter_invalid_version", "SwiftLetterInvalidVersion", "INVALID-VERSION"),
        (400, "swiftletter_invalid_save", "SwiftLetterInvalidSave", "INVALID-SAVE"),
        (
            404,
            "swiftletter_article_unavailable",
            "SwiftLetterArticleUnavailable",
            "ARTICLE-UNAVAILABLE",
        ),
        (403, "swiftletter_forbidden", "SwiftLetterForbidden", "FORBIDDEN"),
        (412, "swiftletter_precondition_failed", "SwiftLetterConflict", "CONFLICT"),
        (409, "swiftletter_article_locked", "SwiftLetterArticleLocked", "ARTICLE-LOCKED"),
        (503, "swiftletter_save_unavailable", "SwiftLetterSaveUnavailable", "SAVE-UNAVAILABLE"),
    ],
)
def test_each_refusal_says_swiftletters_sentence_as_written_never_its_code(
    status, code, kind, quill_code
):
    from quill.core.wordpress import swiftletter_errors

    site = _Site()
    api = site.api()
    article = swiftletter.open_article(api, 4)
    said = "Pat Reyes is editing this article in WordPress. Your changes are still in QUILL."
    site.routes["POST", _SAVE] = _refusal(status, code, said)
    with pytest.raises(getattr(swiftletter_errors, kind)) as refused:
        swiftletter.save_article(api, article, title="Edit", content="Text")
    assert refused.value.plain == said
    assert code not in str(refused.value)
    assert refused.value.code == f"QUILL-SWIFTLETTER-API-{quill_code}"
    assert refused.value.status == status
    # Sent once: never retried, whatever the refusal.
    assert [request.get_method() for request in site.requests] == ["GET", "POST"]


def test_a_refusal_without_a_sentence_falls_back_to_quills_own():
    from quill.core.wordpress.swiftletter_errors import SwiftLetterArticleLocked

    site = _Site()
    api = site.api()
    article = swiftletter.open_article(api, 4)
    site.routes["POST", _SAVE] = _refusal(409, "article_locked")
    with pytest.raises(SwiftLetterArticleLocked) as refused:
        swiftletter.save_article(api, article, title="Edit", content="Text")
    assert refused.value.plain == SwiftLetterArticleLocked.fallback
    assert "still in QUILL" in refused.value.plain


def test_the_conflict_offers_compare_and_the_version_errors_offer_reopen():
    from quill.core.wordpress import swiftletter_errors as errors

    assert errors.SwiftLetterConflict.next_step == "compare"
    assert errors.SwiftLetterVersionRequired.next_step == "reopen"
    assert errors.SwiftLetterArticleLocked.next_step == ""
    codes = {kind.code for kind in errors.BY_CODE.values()}
    assert len(codes) == len(errors.BY_CODE)  # each its own code (GATE-EC)


def test_a_wordpress_refusal_swiftletter_did_not_send_keeps_wordpress_words():
    site = _Site()
    raw = io.BytesIO(b'{"code":"rest_not_logged_in","message":"x"}')
    site.routes["GET", _ARTICLE] = HTTPError(f"https://example.org{_ARTICLE}", 401, "No", {}, raw)
    with pytest.raises(WordPressApiError) as refused:
        swiftletter.open_article(site.api(), 4)
    assert not isinstance(refused.value, swiftletter.SwiftLetterError)


def test_save_reads_the_stored_title_and_content_and_says_when_they_differ():
    site = _Site()
    api = site.api()
    article = swiftletter.open_article(api, 4)
    site.routes["POST", _SAVE] = {
        "id": 4,
        "edit_version": _NEXT_VERSION,
        "title": {"raw": "Edit"},
        "content": {"raw": "<p>Text</p>"},
    }
    saved = swiftletter.save_article_stored(
        api, article, title="Edit", content='<p onclick="x">Text</p>'
    )
    assert saved.returned_stored and saved.stored_differs
    assert saved.content_changed and not saved.title_changed
    baseline = saved.baseline(article)
    assert baseline.content == "<p>Text</p>" and baseline.edit_version == _NEXT_VERSION

    site.routes["POST", _SAVE] = {
        "id": 4,
        "edit_version": _NEXT_VERSION,
        "title": "Edit",
        "content": "<p>Text</p>",
    }
    same = swiftletter.save_article_stored(api, article, title="Edit", content="<p>Text</p>")
    assert same.returned_stored and not same.stored_differs


def test_the_current_test_builds_save_answer_still_works():
    site = _Site()
    api = site.api()
    article = swiftletter.open_article(api, 4)
    saved = swiftletter.save_article_stored(api, article, title="Edit", content="Text")
    assert not saved.returned_stored and not saved.stored_differs
    assert saved.baseline(article).content == "Text"


def test_compare_with_site_reads_the_edit_route_and_never_writes():
    site = _Site()
    api = site.api()
    article = swiftletter.open_article(api, 4)
    current = swiftletter.current_article(api, article)
    assert current.content == "<p>Keep this markup.</p>"
    assert [request.get_method() for request in site.requests] == ["GET", "GET"]
    assert site.requests[-1].full_url.endswith("?context=edit")
    with pytest.raises(WordPressApiError, match="original WordPress site"):
        swiftletter.current_article(site.api("https://elsewhere.example"), article)


def test_article_rows_read_permissions_and_who_changed_them():
    site = _Site()
    rows = site.routes["GET", f"{_NAMESPACE}/newsletters/9"]["articles"]
    rows[0].update(
        review_state="changed",
        can_edit=False,
        can_review=False,
        modified_gmt="2026-11-21T09:30:00",
        modified_by="Pat Reyes",
    )
    rows[1].update(can_edit=True, can_review=True, modified_gmt="2026-11-20T08:00:00")
    rows[1]["modified_by"] = None
    first, second = swiftletter.articles(site.api(), 9)
    assert (first.review_state, first.can_edit, first.can_review) == ("changed", False, False)
    assert first.editor_words == "Pat Reyes"
    assert second.modified_by is None and second.editor_words == "Editor unknown"
    loaded = load(SiteContext("Test", site.api()), "swiftletter:articles", {}, {}, dynamic="9")
    assert loaded[0].detail.endswith(
        "Last changed 21 November 2026, 9:30 AM by Pat Reyes. "
        "Your account cannot edit this article."
    )
    assert loaded[1].detail.endswith("Last changed 20 November 2026, 8:00 AM. Editor unknown.")


@pytest.mark.parametrize("version", ["1", "1.0", "1.7", "1.12.3"])
def test_any_1x_is_accepted(version):
    site = _Site()
    site.routes["GET", _NAMESPACE]["swiftletter"]["api_version"] = version
    assert swiftletter.discover(site.api()) is not None


@pytest.mark.parametrize("version", ["2.0", "3.1", "", None, "one"])
def test_other_versions_are_refused_in_one_sentence(version):
    site = _Site()
    site.routes["GET", _NAMESPACE]["swiftletter"]["api_version"] = version
    with pytest.raises(swiftletter.SwiftLetterVersionError) as refused:
        swiftletter.discover(site.api())
    assert refused.value.plain.endswith("which needs a newer QUILL.")
    assert refused.value.plain.count(". ") == 0


def test_missing_feature_flags_are_off_and_each_flag_is_its_own():
    site = _Site()
    del site.routes["GET", _NAMESPACE]["swiftletter"]["features"]
    found = swiftletter.discover(site.api())
    assert found == swiftletter.Discovery(can_browse=False, can_save=False)
    site = _Site()
    site.routes["GET", _NAMESPACE]["swiftletter"]["features"] = {
        "browse": True,
        "article_context": True,
        "reorder": False,
    }
    found = swiftletter.discover(site.api())
    assert found is not None and found.can_browse and found.can_open and not found.can_save
    assert found.offers("article_context") and not found.offers("reorder")


def test_the_list_says_how_many_newsletters_remain_when_the_site_gives_a_total():
    site = _Site()
    site.headers = {"X-WP-TotalPages": "5", "X-WP-Total": "412"}
    site.routes["GET", f"{_NAMESPACE}/newsletters"] = [
        {"id": n, "title": f"Issue {n}"} for n in range(1, 101)
    ]
    listing = swiftletter.newsletter_list(site.api(), max_pages=3)
    assert len(listing.items) == 300 and listing.total == 412 and listing.remaining == 112
    rows = load(SiteContext("Test", site.api()), "swiftletter:newsletters", {}, {})
    assert rows[0].raw["left"].startswith("112 more of the site's 412 newsletters")


def test_no_remaining_words_when_the_total_is_unknown_or_all_are_shown():
    from quill.core.wordpress.workbench_swiftletter import left_words

    assert left_words(300, None) == ""
    assert left_words(12, 12) == ""
    rows = load(SiteContext("Test", _Site().api()), "swiftletter:newsletters", {}, {})
    assert rows[0].raw["left"] == ""


def test_wordpress_com_never_reads_swiftletter_and_says_so_in_one_sentence():
    from quill.core.wordpress.workbench_swiftletter import WPCOM_WORDS

    site = _Site()
    api = WordPressApi(
        SiteAddress("https://example.wordpress.com", wpcom_site="example.wordpress.com"),
        SiteAuth("bearer", secret="fixture"),
        opener=site,
    )
    assert swiftletter.discover(api) is None
    with pytest.raises(swiftletter.SwiftLetterError) as refused:
        load(SiteContext("Test", api), "swiftletter:newsletters", {}, {})
    assert refused.value.plain == WPCOM_WORDS.format(site="Test")
    assert site.requests == []


def test_a_version_quill_cannot_speak_is_explained_without_reading_again():
    site = _Site()
    site.routes["GET", _NAMESPACE]["swiftletter"]["api_version"] = "2.0"
    ctx = SiteContext("Test", site.api())
    for _ in range(2):
        with pytest.raises(swiftletter.SwiftLetterVersionError):
            load(ctx, "swiftletter:newsletters", {}, {})
    asked = [urlparse(request.full_url).path for request in site.requests]
    assert asked.count(_NAMESPACE) == 1
