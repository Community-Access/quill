"""GATE-RADIO-HELP: F1 help must ship with every radio surface and control.

Quill Radio answers F1 everywhere with two paragraphs: what the window is for
(:mod:`quill.core.radio.surface_help`, keyed by window title) and what the
focused control does (its ``SetHelpText``, its accessible name, and a role
line). Wiring is inherited -- the dialog contract's show paths bind F1 on
every window -- so the only way coverage can rot is content: a new window
with no purpose paragraph, or a new control with nothing authored. This gate
closes both holes, in the mold of :mod:`quill.tools.accessible_name_audit`:

**Titles.** Every ``wx.Frame`` / ``wx.Dialog`` constructed with a title in
the radio UI modules must resolve to a purpose via
``surface_help.is_known_title``. Titles are resolved from literals,
f-string prefixes, module constants, ``title=...`` parameter defaults, and
``self._title = "..."`` assignments; a construction whose title the scan
cannot resolve must be listed in :data:`TITLE_EXEMPT` with a reason.

**Controls.** Every helpable-control construction site (text fields, lists,
trees, buttons, ...) gets a stable key and one status in the committed
snapshot (:data:`SNAPSHOT_PATH`):

* ``helped``       -- calls ``SetHelpText`` inline (auto-verified by the scan).
* ``named-help``   -- its accessible name already carries the full teaching
  sentence ("Reload the highlighted source from the internet"), which F1
  composes with the role line; a deliberate, reviewed classification.
* ``help-elsewhere`` -- helped by code the inline scan cannot see (a factory,
  a loop, a later call).
* ``opt-out``      -- deliberately without help (rare; justify in the diff).

A brand-new site with no help and no prior classification snapshots as
``missing``, and the gate **fails on any ``missing``** -- so a new feature
cannot land without either authoring help or deliberately classifying why
not. Regenerate with::

    python -m quill.tools.radio_help_audit --write

and review the diff: every ``missing`` you commit is a failing build.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from quill.tools.accessible_name_audit import (
    _assignment_targets,
    _build_parent_map,
    _enclosing_scope,
    _unparse,
    _wx_class_name,
)
from quill.ui.accessible_names import _LABELABLE_CLASSES

_REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = _REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "radio_help_inventory.json"

#: The radio UI surface: everything the F1 experience must cover.
_SCAN_DIRS: tuple[str, ...] = ("quill/ui/radio",)
_SCAN_GLOBS: tuple[str, ...] = ("quill/apps/radio*.py",)

#: Controls a person can land on and wonder about. The labelable set (shared
#: with the accessible-name gate) plus the pressables it deliberately skips.
_HELPABLE_CLASSES = frozenset(_LABELABLE_CLASSES) | {"Button", "ToggleButton"}

HELPED = "helped"
NAMED_HELP = "named-help"
HELP_ELSEWHERE = "help-elsewhere"
OPT_OUT = "opt-out"
MISSING = "missing"
STATUSES = frozenset({HELPED, NAMED_HELP, HELP_ELSEWHERE, OPT_OUT})

#: Surface constructions whose titles the scan cannot resolve, with the
#: reason they are fine. Keyed ``<module>::<qualname>``.
TITLE_EXEMPT: dict[str, str] = {
    "quill/ui/radio/first_run_dialog.py::RadioFirstRunDialog.__init__": (
        "titles come from onboarding.SCREEN_TITLES; all three screens are in "
        "surface_help.PURPOSES, pinned by test_surface_help"
    ),
}


@dataclass(frozen=True, order=True)
class ControlSite:
    key: str
    module: str
    qualname: str
    kind: str
    line: int
    helped_inline: bool


@dataclass(frozen=True, order=True)
class TitleViolation:
    key: str
    line: int
    title: str
    reason: str


def _radio_paths() -> list[Path]:
    paths: list[Path] = []
    for rel in _SCAN_DIRS:
        paths.extend(sorted((_REPO_ROOT / rel).glob("*.py")))
    for pattern in _SCAN_GLOBS:
        paths.extend(sorted(_REPO_ROOT.glob(pattern)))
    return paths


def _helps_target_inline(scope: ast.AST, targets: list[str]) -> bool:
    """True when *scope* calls ``SetHelpText`` on one of *targets*."""
    if not targets:
        return False
    wanted = set(targets)
    for sub in ast.walk(scope):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "SetHelpText"
            and _unparse(func.value) in wanted
        ):
            return True
    return False


class _HelpVisitor(ast.NodeVisitor):
    """Collect helpable-control sites and surface-title constructions."""

    def __init__(self, module: str, tree: ast.Module) -> None:
        self._module = module
        self._parents = _build_parent_map(tree)
        self._scope: list[str] = []
        self._seen: dict[str, int] = {}
        self.sites: list[ControlSite] = []
        self.titles: list[tuple[str, int, str | None]] = []  # (key, line, title-or-None)
        #: Module constants (NAME = "literal") for title resolution.
        self._constants: dict[str, str] = {}
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                self._constants[node.targets[0].id] = node.value.value
        #: self._title = "literal" assignments and title="literal" parameter
        #: defaults anywhere in the module, for dialogs with dynamic titles.
        self._self_titles: list[str] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and _unparse(node.targets[0]) == "self._title"
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                self._self_titles.append(node.value.value)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                names = [a.arg for a in args.args + args.kwonlyargs]
                defaults = list(args.defaults) + list(args.kw_defaults)
                for arg_name, default in zip(names[-len(defaults) :], defaults, strict=False):
                    if (
                        arg_name == "title"
                        and isinstance(default, ast.Constant)
                        and isinstance(default.value, str)
                    ):
                        self._self_titles.append(default.value)

    # -- scope bookkeeping -------------------------------------------------------

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

    # -- collection --------------------------------------------------------------

    def _resolve_title(self, value: ast.expr) -> list[str] | None:
        """Every title this expression can carry, or None when unresolvable."""
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return [value.value]
        if isinstance(value, ast.JoinedStr) and value.values:
            first = value.values[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return [first.value]  # a prefix is enough for is_known_title
        if isinstance(value, ast.Name):
            constant = self._constants.get(value.id)
            if constant is not None:
                return [constant]
            if value.id == "title" and self._self_titles:
                return list(self._self_titles)
        if isinstance(value, ast.Attribute) and _unparse(value) == "self._title":
            return list(self._self_titles) or None
        return None

    def visit_Call(self, node: ast.Call) -> None:
        cls = _wx_class_name(node.func)
        qualname = ".".join(self._scope) if self._scope else "<module>"
        if cls in ("Frame", "Dialog"):
            for kw in node.keywords:
                if kw.arg == "title":
                    key = f"{self._module}::{qualname}"
                    resolved = self._resolve_title(kw.value)
                    if resolved is None:
                        self.titles.append((key, node.lineno, None))
                    else:
                        for candidate in resolved:
                            self.titles.append((key, node.lineno, candidate))
        if cls in _HELPABLE_CLASSES:
            helped = any(kw.arg == "helpText" for kw in node.keywords)
            if not helped:
                targets = _assignment_targets(self._parents, node)
                scope = _enclosing_scope(self._parents, node)
                helped = _helps_target_inline(scope, targets)
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
                    helped_inline=helped,
                )
            )
        self.generic_visit(node)


def scan() -> tuple[list[ControlSite], list[TitleViolation]]:
    """Every helpable-control site, and every title with no purpose."""
    from quill.core.radio import surface_help

    sites: list[ControlSite] = []
    violations: list[TitleViolation] = []
    for path in _radio_paths():
        module = path.relative_to(_REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _HelpVisitor(module, tree)
        visitor.visit(tree)
        sites.extend(visitor.sites)
        for key, line, title in visitor.titles:
            if key in TITLE_EXEMPT:
                continue
            if title is None:
                violations.append(
                    TitleViolation(
                        key=key,
                        line=line,
                        title="<unresolved>",
                        reason=(
                            "the scan cannot resolve this title; add it to "
                            "surface_help and TITLE_EXEMPT (with the reason), or "
                            "make the title a literal"
                        ),
                    )
                )
            elif not surface_help.is_known_title(title):
                violations.append(
                    TitleViolation(
                        key=key,
                        line=line,
                        title=title,
                        reason=(
                            "no purpose in quill/core/radio/surface_help.py -- a "
                            "window must say what it is for before it ships"
                        ),
                    )
                )
    return sorted(sites), sorted(violations)


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_snapshot(
    sites: Iterable[ControlSite], previous: dict[str, str] | None = None
) -> dict[str, str]:
    """Map key -> status. Inline-helped sites are always ``helped``; unhelped
    sites keep a valid prior classification, else snapshot as ``missing`` --
    which the gate refuses, so the classification is a deliberate act."""
    previous = previous or {}
    snapshot: dict[str, str] = {}
    for site in sites:
        if site.helped_inline:
            snapshot[site.key] = HELPED
        else:
            prior = previous.get(site.key)
            snapshot[site.key] = prior if prior in (STATUSES - {HELPED}) else MISSING
    return dict(sorted(snapshot.items()))


def write_snapshot(snapshot: dict[str, str], path: Path = SNAPSHOT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    parser.add_argument("--list", dest="list_status", help="list keys with one status")
    args = parser.parse_args(argv)

    sites, title_violations = scan()
    previous = load_snapshot() if SNAPSHOT_PATH.exists() else {}
    snapshot = build_snapshot(sites, previous)

    if args.write:
        write_snapshot(snapshot)
        print(f"Wrote {len(snapshot)} control sites to {SNAPSHOT_PATH}")
    if args.list_status:
        for key, status in snapshot.items():
            if status == args.list_status:
                print(key)
    failed = False
    for violation in title_violations:
        failed = True
        print(f"TITLE {violation.key}:{violation.line}: {violation.title!r} -- {violation.reason}")
    missing = [key for key, status in snapshot.items() if status == MISSING]
    if missing and not args.list_status:
        failed = True
        for key in missing:
            print(f"MISSING {key}: no SetHelpText and no reviewed classification")
    if not args.write and not args.list_status:
        counts: dict[str, int] = {}
        for status in snapshot.values():
            counts[status] = counts.get(status, 0) + 1
        for status in sorted(counts):
            print(f"{status}: {counts[status]}")
        print(f"total: {len(snapshot)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
