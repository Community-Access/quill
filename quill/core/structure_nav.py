from __future__ import annotations

from quill.core.outline import extract_outline_entries

_OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
_CLOSE_TO_OPEN = {value: key for key, value in _OPEN_TO_CLOSE.items()}


def find_matching_bracket(text: str, cursor: int) -> int | None:
    if not text:
        return None
    candidate_positions = [cursor]
    if cursor > 0:
        candidate_positions.append(cursor - 1)
    for position in candidate_positions:
        if position < 0 or position >= len(text):
            continue
        char = text[position]
        if char in _OPEN_TO_CLOSE:
            return _scan_forward(text, position, char, _OPEN_TO_CLOSE[char])
        if char in _CLOSE_TO_OPEN:
            return _scan_backward(text, position, _CLOSE_TO_OPEN[char], char)
    return None


def next_structure_position(text: str, cursor: int, markup_kind: str) -> int | None:
    markers = _structure_markers(text, markup_kind)
    for marker in markers:
        if marker > cursor:
            return marker
    return None


def previous_structure_position(text: str, cursor: int, markup_kind: str) -> int | None:
    markers = _structure_markers(text, markup_kind)
    for marker in reversed(markers):
        if marker < cursor:
            return marker
    return None


#: What Next and Previous Structure (Alt+Down, Alt+Up) call a bracket it lands
#: on. "Moved to next structure" said only that the key worked (FUX-14 audit).
BRACKET_NAMES: dict[str, str] = {
    "(": "Opening parenthesis",
    ")": "Closing parenthesis",
    "[": "Opening bracket",
    "]": "Closing bracket",
    "{": "Opening brace",
    "}": "Closing brace",
}


def describe_structure_target(text: str, position: int, markup_kind: str) -> tuple[str, bool]:
    """What a Next or Previous Structure landing says, and whether it is a heading.

    A heading says what heading navigation says (level, place and title), so
    the caller latches the caret cue and it is not said twice. A bracket is
    named; anything else in the outline (a YAML key) says its title. The caller
    adds the line and column the way every other browse move does.
    """
    from quill.core.markdown_sections import heading_context_at
    from quill.core.structure_announce import describe_heading_arrival

    # A bracket first: on "## Install (Windows)" the stop at "(" is the
    # parenthesis, not the heading the previous stop already named.
    if 0 <= position < len(text) and text[position] in BRACKET_NAMES:
        return BRACKET_NAMES[text[position]], False
    at_line_start = position == 0 or text[position - 1 : position] == "\n"
    if markup_kind in {"markdown", "html"} and at_line_start:
        context = heading_context_at(text, position, markup_kind)
        if context is not None:
            arrival = describe_heading_arrival(
                context.level, context.title, ordinal=context.ordinal, total=context.total
            )
            return arrival, True
    for entry in extract_outline_entries(text, markup_kind):
        if entry.position == position:
            return entry.title or "Structure", False
    return "Structure", False


def _structure_markers(text: str, markup_kind: str) -> list[int]:
    markers = {entry.position for entry in extract_outline_entries(text, markup_kind)}
    markers.update(index for index, char in enumerate(text) if char in "()[]{}")
    return sorted(markers)


def _scan_forward(text: str, start: int, opening: str, closing: str) -> int | None:
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    return None


def _scan_backward(text: str, start: int, opening: str, closing: str) -> int | None:
    depth = 0
    for index in range(start, -1, -1):
        char = text[index]
        if char == closing:
            depth += 1
        elif char == opening:
            depth -= 1
            if depth == 0:
                return index
    return None
