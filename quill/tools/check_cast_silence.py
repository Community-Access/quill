"""GATE-CAST-SILENT: nothing QUILL Cast does goes unsaid (qc.md P4, section 10).

Two shapes of silence, each of which was a real "the button did nothing":

1. **A status line written directly.** ``status.SetLabel(...)`` changes text a
   screen reader does not read. In Cast every status line goes through
   :func:`quill.ui.podcasts.say_status.say_status`, which speaks it -- or says
   at the call site, with ``speak=False``, why it does not.
2. **A failure handler that says nothing.** ``on_failure=lambda *_a: None``, or
   a handler whose body only logs, is background work failing where nobody can
   hear. Cast's failures go through
   :func:`quill.ui.podcasts.failure_report.report_failure`, or at least speak.

Scope: ``quill/ui/podcasts``, ``quill/apps/podcasts*.py`` and
``quill/ui/main_frame_podcast*.py`` -- QUILL Cast and the podcast code QUILL
shares with it. No allowlist: a new silent site is fixed, not excused.

Run: ``python -m quill.tools.check_cast_silence`` (exit 1 on any violation).
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GLOBS: tuple[str, ...] = (
    "quill/ui/podcasts/*.py",
    "quill/apps/podcasts*.py",
    "quill/ui/main_frame_podcast*.py",
)
#: The helper itself is the one place a status label is written directly.
_EXEMPT_FILES: frozenset[str] = frozenset({"quill/ui/podcasts/say_status.py"})
_LOGGERS: frozenset[str] = frozenset({"_log", "log", "logger", "_logger", "logging"})


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    reason: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.reason}"


def _name_of(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _root_name(node: ast.AST) -> str:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else ""


def _says_something(body: ast.AST) -> bool:
    """Whether a handler's body makes any call that is not only logging."""
    for node in ast.walk(body):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and _root_name(func) in _LOGGERS:
                continue
            return True
    return False


def scan_file(path: Path) -> list[Violation]:
    relative = path.relative_to(_REPO_ROOT).as_posix()
    if relative in _EXEMPT_FILES:
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    functions: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            functions.setdefault(node.name, node)
    found: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "SetLabel"
            and "status" in _name_of(func.value).lower()
        ):
            found.append(
                Violation(relative, node.lineno, "a status line set directly; use say_status")
            )
        for keyword in node.keywords:
            if keyword.arg != "on_failure":
                continue
            value = keyword.value
            if isinstance(value, ast.Lambda):
                if not _says_something(value.body):
                    found.append(
                        Violation(relative, value.lineno, "on_failure says nothing; report_failure")
                    )
                continue
            handler = functions.get(_name_of(value))
            if handler is not None and not _says_something(handler):
                found.append(
                    Violation(relative, value.lineno, "on_failure only logs; report_failure")
                )
    return found


def scan() -> list[Violation]:
    found: list[Violation] = []
    for pattern in _GLOBS:
        for path in sorted(_REPO_ROOT.glob(pattern)):
            found.extend(scan_file(path))
    return found


def main(argv: list[str] | None = None) -> int:
    del argv
    found = scan()
    if not found:
        print("GATE-CAST-SILENT: every Cast status line and failure is said.")
        return 0
    print("GATE-CAST-SILENT: silent sites found:")
    for violation in found:
        print(f"  {violation}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
