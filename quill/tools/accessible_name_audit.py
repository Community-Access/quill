"""Source-driven accessible-name inventory and gate (#1012 / GATE-A11Y-NAME).

macOS VoiceOver announces a control only by its own accessible name; the
neighbouring ``wx.StaticText`` that Windows screen readers use is never linked
(issue #1012). The fix has two layers:

* every modal dialog gets names inferred at show time by
  :func:`quill.ui.accessible_names.ensure_accessible_names`, wired into
  :func:`quill.ui.dialog_contract.show_modal_dialog`; and
* non-modal surfaces (frame chrome, editor surfaces, panes) name their
  controls explicitly via ``set_accessible_name`` / ``SetName`` /
  a constructor ``name=``.

This module is the gate that keeps both layers honest, in the mold of
:mod:`quill.tools.dialog_inventory`: it AST-scans every ``quill/**/*.py``
module for constructions of *labelable* wx controls (the classes VoiceOver
reads by window name — text fields, choices, lists, spins, ...), gives each a
**stable key** (``<module>::<qualname>::wx.<Class>[#n]``), detects whether the
site names the control **inline** (constructor ``name=``, a ``SetName`` /
``set_accessible_name`` call on the same target within the enclosing
function), and compares against the committed snapshot
(:data:`SNAPSHOT_PATH`), which classifies every site:

* ``named``            -- names itself inline (auto-verified by the scan).
* ``modal-hook``       -- lives in a dialog shown via ``show_modal_dialog``;
  the runtime walker names it from its neighbouring StaticText at show time.
* ``named-elsewhere``  -- named by code the inline scan cannot see (a factory
  whose caller names the control, a loop variable, ...).
* ``opt-out``          -- deliberately nameless (rare; justify in the diff).

The gate (``tests/unit/ui/test_accessible_name_inventory.py``) fails whenever
the live scan and the snapshot disagree, so a new labelable control cannot
land without a deliberate::

    python -m quill.tools.accessible_name_audit --write

whose diff the reviewer classifies: a control in a *modal* dialog keeps the
default ``modal-hook``; a control on a non-modal surface must either name
itself (flipping to ``named``) or carry an explicit ``named-elsewhere`` /
``opt-out``. The snapshot is therefore also the authoritative list of
deviations from the global fix.

Run directly to print the inventory, ``--write`` to regenerate the snapshot,
``--list <status>`` to list keys with one status.

Known precision limits (review the ``--write`` diff with these in mind):

* Inline-naming detection is *textual* within the enclosing function: if a
  variable is rebound to a second control and only the second is named, both
  construction sites scan as ``named``.
* The ``#n`` key suffix is a per-scope creation index: inserting or deleting a
  same-class construction shifts later keys, so a prior human classification
  can reattach to a different site on the next ``--write`` — check shifted
  keys in the diff, not just added/removed ones.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# Single source of truth for what "labelable" means — shared with the runtime
# walker so the gate and the fix can never drift apart. accessible_names has
# no module-level wx import, so this stays importable in bare CI.
from quill.ui.accessible_names import _LABELABLE_CLASSES

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = _REPO_ROOT / "quill"
SNAPSHOT_PATH = _REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "accessible_name_inventory.json"

NAMED = "named"
MODAL_HOOK = "modal-hook"
NAMED_ELSEWHERE = "named-elsewhere"
OPT_OUT = "opt-out"
STATUSES = frozenset({NAMED, MODAL_HOOK, NAMED_ELSEWHERE, OPT_OUT})

#: Helper callables that assign an accessible name to their first argument.
_NAMING_HELPERS = frozenset({"set_accessible_name"})


@dataclass(frozen=True, order=True)
class ControlSite:
    """A single labelable-control construction discovered in source."""

    key: str
    module: str
    qualname: str
    kind: str
    line: int
    #: ``True`` when the site names the control inline (auto-verified).
    named_inline: bool


def _wx_class_name(func: ast.expr) -> str | None:
    """Return ``<Class>`` for ``wx.<Class>(...)`` / ``wx.<mod>.<Class>(...)``.

    Also matches submodule aliases of the ``wx_<mod>`` convention
    (``import wx.grid as wx_grid`` → ``wx_grid.Grid(...)``).
    """
    if not isinstance(func, ast.Attribute):
        return None
    root = func.value
    # wx.TextCtrl / wx.stc.StyledTextCtrl / wx.dataview.DataViewListCtrl ...
    while isinstance(root, ast.Attribute):
        root = root.value
    if isinstance(root, ast.Name) and (root.id == "wx" or root.id.startswith("wx_")):
        return func.attr
    return None


def _unparse(node: ast.expr) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001 - defensive; unparse handles all exprs
        return ""


def _assignment_targets(parents: dict[ast.AST, ast.AST], call: ast.Call) -> list[str]:
    """Textual targets a construction is bound to (``self._t``, ``ctrl``, ...)."""
    node: ast.AST = call
    parent = parents.get(node)
    targets: list[str] = []
    while parent is not None:
        if isinstance(parent, ast.Assign) and parent.value is node:
            targets.extend(_unparse(t) for t in parent.targets)
            break
        if isinstance(parent, ast.AnnAssign) and parent.value is node:
            targets.append(_unparse(parent.target))
            break
        if isinstance(parent, ast.NamedExpr) and parent.value is node:
            targets.append(_unparse(parent.target))
            break
        # Only look through trivial wrappers (e.g. a cast) — a construction
        # used as a bare expression or a call argument has no target.
        if not isinstance(parent, (ast.Call, ast.Expr)):
            break
        if isinstance(parent, ast.Call) and node in parent.args:
            break
        node = parent
        parent = parents.get(node)
    return [t for t in targets if t]


def _enclosing_scope(parents: dict[ast.AST, ast.AST], node: ast.AST) -> ast.AST:
    """Nearest enclosing function (sync or async), else the module."""
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            return current
        current = parents.get(current)
    return node


def _names_target_inline(scope: ast.AST, targets: list[str]) -> bool:
    """True when *scope* names one of *targets* via SetName or a helper."""
    if not targets:
        return False
    wanted = set(targets)
    for sub in ast.walk(scope):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        # <target>.SetName(...)
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "SetName"
            and _unparse(func.value) in wanted
        ):
            return True
        # set_accessible_name(<target>, ...) — bare or attribute-qualified.
        helper = None
        if isinstance(func, ast.Name):
            helper = func.id
        elif isinstance(func, ast.Attribute):
            helper = func.attr
        if helper in _NAMING_HELPERS and sub.args and _unparse(sub.args[0]) in wanted:
            return True
    return False


class _ControlVisitor(ast.NodeVisitor):
    """Collect labelable-control constructions with stable qualname keys."""

    def __init__(self, module: str, parents: dict[ast.AST, ast.AST]) -> None:
        self._module = module
        self._parents = parents
        self._scope: list[str] = []
        self._seen: dict[str, int] = {}
        self.sites: list[ControlSite] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        cls = _wx_class_name(node.func)
        if cls in _LABELABLE_CLASSES:
            named = any(kw.arg == "name" for kw in node.keywords)
            if not named:
                targets = _assignment_targets(self._parents, node)
                scope = _enclosing_scope(self._parents, node)
                named = _names_target_inline(scope, targets)
            qualname = ".".join(self._scope) if self._scope else "<module>"
            base = f"{self._module}::{qualname}::wx.{cls}"
            index = self._seen.get(base, 0)
            self._seen[base] = index + 1
            key = base if index == 0 else f"{base}#{index + 1}"
            self.sites.append(
                ControlSite(
                    key=key,
                    module=self._module,
                    qualname=qualname,
                    kind=f"wx.{cls}",
                    line=node.lineno,
                    named_inline=named,
                )
            )
        self.generic_visit(node)


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def scan_module(path: Path) -> list[ControlSite]:
    """Scan one module for labelable-control construction sites."""
    module = path.relative_to(_REPO_ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    visitor = _ControlVisitor(module, _build_parent_map(tree))
    visitor.visit(tree)
    return visitor.sites


def scan_control_sites(root: Path = _PACKAGE_ROOT) -> list[ControlSite]:
    """Return every labelable-control site in the package, sorted by key."""
    sites: list[ControlSite] = []
    for path in sorted(root.rglob("*.py")):
        sites.extend(scan_module(path))
    return sorted(sites)


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_snapshot(
    sites: Iterable[ControlSite], previous: dict[str, str] | None = None
) -> dict[str, str]:
    """Map key -> status, preserving compatible prior classifications.

    Inline-named sites are always ``named`` (auto-verified). Unnamed sites
    keep their previous human classification when they had one; brand-new
    unnamed sites default to ``modal-hook``, which the diff reviewer must
    confirm (or fix the site / reclassify).
    """
    previous = previous or {}
    snapshot: dict[str, str] = {}
    for site in sites:
        if site.named_inline:
            snapshot[site.key] = NAMED
        else:
            prior = previous.get(site.key)
            snapshot[site.key] = prior if prior in (STATUSES - {NAMED}) else MODAL_HOOK
    return dict(sorted(snapshot.items()))


def write_snapshot(snapshot: dict[str, str], path: Path = SNAPSHOT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    parser.add_argument("--list", dest="list_status", help="list keys with one status")
    args = parser.parse_args(argv)

    sites = scan_control_sites()
    previous: dict[str, str] = {}
    if SNAPSHOT_PATH.exists():
        previous = load_snapshot()
    snapshot = build_snapshot(sites, previous)

    if args.write:
        write_snapshot(snapshot)
        print(f"Wrote {len(snapshot)} control sites to {SNAPSHOT_PATH}")
    if args.list_status:
        for key, status in snapshot.items():
            if status == args.list_status:
                print(key)
    if not args.write and not args.list_status:
        counts: dict[str, int] = {}
        for status in snapshot.values():
            counts[status] = counts.get(status, 0) + 1
        for status in sorted(counts):
            print(f"{status}: {counts[status]}")
        print(f"total: {len(snapshot)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
