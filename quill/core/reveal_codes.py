"""Reveal Codes — the code-stream model (wx-free).

Turns a QUILL markup string into an ordered stream of **tokens**: visible text
runs interleaved with bracketed *code* tokens for every hidden formatting code and
structural/invisible character — the data both Reveal Codes presentations (the
structured list and the flowed view) render, and the data the sync controller
indexes to keep the pane caret and the editor caret in agreement.

This is the modern, screen-reader-first revival of the WordPerfect "Reveal Codes"
screen (see ``docs/planning/reveal-codes-design.md``). It is built entirely on
existing primitives — :func:`quill.io.rtf_model.analyze_markdown` for the
markup<->visible offset map and per-character formatting, and
:func:`quill.core.char_describe` for invisibles — so the codes it shows always
agree with what the editor and the rich lens understand.

Pure logic, no ``wx``: every token records both its **markup** offset range (what
the editor caret uses, since the editor buffer is the markup) and its **visible**
offset range (the clean-text position), so the pane can drive and follow the editor
caret precisely.
"""

from __future__ import annotations

import enum
import unicodedata
from dataclasses import dataclass, field, replace

from quill.io.rtf_model import MarkdownSegment, analyze_markdown


class TokenKind(enum.Enum):
    """What a token represents in the stream."""

    TEXT = "text"  # a run of visible characters
    FORMAT_ON = "format_on"  # an inline code turning on: [Bold On], [Font: Arial]
    FORMAT_OFF = "format_off"  # the matching close: [Bold Off]
    BLOCK = "block"  # a paragraph-level code at the line head: [Center], [Heading 2]
    STRUCTURE = "structure"  # [Tab], [Hard Return], [Page Break]
    INVISIBLE = "invisible"  # [No-Break Space], [Zero-Width Space], [Smart Quote]


# Inline attributes that produce paired ON/OFF codes, in a stable display order.
_INLINE_FLAGS: tuple[str, ...] = (
    "bold",
    "italic",
    "underline",
    "strike",
    "superscript",
    "subscript",
)
_INLINE_VALUED: tuple[str, ...] = (
    "href",
    "font_family",
    "font_size_pt",
    "color",
    "highlight",
)
_INLINE_ALL: tuple[str, ...] = (*_INLINE_FLAGS, *_INLINE_VALUED)

_FLAG_LABELS: dict[str, str] = {
    "bold": "Bold",
    "italic": "Italic",
    "underline": "Underline",
    "strike": "Strikethrough",
    "superscript": "Superscript",
    "subscript": "Subscript",
}

# Characters surfaced as their own code token rather than hidden inside a text run.
# Maps the character to (label, spoken).
_SPECIAL_CHARS: dict[str, tuple[str, str]] = {
    "\t": ("Tab", "tab"),
    " ": ("No-Break Space", "non-breaking space"),
    " ": ("Narrow No-Break Space", "narrow non-breaking space"),
    "​": ("Zero-Width Space", "zero-width space"),
    "‌": ("Zero-Width Non-Joiner", "zero-width non-joiner"),
    "‍": ("Zero-Width Joiner", "zero-width joiner"),
    "‘": ("Smart Quote ‘", "left smart quote"),
    "’": ("Smart Quote ’", "right smart quote"),
    "“": ("Smart Quote “", "left double smart quote"),
    "”": ("Smart Quote ”", "right double smart quote"),
    "–": ("En Dash", "en dash"),
    "—": ("Em Dash", "em dash"),
    "…": ("Ellipsis", "ellipsis"),
}

_ALIGN_LABELS: dict[str, tuple[str, str]] = {
    "left": ("Left", "left aligned"),
    "right": ("Right", "right aligned"),
    "center": ("Center", "centered"),
    "justify": ("Justify", "justified"),
}


@dataclass(frozen=True, slots=True)
class CodeToken:
    """One element of the Reveal Codes stream.

    ``markup_*`` are offsets into the document buffer (the editor caret space);
    ``visible_*`` are offsets into the clean visible text. For a zero-width code the
    start and end are equal; for a ``TEXT`` run they span the run.
    """

    kind: TokenKind
    label: str  # display / braille: "Bold On", "Tab", "Font: Arial", "Hello"
    spoken: str  # screen-reader phrase: "bold on", "tab", "font Arial"
    markup_start: int
    markup_end: int
    visible_start: int
    visible_end: int
    pair_index: int | None = None  # index of the matching ON/OFF partner
    attrs: dict[str, str] = field(default_factory=dict)

    @property
    def is_code(self) -> bool:
        """True for everything except a visible-text run."""
        return self.kind is not TokenKind.TEXT


def _attr_value(segment: MarkdownSegment | None, name: str) -> object:
    """Active value of inline attribute ``name`` (bool for flags, value otherwise)."""
    if segment is None:
        return False if name in _INLINE_FLAGS else None
    value = getattr(segment, name)
    return bool(value) if name in _INLINE_FLAGS else value


def _value_label(name: str, value: object) -> tuple[str, str]:
    """(display label, spoken phrase) for a valued inline code like a font."""
    if name == "href":
        return f"Link: {value}", f"link to {value}"
    if name == "font_family":
        return f"Font: {value}", f"font {value}"
    if name == "font_size_pt":
        return f"Size: {value}", f"{value} point"
    if name == "color":
        return f"Color: {value}", f"{value} text"
    if name == "highlight":
        return f"Highlight: {value}", f"{value} highlight"
    return f"{name}: {value}", f"{name} {value}"


def _block_codes(segment: MarkdownSegment) -> list[tuple[str, str, dict[str, str]]]:
    """Paragraph-level codes for the head of a paragraph: (label, spoken, attrs)."""
    codes: list[tuple[str, str, dict[str, str]]] = []
    if segment.heading_level:
        lvl = segment.heading_level
        codes.append((f"Heading {lvl}", f"heading level {lvl}", {"level": str(lvl)}))
    elif segment.bullet:
        codes.append(("• List", "bullet", {}))
    if segment.named_style:
        codes.append((f"Style: {segment.named_style}", f"{segment.named_style} style", {}))
    if segment.align in _ALIGN_LABELS:
        label, spoken = _ALIGN_LABELS[segment.align]
        codes.append((label, spoken, {"align": segment.align}))
    if segment.line_spacing:
        codes.append((
            f"Line Spacing: {segment.line_spacing}",
            f"{segment.line_spacing} line spacing",
            {},
        ))
    if segment.indent:
        codes.append(("Indent", "indented", {}))
    if segment.first_line_indent:
        codes.append(("First-Line Indent", "first line indent", {}))
    if segment.space_before:
        codes.append(("Space Before", "space before", {}))
    if segment.space_after:
        codes.append(("Space After", "space after", {}))
    return codes


def _inline_changed(prev: MarkdownSegment | None, curr: MarkdownSegment | None) -> bool:
    return any(_attr_value(prev, name) != _attr_value(curr, name) for name in _INLINE_ALL)


class _StreamBuilder:
    """Accumulates tokens with a pending text run and an open-code stack."""

    def __init__(self, markup_len: int, plain_len: int) -> None:
        self.tokens: list[CodeToken] = []
        self._open: dict[str, int] = {}
        self._markup_len = markup_len
        self._plain_len = plain_len
        self._run: list[str] = []
        self._run_md_start = 0
        self._run_md_last = 0
        self._run_vis_start = 0

    def add_to_run(self, char: str, md_offset: int, plain_offset: int) -> None:
        if not self._run:
            self._run_md_start = md_offset
            self._run_vis_start = plain_offset
        self._run.append(char)
        self._run_md_last = md_offset

    def flush_run(self) -> None:
        if not self._run:
            return
        text = "".join(self._run)
        self.tokens.append(
            CodeToken(
                kind=TokenKind.TEXT,
                label=text,
                spoken=text,
                markup_start=self._run_md_start,
                markup_end=self._run_md_last + 1,
                visible_start=self._run_vis_start,
                visible_end=self._run_vis_start + len(text),
            )
        )
        self._run = []

    def emit(self, token: CodeToken) -> None:
        self.flush_run()
        self.tokens.append(token)

    def transitions(
        self,
        prev: MarkdownSegment | None,
        curr: MarkdownSegment | None,
        md_pos: int,
        vis_pos: int,
    ) -> None:
        """Emit OFF (closing) then ON (opening) codes for changed inline attrs."""
        self.flush_run()
        # Close attributes active in prev but not curr.
        for name in _INLINE_ALL:
            was, now = _attr_value(prev, name), _attr_value(curr, name)
            if was and was != now and name in self._open:
                on_index = self._open.pop(name)
                on = self.tokens[on_index]
                base = on.label.removesuffix(" On")
                self.tokens.append(
                    CodeToken(
                        kind=TokenKind.FORMAT_OFF,
                        label=f"{base} Off",
                        spoken=f"{on.spoken.removesuffix(' on')} off",
                        markup_start=md_pos,
                        markup_end=md_pos,
                        visible_start=vis_pos,
                        visible_end=vis_pos,
                        pair_index=on_index,
                    )
                )
                self.tokens[on_index] = replace(on, pair_index=len(self.tokens) - 1)
        # Open attributes active in curr but not prev.
        for name in _INLINE_ALL:
            was, now = _attr_value(prev, name), _attr_value(curr, name)
            if now and was != now:
                if name in _INLINE_FLAGS:
                    label, spoken, attrs = _FLAG_LABELS[name], _FLAG_LABELS[name].lower(), {}
                else:
                    label, spoken = _value_label(name, now)
                    attrs = {name: str(now)}
                self.tokens.append(
                    CodeToken(
                        kind=TokenKind.FORMAT_ON,
                        label=f"{label} On",
                        spoken=f"{spoken} on",
                        markup_start=md_pos,
                        markup_end=md_pos,
                        visible_start=vis_pos,
                        visible_end=vis_pos,
                        attrs=attrs,
                    )
                )
                self._open[name] = len(self.tokens) - 1


def build_code_stream(markup: str) -> list[CodeToken]:
    """Linearize ``markup`` into an ordered list of text + code tokens.

    Built on :func:`analyze_markdown`, so the codes agree exactly with the editor's
    own markup<->visible mapping. Inline formatting becomes paired FORMAT_ON/OFF
    tokens; paragraph attributes become BLOCK tokens at the line head; paragraph
    breaks become ``[Hard Return]``; tabs and notable invisibles become their own
    tokens; everything else is grouped into TEXT runs.
    """
    analysis = analyze_markdown(markup)
    segments = analysis.segments
    plain = analysis.plain_text
    builder = _StreamBuilder(len(markup), len(plain))
    if not segments:
        return builder.tokens

    prev: MarkdownSegment | None = None
    prev_plain = -1

    for seg in segments:
        starting_paragraph = prev is None
        if prev is not None and prev_plain >= 0:
            gap = seg.plain_offset - prev_plain - 1
            if gap > 0:
                # Close any inline codes open in the finished paragraph, then emit
                # one hard return per intervening newline, and reset inline state.
                builder.transitions(prev, None, prev.md_offset + 1, prev_plain + 1)
                for n in range(gap):
                    builder.emit(
                        CodeToken(
                            kind=TokenKind.STRUCTURE,
                            label="¶ Hard Return",
                            spoken="hard return",
                            markup_start=prev.md_offset + 1 + n,
                            markup_end=prev.md_offset + 1 + n,
                            visible_start=prev_plain + 1 + n,
                            visible_end=prev_plain + 2 + n,
                        )
                    )
                prev = None
                starting_paragraph = True

        if starting_paragraph:
            for label, spoken, attrs in _block_codes(seg):
                builder.emit(
                    CodeToken(
                        kind=TokenKind.BLOCK,
                        label=label,
                        spoken=spoken,
                        markup_start=seg.md_offset,
                        markup_end=seg.md_offset,
                        visible_start=seg.plain_offset,
                        visible_end=seg.plain_offset,
                        attrs=attrs,
                    )
                )

        if _inline_changed(prev, seg):
            builder.transitions(prev, seg, seg.md_offset, seg.plain_offset)

        char = plain[seg.plain_offset] if 0 <= seg.plain_offset < len(plain) else ""
        special = _SPECIAL_CHARS.get(char)
        if special:
            label, spoken = special
            builder.emit(
                CodeToken(
                    kind=TokenKind.STRUCTURE if char == "\t" else TokenKind.INVISIBLE,
                    label=label,
                    spoken=spoken,
                    markup_start=seg.md_offset,
                    markup_end=seg.md_offset + 1,
                    visible_start=seg.plain_offset,
                    visible_end=seg.plain_offset + 1,
                )
            )
        else:
            builder.add_to_run(char, seg.md_offset, seg.plain_offset)

        prev = seg
        prev_plain = seg.plain_offset

    builder.flush_run()
    builder.transitions(prev, None, len(markup), len(plain))
    return builder.tokens


def token_at_markup_offset(tokens: list[CodeToken], markup_offset: int) -> int:
    """Index of the token whose markup range best contains ``markup_offset``.

    Used for editor -> pane sync: returns the last token at or before the offset, so
    a caret resting just after a code lands on a sensible neighbour. 0 for empty or
    leading positions.
    """
    best = 0
    for index, token in enumerate(tokens):
        if token.markup_start <= markup_offset:
            best = index
        else:
            break
    return best


def pair_distance(tokens: list[CodeToken], index: int) -> int | None:
    """Visible-character distance from an ON code to its matching OFF, if paired."""
    if not 0 <= index < len(tokens):
        return None
    token = tokens[index]
    if token.pair_index is None:
        return None
    partner = tokens[token.pair_index]
    return abs(partner.visible_start - token.visible_start)


def describe_token(tokens: list[CodeToken], index: int, verbosity: str = "balanced") -> str:
    """The spoken announcement for arriving on a token, honouring verbosity.

    - ``quiet``: the bare label / the text itself.
    - ``balanced``: an ON code adds its reach ("bold on, 12 characters").
    - ``detailed``: also appends a Unicode note for an invisible.
    """
    if not 0 <= index < len(tokens):
        return ""
    token = tokens[index]
    if token.kind is TokenKind.TEXT or verbosity == "quiet":
        return token.spoken
    parts = [token.spoken]
    if token.kind is TokenKind.FORMAT_ON:
        distance = pair_distance(tokens, index)
        if distance is not None:
            parts.append(f"{distance} character{'s' if distance != 1 else ''}")
    if verbosity == "detailed" and token.kind is TokenKind.INVISIBLE:
        note = unicode_note(token.label)
        if note:
            parts.append(note)
    return ", ".join(parts)


def unicode_note(label: str) -> str:
    """A short Unicode note for the (possibly trailing) glyph in a token label."""
    glyph = label[-1] if label else ""
    if not glyph:
        return ""
    try:
        name = unicodedata.name(glyph)
    except (ValueError, TypeError):
        return ""
    return f"{name} (U+{ord(glyph):04X})"
