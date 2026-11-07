"""A pull request's patch as lines to read and comment on.

Each line of GitHub's unified patch becomes a :class:`DiffLine` that knows its
line number in the old file and the new one, so a comment can be placed the
way GitHub's REST API wants it (``line``/``side``, plus ``start_line``/
``start_side`` for a range). How the line is *marked* is the reader's choice:
words ("Added line 12") or symbols ("+ 12"). Symbols are shorter but a screen
reader only speaks them at a punctuation level that reads them, which is what
:data:`SYMBOLS_NOTE` tells the person who picks them.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from quill.core.github.review_errors import GitHubReviewError

LINE_MARKS_WORDS = "words"
LINE_MARKS_SYMBOLS = "symbols"
LINE_MARK_STYLES: tuple[str, ...] = (LINE_MARKS_WORDS, LINE_MARKS_SYMBOLS)
LINE_MARK_LABELS: dict[str, str] = {
    LINE_MARKS_WORDS: "Words: Added line, Removed line",
    LINE_MARKS_SYMBOLS: "Symbols: plus and minus",
}
SYMBOLS_NOTE = (
    "Symbols are spoken only when your screen reader reads punctuation. "
    "Turn punctuation reading up, or choose Words."
)

_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$")
_SUGGESTION = re.compile(r"\n?```suggestion\n.*?\n?```\n?", re.DOTALL)


@dataclass(frozen=True, slots=True)
class DiffLine:
    """One line of a patch: a hunk heading, a change, context, or a note."""

    kind: str  # "hunk" / "added" / "removed" / "context" / "note"
    text: str
    old_line: int = 0
    new_line: int = 0
    hunk: int = -1

    @property
    def commentable(self) -> bool:
        return self.kind in ("added", "removed", "context")

    @property
    def side(self) -> str:
        """GitHub's side: LEFT for a removed line, RIGHT for everything else."""
        return "LEFT" if self.kind == "removed" else "RIGHT"

    @property
    def line(self) -> int:
        return self.old_line if self.kind == "removed" else self.new_line


def parse_diff_lines(patch: str) -> tuple[DiffLine, ...]:
    """Every line of a unified patch, numbered on both sides."""
    out: list[DiffLine] = []
    old_line = new_line = 0
    hunk = -1
    for raw in patch.splitlines():
        match = _HEADER.match(raw)
        if match:
            hunk += 1
            old_line, new_line = int(match[1]), int(match[2])
            out.append(DiffLine("hunk", match[3].strip(), old_line, new_line, hunk))
            continue
        if hunk < 0 or not raw:
            continue
        marker, text = raw[0], raw[1:]
        if marker == "+":
            out.append(DiffLine("added", text, 0, new_line, hunk))
            new_line += 1
        elif marker == "-":
            out.append(DiffLine("removed", text, old_line, 0, hunk))
            old_line += 1
        elif marker == " ":
            out.append(DiffLine("context", text, old_line, new_line, hunk))
            old_line += 1
            new_line += 1
        elif marker == "\\":
            out.append(DiffLine("note", text.strip(), 0, 0, hunk))
    return tuple(out)


def render_line(line: DiffLine, style: str = LINE_MARKS_WORDS) -> str:
    """The line as the reader hears it, in the chosen mark style."""
    symbols = style == LINE_MARKS_SYMBOLS
    if line.kind == "hunk":
        where = f"old line {line.old_line}, new line {line.new_line}"
        heading = f": {line.text}" if line.text else ""
        return f"@@ {where} @@{heading}" if symbols else f"Changes at {where}{heading}"
    if line.kind == "added":
        return (
            f"+ {line.new_line}: {line.text}"
            if symbols
            else (f"Added line {line.new_line}: {line.text}")
        )
    if line.kind == "removed":
        return (
            f"- {line.old_line}: {line.text}"
            if symbols
            else (f"Removed line {line.old_line}: {line.text}")
        )
    if line.kind == "context":
        return (
            f"  {line.new_line}: {line.text}"
            if symbols
            else (f"Unchanged line {line.new_line}: {line.text}")
        )
    return f"\\ {line.text}" if symbols else f"Note: {line.text}"


def render_patch(patch: str, style: str = LINE_MARKS_WORDS) -> str:
    """A whole patch, one rendered line per row."""
    return "\n".join(render_line(line, style) for line in parse_diff_lines(patch))


@dataclass(frozen=True, slots=True)
class LineCommentAnchor:
    """Where a review comment goes, in the shape GitHub's REST API takes."""

    path: str
    line: int
    side: str = "RIGHT"
    start_line: int = 0
    start_side: str = ""

    @property
    def is_range(self) -> bool:
        return bool(self.start_line) and (
            self.start_line != self.line or self.start_side != self.side
        )

    def payload(self) -> dict[str, object]:
        data: dict[str, object] = {"path": self.path, "line": self.line, "side": self.side}
        if self.is_range:
            data["start_line"] = self.start_line
            data["start_side"] = self.start_side or self.side
        return data

    def describe(self) -> str:
        """ "line 12 of path" or "lines 10 to 14 of path" ("old" for removed lines)."""

        def where(line: int, side: str) -> str:
            return f"old line {line}" if side == "LEFT" else f"line {line}"

        start_side = self.start_side or self.side
        if self.is_range and start_side == self.side:
            old = "old " if self.side == "LEFT" else ""
            return f"{old}lines {self.start_line} to {self.line} of {self.path}"
        if self.is_range:
            start = where(self.start_line, start_side)
            return f"{start} to {where(self.line, self.side)} of {self.path}"
        return f"{where(self.line, self.side)} of {self.path}"


def anchor_for(path: str, lines: Sequence[DiffLine]) -> LineCommentAnchor:
    """The comment anchor for one line or a run of lines inside one hunk."""
    chosen = [line for line in lines if line.commentable]
    if not path:
        raise GitHubReviewError("This change has no file name to comment on.")
    if not chosen:
        raise GitHubReviewError(
            "Comments go on an added, removed or unchanged line. Move to one first."
        )
    if len({line.hunk for line in chosen}) > 1:
        raise GitHubReviewError(
            "GitHub takes a comment on several lines only inside one run of changes. "
            "Choose lines from the same hunk."
        )
    first, last = chosen[0], chosen[-1]
    if len(chosen) == 1:
        return LineCommentAnchor(path, last.line, last.side)
    return LineCommentAnchor(path, last.line, last.side, first.line, first.side)


def lines_for_range(
    lines: Sequence[DiffLine], start: int, end: int, *, side: str = "RIGHT"
) -> tuple[DiffLine, ...]:
    """The patch lines from *start* to *end* on one side, all of them shown."""
    if start <= 0 or end <= 0:
        raise GitHubReviewError("Line numbers start at 1.")
    if end < start:
        start, end = end, start
    side = side.upper()
    wanted = set(range(start, end + 1))
    found = [
        line
        for line in lines
        if line.commentable
        and (
            (side == "LEFT" and line.kind != "added" and line.old_line in wanted)
            or (side != "LEFT" and line.kind != "removed" and line.new_line in wanted)
        )
    ]
    numbers = {line.old_line if side == "LEFT" else line.new_line for line in found}
    missing = sorted(wanted - numbers)
    if missing:
        raise GitHubReviewError(
            f"Line {missing[0]} is not in this file's changes, so GitHub will not take a "
            "comment on it. Choose lines the patch shows."
        )
    return tuple(found)


def parse_range(text: str) -> tuple[int, int]:
    """ "12-15", "12 to 15" or "12" as a (start, end) pair."""
    numbers = [int(part) for part in re.findall(r"\d+", text)]
    if not numbers or len(numbers) > 2:
        raise GitHubReviewError("Type a start and end line, for example 12-15.")
    return (numbers[0], numbers[-1])


def suggestion_block(lines: Sequence[DiffLine]) -> str:
    """A ```suggestion block holding the new-file text of the chosen lines."""
    kept = [line.text for line in lines if line.kind in ("added", "context")]
    if not kept:
        raise GitHubReviewError(
            "A suggestion replaces lines of the new file. Choose an added or unchanged line."
        )
    return "```suggestion\n" + "\n".join(kept) + "\n```"


def strip_suggestion_block(body: str) -> str:
    """The comment without its first ```suggestion block."""
    return _SUGGESTION.sub("\n", body, count=1).strip("\n")


def unified_diff_text(files: Sequence[object]) -> str:
    """The pull request's files as one ``.diff`` text, the way git writes it."""
    chunks: list[str] = []
    for pull_file in files:
        name = str(getattr(pull_file, "filename", "") or "")
        old = str(getattr(pull_file, "previous_filename", "") or "") or name
        status = str(getattr(pull_file, "status", "") or "")
        patch = str(getattr(pull_file, "patch", "") or "")
        before = "/dev/null" if status == "added" else f"a/{old}"
        after = "/dev/null" if status == "removed" else f"b/{name}"
        chunks.append(f"diff --git a/{old} b/{name}")
        if patch:
            chunks.extend([f"--- {before}", f"+++ {after}", patch.rstrip("\n")])
        else:
            chunks.append(f"Binary files {before} and {after} differ")
    return "\n".join(chunks) + ("\n" if chunks else "")


__all__ = [
    "LINE_MARKS_SYMBOLS",
    "LINE_MARKS_WORDS",
    "LINE_MARK_LABELS",
    "LINE_MARK_STYLES",
    "SYMBOLS_NOTE",
    "DiffLine",
    "LineCommentAnchor",
    "anchor_for",
    "lines_for_range",
    "parse_diff_lines",
    "parse_range",
    "render_line",
    "render_patch",
    "strip_suggestion_block",
    "suggestion_block",
    "unified_diff_text",
]
