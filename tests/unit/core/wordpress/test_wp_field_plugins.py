"""Advanced Custom Fields' ``acf`` REST field, read behind detection (WP-R-034)."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

from quill.core.wordpress import field_plugins as fp
from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi

ACF_PROPS = {
    "title": {"type": "object"},
    "acf": {
        "type": "object",
        "properties": {
            "venue_name": {"type": ["string", "null"], "description": "Where it happens"},
            "doors_open": {"type": ["string", "null"]},
            "accessible": {"type": ["boolean", "null"], "title": "Step-free"},
            "performers": {"type": ["array", "null"], "items": {"type": "string"}},
            "map_link": {"type": ["object", "null"]},
        },
    },
}


class _Opener:
    def __init__(self, answers):
        self.answers = answers
        self.seen = []

    def __call__(self, request, timeout=None, context=None):
        parsed = urlparse(request.full_url)
        path = parsed.path.removeprefix("/wp-json/")
        self.seen.append((request.get_method(), path, parse_qs(parsed.query)))
        body = json.dumps(self.answers[(request.get_method(), path)]).encode()

        class R:
            status = 200
            headers: dict = {}

            def read(self):
                return body

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

        return R()


def _api(opener):
    return WordPressApi(SiteAddress("https://radio.example"), SiteAuth("none"), opener=opener)


def test_acf_fields_are_read_when_the_schema_shows_them() -> None:
    opener = _Opener({
        ("OPTIONS", "wp/v2/tribe_events"): {"schema": {"properties": ACF_PROPS}},
        ("GET", "wp/v2/tribe_events/12"): {
            "acf": {"venue_name": "The Hall", "accessible": True, "performers": ["Ann"]},
        },
    })
    found = fp.read_acf(_api(opener), "wp/v2/tribe_events", 12)
    assert found is not None and found.plugin == "Advanced Custom Fields"
    assert [f.key for f in found.form.fields] == ["venue_name", "doors_open", "accessible"]
    assert found.form.fields[0].value == "The Hall"
    assert [s.key for s in found.form.structured] == ["performers"]
    # An object with no properties schema is left as the site has it.
    assert found.form.left_alone == 1
    assert found.count == 4
    query = opener.seen[-1][2]
    assert query["_fields"] == ["acf"] and query["context"] == ["edit"]


def test_no_acf_property_means_no_acf_and_no_second_request() -> None:
    opener = _Opener({("OPTIONS", "wp/v2/posts"): {"schema": {"properties": {"meta": {}}}}})
    assert fp.read_acf(_api(opener), "wp/v2/posts", 3) is None
    assert len(opener.seen) == 1


def test_known_properties_save_the_options_request() -> None:
    opener = _Opener({("GET", "wp/v2/pages/5"): {"acf": []}})
    found = fp.read_acf(_api(opener), "wp/v2/pages", 5, properties=ACF_PROPS)
    assert found is not None and found.values == {}
    assert [m for m, _p, _q in opener.seen] == ["GET"]


def test_a_new_item_or_an_empty_group_asks_nothing_more() -> None:
    opener = _Opener({})
    found = fp.read_acf(_api(opener), "wp/v2/pages", 0, properties=ACF_PROPS)
    assert found is not None and found.values == {} and opener.seen == []
    empty = fp.read_acf(_api(opener), "wp/v2/pages", 5, properties={"acf": {"type": "object"}})
    assert empty is not None and empty.count == 0 and opener.seen == []


def test_detection_reads_only_an_object_property() -> None:
    assert fp.acf_schema({}) is None
    assert fp.acf_schema({"acf": "nope"}) is None
    assert fp.acf_schema({"acf": {"properties": {"a": {"type": "string"}, "b": 1}}}) == {
        "a": {"type": "string"}
    }
