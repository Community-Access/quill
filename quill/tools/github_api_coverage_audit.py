"""GATE-GITHUB-COVER (GitHub Workbench PRD section 19): every GitHub API operation has a row.

:mod:`quill.core.github.api_coverage` reads ``quill/core/github/api_coverage.json``
against the vendored snapshot in ``quill/data/github_api/``. This gate fails on:

- an operation in the snapshot with no row (``missing``) -- what a refreshed
  snapshot shows first, until somebody decides where the new operation lives;
- a row for an operation the snapshot no longer has (``stale``);
- a covered row whose home (command id, sheet field or Navigator node) does
  not exist, a planned row with no plan, or another row with no reason;
- more ``planned`` rows than ``planned_ceiling``: the planned list only shrinks;
- the generated chapter "Everything GitHub can do, and where" in
  ``docs/github/workbench-reference.md`` differing from the table.

Usage::

    python -m quill.tools.github_api_coverage_audit              # check
    python -m quill.tools.github_api_coverage_audit --write-doc  # regenerate the chapter

Refreshing the snapshot itself is ``scripts/github_api_snapshot.py``, run by a
person on purpose; nothing here touches the network.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from functools import cache
from pathlib import Path

from quill.core.github.api_coverage import (
    CoverageEntry,
    counts,
    ghes_availability,
    load_coverage,
    load_snapshot,
    problems,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = _REPO_ROOT / "docs" / "github" / "workbench-reference.md"
BEGIN = (
    "<!-- BEGIN GENERATED COVERAGE: python -m quill.tools.github_api_coverage_audit --write-doc -->"
)
END = "<!-- END GENERATED COVERAGE -->"

__all__ = ["BEGIN", "DOC_PATH", "END", "describe_home", "generate", "main", "render"]

#: GitHub's own category names for its API slugs (PRD section 19's list).
_NAMES = {
    "actions": "Actions",
    "activity": "Activity",
    "agent-automations": "Agent automations",
    "agent-tasks": "Agent tasks",
    "agents": "Agents",
    "apps": "Apps",
    "billing": "Billing",
    "branches": "Branches",
    "campaigns": "Campaigns",
    "checks": "Checks",
    "classroom": "Classroom",
    "code-quality": "Code quality",
    "code-scanning": "Code scanning",
    "code-security": "Code security",
    "codes-of-conduct": "Codes of conduct",
    "codespaces": "Codespaces",
    "collaborators": "Collaborators",
    "commits": "Commits",
    "copilot": "Copilot",
    "copilot-spaces": "Copilot Spaces",
    "credentials": "Credentials",
    "dependabot": "Dependabot",
    "dependency-graph": "Dependency graph",
    "deploy-keys": "Deploy keys",
    "deployments": "Deployments",
    "emojis": "Emojis",
    "gists": "Gists",
    "git": "Git database",
    "gitignore": "Gitignore",
    "interactions": "Interactions",
    "issues": "Issues",
    "licenses": "Licenses",
    "markdown": "Markdown",
    "meta": "Meta",
    "metrics": "Metrics",
    "migrations": "Migrations",
    "orgs": "Organizations",
    "packages": "Packages",
    "pages": "Pages",
    "private-registries": "Private registries",
    "projects": "Projects",
    "pulls": "Pull requests",
    "rate-limit": "Rate limit",
    "reactions": "Reactions",
    "releases": "Releases",
    "repos": "Repositories",
    "search": "Search",
    "secret-scanning": "Secret scanning",
    "security-advisories": "Security advisories",
    "teams": "Teams",
    "users": "Users",
    "enterprise-admin": "Enterprise administration",
    "classic projects": "Projects (classic)",
    "sponsors": "Sponsors",
}
_STATUS_WORDS = {
    "covered": "Yes",
    "planned": "Planned",
    "no_api_needed": "Not needed",
    "out_of_scope": "Left to GitHub",
}


def _name(slug: str) -> str:
    return _NAMES.get(slug, slug.replace("-", " ").capitalize())


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


@cache
def _home_words() -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    """(command id -> words, sheet kind -> title, "kind.field" -> label, node id -> path)."""
    from quill.core.github import workbench_menu
    from quill.core.github.item_actions import GITHUB_ACTIONS
    from quill.core.github.sheet_catalog import SHEETS
    from quill.core.github.workbench_tree import GITHUB_TREE
    from quill.core.github.workbench_window_menu import WINDOW_MENU, WORKBENCH_KEYS
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.workbench.menus import MenuSub

    commands: dict[str, str] = {}
    for spec in WINDOW_MENU:
        menu = spec.title.replace("&", "")
        for row in spec.rows:
            inner = row.rows if isinstance(row, MenuSub) else (row,)
            prefix = f"{menu} > {row.title.replace('&', '')}" if isinstance(row, MenuSub) else menu
            for item in inner:
                if item is not None and item.command_id not in commands:
                    key = f" ({item.key})" if item.key else ""
                    commands[item.command_id] = f"{prefix} > {item.label.replace('&', '')}{key}"
    for kind in GITHUB_ACTIONS.row_types:
        top, more = GITHUB_ACTIONS.menu_for(kind)
        for action in (*top, *more):
            if action.command_id not in commands:
                key = WORKBENCH_KEYS.get(action.command_id, "")
                words = f"context menu > {action.label}" + (f" ({key})" if key else "")
                commands[action.command_id] = words
    for value in vars(workbench_menu).values():
        rows = value if isinstance(value, tuple) else ()
        for row in rows:
            command_id = getattr(row, "command_id", "")
            if isinstance(command_id, str) and command_id and command_id not in commands:
                key = DEFAULT_KEYMAP.get(command_id, "")
                label = str(getattr(row, "label", "")).replace("&", "")
                commands[command_id] = f"editor GitHub menu > {label}" + (
                    f" ({key})" if key else ""
                )
    for command_id, key in DEFAULT_KEYMAP.items():
        if command_id.startswith("github.") and command_id not in commands:
            commands[command_id] = f"editor command {command_id}" + (f" ({key})" if key else "")
    titles = {kind: sheet.sheet.title for kind, sheet in SHEETS.items()}
    fields = {
        f"{kind}.{f.key}": f.label
        for kind, sheet in SHEETS.items()
        for p in sheet.sheet.pages
        for f in p.fields
    }
    labels = {(t, n.key): n for t, n in GITHUB_TREE.all_nodes()}
    nodes: dict[str, str] = {}
    for (template, key), node in labels.items():
        path = [node.label]
        parent = node.parent
        while parent and (template, parent) in labels:
            up = labels[(template, parent)]
            path.insert(0, up.label)
            parent = up.parent
        if template and path[0] != template.capitalize():
            path.insert(0, template.capitalize())
        nodes[f"{template}:{key}"] = " > ".join(path)
    return commands, titles, fields, nodes


def describe_home(home: str) -> str:
    """A covered row's home, in words a person can follow: menu, key, sheet or node."""
    commands, titles, fields, nodes = _home_words()
    kind, _, rest = home.partition(":")
    if kind == "command":
        return commands.get(rest, rest)
    if kind == "sheet":
        sheet, _, field = rest.partition(".")
        title = titles.get(sheet, sheet)
        if field:
            return f"Properties (Alt+Enter) on {title}: {fields.get(rest, field)}"
        return f"Properties (Alt+Enter) on {title}"
    if kind == "node":
        return f"Navigator: {nodes.get(rest, rest)}"
    return home


def _where(entry: CoverageEntry) -> str:
    if entry.status == "covered":
        return describe_home(entry.home)
    if entry.status == "planned":
        return entry.home
    return f"{entry.reason} {entry.home}." if entry.home not in ("", "None") else entry.reason


def _tally(rows: list[CoverageEntry]) -> str:
    found = counts({"": {r.key: r for r in rows}})
    return ", ".join(f"{found[s]} {_STATUS_WORDS[s].lower()}" for s in found if found[s])


def generate() -> str:
    """The generated chapter, markers included."""
    table = load_coverage()
    snap = load_snapshot()
    total = counts(table)
    out = [
        BEGIN,
        "",
        "## Everything GitHub can do, and where",
        "",
        "Generated from `quill/core/github/api_coverage.json` against the snapshot of GitHub's "
        "own API descriptions in `quill/data/github_api/` (GitHub Workbench PRD section 19). "
        "Every REST operation and GraphQL mutation GitHub publishes is listed under GitHub's "
        "category name, with one of four answers:",
        "",
        "- **Yes**: the Workbench does it; the row says where, with its key.",
        "- **Planned**: not yet; the row says where it will live.",
        "- **Not needed**: plumbing a person never meets as such.",
        "- **Left to GitHub**: the Workbench does not do it, and the row says why.",
        "",
        f"In all: {total['covered']} yes, {total['planned']} planned, "
        f"{total['no_api_needed']} not needed and {total['out_of_scope']} left to GitHub.",
        "",
        "**Wikis** have no API: GitHub serves each one as a Git repository "
        "(`owner/name.wiki.git`). Reading and editing them is planned under Repository > Wiki.",
    ]
    by_category: dict[str, list[tuple[Mapping[str, str], CoverageEntry]]] = {}
    for key, op in snap.rest.items():
        entry = table["rest"].get(key)
        if entry is not None:
            by_category.setdefault(op.get("category", ""), []).append((op, entry))
    out += ["", "### REST operations, by category", ""]
    for slug in sorted(by_category, key=_name):
        rows = sorted(
            by_category[slug], key=lambda pair: (pair[0].get("path", ""), pair[0].get("method", ""))
        )
        out += [
            f"#### {_name(slug)}",
            "",
            f"{len(rows)} operations: {_tally([e for _o, e in rows])}.",
            "",
            "| Operation | Call | Can QUILL do it? | Where, or why |",
            "| --- | --- | --- | --- |",
        ]
        for op, entry in rows:
            out.append(
                f"| {_cell(op.get('name', ''))} | `{op.get('method', '')} {op.get('path', '')}` "
                f"| {_STATUS_WORDS.get(entry.status, entry.status)} | {_cell(_where(entry))} |"
            )
        out.append("")
    mutations: dict[str, list[tuple[Mapping[str, str], CoverageEntry]]] = {}
    for key, op in snap.graphql_mutations.items():
        entry = table["graphql_mutations"].get(key)
        if entry is not None:
            mutations.setdefault(op.get("category", ""), []).append((op, entry))
    out += ["### GraphQL mutations, by category", ""]
    for slug in sorted(mutations, key=_name):
        rows = sorted(mutations[slug], key=lambda pair: pair[0].get("name", ""))
        out += [
            f"#### GraphQL: {_name(slug)}",
            "",
            f"{len(rows)} mutations: {_tally([e for _o, e in rows])}.",
            "",
            "| Mutation | Can QUILL do it? | Where, or why |",
            "| --- | --- | --- |",
        ]
        for op, entry in rows:
            out.append(
                f"| `{op.get('name', '')}` | {_STATUS_WORDS.get(entry.status, entry.status)} "
                f"| {_cell(_where(entry))} |"
            )
        out.append("")
    out += [
        "### GraphQL reads with no REST twin",
        "",
        "| Query field | Can QUILL do it? | Where, or why |",
        "| --- | --- | --- |",
    ]
    for key, entry in sorted(table["graphql_queries"].items()):
        said = _STATUS_WORDS.get(entry.status, entry.status)
        out.append(f"| `{key}` | {said} | {_cell(_where(entry))} |")
    out += [
        "",
        "### GitHub Enterprise Cloud and Enterprise Server only",
        "",
        "Operations api.github.com's description does not have, read from GitHub's own "
        "Enterprise Cloud and Enterprise Server descriptions. For a Server row, the edition "
        "column gives the first and last Server version that has it. The Workbench signs in "
        "to GitHub.com accounts only, so Server-only rows are left to the server's own pages.",
        "",
        "| Operation | Call | Edition | Can QUILL do it? | Where, or why |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key, op in sorted(
        snap.enterprise.items(), key=lambda kv: (kv[1].get("edition", ""), kv[0])
    ):
        entry = table["enterprise"].get(key)
        if entry is None:
            continue
        edition = "Cloud"
        if op.get("edition") != "ghec":
            span = ghes_availability(key)
            edition = f"Server {span[0]} to {span[1]}" if span else "Server"
        out.append(
            f"| {_cell(op.get('name', ''))} | `{key}` | {edition} "
            f"| {_STATUS_WORDS.get(entry.status, entry.status)} | {_cell(_where(entry))} |"
        )
    out += ["", END]
    return "\n".join(out) + "\n"


def render(text: str) -> str:
    """*text* with the chapter replaced, or appended when it has none."""
    region = generate()
    if BEGIN in text and END in text:
        head = text[: text.index(BEGIN)]
        tail = text[text.index(END) + len(END) :].lstrip("\n")
        return head + region + (("\n" + tail) if tail else "")
    return text.rstrip("\n") + "\n\n" + region


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write-doc", action="store_true", help="regenerate the reference chapter")
    args = parser.parse_args(argv)
    current = DOC_PATH.read_text(encoding="utf-8")
    if args.write_doc:
        DOC_PATH.write_text(render(current), encoding="utf-8", newline="\n")
        print(f"wrote {DOC_PATH.relative_to(_REPO_ROOT)}")
        return 0
    found = problems()
    if render(current) != current:
        found.append(
            "drift: docs/github/workbench-reference.md's coverage chapter differs from the "
            "table; run with --write-doc"
        )
    for line in found:
        print(line)
    table = load_coverage()
    tally = counts(table)
    summary = ", ".join(f"{tally[s]} {s}" for s in tally)
    if found:
        print(f"GATE-GITHUB-COVER: {len(found)} problems ({summary}).")
        return 1
    print(f"GitHub API coverage: {sum(tally.values())} rows, {summary}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
