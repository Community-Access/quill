"""Custom fields that are lists and groups, and meta on terms, users and comments (WP-R-033)."""

from __future__ import annotations

import json
from urllib.parse import urlparse

import pytest

from quill.core.wordpress import custom_field_shapes as shapes
from quill.core.wordpress import custom_fields as cf
from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi

SPEAKERS = {"type": "array", "title": "Speakers", "items": {"type": "string"}}
SEATS = {"type": "array", "items": {"type": "integer"}}
VENUE = {
    "type": "object",
    "title": "Venue",
    "properties": {
        "street": {"type": "string"},
        "city": {"type": "string"},
        "step_free": {"type": "boolean", "title": "Step-free entrance"},
        "capacity": {"type": "integer"},
    },
    "additionalProperties": True,
}
ROWS = {
    "type": "array",
    "title": "Schedule",
    "items": {
        "type": "object",
        "properties": {"time": {"type": "string"}, "act": {"type": "string"}},
    },
}
GRID = {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}
SCHEMA = {
    "seo_title": {"type": "string"},
    "speakers": SPEAKERS,
    "seats": SEATS,
    "venue": VENUE,
    "schedule": ROWS,
    "grid": GRID,
    "untyped_list": {"type": "array"},
}
ON_SITE = {
    "seo_title": "Fair",
    "speakers": ["Ann", "Bo", "Cy", "Di"],
    "seats": [4, 8],
    "venue": {"street": "1 Main St", "city": "Springfield", "step_free": True, "floor": "2"},
    "schedule": [{"time": "10:00", "act": "Choir"}],
    "grid": [["a", "b"]],
    "untyped_list": [1, "x"],
}


def _form(kept=None):
    return cf.build_form(SCHEMA, ON_SITE, kept or {})


def test_lists_and_groups_become_rows_and_only_the_unsafe_are_left_alone() -> None:
    form = _form()
    assert [f.key for f in form.fields] == ["seo_title"]
    assert [(s.key, s.shape) for s in form.structured] == [
        ("speakers", "list"),
        ("seats", "list"),
        ("venue", "group"),
        ("schedule", "list"),
    ]
    # A list of lists and a list with no items schema stay as the site has them.
    assert form.left_alone == 2
    assert form.types["venue"] == "object" and form.types["speakers"] == "array"


def test_each_row_says_what_it_holds() -> None:
    rows = [shapes.describe(s) for s in _form().structured]
    assert rows[0] == "Speakers, a list of 4 items: Ann; Bo; Cy, and 1 more"
    assert rows[1] == "Seats, a list of 2 items: 4; 8"
    assert rows[2] == (
        "Venue, a group: Street 1 Main St, City Springfield, Step-free entrance yes, Floor 2"
    )
    assert rows[3] == "Schedule, a list of 1 item: Time 10:00, Act Choir"
    empty = shapes.StructuredField("s", "&Speakers:", "", "list", SPEAKERS, [])
    assert shapes.describe(empty) == "Speakers, an empty list"


def test_kept_values_win_over_the_sites() -> None:
    form = _form({"speakers": ["Eve"]})
    assert form.structured[0].value == ["Eve"]
    assert form.site_values["speakers"] == ["Ann", "Bo", "Cy", "Di"]


def test_list_edits_are_pure_and_say_where_the_row_went() -> None:
    values = ["Ann", "Bo", "Cy"]
    assert shapes.add_item(values, "Dee") == (["Ann", "Bo", "Cy", "Dee"], 3)
    assert shapes.add_item(values, "Dee", at=0) == (["Ann", "Dee", "Bo", "Cy"], 1)
    assert shapes.remove_item(values, 2) == (["Ann", "Bo"], 1)
    assert shapes.remove_item(["Ann"], 0) == ([], None)
    assert shapes.move_item(values, 0, 1) == (["Bo", "Ann", "Cy"], 1)
    assert shapes.move_item(values, 2, -1) == (["Ann", "Cy", "Bo"], 1)
    # At an end it stays put; the caller says so.
    assert shapes.move_item(values, 0, -1) == (values, 0)
    assert shapes.move_item(values, 2, 1) == (values, 2)
    assert values == ["Ann", "Bo", "Cy"]


def test_typed_values_go_back_in_the_schemas_types() -> None:
    form = _form()
    changed, value = cf.structured_change(form, "seats", ["4", "10"])
    assert changed and value == [4, 10]
    with pytest.raises(cf.FieldValueError, match="Seats"):
        cf.structured_change(form, "seats", ["four"])
    unchanged, value = cf.structured_change(form, "seats", [4, 8])
    assert not unchanged and value == [4, 8]


def test_a_group_keeps_keys_its_schema_does_not_name() -> None:
    form = _form()
    venue = form.structured[2]
    fields = shapes.group_fields(venue.schema, venue.value)
    assert [f.key for f in fields] == ["street", "city", "step_free", "capacity"]
    assert [f.kind for f in fields] == ["text", "text", "check", "text"]
    assert fields[0].value == "1 Main St" and fields[2].value is True
    assert len({f.label.split("&")[1][0].lower() for f in fields}) == 4
    answers = {"street": "2 Elm St", "city": "Springfield", "step_free": False, "capacity": "120"}
    after = shapes.apply_group(venue.schema, venue.value, answers, "Venue")
    assert after == {
        "street": "2 Elm St",
        "city": "Springfield",
        "step_free": False,
        "capacity": 120,
        "floor": "2",
    }
    with pytest.raises(cf.FieldValueError, match="Venue, Capacity"):
        shapes.apply_group(venue.schema, venue.value, {"capacity": "lots"}, "Venue")


def test_a_round_trip_with_nothing_edited_changes_nothing() -> None:
    form = _form()
    for sf in form.structured:
        changed, value = cf.structured_change(form, sf.key, sf.value)
        assert not changed, sf.key
        assert value == ON_SITE[sf.key]
    assert cf.structured_change(form, "nonesuch", 1) == (False, 1)


def test_blank_items_have_the_right_type() -> None:
    assert shapes.blank({"type": "string"}) == ""
    assert shapes.blank({"type": "integer"}) == 0
    assert shapes.blank({"type": "boolean"}) is False
    assert shapes.blank({"type": "string", "enum": ["a", "b"]}) == "a"
    assert shapes.blank({"type": "string", "default": "x"}) == "x"
    assert shapes.blank(ROWS["items"]) == {"time": "", "act": ""}
    assert shapes.blank(SPEAKERS) == []


def test_coerce_reads_what_a_person_types() -> None:
    assert shapes.coerce({"type": "boolean"}, "Yes") is True
    assert shapes.coerce({"type": "boolean"}, "no") is False
    assert shapes.coerce({"type": "number"}, " 2.5 ") == 2.5
    assert shapes.coerce({"type": ["integer", "null"]}, "") is None
    assert shapes.coerce({"type": "integer"}, 3.0) == 3
    assert shapes.coerce({"type": "string"}, None) == ""
    assert shapes.coerce(SPEAKERS, "") == []
    # A value of an unexpected shape is handed back rather than invented.
    assert shapes.coerce(VENUE, ["not", "a", "group"]) == ["not", "a", "group"]


def test_merge_kept_replaces_only_the_page_shown() -> None:
    form = _form()
    kept = {"seo_title": "Old answer", "speakers": ["Eve"]}
    assert cf.merge_kept(kept, form, {}) == {"speakers": ["Eve"]}
    assert cf.merge_kept(kept, form, {"seo_title": "New"}) == {
        "speakers": ["Eve"],
        "seo_title": "New",
    }
    assert cf.merge_kept(kept, form, {}, keys=["speakers"]) == {"seo_title": "Old answer"}


# --------------------------------------------------------------------------- #
# meta on terms, users and comments


class _Opener:
    def __init__(self, answers):
        self.answers = answers
        self.seen = []

    def __call__(self, request, timeout=None, context=None):
        path = urlparse(request.full_url).path.removeprefix("/wp-json/")
        self.seen.append((request.get_method(), path, request.data))
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


def test_routes_for_every_object_that_carries_meta() -> None:
    assert cf.object_route(None, "post", "tribe_events") == "wp/v2/tribe_events"
    assert cf.object_route(None, "post") == "wp/v2/posts"
    assert cf.object_route(None, "term", "post_tag") == "wp/v2/tags"
    assert cf.object_route(None, "user") == "wp/v2/users"
    assert cf.object_route(None, "comment") == "wp/v2/comments"
    assert set(cf.OBJECT_TYPES) == {"post", "term", "user", "comment"}


@pytest.mark.parametrize(
    ("object_type", "subtype", "route"),
    [
        ("term", "category", "wp/v2/categories"),
        ("user", "", "wp/v2/users"),
        ("comment", "", "wp/v2/comments"),
    ],
)
def test_meta_on_other_objects_reads_and_writes_the_same_way(object_type, subtype, route) -> None:
    opener = _Opener({
        ("OPTIONS", route): {"schema": {"properties": {"meta": {"properties": SCHEMA}}}},
        ("GET", f"{route}/7"): {"meta": ON_SITE},
        ("POST", f"{route}/7"): {"id": 7, "meta": ON_SITE},
    })
    api = _api(opener)
    where = cf.object_route(api, object_type, subtype)
    assert where == route
    form = cf.build_form(cf.meta_schema_for(api, where), cf.site_values_for(api, where, 7), {})
    assert [s.key for s in form.structured] == ["speakers", "seats", "venue", "schedule"]
    cf.send_meta(api, where, 7, {"speakers": ["Eve"]})
    method, path, data = opener.seen[-1]
    assert (method, path) == ("POST", f"{route}/7")
    assert json.loads(data) == {"meta": {"speakers": ["Eve"]}}


def test_a_new_object_has_no_values_to_read() -> None:
    assert cf.site_values_for(_api(_Opener({})), "wp/v2/users", 0) == {}
