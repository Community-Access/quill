"""Import interpretation: text -> list items / definition entries (§5, §6, §17, §18).

Turning a selection, pasted text, or file contents into model items is where the
"excellent defaults, no silent data loss" promise lives. The functions here are
deliberately conservative: they detect consistently-used markers, treat blank
lines as paragraph separators without inventing blank items, and — crucially for
definition lists — refuse to silently pick a term/definition separator when more
than one is plausible (§18.2), surfacing the ambiguity for the preview instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from quill.core.lists.model import (
    DefinitionEntry,
    DefinitionList,
    FlatList,
    ListItem,
    ListType,
)
from quill.core.lists.settings import StructuredListSettings

# Marker shapes for import detection (§6.2). Ordered allows "." or ")".
_BULLET_RE = re.compile(r"^[ \t]*([-+*])[ \t]+(.*)$")
_ORDERED_RE = re.compile(r"^[ \t]*\d+[.)][ \t]+(.*)$")
_TASK_RE = re.compile(r"^[ \t]*[-+*][ \t]+\[([ xX])\][ \t]+(.*)$")


class SelectionMode(Enum):
    AUTO = "auto"
    PARAGRAPH = "paragraph"
    NONBLANK_LINE = "nonblank_line"
    EVERY_LINE = "every_line"


def strip_marker(line: str) -> tuple[str, str, bool]:
    """Return ``(content, kind, checked)`` after removing any list marker.

    ``kind`` is one of ``"task"``, ``"ordered"``, ``"bullet"``, or ``""`` when the
    line carries no recognizable marker. Task markers are checked *before* bullet
    markers because a task line is also a bullet line.
    """
    task = _TASK_RE.match(line)
    if task is not None:
        return task.group(2), "task", task.group(1).lower() == "x"
    ordered = _ORDERED_RE.match(line)
    if ordered is not None:
        return ordered.group(1), "ordered", False
    bullet = _BULLET_RE.match(line)
    if bullet is not None:
        return bullet.group(2), "bullet", False
    return line, "", False


def _is_list_line(line: str) -> bool:
    """True when ``line`` carries a recognizable bullet/ordered/task marker."""
    return strip_marker(line)[1] != ""


def find_list_block(text: str, offset: int) -> tuple[int, int] | None:
    """Char range of the contiguous list block containing ``offset`` (§4.2).

    A "list line" is one with a recognizable marker (:func:`strip_marker`). The
    block is the maximal run of consecutive list lines containing the caret's
    line. Returns ``None`` when the caret is not on a list line, so the caller can
    fall back to starting a fresh list. The returned range excludes any trailing
    newline so replacing it leaves the surrounding blank lines intact.
    """
    if not text:
        return None
    lines = text.split("\n")
    # Character offset at the start of each line.
    starts: list[int] = []
    pos = 0
    for line in lines:
        starts.append(pos)
        pos += len(line) + 1  # +1 for the '\n' that split removed
    # The caret line is the last line whose start is <= offset.
    caret_line = 0
    for i, start in enumerate(starts):
        if start <= offset:
            caret_line = i
        else:
            break
    if not _is_list_line(lines[caret_line]):
        return None
    top = caret_line
    while top > 0 and _is_list_line(lines[top - 1]):
        top -= 1
    bottom = caret_line
    while bottom + 1 < len(lines) and _is_list_line(lines[bottom + 1]):
        bottom += 1
    block_start = starts[top]
    block_end = starts[bottom] + len(lines[bottom])
    return (block_start, block_end)


def list_block_to_flat(text: str, settings: StructuredListSettings | None = None) -> FlatList:
    """Parse a block of existing list lines into a :class:`FlatList`, keeping nesting.

    Indentation widths across the block are ranked so 2-space, 4-space, or tab
    indents all map to sequential nesting levels (so an edited nested list is not
    silently flattened). The type is checklist when every line is a task, ordered
    when every marker is numbered, otherwise bullet. Non-marker and blank lines are
    skipped. An empty block yields a single empty bullet item.
    """
    cfg = settings if settings is not None else StructuredListSettings()
    parsed: list[tuple[int, str, str, bool]] = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        content, kind, checked = strip_marker(line)
        if kind == "":
            continue
        indent = len(line) - len(line.lstrip(" \t"))
        parsed.append((indent, _trim(content, cfg), kind, checked))
    if not parsed:
        return FlatList(list_type=ListType.BULLET, items=[ListItem("")])
    widths = sorted({indent for indent, _c, _k, _ck in parsed})
    rank = {width: level for level, width in enumerate(widths)}
    items = [
        ListItem(text=content, level=rank[indent], checked=checked)
        for indent, content, _kind, checked in parsed
    ]
    if all(kind == "task" for _i, _c, kind, _ck in parsed):
        list_type = ListType.CHECKLIST
    elif all(kind == "ordered" for _i, _c, kind, _ck in parsed):
        list_type = ListType.ORDERED
    else:
        list_type = ListType.BULLET
    return FlatList(list_type=list_type, items=items)


def _trim(text: str, settings: StructuredListSettings) -> str:
    if settings.trim_leading:
        text = text.lstrip(" \t")
    if settings.trim_trailing:
        text = text.rstrip(" \t")
    if settings.collapse_internal_spaces:
        text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def _resolve_mode(text: str, settings: StructuredListSettings) -> SelectionMode:
    configured = settings.selection_mode
    if configured == "paragraph":
        return SelectionMode.PARAGRAPH
    if configured == "nonblank_line":
        return SelectionMode.NONBLANK_LINE
    if configured == "every_line":
        return SelectionMode.EVERY_LINE
    # AUTO (§5.1 recommended): blank-line-separated content reads as paragraphs;
    # otherwise each non-blank line is its own item.
    has_blank_separator = bool(re.search(r"\n[ \t]*\n", text))
    return SelectionMode.PARAGRAPH if has_blank_separator else SelectionMode.NONBLANK_LINE


def interpret_selection(
    text: str, settings: StructuredListSettings | None = None
) -> list[tuple[str, str, bool]]:
    """Interpret ``text`` into ``(content, marker_kind, checked)`` item tuples.

    Honors the configured selection mode (auto/paragraph/line), blank-line policy,
    whitespace trimming, and marker detection. Returns one tuple per item; an
    empty selection yields no items.
    """
    cfg = settings if settings is not None else StructuredListSettings()
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        return []
    mode = _resolve_mode(normalized, cfg)
    lines = normalized.split("\n")

    raw_items: list[str] = []
    if mode is SelectionMode.PARAGRAPH:
        paragraph: list[str] = []
        for line in lines:
            if line.strip() == "":
                if paragraph:
                    raw_items.append(_join_paragraph(paragraph, cfg))
                    paragraph = []
                elif cfg.create_blank_items and not cfg.blank_lines_as_separators:
                    raw_items.append("")
            else:
                paragraph.append(line)
        if paragraph:
            raw_items.append(_join_paragraph(paragraph, cfg))
    else:
        for line in lines:
            if line.strip() == "":
                if mode is SelectionMode.EVERY_LINE or cfg.create_blank_items:
                    raw_items.append("")
                continue
            raw_items.append(line)

    items: list[tuple[str, str, bool]] = []
    for raw in raw_items:
        content, kind, checked = (raw, "", False)
        if cfg.detect_existing_markers:
            content, kind, checked = strip_marker(raw)
        items.append((_trim(content, cfg), kind, checked))
    return items


def _join_paragraph(lines: list[str], settings: StructuredListSettings) -> str:
    if settings.preserve_internal_breaks:
        return "\n".join(lines)
    return " ".join(line.strip() for line in lines)


# -- definition-list interpretation (§17, §18) ----------------------------- #

# Ordered most-to-least specific. A tab is the least ambiguous; a bare colon is
# the most (it appears in URLs and prose), so it is only chosen when it divides
# the lines consistently and nothing more specific applies.
_SEPARATORS: list[tuple[str, str]] = [
    ("tab", "\t"),
    ("dash", " - "),
    ("equals", "="),
    ("colon", ":"),
]


@dataclass(slots=True)
class DefinitionInterpretation:
    """A proposed reading of pasted/selected content as definition entries (§18.2)."""

    separator: str  # label: tab|dash|equals|colon|alternating_lines|alternating_paragraphs
    entries: list[tuple[str, str]] = field(default_factory=list)
    ambiguous: bool = False
    candidates: list[str] = field(default_factory=list)
    incomplete_indices: list[int] = field(default_factory=list)


def _split_on(line: str, sep: str) -> tuple[str, str] | None:
    idx = line.find(sep)
    if idx < 0:
        return None
    return line[:idx].strip(), line[idx + len(sep) :].strip()


def detect_definition_separator(text: str) -> DefinitionInterpretation:
    """Pick the best term/definition reading, flagging ambiguity (§18.1, §18.2).

    Tries inline separators (tab, " - ", "=", ":") and the alternating-lines
    pattern. A separator "fits" when it splits the majority of non-blank lines.
    When two or more readings fit comparably the result is marked ``ambiguous``
    so the caller shows a preview rather than guessing (no silent conversion).
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln for ln in normalized.split("\n") if ln.strip()]
    if not lines:
        return DefinitionInterpretation(separator="colon", entries=[])

    fitting: list[str] = []
    best: DefinitionInterpretation | None = None
    for label, sep in _SEPARATORS:
        pairs = [_split_on(ln, sep) for ln in lines]
        hits = sum(1 for p in pairs if p is not None and p[0])
        if hits >= max(1, (len(lines) + 1) // 2):  # splits at least half the lines
            fitting.append(label)
            interp = _build_interpretation(label, lines, sep)
            if best is None:
                best = interp

    # Alternating lines: an even number of lines with no consistent inline sep.
    if not fitting and len(lines) % 2 == 0:
        entries = [(lines[i].strip(), lines[i + 1].strip()) for i in range(0, len(lines), 2)]
        return DefinitionInterpretation(
            separator="alternating_lines",
            entries=entries,
            ambiguous=False,
            candidates=["alternating_lines"],
        )

    if best is None:
        # No separator divides the content; treat each line as a term with a
        # blank definition (the caller's preview lets the user correct this).
        entries = [(ln.strip(), "") for ln in lines]
        return DefinitionInterpretation(
            separator="none", entries=entries, ambiguous=False, candidates=[]
        )

    best.candidates = fitting
    best.ambiguous = len(fitting) > 1
    return best


def _build_interpretation(label: str, lines: list[str], sep: str) -> DefinitionInterpretation:
    entries: list[tuple[str, str]] = []
    incomplete: list[int] = []
    for index, line in enumerate(lines):
        split = _split_on(line, sep)
        if split is None:
            entries.append((line.strip(), ""))
            incomplete.append(index)
        else:
            term, definition = split
            entries.append((term, definition))
            if not term or not definition:
                incomplete.append(index)
    return DefinitionInterpretation(separator=label, entries=entries, incomplete_indices=incomplete)


def interpret_definition_entries(text: str, *, separator: str) -> DefinitionList:
    """Build a :class:`DefinitionList` using an explicitly chosen ``separator``.

    ``separator`` is a label from :class:`DefinitionInterpretation`
    (``tab``/``dash``/``equals``/``colon``/``alternating_lines``/
    ``alternating_paragraphs``) or a literal custom string. The caller picks it
    from the preview, so this function does not re-guess.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if separator == "alternating_paragraphs":
        return _entries_from_alternating_paragraphs(normalized)
    lines = [ln for ln in normalized.split("\n") if ln.strip()]
    if separator == "alternating_lines":
        pairs = [
            (lines[i].strip(), lines[i + 1].strip() if i + 1 < len(lines) else "")
            for i in range(0, len(lines), 2)
        ]
        return _list_from_pairs(pairs)
    sep = {"tab": "\t", "dash": " - ", "equals": "=", "colon": ":"}.get(separator, separator)
    pairs = []
    for line in lines:
        split = _split_on(line, sep) if sep else None
        pairs.append(split if split is not None else (line.strip(), ""))
    return _list_from_pairs(pairs)


def _entries_from_alternating_paragraphs(text: str) -> DefinitionList:
    paragraphs = [p.strip() for p in re.split(r"\n[ \t]*\n", text) if p.strip()]
    pairs = [
        (paragraphs[i], paragraphs[i + 1] if i + 1 < len(paragraphs) else "")
        for i in range(0, len(paragraphs), 2)
    ]
    return _list_from_pairs(pairs)


def _list_from_pairs(pairs: list[tuple[str, str]]) -> DefinitionList:
    entries = [
        DefinitionEntry(terms=[term], definitions=[definition]) for term, definition in pairs
    ]
    return DefinitionList(entries=entries)


def interpret_text_into_flat(text: str, settings: StructuredListSettings | None = None) -> FlatList:
    """Interpret imported/pasted text into a flat list (§17.4 import preview).

    One item per interpreted line or paragraph, with marker detection and a
    checklist promotion when every line is a task. Empty input yields a single
    empty item so the studio always has something to edit and preview.
    """
    cfg = settings if settings is not None else StructuredListSettings()
    interpreted = interpret_selection(text, cfg)
    items = [
        ListItem(text=content, checked=checked)
        for content, _kind, checked in interpreted
        if content.strip() or len(interpreted) == 1
    ]
    if not items:
        items = [ListItem("")]
    is_checklist = bool(interpreted) and all(kind == "task" for _c, kind, _ck in interpreted)
    return FlatList(list_type=ListType.CHECKLIST if is_checklist else ListType.BULLET, items=items)


def interpret_text_into_definition(
    text: str, settings: StructuredListSettings | None = None
) -> DefinitionList:
    """Interpret imported/pasted text into a definition list (§17.5 import preview).

    Uses a confident term/definition separator when one is detected; an ambiguous
    or absent separator falls back to one term-only entry per non-blank line rather
    than guessing a split (§18.2). Empty input yields a single blank entry.
    """
    detection = detect_definition_separator(text)
    if detection.entries and not detection.ambiguous:
        return _list_from_pairs(detection.entries)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    entries = [DefinitionEntry(terms=[line]) for line in lines]
    return DefinitionList(entries=entries or [DefinitionEntry()])
