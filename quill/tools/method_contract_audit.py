"""Undefined-private-method call gate (CALL-1).

A call to ``self._name(...)`` where ``_name`` is never defined anywhere in the
``quill`` package is almost always a bug: a typo, a rename that missed a call
site, or a method deleted out from under its callers. This class has bitten the
app before (a Settings apply/reset path called several never-defined helpers and
crashed with ``AttributeError``).

Private names (single leading underscore) are app-defined — they are never
inherited wx/stdlib methods — so this audit can flag them with no false positives
from the framework. It scans the whole package via AST: it collects every defined
function/method name plus every assigned attribute (``self._x = ...`` and
class-body ``_x = ...`` / ``_x: T`` dataclass fields), then reports any
``self._x(...)`` call whose name is in neither set.

Run directly (``python -m quill.tools.method_contract_audit``) to print findings;
the gate lives in ``tests/unit/tools/test_method_contract_audit.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _collect(tree: ast.AST, defined: set[str], assigned: set[str]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
        elif isinstance(node, ast.ClassDef):
            # Class-body assignments / annotations are instance attributes once
            # constructed (incl. dataclass fields), so a call to one is valid.
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            assigned.add(target.id)
                elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    assigned.add(stmt.target.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and _is_self(target.value):
                    assigned.add(target.attr)
        elif isinstance(node, ast.AnnAssign):
            tgt = node.target
            if isinstance(tgt, ast.Attribute) and _is_self(tgt.value):
                assigned.add(tgt.attr)


def _is_self(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "self"


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def find_undefined_private_calls(root: Path | None = None) -> dict[str, list[str]]:
    """Return ``{name: ["<rel path>:<line>", ...]}`` for undefined ``self._x()`` calls."""
    base = root if root is not None else _PACKAGE_ROOT
    defined: set[str] = set()
    assigned: set[str] = set()
    call_sites: dict[str, list[str]] = {}

    trees: list[tuple[Path, ast.AST]] = []
    for path in _iter_python_files(base):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        trees.append((path, tree))
        _collect(tree, defined, assigned)

    for path, parsed in trees:
        for node in ast.walk(parsed):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            func = node.func
            name = func.attr
            if not _is_self(func.value):
                continue
            if not name.startswith("_") or name.startswith("__"):
                continue
            if name in defined or name in assigned:
                continue
            rel = path.relative_to(base).as_posix()
            call_sites.setdefault(name, []).append(f"{rel}:{func.lineno}")
    return call_sites


def main() -> int:
    findings = find_undefined_private_calls()
    if not findings:
        print("Method-contract audit passed: no undefined self._private() calls.")
        return 0
    print("Method-contract audit failed: calls to never-defined private methods:")
    for name in sorted(findings):
        print(f"- self.{name}(): {', '.join(findings[name])}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
