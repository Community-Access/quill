"""GATE-BULK-COUNT: a verb that touches many rows says how many.

The rule (list.md 11.4, from 14.2): **every action that acts on more than one
row ends by saying eligible / done / skipped.** "Removed downloads" tells a
listener who cannot see the list nothing at all -- not whether it meant two
files or two hundred, and not whether the three it could not touch were
mentioned. Download All was made to count on 2026-08-24; this gate is what
keeps the other forty honest, and what stops the forty-first shipping without
it.

**What is scanned.** Every function in the podcast and radio UI, and in the
app frames, whose name reads as a bulk verb: one of its snake_case words is
``all``, ``bulk``, ``batch``, ``many``, ``multi`` or ``every``. Name-based on
purpose -- the alternative is guessing from the body whether a loop is over
rows or over columns, and a gate that guesses is a gate people learn to
ignore.

**What each site is.** One status per function, in the committed snapshot
(:data:`SNAPSHOT_PATH`):

* ``counted``      -- auto-verified: the function announces something built
  from a count (``len(...)``, a ``Counted``/``DownloadBatch`` sentence, or a
  local name holding one).
* ``counts-elsewhere`` -- it delegates to a helper that counts (the prompt
  functions in ``show_actions``, ``show_downloads``); a reviewed
  classification, because the scan cannot follow the call.
* ``single-row``   -- the name reads bulk, the verb is not ("select_all" in a
  picker changes a selection, it does not act on rows).
* ``no-announce``  -- a pure computation or a UI-state helper with nothing to
  say; the caller announces.
* ``opt-out``      -- deliberately silent (rare; justify in the diff).

A brand-new bulk function with no counted announcement and no classification
snapshots as ``missing``, and the gate **fails on any ``missing``**.

Regenerate with::

    python -m quill.tools.bulk_count_audit --write

and review the diff: every ``missing`` you commit is a failing build.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path

from quill.tools.help_audit import REPO_ROOT, resolve_paths

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "bulk_count_inventory.json"

#: Where bulk verbs live in the two apps this rule is about.
_SCAN_DIRS: tuple[str, ...] = ("quill/ui/podcasts", "quill/ui/radio")
_SCAN_GLOBS: tuple[str, ...] = (
    "quill/apps/podcasts*.py",
    "quill/apps/radio*.py",
    "quill/ui/main_frame_podcast*.py",
)

#: Whole snake_case words that read as "this acts on more than one row".
#: Matched as *words*, not substrings -- "install" and "allowed" contain
#: "all" and are not bulk verbs, and a gate that flags them is a gate people
#: learn to click past.
_BULK_WORDS: frozenset[str] = frozenset({"all", "bulk", "batch", "many", "multi", "every"})

#: Functions whose name is a bulk word but whose job is not a bulk verb.
_NAME_EXEMPT: frozenset[str] = frozenset()

COUNTED = "counted"
COUNTS_ELSEWHERE = "counts-elsewhere"
SINGLE_ROW = "single-row"
NO_ANNOUNCE = "no-announce"
OPT_OUT = "opt-out"
MISSING = "missing"
STATUSES = frozenset({COUNTED, COUNTS_ELSEWHERE, SINGLE_ROW, NO_ANNOUNCE, OPT_OUT})

#: Calls that speak to the listener.
_ANNOUNCE_NAMES: frozenset[str] = frozenset({
    "_announce",
    "announce",
    "_set_status",
    "_announce_now",
    "speak",
})

#: Callables whose result is a counted sentence by construction.
_COUNTED_CALLS: frozenset[str] = frozenset({"sentence", "spoken_summary"})

#: Names that are a count wherever they appear, in this family's house style.
_COUNT_NAMES: frozenset[str] = frozenset({
    "count",
    "removed",
    "restored",
    "queued",
    "added",
    "changed",
    "skipped",
    "started",
    "failed",
    "eligible",
    "waiting",
})


@dataclass(frozen=True, order=True)
class BulkSite:
    key: str
    module: str
    qualname: str
    line: int
    counted_inline: bool


def _is_bulk_name(name: str) -> bool:
    if name in _NAME_EXEMPT or name.startswith("__"):
        return False
    return bool(_BULK_WORDS & set(name.lower().strip("_").split("_")))


def _counted_names(node: ast.AST) -> set[str]:
    """Local names in this function that hold a number, or a sentence built
    from one.

    Seeded from ``x = len(...)`` / ``sum(...)`` / ``.sentence(...)`` and from
    the tallying idiom ``changed = 0`` ... ``changed += 1``, then grown to a
    fixed point so ``message = f"Added {added}..."`` counts as counted too.
    That last step is what makes the gate believe the code this family
    actually writes, rather than only the shape it was first taught.
    """
    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name):
            names.add(sub.target.id)
    for _pass in range(4):
        before = len(names)
        for sub in ast.walk(node):
            if not isinstance(sub, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                continue
            value = getattr(sub, "value", None)
            if value is None or not _mentions_a_count(value, names):
                continue
            targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]  # type: ignore[list-item]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        if len(names) == before:
            break
    return names


def _announces_a_count(node: ast.AST) -> bool:
    """True when this function speaks something built from a number."""
    names = _counted_names(node)
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name not in _ANNOUNCE_NAMES:
            continue
        for arg in list(sub.args) + [kw.value for kw in sub.keywords]:
            if _mentions_a_count(arg, names):
                return True
    return False


def _mentions_a_count(node: ast.AST, names: set[str] | None = None) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in ("len", "sum") or name in _COUNTED_CALLS:
                return True
            # A helper that says "count" in its name returns one: the count
            # need not be computed in the same function to be spoken there.
            if "count" in name.lower():
                return True
        if isinstance(sub, ast.Name):
            if sub.id in _COUNT_NAMES:
                return True
            if names is not None and sub.id in names:
                return True
    return False


def scan() -> list[BulkSite]:
    """Every bulk-named function in the two apps, and whether it counts."""
    sites: list[BulkSite] = []
    for path in resolve_paths(_SCAN_DIRS, _SCAN_GLOBS):
        module = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        scope: list[str] = []

        def walk(node: ast.AST, scope: list[str] = scope, module: str = module) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    scope.append(child.name)
                    walk(child)
                    scope.pop()
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if _is_bulk_name(child.name):
                        qualname = ".".join([*scope, child.name])
                        sites.append(
                            BulkSite(
                                key=f"{module}::{qualname}",
                                module=module,
                                qualname=qualname,
                                line=child.lineno,
                                counted_inline=_announces_a_count(child),
                            )
                        )
                    scope.append(child.name)
                    walk(child)
                    scope.pop()
                else:
                    walk(child)

        walk(tree)
    return sorted(sites)


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_snapshot(sites: list[BulkSite], previous: dict[str, str] | None = None) -> dict[str, str]:
    """Map key -> status. Inline-counted sites are always ``counted``; the
    rest keep a valid prior classification, else snapshot as ``missing``."""
    previous = previous or {}
    snapshot: dict[str, str] = {}
    for site in sites:
        if site.counted_inline:
            snapshot[site.key] = COUNTED
        else:
            prior = previous.get(site.key)
            snapshot[site.key] = prior if prior in (STATUSES - {COUNTED}) else MISSING
    return dict(sorted(snapshot.items()))


def write_snapshot(snapshot: dict[str, str], path: Path = SNAPSHOT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    parser.add_argument("--list", dest="list_status", help="list keys with one status")
    args = parser.parse_args(argv)

    sites = scan()
    previous = load_snapshot() if SNAPSHOT_PATH.exists() else {}
    snapshot = build_snapshot(sites, previous)

    if args.write:
        write_snapshot(snapshot)
        print(f"Wrote {len(snapshot)} bulk-action sites to {SNAPSHOT_PATH}")
    if args.list_status:
        for key, status in snapshot.items():
            if status == args.list_status:
                print(key)
        return 0
    missing = [key for key, status in snapshot.items() if status == MISSING]
    for key in missing:
        print(f"MISSING {key}: acts on many rows but announces no count")
    if not args.write:
        counts: dict[str, int] = {}
        for status in snapshot.values():
            counts[status] = counts.get(status, 0) + 1
        for status in sorted(counts):
            print(f"{status}: {counts[status]}")
        print(f"total: {len(snapshot)}")
        if missing:
            print("Regenerate with: python -m quill.tools.bulk_count_audit --write")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
