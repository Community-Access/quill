"""Find window sizes written in raw pixels (GATE-DPI, #1702).

Every QuillVille app declares itself per-monitor DPI aware
(``quill/platform/windows/dpi_awareness.py``), so Windows no longer stretches
it. That is what makes text sharp at 150 and 200 percent -- and it is also
what makes a size written as plain pixels too small there. So every fixed
size has to go through ``FromDIP`` or :mod:`quill.ui.dpi`, and this audit
finds the ones that do not:

- a ``size=`` argument that is a two-element tuple, list or ``wx.Size(...)``
  holding a positive integer literal;
- ``SetSize``, ``SetMinSize``, ``SetMaxSize``, ``SetInitialSize``,
  ``SetClientSize``, ``SetMinClientSize``, ``SetMaxClientSize`` and
  ``SetSizeHints`` called with one, either as a pair or as plain integers;
- the same pair as ``default_size=``, as a ``size`` parameter's default, or
  held in a module constant (``_SIZE = (720, 520)``) passed on unconverted;
- a list column width: ``SetColumnWidth(col, 200)``, ``InsertColumn(...,
  width=200)`` or its fourth positional argument, and ``width=`` on
  ``AppendTextColumn`` / ``AppendColumn`` and friends.

Only a positive integer *literal* counts. ``-1`` means "let the sizer decide"
and needs no conversion; a size computed from a text extent or a sizer is
already in real pixels and must not be converted twice. A literal wrapped in
``FromDIP(...)``, ``dip(...)`` or ``dip_size(...)`` is converted, so it is not
reached by the scan at all.

Run ``python -m quill.tools.fixed_pixel_audit`` to list every finding.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The trees the gate covers: every UI module a QuillVille app is built from.
SCAN_ROOTS: tuple[str, ...] = (
    "quill/ui",
    "quill/apps",
    "standalone/social/quill_social/ui",
)

SIZE_METHODS = frozenset({
    "SetSize",
    "SetMinSize",
    "SetMaxSize",
    "SetInitialSize",
    "SetClientSize",
    "SetMinClientSize",
    "SetMaxClientSize",
    "SetSizeHints",
})
COLUMN_WIDTH_KW_METHODS = frozenset({
    "InsertColumn",
    "AppendColumn",
    "AppendTextColumn",
    "AppendIconTextColumn",
    "AppendToggleColumn",
    "AppendProgressColumn",
    "AppendDateColumn",
    "AppendBitmapColumn",
})


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    #: The literal (or pair) node that holds raw pixels.
    node: ast.AST
    #: The call the literal is an argument of (or the function it defaults).
    call: ast.AST


def _is_pixel(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and type(node.value) is int and node.value > 0


def _pair_elements(node: ast.AST) -> list[ast.AST] | None:
    if isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) == 2:
        return list(node.elts)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Size"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "wx"
        and len(node.args) == 2
        and not node.keywords
    ):
        return list(node.args)
    return None


def _is_pixel_pair(node: ast.AST) -> bool:
    elements = _pair_elements(node)
    return elements is not None and any(_is_pixel(e) for e in elements)


def _method_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _is_raw(node: ast.AST, constants: frozenset[str]) -> bool:
    """A literal pixel pair, or a module constant holding one, used as is."""
    if _is_pixel_pair(node):
        return True
    return isinstance(node, ast.Name) and node.id in constants


def _pixel_constants(tree: ast.Module) -> frozenset[str]:
    """Module-level names bound to a pixel pair (``_SIZE = (720, 520)``)."""
    names: set[str] = set()
    for stmt in tree.body:
        targets: list[ast.expr] = []
        if isinstance(stmt, ast.Assign):
            targets, value = stmt.targets, stmt.value
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            targets, value = [stmt.target], stmt.value
        else:
            continue
        if _is_pixel_pair(value):
            names.update(t.id for t in targets if isinstance(t, ast.Name))
    return frozenset(names)


def _call_findings(
    call: ast.Call, constants: frozenset[str] = frozenset()
) -> Iterator[tuple[str, ast.AST]]:
    for keyword in call.keywords:
        if keyword.arg in {"size", "default_size"} and _is_raw(keyword.value, constants):
            yield f"{keyword.arg}=", keyword.value
    name = _method_name(call)
    if name in SIZE_METHODS:
        if len(call.args) == 1 and _is_raw(call.args[0], constants):
            yield name, call.args[0]
        elif 2 <= len(call.args) <= 4 and not (name == "SetSize" and len(call.args) == 4):
            for arg in call.args:
                if _is_pixel(arg):
                    yield name, arg
        for keyword in call.keywords:
            if keyword.arg in {"minW", "minH", "maxW", "maxH", "width", "height"} and _is_pixel(
                keyword.value
            ):
                yield name, keyword.value
    if name == "SetColumnWidth" and len(call.args) == 2 and _is_pixel(call.args[1]):
        yield name, call.args[1]
    if name in COLUMN_WIDTH_KW_METHODS:
        for keyword in call.keywords:
            if keyword.arg == "width" and _is_pixel(keyword.value):
                yield f"{name} width=", keyword.value
        if name == "InsertColumn" and len(call.args) >= 4 and _is_pixel(call.args[3]):
            yield f"{name} width", call.args[3]


def scan_source(source: str, path: str = "<source>") -> list[Finding]:
    """Every raw-pixel size in ``source``."""
    tree = ast.parse(source, filename=path)
    constants = _pixel_constants(tree)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kind, literal in _call_findings(node, constants):
                findings.append(Finding(path, literal.lineno, kind, literal, node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # A ``size=(560, 400)`` parameter default is a raw size the body
            # passes straight on; default to ``None`` and convert there.
            for arg, default in _defaults(node.args):
                if (arg.arg == "size" or arg.arg.endswith("_size")) and _is_pixel_pair(default):
                    findings.append(Finding(path, default.lineno, "default", default, node))
    findings.sort(key=lambda f: (f.line, getattr(f.node, "col_offset", 0)))
    return findings


def _defaults(args: ast.arguments) -> Iterator[tuple[ast.arg, ast.expr]]:
    positional = [*args.posonlyargs, *args.args]
    yield from zip(positional[len(positional) - len(args.defaults) :], args.defaults, strict=True)
    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        if default is not None:
            yield arg, default


def iter_scanned_files(root: Path = REPO_ROOT) -> Iterator[Path]:
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if base.is_dir():
            yield from sorted(base.rglob("*.py"))


def scan_tree(root: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_scanned_files(root):
        relative = path.relative_to(root).as_posix()
        findings.extend(scan_source(path.read_text(encoding="utf-8"), relative))
    return findings


def main(argv: list[str] | None = None) -> int:
    findings = scan_tree()
    for finding in findings:
        print(f"{finding.path}:{finding.line}: raw pixel size in {finding.kind}")
    print(f"{len(findings)} raw pixel size(s); wrap each in FromDIP, dip() or dip_size().")
    return 1 if findings else 0


if __name__ == "__main__":  # pragma: no cover - the gate's entry point
    sys.exit(main())
