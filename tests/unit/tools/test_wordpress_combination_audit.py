"""The combination test (WP-R-030) over the test site's recorded REST index."""

from __future__ import annotations

import copy

import pytest

from quill.core.wordpress import query
from quill.tools import wordpress_combination_audit as audit

INDEX = audit.load_index()


def test_the_recorded_index_is_the_whole_test_site() -> None:
    wp_routes = [p for p, r in INDEX["routes"].items() if r["namespace"] == "wp/v2"]
    assert len(INDEX["routes"]) == 802 and len(wp_routes) == 150
    assert len(INDEX["namespaces"]) == 27


def test_every_argument_value_property_and_method_is_covered_or_planned() -> None:
    new, stale = audit.problems()
    assert new == [], (
        "New gaps in the WordPress combinations. Cover them (query.ATTRIBUTES, "
        "query.VALUE_LABELS, audit.field_kind), or classify them with "
        "python -m quill.tools.wordpress_combination_audit --write"
    )
    assert stale == [], "Covered now: regenerate the snapshot so it shrinks"


def test_the_planned_list_only_names_real_gaps() -> None:
    planned = audit.load_snapshot()
    assert all(v.startswith(f"{audit.PLANNED}: ") for v in planned.values())
    assert set(planned) == set(audit.gaps())


def test_the_arguments_jeff_asked_for_are_known_by_name() -> None:
    posts = next(
        args
        for methods, args in audit._endpoints(INDEX["routes"]["/wp/v2/posts"])
        if "GET" in methods
    )
    for name in (
        "tax_relation",
        "categories_exclude",
        "tags_exclude",
        "modified_after",
        "modified_before",
        "search_columns",
        "search_semantics",
        "ignore_sticky",
        "before",
        "after",
    ):
        assert query.classify_arg(name, posts[name]) == "known", name


def test_plugin_taxonomies_are_found_and_filterable_by_rule() -> None:
    bases = audit.taxonomy_bases(INDEX)
    for base in ("categories", "tags", "product_cat", "product_tag", "tribe_events_cat"):
        assert base in bases
    product = next(
        args
        for methods, args in audit._endpoints(INDEX["routes"]["/wp/v2/product"])
        if "GET" in methods
    )
    table = query.attributes_for_route(product, bases)
    assert table["product_cat"].kind == "terms"
    assert table["product_cat"].exclude == "product_cat_exclude"


def test_every_plugin_status_is_offered_on_posts() -> None:
    posts = next(
        args
        for methods, args in audit._endpoints(INDEX["routes"]["/wp/v2/posts"])
        if "GET" in methods
    )
    offered = query.attributes_for_route(posts)["status"].values
    for status in ("wc-processing", "tribe-ea-success", "request-pending", "any"):
        assert status in offered


def _with(route_args: dict, method: str = "GET") -> dict:
    fake = copy.deepcopy(INDEX)
    route = fake["routes"]["/wp/v2/posts"]
    for ep in route["endpoints"]:
        if method in ep["methods"]:
            ep["args"].update(route_args)
    return fake


def test_a_new_argument_value_or_property_is_named() -> None:
    fake = _with({"mood": {}, "orderby": {"type": "string", "enum": ["date", "vibes"]}})
    found = audit.gaps(fake)
    assert found["GET /wp/v2/posts ?mood"] == "missing"
    assert found["GET ?orderby=vibes"] == "value has no spoken label"
    new, _stale = audit.problems(found, {k: "" for k in audit.gaps()})
    assert "GET /wp/v2/posts ?mood" in new
    fake = _with({"colour": {"type": "string"}})
    assert audit.gaps(fake)["GET /wp/v2/posts ?colour"] == "schema_built"
    fake = _with({"shape": {}}, method="POST")
    assert audit.gaps(fake)["POST /wp/v2/posts .shape"] == "no field type"


def test_a_method_with_no_action_is_named() -> None:
    fake = copy.deepcopy(INDEX)
    fake["routes"]["/wp/v2/posts"]["endpoints"].append({"methods": ["PROPFIND"], "args": {}})
    assert audit.gaps(fake)["PROPFIND /wp/v2/posts"] == "no action for this method"


def test_a_covered_gap_must_leave_the_snapshot() -> None:
    _new, stale = audit.problems({}, {"GET ?orderby=price": "value has no spoken label"})
    assert stale == ["GET ?orderby=price"]


@pytest.mark.parametrize(
    ("schema", "kind"),
    [
        ({"type": "string"}, "text"),
        ({"type": ["string", "null"], "format": "date-time"}, "date"),
        ({"type": "string", "enum": ["a"]}, "choice"),
        ({"type": "boolean"}, "check"),
        ({"type": "integer"}, "number"),
        ({"type": "array", "items": {"type": "integer"}}, "ids"),
        ({"type": "array", "items": {"type": "string"}}, "list"),
        ({"type": "array", "items": {"type": "string", "enum": ["a"]}}, "choices"),
        ({"type": "object"}, "group"),
        ({"type": ["object", "string"]}, "group"),
        ({}, ""),
    ],
)
def test_field_kinds(schema, kind) -> None:
    assert audit.field_kind(schema) == kind


def test_the_command_line_passes_and_says_how_many(capsys) -> None:
    assert audit.main([]) == 0
    assert "planned gap(s), nothing new" in capsys.readouterr().out
