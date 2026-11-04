"""Functions and classes in a source file, where they can be told cheaply (code.md 4.2).

``project.outline`` and the review window's "in function parse_args" both ask
the same question: what is defined where. Python is answered exactly, by its
own parser. Every other language is answered by a few line patterns that are
right far more often than not -- good enough to say where a change is, and
never presented as more than that. wx-free.
"""

from __future__ import annotations

import ast
import re

from quill.core.ai.project import OutlineItem

__all__ = ["enclosing_name", "outline_text"]

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "class",
        re.compile(
            r"^\s*(?:export\s+)?(?:public\s+|private\s+|internal\s+)?(?:abstract\s+|sealed\s+|static\s+)*(?:class|struct|interface|enum|trait)\s+([A-Za-z_]\w*)"
        ),
    ),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)")),
    ("function", re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)")),
    ("function", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)")),
    (
        "function",
        re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"),
    ),
    (
        "function",
        re.compile(
            r"^\s*(?:public|private|protected|internal|static|async|virtual|override|\s)+[\w<>\[\],?]+\s+([A-Za-z_]\w*)\s*\([^;]*$"
        ),
    ),
)


def _python_outline(text: str) -> list[OutlineItem] | None:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    items: list[OutlineItem] = []

    def visit(node: ast.AST, depth: int) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                items.append(OutlineItem("class", child.name, child.lineno, depth))
                visit(child, depth + 1)
            elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                items.append(OutlineItem("function", child.name, child.lineno, depth))
                visit(child, depth + 1)

    visit(tree, 0)
    return items


def outline_text(suffix: str, text: str) -> list[OutlineItem]:
    """The definitions in *text*, in order, for a file ending in *suffix*."""
    if suffix in (".py", ".pyw"):
        exact = _python_outline(text)
        if exact is not None:
            return exact
    items: list[OutlineItem] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if len(line) > 400:
            continue
        for kind, pattern in _PATTERNS:
            match = pattern.match(line)
            if match and match.group(1) not in {"if", "for", "while", "switch", "return", "new"}:
                indent = len(line) - len(line.lstrip())
                items.append(OutlineItem(kind, match.group(1), number, min(indent // 4, 6)))
                break
    return items


def enclosing_name(items: list[OutlineItem], line: int) -> str:
    """The innermost definition at or above *line*, as "function parse_args"; or ""."""
    best: OutlineItem | None = None
    for item in items:
        if item.line <= line and (best is None or item.line >= best.line):
            best = item
    return f"{best.kind} {best.name}" if best is not None else ""
