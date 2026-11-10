"""The query builder: every collection argument as a filter (WP-R-030 groundwork)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from quill.core.wordpress import query as q
from quill.core.wordpress.api import _query

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def _build(*conditions, **kw):
    return q.build(conditions, now=NOW, **kw)


def test_terms_any_all_and_none_of() -> None:
    assert _build(q.Condition("categories", "is any of", [3, "4"])) == {"categories": [3, 4]}
    assert _build(q.Condition("categories", "is none of", [5])) == {"categories_exclude": [5]}
    assert _build(q.Condition("tags", "is all of", [1, 2])) == {
        "tags[terms]": [1, 2],
        "tags[operator]": "AND",
    }
    with_children = _build(q.Condition("categories", "is any of", [3], include_children=True))
    assert with_children == {
        "categories[terms]": [3],
        "categories[operator]": "OR",
        "categories[include_children]": True,
    }


def test_two_taxonomies_send_tax_relation() -> None:
    both = [q.Condition("categories", "is any of", [3]), q.Condition("tags", "is any of", [7])]
    assert _build(*both)["tax_relation"] == "AND"
    assert _build(*both, taxonomies_match="any")["tax_relation"] == "OR"
    assert "tax_relation" not in _build(both[0])
    # An explicit row wins over the default.
    explicit = _build(*both, q.Condition("tax_relation", "is", "OR"))
    assert explicit["tax_relation"] == "OR"
    with pytest.raises(q.QueryError):
        _build(*both, taxonomies_match="some")


def test_dates_before_after_between_and_lately() -> None:
    assert _build(q.Condition("after", "after", "2026-01-01T00:00:00")) == {
        "after": "2026-01-01T00:00:00"
    }
    assert _build(q.Condition("after", "before", datetime(2026, 2, 1, tzinfo=UTC))) == {
        "before": "2026-02-01T00:00:00"
    }
    assert _build(q.Condition("modified_after", "between", ("2026-01-01", "2026-02-01"))) == {
        "modified_after": "2026-01-01",
        "modified_before": "2026-02-01",
    }
    assert _build(q.Condition("modified_before", "after", "2026-03-01")) == {
        "modified_after": "2026-03-01"
    }
    assert _build(q.Condition("modified_after", "in the last days", 7)) == {
        "modified_after": "2026-11-02T12:00:00"
    }
    with pytest.raises(q.QueryError, match="needs a date"):
        _build(q.Condition("after", "after", ""))


def test_search_columns_semantics_and_sticky() -> None:
    params = _build(
        q.Condition("search", "contains", "  open mic "),
        q.Condition("search_columns", "is any of", ["post_title", "post_excerpt"]),
        q.Condition("search_semantics", "is", "exact"),
        q.Condition("ignore_sticky", "is", True),
        q.Condition("sticky", "is not", True),
    )
    assert params == {
        "search": "open mic",
        "search_columns": ["post_title", "post_excerpt"],
        "search_semantics": "exact",
        "ignore_sticky": True,
        "sticky": False,
    }
    with pytest.raises(q.QueryError, match="Search in cannot be post_name"):
        _build(q.Condition("search_columns", "is any of", ["post_name"]))


def test_ids_with_and_without_an_exclude_partner() -> None:
    assert _build(q.Condition("author", "is none of", [2])) == {"author_exclude": [2]}
    assert _build(q.Condition("author_exclude", "is any of", [2])) == {"author_exclude": [2]}
    with pytest.raises(q.QueryError, match="On the post cannot"):
        _build(q.Condition("post", "is none of", [2]))
    with pytest.raises(q.QueryError, match="needs ids"):
        _build(q.Condition("author", "is any of", ["Jeff"]))


def test_unknown_attributes_and_operators_are_plain_sentences() -> None:
    with pytest.raises(q.QueryError, match="cannot be filtered by colour"):
        _build(q.Condition("colour", "is", "red"))
    with pytest.raises(q.QueryError, match="Sticky cannot be filtered with 'contains'"):
        _build(q.Condition("sticky", "contains", "x"))
    assert q.QueryError.code == "QUILL-WP-QUERY-UNUSABLE"


def test_a_routes_own_enums_and_taxonomies_are_accepted() -> None:
    args = {
        "status": {"type": "array", "items": {"type": "string", "enum": ["publish", "wc-pending"]}},
        "orderby": {"type": "string", "enum": ["date", "price"]},
        "product_cat": {"type": ["object", "array"]},
        "product_cat_exclude": {"type": ["object", "array"]},
        "per_page": {"type": "integer"},
        "brand_color": {"type": "string"},
    }
    table = q.attributes_for_route(args, taxonomy_bases=["product_cat"])
    assert "wc-pending" in table["status"].values and "publish" in table["status"].values
    assert "price" in table["orderby"].values
    assert table["product_cat"].kind == "terms"
    assert table["product_cat"].exclude == "product_cat_exclude"
    assert "per_page" not in table and "product_cat_exclude" not in table
    assert table["brand_color"].schema_built and table["brand_color"].kind == "text"
    params = q.build(
        [
            q.Condition("status", "is any of", ["wc-pending"]),
            q.Condition("product_cat", "is none of", [9]),
            q.Condition("orderby", "is", "price"),
        ],
        attributes=table,
    )
    assert params == {"status": ["wc-pending"], "product_cat_exclude": [9], "orderby": "price"}
    # Without the route's table, the plugin's values are not offered.
    with pytest.raises(q.QueryError):
        _build(q.Condition("orderby", "is", "price"))


def test_parameters_go_on_the_wire_as_wordpress_reads_them() -> None:
    params = _build(
        q.Condition("tags", "is all of", [1, 2]),
        q.Condition("categories", "is any of", [3]),
        q.Condition("ignore_sticky", "is", True),
    )
    wire = _query(params)
    assert "tags%5Bterms%5D=1%2C2" in wire
    assert "tags%5Boperator%5D=AND" in wire
    assert "categories=3" in wire and "tax_relation=AND" in wire
    assert "ignore_sticky=true" in wire


@pytest.mark.parametrize(
    ("schema", "kind"),
    [
        ({"type": "string"}, "text"),
        ({"type": "string", "format": "date-time"}, "date"),
        ({"type": "string", "enum": ["a"]}, "choice"),
        ({"type": "array", "items": {"type": "integer"}}, "ids"),
        ({"type": "array", "items": {"type": "string"}}, "slugs"),
        ({"type": "array", "items": {"type": "string", "enum": ["a"]}}, "choices"),
        ({"type": ["object", "array"]}, "terms"),
        ({"type": "boolean"}, "boolean"),
        ({"type": ["boolean", "array"]}, "ids"),
        ({"type": "integer"}, "number"),
        ({}, ""),
    ],
)
def test_kinds_follow_the_schema(schema, kind) -> None:
    assert q.kind_for_schema(schema) == kind


def test_every_kind_offers_operators() -> None:
    for attr in q.ATTRIBUTES.values():
        assert attr.operators, attr.name
        assert attr.label and attr.help, attr.name


def test_classify_arg() -> None:
    assert q.classify_arg("per_page", {"type": "integer"}) == "paging"
    assert q.classify_arg("tax_relation", {"type": "string"}) == "known"
    assert q.classify_arg("categories_exclude", {"type": ["object", "array"]}) == "known"
    assert q.classify_arg("genre", {"type": ["object", "array"]}, ["genre"]) == "taxonomy"
    assert q.classify_arg("genre_exclude", {"type": ["object", "array"]}, ["genre"]) == "taxonomy"
    assert q.classify_arg("colour", {"type": "string"}) == "schema_built"
    assert q.classify_arg("mystery", {}) == "missing"


def test_values_are_said_in_words_where_wordpress_uses_code() -> None:
    assert q.value_label("orderby", "modified") == "Date changed"
    assert q.value_label("tax_relation", "OR") == "Any of these"
    assert q.value_label("orderby", "price") == "price"
    assert "status" in q.SITE_LABELLED
