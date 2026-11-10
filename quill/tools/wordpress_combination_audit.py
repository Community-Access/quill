"""The combination test (WP-R-030): every route argument a filter, every property a field.

The WordPress PRD (12a) turns each route of a site's REST index into the
interface by rule: each GET argument of a collection becomes a Filter Builder
attribute, each value of its ``enum`` is offered, and each writable property
becomes a field of the Properties sheet. This gate holds QUILL to that over
the test site's recorded index
(``tests/unit/core/wordpress/fixtures/rest_index_test_site.json``, 150
``wp/v2`` routes), so when WordPress or a plugin adds an argument the gate
names it.

Every ``wp/v2`` argument is checked:

* **Collection GET arguments** go through
  :func:`quill.core.wordpress.query.classify_arg`: ``paging`` (page,
  per_page, context), ``known`` (a row of the attribute table, with its label
  and help), ``taxonomy`` (a taxonomy's ``rest_base``, by rule) and
  ``schema_built`` (works, with the operator its type implies, but has no
  label of its own yet) or ``missing`` (no usable type).
* **Enum values** of those arguments must all be among the values the
  route's attribute offers (:func:`quill.core.wordpress.query.attributes_for_route`).
* **Writable properties** (the arguments of POST, PUT and PATCH) must map to
  a field kind by :func:`field_kind`.
* **Every value is said in words**: an enum value with no spoken label in
  :data:`quill.core.wordpress.query.VALUE_LABELS` is a gap, except for the
  arguments whose values the site names itself (statuses, post types).
* **Every method** is one of the five the action table turns into commands.

Anything that is not plainly covered is a **gap**. Today's gaps are committed
in ``tests/unit/core/wordpress/fixtures/route_combinations.json``, each
classified ``planned``, and the list may only shrink: a new gap fails (classify
it, or better, cover it), and a gap that is no longer one fails until it is
removed, so the snapshot never claims work that is done.

Run ``python -m quill.tools.wordpress_combination_audit`` to check and
``--write`` to regenerate the snapshot (then read the diff).

Which routes are taxonomies is not in the index, so it is read the way
WordPress shapes them: a ``wp/v2`` collection whose GET takes ``hide_empty``
is a taxonomy's terms, and its last path segment is the ``rest_base``.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from quill.core.wordpress import query

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO_ROOT / "tests" / "unit" / "core" / "wordpress" / "fixtures"
INDEX_PATH = _FIXTURES / "rest_index_test_site.json"
SNAPSHOT_PATH = _FIXTURES / "route_combinations.json"

PLANNED = "planned"
COVERED_ARG_STATES = frozenset({"paging", "known", "taxonomy"})
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH"})
#: Every method becomes an action by rule (12a): GET a list or Open, POST New or
#: OK, PUT and PATCH OK and Apply, DELETE Delete (Trash where the type has one).
ACTION_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

__all__ = [
    "INDEX_PATH",
    "PLANNED",
    "SNAPSHOT_PATH",
    "field_kind",
    "gaps",
    "load_index",
    "load_snapshot",
    "main",
    "problems",
    "taxonomy_bases",
]


def field_kind(schema: Mapping[str, Any]) -> str:
    """The Properties sheet control a writable property's schema implies, or ``""``.

    Strings are text boxes (dates are date boxes), ``enum`` a list, booleans
    check boxes, integers and numbers number boxes, lists of ids pickers,
    other lists a list with Add and Remove, and objects a group (12a).
    """
    kind = schema.get("type")
    kinds = set(kind) if isinstance(kind, list) else {kind}
    kinds.discard("null")
    items = schema.get("items") if isinstance(schema.get("items"), dict) else {}
    if schema.get("enum"):
        return "choice"
    if "object" in kinds:
        return "group"
    if "array" in kinds:
        item_type = (items or {}).get("type")
        if (items or {}).get("enum"):
            return "choices"
        return "ids" if item_type == "integer" else "list"
    if "boolean" in kinds:
        return "check"
    if kinds & {"integer", "number"}:
        return "number"
    if "string" in kinds:
        return "date" if schema.get("format") == "date-time" else "text"
    return ""


def load_index(path: Path = INDEX_PATH) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _wp_routes(index: Mapping[str, Any]) -> Iterator[tuple[str, Mapping[str, Any]]]:
    routes = index.get("routes")
    for path, route in sorted((routes or {}).items()):
        if isinstance(route, dict) and route.get("namespace") == "wp/v2":
            yield path, route


def _endpoints(route: Mapping[str, Any]) -> Iterator[tuple[set[str], dict[str, Any]]]:
    for ep in route.get("endpoints") or []:
        if isinstance(ep, dict):
            args = ep.get("args")
            yield set(ep.get("methods") or []), dict(args) if isinstance(args, dict) else {}


def _is_collection_get(methods: set[str], args: Mapping[str, Any]) -> bool:
    return "GET" in methods and "per_page" in args


def taxonomy_bases(index: Mapping[str, Any]) -> list[str]:
    """The ``rest_base`` of every taxonomy in the index (collections that take ``hide_empty``)."""
    found: list[str] = []
    for path, route in _wp_routes(index):
        for methods, args in _endpoints(route):
            if _is_collection_get(methods, args) and "hide_empty" in args and "(?P" not in path:
                found.append(path.rstrip("/").rsplit("/", 1)[-1])
    return sorted(set(found))


def gaps(index: Mapping[str, Any] | None = None) -> dict[str, str]:
    """``key -> what is missing`` for everything the index offers that QUILL does not cover.

    Keys are ``GET <route> ?<argument>``, ``GET <route> ?<argument>=<value>``
    and ``<METHOD> <route> .<property>``.
    """
    found_index = load_index() if index is None else index
    bases = taxonomy_bases(found_index)
    out: dict[str, str] = {}
    for path, route in _wp_routes(found_index):
        for methods, args in _endpoints(route):
            if _is_collection_get(methods, args):
                table = query.attributes_for_route(args, bases)
                for name, schema in sorted(args.items()):
                    state = query.classify_arg(name, schema, bases)
                    if state not in COVERED_ARG_STATES:
                        out[f"GET {path} ?{name}"] = state
                    attr = query.attribute_for(name, schema, bases)
                    offered = table[attr.name].values if attr and attr.name in table else ()
                    for value in query.enum_values(schema):
                        if name not in query.PAGING and value not in offered:
                            out[f"GET {path} ?{name}={value}"] = "value not offered"
                        labelled = name in query.SITE_LABELLED or name in query.PAGING
                        if not labelled and query.value_label(name, value) == value:
                            # One row per argument and value, not per route.
                            out[f"GET ?{name}={value}"] = "value has no spoken label"
            for method in sorted(methods - ACTION_METHODS):
                out[f"{method} {path}"] = "no action for this method"
            for method in sorted(methods & WRITE_METHODS):
                for name, schema in sorted(args.items()):
                    if not field_kind(schema):
                        out[f"{method} {path} .{name}"] = "no field type"
    return out


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    entries = raw.get("gaps") if isinstance(raw, dict) else None
    return {str(k): str(v) for k, v in entries.items()} if isinstance(entries, dict) else {}


def problems(
    found: Mapping[str, str] | None = None, committed: Mapping[str, str] | None = None
) -> tuple[list[str], list[str]]:
    """``(new gaps, gaps the snapshot still lists that are covered now)``."""
    now = gaps() if found is None else found
    known = load_snapshot() if committed is None else committed
    new = sorted(k for k in now if k not in known)
    stale = sorted(k for k in known if k not in now)
    return new, stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    args = parser.parse_args(argv)
    found = gaps()
    if args.write:
        body = {
            "_about": (
                "Gaps the combination test (WP-R-030) finds in the test site's recorded "
                "index, each one planned work. This list may only shrink: regenerate with "
                "python -m quill.tools.wordpress_combination_audit --write and read the diff."
            ),
            "gaps": {key: f"{PLANNED}: {why}" for key, why in sorted(found.items())},
        }
        SNAPSHOT_PATH.write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"Wrote {len(found)} planned gap(s) to {SNAPSHOT_PATH}")
        return 0
    committed = {k: v.removeprefix(f"{PLANNED}: ") for k, v in load_snapshot().items()}
    new, stale = problems(found, committed)
    for key in new:
        print(f"new gap, not planned: {key} ({found[key]})")
    for key in stale:
        print(f"covered now, remove from the snapshot: {key}")
    if new or stale:
        print("Run: python -m quill.tools.wordpress_combination_audit --write")
        return 1
    print(f"WordPress combinations: {len(found)} planned gap(s), nothing new.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
