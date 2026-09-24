"""List markers: whether to fill them in, how to write them, how to take them off.

The third job :mod:`quill.core.markdown_sections` had quietly accumulated
(GATE-11), and the one with nothing whatever to do with sections. It lives here
now so that the section modules are about sections.

``is_caret_inside_list`` is the one that reads a document; the rest rewrite a
span of text or answer a yes/no about a setting. All four are pure, and none
of them knows what a widget is.
"""

from __future__ import annotations

import re
import time

__all__ = [
    "fill_numbered_markers",
    "is_caret_inside_list",
    "should_auto_fill_numbers",
    "strip_list_markers",
]


# --- Numbered-list auto-fill gate ------------------------------------------
#
# The EdSharp port toggle for numbered lists (Ctrl+Alt+8) inserts a list
# with leading "1. ", "2. ", "3. " markers when (and only when) one of
# the three OR'd conditions below holds:
#
#   1. the active document surface is markdown (the default-experience
#      rule -- a user who explicitly authored a Markdown file wants
#      markers, and we honour that without an extra click),
#   2. settings.list_auto_fill_numbers is on (explicit opt-in),
#   3. the user just ran toggle_numbered_list on the active document
#      (per-document arming flag with a 5-minute lifetime; cleared on
#      document close).
#
# In every other case the inserted list uses today's no-fill behaviour:
# only the first item gets a marker and the rest are bare lines.
#
# We model this as a single helper that takes a frame-like object so it
# can be exercised from pure unit tests without spinning up a real
# MainFrame.

_LIST_AUTO_FILL_ARM_SECONDS = 300.0


def should_auto_fill_numbers(
    settings: object | None,
    surface: str,
    *,
    armed_until: float = 0.0,
    now: float | None = None,
) -> bool:
    """Return True if a numbered-list insertion should auto-fill markers.

    Parameters mirror the live conditions:

    * ``settings`` — a Settings-like object exposing
      ``list_auto_fill_numbers``; ``None`` disables the explicit opt-in.
    * ``surface`` — the active document surface (``"markdown"``,
      ``"html"``, ``"plain"``).
    * ``armed_until`` — the value of the per-document arming flag (a
      monotonic-clock timestamp); ``0.0`` means no arming.
    * ``now`` — the current monotonic-clock value (defaults to the real
      clock in production; pass a fixed value from tests).
    """
    if surface == "markdown":
        return True
    explicit = bool(getattr(settings, "list_auto_fill_numbers", False))
    if explicit:
        return True
    if armed_until > 0.0:
        current = time.monotonic() if now is None else now
        if current <= armed_until:
            return True
    return False


# --- Numbered-list marker helpers -----------------------------------------
#
# The toggle commands and the auto-fill gate produce Markdown like:
#
#     1. item one
#     2. item two
#     3. item three
#
# so we keep the rewrite pure: fill_numbered_markers scans the inserted
# list and rewrites the leading "1. " markers to "1. ", "2. ", "3. ", ...
# without touching body text.  strip_list_markers removes both bullet
# ("- ") and numbered ("1. ") markers so the toggle can collapse a list
# back to plain text.

_NUMBERED_MARKER_RE = re.compile(r"^(?P<indent>\s*)\d+\.\s")


def fill_numbered_markers(text: str) -> str:
    """Rewrite consecutive '1. ' markers to 1., 2., 3., ... .

    Only the first item of each consecutive numbered run is renumbered.
    Existing non-numbered lines (blank lines, indented sub-items) are
    preserved as-is.
    """
    out_lines: list[str] = []
    counter = 0
    for line in text.splitlines():
        match = _NUMBERED_MARKER_RE.match(line)
        if match is None:
            counter = 0
            out_lines.append(line)
            continue
        counter += 1
        out_lines.append(f"{match.group('indent')}{counter}. {line[match.end() :]}")
    return "\n".join(out_lines)


_BULLET_MARKER_RE = re.compile(r"^(?P<indent>\s*)[-*+]\s")


def strip_list_markers(text: str) -> str:
    """Remove leading '-' / '*' / '+' / 'N. ' markers from each line.

    Blank lines and lines without a recognised marker pass through
    unchanged so the caller's surrounding whitespace is preserved.
    """
    out_lines: list[str] = []
    for line in text.splitlines():
        bullet = _BULLET_MARKER_RE.match(line)
        if bullet is not None:
            out_lines.append(f"{bullet.group('indent')}{line[bullet.end() :]}")
            continue
        numbered = _NUMBERED_MARKER_RE.match(line)
        if numbered is not None:
            out_lines.append(f"{numbered.group('indent')}{line[numbered.end() :]}")
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def is_caret_inside_list(text: str, caret: int, *, markup_kind: str = "markdown") -> bool:
    """Return True if ``caret`` is on or inside a recognised list item.

    Used by the toggle commands to decide whether to insert or strip.
    """
    if markup_kind != "markdown":
        return False
    line_start = text.rfind("\n", 0, caret) + 1
    line_end = text.find("\n", caret)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end]
    return _BULLET_MARKER_RE.match(line) is not None or _NUMBERED_MARKER_RE.match(line) is not None
