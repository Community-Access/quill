"""Bullets, numbers, or neither -- one cycle over the lines you have chosen.

WordPad's ``Ctrl+Shift+L`` steps a paragraph between a bulleted list, a numbered
list and no list at all, and that is the shape both editors want: one key, three
states, each announcing itself, so you press it until you hear the one you meant.
A toggle can only say yes or no, which is why QUILL Lite had bullets and no way to
make a numbered list at all and QUILL had two commands on two chords that did not
know about each other (bad.md P1.5, 4.2 Tier 1).

This is the *markup* half -- the ``- `` and ``1. `` a Markdown document wears.
The rich half is ``ITextPara.ListType`` and lives in the shared RichEdit surface,
because in a rich document a list is a paragraph property rather than characters
in the text.

Two rules the obvious implementation gets wrong:

* **Scope is the selected lines, or the caret's line -- never the document.**
  QUILL's list-off ran ``strip_list_markers`` over the whole buffer and put it
  back with ``SetValue``, which removed every list in the file and cleared the
  undo stack along with them (bad.md R2). Nothing here reads outside the span it
  was given.
* **Numbering restarts at one and counts the lines it numbers**, skipping blank
  ones. A numbered list whose markers are all ``1.`` is not a numbered list, and
  one that counts blank lines is a list with gaps in it.

wx-free and directly tested.
"""

from __future__ import annotations

import re

__all__ = [
    "LIST_STYLES",
    "cycle_list_style",
    "list_block_span",
    "list_style_of",
    "strip_list_block",
]

#: The ring, in order. Pressing the key at the last stop comes back to the first.
LIST_STYLES: tuple[str, str, str] = ("none", "bullet", "numbered")

#: ``- item``, ``* item`` or ``+ item``, with any indent in front of it.
_BULLET = re.compile(r"^(\s*)[-*+]\s+")

#: ``1. item`` or ``1) item``.
_NUMBER = re.compile(r"^(\s*)\d+[.)]\s+")


def list_style_of(lines: list[str]) -> str:
    """What *lines* already are: ``"bullet"``, ``"numbered"`` or ``"none"``.

    Every non-blank line has to agree. A half-marked run is "none", so the next
    press marks all of it rather than unmarking the half that was done -- which
    is the answer somebody who has just typed a new item wants.
    """
    content = [line for line in lines if line.strip()]
    if not content:
        return "none"
    if all(_BULLET.match(line) for line in content):
        return "bullet"
    if all(_NUMBER.match(line) for line in content):
        return "numbered"
    return "none"


def _strip(line: str) -> str:
    """*line* with whatever list marker it has taken off, indent kept."""
    for pattern in (_BULLET, _NUMBER):
        match = pattern.match(line)
        if match:
            return match.group(1) + line[match.end() :]
    return line


def cycle_list_style(text: str, start: int, end: int) -> tuple[str, str, int, int]:
    """Step the lines spanned by ``[start, end]`` to the next list style.

    Returns ``(new_text, style, new_start, new_end)``, where *style* is the style
    the lines are now in, and the two offsets span the rewritten lines so the
    caller can restore a selection over them.

    A caret with no selection acts on the caret's own line, which is what every
    other line tool in both editors does.
    """
    length = len(text)
    start = max(0, min(int(start), length))
    end = max(start, min(int(end), length))
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = length

    block = text[line_start:line_end]
    lines = block.split("\n")
    style = LIST_STYLES[(LIST_STYLES.index(list_style_of(lines)) + 1) % len(LIST_STYLES)]

    rewritten: list[str] = []
    number = 0
    for line in lines:
        bare = _strip(line)
        if not bare.strip():
            rewritten.append(bare)
            continue
        indent = bare[: len(bare) - len(bare.lstrip())]
        body = bare[len(indent) :]
        if style == "bullet":
            rewritten.append(f"{indent}- {body}")
        elif style == "numbered":
            number += 1
            rewritten.append(f"{indent}{number}. {body}")
        else:
            rewritten.append(bare)

    updated = "\n".join(rewritten)
    return (
        text[:line_start] + updated + text[line_end:],
        style,
        line_start,
        line_start + len(updated),
    )


def list_block_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    """The span of the one contiguous list the caret (or selection) sits in.

    ``None`` when there is no list there. Walks outward from the caret's line
    while each neighbouring line is a list item or a blank line *between* two
    items, so a list with a paragraph break inside it stays one list and the
    next list further down the document is a different one.

    This exists because of bad.md R2. QUILL's "turn the list off" ran
    :func:`strip_list_markers` over **the whole document** and wrote the result
    back with ``SetValue`` -- so switching one three-item list off silently
    unmade every other list in the file, and ``SetValue`` also cleared the
    RichEdit undo stack, so Ctrl+Z could not bring any of them back. The
    announcement was "Bullet List removed", singular, which is the sentence a
    listener has to believe.
    """
    line_starts: list[int] = [0]
    for index, character in enumerate(text):
        if character == "\n":
            line_starts.append(index + 1)

    def _line_end(line_start: int) -> int:
        end_index = text.find("\n", line_start)
        return len(text) if end_index == -1 else end_index

    line_spans = [(line_start, _line_end(line_start)) for line_start in line_starts]

    def is_item(row: int) -> bool:
        if not 0 <= row < len(line_spans):
            return False
        line = text[line_spans[row][0] : line_spans[row][1]]
        return _BULLET.match(line) is not None or _NUMBER.match(line) is not None

    def is_blank(row: int) -> bool:
        if not 0 <= row < len(line_spans):
            return False
        return not text[line_spans[row][0] : line_spans[row][1]].strip()

    if end < start:
        start, end = end, start
    first = max(row for row, span in enumerate(line_spans) if span[0] <= start)
    last = max(row for row, span in enumerate(line_spans) if span[0] <= end)
    rows = [row for row in range(first, last + 1) if is_item(row)]
    if not rows:
        return None
    top, bottom = rows[0], rows[-1]
    # A blank line only continues the list when another item follows it;
    # otherwise the list ended and the blank belongs to what comes next.
    while is_item(top - 1) or (is_blank(top - 1) and is_item(top - 2)):
        top -= 2 if not is_item(top - 1) else 1
    while is_item(bottom + 1) or (is_blank(bottom + 1) and is_item(bottom + 2)):
        bottom += 2 if not is_item(bottom + 1) else 1
    return line_spans[top][0], line_spans[bottom][1]


def strip_list_block(text: str, start: int, end: int) -> tuple[int, int, str, int] | None:
    """``(start, end, replacement, items)`` for turning off just this list.

    The count is returned because the caller must say it: "Bullet list removed,
    4 items" is the only way somebody who cannot see the markers disappear
    learns how much just changed (GATE-BULK-COUNT).
    """
    span = list_block_span(text, start, end)
    if span is None:
        return None
    block_start, block_end = span
    block = text[block_start:block_end]
    items = sum(
        1
        for line in block.splitlines()
        if _BULLET.match(line) is not None or _NUMBER.match(line) is not None
    )
    return block_start, block_end, _strip_markers(block), items


def _strip_markers(block: str) -> str:
    """*block* with every bullet or number marker removed, indents kept."""
    out: list[str] = []
    for line in block.splitlines():
        bullet = _BULLET.match(line)
        if bullet is not None:
            out.append(f"{bullet.group(1)}{line[bullet.end() :]}")
            continue
        number = _NUMBER.match(line)
        if number is not None:
            out.append(f"{number.group(1)}{line[number.end() :]}")
            continue
        out.append(line)
    return "\n".join(out)
