"""Where the GitHub Workbench reaches each GitHub API operation (GitHub PRD section 19).

``api_coverage.json`` (beside this module) gives every operation in the
vendored snapshot (``quill/data/github_api/``) one row:

- ``covered``: *home* names what does it -- ``command:<id>`` (a Workbench or
  editor command), ``sheet:<kind>`` or ``sheet:<kind>.<field>`` (a Properties
  sheet and field), or ``node:<template>:<key>`` (a Navigator node whose list
  reads it); *via* is the module that makes the call;
- ``planned``: *row* names its feature in :data:`~quill.core.github.workbench_tree.PLANNED`
  or the PRD section it comes from, and *home* is where it will live;
- ``no_api_needed`` and ``out_of_scope``: *reason* says why, in one line.

GATE-GITHUB-COVER (``tests/unit/core/test_github_api_coverage.py`` and
``python -m quill.tools.github_api_coverage_audit``) fails on a snapshot
operation with no row (``missing``), a row for an operation the snapshot no
longer has (``stale``), a covered row whose home does not exist, and a
``planned`` count above ``planned_ceiling``. The app and the tests never fetch
the API description; ``scripts/github_api_snapshot.py`` refreshes it on purpose.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

__all__ = [
    "COVERAGE_PATH",
    "SECTIONS",
    "SNAPSHOT_DIR",
    "STATUSES",
    "CoverageEntry",
    "Snapshot",
    "counts",
    "ghes_availability",
    "ghes_versions",
    "home_exists",
    "load_coverage",
    "load_snapshot",
    "planned_ceiling",
    "problems",
    "server_version_for_host",
    "unavailable_reason",
]

COVERAGE_PATH = Path(__file__).with_name("api_coverage.json")
SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "data" / "github_api"
STATUSES = ("covered", "planned", "no_api_needed", "out_of_scope")
SECTIONS = ("rest", "graphql_mutations", "graphql_queries", "enterprise")
"""``graphql_queries`` is the read-query ledger: it has no snapshot to be checked against."""


@dataclass(frozen=True, slots=True)
class CoverageEntry:
    """One operation's row."""

    key: str
    status: str
    home: str
    via: str = ""
    row: str = ""
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Snapshot:
    """What the vendored snapshot holds, per section, keyed like the table."""

    rest: Mapping[str, Mapping[str, str]]
    graphql_mutations: Mapping[str, Mapping[str, str]]
    enterprise: Mapping[str, Mapping[str, str]]
    viewer_fields: Mapping[str, tuple[str, ...]]

    def section(self, name: str) -> Mapping[str, Mapping[str, str]] | None:
        found: Mapping[str, Mapping[str, str]] | None = {
            "rest": self.rest,
            "graphql_mutations": self.graphql_mutations,
            "enterprise": self.enterprise,
        }.get(name)
        return found


def _read(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _rows(data: Mapping[str, Any], key: str) -> list[Mapping[str, str]]:
    rows = data.get(key)
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def load_snapshot(directory: Path = SNAPSHOT_DIR) -> Snapshot:
    """The vendored REST, GraphQL and Enterprise operations."""
    rest = _read(directory / "rest.json")
    graph = _read(directory / "graphql.json")
    enterprise_path = directory / "enterprise.json"
    enterprise = _read(enterprise_path) if enterprise_path.is_file() else {}
    viewer = graph.get("viewer_fields")
    return Snapshot(
        rest={f"{r['method']} {r['path']}": r for r in _rows(rest, "operations")},
        graphql_mutations={str(r["name"]): r for r in _rows(graph, "mutations")},
        enterprise={f"{r['method']} {r['path']}": r for r in _rows(enterprise, "operations")},
        viewer_fields=(
            {str(k): tuple(str(f) for f in v) for k, v in viewer.items() if isinstance(v, list)}
            if isinstance(viewer, dict)
            else {}
        ),
    )


def _raw_coverage(path: Path = COVERAGE_PATH) -> dict[str, Any]:
    return _read(path)


def load_coverage(path: Path = COVERAGE_PATH) -> dict[str, dict[str, CoverageEntry]]:
    """Every section's rows, by key."""
    raw = _raw_coverage(path)
    out: dict[str, dict[str, CoverageEntry]] = {}
    for section in SECTIONS:
        rows = raw.get(section)
        found: dict[str, CoverageEntry] = {}
        if isinstance(rows, dict):
            for key, value in rows.items():
                if isinstance(value, dict):
                    found[str(key)] = CoverageEntry(
                        str(key),
                        str(value.get("status", "")),
                        str(value.get("home", "")),
                        str(value.get("via", "")),
                        str(value.get("row", "")),
                        str(value.get("reason", "")),
                    )
        out[section] = found
    return out


def planned_ceiling(path: Path = COVERAGE_PATH) -> int:
    """The most ``planned`` rows the table may hold; it only ever goes down."""
    value = _raw_coverage(path).get("planned_ceiling")
    return int(value) if isinstance(value, int) else 0


def counts(table: Mapping[str, Mapping[str, CoverageEntry]]) -> dict[str, int]:
    """How many rows have each status, across every section."""
    tally = dict.fromkeys(STATUSES, 0)
    for rows in table.values():
        for entry in rows.values():
            tally[entry.status] = tally.get(entry.status, 0) + 1
    return tally


@cache
def _known_homes() -> tuple[
    frozenset[str], dict[str, frozenset[str]], frozenset[str], frozenset[str]
]:
    """(command ids, sheet kind -> field keys, node ids, PLANNED feature names)."""
    from quill.core.github.item_actions import GITHUB_ACTIONS
    from quill.core.github.sheet_catalog import SHEETS
    from quill.core.github.workbench_tree import GITHUB_TREE, PLANNED
    from quill.core.github.workbench_window_menu import WINDOW_MENU, WORKBENCH_KEYS
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.workbench.menus import all_rows

    commands = {row.command_id for _spec, row in all_rows(WINDOW_MENU)}
    commands |= set(WORKBENCH_KEYS)
    commands |= {k for k in DEFAULT_KEYMAP if k.startswith("github.")}
    for kind in GITHUB_ACTIONS.row_types:
        top, more = GITHUB_ACTIONS.menu_for(kind)
        commands |= {str(getattr(row, "command_id", "")) for row in (*top, *more)}
    sheets = {
        kind: frozenset(f.key for p in sheet.sheet.pages for f in p.fields)
        for kind, sheet in SHEETS.items()
    }
    nodes = {f"{template}:{node.key}" for template, node in GITHUB_TREE.all_nodes()}
    planned = {row.operation for row in PLANNED.rows}
    return frozenset(commands), sheets, frozenset(nodes), frozenset(planned)


def home_exists(home: str) -> bool:
    """True when a covered row's *home* names a real command, sheet field or node."""
    commands, sheets, nodes, _planned = _known_homes()
    kind, _, rest = home.partition(":")
    if kind == "command":
        return rest in commands
    if kind == "sheet":
        sheet, _, field = rest.partition(".")
        return sheet in sheets and (not field or field in sheets[sheet])
    if kind == "node":
        return rest in nodes
    return False


def _planned_row_ok(row: str) -> bool:
    if row.startswith(("Appendix ", "section ")):
        return True
    return row in _known_homes()[3]


def problems(
    table: Mapping[str, Mapping[str, CoverageEntry]] | None = None,
    snapshot: Snapshot | None = None,
    ceiling: int | None = None,
) -> list[str]:
    """Every missing, stale or malformed row, as sentences; empty when the gate holds."""
    rows = load_coverage() if table is None else table
    snap = load_snapshot() if snapshot is None else snapshot
    limit = planned_ceiling() if ceiling is None else ceiling
    said: list[str] = []
    for section in SECTIONS:
        have = rows.get(section, {})
        ops = snap.section(section)
        if ops is not None:
            said += [
                f"missing: {section} {key} ({ops[key].get('name', '')}) has no row"
                for key in sorted(set(ops) - set(have))
            ]
            said += [
                f"stale: {section} {key} is no longer in the snapshot"
                for key in sorted(set(have) - set(ops))
            ]
        for key, entry in sorted(have.items()):
            said += _entry_problems(section, key, entry)
    planned = counts(rows).get("planned", 0)
    if planned > limit:
        said.append(
            f"ratchet: {planned} planned rows, above the ceiling of {limit}; "
            "the planned list may only shrink"
        )
    return said


def _entry_problems(section: str, key: str, entry: CoverageEntry) -> Iterable[str]:
    where = f"{section} {key}"
    if entry.status not in STATUSES:
        yield f"unknown status: {where} is {entry.status!r}"
    elif entry.status == "covered":
        if not home_exists(entry.home):
            yield f"no such home: {where} is covered by {entry.home!r}, which does not exist"
        if not entry.via:
            yield f"unproven: {where} is covered without the module that calls it"
    elif entry.status == "planned":
        if not entry.home:
            yield f"homeless: {where} is planned with no future home"
        if not _planned_row_ok(entry.row):
            yield f"no such plan: {where} names {entry.row!r}, not a PLANNED row or PRD section"
    elif not entry.reason:
        yield f"unexplained: {where} is {entry.status} without a reason"


@cache
def _ghes_table(
    directory: Path = SNAPSHOT_DIR,
) -> tuple[tuple[str, ...], dict[str, tuple[str, str]]]:
    """(vendored versions, operation -> (first, last)); empty when nothing is vendored."""
    path = directory / "ghes_versions.json"
    if not path.is_file():
        return (), {}
    raw = _read(path)
    versions = raw.get("versions")
    spans = raw.get("operations")
    table: dict[str, tuple[str, str]] = {}
    if isinstance(spans, dict):
        for key, span in spans.items():
            if isinstance(span, list) and len(span) == 2:
                table[str(key)] = (str(span[0]), str(span[1]))
    listed = tuple(str(v) for v in versions) if isinstance(versions, list) else ()
    return listed, table


def _version(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in text.strip().split("."))
    except ValueError:
        return ()


def ghes_availability(key: str, directory: Path = SNAPSHOT_DIR) -> tuple[str, str] | None:
    """The first and last GitHub Enterprise Server version whose description has *key*.

    ``None`` when no vendored GHES description has it (or none is vendored).
    ``ghes_versions.json`` is written by ``scripts/github_api_snapshot.py --ghes-versions``.
    """
    return _ghes_table(directory)[1].get(key)


def ghes_versions(directory: Path = SNAPSHOT_DIR) -> tuple[str, ...]:
    """The GitHub Enterprise Server versions the snapshot was read from, oldest first."""
    return _ghes_table(directory)[0]


def unavailable_reason(key: str, server_version: str | None, directory: Path = SNAPSHOT_DIR) -> str:
    """Why *key* cannot run on a GitHub Enterprise Server at *server_version*, or ``""``.

    ``server_version`` is ``None`` for GitHub.com, where nothing is greyed out
    by version. A row or sheet field greys itself with this sentence instead
    of failing. Versions newer than the newest vendored one are judged by the
    newest; an unknown version, or no vendored data, never greys anything.
    """
    if server_version is None:
        return ""
    versions, spans = _ghes_table(directory)
    wanted = _version(server_version)
    if not versions or not wanted:
        return ""
    oldest, newest = _version(versions[0]), _version(versions[-1])
    if wanted < oldest:
        return ""
    span = spans.get(key)
    if span is None:
        return (
            f"GitHub Enterprise Server {server_version} does not offer this; "
            "it is on GitHub.com only."
        )
    first, last = span
    if wanted < _version(first):
        return (
            f"This needs GitHub Enterprise Server {first} or later; "
            f"this server runs {server_version}."
        )
    if _version(last) < newest and wanted > _version(last):
        return f"GitHub Enterprise Server removed this after version {last}."
    return ""


def server_version_for_host(host: str) -> str | None:
    """The GitHub Enterprise Server version for an account's *host*; ``None`` for GitHub.com.

    Accounts are GitHub.com only today (``accounts.py`` refuses other hosts), so
    this is always ``None`` and nothing greys by version. When Enterprise
    Server accounts arrive, the version their ``/meta`` reports goes here.
    """
    del host
    return None
