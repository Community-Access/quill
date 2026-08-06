"""Safe test execution for the Regular Expression Helper.

Runs a user-supplied pattern against user-supplied text and reports every
match with its line and column, phrased for speech ("line 12, column 5")
rather than raw offsets a listener would have to convert in their head.

Safety over rawness: both the text size and the match count are bounded, a
zero-width match can never spin the loop forever, and nothing in this module
raises -- a bad pattern or a bad replacement template comes back as a
plain-language sentence in the result, because an unhandled traceback is a
dead end for someone who cannot visually scan it for the relevant line.

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass

from quill.core.regex_helper.explain import diagnose_error

__all__ = ["MatchInfo", "RunResult", "preview_replace", "run_pattern"]


@dataclass(frozen=True)
class MatchInfo:
    """One match, located the way a person navigates a document.

    ``line`` and ``column`` are one-based, matching how editors and screen
    readers announce caret position; ``start``/``end`` are the raw offsets for
    callers that move the caret programmatically. ``groups`` holds the text of
    each capture group (``None`` for groups that did not participate).
    """

    start: int
    end: int
    text: str
    line: int
    column: int
    groups: tuple[str | None, ...]


@dataclass(frozen=True)
class RunResult:
    """The outcome of a test run. ``error`` is plain language, never a traceback."""

    ok: bool
    matches: tuple[MatchInfo, ...]
    truncated: bool
    error: str


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for index, ch in enumerate(text):
        if ch == "\n":
            starts.append(index + 1)
    return starts


def _line_column(starts: list[int], offset: int) -> tuple[int, int]:
    line_index = bisect_right(starts, offset) - 1
    return line_index + 1, offset - starts[line_index] + 1


def _compile_error(pattern: str, err: re.error) -> str:
    message, _position = diagnose_error(pattern, err)
    return message


def run_pattern(
    pattern: str,
    text: str,
    *,
    flags: int = 0,
    max_matches: int = 500,
    max_text_chars: int = 200_000,
) -> RunResult:
    """Run ``pattern`` over ``text`` and report every match, safely bounded.

    Oversized text is truncated (and flagged) rather than refused, and the
    match list stops at ``max_matches`` with ``truncated`` set, so a runaway
    pattern like ``.*`` on a huge document degrades to a partial answer
    instead of freezing the app -- a frozen UI is a total loss for a
    screen-reader user, who gets no visual hint that anything is still alive.
    Never raises: compile problems land in ``error`` as plain language.
    """
    truncated = False
    if len(text) > max_text_chars:
        text = text[:max_text_chars]
        truncated = True
    try:
        compiled = re.compile(pattern, flags)
    except re.error as err:
        return RunResult(ok=False, matches=(), truncated=False, error=_compile_error(pattern, err))
    starts = _line_starts(text)
    matches: list[MatchInfo] = []
    position = 0
    while position <= len(text):
        found = compiled.search(text, position)
        if found is None:
            break
        if len(matches) >= max_matches:
            truncated = True
            break
        line, column = _line_column(starts, found.start())
        matches.append(
            MatchInfo(
                start=found.start(),
                end=found.end(),
                text=found.group(0),
                line=line,
                column=column,
                groups=found.groups(),
            )
        )
        # A zero-width match (for example ``a*`` matching nothing) would leave
        # the search position unchanged and loop forever; step past it by hand.
        position = found.end() if found.end() > found.start() else found.start() + 1
    return RunResult(ok=True, matches=tuple(matches), truncated=truncated, error="")


def preview_replace(
    pattern: str,
    replacement: str,
    text: str,
    *,
    count: int = 20,
) -> tuple[str, ...]:
    """Preview the first ``count`` replacements as spoken "before to after" lines.

    Each line is a single sentence -- "'colour' to 'color' at line 12" -- so
    the whole preview can be arrowed through and heard one change at a time
    before anything is committed to the document. A bad pattern or a
    replacement that names a missing group comes back as a one-line
    plain-language message instead of an exception.
    """
    try:
        compiled = re.compile(pattern)
    except re.error as err:
        return (f"The pattern could not be used: {_compile_error(pattern, err)}",)
    starts = _line_starts(text)
    lines: list[str] = []
    position = 0
    while position <= len(text) and len(lines) < count:
        found = compiled.search(text, position)
        if found is None:
            break
        try:
            after = found.expand(replacement)
        except re.error as err:
            detail = err.msg or str(err)
            if "group" in detail:
                return (
                    "The replacement text refers to a group that the pattern "
                    f"does not define ({detail}).",
                )
            return (f"The replacement text is not valid: {detail}.",)
        except (IndexError, KeyError) as err:
            return (
                f"The replacement text refers to a group that the pattern does not define ({err}).",
            )
        line, _column = _line_column(starts, found.start())
        lines.append(f"'{found.group(0)}' to '{after}' at line {line}")
        position = found.end() if found.end() > found.start() else found.start() + 1
    return tuple(lines)
