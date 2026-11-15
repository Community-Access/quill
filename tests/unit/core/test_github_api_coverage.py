"""GATE-GITHUB-COVER (GitHub Workbench PRD section 19): every GitHub API operation has a row.

The snapshot in ``quill/data/github_api/`` is GitHub's own description of its
API; ``quill/core/github/api_coverage.json`` says, for each operation, whether
the Workbench does it (and which command, sheet field or node), plans to, does
not need to, or leaves it to GitHub (and why). A refreshed snapshot with a new
operation fails here as ``missing`` until somebody decides.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from quill.core.github import api_coverage as cover
from quill.tools import github_api_coverage_audit as audit

REPO = Path(__file__).resolve().parents[3]


def test_the_table_accounts_for_every_operation_and_every_home_exists() -> None:
    found = cover.problems()
    assert found == [], "\n".join(found[:40])


def test_the_snapshot_is_githubs_own_description() -> None:
    """Refreshed 2026-11-13 from rest-api-description@53fd7d2 and the public schema.

    Appendices E and F (read 2026-11-09) had 1272 operations and 284 mutations;
    GitHub added 9 operations since (issue fields and issue types for a user's
    own repositories, and a repository's planning statuses). The schema lists
    51 types with viewer fields where the PRD's table, which skipped some
    interfaces, listed 42.
    """
    snap = cover.load_snapshot()
    assert len(snap.rest) == 1281
    assert len({op["category"] for op in snap.rest.values()}) == 51
    assert len(snap.graphql_mutations) == 284
    assert len(snap.viewer_fields) >= 42
    for name in ("rest.json", "graphql.json", "ghes_versions.json"):
        raw = json.loads((cover.SNAPSHOT_DIR / name).read_text(encoding="utf-8"))
        assert "read 2026-11-13" in raw["source"], name
    assert (cover.SNAPSHOT_DIR / "LICENSE-rest-api-description.txt").is_file()


def test_every_section_is_classified_in_full() -> None:
    table = cover.load_coverage()
    snap = cover.load_snapshot()
    assert set(table["rest"]) == set(snap.rest)
    assert set(table["graphql_mutations"]) == set(snap.graphql_mutations)
    assert set(table["enterprise"]) == set(snap.enterprise)
    for rows in table.values():
        for entry in rows.values():
            assert entry.status in cover.STATUSES, entry


def test_planned_may_only_shrink() -> None:
    """The ceiling is the ratchet: lower it when rows move to covered, never raise it."""
    table = cover.load_coverage()
    assert cover.counts(table)["planned"] <= cover.planned_ceiling()
    raw = json.loads(cover.COVERAGE_PATH.read_text(encoding="utf-8"))
    # 1103 at the PRD-derived snapshot; raised once, 2026-11-13, to 1161 for rows
    # GitHub's own descriptions added: 9 new api.github.com operations and 52
    # GHEC-only organization and repository operations (less the 3 hand-named
    # rows they replaced). Lower it as rows are built; never raise it again
    # without a dated reason here.
    assert raw["planned_ceiling"] <= 1161, "the planned ceiling was raised; it may only go down"


def test_a_covered_row_names_a_module_that_exists() -> None:
    table = cover.load_coverage()
    for section, rows in table.items():
        for key, entry in rows.items():
            if entry.status == "covered":
                assert (REPO / entry.via).is_file(), f"{section} {key}: {entry.via}"


def test_missing_stale_and_bad_homes_are_reported() -> None:
    snap = cover.load_snapshot()
    table = {section: dict(rows) for section, rows in cover.load_coverage().items()}
    gone = next(iter(table["rest"]))
    del table["rest"][gone]
    table["rest"]["GET /not/a/real/operation"] = cover.CoverageEntry(
        "GET /not/a/real/operation", "covered", "command:github.workbench.no_such_thing", "x.py"
    )
    found = cover.problems(table, snap, ceiling=10_000)
    assert any(line.startswith(f"missing: rest {gone}") for line in found)
    assert any(line.startswith("stale: rest GET /not/a/real/operation") for line in found)
    assert any("no such home" in line for line in found)


def test_the_ratchet_fails_when_planned_grows() -> None:
    table = cover.load_coverage()
    planned = cover.counts(table)["planned"]
    found = cover.problems(table, cover.load_snapshot(), ceiling=planned - 1)
    assert any(line.startswith("ratchet:") for line in found)


def test_homes_are_checked_against_the_real_tables() -> None:
    assert cover.home_exists("command:github.workbench.merge")
    assert cover.home_exists("sheet:issue.title")
    assert cover.home_exists("node:repository:issues")
    assert not cover.home_exists("command:github.workbench.not_a_command")
    assert not cover.home_exists("sheet:issue.no_such_field")
    assert not cover.home_exists("node:repository:nowhere")


def test_versions_grey_out_with_a_reason_only_on_enterprise_server() -> None:
    assert cover.ghes_versions() == ("3.18", "3.19", "3.20", "3.21", "3.22")
    issues = "GET /repos/{owner}/{repo}/issues"
    assert cover.ghes_availability(issues) == ("3.18", "3.22")
    assert cover.unavailable_reason(issues, None) == ""
    assert cover.unavailable_reason(issues, "3.20") == ""
    assert "GitHub.com only" in cover.unavailable_reason("GET /user/issue-types", "3.22")
    assert cover.unavailable_reason("GET /user/issue-types", None) == ""
    raw = json.loads((cover.SNAPSHOT_DIR / "ghes_versions.json").read_text(encoding="utf-8"))
    late = next(k for k, v in raw["operations"].items() if v[0] == "3.21")
    assert "3.21 or later" in cover.unavailable_reason(late, "3.19")
    gone = next(k for k, v in raw["operations"].items() if v[1] == "3.20")
    assert "removed this after version 3.20" in cover.unavailable_reason(gone, "3.22")
    assert cover.unavailable_reason(issues, "not a version") == ""
    assert cover.server_version_for_host("github.com") is None


def test_the_read_query_ledger_names_what_10b2_asks_for() -> None:
    queries = cover.load_coverage()["graphql_queries"]
    for name in (
        "pinnedItems",
        "fundingLinks",
        "contributionsCollection",
        "dependencyGraphManifests",
        "discussionCategories",
        "lists",
    ):
        assert name in queries, name
        assert queries[name].home, name


def test_enterprise_rows_have_homes_and_reasons() -> None:
    rows = cover.load_coverage()["enterprise"]
    assert rows["GET /orgs/{org}/audit-log"].status == "planned"
    assert rows["GET /orgs/{org}/credential-authorizations"].status == "planned"
    assert any(key.startswith(("GET /scim/", "POST /scim/")) for key in rows)
    snap = cover.load_snapshot()
    assert {op["named_from"] for op in snap.enterprise.values()} == {"description"}
    for key, entry in rows.items():
        if entry.status == "out_of_scope":
            assert entry.reason and entry.home, key


def test_the_generated_chapter_matches_the_table() -> None:
    current = audit.DOC_PATH.read_text(encoding="utf-8")
    assert audit.render(current) == current, (
        "Regenerate with: python -m quill.tools.github_api_coverage_audit --write-doc"
    )
    assert "## Everything GitHub can do, and where" in current


def test_the_snapshot_script_rebuilds_the_same_snapshot_from_the_prd() -> None:
    """The vendored snapshot is exactly what the appendices say (no hand edits)."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import github_api_snapshot as script
    finally:
        sys.path.remove(str(REPO / "scripts"))
    source = json.loads((cover.SNAPSHOT_DIR / "rest.json").read_text(encoding="utf-8"))["source"]
    if not str(source).startswith("PRD"):
        return  # refreshed from GitHub's own description since; the PRD is history
    rest, graph = script.parse_prd(script.PRD.read_text(encoding="utf-8"))
    snap = cover.load_snapshot()
    assert {script.key(r) for r in rest} == set(snap.rest)
    assert {m["name"] for m in graph["mutations"]} == set(snap.graphql_mutations)


def test_the_openapi_and_sdl_readers_work_offline() -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import github_api_snapshot as script
    finally:
        sys.path.remove(str(REPO / "scripts"))
    doc = {
        "paths": {
            "/orgs/{org}/audit-log": {
                "get": {
                    "summary": "Get the audit log for an organization",
                    "operationId": "orgs/get-audit-log",
                    "x-github": {"category": "orgs", "subcategory": "orgs"},
                }
            }
        }
    }
    rows = script.parse_openapi(doc, {})
    assert rows[0]["operation_id"] == "orgs/get-audit-log"
    assert rows[0]["tier"] == "read"
    added, removed = script.diff([], [script.key(rows[0])])
    assert added == ["GET /orgs/{org}/audit-log"] and removed == []
    sdl = (
        'type Mutation {\n  """\n  Adds a star.\n  """\n  addStar(\n'
        '    """\n    Parameters for AddStar\n    """\n    input: AddStarInput!\n'
        "  ): AddStarPayload\n}\n"
        "type Repository {\n  viewerHasStarred: Boolean!\n  name: String!\n}\n"
    )
    parsed = script.parse_graphql_sdl(sdl, {"addStar": "activity"})
    assert parsed["mutations"] == [
        {"category": "activity", "name": "addStar", "description": "Adds a star."}
    ]
    assert parsed["viewer_fields"] == {"Repository": ["viewerHasStarred"]}


def test_the_gate_command_passes() -> None:
    assert audit.main([]) == 0
