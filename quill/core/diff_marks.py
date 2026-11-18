"""A difference as lines to read one at a time, each marked the way you choose.

Adapted from Kelly Ford's ``difftext`` module in TheIdeaPlace app-kit, which
GHManage and The Chat Place use, so that a change reads the same in QUILL, in
GHManage and in The Chat Place: the same four ways of marking a line, with the
same marks. Kelly's design, in his words: a unified diff marks each line with
"+", "-" or a space, and at a screen reader's lower punctuation levels those
marks are not spoken, and a space never is; so the mark is written as a word or
an audible symbol, always first on the line, one line out for each line in.

The four styles (:data:`STYLES`):

* ``words``: "Added: x", "Removed: x", "Unchanged: x". The default.
* ``short``: "Add x", "Del x", "Same x". Shorter, and still spoken at every
  punctuation level.
* ``symbols``: "+ x", "- x", "= x", like ``git diff``; "=" stands for git's
  space, which is never spoken.
* ``changed``: as symbols, but a removed line followed by its replacement reads
  "!- old" then "!+ new" (``!`` as ``diff -c`` marks a changed line), pair by
  pair, so each change is heard whole.

A blank line reads "blank line", each run of changes starts with where it is
("Lines 10 to 15:"), and a file starts with a one-line summary. QUILL adds the
pieces every one of its views needs: rendering two texts directly
(:func:`render_texts`), a whole multi-file patch (:func:`render_unified`), and
the order the ``changed`` style reads a run in (:func:`reading_order`), for
views that keep each line as a row.

Used by the editor's Compare with File, Compare Files, WordPress's Compare with
Site, and the GitHub Workbench's review of a pull request. No wx; strict-typed.

------------------------------------------------------------------------------
Portions adapted from TheIdeaPlace app-kit, ``python/theideaplace_appkit/difftext.py``:

MIT License

Copyright (c) 2026 TheIdeaPlace (Kelly Ford)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from difflib import unified_diff

__all__ = [
    "CHANGED",
    "DEFAULT",
    "LABELS",
    "SHORT",
    "STYLES",
    "SYMBOLS",
    "SYMBOLS_NOTE",
    "WORDS",
    "FileDiff",
    "Hunk",
    "change_count",
    "file_summary",
    "is_symbol_style",
    "mark_for",
    "parse_unified",
    "reading_order",
    "render",
    "render_lines",
    "render_replacement",
    "render_texts",
    "render_unified",
    "style_or_default",
    "where",
]

WORDS = "words"
SHORT = "short"
SYMBOLS = "symbols"
CHANGED = "changed"

STYLES: tuple[str, ...] = (WORDS, SHORT, SYMBOLS, CHANGED)
DEFAULT = WORDS

#: What a choice of style shows, in Kelly's words.
LABELS: dict[str, str] = {
    WORDS: "Words (Added, Removed, Unchanged)",
    SHORT: "Short words (Add, Del, Same)",
    SYMBOLS: "Diff symbols (+, -, =)",
    CHANGED: "Diff symbols with changed lines (!-, !+, +, -, =)",
}

#: Said when a symbol style is chosen: symbols can be silent.
SYMBOLS_NOTE = (
    "Symbols are spoken only if your screen reader's punctuation level reads them. "
    "If you do not hear them, raise the punctuation level or choose one of the word styles."
)

_MARKS: dict[str, dict[str, str]] = {
    WORDS: {"+": "Added:", "-": "Removed:", " ": "Unchanged:"},
    SHORT: {"+": "Add", "-": "Del", " ": "Same"},
    SYMBOLS: {"+": "+", "-": "-", " ": "="},
    CHANGED: {"+": "+", "-": "-", " ": "=", "!-": "!-", "!+": "!+"},
}

_HEADER = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def style_or_default(style: str) -> str:
    """*style* when it is one of :data:`STYLES`, else the default."""
    return style if style in STYLES else DEFAULT


def is_symbol_style(style: str) -> bool:
    return style in (SYMBOLS, CHANGED)


def mark_for(kind: str, style: str) -> str:
    """The mark for a line of *kind*: ``+``, ``-``, `` `` (unchanged), ``!-`` or ``!+``."""
    marks = _MARKS[style_or_default(style)]
    if kind in ("!-", "!+") and kind not in marks:
        kind = kind[1]
    return marks.get(kind, marks[" "])


@dataclass
class Hunk:
    """One run of a diff's lines, each starting " ", "-", "+" or "\\"."""

    old_start: int  # 1-based; 0 when not known
    new_start: int
    lines: list[str] = field(default_factory=list)

    @property
    def added(self) -> int:
        return sum(1 for line in self.lines if line.startswith("+"))

    @property
    def removed(self) -> int:
        return sum(1 for line in self.lines if line.startswith("-"))


def parse_unified(text: str) -> list[Hunk]:
    """The hunks in unified-diff text (``git diff``, a GitHub patch, or difflib's).

    Anything outside a hunk (file names, ``index``) is skipped; each ``@@``
    header's counts say where its hunk ends, so a removed line that starts
    "--" is still a removed line.
    """
    hunks: list[Hunk] = []
    old_left = new_left = 0
    after_line = False
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for line in lines:
        match = _HEADER.match(line)
        if match:
            old_left = int(match.group(2) or 1)
            new_left = int(match.group(4) or 1)
            hunks.append(Hunk(int(match.group(1)), int(match.group(3))))
            after_line = False
            continue
        if not hunks:
            continue
        if line.startswith("\\"):
            if after_line:
                hunks[-1].lines.append(line)
            continue
        after_line = False
        if old_left <= 0 and new_left <= 0:
            continue
        if line == "":
            line = " "
        mark = line[:1]
        if mark == "+":
            new_left -= 1
        elif mark == "-":
            old_left -= 1
        elif mark == " ":
            old_left -= 1
            new_left -= 1
        else:
            old_left = new_left = 0
            continue
        hunks[-1].lines.append(line)
        after_line = True
    return [hunk for hunk in hunks if hunk.lines]


def where(hunk: Hunk) -> str:
    """ "At line 12:", "Lines 12 to 20:" (in the new text), or "A change:"."""
    kept = sum(1 for line in hunk.lines if line.startswith(" "))
    if hunk.new_start:
        start, count = hunk.new_start, hunk.added + kept
    elif hunk.old_start:
        start, count = hunk.old_start, hunk.removed + kept
    else:
        return "A change:"
    end = start + max(count - 1, 0)
    return f"At line {start}:" if end <= start else f"Lines {start} to {end}:"


def _mark(line: str) -> str:
    mark = line[:1]
    return mark if mark in ("+", "-", "\\") else " "


def reading_order(marks: Sequence[str], style: str) -> list[tuple[int, str]]:
    """``(index, mark)`` in the order to read lines whose marks are *marks*.

    In the ``changed`` style a run of removed lines followed straight away by a
    run of added lines is paired in order, each pair read old then new ("!-",
    "!+"), so the pairs interleave. Leftovers keep "-" or "+". A note ("\\")
    stays after its line. For views that keep each line as a row with its own
    index (the GitHub Workbench's review list), this is the order to show them.
    """
    marked = [(index, mark) for index, mark in enumerate(marks)]
    if style_or_default(style) != CHANGED:
        return marked
    out: list[tuple[int, str]] = []
    i = 0

    def run(i: int, want: str) -> tuple[list[list[tuple[int, str]]], int]:
        groups: list[list[tuple[int, str]]] = []
        while i < len(marked) and marked[i][1] == want:
            group = [marked[i]]
            i += 1
            while i < len(marked) and marked[i][1] == "\\":
                group.append(marked[i])
                i += 1
            groups.append(group)
        return groups, i

    while i < len(marked):
        if marked[i][1] != "-":
            out.append(marked[i])
            i += 1
            continue
        removed, i = run(i, "-")
        added, i = run(i, "+")
        pairs = min(len(removed), len(added))
        for old, new in zip(removed[:pairs], added[:pairs], strict=True):
            out.extend([(old[0][0], "!-"), *old[1:], (new[0][0], "!+"), *new[1:]])
        for group in removed[pairs:] + added[pairs:]:
            out.extend(group)
    return out


def render_lines(lines: Sequence[str], style: str = DEFAULT) -> list[str]:
    """One line of text for each diff line, its mark first.

    A blank line reads "blank line"; "\\ No newline at end of file" reads "Note: ...".
    """
    style = style_or_default(style)
    out: list[str] = []
    for index, mark in reading_order([_mark(line) for line in lines], style):
        text = lines[index][1:]
        if mark == "\\":
            out.append(f"Note: {text.strip()}")
        else:
            out.append(f"{mark_for(mark, style)} {text if text.strip() else 'blank line'}")
    return out


def render_replacement(
    old_lines: Sequence[str], new_lines: Sequence[str], style: str = DEFAULT
) -> list[str]:
    """*old_lines* taken out and *new_lines* put in, marked in *style*.

    For views that already know one difference's two sides (Compare Files,
    a file in a pull request): in the changed-lines style each old line is
    paired with the new one that replaced it.
    """
    return render_lines(
        [f"-{line}" for line in old_lines] + [f"+{line}" for line in new_lines], style
    )


def render(hunks: Sequence[Hunk], style: str = DEFAULT) -> list[str]:
    """Each hunk as where it is, then its lines, with a blank line between hunks."""
    out: list[str] = []
    for hunk in hunks:
        if out:
            out.append("")
        out.append(where(hunk))
        out.extend(render_lines(hunk.lines, style))
    return out


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def change_count(hunks: Sequence[Hunk]) -> tuple[int, int]:
    """(lines added, lines removed) across *hunks*."""
    return sum(h.added for h in hunks), sum(h.removed for h in hunks)


def file_summary(
    name: str, hunks: Sequence[Hunk], status: str = "modified", old_name: str = ""
) -> str:
    """ "src/app.py: modified, 2 lines added, 1 removed." (renamed files say from what)."""
    added, removed = change_count(hunks)
    parts = [status]
    if old_name and old_name != name:
        parts[0] = f"renamed from {old_name}"
    parts.append(f"{_count(added, 'line', 'lines')} added")
    parts.append(f"{removed} removed")
    runs = len(hunks)
    if runs > 1:
        parts.append(f"in {runs} places")
    return f"{name}: {', '.join(parts)}."


@dataclass
class FileDiff:
    name: str
    old_name: str
    status: str
    hunks: list[Hunk]


_FILE = re.compile(r"^diff --git a/(.+?) b/(.+)$")


def _files(text: str) -> list[FileDiff]:
    """Split a multi-file unified diff by file; a single-file one is one entry."""
    found: list[FileDiff] = []
    chunk: list[str] = []
    old = new = ""
    status = "modified"

    def flush() -> None:
        if chunk or old or new:
            hunks = parse_unified("\n".join(chunk))
            if hunks or old or new:
                found.append(FileDiff(new or old or "the text", old, status, hunks))

    for line in text.replace("\r\n", "\n").split("\n"):
        match = _FILE.match(line)
        if match:
            flush()
            chunk, old, new, status = [], match.group(1), match.group(2), "modified"
            continue
        if line.startswith("new file mode"):
            status = "added"
        elif line.startswith("deleted file mode"):
            status = "deleted"
        elif line.startswith("--- ") and not old:
            old = line[4:].removeprefix("a/").strip()
        elif line.startswith("+++ ") and not new:
            new = line[4:].removeprefix("b/").strip()
        else:
            chunk.append(line)
    flush()
    return found


def render_unified(text: str, style: str = DEFAULT) -> str:
    """A whole unified diff, one file after another: its summary, then its runs."""
    blocks = []
    for one in _files(text):
        if one.name == "/dev/null":
            one.name = one.old_name
        lines = [
            file_summary(
                one.name, one.hunks, one.status, one.old_name if one.status == "modified" else ""
            )
        ]
        rendered = render(one.hunks, style)
        if rendered:
            lines.extend(["", *rendered])
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "No differences."


def render_texts(
    old: str, new: str, old_name: str = "before", new_name: str = "after", style: str = DEFAULT
) -> str:
    """Two texts compared directly: a summary naming both, then each run of changes."""
    diff = "\n".join(
        unified_diff(old.splitlines(), new.splitlines(), old_name, new_name, lineterm="", n=3)
    )
    hunks = parse_unified(diff)
    if not hunks:
        return f"{new_name} and {old_name} are the same."
    added, removed = change_count(hunks)
    head = (
        f"Comparing {new_name} with {old_name}: {_count(added, 'line', 'lines')} added, "
        f"{removed} removed, in {_count(len(hunks), 'place', 'places')}."
    )
    return "\n".join([head, "", *render(hunks, style)])
