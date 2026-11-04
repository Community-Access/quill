"""Code mode for reviewing a change: line numbers, indent counts, token diffs (code.md 5.4).

Review AI Changes was tuned for prose ("changed 'quick' to 'rapid'" with the
sentence around it). Code wants different things, so a project review reads
each change through this module:

- **Where it is:** "Change 2 of 3, lines 40 to 44, in function parse_args."
- **What changed in a line:** a token-level diff, so a renamed variable is
  "changed tokn to token" rather than the whole line twice.
- **Indentation as a count,** said once, when it changes: "indent 8".
- **Line numbers lead every line,** so a braille reader can jump by number,
  and every row is one line: no columns.

wx-free; the review window only shows what :func:`describe_hunk` returns.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from quill.core.ai.change_set import ChangeKind, FileChange, Hunk
from quill.core.ai.project_outline import enclosing_name, outline_text

__all__ = [
    "HunkWords",
    "describe_file",
    "describe_hunk",
    "indent_of",
    "numbered_lines",
    "token_changes",
]

_TOKEN = re.compile(r"\w+|[^\w\s]+|\s+")


@dataclass(frozen=True, slots=True)
class HunkWords:
    """One change, in words: the heading line and the body to read."""

    heading: str
    body: str


def indent_of(line: str) -> int:
    """Leading whitespace as a count of columns (a tab counts as four)."""
    count = 0
    for char in line:
        if char == " ":
            count += 1
        elif char == "\t":
            count += 4
        else:
            break
    return count


def numbered_lines(lines: list[str], first: int) -> list[str]:
    """Each line led by its number, with "indent N" said when the indent changes."""
    out: list[str] = []
    last_indent: int | None = None
    for offset, line in enumerate(lines):
        number = first + offset
        if not line.strip():
            out.append(f"{number}: blank")
            continue
        indent = indent_of(line)
        note = f"indent {indent}, " if indent != last_indent else ""
        last_indent = indent
        out.append(f"{number}: {note}{line.strip()}")
    return out


def token_changes(old: str, new: str) -> list[str]:
    """The tokens that differ between two lines: ["changed tokn to token"]."""
    a = [t for t in _TOKEN.findall(old) if not t.isspace()]
    b = [t for t in _TOKEN.findall(new) if not t.isspace()]
    words: list[str] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        before = " ".join(a[i1:i2])
        after = " ".join(b[j1:j2])
        if tag == "replace":
            words.append(f"changed {before} to {after}")
        elif tag == "delete":
            words.append(f"removed {before}")
        elif tag == "insert":
            words.append(f"added {after}")
    return words


def _where(hunk: Hunk) -> str:
    if not hunk.old:
        return f"before line {hunk.old_start}" if hunk.old_start > 1 else "at the start"
    if hunk.old_end == hunk.old_start:
        return f"line {hunk.old_start}"
    return f"lines {hunk.old_start} to {hunk.old_end}"


def describe_hunk(change: FileChange, index: int) -> HunkWords:
    """Change *index* (0-based) of an edit, as a heading and a readable body."""
    hunk = change.hunks[index]
    total = len(change.hunks)
    suffix = "." + change.path.rsplit(".", 1)[-1].lower() if "." in change.path else ""
    names = outline_text(suffix, change.original)
    inside = enclosing_name(names, max(hunk.old_start, 1))
    state = "accepted" if hunk.accepted else "rejected"
    heading = f"Change {index + 1} of {total}, {_where(hunk)}"
    if inside:
        heading += f", in {inside}"
    heading += f". {state.capitalize()}."
    body: list[str] = []
    if len(hunk.old) == 1 and len(hunk.new) == 1:
        tokens = token_changes(hunk.old[0], hunk.new[0])
        if tokens:
            body.append("In this line: " + "; ".join(tokens) + ".")
        body.append("Now:")
        body.extend(numbered_lines(hunk.new, hunk.old_start))
        body.append("Was:")
        body.extend(numbered_lines(hunk.old, hunk.old_start))
    else:
        if hunk.new:
            count = len(hunk.new)
            body.append(f"New text, {count} line{'s' if count != 1 else ''}:")
            body.extend(numbered_lines(hunk.new, hunk.old_start))
        if hunk.old:
            count = len(hunk.old)
            verb = "Replaces" if hunk.new else "Removes"
            body.append(f"{verb} {count} line{'s' if count != 1 else ''}:")
            body.extend(numbered_lines(hunk.old, hunk.old_start))
    if change.reason:
        body.append(f"The agent's reason: {change.reason}")
    return HunkWords(heading, "\n".join(body))


def describe_file(change: FileChange) -> HunkWords:
    """A new, deleted or renamed file, as a heading and a body."""
    if change.kind is ChangeKind.CREATE:
        lines = change.proposed.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        heading = f"New file {change.path}, {len(lines)} line{'s' if len(lines) != 1 else ''}."
        body = "\n".join(numbered_lines(lines, 1))
    elif change.kind is ChangeKind.DELETE:
        count = change.original.count("\n") + 1 if change.original else 0
        heading = f"Delete {change.path}, {count} line{'s' if count != 1 else ''}."
        body = "This file would be removed from the project. Undo Last Turn brings it back."
    else:
        heading = f"Rename {change.path} to {change.new_path}."
        body = "The file's text does not change; only its name and folder."
    if change.reason:
        body += f"\nThe agent's reason: {change.reason}"
    state = "Accepted." if change.accepted else "Rejected."
    return HunkWords(f"{heading} {state}", body)
