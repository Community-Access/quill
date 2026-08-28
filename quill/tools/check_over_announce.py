"""Over-announce gate (GATE-13): speak only what the screen reader does not say.

The mirror of ``check_announce_gap`` (GATE-12). That gate catches a dialog
that updates a status label *silently*; this one catches the opposite
failure, which no user ever files as a bug: an app with a direct speech
channel narrating things JAWS, NVDA and Narrator were going to say anyway.
A duplicated announcement is absorbed as "this app is chatty" and paid for
on every occurrence, forever. The rule (from EdSharp 5.0's own regression
fix, imported 2026-08-27): the screen reader already announces window and
dialog titles, focus moves, control names, roles and states, and selection
changes -- the app must announce only what it alone knows.

Three mechanical patterns, each a real way to say something twice:

1. **An announcement inside an ``EVT_SET_FOCUS``-only handler.** Focus
   arrival is the one event every screen reader narrates on its own;
   anything spoken from a handler that exists *for* focus races or repeats
   the reader's own announcement. (Handlers found by name from
   ``Bind(wx.EVT_SET_FOCUS, ...)`` sites, lambdas included. A handler also
   bound to key or mouse events -- a shared caret-activity handler -- is
   not a focus handler and is not flagged.)
2. **Announcing a window title**: any announce-style call whose sole
   argument is ``<x>.GetTitle()``. The reader said the title when the
   window opened.
3. **Announcing a title literal**: an announce-style call whose sole
   argument is a string literal that also appears as a ``title=`` literal
   in the same file.

Deliberately NOT flagged: announcing a status label after ``SetLabel``
(``self._announce(self._status.GetLabel())``) -- that is GATE-12's *fix*
pattern, because label changes on an unfocused StaticText are exactly what
the reader does not say.

Run directly::

    python -m quill.tools.check_over_announce

or via pytest (``tests/unit/tools/test_over_announce.py``). Exit code is
non-zero when any violation is found.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_SCAN_DIRS = ("quill/ui", "quill/apps", "quill/devtools")

#: A call is announce-style when its callable name contains this stem.
#: Catches announce, _announce, _announce_fn, announce_cb, announce_status...
_ANNOUNCE_STEM = "announce"

#: Files allowed to break the rule, with the reason. Keep short.
_ALLOWLIST: dict[str, str] = {}

_TITLE_KWARG_RE = re.compile(r'title\s*=\s*"([^"\n]{3,})"')


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    reason: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.reason}"


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _is_announce_call(node: ast.Call) -> bool:
    return _ANNOUNCE_STEM in _call_name(node).lower()


def _sole_arg(node: ast.Call) -> ast.expr | None:
    if len(node.args) == 1:
        return node.args[0]
    return None


def _is_get_title_call(expr: ast.expr) -> bool:
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "GetTitle"
    )


def _focus_handler_names(tree: ast.AST) -> set[str]:
    """Names bound to ``EVT_SET_FOCUS`` and to nothing else.

    A handler also bound to key, mouse or other events (a shared
    caret-activity handler, say) is not *about* focus, so an announcement
    inside it is judged on its own merits by the other checks.
    """
    focus_bound: set[str] = set()
    otherwise_bound: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "Bind" or len(node.args) < 2:
            continue
        event = node.args[0]
        handler = node.args[1]
        name = ""
        if isinstance(handler, ast.Attribute):
            name = handler.attr
        elif isinstance(handler, ast.Name):
            name = handler.id
        if not name:
            continue  # A lambda handler is checked in place, below.
        if isinstance(event, ast.Attribute) and event.attr == "EVT_SET_FOCUS":
            focus_bound.add(name)
        else:
            otherwise_bound.add(name)
    return focus_bound - otherwise_bound


def _lambda_focus_announces(tree: ast.AST) -> list[int]:
    """Lines of announce calls inside lambdas bound to EVT_SET_FOCUS."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "Bind" or len(node.args) < 2:
            continue
        event = node.args[0]
        if not (isinstance(event, ast.Attribute) and event.attr == "EVT_SET_FOCUS"):
            continue
        handler = node.args[1]
        if isinstance(handler, ast.Lambda):
            for inner in ast.walk(handler):
                if isinstance(inner, ast.Call) and _is_announce_call(inner):
                    lines.append(inner.lineno)
    return lines


def _check_file(path: Path) -> list[Violation]:
    rel = path.relative_to(_REPO_ROOT).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    if _ANNOUNCE_STEM not in text.lower():
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    violations: list[Violation] = []
    title_literals = set(_TITLE_KWARG_RE.findall(text))
    focus_handlers = _focus_handler_names(tree)

    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        in_focus_handler = func.name in focus_handlers
        for node in ast.walk(func):
            if not isinstance(node, ast.Call) or not _is_announce_call(node):
                continue
            if in_focus_handler:
                violations.append(
                    Violation(
                        rel,
                        node.lineno,
                        f"announce inside EVT_SET_FOCUS handler {func.name!r} -- "
                        "the screen reader already narrates focus arrival",
                    )
                )
                continue
            arg = _sole_arg(node)
            if arg is None:
                continue
            if _is_get_title_call(arg):
                violations.append(
                    Violation(
                        rel,
                        node.lineno,
                        "announces a window title (GetTitle()) -- the reader "
                        "said it when the window opened",
                    )
                )
            elif (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and arg.value in title_literals
            ):
                violations.append(
                    Violation(
                        rel,
                        node.lineno,
                        f"announces the title literal {arg.value!r} -- the "
                        "reader said it when the window opened",
                    )
                )

    for line in _lambda_focus_announces(tree):
        violations.append(
            Violation(
                rel,
                line,
                "announce inside a lambda bound to EVT_SET_FOCUS -- the "
                "screen reader already narrates focus arrival",
            )
        )
    return violations


def scan() -> list[Violation]:
    violations: list[Violation] = []
    for rel_dir in _SCAN_DIRS:
        root = _REPO_ROOT / rel_dir
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(_REPO_ROOT).as_posix()
            if rel in _ALLOWLIST:
                continue
            violations.extend(_check_file(path))
    return violations


def main() -> int:
    violations = scan()
    if violations:
        print("Over-announce gate (GATE-13) violations:")
        for violation in violations:
            print(f"  {violation}")
        print(
            "\nThe screen reader already says titles, focus moves and control "
            "names. Announce only what the app alone knows."
        )
        return 1
    print("GATE-13: no over-announcements found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
