"""Enter in a list: the next marker, an exit from an empty item, and when.

Extracted from :mod:`quill.core.format_ops` (GATE-11) when QUILL Lite gained
the behaviour QUILL already had, so both editors run one function instead of
two that could drift. ``format_ops`` re-exports everything here, so every
existing import keeps working.

**What Enter does on a list line** (:func:`continue_markdown_list`):

* At the end of an item, the next line starts with the next marker: ``- ``
  after a bullet, ``3. `` after ``2. ``, ``3) `` after ``2) ``, an unchecked
  ``- [ ] `` after any task item. The item's indentation is kept, so a nested
  item continues at its own depth.
* In the middle of an item, the item splits there: the text after the caret
  becomes the next item, and the spaces at the split are dropped rather than
  carried to the start of the new item.
* On an item that has a marker and nothing else, the marker goes and the list
  ends. The line itself stays (empty, keeping its indentation), so the
  paragraph after a list is where the caret lands -- the same thing Word does
  with a second Enter.
* A new numbered item renumbers the items below it at the same depth while
  they still count on from it, so ``1. 2. 3.`` with an item added after the
  first reads ``1. 2. 3. 4.`` rather than ``1. 2. 2. 3.``. Numbering somebody
  chose for themselves (a list that jumps from 2 to 7) is left alone: the
  walk stops at the first number that does not follow.

Everything is one returned string, so the caller writes it as **one** undo
step: Ctrl+Z after Enter takes back the new line, the marker and any
renumbering together.

**When** (:func:`list_continuation_allowed`), decided by the document and not
by habit:

* Markdown: always. A list marker there is structure, and this is what every
  Markdown editor does.
* Plain text: only when the *Continue lists in plain text* setting is on, and
  never in a file the shared rule calls code or configuration
  (:func:`quill.core.spellcheck_filetypes.is_code_filename`). The setting is
  **off by default**: in a ``.txt`` or a new untitled note, a line that happens
  to start with ``1.`` is as often a date, a version or a numbered paragraph
  somebody is typing by hand, and an editor that adds ``2.`` to the next line
  unasked is changing text the person did not type -- which, by ear, is found
  only when it is read back.
* Rich text: never. A list there is a paragraph property the control draws and
  renumbers itself, and characters typed in front of it would be a second list
  on top of the first.
* HTML, YAML and anything else: never.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "MarkdownListContinuation",
    "continue_markdown_list",
    "continuation_message",
    "list_continuation_allowed",
]


@dataclass(frozen=True, slots=True)
class MarkdownListContinuation:
    text: str
    caret: int
    exited_list: bool
    #: How many numbered items below the new one were renumbered.
    renumbered: int = 0


_MARKDOWN_LIST_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?:(?P<number>\d+)(?P<num_sep>[.)])|(?P<bullet>[-+*]))"
    r"(?P<spacing>[ \t]+)(?:(?P<task>\[[ xX]\])(?P<task_spacing>[ \t]+))?(?P<body>.*)$"
)


def continue_markdown_list(text: str, caret: int) -> MarkdownListContinuation | None:
    """What Enter should do at *caret*, or ``None`` when it is not on a list item.

    ``None`` also when the caret is inside the marker itself (``1|. item``):
    splitting a marker is never what somebody pressing Enter there meant, so
    the key keeps its ordinary meaning.
    """
    if caret < 0 or caret > len(text):
        return None
    line_start = text.rfind("\n", 0, caret) + 1
    newline = text.find("\n", caret)
    content_end = len(text) if newline == -1 else newline
    line_text = text[line_start:content_end].rstrip("\r")
    match = _MARKDOWN_LIST_PATTERN.match(line_text)
    if match is None:
        return None

    marker_end = len(match.group(0)) - len(match.group("body"))
    line_offset = caret - line_start
    if line_offset < marker_end:
        return None

    before_body = line_text[marker_end:line_offset]
    after_body = line_text[line_offset:]
    if not before_body.strip() and not after_body.strip():
        # An empty item: the marker goes, the line (and its newline) stays.
        indent = match.group("indent")
        updated = text[:line_start] + indent + text[line_start + len(line_text) :]
        return MarkdownListContinuation(updated, line_start + len(indent), exited_list=True)

    left, right = caret, caret
    if after_body.strip():
        # A split: the spaces either side of the caret belong to neither half.
        left -= len(before_body) - len(before_body.rstrip(" \t"))
        right += len(after_body) - len(after_body.lstrip(" \t"))
    marker = _continuation_marker(match)
    tail, renumbered = _renumber_following(text[content_end:], match)
    updated = text[:left] + "\n" + marker + text[right:content_end] + tail
    return MarkdownListContinuation(
        updated, left + 1 + len(marker), exited_list=False, renumbered=renumbered
    )


def _continuation_marker(match: re.Match[str]) -> str:
    indent = match.group("indent")
    bullet = match.group("bullet")
    number = match.group("number")
    num_sep = match.group("num_sep") or "."
    spacing = match.group("spacing") or " "
    task = match.group("task")
    task_spacing = match.group("task_spacing") or " "
    if bullet is not None:
        head = f"{indent}{bullet}{spacing}"
    else:
        head = f"{indent}{int(number or '1') + 1}{num_sep}{spacing}"
    if task is not None:
        # A task list stays one: the next item is a new, unchecked task.
        return f"{head}[ ]{task_spacing}"
    return head


def _renumber_following(tail: str, match: re.Match[str]) -> tuple[str, int]:
    """Renumber the items after a new numbered one while they count on from it.

    *tail* is the text after the item's own line (starting at its newline, or
    empty). Only items at the same depth with the same separator count; a
    deeper line (a nested item or a continuation) is passed over, and anything
    else -- a blank line, a shallower line, a number that does not follow --
    ends the walk.
    """
    number = match.group("number")
    if number is None or not tail:
        return tail, 0
    indent = match.group("indent")
    separator = match.group("num_sep")
    expected = int(number) + 1
    lines = tail.split("\n")
    changed = 0
    # lines[0] is the empty remainder of the item's own line.
    for index in range(1, len(lines)):
        line = lines[index]
        if not line.strip():
            break
        found = _MARKDOWN_LIST_PATTERN.match(line)
        if found is not None and found.group("indent") == indent:
            if found.group("number") is None or found.group("num_sep") != separator:
                break
            if int(found.group("number")) != expected:
                break
            digits_at = len(indent)
            digits_end = digits_at + len(found.group("number"))
            lines[index] = line[:digits_at] + str(expected + 1) + line[digits_end:]
            expected += 1
            changed += 1
            continue
        leading = len(line) - len(line.lstrip(" \t"))
        if leading > len(indent):
            continue
        break
    return "\n".join(lines), changed


def continuation_message(result: MarkdownListContinuation) -> str:
    """The sentence both editors say after Enter in a list, from one place."""
    if result.exited_list:
        return "Exited list"
    if result.renumbered == 1:
        return "Continued list item, renumbered 1 item below"
    if result.renumbered:
        return f"Continued list item, renumbered {result.renumbered} items below"
    return "Continued list item"


#: Kinds where a list marker is structure and Enter always continues it.
_ALWAYS_KINDS = frozenset({"markdown"})


def list_continuation_allowed(
    kind: str | None,
    name: str | Path | None,
    *,
    rich: bool,
    plain_text_enabled: bool,
) -> bool:
    """Whether Enter may continue a list in this document. See the module notes.

    *kind* is the document's markup kind as the editor already classifies it
    (``"markdown"``, ``"html"``, ``"plain"``, ...; ``None`` is plain). *name*
    is the file name or path, ``None`` for an untitled document.
    """
    from quill.core.spellcheck_filetypes import is_code_filename

    if rich:
        return False
    normalised = (kind or "plain").strip().lower()
    if normalised in _ALWAYS_KINDS:
        return True
    if normalised != "plain":
        return False
    return bool(plain_text_enabled) and not is_code_filename(name)
