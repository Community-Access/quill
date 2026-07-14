"""Source-driven dialog inventory and registry gate (A11Y-4 / DLG-3).

``zfix.md`` (the Tier 4 Dialog Unification Plan) makes one rule non-negotiable:
**no dialog may exist in QUILL without being registered and classified**, and the
authoritative inventory is generated from source -- not hand-maintained in a
checklist. This module is that authority.

It scans every ``quill/**/*.py`` module via AST (no ``wx`` required) and records
every dialog *surface* -- the construction or invocation expression that puts a
modal/owned dialog in front of the user -- together with its sanctioned
classification:

* ``native``          -- stock wx dialogs (``wx.MessageDialog``,
  ``wx.RichMessageDialog``, ``wx.MessageBox``, choosers, text/file/dir pickers,
  progress, about). The native-first default.
* ``web``             -- sanctioned accessible web surfaces (``show_web_form``).
* ``hardened_custom`` -- a raw ``wx.Dialog(...)`` construction (the only allowed
  bespoke base; everything else must route through native or web).

Each surface gets a **stable key** independent of line numbers:
``<relative_module>::<enclosing_qualname>::<kind>`` (with a ``#n`` suffix when the
same kind is built more than once in the same scope). The committed snapshot
(:data:`SNAPSHOT_PATH`) maps every key to its classification. The gate
(``tests/unit/ui/test_dialog_inventory.py`` and the registry cross-check in
``check_banned_patterns``) fails whenever the live scan and the snapshot
disagree, so a new or moved dialog cannot land without a deliberate::

    python -m quill.tools.dialog_inventory --write

and the classification it produces is reviewed in the diff. That is the
"magical" gating zfix.md asks for: adding a dialog *forces* it into the registry.

Run directly (``python -m quill.tools.dialog_inventory``) to print the live
inventory, or with ``--write`` to regenerate the committed snapshot.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_ROOT = _REPO_ROOT / "quill"
SNAPSHOT_PATH = _REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "dialog_inventory.json"

#: Sanctioned classifications. A surface that cannot be classified into one of
#: these is "bespoke surface drift" and must be rejected by the gate.
NATIVE = "native"
WEB = "web"
HARDENED_CUSTOM = "hardened_custom"
SURFACES = frozenset({NATIVE, WEB, HARDENED_CUSTOM})

#: Stock wx dialog/message constructors that are accessible by construction and
#: are the native-first default for confirms, choices, text, files and progress.
_NATIVE_WX_DIALOGS = frozenset({
    "MessageDialog",
    "RichMessageDialog",
    "MessageBox",
    "GenericMessageDialog",
    "SingleChoiceDialog",
    "MultiChoiceDialog",
    "TextEntryDialog",
    "PasswordEntryDialog",
    "NumberEntryDialog",
    "FileDialog",
    "DirDialog",
    "ColourDialog",
    "FontDialog",
    "ProgressDialog",
    "GenericProgressDialog",
    "FindReplaceDialog",
    "AboutBox",
    "AboutDialog",
})

#: The only sanctioned bespoke base.
_HARDENED_WX_DIALOG = "Dialog"

#: Sanctioned web-surface helpers (bare-name function calls).
_WEB_HELPERS = frozenset({"show_web_form"})


@dataclass(frozen=True, order=True)
class DialogSurface:
    """A single dialog construction/invocation discovered in source."""

    key: str
    surface: str
    module: str
    qualname: str
    kind: str
    line: int


def _classify(kind: str) -> str | None:
    """Return the sanctioned surface for a dialog *kind*, or ``None``."""
    if kind == f"wx.{_HARDENED_WX_DIALOG}":
        return HARDENED_CUSTOM
    if kind.startswith("wx.") and kind[3:] in _NATIVE_WX_DIALOGS:
        return NATIVE
    if kind in _WEB_HELPERS:
        return WEB
    return None


class _DialogVisitor(ast.NodeVisitor):
    """Collect dialog surfaces with a stable, line-independent qualname key."""

    def __init__(self, module: str) -> None:
        self._module = module
        self._scope: list[str] = []
        self._seen: dict[str, int] = {}
        self.surfaces: list[DialogSurface] = []

    # -- scope tracking -------------------------------------------------
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # A `class X(wx.Dialog)` subclass is a dialog surface even though it
        # never contains a bare `wx.Dialog(...)` call site — without this the
        # registry was blind to subclass-style dialogs (#802 review). Recorded
        # inside the class scope so the hardening contract can inspect the
        # class body.
        self._scope.append(node.name)
        for base in node.bases:
            kind = self._call_kind(base)
            if kind is None:
                continue
            surface = _classify(kind)
            if surface is not None:
                self._record(f"subclass:{kind}", surface, node.lineno)
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

    # -- detection ------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        kind = self._call_kind(node.func)
        if kind is not None:
            surface = _classify(kind)
            if surface is not None:
                self._record(kind, surface, node.lineno)
        self.generic_visit(node)

    @staticmethod
    def _call_kind(func: ast.expr) -> str | None:
        """Return ``wx.<Name>`` or the bare helper name for a call target."""
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "wx"
        ):
            return f"wx.{func.attr}"
        if isinstance(func, ast.Name):
            return func.id
        return None

    def _record(self, kind: str, surface: str, line: int) -> None:
        qualname = ".".join(self._scope) if self._scope else "<module>"
        base = f"{self._module}::{qualname}::{kind}"
        index = self._seen.get(base, 0)
        self._seen[base] = index + 1
        key = base if index == 0 else f"{base}#{index + 1}"
        self.surfaces.append(
            DialogSurface(
                key=key,
                surface=surface,
                module=self._module,
                qualname=qualname,
                kind=kind,
                line=line,
            )
        )


def scan_module(path: Path) -> list[DialogSurface]:
    """Scan one module for dialog surfaces."""
    module = path.relative_to(_REPO_ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    visitor = _DialogVisitor(module)
    visitor.visit(tree)
    return visitor.surfaces


def scan_dialog_surfaces(root: Path = _PACKAGE_ROOT) -> list[DialogSurface]:
    """Return every dialog surface in the package, sorted by stable key."""
    surfaces: list[DialogSurface] = []
    for path in sorted(root.rglob("*.py")):
        surfaces.extend(scan_module(path))
    return sorted(surfaces)


def surface_map(surfaces: Iterable[DialogSurface]) -> dict[str, str]:
    """Map stable key -> classification (the committed registry shape)."""
    return {surface.key: surface.surface for surface in surfaces}


def load_snapshot() -> dict[str, str]:
    return dict(json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8")))


def write_snapshot() -> dict[str, str]:
    registry = surface_map(scan_dialog_surfaces())
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the committed dialog registry snapshot.",
    )
    args = parser.parse_args()
    if args.write:
        registry = write_snapshot()
        print(f"Wrote {len(registry)} dialog surfaces to {SNAPSHOT_PATH}")
        return 0
    surfaces = scan_dialog_surfaces()
    counts: dict[str, int] = {}
    for surface in surfaces:
        counts[surface.surface] = counts.get(surface.surface, 0) + 1
    print(f"QUILL exposes {len(surfaces)} dialog surfaces:")
    for surface_name in sorted(counts):
        print(f"  {surface_name}: {counts[surface_name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
