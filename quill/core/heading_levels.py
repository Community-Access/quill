"""Promote and demote a heading, on the line the caret is on.

Shared because both products need it and neither may own it: QUILL binds
``format.decrease_heading_level`` / ``increase_heading_level`` to Alt+Shift+Left
and Right, and QuillLite binds the same pair. Until 2026-09-09 the rule lived
inline in ``main_frame.py`` as two regexes and four branches, which is exactly
the shape that gets copied rather than called the second time somebody needs it.

The operation is smaller than it looks and the *refusals* are most of it. There
are four different reasons nothing can happen -- the caret is not on a heading,
the document has no markup to put a heading in, the heading is already at level
one, the heading is already at level six -- and to a listener all four are
identical unless they are told apart, because none of them makes a sound and
none of them moves the caret. So this returns a reason rather than a bool, and
the caller's whole job is to say which one it was.

Levels are clamped to 1-6 rather than wrapping. Wrapping would turn "demote past
the bottom" into "promote to the top", which is a document-restructuring
operation nobody asked for and which is hard to notice by ear.

wx-free and directly tested.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "MAX_LEVEL",
    "MIN_LEVEL",
    "HeadingChange",
    "LevelResult",
    "adjust_heading_level",
    "heading_level_at",
]

#: Markdown and HTML both stop at six, so both products do.
MIN_LEVEL = 1
MAX_LEVEL = 6

_MARKDOWN = re.compile(r"^(#{1,6})\s+(.*)$")
_HTML = re.compile(r"^\s*<h([1-6])([^>]*)>(.*)</h\1>\s*$", re.IGNORECASE)


class LevelResult(Enum):
    """Why the caret's heading did or did not change level."""

    OK = "ok"
    #: The caret's line is not a heading.
    NOT_A_HEADING = "not_a_heading"
    #: Already ``#`` -- promoting further would mean wrapping, which is worse.
    AT_TOP = "at_top"
    #: Already ``######``.
    AT_BOTTOM = "at_bottom"
    #: The document has no markup that can express a heading at all.
    NO_MARKUP = "no_markup"


@dataclass(frozen=True, slots=True)
class HeadingChange:
    """What to write, where, and what to say about it."""

    result: LevelResult
    #: The line's span in the original text; ``(0, 0)`` when nothing changed.
    start: int = 0
    end: int = 0
    #: The rewritten line, or ``""`` when nothing changed.
    replacement: str = ""
    old_level: int = 0
    new_level: int = 0

    @property
    def changed(self) -> bool:
        return self.result is LevelResult.OK


def _line_span(text: str, caret: int) -> tuple[int, int]:
    caret = max(0, min(caret, len(text)))
    start = text.rfind("\n", 0, caret) + 1
    end = text.find("\n", start)
    return start, len(text) if end == -1 else end


def heading_level_at(text: str, caret: int, *, markup_kind: str = "markdown") -> int:
    """The heading level of the caret's line, or ``0`` for body text.

    Lives here so that "is this line a heading" is answered by the same two
    patterns that :func:`adjust_heading_level` promotes and demotes. A second
    regex somewhere else is a second answer, and the caret-move announcer
    calling one while Alt+Shift+Right obeys the other is exactly the drift that
    makes an editor feel unreliable to somebody who cannot see the font.
    """
    if markup_kind not in {"markdown", "html"}:
        return 0
    start, end = _line_span(text, caret)
    line = text[start:end]
    if markup_kind == "markdown":
        match = _MARKDOWN.match(line)
        return len(match.group(1)) if match else 0
    html_match = _HTML.match(line)
    return int(html_match.group(1)) if html_match else 0


def adjust_heading_level(
    text: str, caret: int, delta: int, *, markup_kind: str = "markdown"
) -> HeadingChange:
    """Move the caret line's heading *delta* levels, clamped to 1-6.

    *delta* is negative to promote (``##`` -> ``#``, which is *towards* level
    one) and positive to demote, matching QUILL's
    ``decrease_heading_level`` / ``increase_heading_level`` and the Alt+Shift+Left
    / Right keys the two products share: left moves out, right moves in.
    """
    if markup_kind not in {"markdown", "html"}:
        return HeadingChange(LevelResult.NO_MARKUP)
    start, end = _line_span(text, caret)
    line = text[start:end]

    if markup_kind == "markdown":
        match = _MARKDOWN.match(line)
        if match is None:
            return HeadingChange(LevelResult.NOT_A_HEADING)
        old_level = len(match.group(1))
        new_level = min(MAX_LEVEL, max(MIN_LEVEL, old_level + delta))
        if new_level == old_level:
            return HeadingChange(
                LevelResult.AT_TOP if delta < 0 else LevelResult.AT_BOTTOM,
                old_level=old_level,
                new_level=old_level,
            )
        replacement = f"{'#' * new_level} {match.group(2)}"
    else:
        match = _HTML.match(line)
        if match is None:
            return HeadingChange(LevelResult.NOT_A_HEADING)
        old_level = int(match.group(1))
        new_level = min(MAX_LEVEL, max(MIN_LEVEL, old_level + delta))
        if new_level == old_level:
            return HeadingChange(
                LevelResult.AT_TOP if delta < 0 else LevelResult.AT_BOTTOM,
                old_level=old_level,
                new_level=old_level,
            )
        # The attributes are carried across untouched: an id= on a heading is
        # very often the anchor somebody else's link points at, and silently
        # dropping it while "adjusting a level" would break that link.
        replacement = f"<h{new_level}{match.group(2)}>{match.group(3)}</h{new_level}>"

    return HeadingChange(
        LevelResult.OK,
        start=start,
        end=end,
        replacement=replacement,
        old_level=old_level,
        new_level=new_level,
    )
