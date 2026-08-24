"""GATE-REACH: a documented surface must be reachable from a running app.

QUILL Cast's user guide described three welcome screens for two releases. The
dialog existed, was well written, and had its own passing tests. Nothing in the
app ever called it (list.md 12.3).

Every gate we had ran in the wrong direction. ``check_help_coverage`` asks
whether a *feature* has documentation; the two ``*_help_audit`` gates ask
whether a *window in the source* has an authored purpose. All of them start
from the code and look for the words. Nothing started from a surface and asked
**"can anybody get here?"**

That question has a precise, cheap form: a module under ``quill/ui`` that
defines a window is dead unless some app entry point can reach it by imports.
Not "is it mentioned somewhere" -- ``first_run_dialog`` was mentioned by its own
tests, and by the ``maybe_run_first_run`` helper that nothing called. Reachable
means: start at the app entries and follow imports; if you never arrive, no
listener ever will either.

**Tests do not count as callers**, which is the whole point. A surface reached
only from ``tests/`` is a surface with passing tests and no way in -- exactly
the shape that shipped.

Static and conservative. Import graphs cannot see a plugin registry or a
string-keyed dispatch, so anything genuinely reached that way is *classified*
in the snapshot rather than argued about -- and the classification is the
review. Regenerate with::

    python -m quill.tools.surface_reachability_audit --write
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from functools import cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "surface_reachability.json"

#: Where a running app starts. Everything a listener can reach is reachable
#: from one of these by following imports.
ENTRY_GLOBS: tuple[str, ...] = (
    "quill/__main__.py",
    "quill/apps/*.py",
    "quill/ui/main_frame*.py",
)

#: A module *defines a surface* when it builds a window or a modal. These are
#: the constructions that put something on screen and therefore have to be
#: reachable; a module of pure helpers is not a surface and is not audited.
_SURFACE_CALLS = ("wx.Dialog", "wx.Frame", "ShowModal", "_show_modal_dialog")

REACHABLE = "reachable"
#: Reached by something the import graph cannot see -- a registry, a
#: string-keyed dispatch, a Quillin. A reviewed classification, and the review
#: is naming which mechanism in the diff.
DYNAMIC = "dynamic"
#: Deliberately unreachable for now (a surface behind an unreleased flag).
PARKED = "parked"
UNREACHABLE = "unreachable"

STATUSES = frozenset({REACHABLE, DYNAMIC, PARKED})


def _module_name(path: Path) -> str:
    return path.relative_to(REPO_ROOT).with_suffix("").as_posix().replace("/", ".")


# Parsed once per file per process: the walk revisits a module every time a
# different entry point imports it, and the suite builds the snapshot more
# than once. The tree does not change under a single run.
@cache
def _imports(path: Path) -> frozenset[str]:
    """Every ``quill.*`` module this one imports, at any nesting.

    Local imports inside functions count: this codebase uses them constantly to
    keep import time down, and a surface reached only from a function-local
    import is every bit as reachable as one reached from the top of the file.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return frozenset()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names if alias.name.startswith("quill"))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("quill"):
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return frozenset(found)


@cache
def _defines_surface(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    return any(token in text for token in _SURFACE_CALLS)


def entry_modules() -> list[Path]:
    found: list[Path] = []
    for pattern in ENTRY_GLOBS:
        found.extend(sorted(REPO_ROOT.glob(pattern)))
    return found


def reachable_modules() -> set[str]:
    """Every ``quill`` module an app entry point can reach by imports."""
    by_name = {
        _module_name(path): path
        for path in REPO_ROOT.glob("quill/**/*.py")
        if "_vendor" not in path.parts
    }
    seen: set[str] = set()
    queue = [_module_name(path) for path in entry_modules()]
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        path = by_name.get(name)
        if path is None:
            continue
        for imported in _imports(path):
            # ``from x import y`` may name a module or a symbol inside one;
            # both spellings are queued and the unknown one falls out above.
            if imported not in seen:
                queue.append(imported)
    return seen


def surface_modules() -> list[str]:
    """Every module under ``quill/ui`` that puts something on screen."""
    return sorted(
        _module_name(path)
        for path in REPO_ROOT.glob("quill/ui/**/*.py")
        if path.name != "__init__.py" and _defines_surface(path)
    )


def build_snapshot() -> dict[str, str]:
    reached = reachable_modules()
    previous = load_snapshot()
    out: dict[str, str] = {}
    for module in surface_modules():
        if module in reached:
            out[module] = REACHABLE
            continue
        # Keep a reviewed classification; anything else is a new problem.
        prior = previous.get(module, "")
        out[module] = prior if prior in STATUSES and prior != REACHABLE else UNREACHABLE
    return out


def load_snapshot() -> dict[str, str]:
    try:
        raw = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def write_snapshot(snapshot: dict[str, str]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({k: snapshot[k] for k in sorted(snapshot)}, indent=2, ensure_ascii=False)
    SNAPSHOT_PATH.write_text(body + "\n", encoding="utf-8", newline="\n")


def documented_surfaces() -> dict[str, list[str]]:
    """Window names the user guides bold, per guide.

    Used for the human half of the report: a surface named in the docs and
    absent from the code is the other direction of the same fault, and the
    guides are where somebody would have read about those welcome screens.
    """
    found: dict[str, list[str]] = {}
    for guide in sorted(REPO_ROOT.glob("standalone/*/docs/userguide.md")):
        text = guide.read_text(encoding="utf-8", errors="replace")
        names = sorted({
            match.strip()
            for match in re.findall(r"\*\*([A-Z][A-Za-z0-9 ']{2,40}?)\.\.\.\*\*", text)
        })
        if names:
            found[guide.relative_to(REPO_ROOT).as_posix()] = names
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    args = parser.parse_args()

    snapshot = build_snapshot()
    if args.write:
        write_snapshot(snapshot)

    stored = load_snapshot()
    unreachable = sorted(k for k, v in snapshot.items() if v == UNREACHABLE)
    drifted = sorted(k for k, v in snapshot.items() if stored.get(k) != v)

    for module in unreachable:
        print(
            f"UNREACHABLE {module}: defines a window that no app entry point can "
            "reach by imports. Wire it up, or classify it 'dynamic' (reached by a "
            "registry the import graph cannot see) or 'parked' with a reason."
        )
    if drifted and not args.write:
        for module in drifted:
            print(f"DRIFT {module}: {stored.get(module, '<new>')} -> {snapshot[module]}")
    if unreachable or (drifted and not args.write):
        print("Regenerate with: python -m quill.tools.surface_reachability_audit --write")
        return 1
    print(f"Surface reachability: {len(snapshot)} surface module(s), all reachable or reviewed.")
    return 0


if __name__ == "__main__":  # pragma: no cover - the gate's entry point
    raise SystemExit(main())
