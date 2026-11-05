"""A custom type (an Event) goes back to its REST base, and opens by address.

The live run against the test site found both: WordPress sends ``type: event``
but the route is ``wp/v2/events``, so an opened Event could not be sent back;
and Open by Web Address looked only in posts and pages.
"""

from __future__ import annotations

import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from quill.core.wordpress import site as wp
from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi
from quill.ui.wordpress_open_commands import find_by_address

API = "/wp-json/wp/v2"


class _Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode()
        self.status = 200
        self.headers = {}

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _Site:
    def __init__(self):
        self.routes = {}
        self.requests = []

    def on(self, method, path, answer):
        self.routes[(method, path)] = answer
        return self

    def __call__(self, request, timeout=None, context=None):
        self.requests.append(request)
        parsed = urlparse(request.full_url)
        answer = self.routes.get((request.get_method(), parsed.path))
        if answer is None:
            raise HTTPError(
                request.full_url, 404, "nf", {}, io.BytesIO(b'{"code":"rest_no_route"}')
            )
        if callable(answer):
            answer = answer(parse_qs(parsed.query))
        return _Response(answer)

    def paths(self, method):
        return [urlparse(r.full_url).path for r in self.requests if r.get_method() == method]


def _api(site):
    return WordPressApi(
        SiteAddress("https://radio.example"),
        SiteAuth("app_password", "jeff", "abcd efgh ijkl mnop qrst uvwx"),
        opener=site,
        site_name="Community Radio",
    )


EVENT = {"id": 12, "type": "event", "slug": "open-day", "title": {"raw": "Open Day"}}
TYPES = {
    "post": {"rest_base": "posts", "name": "Posts"},
    "page": {"rest_base": "pages", "name": "Pages"},
    "attachment": {"rest_base": "media", "name": "Media"},
    "event": {"rest_base": "events", "name": "Events"},
}


def test_an_opened_event_is_sent_back_to_its_rest_base() -> None:
    site = _Site().on("GET", f"{API}/events/12", EVENT).on("POST", f"{API}/events/12", EVENT)
    api = _api(site)
    item = wp.load_item(api, "events", 12)
    assert item.kind == "events"
    wp.update_item(api, item)
    assert site.paths("POST") == [f"{API}/events/12"]


def test_posts_and_pages_still_take_the_sites_word() -> None:
    assert wp.kind_from_payload({"type": "page"}, "post") == "page"
    assert wp.kind_from_payload({"type": "event"}, "") == "event"
    assert wp.kind_from_payload({}, "events") == "events"
    assert wp.kind_from_payload(None, "post") == "post"


def test_writing_types_leaves_out_posts_pages_and_media() -> None:
    site = _Site().on("GET", f"{API}/types", TYPES)
    assert wp.writing_types(_api(site)) == [("event", "events", "Events")]
    assert wp.list_content_types(_api(site)) == [
        ("post", "Posts"),
        ("page", "Pages"),
        ("events", "Events"),
    ]


def _slug_lookup(found_in):
    def answer(query):
        return [{"id": 12}] if query.get("slug") == ["open-day"] and found_in else []

    return answer


def test_an_event_opens_by_its_pretty_address() -> None:
    site = (
        _Site()
        .on("GET", f"{API}/posts", _slug_lookup(False))
        .on("GET", f"{API}/pages", _slug_lookup(False))
        .on("GET", f"{API}/types", TYPES)
        .on("GET", f"{API}/events", _slug_lookup(True))
    )
    assert find_by_address(_api(site), "https://radio.example/event/open-day/") == ("events", 12)


def test_an_event_opens_by_its_plain_address() -> None:
    site = _Site().on("GET", f"{API}/types", TYPES).on("GET", f"{API}/events", _slug_lookup(True))
    assert find_by_address(_api(site), "https://radio.example/?event=open-day") == ("events", 12)


def test_a_post_address_never_asks_for_the_types() -> None:
    site = _Site().on("GET", f"{API}/posts", _slug_lookup(True))
    assert find_by_address(_api(site), "https://radio.example/2026/open-day/") == ("post", 12)
    assert f"{API}/types" not in site.paths("GET")


def test_nothing_anywhere_is_none() -> None:
    site = (
        _Site()
        .on("GET", f"{API}/posts", _slug_lookup(False))
        .on("GET", f"{API}/pages", _slug_lookup(False))
        .on("GET", f"{API}/types", TYPES)
        .on("GET", f"{API}/events", _slug_lookup(False))
    )
    assert find_by_address(_api(site), "https://radio.example/nowhere/") is None
