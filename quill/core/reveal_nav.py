"""Reveal Codes navigation model — the caret motion the pane *feels* like (wx-free).

The token stream (:mod:`quill.core.reveal_codes`) is deliberately coarse: a whole
run of visible text is a single ``TEXT`` token. That is the right granularity for a
*list* of codes, but it is the wrong granularity for a caret. To make the Reveal
Codes pane feel like editing real text — arrow through characters, jump by word
with Ctrl+Arrow, move by line with Up/Down, and step *over* a ``[Bold On]`` code as
one atomic unit — we flatten the token stream into **navigation cells**:

* one cell per visible character (a ``TEXT`` token becomes N cells), and
* one atomic cell per code (``[Bold On]``, ``[Tab]``, ``[¶]`` …).

Every cell records where it sits in the editor buffer (``markup_offset``) *and* in
the flowed rendering (``flow_start``/``flow_end``), so the pane drives both the
editor caret and its own visible caret from a single integer index. Line indices
are assigned so Up/Down move by logical line (hard returns), matching how the caret
moves in the editor itself.

Pure logic, no ``wx``. The pane in :mod:`quill.ui.reveal_codes_pane` owns the widget
and the speech; this module owns *where the caret goes* and *what it should say*.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.reveal_codes import CodeToken, TokenKind, describe_token

# The flowed glyph for a hard return, followed by a real newline so the visible
# caret wraps and Up/Down have somewhere to go. Kept in sync with the pane.
_HARD_RETURN_GLYPH = "[¶]"


def _is_hard_return(token: CodeToken) -> bool:
    return token.kind is TokenKind.STRUCTURE and token.label.endswith("Hard Return")


def _speak_char(char: str) -> str:
    """How a single character announces when the caret lands on it.

    Literal for printable glyphs; a spoken name for whitespace the ear cannot
    otherwise distinguish. Screen readers already do this for real text; because
    the pane is the *sole* speaker during navigation (see the pane's key handler),
    we reproduce the convention here rather than inherit it from the control.
    """
    if char == " ":
        return "space"
    if char == " ":
        return "non-breaking space"
    return char


def _is_word_char(char: str | None) -> bool:
    return char is not None and (char.isalnum() or char == "'")


@dataclass(frozen=True, slots=True)
class NavCell:
    """One caret stop in the flowed Reveal Codes view.

    A *text* cell (``is_code`` false) is a single visible character. A *code* cell
    is an entire bracketed code, navigated atomically — one Left/Right steps over
    the whole thing.
    """

    token_index: int  # index into the source token stream
    kind: TokenKind
    is_code: bool
    char: str | None  # the character for a text cell, else None
    markup_offset: int  # editor-buffer caret target
    visible_offset: int  # clean-text offset
    flow_start: int  # offset into the flowed string (caret lands here)
    flow_end: int
    line: int  # 0-based logical line
    spoken: str  # bare per-cell announcement (char name, or code phrase)
    label: str  # what is drawn in the flowed string


@dataclass(frozen=True, slots=True)
class FlowView:
    """The flowed rendering and its aligned navigation cells."""

    text: str
    cells: tuple[NavCell, ...]

    @property
    def line_count(self) -> int:
        return (self.cells[-1].line + 1) if self.cells else 0


def build_flow_view(tokens: list[CodeToken]) -> FlowView:
    """Flatten ``tokens`` into the flowed string + the aligned nav cells.

    The string is what the pane's read-only control shows; the cells are what the
    caret model walks. They are built together so ``flow_start`` always points at
    the exact character offset the visible caret should occupy.
    """
    parts: list[str] = []
    cells: list[NavCell] = []
    pos = 0
    line = 0
    for ti, token in enumerate(tokens):
        if token.kind is TokenKind.TEXT:
            for i, char in enumerate(token.label):
                cells.append(
                    NavCell(
                        token_index=ti,
                        kind=TokenKind.TEXT,
                        is_code=False,
                        char=char,
                        markup_offset=token.markup_start + i,
                        visible_offset=token.visible_start + i,
                        flow_start=pos,
                        flow_end=pos + 1,
                        line=line,
                        spoken=_speak_char(char),
                        label=char,
                    )
                )
                pos += 1
            parts.append(token.label)
            continue

        hard_return = _is_hard_return(token)
        piece = _HARD_RETURN_GLYPH if hard_return else f"[{token.label}]"
        cells.append(
            NavCell(
                token_index=ti,
                kind=token.kind,
                is_code=True,
                char=None,
                markup_offset=token.markup_start,
                visible_offset=token.visible_start,
                flow_start=pos,
                flow_end=pos + len(piece),
                line=line,
                spoken=token.spoken,
                label=piece,
            )
        )
        pos += len(piece)
        parts.append(piece)
        if hard_return:
            parts.append("\n")
            pos += 1
            line += 1
    return FlowView("".join(parts), tuple(cells))


# --------------------------------------------------------------------------- #
# Caret motion. The caret is an index into ``cells`` (the cell it rests on).
# Every mover clamps to a valid cell and never raises, so the pane can bind it
# straight to a key without guarding bounds.
# --------------------------------------------------------------------------- #
def _clamp(index: int, cells: tuple[NavCell, ...]) -> int:
    if not cells:
        return 0
    return max(0, min(index, len(cells) - 1))


def move_char(cells: tuple[NavCell, ...], index: int, direction: int) -> int:
    """Left/Right by one cell: one character in text, one whole code over a code."""
    return _clamp(index + (1 if direction > 0 else -1), cells)


def move_word(cells: tuple[NavCell, ...], index: int, direction: int) -> int:
    """Ctrl+Left/Right: to the next/previous word start; codes are hard stops."""
    n = len(cells)
    if n == 0:
        return 0
    if direction > 0:
        i = index
        if i < n and cells[i].is_code:  # sitting on a code: step off it first
            return _clamp(i + 1, cells)
        while i < n and _is_word_char(cells[i].char):  # over the current word
            i += 1
        while i < n and not cells[i].is_code and not _is_word_char(cells[i].char):
            i += 1  # over trailing separators, but stop at a code
        return _clamp(i, cells)
    # Backward: to the start of the word at or before the caret.
    i = index - 1
    while i > 0 and not cells[i].is_code and not _is_word_char(cells[i].char):
        i -= 1
    if i >= 0 and cells[i].is_code:
        return i
    while i > 0 and _is_word_char(cells[i - 1].char):
        i -= 1
    return _clamp(i, cells)


def _line_cells(cells: tuple[NavCell, ...], line: int) -> list[int]:
    return [i for i, c in enumerate(cells) if c.line == line]


def move_line(cells: tuple[NavCell, ...], index: int, direction: int) -> int:
    """Up/Down by one logical line, holding the column where it can."""
    if not cells:
        return 0
    index = _clamp(index, cells)
    cur = cells[index].line
    target = cur + (1 if direction > 0 else -1)
    if target < 0 or target > cells[-1].line:
        return index
    here = _line_cells(cells, cur)
    col = here.index(index) if index in here else 0
    there = _line_cells(cells, target)
    if not there:
        return index
    return there[min(col, len(there) - 1)]


def line_home(cells: tuple[NavCell, ...], index: int) -> int:
    if not cells:
        return 0
    index = _clamp(index, cells)
    here = _line_cells(cells, cells[index].line)
    return here[0] if here else index


def line_end(cells: tuple[NavCell, ...], index: int) -> int:
    if not cells:
        return 0
    index = _clamp(index, cells)
    here = _line_cells(cells, cells[index].line)
    return here[-1] if here else index


def cell_at_flow_offset(cells: tuple[NavCell, ...], flow_offset: int) -> int:
    """The cell whose flowed span best contains ``flow_offset`` (for mouse clicks)."""
    best = 0
    for i, cell in enumerate(cells):
        if cell.flow_start <= flow_offset:
            best = i
        else:
            break
    return best


def cell_for_markup_offset(cells: tuple[NavCell, ...], markup_offset: int) -> int:
    """The cell nearest a markup offset (for editor -> pane sync)."""
    best = 0
    for i, cell in enumerate(cells):
        if cell.markup_offset <= markup_offset:
            best = i
        else:
            break
    return best


# --------------------------------------------------------------------------- #
# What the caret should say when it arrives.
# --------------------------------------------------------------------------- #
def announce_cell(
    tokens: list[CodeToken],
    cells: tuple[NavCell, ...],
    index: int,
    verbosity: str = "balanced",
) -> str:
    """Speech for landing on a cell: the character, or the code's rich phrase."""
    if not 0 <= index < len(cells):
        return ""
    cell = cells[index]
    if not cell.is_code:
        return cell.spoken
    return describe_token(tokens, cell.token_index, verbosity)


def word_at(cells: tuple[NavCell, ...], index: int) -> str:
    """The word (or code phrase) the caret rests on, for Ctrl+Arrow speech."""
    if not 0 <= index < len(cells):
        return ""
    cell = cells[index]
    if cell.is_code:
        return cell.spoken
    letters: list[str] = []
    i = index
    while i < len(cells) and _is_word_char(cells[i].char):
        letters.append(cells[i].char or "")
        i += 1
    return "".join(letters) or cell.spoken


def announce_line(cells: tuple[NavCell, ...], index: int) -> str:
    """The whole logical line the caret is on, the way an editor reads a line move.

    Visible text is read verbatim; a line that carries only codes reads its code
    phrases; an empty line reads "blank line".
    """
    if not 0 <= index < len(cells):
        return ""
    line_ids = _line_cells(cells, cells[index].line)
    text = "".join(cells[i].char or "" for i in line_ids if not cells[i].is_code)
    if text.strip():
        return text
    codes = [
        cells[i].spoken for i in line_ids if cells[i].is_code and not _is_hard_return_cell(cells[i])
    ]
    if codes:
        return ", ".join(codes)
    return "blank line"


def _is_hard_return_cell(cell: NavCell) -> bool:
    return cell.is_code and cell.label == _HARD_RETURN_GLYPH


# --------------------------------------------------------------------------- #
# F2 region editing: the whole span bounded by a formatting ON/OFF pair.
# --------------------------------------------------------------------------- #
# The editable content is the *innermost* enclosing region's source between the
# codes, so a region carrying a tab or a nested code (``**a *b* c**``) edits as a
# unit and nothing is lost — the nested codes ride along as their markup and are
# spliced straight back. A commit is a literal ``markup[start:end] = new_text``.
_EDITABLE_CONTENT = frozenset({TokenKind.TEXT, TokenKind.STRUCTURE, TokenKind.INVISIBLE})


@dataclass(frozen=True, slots=True)
class EditableRegion:
    """The span between a formatting ON/OFF pair, targeted by F2.

    ``markup_start``/``markup_end`` bound the whole inner region in the editor
    buffer — from the first content token after the ON code to the last content
    token before the OFF code — so a commit replaces everything the codes wrap
    while leaving the codes themselves in place.
    """

    token_index: int  # the content token the caret was on
    on_index: int
    off_index: int
    on_label: str  # e.g. "Bold" — for the "Editing bold …" prompt
    markup_start: int
    markup_end: int


def enclosing_region(tokens: list[CodeToken], token_index: int) -> EditableRegion | None:
    """The innermost formatting region enclosing the content token at ``token_index``.

    "Surrounded by formatting codes" means some ``FORMAT_ON`` before the token pairs
    with a ``FORMAT_OFF`` after it; the *closest* such ON wins, so F2 on nested text
    edits the tightest region around the caret. The returned span covers the whole
    inner region — text, tabs, and any nested codes alike. Returns ``None`` for
    plain, unbounded text (or when the caret is on a code itself).
    """
    if not 0 <= token_index < len(tokens):
        return None
    if tokens[token_index].kind not in _EDITABLE_CONTENT:
        return None
    for on_index in range(token_index - 1, -1, -1):
        candidate = tokens[on_index]
        if candidate.kind is not TokenKind.FORMAT_ON:
            continue
        pair = candidate.pair_index
        if pair is None or pair <= token_index:
            continue
        inner_first, inner_last = on_index + 1, pair - 1
        if inner_first > inner_last:  # an empty region has nothing to edit
            return None
        return EditableRegion(
            token_index=token_index,
            on_index=on_index,
            off_index=pair,
            on_label=candidate.label.removesuffix(" On"),
            markup_start=tokens[inner_first].markup_start,
            markup_end=tokens[inner_last].markup_end,
        )
    return None


def region_source(markup: str, region: EditableRegion) -> str:
    """The current editor-buffer text the region wraps (what F2 opens for editing)."""
    start = max(0, min(region.markup_start, len(markup)))
    end = max(start, min(region.markup_end, len(markup)))
    return markup[start:end]


def splice_region(markup: str, region: EditableRegion, new_text: str) -> str:
    """Return ``markup`` with the region's span replaced by ``new_text``."""
    start = max(0, min(region.markup_start, len(markup)))
    end = max(start, min(region.markup_end, len(markup)))
    return markup[:start] + new_text + markup[end:]
