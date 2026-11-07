"""Accessibility checks for Mermaid diagrams inside Markdown.

A Mermaid diagram renders as an SVG picture. Without an accessible title and
description a screen reader reaches it as an unlabelled graphic, so the
checklist here asks for both, warns about choices that tend to hurt contrast
(a theme forced in an init block, hand-set fill and text colours), and, when a
page holds more than one diagram, asks for a heading before each so a listener
can jump between them.

Pure logic: no ``wx``. Every finding carries the 1-based line it refers to, so
the Accessibility Tune-Up can list it beside its other findings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FENCE_OPEN = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})\s*(?P<info>[^\s`]*)")
_HEADING = re.compile(r"^ {0,3}#{1,6}(\s|$)")
_SETEXT = re.compile(r"^ {0,3}(=+|-+)\s*$")
_ACC_TITLE = re.compile(r"^\s*accTitle\s*:", re.IGNORECASE)
_ACC_DESCR = re.compile(r"^\s*accDescr\s*(:|\{)", re.IGNORECASE)
_INIT = re.compile(r"%%\{\s*(init|initialize)\s*:(?P<body>.*?)\}%%", re.IGNORECASE | re.DOTALL)
_THEME = re.compile(r"""["']?theme["']?\s*:""", re.IGNORECASE)
_COLOUR = re.compile(r"^\s*(style|classDef|linkStyle)\b.*\b(fill|color|stroke)\s*:", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class MermaidFinding:
    """One problem found in one diagram."""

    kind: str
    line: int
    title: str
    rationale: str
    context: str


@dataclass(frozen=True, slots=True)
class MermaidBlock:
    """A fenced ``mermaid`` block: where it opens and the lines inside it."""

    start_line: int
    body: tuple[str, ...]


def find_mermaid_blocks(text: str) -> list[MermaidBlock]:
    """Return every fenced block whose info string is ``mermaid``."""

    lines = text.split("\n")
    blocks: list[MermaidBlock] = []
    index = 0
    while index < len(lines):
        opened = _FENCE_OPEN.match(lines[index])
        if opened is None:
            index += 1
            continue
        fence = opened.group("fence")
        info = opened.group("info").strip("{}.").lower()
        close = re.compile(rf"^ {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*$")
        end = index + 1
        while end < len(lines) and close.match(lines[end]) is None:
            end += 1
        if info == "mermaid":
            blocks.append(MermaidBlock(start_line=index + 1, body=tuple(lines[index + 1 : end])))
        index = end + 1
    return blocks


def check_mermaid(text: str) -> list[MermaidFinding]:
    """Check every Mermaid diagram in Markdown ``text``."""

    blocks = find_mermaid_blocks(text)
    if not blocks:
        return []
    lines = text.split("\n")
    findings: list[MermaidFinding] = []
    for number, block in enumerate(blocks, start=1):
        findings.extend(_check_block(block, number))
    if len(blocks) > 1:
        for number, block in enumerate(blocks, start=1):
            if not _heading_before(lines, block.start_line - 1):
                findings.append(
                    MermaidFinding(
                        kind="heading",
                        line=block.start_line,
                        title=f"Diagram {number} has no heading before it",
                        rationale=(
                            "This page has more than one diagram. A heading before "
                            "each one lets a listener jump straight to it and know "
                            "which diagram they are on."
                        ),
                        context=lines[block.start_line - 1].strip(),
                    )
                )
    findings.sort(key=lambda f: (f.line, f.kind))
    return findings


def _check_block(block: MermaidBlock, number: int) -> list[MermaidFinding]:
    opening = f"Diagram {number}"
    context = next((line.strip() for line in block.body if line.strip()), "mermaid")
    found: list[MermaidFinding] = []
    if not any(_ACC_TITLE.match(line) for line in block.body):
        found.append(
            MermaidFinding(
                kind="acc-title",
                line=block.start_line,
                title=f"{opening} has no accessible title (accTitle)",
                rationale=(
                    "Without accTitle the rendered diagram reaches a screen reader "
                    "as an unnamed picture. Add a line such as accTitle: Order flow."
                ),
                context=context,
            )
        )
    if not any(_ACC_DESCR.match(line) for line in block.body):
        found.append(
            MermaidFinding(
                kind="acc-descr",
                line=block.start_line,
                title=f"{opening} has no accessible description (accDescr)",
                rationale=(
                    "accDescr is the text a listener gets instead of the picture. "
                    "Say in a sentence or two what the diagram shows."
                ),
                context=context,
            )
        )
    joined = "\n".join(block.body)
    for match in _INIT.finditer(joined):
        if _THEME.search(match.group("body")):
            offset = joined[: match.start()].count("\n")
            found.append(
                MermaidFinding(
                    kind="theme",
                    line=block.start_line + 1 + offset,
                    title=f"{opening} sets a theme in its init block",
                    rationale=(
                        "A forced theme overrides the reader's own light or dark "
                        "choice and can leave text with too little contrast. Leave "
                        "the theme out unless you have checked it."
                    ),
                    context=match.group(0).split("\n", 1)[0].strip(),
                )
            )
    for offset, line in enumerate(block.body):
        if _COLOUR.match(line):
            found.append(
                MermaidFinding(
                    kind="colour",
                    line=block.start_line + 1 + offset,
                    title=f"{opening} sets its own colours",
                    rationale=(
                        "Check that text on these fills meets a contrast ratio of at "
                        "least 4.5 to 1, and that colour is not the only thing that "
                        "tells two parts apart."
                    ),
                    context=line.strip(),
                )
            )
    return found


def _heading_before(lines: list[str], fence_index: int) -> bool:
    """Is the nearest non-blank line above the fence a heading?"""

    index = fence_index - 1
    while index >= 0 and not lines[index].strip():
        index -= 1
    if index < 0:
        return False
    if _HEADING.match(lines[index]):
        return True
    return bool(index >= 1 and _SETEXT.match(lines[index]) and lines[index - 1].strip())
