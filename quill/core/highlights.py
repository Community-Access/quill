"""Highlighted passages: Word's highlight colours, named, found and walked.

Item 39 of the 2026-10-16 editor checklist: "find and hear highlighted
passages in Word documents". The highlight itself already travelled -- the
python-docx reader and writer carry it, the RTF bridge carries it, the Format
menu applies it -- but nothing could tell a listener *where* the highlighted
passages were. A sighted reader of a marked-up contract sees the yellow at a
glance; somebody reading by ear met it only by asking Describe Formatting one
character at a time. This module is the part that does not care which editor
or which control the text is in:

* **The palette.** Word has fifteen highlight colours and stores each one
  under a different spelling in every layer: ``yellow`` in QUILL's hidden
  codes, ``YELLOW`` in python-docx, ``yellow`` in the package XML, but
  ``BRIGHT_GREEN`` / ``green`` / ``#00FF00`` for the same green, and only a
  ``#RRGGBB`` value once the text has been through a Rich Edit control.
  :func:`highlight_name` folds every spelling to one name a person would say,
  and :func:`highlight_hex` / :func:`docx_highlight_member` turn that name back
  into what each writer needs. Before this table existed the round trip lost
  colours twice: the RTF writer knew only six colour names, so a pink or
  turquoise highlight was written as no highlight at all, and the Word writer
  could not read the ``#RRGGBB`` values the Rich Edit control hands back, so
  every highlight in a Word document saved from rich mode came back yellow.
* **The passages.** :func:`passages_from_markdown` reads them out of QUILL's
  canonical Markdown (the ``[text]{highlight="yellow"}`` hidden code), with
  offsets into that same buffer. :func:`align_runs` places highlighted runs
  read from somewhere else -- a Rich Edit control's RTF, a ``.docx`` on disk --
  onto the text the editor is actually showing, by their words and their
  paragraph rather than by offset, so an edit above a passage moves it rather
  than losing it.
* **Walking.** :func:`next_passage` and :func:`previous_passage` wrap at the
  ends, the way Next Inline Note does, and :func:`spoken_passage` /
  :func:`list_label` are the two sentences a listener hears: the colour and
  the words on arrival, and the words, colour and surrounding sentence in the
  list.

wx-free and strict-typed. ``quill.io.rtf_model`` is imported for its Markdown
analysis, the same way :mod:`quill.core.reveal_codes` does.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

__all__ = [
    "HIGHLIGHT_COLOURS",
    "HighlightPassage",
    "HighlightRun",
    "align_runs",
    "docx_highlight_member",
    "highlight_from_colorref",
    "highlight_hex",
    "highlight_name",
    "highlight_rgb",
    "list_label",
    "next_passage",
    "passage_index_at",
    "passages_from_markdown",
    "previous_passage",
    "runs_from_markdown",
    "spoken_passage",
]


@dataclass(frozen=True, slots=True)
class _Colour:
    """One of Word's fifteen highlight colours, in every spelling it has."""

    name: str  #: what QUILL writes in a hidden code and says aloud
    rgb: tuple[int, int, int]
    ooxml: str  #: ``<w:highlight w:val="...">``
    docx_member: str  #: ``docx.enum.text.WD_COLOR_INDEX`` member name


#: Word's highlight palette. The first seven are the ones QUILL's Format menu
#: and hidden codes already used by name, kept under those names so nothing
#: already written changes meaning: "green" is Word's *bright* green and "gray"
#: its light (25 percent) gray. The rest are the darker eight Word also offers.
HIGHLIGHT_COLOURS: tuple[_Colour, ...] = (
    _Colour("yellow", (255, 255, 0), "yellow", "YELLOW"),
    _Colour("green", (0, 255, 0), "green", "BRIGHT_GREEN"),
    _Colour("turquoise", (0, 255, 255), "cyan", "TURQUOISE"),
    _Colour("pink", (255, 0, 255), "magenta", "PINK"),
    _Colour("blue", (0, 0, 255), "blue", "BLUE"),
    _Colour("red", (255, 0, 0), "red", "RED"),
    _Colour("gray", (192, 192, 192), "lightGray", "GRAY_25"),
    _Colour("dark blue", (0, 0, 128), "darkBlue", "DARK_BLUE"),
    _Colour("teal", (0, 128, 128), "darkCyan", "TEAL"),
    _Colour("dark green", (0, 128, 0), "darkGreen", "GREEN"),
    _Colour("violet", (128, 0, 128), "darkMagenta", "VIOLET"),
    _Colour("dark red", (128, 0, 0), "darkRed", "DARK_RED"),
    _Colour("dark yellow", (128, 128, 0), "darkYellow", "DARK_YELLOW"),
    _Colour("dark gray", (128, 128, 128), "darkGray", "GRAY_50"),
    _Colour("black", (0, 0, 0), "black", "BLACK"),
)


def _key(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


#: Every non-hex spelling -> the canonical name. ``docx_member`` names are
#: python-docx's, where ``GREEN`` is the *dark* green: it is looked up last so
#: the hidden-code and XML spelling "green" (bright) wins.
_BY_SPELLING: dict[str, str] = {}
for _entry in HIGHLIGHT_COLOURS:
    _BY_SPELLING.setdefault(_key(_entry.docx_member), _entry.name)
for _entry in HIGHLIGHT_COLOURS:
    _BY_SPELLING[_key(_entry.ooxml)] = _entry.name
for _entry in HIGHLIGHT_COLOURS:
    _BY_SPELLING[_key(_entry.name)] = _entry.name
del _entry  # a loop name must not shadow _colour() below
_BY_SPELLING.update({
    "grey": "gray",
    "brightgreen": "green",
    "lightgrey": "gray",
    "gray25": "gray",
    "grey25": "gray",
    "darkgrey": "dark gray",
    "gray50": "dark gray",
    "grey50": "dark gray",
    "cyan": "turquoise",
    "magenta": "pink",
})

_NO_HIGHLIGHT = {"", "none", "auto", "automatic", "nocolor", "transparent"}


def _parse_hex(value: str) -> tuple[int, int, int] | None:
    digits = value.strip().lstrip("#")
    if len(digits) == 3:
        digits = "".join(char * 2 for char in digits)
    if len(digits) != 6:
        return None
    try:
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
    except ValueError:
        return None


def _nearest(rgb: tuple[int, int, int]) -> str:
    def distance(colour: _Colour) -> int:
        return sum((a - b) ** 2 for a, b in zip(colour.rgb, rgb, strict=True))

    return min(HIGHLIGHT_COLOURS, key=distance).name


def highlight_name(value: object) -> str | None:
    """The canonical colour name for any spelling of a highlight, or ``None``.

    ``None`` means "not highlighted": no value, ``none``/``auto``, or a value
    that names no colour at all. A ``#RRGGBB`` value is matched exactly where
    Word's palette has it and otherwise to the nearest of the fifteen, because
    every highlight a Rich Edit control writes back is a colour value and a
    listener needs a word, not six hex digits.
    """
    if value is None:
        return None
    text = str(value).strip()
    if _key(text) in _NO_HIGHLIGHT:
        return None
    if text.startswith("#"):
        rgb = _parse_hex(text)
        return _nearest(rgb) if rgb is not None else None
    return _BY_SPELLING.get(_key(text))


def _colour(value: object) -> _Colour | None:
    name = highlight_name(value)
    return next((colour for colour in HIGHLIGHT_COLOURS if colour.name == name), None)


def highlight_rgb(value: object) -> tuple[int, int, int] | None:
    """``(r, g, b)`` for any spelling of a highlight colour, or ``None``."""
    colour = _colour(value)
    return colour.rgb if colour is not None else None


def highlight_hex(value: object) -> str | None:
    """``#RRGGBB`` for any spelling of a highlight colour, or ``None``."""
    rgb = highlight_rgb(value)
    if rgb is None:
        return None
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def highlight_from_colorref(value: object) -> str | None:
    """The highlight's name for a Win32 COLORREF (``0x00BBGGRR``), or ``None``.

    For a Rich Edit control's ``ITextFont.BackColor``. Automatic (tomAutoColor
    is negative), out-of-range and plain white backgrounds are "no highlight".
    Describe Formatting in a rich document said nothing about highlighting
    until 2026-10-16, so a listener checking a Word document's yellow passages
    one character at a time heard "Calibri, 11 point" on every one of them.
    """
    try:
        colorref = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return None
    if colorref < 0 or colorref >= 0xFFFFFF:
        return None
    red, green, blue = colorref & 0xFF, (colorref >> 8) & 0xFF, (colorref >> 16) & 0xFF
    return highlight_name(f"#{red:02X}{green:02X}{blue:02X}")


def docx_highlight_member(value: object) -> str | None:
    """The ``WD_COLOR_INDEX`` member name python-docx needs, or ``None``."""
    colour = _colour(value)
    return colour.docx_member if colour is not None else None


# --------------------------------------------------------------------------- #
# Passages
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class HighlightRun:
    """A highlighted run read from somewhere other than the editor's own text.

    ``context`` is the whole paragraph the run sits in and ``offset`` where in
    that paragraph it starts; together they place the run when the same words
    occur twice (two highlighted "the"s in one sentence are two passages).
    """

    colour: str
    text: str
    context: str = ""
    offset: int = -1


@dataclass(frozen=True, slots=True)
class HighlightPassage:
    """One highlighted passage, as positions in the text the editor shows."""

    start: int
    end: int
    colour: str
    text: str
    context: str = ""


def _merge_into_runs(
    pieces: Iterable[tuple[int, str, str | None, str, int]],
) -> list[tuple[int, int, str, str, str, int]]:
    """Group per-character pieces into runs of one colour within one paragraph.

    *pieces* are ``(position, char, colour, paragraph text, offset in paragraph)``;
    the result is ``(start, end, colour, text, paragraph, offset)``.
    """
    runs: list[tuple[int, int, str, str, str, int]] = []
    current: list[object] | None = None
    for position, char, colour, paragraph, offset in pieces:
        name = highlight_name(colour)
        if (
            current is not None
            and name == current[2]
            and paragraph is current[4]
            and position == current[1]
            and char != "\n"
        ):
            current[1] = position + 1
            current[3] = f"{current[3]}{char}"
            continue
        if current is not None:
            runs.append(tuple(current))  # type: ignore[arg-type]
            current = None
        if name is not None and char != "\n":
            current = [position, position + 1, name, char, paragraph, offset]
    if current is not None:
        runs.append(tuple(current))  # type: ignore[arg-type]
    return runs


def _markdown_runs(
    markdown: str,
) -> tuple[list[tuple[int, int, str, str, str, int]], dict[int, int]]:
    """Runs keyed by *plain* offset, and the plain -> Markdown offset table."""
    from quill.io.rtf_model import analyze_markdown

    analysis = analyze_markdown(markdown)
    plain = analysis.plain_text
    lines = plain.split("\n")
    line_of: list[str] = []
    line_start: list[int] = []
    cursor = 0
    for line in lines:
        line_of.extend([line] * (len(line) + 1))
        line_start.extend([cursor] * (len(line) + 1))
        cursor += len(line) + 1
    md_offsets = {segment.plain_offset: segment.md_offset for segment in analysis.segments}
    pieces = (
        (
            segment.plain_offset,
            plain[segment.plain_offset],
            segment.highlight,
            line_of[segment.plain_offset],
            segment.plain_offset - line_start[segment.plain_offset],
        )
        for segment in analysis.segments
        if segment.plain_offset < len(plain)
    )
    return _merge_into_runs(pieces), md_offsets


def passages_from_markdown(markdown: str) -> list[HighlightPassage]:
    """Every ``[text]{highlight=...}`` passage, as offsets into *markdown* itself.

    These are the offsets a Markdown buffer's caret uses, so a passage found
    here can be gone to directly, and recomputing after an edit is what keeps
    them true.
    """
    runs, md_offsets = _markdown_runs(markdown)
    passages: list[HighlightPassage] = []
    for start, end, colour, text, paragraph, _offset in runs:
        if start not in md_offsets or end - 1 not in md_offsets:
            continue
        passages.append(
            HighlightPassage(
                start=md_offsets[start],
                end=md_offsets[end - 1] + 1,
                colour=colour,
                text=text,
                context=paragraph,
            )
        )
    return passages


def runs_from_markdown(markdown: str) -> list[HighlightRun]:
    """The highlighted runs in *markdown*, placed later by :func:`align_runs`.

    For text that is not the editor's own buffer -- the Markdown the RTF bridge
    makes of a Rich Edit control's contents -- where only the words and the
    paragraph can be trusted to match what the control shows.
    """
    runs, _md_offsets = _markdown_runs(markdown)
    return [
        HighlightRun(colour=colour, text=text, context=paragraph, offset=offset)
        for _start, _end, colour, text, paragraph, offset in runs
    ]


def align_runs(runs: Sequence[HighlightRun], text: str) -> list[HighlightPassage]:
    """Place *runs* onto *text*, in order, by their words and their paragraph.

    Each run is looked for after the previous one: first inside its own
    paragraph (found by the paragraph's words, so a list marker or heading
    hashes the editor shows in front of it do not matter), at the offset it
    had there; then anywhere in that paragraph; then anywhere after the last
    passage. A run whose words are no longer in the text -- deleted, or
    retyped -- is left out rather than guessed at.
    """
    passages: list[HighlightPassage] = []
    cursor = 0
    paragraph_cursor = 0
    for run in runs:
        if not run.text.strip():
            continue
        start = -1
        context = run.context
        if context:
            found = text.find(context, paragraph_cursor)
            if found == -1:
                found = text.find(context, max(0, cursor - len(context)))
            if found != -1:
                if run.offset >= 0 and text.startswith(run.text, found + run.offset):
                    start = found + run.offset
                else:
                    start = text.find(run.text, max(found, cursor), found + len(context))
                if start != -1:
                    paragraph_cursor = found
        if start == -1:
            start = text.find(run.text, cursor)
        if start == -1:
            continue
        end = start + len(run.text)
        passages.append(
            HighlightPassage(
                start=start,
                end=end,
                colour=run.colour,
                text=run.text,
                context=context or _line_around(text, start),
            )
        )
        cursor = end
    return passages


def _line_around(text: str, position: int) -> str:
    begin = text.rfind("\n", 0, position) + 1
    finish = text.find("\n", position)
    return text[begin : finish if finish != -1 else len(text)]


# --------------------------------------------------------------------------- #
# Walking and speaking
# --------------------------------------------------------------------------- #


def next_passage(passages: Sequence[HighlightPassage], caret: int) -> int | None:
    """Index of the first passage starting after *caret*, wrapping to the first."""
    if not passages:
        return None
    for index, passage in enumerate(passages):
        if passage.start > caret:
            return index
    return 0


def previous_passage(passages: Sequence[HighlightPassage], caret: int) -> int | None:
    """Index of the last passage starting before *caret*, wrapping to the last.

    "Before" is strict, so pressing Previous on arrival at a passage moves to
    the one before it rather than staying put.
    """
    if not passages:
        return None
    for index in range(len(passages) - 1, -1, -1):
        if passages[index].start < caret:
            return index
    return len(passages) - 1


def passage_index_at(passages: Sequence[HighlightPassage], caret: int) -> int:
    """The passage the caret is in, else the next one, else the last: the list's start row."""
    for index, passage in enumerate(passages):
        if passage.start <= caret < passage.end or passage.start >= caret:
            return index
    return max(0, len(passages) - 1)


def _clip(text: str, limit: int) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"


def spoken_passage(passage: HighlightPassage, index: int, total: int) -> str:
    """What arrival at a passage says: colour, position and the passage's words.

    Not the surrounding sentence: the caret has just moved there and the
    reader will read the line itself if the listener asks. The words are said
    because a program-moved caret is not one every reader speaks, and the
    colour and the count are things only this command knows (GATE-13).
    """
    words = _clip(passage.text, 200)
    return f"{passage.colour.capitalize()} highlight, {index + 1} of {total}: {words}"


def list_label(passage: HighlightPassage, *, width: int = 90) -> str:
    """A list row: the words first (so first-letter navigation works), then where.

    ``"budget is final, yellow highlight, in: The budget is final unless ..."``
    -- the colour on its own would make every row in a one-colour document
    sound the same, which is the thing a list of passages exists to avoid.
    """
    words = _clip(passage.text, width)
    row = f"{words}, {passage.colour} highlight"
    context = " ".join(passage.context.split())
    if context and context != " ".join(passage.text.split()):
        row = f"{row}, in: {_clip(context, width)}"
    return row
