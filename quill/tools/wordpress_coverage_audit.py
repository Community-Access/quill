"""The coverage gate (WordPress PRD 12): every route on the test site has a home or a reason.

:func:`quill.core.wordpress.workbench_coverage.classify` puts each route of
the test site's recorded index
(``tests/unit/core/wordpress/fixtures/rest_index_test_site.json``, 802
routes over 27 namespaces) in one of five places: ``covered``,
``schema_built``, ``planned``, ``wp_admin_only`` or ``out_of_scope``, each
with its home. The committed snapshot
(``tests/unit/core/wordpress/fixtures/route_coverage.json``) is the review:

- a route in the index and not in the snapshot is ``missing`` and fails;
- a route whose status changed fails until the snapshot is regenerated, so
  the diff shows exactly what moved (planned to covered, say);
- a route in the snapshot and gone from the index fails as stale.

Run ``python -m quill.tools.wordpress_coverage_audit`` to check and
``--write`` to regenerate the snapshot (then read the diff).
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path

from quill.core.wordpress.workbench_coverage import classify_index, summary

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = _REPO_ROOT / "tests" / "unit" / "core" / "wordpress" / "fixtures"
INDEX_PATH = _FIXTURES / "rest_index_test_site.json"
SNAPSHOT_PATH = _FIXTURES / "route_coverage.json"

__all__ = ["INDEX_PATH", "SNAPSHOT_PATH", "current", "load_snapshot", "main", "problems"]


def current(path: Path = INDEX_PATH) -> dict[str, str]:
    """Each recorded route and its status now."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    routes = raw.get("routes") if isinstance(raw, dict) else None
    classes = classify_index(routes if isinstance(routes, dict) else {})
    return {route: c.status for route, c in classes.items()}


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    routes = raw.get("routes") if isinstance(raw, dict) else None
    if not isinstance(routes, dict):
        return {}
    return {str(k): str(v).split(":", 1)[0] for k, v in routes.items()}


def problems(
    found: Mapping[str, str] | None = None, committed: Mapping[str, str] | None = None
) -> list[str]:
    """Every missing, changed or stale route, as sentences."""
    now = current() if found is None else found
    known = load_snapshot() if committed is None else committed
    said: list[str] = []
    for route in sorted(now):
        if route not in known:
            said.append(f"missing: {route} ({now[route]}), not yet reviewed")
        elif known[route] != now[route]:
            said.append(f"changed: {route} was {known[route]}, is {now[route]}")
    said.extend(
        f"stale: {route} is no longer in the index" for route in sorted(set(known) - set(now))
    )
    return said


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    args = parser.parse_args(argv)
    raw = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    classes = classify_index(raw.get("routes") or {})
    if args.write:
        body = {
            "_about": (
                "Where the WordPress Workbench reaches each route of the test site's recorded "
                "index (PRD 12): covered, schema_built, planned, wp_admin_only or "
                "out_of_scope, with its home. Regenerate with python -m "
                "quill.tools.wordpress_coverage_audit --write and read the diff."
            ),
            "summary": summary(classes),
            "routes": {r: f"{c.status}: {c.home}" for r, c in sorted(classes.items())},
        }
        SNAPSHOT_PATH.write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"Wrote {len(classes)} routes to {SNAPSHOT_PATH}")
        return 0
    found = problems({r: c.status for r, c in classes.items()})
    for line in found:
        print(line)
    if found:
        print("Run: python -m quill.tools.wordpress_coverage_audit --write")
        return 1
    print(f"WordPress coverage: {len(classes)} routes, {summary(classes)}.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
