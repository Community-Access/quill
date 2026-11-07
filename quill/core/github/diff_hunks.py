"""Line-addressable, screen-reader-friendly rendering of unified PR hunks."""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$")


@dataclass(frozen=True, slots=True)
class DiffHunk:
    heading: str
    text: str
    right_lines: dict[int, int]
    left_lines: dict[int, int]


def parse_hunks(patch: str) -> tuple[DiffHunk, ...]:
    """Parse hunk headers and keep exact file-line to text-position maps."""
    hunks: list[DiffHunk] = []
    heading = ""
    lines: list[str] = []
    right_lines: dict[int, int] = {}
    left_lines: dict[int, int] = {}
    old_line = new_line = 0

    def finish() -> None:
        if heading:
            hunks.append(DiffHunk(heading, "\n".join(lines), right_lines.copy(), left_lines.copy()))

    for raw in patch.splitlines():
        match = _HEADER.match(raw)
        if match:
            finish()
            old_line, new_line = int(match[1]), int(match[2])
            heading = f"Hunk: old line {old_line}, new line {new_line}{match[3]}"
            lines = [heading]
            right_lines = {}
            left_lines = {}
            continue
        if not heading or not raw or raw[0] not in " +-":
            continue
        marker = raw[0]
        if marker == " ":
            label = f"Context, line {new_line}: {raw[1:]}"
            right_lines[new_line] = len("\n".join(lines)) + 1
            left_lines[old_line] = len("\n".join(lines)) + 1
            old_line += 1
            new_line += 1
        elif marker == "+":
            label = f"Added, line {new_line}: {raw[1:]}"
            right_lines[new_line] = len("\n".join(lines)) + 1
            new_line += 1
        else:
            label = f"Removed, old line {old_line}: {raw[1:]}"
            left_lines[old_line] = len("\n".join(lines)) + 1
            old_line += 1
        lines.append(label)
    finish()
    return tuple(hunks)


def find_line(patch: str, line: int, *, side: str = "RIGHT") -> tuple[str, int] | None:
    """Return the one hunk and insertion offset for an exact changed/context line."""
    if line <= 0:
        return None
    for hunk in parse_hunks(patch):
        offset = (hunk.left_lines if side.upper() == "LEFT" else hunk.right_lines).get(line)
        if offset is not None:
            return hunk.text, offset
    return None
