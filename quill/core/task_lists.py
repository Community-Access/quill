"""Task lists: check ``- [ ]`` off, and say how many are done (wx-free).

A Markdown task line is a list item whose text starts with a box: ``- [ ]``
for a task still to do and ``- [x]`` for one that is done. Bullets ``-``,
``*`` and ``+`` and numbered items ``1.`` / ``1)`` all count, at any depth.

The idea is PlanCake's (Andre of Oire Software): an AI-written plan is full of
checklists, and checking one should be two keys rather than an arrow, a delete
and a retype. What a listener cannot get any other way is the *count* -- "3 of
7 tasks complete" means reading every line otherwise -- so the announcement is
:func:`quill.core.lists.announce.checklist_toggle_announcement`, the Structured
List Studio's own sentence, which nothing called until this module.

Both editors call :func:`toggle_tasks` and apply the one edit it returns
through the ordinary undo stack, so Ctrl+Z takes the check mark back like any typing.
The preview and the HTML export call :func:`task_item_html` so a task renders as
a real, read-only check box with the item's text as its label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.lists.announce import checklist_toggle_announcement
from quill.core.lists.model import FlatList, ListItem, ListType

__all__ = [
    "NOT_A_TASK",
    "TaskToggle",
    "is_task_line",
    "task_item_html",
    "toggle_tasks",
]

#: Said, and nothing changed, when the caret's line is not a task.
NOT_A_TASK = "Not a task line"

#: indent, marker, space, box state, then the item's text.
_TASK_RE = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])([ \t]+)\[([ xX])\](?=[ \t]|$)[ \t]?(.*)$")
#: Any list item at all, task or not -- what keeps a list's run together.
_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])[ \t]+")


@dataclass(frozen=True, slots=True)
class TaskToggle:
    """One toggle, ready to apply: replace ``[start, end)`` with ``text``."""

    start: int
    end: int
    text: str
    announcement: str
    changed: int


def is_task_line(line: str) -> bool:
    """True when *line* is a Markdown task item, checked or not."""
    return _TASK_RE.match(line) is not None


def _lines_with_offsets(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    offset = 0
    for line in text.split("\n"):
        out.append((offset, line))
        offset += len(line) + 1
    return out


def _list_run(lines: list[tuple[int, str]], index: int) -> range:
    """The contiguous run of list lines around *index*: the list it belongs to.

    A blank line or any non-item line ends the run, so the count is the count
    of *this* checklist rather than of every task in a long plan.
    """
    start = index
    while start > 0 and _ITEM_RE.match(lines[start - 1][1]):
        start -= 1
    end = index
    while end + 1 < len(lines) and _ITEM_RE.match(lines[end + 1][1]):
        end += 1
    return range(start, end + 1)


def toggle_tasks(text: str, start: int, end: int) -> TaskToggle | None:
    """Check or uncheck the task on the caret's line, or every task in a selection.

    Returns ``None`` when no line in range is a task. With several task lines
    selected, the group is checked if any of them is open, and unchecked only
    when all of them were already done -- the way a group check box behaves.
    The returned span is the smallest one covering every changed box, so the
    edit disturbs nothing else on the lines.
    """
    if start > end:
        start, end = end, start
    lines = _lines_with_offsets(text)
    chosen: list[int] = []
    for number, (offset, line) in enumerate(lines):
        line_end = offset + len(line)
        if line_end < start or offset > end:
            continue
        if offset > start and offset == end and start != end:
            continue  # a selection ending at a line's very start excludes it
        if _TASK_RE.match(line):
            chosen.append(number)
    if not chosen:
        return None
    states: dict[int, bool] = {}
    for n in chosen:
        match = _TASK_RE.match(lines[n][1])
        assert match is not None
        states[n] = match.group(4) != " "
    target = not all(states.values())
    boxes: list[tuple[int, str]] = []
    for n in chosen:
        if states[n] == target:
            continue
        match = _TASK_RE.match(lines[n][1])
        assert match is not None
        boxes.append((lines[n][0] + match.start(4), "x" if target else " "))
    first = boxes[0][0]
    last = boxes[-1][0] + 1
    piece = list(text[first:last])
    for position, char in boxes:
        piece[position - first] = char
    new_text = text[:first] + "".join(piece) + text[last:]
    announcement = _announce(new_text, chosen, target, len(boxes))
    return TaskToggle(first, last, "".join(piece), announcement, len(boxes))


def _announce(new_text: str, chosen: list[int], target: bool, changed: int) -> str:
    lines = _lines_with_offsets(new_text)
    covered: list[int] = []
    for n in chosen:
        for m in _list_run(lines, n):
            if m not in covered:
                covered.append(m)
    items: list[ListItem] = []
    focus = 0
    for m in covered:
        match = _TASK_RE.match(lines[m][1])
        if match is None:
            continue
        if m == chosen[0]:
            focus = len(items)
        items.append(ListItem(text=match.group(5).strip(), checked=match.group(4) != " "))
    model = FlatList(list_type=ListType.CHECKLIST, items=items)
    if len(chosen) == 1:
        return checklist_toggle_announcement(model, focus)
    done = sum(1 for item in items if item.checked)
    verb = "Checked" if target else "Unchecked"
    noun = "task" if changed == 1 else "tasks"
    return f"{verb} {changed} {noun}. {done} of {len(items)} tasks complete."


def task_item_html(rendered_text: str) -> str | None:
    """A rendered list item's inner HTML as a read-only check box, or ``None``.

    *rendered_text* is the item's text after inline rendering. The box is
    disabled -- the page is a picture of the document, not a form -- and the
    ``label`` around it is its accessible name, so a screen reader says
    "check box, checked, Write the tests" rather than a bare "check box".
    """
    match = re.match(r"^\[([ xX])\](?:[ \t]+|$)(.*)$", rendered_text, re.DOTALL)
    if match is None:
        return None
    checked = " checked" if match.group(1) != " " else ""
    return f'<label class="task"><input type="checkbox" disabled{checked}> {match.group(2)}</label>'
