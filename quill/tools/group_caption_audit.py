"""GATE-GROUP: a check box or radio button in a group says which group it is.

On Windows NVDA and JAWS do not reliably speak a ``wx.StaticBox`` caption when
focus moves into a control inside it, and a ``wx.RadioBox`` reads its choices
without its title (Jeff, Scribe Options, 2026-11-23). The cure is
:mod:`quill.ui.accessible_group`; this audit makes sure it is used:

* every ``wx.CheckBox`` or ``wx.RadioButton`` in a static box -- built with
  one as its parent (``box.GetStaticBox()``, a name bound to one, or a
  ``wx.StaticBox``), or added to a ``wx.StaticBoxSizer`` (the older layout,
  where the controls are the window's children) -- is bound to a name that
  the same function passes to ``describe_group``;
* no ``wx.RadioBox`` is built at all: ``GroupedRadioBox`` takes the same
  arguments and its choices carry the title.

The scan is source-level (``ast``), so it needs no display and no wx. A site
that truly cannot go through the helper is listed in :data:`ALLOWED` with the
reason, and the reason is the review.

Usage::

    python -m quill.tools.group_caption_audit            # the gated scope
    python -m quill.tools.group_caption_audit --all      # every UI module
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The modules the gate holds to the rule (repo-relative globs).
SCOPE: tuple[str, ...] = ("quill/ui/scribe_*.py",)

#: Every module with UI code in the family, for ``--all`` (the later pass).
FAMILY: tuple[str, ...] = (
    "quill/ui/**/*.py",
    "quill/apps/**/*.py",
    "standalone/*/**/*.py",
)

#: The helper itself builds the radio buttons it describes.
_HELPER_MODULE = "quill/ui/accessible_group.py"

#: ``key`` -> why that site cannot go through the helper. Empty, and should stay so.
ALLOWED: dict[str, str] = {}

_MEMBERS = frozenset({"CheckBox", "RadioButton"})
_DESCRIBE = "describe_group"


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    key: str
    problem: str


def _wx_class(func: ast.expr) -> str | None:
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == "wx":
            return func.attr
    return None


def _is_box_call(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "GetStaticBox":
        return True
    return _wx_class(func) == "StaticBox"


def _parent_arg(call: ast.Call) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == "parent":
            return keyword.value
    return call.args[0] if call.args else None


def _scopes(tree: ast.Module) -> Iterable[tuple[str, ast.AST]]:
    """Each function (by qualified name) and the module body itself."""
    yield "<module>", tree

    def walk(node: ast.AST, prefix: str) -> Iterable[tuple[str, ast.AST]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                yield from walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{child.name}"
                yield name, child
                yield from walk(child, f"{name}.")

    yield from walk(tree, "")


def _own_nodes(scope: ast.AST) -> Iterable[ast.AST]:
    """Nodes of *scope*, not descending into nested functions or classes."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def scan_source(source: str, rel: str) -> list[Finding]:
    """Every violation in one module's *source*; *rel* is its repo path."""
    if rel == _HELPER_MODULE:
        return []
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    findings: list[Finding] = []
    for qualname, scope in _scopes(tree):
        nodes = list(_own_nodes(scope))
        boxes: set[str] = set()
        sizers: set[str] = set()
        for node in nodes:
            if isinstance(node, ast.Assign) and _is_box_call(node.value):
                boxes.update(ast.unparse(target) for target in node.targets)
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and _wx_class(node.value.func) == "StaticBoxSizer"
            ):
                sizers.update(ast.unparse(target) for target in node.targets)
        added: set[str] = set()
        added_inline: set[int] = set()
        for node in nodes:
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"Add", "Insert", "Prepend"}
                and ast.unparse(node.func.value) in sizers
            ):
                for arg in node.args:
                    added.add(ast.unparse(arg))
                    added_inline.add(id(arg))
        described: set[str] = set()
        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name == _DESCRIBE:
                described.update(ast.unparse(arg) for arg in node.args[1:])
        counts: dict[str, int] = {}
        for node in sorted(
            (n for n in nodes if isinstance(n, ast.Call)), key=lambda n: (n.lineno, n.col_offset)
        ):
            cls = _wx_class(node.func)
            if cls not in _MEMBERS and cls != "RadioBox":
                continue
            counts[cls] = counts.get(cls, 0) + 1
            suffix = f"#{counts[cls]}" if counts[cls] > 1 else ""
            key = f"{rel}::{qualname}::wx.{cls}{suffix}"
            if key in ALLOWED:
                continue
            if cls == "RadioBox":
                findings.append(Finding(rel, node.lineno, key, "wx.RadioBox: use GroupedRadioBox"))
                continue
            holder = parents.get(node)
            target = ""
            if isinstance(holder, ast.Assign) and len(holder.targets) == 1:
                target = ast.unparse(holder.targets[0])
            elif isinstance(holder, ast.AnnAssign):
                target = ast.unparse(holder.target)
            parent = _parent_arg(node)
            in_box = parent is not None and (_is_box_call(parent) or ast.unparse(parent) in boxes)
            in_sizer = id(node) in added_inline or (bool(target) and target in added)
            if not (in_box or in_sizer):
                continue
            if not target:
                findings.append(
                    Finding(
                        rel, node.lineno, key, f"wx.{cls} in a static box is not bound to a name"
                    )
                )
            elif target not in described:
                findings.append(
                    Finding(
                        rel,
                        node.lineno,
                        key,
                        f"wx.{cls} {target} in a static box is not passed to describe_group",
                    )
                )
    return findings


def module_paths(globs: Sequence[str]) -> list[Path]:
    seen: dict[Path, None] = {}
    for pattern in globs:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.suffix == ".py" and "tests" not in path.relative_to(REPO_ROOT).parts:
                seen.setdefault(path, None)
    return list(seen)


def audit(globs: Sequence[str] = SCOPE) -> list[Finding]:
    findings: list[Finding] = []
    for path in module_paths(globs):
        rel = path.relative_to(REPO_ROOT).as_posix()
        findings.extend(scan_source(path.read_text(encoding="utf-8"), rel))
    return sorted(findings)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="scan every family UI module")
    args = parser.parse_args(argv)
    findings = audit(FAMILY if args.all else SCOPE)
    for finding in findings:
        print(f"{finding.path}:{finding.line}: {finding.problem}")
    files = len({finding.path for finding in findings})
    print(f"{len(findings)} site(s) in {files} module(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
