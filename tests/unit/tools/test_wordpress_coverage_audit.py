"""The coverage gate (WordPress PRD 12) over the test site's recorded REST index."""

from __future__ import annotations

from quill.core.wordpress.workbench_coverage import (
    STATUSES,
    classify,
    coverage_table,
    namespace_of,
)
from quill.tools import wordpress_coverage_audit as audit


def test_every_recorded_route_is_classified_and_the_snapshot_matches() -> None:
    found = audit.current()
    assert len(found) == 802
    assert set(found.values()) <= set(STATUSES)
    assert audit.problems() == [], (
        "Routes moved or appeared: run python -m quill.tools.wordpress_coverage_audit --write "
        "and read the diff"
    )


def test_a_new_route_is_missing_until_reviewed() -> None:
    found = {**audit.current(), "/acme/v1/widgets": "schema_built"}
    said = audit.problems(found)
    assert said == ["missing: /acme/v1/widgets (schema_built), not yet reviewed"]
    moved = dict(audit.current())
    moved["/wp/v2/posts"] = "planned"
    assert any(line.startswith("changed: /wp/v2/posts") for line in audit.problems(moved))


def test_the_rules_put_routes_where_a_person_finds_them() -> None:
    assert classify("/wp/v2/posts").status == "covered"
    assert classify("/wp/v2/tribe_events").status == "schema_built"
    assert classify("/wc/store/v1/cart").status == "out_of_scope"
    assert classify("/wc/v3/orders").status == "planned"
    assert classify("/jetpack/v4/connection").status == "wp_admin_only"
    assert classify("/acme/v1/widgets", ["GET"]).status == "schema_built"
    assert classify("/acme/v1/sync", ["POST"]).status == "wp_admin_only"


def test_namespaces_and_the_shared_engine_table() -> None:
    names = ["wp/v2", "wc/store", "wc/store/v1"]
    assert namespace_of("/wc/store/v1/cart", names) == "wc/store/v1"
    assert namespace_of("/wp/v2/posts", names) == "wp/v2"
    table = coverage_table({"/wp/v2/posts": classify("/wp/v2/posts")})
    assert "1 built" in table.summary()
