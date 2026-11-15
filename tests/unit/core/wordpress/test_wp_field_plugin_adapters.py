"""Meta Box, Pods and CMB2 on Properties; lists and groups; the Content Model's evidence.

WP-R-033, WP-R-034, WP-R-036 and WP-R-038. Every answer below is a recorded
shape from each plugin's documented REST exposure (the module docstrings say
which); no live site and no network.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import field_plugins_cmb2 as cmb2
from quill.core.wordpress import field_plugins_more as more
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.field_plugins import plugin_pages
from quill.core.wordpress.workbench_edit import EditRefused, body_for, verify
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.properties import FieldChange, FieldKind, PageSpec, SheetSpec

PODS = {
    "pods": [
        {
            "name": "book",
            "label": "Books",
            "type": "post_type",
            "storage": "meta",
            "rest_enable": "1",
            "write_all": "0",
            "fields": {
                "isbn": {"name": "isbn", "label": "ISBN", "type": "text", "rest_write": "1"},
                "pages": {"name": "pages", "label": "Pages", "type": "number", "rest_write": "1"},
                "printed": {"name": "printed", "type": "boolean", "rest_write": "0"},
                "author_link": {"name": "author_link", "type": "pick", "rest_write": "1"},
                "hidden": {"name": "hidden", "type": "text", "rest_write": "1"},
            },
        },
        {
            "name": "genre",
            "label": "Genres",
            "type": "taxonomy",
            "storage": "table",
            "fields": [{"name": "colour", "type": "color"}],
        },
    ]
}

BOXES = {
    "book_box": {
        "id": "book_box",
        "title": "Book details",
        "object_types": ["book"],
        "show_in_rest": "GET, POST",
    },
    "user_box": {
        "id": "user_box",
        "title": "About you",
        "object_types": ["user"],
        "show_in_rest": "GET",
    },
}

BOOK_FIELDS = {
    "blurb": {"id": "blurb", "name": "Blurb", "type": "textarea", "value": "A story."},
    "format": {
        "id": "format",
        "name": "Format",
        "type": "select",
        "options": {"paper": "Paper", "cloth": "Cloth"},
        "value": "paper",
    },
    "cover": {"id": "cover", "name": "Cover", "type": "file", "value": "x.jpg"},
}


class Api:
    """Answers each plugin's routes as documented; records every write."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, str, Any]] = []
        self.reads: list[str] = []
        self.cmb2: dict[str, Any] = {k: v["value"] for k, v in BOOK_FIELDS.items()}
        self.keep = True

    def get(self, route: str, **params: Any) -> Any:
        self.reads.append(route)
        if route == "pods/v1/pods":
            assert params.get("return_type") == "full"
            return PODS
        if route == "cmb2/v1/boxes":
            return BOXES
        if route == "cmb2/v1/boxes/book_box/fields":
            assert params == {"object_id": 7, "object_type": "post"}
            return {k: {**v, "value": self.cmb2[k]} for k, v in BOOK_FIELDS.items()}
        if route.startswith("cmb2/v1/boxes/book_box/fields/"):
            return {"id": route.rsplit("/", 1)[1], "value": self.cmb2[route.rsplit("/", 1)[1]]}
        if route == "wp/v2/book/7":
            return {"id": 7, "modified_gmt": "2026-11-01T10:00:00"}
        raise WordPressApiError("no route", status=404)

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append(("POST", route, body))
        if route.startswith("cmb2/v1/boxes/book_box/fields/") and self.keep:
            self.cmb2[route.rsplit("/", 1)[1]] = body["value"]
        return dict(body or {})


BOOK = {
    "id": 7,
    "type": "book",
    "isbn": "978-1",
    "pages": "320",
    "printed": True,
    "author_link": [{"id": 3}],
    "meta_box": {
        "venue": "The Hall",
        "seats": 120,
        "tags": ["a", "b"],
        "rows": [],
        "address": {"street": "1 Main", "zip": "12345"},
    },
}


def _base() -> SheetSpec:
    return SheetSpec("item", "Item", (PageSpec("general", "General", ()),))


def _sheet(pages: list[more.PluginPage]) -> tuple[SheetSpec, dict[str, Any], dict[str, Any]]:
    return more.with_pages(_base(), pages)


# -- Meta Box -------------------------------------------------------------------------


def test_meta_box_fields_take_their_kind_from_their_values_and_save_as_meta_box() -> None:
    page = more.metabox_page({}, BOOK)
    assert page is not None and page.title == "Meta Box"
    by_key = {f.key: f for f in page.fields}
    assert by_key["meta_box.seats"].kind is FieldKind.NUMBER
    assert by_key["meta_box.tags"].kind is FieldKind.LIST
    assert by_key["meta_box.address"].kind is FieldKind.MULTILINE  # a group: JSON plus Edit Group
    assert by_key["meta_box.rows"].readonly  # an empty list says nothing about its kind
    assert "does not say what kind" in by_key["meta_box.rows"].help
    assert "taken from the value it holds" in by_key["meta_box.venue"].help
    sheet, values, lookup = _sheet([page])
    assert values["meta_box.venue"] == "The Hall" and "meta_box.rows" not in lookup
    row = WbRow("item", "S", "7", {"title": "Book"}, "", route="wp/v2/book/7", subkind="book")
    body = body_for(
        sheet, row, [FieldChange("meta_box.seats", "Seats", 120, "140")], meta_schema=lookup
    )
    assert body == {"meta_box": {"seats": 140}}
    assert verify(body, {"meta_box": {"seats": "140"}}) == ()
    with pytest.raises(EditRefused):
        body_for(
            sheet, row, [FieldChange("meta_box.seats", "Seats", 120, "many")], meta_schema=lookup
        )


def test_a_described_meta_box_schema_wins_and_no_meta_box_means_no_page() -> None:
    props = {
        "meta_box": {
            "type": "object",
            "properties": {"rating": {"type": "integer", "title": "Rating", "enum": [1, 2, 3]}},
        }
    }
    page = more.metabox_page(props, {"meta_box": {"rating": 2}})
    assert page is not None
    (rating,) = page.fields
    assert rating.kind is FieldKind.CHOICE and rating.choices == ("1", "2", "3")
    assert more.metabox_page({}, {"id": 1}) is None


# -- Pods -----------------------------------------------------------------------------


def test_pods_fields_are_read_from_its_definitions_and_written_where_allowed() -> None:
    api = Api()
    pod = more.pod_for(more.pods_definitions(api) or [], "item", "book")  # type: ignore[arg-type]
    assert pod is not None and pod["label"] == "Books"
    page = more.pods_page(pod, BOOK)
    assert page is not None and page.title == "Pods (Books)"
    by_key = {f.key: f for f in page.fields}
    assert "pods.hidden" not in by_key  # not shown in REST, so not on the item
    assert not by_key["pods.isbn"].readonly and by_key["pods.pages"].kind is FieldKind.NUMBER
    assert by_key["pods.printed"].readonly and "Allow write in REST is off" in (
        by_key["pods.printed"].help
    )
    assert by_key["pods.author_link"].readonly and "pick" in by_key["pods.author_link"].help
    sheet, values, lookup = _sheet([page])
    row = WbRow("item", "S", "7", {"title": "Book"}, "", route="wp/v2/book/7", subkind="book")
    changes = [
        FieldChange("pods.pages", "Pages", "320", "336"),
        FieldChange("pods.isbn", "ISBN", "978-1", "978-2"),
    ]
    body = body_for(sheet, row, changes, meta_schema=lookup)
    assert body == {"pages": 336.0, "isbn": "978-2"}  # top-level REST fields, typed
    assert verify(body, {"pages": "336", "isbn": "978-2"}) == ()  # 336.0 sent, "336" kept
    with pytest.raises(EditRefused, match="read only"):
        body_for(
            sheet, row, [FieldChange("pods.printed", "Printed", True, False)], meta_schema=lookup
        )


def test_pods_without_permission_gives_no_page_rather_than_a_guess() -> None:
    class Refusing(Api):
        def get(self, route: str, **params: Any) -> Any:
            if route == "pods/v1/pods":
                raise WordPressApiError("no", status=403)
            return super().get(route, **params)

    pages = plugin_pages(
        Refusing(),
        row_kind="item",
        slug="book",
        object_id=7,  # type: ignore[arg-type]
        properties={},
        raw={"isbn": "x"},
        namespaces=("wp/v2", "pods/v1"),
    )
    assert pages == []


# -- CMB2 -----------------------------------------------------------------------------


def test_cmb2_boxes_for_the_object_become_one_page_written_field_by_field() -> None:
    api = Api()
    page = cmb2.cmb2_page(api, "item", "book", 7)  # type: ignore[arg-type]
    assert page is not None
    by_key = {f.key: f for f in page.fields}
    assert by_key["cmb2.book_box.format"].choices == ("paper", "cloth")
    assert by_key["cmb2.book_box.cover"].readonly  # a file field has no plain form
    assert "In the box Book details" in by_key["cmb2.book_box.blurb"].help
    sheet, values, lookup = _sheet([page])
    row = WbRow("item", "S", "7", {"title": "Book"}, "", route="wp/v2/book/7", subkind="book")
    body = body_for(
        sheet,
        row,
        [FieldChange("cmb2.book_box.format", "Format", "paper", "cloth")],
        meta_schema=lookup,
    )
    assert body == {"cmb2": {"book_box.format": "cloth"}}
    with pytest.raises(EditRefused):  # not one of the box's options
        body_for(
            sheet,
            row,
            [FieldChange("cmb2.book_box.format", "Format", "paper", "vellum")],
            meta_schema=lookup,
        )
    before = {"cmb2": page.before}
    result = cmb2.save_with_cmb2(api, row, body, before=before)  # type: ignore[arg-type]
    assert api.writes == [
        (
            "POST",
            "cmb2/v1/boxes/book_box/fields/format",
            {"object_id": 7, "object_type": "post", "value": "cloth"},
        )
    ]
    assert result.sentence == "Saved 1 change to Book on S." and not result.not_kept
    assert result.undo == {"cmb2": {"book_box.format": "paper"}}
    api.keep = False  # the site answers, and keeps nothing
    missed = cmb2.save_with_cmb2(api, row, {"cmb2": {"book_box.blurb": "New"}}, before=before)  # type: ignore[arg-type]
    assert missed.not_kept == ("cmb2.book_box.blurb",) and "did not keep" in missed.sentence


def test_a_read_only_box_and_an_object_with_no_box() -> None:
    api = Api()
    assert cmb2.boxes_for(BOXES, "user") == ["user_box"]
    assert cmb2.cmb2_page(api, "item", "post", 7) is None  # type: ignore[arg-type]
    assert cmb2.cmb2_schema({"type": "checkbox"})["enum"] == ["on", ""]
    assert cmb2.cmb2_schema({"type": "text", "repeatable": True})["type"] == "array"
    assert not cmb2._writable(BOXES["user_box"]) and cmb2._writable(BOXES["book_box"])


def test_plugin_pages_ask_only_the_plugins_the_site_has() -> None:
    api = Api()
    pages = plugin_pages(
        api,
        row_kind="item",
        slug="book",
        object_id=7,
        properties={},  # type: ignore[arg-type]
        raw=BOOK,
        namespaces=("wp/v2",),
    )
    assert [p.plugin for p in pages] == ["Meta Box"] and api.reads == []
    pages = plugin_pages(
        api,
        row_kind="item",
        slug="book",
        object_id=7,
        properties={},  # type: ignore[arg-type]
        raw=BOOK,
        namespaces=("wp/v2", "pods/v1", "cmb2/v1"),
    )
    assert [p.plugin for p in pages] == ["Meta Box", "Pods", "CMB2"]


# -- lists and groups (WP-R-033) -------------------------------------------------------


def test_lists_and_groups_get_the_list_window_and_deeper_shapes_keep_json() -> None:
    from quill.core.wordpress.workbench_sheets import _schema_field

    speakers = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "minutes": {"type": "integer"}},
        },
    }
    deep = {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}
    venue = {"type": "object", "properties": {"street": {"type": "string"}}}
    fields = tuple(
        _schema_field(f"meta.{k}", k, v)
        for k, v in (("speakers", speakers), ("deep", deep), ("venue", venue))
    )
    sheet = SheetSpec("item", "Item", (PageSpec("general", "General", fields),))
    found = more.structured_fields(sheet, {"speakers": speakers, "deep": deep, "venue": venue})
    assert set(found) == {"meta.speakers", "meta.venue"}
    assert more.box_value("", speakers) == [] and more.box_value("not json", venue) is None
    assert more.box_value('{"street": "1 Main", "kept": true}', venue) == {
        "street": "1 Main",
        "kept": True,
    }
    assert more.box_value("[]", venue) is None  # a list where a group belongs
    assert more.box_text({"a": 1}) == '{\n "a": 1\n}'


# -- who defines what (WP-R-036, WP-R-038) ---------------------------------------------


def test_provenance_goes_by_evidence_and_says_unknown_otherwise() -> None:
    from quill.core.wordpress.workbench_model_sources import PluginDefinition, provenance

    pods = {"book": PluginDefinition("Pods", "type", "book", "Books", "its pods/v1 routes")}
    found = provenance("book", namespaces=("wp/v2", "pods/v1"), defined=pods)
    assert (found.owner, found.evidence) == ("Pods", "Pods lists it in its pods/v1 routes.")
    found = provenance("event", "acme/v1")
    assert found.owner == "the plugin behind acme/v1" and "acme/v1" in found.evidence
    found = provenance("event", cpt_ui=True)
    assert not found.known and "Custom Post Type UI is active" in found.evidence
    assert provenance("product").owner == "unknown"  # no WooCommerce namespace, no claim


class ModelApi:
    """A site with QUILL Site Types, Pods, CMB2 and ACF, and CPT UI active."""

    def __init__(self) -> None:
        self.writes: list[Any] = []

    def get(self, route: str, **params: Any) -> Any:
        answers: dict[str, Any] = {
            "wp/v2/types": {
                "post": {"name": "Posts", "rest_base": "posts"},
                "book": {
                    "name": "Books",
                    "slug": "book",
                    "rest_base": "book",
                    "hierarchical": False,
                    "supports": {"title": True, "editor": True, "comments": False},
                    "taxonomies": ["genre"],
                    "labels": {"singular_name": "Book"},
                },
                "event": {"name": "Events", "rest_base": "events"},
                "zine": {"name": "Zines", "rest_base": "zine"},
            },
            "wp/v2/taxonomies": {
                "genre": {
                    "name": "Genres",
                    "rest_base": "genre",
                    "types": ["book"],
                    "hierarchical": True,
                }
            },
            "quill-site-types/v1/types": [{"slug": "zine", "name": "Zines"}],
            "quill-site-types/v1/taxonomies": [],
            "quill-site-types/v1/field-groups": [
                {
                    "id": "zine_facts",
                    "title": "Zine facts",
                    "attach": {"post_types": ["zine"]},
                    "fields": [{"name": "issue", "kind": "number"}],
                }
            ],
            "pods/v1/pods": PODS,
            "cmb2/v1/boxes": BOXES,
            "wp/v2/plugins": [
                {"plugin": "custom-post-type-ui/custom-post-type-ui", "status": "active"}
            ],
        }
        return answers.get(route, [])

    def request(self, method: str, route: str, **_kw: Any) -> Any:
        props: dict[str, Any] = {}
        if route == "wp/v2/posts":
            props = {
                "meta": {
                    "type": "object",
                    "properties": {"footnotes": {"type": "string"}, "mood": {"type": "string"}},
                },
                "acf": {"type": "object", "properties": {"venue": {"type": "string"}}},
            }
        if route == "wp/v2/zine":
            props = {"meta": {"type": "object", "properties": {"issue": {"type": "integer"}}}}

        class _R:
            payload = {"schema": {"properties": props}}

        return _R()


def _model() -> dict[str, WbRow]:
    from quill.core.wordpress.workbench_discovered import model_rows

    namespaces = ("wp/v2", "quill-site-types/v1", "pods/v1", "cmb2/v1")
    return {r.key: r for r in model_rows(ModelApi(), "S", namespaces=namespaces)}  # type: ignore[arg-type]


def test_the_content_model_names_owners_by_evidence_and_lists_every_field_group() -> None:
    rows = _model()
    assert rows["book"].cell("registered_by") == "Pods"
    assert "Pods lists it in its pods/v1 routes" in rows["book"].detail
    assert rows["event"].cell("registered_by") == "unknown"
    assert "Custom Post Type UI is active here" in rows["event"].detail
    assert rows["zine"].cell("registered_by") == "QUILL Site Types"
    assert rows["meta:post"].cell("registered_by") == "unknown"
    assert "mood" in rows["meta:post"].detail and "footnotes" not in rows["meta:post"].detail
    assert rows["core-meta:post"].cell("registered_by") == "WordPress"
    assert rows["acf:post"].cell("registered_by") == "Advanced Custom Fields"
    assert "meta:zine" not in rows  # its one key is QUILL Site Types' own field
    assert rows["pods:book"].cell("kind") == "field group"
    assert rows["cmb2:book_box"].cell("registered_by") == "CMB2"
    assert "table of its own" in rows["pods:genre"].detail and not rows["pods:genre"].raw["movable"]
    assert all(
        r.cell("definition") == "Read only"
        for k, r in rows.items()
        if k not in ("zine", "zine_facts")
    )


def test_a_definition_is_offered_as_a_copy_and_never_a_delete() -> None:
    from quill.core.wordpress.workbench_model_move import move_preview

    rows = _model()
    assert rows["post"].raw["movable"] is None and rows["zine"].raw["movable"] is None
    book = rows["book"].raw["movable"]
    assert book["body"] == {
        "slug": "book",
        "name": "Books",
        "singular_name": "Book",
        "description": "",
        "hierarchical": False,
        "has_archive": False,
        "taxonomies": ["genre"],
        "supports": ["title", "editor"],
        "labels": {"singular_name": "Book"},
    }
    summary, lines = move_preview("S", "type", book["body"], "Pods", book["skipped"])
    assert "Nothing is removed from Pods" in summary and "turn it off in Pods first" in summary
    assert lines[0] == "Post type: Books (book)"
    genre = rows["genre"].raw["movable"]["body"]
    assert genre["object_types"] == ["book"] and genre["hierarchical"] is True
    acf = rows["acf:post"].raw["movable"]
    assert acf["body"]["id"] == "acf_post" and acf["body"]["attach"]["post_types"] == ["post"]
    assert acf["body"]["fields"] == [
        {
            "name": "venue",
            "label": "Venue",
            "kind": "text",
            "help": "",
            "required": False,
            "choices": [],
        }
    ]
    summary, _lines = move_preview("S", "field_group", acf["body"], "Advanced Custom Fields", [])
    assert "Values already saved under these field names stay" in summary
    pods = rows["pods:book"].raw["movable"]["body"]
    kinds = {f["name"]: f["kind"] for f in pods["fields"]}
    assert kinds["printed"] == "true_false" and kinds["author_link"] == "related_item"


def test_a_field_name_quill_site_types_cannot_hold_is_named_not_dropped() -> None:
    from quill.core.wordpress.workbench_model_move import kind_for, move_body

    body, skipped = move_body(
        "field_group",
        "x",
        {
            "key": "meta_box:post",
            "name": "MB",
            "fields": [{"name": "Venue"}, {"name": "_secret"}, {"name": "ok"}],
            "attach": ["taxonomy:genre", "user", "term"],
        },
    )
    assert [f["name"] for f in body["fields"]] == ["ok"]
    assert len(skipped) == 3 and "term" in skipped[-1]
    assert body["attach"] == {
        "post_types": [],
        "taxonomies": ["genre"],
        "users": True,
        "comments": False,
    }
    assert kind_for({"type": "array", "items": {"type": "string", "enum": ["a"]}}) == "choices"
    assert kind_for({"type": "string", "format": "email"}) == "email"
