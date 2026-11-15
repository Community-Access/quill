"""Vendor, refresh and diff the GitHub API snapshot (GitHub Workbench PRD section 19).

``quill/data/github_api/`` holds a compact snapshot of what GitHub's API can
do: every REST operation (``rest.json``) and every GraphQL mutation and viewer
answer (``graphql.json``). GATE-GITHUB-COVER
(``tests/unit/core/test_github_api_coverage.py``) checks that each one has a
row in ``quill/core/github/api_coverage.json``. The app and the tests never
fetch anything: the snapshot changes only when a person runs this script on
purpose and reads the diff.

Usage (from the repository root)::

    # Rebuild the snapshot offline from PRD Appendices E and F (how it was
    # first vendored, 2026-11-13):
    python scripts/github_api_snapshot.py --from-prd --write

    # Refresh from GitHub's own descriptions. Each argument is a local file
    # or an https URL; a URL is fetched only because you typed it:
    #   REST:    github/rest-api-description,
    #            descriptions/api.github.com/api.github.com.json
    #   GraphQL: https://docs.github.com/public/fpt/schema.docs.graphql
    python scripts/github_api_snapshot.py --rest api.github.com.json \
        --graphql schema.docs.graphql            # prints the diff only
    python scripts/github_api_snapshot.py --rest ... --graphql ... --write

    # GitHub Enterprise Cloud: the operations its description has that
    # api.github.com's does not (audit log, SAML authorizations, SCIM ...):
    python scripts/github_api_snapshot.py --edition ghec --diff ghec.json [--write]

    # GitHub Enterprise Server, one description per supported version; writes
    # the first and last version that has each operation:
    python scripts/github_api_snapshot.py --ghes-versions ghes-3.15.json \
        ghes-3.16.json ghes-3.17.json [--write]

After ``--write``, run ``python -m quill.tools.github_api_coverage_audit``: a new
operation is ``missing`` until somebody gives it a row.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "quill" / "data" / "github_api"
REST_PATH = DATA / "rest.json"
GRAPHQL_PATH = DATA / "graphql.json"
ENTERPRISE_PATH = DATA / "enterprise.json"
GHES_VERSIONS_PATH = DATA / "ghes_versions.json"
PRD = REPO / "docs" / "Product Requirement Documents and Specifications" / "github-workbench-prd.md"
_METHODS = ("get", "post", "put", "patch", "delete")


# ---------------------------------------------------------------------------
# Reading sources


def _read_source(where: str) -> str:
    """A local file, or an https URL the person running this typed."""
    if where.startswith("https://"):
        from urllib.request import urlopen  # only when a human passed a URL

        with urlopen(where, timeout=60) as reply:  # noqa: S310 - https only, typed by hand
            return str(reply.read().decode("utf-8"))
    return Path(where).read_text(encoding="utf-8")


def _tier(method: str) -> str:
    return {"GET": "read", "DELETE": "3"}.get(method.upper(), "1")


def parse_prd(text: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """REST operations and GraphQL mutations/viewer fields from Appendices E and F."""
    start = text.index("## Appendix E")
    middle = text.index("## Appendix F")
    rest: list[dict[str, str]] = []
    category = subcategory = ""
    row = re.compile(r"^\| (.+?) \| `([A-Z]+) ([^`]+)` \| (.+?) \| (\S+) \|$")
    for line in text[start:middle].splitlines():
        if line.startswith("### REST: "):
            category = line[len("### REST: ") :].split(" (", 1)[0].strip()
            subcategory = category
        elif line.startswith("#### ") and " / " in line:
            subcategory = line[5:].split(" / ", 1)[1].rsplit(" (", 1)[0].strip()
        else:
            m = row.match(line)
            if m:
                scope = m.group(4).strip().strip("`")
                rest.append({
                    "category": category,
                    "subcategory": subcategory,
                    "name": m.group(1).strip(),
                    "operation_id": "",
                    "method": m.group(2),
                    "path": m.group(3),
                    "scope": "" if scope == "-" else scope,
                    "tier": m.group(5),
                })
    graph = text[middle:]
    viewer: dict[str, list[str]] = {}
    mutations: list[dict[str, str]] = []
    in_viewer = False
    gcat = ""
    for line in graph.splitlines():
        if line.startswith("### F.1"):
            in_viewer = True
        elif line.startswith("### F.2"):
            in_viewer = False
        elif line.startswith("#### GraphQL: "):
            gcat = line[len("#### GraphQL: ") :].split(" (", 1)[0].strip()
        elif in_viewer and line.startswith("| ") and "`" in line:
            kind, fields = line.strip("| ").split(" | ", 1)
            viewer[kind.strip()] = re.findall(r"`([^`]+)`", fields)
        elif gcat and line.startswith("| `"):
            name, _, what = line[2:].partition(" | ")
            mutations.append({
                "category": gcat,
                "name": name.strip("` "),
                "description": what.rstrip(" |").strip(),
            })
    return rest, {"mutations": mutations, "viewer_fields": viewer}


def parse_openapi(
    doc: Mapping[str, Any], known: Mapping[str, Mapping[str, str]]
) -> list[dict[str, str]]:
    """Every operation in an OpenAPI description; scope and tier kept from *known*."""
    out: list[dict[str, str]] = []
    for path, item in sorted((doc.get("paths") or {}).items()):
        if not isinstance(item, Mapping):
            continue
        for method in _METHODS:
            op = item.get(method)
            if not isinstance(op, Mapping):
                continue
            key = f"{method.upper()} {path}"
            gh = op.get("x-github") or {}
            tags = op.get("tags") or ["uncategorized"]
            old = known.get(key, {})
            out.append({
                "category": str(gh.get("category") or tags[0]),
                "subcategory": str(gh.get("subcategory") or gh.get("category") or tags[0]),
                "name": str(op.get("summary") or op.get("operationId") or key),
                "operation_id": str(op.get("operationId") or ""),
                "method": method.upper(),
                "path": path,
                "scope": str(old.get("scope", "")),
                "tier": str(old.get("tier") or _tier(method)),
            })
    return out


def parse_graphql_sdl(text: str, known: Mapping[str, str]) -> dict[str, Any]:
    """Mutations (category kept from *known*, else "uncategorized") and viewer fields."""
    mutations: list[dict[str, str]] = []
    viewer: dict[str, list[str]] = {}
    block = re.compile(r"^(?:type|interface) (\w+)[^{]*\{(.*?)^\}", re.M | re.S)
    for name, body in block.findall(text):
        if name == "Mutation":
            doc, words, in_doc, depth = "", [], False, 0
            for raw in body.splitlines():
                line = raw.strip()
                if in_doc:
                    if line.endswith('"""'):
                        in_doc = False
                        doc = " ".join([*words, line[:-3]]).strip()
                    else:
                        words.append(line)
                    continue
                if line.startswith('"""'):
                    inner = line[3:]
                    if len(inner) >= 3 and inner.endswith('"""'):
                        doc = inner[:-3].strip()
                    else:
                        in_doc, words = True, ([inner] if inner else [])
                    continue
                if depth == 0 and re.match(r"^\w+\s*[(:]", line):
                    field = re.split(r"[\s(:]", line, maxsplit=1)[0]
                    mutations.append({
                        "category": known.get(field, "uncategorized"),
                        "name": field,
                        "description": doc,
                    })
                    doc = ""
                depth += line.count("(") - line.count(")")
            continue
        fields = sorted(set(re.findall(r"^\s+(viewer[A-Z]\w*)", body, re.M)))
        if fields:
            viewer[name] = fields
    return {"mutations": mutations, "viewer_fields": dict(sorted(viewer.items()))}


# ---------------------------------------------------------------------------
# Writing the snapshot: one row per line, so a refresh reads as a clean diff


def _rows_json(about: Mapping[str, Any], key: str, rows: Iterable[Any]) -> str:
    head = json.dumps(dict(about), indent=1, ensure_ascii=False)[:-2]
    body = ",\n".join("  " + json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows)
    return f'{head},\n "{key}": [\n{body}\n ]\n}}\n'


def write_rest(rows: list[dict[str, str]], source: str) -> None:
    about = {
        "_about": (
            "GitHub REST operations (GitHub Workbench PRD section 19, Appendix E). "
            "Refreshed only by scripts/github_api_snapshot.py; never fetched by the app "
            "or the tests. Each row's key is 'METHOD path'."
        ),
        "source": source,
        "count": len(rows),
    }
    rows = sorted(rows, key=lambda r: (r["category"], r["subcategory"], r["path"], r["method"]))
    REST_PATH.write_text(_rows_json(about, "operations", rows), encoding="utf-8", newline="\n")


def write_graphql(data: Mapping[str, Any], source: str) -> None:
    about = {
        "_about": (
            "GitHub GraphQL mutations and viewer permission fields (GitHub Workbench PRD "
            "Appendix F). Refreshed only by scripts/github_api_snapshot.py."
        ),
        "source": source,
        "count": len(data["mutations"]),
        "viewer_fields": data["viewer_fields"],
    }
    rows = sorted(data["mutations"], key=lambda r: (r["category"], r["name"]))
    GRAPHQL_PATH.write_text(_rows_json(about, "mutations", rows), encoding="utf-8", newline="\n")


def load_rest() -> list[dict[str, str]]:
    if not REST_PATH.is_file():
        return []
    return list(json.loads(REST_PATH.read_text(encoding="utf-8"))["operations"])


def load_graphql() -> dict[str, Any]:
    if not GRAPHQL_PATH.is_file():
        return {"mutations": [], "viewer_fields": {}}
    return dict(json.loads(GRAPHQL_PATH.read_text(encoding="utf-8")))


def key(row: Mapping[str, str]) -> str:
    return f"{row['method']} {row['path']}"


def diff(old: Iterable[str], new: Iterable[str]) -> tuple[list[str], list[str]]:
    """(added, removed), each sorted."""
    a, b = set(old), set(new)
    return sorted(b - a), sorted(a - b)


def _say_diff(what: str, added: list[str], removed: list[str]) -> None:
    print(f"{what}: {len(added)} added, {len(removed)} removed.")
    for k in added:
        print(f"  added: {k}")
    for k in removed:
        print(f"  removed: {k}")


def _enterprise_rows(edition: str, rows: list[dict[str, str]], source: str = "") -> None:
    """Merge the operations only *edition* has into enterprise.json."""
    current = json.loads(ENTERPRISE_PATH.read_text(encoding="utf-8"))
    if source:
        sources = dict(current.get("sources") or {})
        sources[edition] = source
        current["sources"] = sources
    kept = [r for r in current["operations"] if r.get("edition") != edition]
    for r in rows:
        kept.append({**r, "edition": edition, "named_from": "description"})
    current["operations"] = sorted(kept, key=lambda r: (r["edition"], r["path"], r["method"]))
    ENTERPRISE_PATH.write_text(
        _rows_json(
            {k: v for k, v in current.items() if k != "operations"},
            "operations",
            current["operations"],
        ),
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--from-prd", action="store_true", help="rebuild from PRD Appendices E and F"
    )
    parser.add_argument("--rest", help="api.github.com OpenAPI description (file or https URL)")
    parser.add_argument("--graphql", help="schema.docs.graphql (file or https URL)")
    parser.add_argument(
        "--source", help="provenance to record (upstream commit and read date) instead of the path"
    )
    parser.add_argument("--diff", help="an Enterprise description to compare with the snapshot")
    parser.add_argument("--edition", default="ghec", help="label for --diff rows (ghec, ghes-3.17)")
    parser.add_argument(
        "--ghes-versions", nargs="+", help="GHES descriptions named ghes-<version>.json"
    )
    parser.add_argument(
        "--write", action="store_true", help="write the snapshot (else print the diff)"
    )
    args = parser.parse_args(argv)

    old_rest = load_rest()
    old_graph = load_graphql()
    known = {key(r): r for r in old_rest}
    if args.from_prd:
        rest, graph = parse_prd(PRD.read_text(encoding="utf-8"))
        _say_diff("REST", *diff(known, (key(r) for r in rest)))
        _say_diff(
            "GraphQL mutations",
            *diff(
                (m["name"] for m in old_graph["mutations"]), (m["name"] for m in graph["mutations"])
            ),
        )
        if args.write:
            write_rest(rest, "PRD Appendix E (api.github.com 1.1.4, read 2026-11-09)")
            write_graphql(graph, "PRD Appendix F (schema.docs.graphql, read 2026-11-09)")
        return 0
    if args.rest:
        rest = parse_openapi(json.loads(_read_source(args.rest)), known)
        _say_diff("REST", *diff(known, (key(r) for r in rest)))
        if args.write:
            write_rest(rest, args.source or args.rest)
    if args.graphql:
        cats = {m["name"]: m["category"] for m in old_graph["mutations"]}
        graph = parse_graphql_sdl(_read_source(args.graphql), cats)
        _say_diff("GraphQL mutations", *diff(cats, (m["name"] for m in graph["mutations"])))
        if args.write:
            write_graphql(graph, args.source or args.graphql)
    if args.diff:
        theirs = parse_openapi(json.loads(_read_source(args.diff)), known)
        others = set()
        if ENTERPRISE_PATH.is_file():
            others = {
                key(r)
                for r in json.loads(ENTERPRISE_PATH.read_text(encoding="utf-8"))["operations"]
                if r.get("edition") != args.edition
            }
        # Only what neither api.github.com nor another edition already lists.
        only = [r for r in theirs if key(r) not in known and key(r) not in others]
        _say_diff(
            f"{args.edition} beside api.github.com",
            [key(r) for r in only],
            sorted(set(known) - {key(r) for r in theirs}),
        )
        if args.write:
            _enterprise_rows(args.edition, only, args.source or args.diff)
    if args.ghes_versions:

        def version(p: str) -> tuple[int, ...]:
            found = re.search(r"(\d+(?:\.\d+)+)", Path(p).name)
            return tuple(int(x) for x in found.group(1).split(".")) if found else (0,)

        spans: dict[str, list[str]] = {}
        for path in sorted(args.ghes_versions, key=version):
            label = ".".join(str(x) for x in version(path))
            for r in parse_openapi(json.loads(_read_source(path)), known):
                span = spans.setdefault(key(r), [label, label])
                span[1] = label
        print(f"GHES: {len(spans)} operations across {len(args.ghes_versions)} versions.")
        if args.write:
            head = {
                "_about": (
                    "First and last GitHub Enterprise Server version whose description has "
                    "each operation (scripts/github_api_snapshot.py --ghes-versions)."
                ),
                "source": args.source or "",
                "versions": [
                    ".".join(str(x) for x in version(v))
                    for v in sorted(args.ghes_versions, key=version)
                ],
            }
            text = json.dumps(head, indent=1)[:-2] + ',\n "operations": {\n'
            text += ",\n".join(
                f"  {json.dumps(k)}: {json.dumps(v)}" for k, v in sorted(spans.items())
            )
            GHES_VERSIONS_PATH.write_text(text + "\n }\n}\n", encoding="utf-8", newline="\n")
    if not any((args.rest, args.graphql, args.diff, args.ghes_versions)):
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
