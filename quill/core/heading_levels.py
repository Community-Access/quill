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
    "heading_text_at",
    "set_heading_level",
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


def heading_text_at(text: str, caret: int, *, markup_kind: str = "markdown") -> str:
    """The words of the caret's heading, without its marker.

    ``## Installing`` gives ``Installing`` and ``<h2>Installing</h2>`` gives the
    same, so an announcement can put the level in front of the text -- "Heading
    2, Installing" -- in one utterance rather than two.

    That ordering is not a preference about tidiness. A cue *queued behind* the
    screen reader is at the reader's mercy: on a large caret jump -- Ctrl+Home,
    a search hit, a bookmark -- NVDA and JAWS cancel whatever is pending and
    start again on the new line, and the "Heading 1" that was waiting its turn
    is simply never heard. Said first, as part of one utterance the editor owns,
    it survives every kind of move.

    A line that is not a heading gives its own text, stripped. Callers pass this
    in whatever mode they are in, including rich text, where the buffer line
    *is* the heading's text.
    """
    start, end = _line_span(text, caret)
    line = text[start:end]
    level = heading_level_at(text, caret, markup_kind=markup_kind)
    body, _attributes = _heading_body(line, markup_kind, level)
    return body


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


def set_heading_level(
    text: str, caret: int, level: int, *, markup_kind: str = "markdown"
) -> HeadingChange:
    """Make the caret's line a heading of *level*, or body text at ``level=0``.

    The absolute sibling of :func:`adjust_heading_level`, which moves a level by
    a step. Both exist because both are real operations with different keys:
    Ctrl+Alt+2 means "this is a Heading 2" whatever it was before, and
    Alt+Shift+Right means "one deeper than it is".

    **It rewrites the line rather than prepending to it**, and that is the whole
    reason this is a function rather than four lines at the call site. Applying
    Heading 2 to a line that is already ``### Notes`` has exactly one sensible
    result -- ``## Notes`` -- and the obvious implementation produces
    ``## ### Notes``, which renders as a Heading 2 whose text begins with three
    hashes. Nothing tells a listener that happened: the reader says "Heading 2"
    either way, and the mistake surfaces later, in the published document.

    ``level=0`` is the way back to body text: the marker comes off and the words
    stay. ``NOT_A_HEADING`` when there was nothing to take off, so the caller can
    say "Already body text" instead of reporting a change that did not happen.
    """
    level = int(level)
    if markup_kind not in {"markdown", "html"}:
        return HeadingChange(LevelResult.NO_MARKUP)
    if level and not (MIN_LEVEL <= level <= MAX_LEVEL):
        return HeadingChange(LevelResult.NO_MARKUP)
    start, end = _line_span(text, caret)
    line = text[start:end]
    old_level = heading_level_at(text, caret, markup_kind=markup_kind)
    body, attributes = _heading_body(line, markup_kind, old_level)
    if not level:
        if not old_level:
            return HeadingChange(LevelResult.NOT_A_HEADING)
        replacement = body
    elif markup_kind == "markdown":
        replacement = f"{'#' * level} {body}".rstrip()
    else:
        replacement = f"<h{level}{attributes}>{body}</h{level}>"
    return HeadingChange(
        LevelResult.OK,
        start=start,
        end=end,
        replacement=replacement,
        old_level=old_level,
        new_level=level,
    )


def _heading_body(line: str, markup_kind: str, old_level: int) -> tuple[str, str]:
    """The words of a line without its heading marker, and any HTML attributes.

    The attributes are carried across for the same reason
    :func:`adjust_heading_level` carries them: an ``id=`` on a heading is very
    often the anchor somebody else's link points at, and dropping it while
    "changing a level" breaks that link silently.
    """
    if not old_level:
        return line.strip(), ""
    if markup_kind == "markdown":
        match = _MARKDOWN.match(line)
        return (match.group(2).strip(), "") if match else (line.strip(), "")
    match = _HTML.match(line)
    return (match.group(3).strip(), match.group(2)) if match else (line.strip(), "")
