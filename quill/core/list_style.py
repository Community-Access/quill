"""Bullets, numbers, or neither -- one cycle over the lines you have chosen.

WordPad's ``Ctrl+Shift+L`` steps a paragraph between a bulleted list, a numbered
list and no list at all, and that is the shape both editors want: one key, three
states, each announcing itself, so you press it until you hear the one you meant.
A toggle can only say yes or no, which is why QuillLite had bullets and no way to
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

__all__ = ["LIST_STYLES", "cycle_list_style", "list_style_of"]

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
