"""The REST client against a recorded site: routes, signing, paging, failures."""

from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_media as wpm
from quill.core.wordpress.api import (
    SiteAddress,
    SiteAuth,
    WordPressApi,
    WordPressApiError,
    WordPressPolicyError,
    plain_error,
    route_url,
)


class _Response:
    def __init__(self, payload, status=200, headers=None):
        self._raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.status = status
        self.headers = headers or {}

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class FakeSite:
    """An opener that answers by (method, path) and records every request."""

    def __init__(self):
        self.routes: dict[tuple[str, str], object] = {}
        self.requests: list = []

    def on(self, method, path, answer):
        self.routes[(method, path)] = answer
        return self

    def __call__(self, request, timeout=None, context=None):
        self.requests.append(request)
        parsed = urlparse(request.full_url)
        key = (request.get_method(), parsed.path)
        answer = self.routes.get(key)
        if answer is None:
            raise HTTPError(
                request.full_url, 404, "nf", {}, io.BytesIO(b'{"code":"rest_no_route"}')
            )
        if callable(answer):
            answer = answer(request, parse_qs(parsed.query))
        if isinstance(answer, BaseException):
            raise answer
        if isinstance(answer, _Response):
            return answer
        return _Response(answer)


def _api(fake, **kw):
    return WordPressApi(
        SiteAddress("https://radio.example"),
        SiteAuth("app_password", "jeff", "abcd efgh ijkl mnop qrst uvwx"),
        opener=fake,
        site_name="Community Radio",
        **kw,
    )


def test_routes_for_self_hosted_and_wpcom() -> None:
    assert (
        route_url(SiteAddress("https://a.example/"), "wp/v2/posts", {"page": 2})
        == "https://a.example/wp-json/wp/v2/posts?page=2"
    )
    com = SiteAddress("https://b.wordpress.com", wpcom_site="b.wordpress.com")
    assert route_url(com, "wp/v2/media/5") == (
        "https://public-api.wordpress.com/wp/v2/sites/b.wordpress.com/media/5"
    )
    assert route_url(com, "") == "https://public-api.wordpress.com/wp/v2/sites/b.wordpress.com"
    assert route_url(SiteAddress("https://a.example"), "") == "https://a.example/wp-json/"


def test_list_values_and_booleans_are_query_friendly() -> None:
    url = route_url(
        SiteAddress("https://a.example"),
        "wp/v2/posts",
        {"status": ["draft", "publish"], "x": True, "n": None},
    )
    assert parse_qs(urlparse(url).query) == {"status": ["draft,publish"], "x": ["true"]}


def test_only_https_or_loopback_gets_a_password() -> None:
    with pytest.raises(WordPressPolicyError):
        WordPressApi(SiteAddress("http://radio.example"), SiteAuth("app_password", "a", "b"))
    WordPressApi(SiteAddress("http://127.0.0.1:8080"), SiteAuth("app_password", "a", "b"))
    WordPressApi(SiteAddress("http://mysite.test"), SiteAuth("app_password", "a", "b"))


def test_signing_and_the_secret_never_shows() -> None:
    basic = SiteAuth("app_password", "jeff", "pw")
    assert basic.header().startswith("Basic ")
    assert "pw" not in repr(basic)
    bearer = SiteAuth("bearer", secret="tok123")
    assert bearer.header() == "Bearer tok123"
    assert "tok123" not in repr(bearer)
    assert "tok123" not in repr(WordPressApi(SiteAddress("https://x.example"), bearer))


def test_collections_page_until_the_last_page() -> None:
    def posts(_req, query):
        page = int(query["page"][0])
        rows = [
            {
                "id": page * 10 + i,
                "type": "post",
                "title": {"rendered": f"P{page}{i}"},
                "status": "publish",
                "modified_gmt": "2026-11-03T10:00:00",
                "link": "",
            }
            for i in range(2)
        ]
        return _Response(rows, headers={"X-WP-TotalPages": "3"})

    fake = FakeSite().on("GET", "/wp-json/wp/v2/posts", posts)
    items = list(wp.list_items(_api(fake), "post"))
    assert [i.id for i in items] == [10, 11, 20, 21, 30, 31]
    assert len(fake.requests) == 3
    assert items[0].spoken().startswith("P10, Published, last changed 3 November 2026, 10:00 AM")


def test_paging_stops_on_a_short_page_without_the_header() -> None:
    fake = FakeSite().on(
        "GET", "/wp-json/wp/v2/tags", [{"id": 1, "name": "JAWS", "slug": "jaws", "count": 3}]
    )
    terms = wp.list_terms(_api(fake), "post_tag")
    assert [t.name for t in terms] == ["JAWS"]
    assert len(fake.requests) == 1


def test_a_refusal_is_a_plain_sentence_naming_the_site() -> None:
    body = io.BytesIO(json.dumps({"code": "rest_cannot_publish", "message": "Sorry"}).encode())
    fake = FakeSite().on(
        "POST",
        "/wp-json/wp/v2/posts/5",
        HTTPError("u", 403, "Forbidden", {}, body),
    )
    item = wp.Item(id=5, kind="post", title="T", content="c", status="publish")
    with pytest.raises(WordPressApiError) as caught:
        wp.update_item(_api(fake), item)
    assert caught.value.status == 403
    assert caught.value.wp_code == "rest_cannot_publish"
    assert caught.value.plain.startswith("Your account on Community Radio cannot publish this.")
    assert "403" not in caught.value.plain


def test_network_failures_say_what_to_do() -> None:
    fake = FakeSite().on("GET", "/wp-json/wp/v2/users/me", URLError("timed out"))
    with pytest.raises(WordPressApiError) as caught:
        wp.load_account(_api(fake))
    assert "took too long" in caught.value.plain


def test_plain_error_never_gives_a_bare_status() -> None:
    for status in (400, 401, 403, 404, 413, 429, 500, 502, 418):
        sentence = plain_error(status=status, site_name="Site")
        assert sentence.endswith(".") and "Site" in sentence


def test_a_php_notice_before_the_json_is_tolerated() -> None:
    fake = FakeSite().on(
        "GET",
        "/wp-json/wp/v2/users/me",
        _Response(
            b'<b>Notice</b>: x\n{"id": 3, "name": "Jeff", "roles": ["editor"], '
            b'"capabilities": {"publish_posts": true, "publish_pages": true, '
            b'"upload_files": true}}'
        ),
    )
    account = wp.load_account(_api(fake))
    assert account.role_name == "Editor"
    assert account.publish_label("page") == "Publish or Update"


def test_a_contributor_submits_for_review() -> None:
    fake = FakeSite().on(
        "GET",
        "/wp-json/wp/v2/users/me",
        {"id": 4, "roles": ["contributor"], "capabilities": {"edit_posts": True}},
    )
    account = wp.load_account(_api(fake))
    assert account.publish_label("post") == "Submit for Review"
    assert not account.can_upload


def test_load_keeps_raw_content_with_block_comments() -> None:
    raw = "<!-- wp:paragraph -->\n<p>Hi</p>\n<!-- /wp:paragraph -->"
    fake = FakeSite().on(
        "GET",
        "/wp-json/wp/v2/pages/7",
        {
            "id": 7,
            "type": "page",
            "status": "publish",
            "slug": "about",
            "title": {"raw": "About &amp; us", "rendered": "About &#038; us"},
            "content": {"raw": raw, "rendered": "<p>Hi</p>"},
            "modified_gmt": "2026-11-01T09:00:00",
        },
    )
    item = wp.load_item(_api(fake), "page", 7)
    assert item.content == raw
    assert item.title == "About &amp; us"
    assert item.slug == "about"


def test_site_info_reads_name_version_and_authorize_url() -> None:
    fake = FakeSite().on(
        "GET",
        "/wp-json/",
        {
            "name": "Community Radio &amp; Friends",
            "description": "",
            "home": "https://radio.example",
            "generator": "https://wordpress.org/?v=7.0.1",
            "namespaces": ["wp/v2", "batch/v1"],
            "authentication": {
                "application-passwords": {
                    "endpoints": {
                        "authorization": "https://radio.example/wp-admin/authorize-application.php"
                    }
                }
            },
        },
    )
    info = wp.load_site_info(_api(fake))
    assert info.name == "Community Radio & Friends"
    assert info.wp_version == "7.0.1"
    assert info.supports("batch/v1")
    assert info.authorize_url.endswith("authorize-application.php")


def test_upload_sends_the_file_then_its_fields() -> None:
    seen = {}

    def upload(req, _q):
        seen["disposition"] = req.get_header("Content-disposition")
        seen["type"] = req.get_header("Content-type")
        seen["body"] = req.data
        return {
            "id": 9,
            "source_url": "https://radio.example/u/fair.jpg",
            "mime_type": "image/jpeg",
            "media_details": {"width": 2400, "height": 1600},
        }

    def fields(req, _q):
        seen["fields"] = json.loads(req.data)
        return {
            "id": 9,
            "alt_text": "Volunteers at the fair",
            "source_url": "https://radio.example/u/fair.jpg",
            "mime_type": "image/jpeg",
            "media_details": {"width": 2400, "height": 1600, "filesize": 204800},
        }

    fake = (
        FakeSite()
        .on("POST", "/wp-json/wp/v2/media", upload)
        .on("POST", "/wp-json/wp/v2/media/9", fields)
    )
    item = wpm.upload_media(
        _api(fake), 'fair".jpg', b"JPEG", "image/jpeg", alt_text="Volunteers at the fair"
    )
    assert seen["disposition"] == 'attachment; filename="fair.jpg"'
    assert seen["type"] == "image/jpeg" and seen["body"] == b"JPEG"
    assert seen["fields"] == {"alt_text": "Volunteers at the fair"}
    assert item.spoken().startswith(
        "fair.jpg, image, 2400 by 1600, 200 KB, alt text: Volunteers at the fair"
    )


def test_batch_goes_in_chunks_of_25() -> None:
    sizes = []

    def batch(req, _q):
        body = json.loads(req.data)
        sizes.append(len(body["requests"]))
        return {"responses": [{"status": 200} for _ in body["requests"]]}

    fake = FakeSite().on("POST", "/wp-json/batch/v1", batch)
    answers = _api(fake).batch([
        {"method": "POST", "path": f"/wp/v2/posts/{i}", "body": {}} for i in range(30)
    ])
    assert sizes == [25, 5] and len(answers) == 30


def test_merge_moves_posts_then_deletes_the_source() -> None:
    calls = []
    fake = (
        FakeSite()
        .on(
            "GET",
            "/wp-json/wp/v2/posts",
            [{"id": 1, "categories": [3, 7]}, {"id": 2, "categories": [3]}],
        )
        .on(
            "POST",
            "/wp-json/batch/v1",
            lambda req, _q: calls.append(json.loads(req.data)) or {"responses": []},
        )
        .on(
            "DELETE",
            "/wp-json/wp/v2/categories/3",
            lambda req, q: calls.append(("delete", q)) or {"deleted": True},
        )
    )
    moved = wp.merge_terms(_api(fake), "category", 3, 7)
    assert moved == 2
    bodies = [r["body"] for r in calls[0]["requests"]]
    assert bodies == [{"categories": [7]}, {"categories": [7]}]
    assert calls[1] == ("delete", {"force": ["true"]})


def test_revisions_and_autosaves_newest_first_and_forbidden_is_skipped() -> None:
    body = io.BytesIO(b'{"code":"rest_cannot_read"}')
    fake = (
        FakeSite()
        .on(
            "GET",
            "/wp-json/wp/v2/posts/5/revisions",
            [{"id": 1, "modified_gmt": "2026-11-01T00:00:00", "content": {"raw": "a"}}],
        )
        .on("GET", "/wp-json/wp/v2/posts/5/autosaves", HTTPError("u", 403, "x", {}, body))
    )
    revs = wp.list_revisions(_api(fake), "post", 5)
    assert [r.id for r in revs] == [1]


def test_helpers() -> None:
    assert wp.slugify("Spring Workshop: Book Now!") == "spring-workshop-book-now"
    assert wp.slugify("Café crème") == "cafe-creme"
    assert wp.human_size(512) == "512 bytes"
    assert wp.human_size(3 * 1024 * 1024) == "3.0 MB"
    assert wp.plain_text("<!-- wp:p --><p>A &amp; <b>B</b></p>") == "A & B"
    assert wp.friendly_date("") == "at an unknown time"


def test_batch_is_found_among_routes_not_namespaces() -> None:
    """WordPress 7.1 lists /batch/v1 as a route only (seen on the live test site)."""
    fake = FakeSite().on(
        "GET",
        "/wp-json/",
        {"name": "T", "namespaces": ["wp/v2"], "routes": {"/": {}, "/batch/v1": {}, "/wp/v2": {}}},
    )
    info = wp.load_site_info(_api(fake))
    assert info.supports("batch/v1")
    assert info.supports("wp/v2")
    assert not info.supports("wp-site-health/v1")
