"""BRF layout diagnostics and repair (NLS-BRT parity).

Pure, wx-free helpers for the two things a braille proofreader does most when a
``.brf`` will not emboss cleanly: diagnose **page width exceeded** (a line over
the cell limit, almost always trailing spaces) and **page depth exceeded** (a
page over the line limit). They mirror the NLS Braille Repair Tool's status
metrics and its trailing-space / longest-line / longest-page repair workflow.

- :func:`compute_layout_metrics` reports the NLS-style status numbers: the
  cursor column and current line length, the longest line in the file, the
  current/total page counts, the lines on the current page, and the longest
  page — each compared against the configured cell-per-line and line-per-page
  limits.
- :func:`longest_line_offset` / :func:`longest_page_offset` give the caret
  target for "go to the longest line/page" navigation.
- :func:`strip_trailing_spaces_all` / :func:`strip_trailing_spaces_current_line`
  remove trailing spaces while preserving every line ending and form feed.

The page metrics consume a :class:`~quill.core.brf_page_map.BRFPageMap`; the line
metrics walk the text directly so they stay correct regardless of page-break
mode. This module is strict-typed; mypy ``--strict`` must stay clean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.brf_page_map import BRFPageMap

# A run of spaces/tabs immediately before a line ending (LF, CR, FF) or EOF.
_TRAILING_RE = re.compile(r"[ \t]+(?=\r|\n|\f|$)")
# Characters that end a "line" for width measurement: LF, CR, and FF (a form
# feed terminates the last line of a page even without an explicit newline).
_LINE_BREAKS = "\n\r\f"


@dataclass(frozen=True, slots=True)
class LayoutMetrics:
    """NLS-style layout status for the caret position."""

    cursor_column: int  # 1-based cell at the caret on its line
    current_line_length: int  # cells in the caret's line (no line ending)
    longest_line_length: int  # cells in the file's longest line
    longest_line_offset: int  # char offset of that line's first character
    cells_per_line: int  # the configured width limit
    over_width: bool

    current_page: int  # 1-based
    page_count: int
    current_line_on_page: int  # 1-based line within the current page
    lines_on_current_page: int
    longest_page_lines: int
    longest_page_offset: int  # char offset of that page's first character
    lines_per_page: int  # the configured height limit
    over_depth: bool


def _current_line_bounds(text: str, cursor: int) -> tuple[int, int]:
    """Return ``(line_start, line_end)`` for the line containing ``cursor``.

    A line runs between line breaks (LF, CR, or FF). ``line_end`` is the offset
    of the next break or the end of the text (exclusive of the break itself).
    """
    cursor = max(0, min(cursor, len(text)))
    start = 0
    for index in range(cursor - 1, -1, -1):
        if text[index] in _LINE_BREAKS:
            start = index + 1
            break
    end = len(text)
    for index in range(cursor, len(text)):
        if text[index] in _LINE_BREAKS:
            end = index
            break
    return start, end


def iter_lines(text: str) -> list[tuple[int, str]]:
    """Return ``(offset, content)`` for every line, content without its break.

    Lines are split on LF, CR (CRLF counts once), and FF. The offset is the
    character offset of the line's first cell in ``text``.
    """
    lines: list[tuple[int, str]] = []
    start = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\r":
            lines.append((start, text[start:i]))
            if i + 1 < n and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            start = i
        elif ch in "\n\f":
            lines.append((start, text[start:i]))
            i += 1
            start = i
        else:
            i += 1
    lines.append((start, text[start:n]))
    return lines


def longest_line_offset(text: str) -> int:
    """Char offset of the first character of the file's longest line."""
    best_offset = 0
    best_length = -1
    for offset, content in iter_lines(text):
        if len(content) > best_length:
            best_length = len(content)
            best_offset = offset
    return best_offset


def _longest_page(page_map: BRFPageMap) -> tuple[int, int]:
    """Return ``(longest_line_count, start_offset)`` for the deepest page."""
    best_lines = -1
    best_offset = 0
    for page in page_map.pages:
        if page.line_count > best_lines:
            best_lines = page.line_count
            best_offset = page.start_offset
    return max(best_lines, 0), best_offset


def longest_page_offset(page_map: BRFPageMap) -> int:
    """Char offset of the first character of the file's deepest page."""
    return _longest_page(page_map)[1]


def compute_layout_metrics(
    page_map: BRFPageMap,
    text: str,
    cursor: int,
    *,
    cells_per_line: int,
    lines_per_page: int,
) -> LayoutMetrics:
    """Compute the NLS-style layout metrics for the caret at ``cursor``."""
    line_start, line_end = _current_line_bounds(text, cursor)
    current_line_length = line_end - line_start
    cursor_column = max(0, min(cursor, len(text)) - line_start) + 1

    longest_offset = longest_line_offset(text)
    l_start, l_end = _current_line_bounds(text, longest_offset)
    longest_line_length = l_end - l_start

    longest_page_lines, longest_page_off = _longest_page(page_map)

    if page_map.pages:
        page = page_map.page_containing(max(0, min(cursor, len(text))))
        current_page = page.index + 1
        lines_on_current_page = page.line_count
        current_line_on_page = page.line_at_offset(max(0, min(cursor, len(text)))) + 1
    else:
        current_page = 0
        lines_on_current_page = 0
        current_line_on_page = 0

    return LayoutMetrics(
        cursor_column=cursor_column,
        current_line_length=current_line_length,
        longest_line_length=longest_line_length,
        longest_line_offset=longest_offset,
        cells_per_line=cells_per_line,
        over_width=longest_line_length > cells_per_line,
        current_page=current_page,
        page_count=page_map.page_count,
        current_line_on_page=current_line_on_page,
        lines_on_current_page=lines_on_current_page,
        longest_page_lines=longest_page_lines,
        longest_page_offset=longest_page_off,
        lines_per_page=lines_per_page,
        over_depth=longest_page_lines > lines_per_page,
    )


def describe_layout(metrics: LayoutMetrics) -> str:
    """A spoken, screen-reader-friendly summary of the layout metrics."""
    parts = [
        f"Cell {metrics.cursor_column} of {metrics.current_line_length}.",
        f"Longest line {metrics.longest_line_length} of {metrics.cells_per_line} cells"
        + (". Page width exceeded." if metrics.over_width else "."),
        f"Braille page {metrics.current_page} of {metrics.page_count},"
        f" line {metrics.current_line_on_page} of {metrics.lines_on_current_page}.",
        f"Longest page {metrics.longest_page_lines} of {metrics.lines_per_page} lines"
        + (". Page depth exceeded." if metrics.over_depth else "."),
    ]
    return " ".join(parts)


def strip_trailing_spaces_all(text: str) -> tuple[str, int]:
    """Remove trailing spaces/tabs from every line. Returns ``(text, removed)``.

    Line endings (LF, CRLF) and form feeds are preserved exactly; only the
    space/tab run *before* each break (or end of file) is removed.
    """
    result = _TRAILING_RE.sub("", text)
    return result, len(text) - len(result)


def strip_trailing_spaces_current_line(text: str, cursor: int) -> tuple[str, int, int]:
    """Remove trailing spaces/tabs from the caret's line.

    Returns ``(new_text, new_cursor, removed)``. The caret is clamped so it
    never lands past the new end of the line.
    """
    line_start, line_end = _current_line_bounds(text, cursor)
    content = text[line_start:line_end]
    stripped = content.rstrip(" \t")
    removed = len(content) - len(stripped)
    if removed == 0:
        return text, cursor, 0
    new_text = text[:line_start] + stripped + text[line_end:]
    new_end = line_start + len(stripped)
    new_cursor = min(cursor, new_end) if cursor > line_start else cursor
    return new_text, new_cursor, removed
