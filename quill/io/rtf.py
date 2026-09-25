"""RTF round-trip through the io layer (EDS-21).

Promotes RTF from the previous lossy extract-only path to a real ``io/*`` format
that reads RTF formatting into QUILL's Markdown-style internal markup and writes
that markup back out to valid RTF, following the
``read(path) -> Document`` / ``write(doc, path)`` contract.

The mapping is intentionally line-oriented (one RTF paragraph per source line) so
that the plain-text-first editor surface is unchanged. Supported constructs that
survive a round trip: headings, **bold**, *italic*, bullet lists, and links.
"""

from __future__ import annotations

import codecs
import re
from pathlib import Path

from quill.core.document import Document
from quill.core.heading_ladder import HEADING_POINT_SIZES
from quill.core.inline_markup import normalize_inline_markup
from quill.io.rtf_safety import RtfSafetyReport, scan_rtf_safety
from quill.io.rtf_styles import (
    DEFAULT_HALF_POINTS,
    NAMED_PARAGRAPH_STYLES,
    NAMED_STYLE_BY_INDEX,
    RtfTables,
    escape_rtf_text,
    heading_stylesheet,
)

__all__ = [
    "markdown_to_rtf",
    "read_rtf_document",
    "rtf_to_markdown",
    "write_rtf_document",
]

_RTF_ENCODING = "cp1252"


def _detect_rtf_encoding(path: Path) -> str:
    """Return the code page named by \\ansicpg in the RTF header, or cp1252."""
    with path.open("rb") as fh:
        header = fh.read(512)
    match = re.search(rb"\\ansicpg(\d+)", header)
    if match:
        cp = int(match.group(1))
        try:
            codecs.lookup(f"cp{cp}")
            return f"cp{cp}"
        except LookupError:
            pass
    return _RTF_ENCODING


# Private sentinels used to carry a parsed hyperlink through the tokenizer.
_LINK_OPEN = "\x01"
_LINK_SEP = "\x02"
_LINK_CLOSE = "\x03"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_RE = re.compile(r"^[-*]\s+(.*)$")
_LINK_MD_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
# Hidden-codes run span ``[text]{attrs}`` and alignment/style fenced divs.
_SPAN_MD_RE = re.compile(r"\[([^\]]+)\]\{([^}]*)\}")
_FENCE_OPEN_RE = re.compile(r"^:::+\s*\{([^}]*)\}\s*$")
_FENCE_CLOSE_RE = re.compile(r"^:::+\s*$")
_PAGEBREAK_RE = re.compile(r"^:::+\s*pagebreak\s*$", re.IGNORECASE)
_ATTR_PAIR_RE = re.compile(r'([A-Za-z][\w-]*)\s*=\s*"([^"]*)"|([A-Za-z][\w-]*)')

_ALIGN_CONTROL = {"center": "\\qc", "right": "\\qr", "justify": "\\qj"}
# Line spacing in RTF: \slN\slmult1 where N is the line height in twips at single
# = 240 (so 1.5 -> 360, double -> 480) and \slmult1 means "multiple of a line".
_LINE_SPACING_CONTROL = {
    "1": "\\sl240\\slmult1",
    "1.5": "\\sl360\\slmult1",
    "2": "\\sl480\\slmult1",
}

_FIELD_RE = re.compile(
    r'\{\\field\{\\\*\\fldinst\s*HYPERLINK\s*"([^"]*)"\s*\}\{\\fldrslt\s*(.*?)\}\}',
    re.DOTALL,
)
_SENTINEL_RE = re.compile(f"{_LINK_OPEN}(.*?){_LINK_SEP}(.*?){_LINK_CLOSE}", re.DOTALL)

#: ``{onttbl{0 Calibri;}{1 Arial;}}`` -- scanned up front rather than
#: walked, because the table is a flat list of name-per-index and the tokenizer
#: would otherwise have to leave its skip-destination fast path to read it.
_FONT_TABLE_RE = re.compile(r"\\f(\d+)[^;}]*?\s+([^;}]+);")
#: Where the font table stops. A non-greedy ``\}`` cannot be used to find it: the
#: table is a group *of* groups, so the first ``}`` closes only its first entry
#: and the scan would see one font however many the document declares.
_FONT_TABLE_END_RE = re.compile(r"\{\\(?:stylesheet|colortbl|info)|\\pard")

_SKIP_DESTINATIONS = {
    "fonttbl",
    "stylesheet",
    "info",
    "pntext",
    "pntxta",
    "pntxtb",
    "listtable",
    "listoverridetable",
    "generator",
    "themedata",
    "colorschememapping",
    "latentstyles",
    "datastore",
    "mmath",
    "header",
    "footer",
}


def _parse_pairs(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in _ATTR_PAIR_RE.finditer(raw):
        if match.group(1) is not None:
            attrs[match.group(1).lower()] = match.group(2)
        elif match.group(3) is not None:
            attrs.setdefault(match.group(3).lower(), "")
    return attrs


# --------------------------------------------------------------------------- #
# Markdown -> RTF
# --------------------------------------------------------------------------- #


def _span_controls(raw: str, tables: RtfTables) -> tuple[str, str]:
    """Return ``(open, close)`` RTF control runs for a span's attributes."""
    attrs = _parse_pairs(raw)
    opens: list[str] = []
    closes: list[str] = []
    family = attrs.get("font-family", "")
    if family:
        opens.append(f"\\f{tables.font_index(family)}")
    size = attrs.get("font-size", "")
    if size.isdigit():
        opens.append(f"\\fs{int(size) * 2}")  # RTF font size is in half-points
    color = attrs.get("color", "")
    if color:
        index = tables.color_index(color)
        if index:
            opens.append(f"\\cf{index}")
    highlight = attrs.get("highlight", "")
    if highlight:
        index = tables.color_index(highlight)
        if index:
            opens.append(f"\\highlight{index}")
    if "underline" in attrs:
        opens.append("\\ul")
        closes.append("\\ulnone")
    if "strike" in attrs:
        opens.append("\\strike")
        closes.append("\\strike0")
    if "superscript" in attrs:
        opens.append("\\super")
        closes.append("\\nosupersub")
    elif "subscript" in attrs:
        opens.append("\\sub")
        closes.append("\\nosupersub")
    return "".join(opens), "".join(closes)


def _block_controls(attrs: dict[str, str], *, include_indent: bool) -> str:
    """Return the RTF paragraph control words for a fenced div's block attributes.

    ``include_indent`` is ``False`` for bullets (which carry their own
    ``\\fi-360\\li720`` hanging indent) so block indent does not fight the bullet.
    """
    parts: list[str] = []
    # The named style first, so Word opens the paragraph *as* Quote/Title rather
    # than as Normal that happens to be indented and italic. Written as a real
    # \\sN pointing at the stylesheet entry, which is the only thing that puts a
    # name in Word's style box and the style in its gallery.
    named = NAMED_PARAGRAPH_STYLES.get(attrs.get("pstyle", "").lower())
    if named:
        parts.append(f"\\s{named[0]}")
    align_cw = _ALIGN_CONTROL.get(attrs.get("align", ""), "")
    if align_cw:
        parts.append(align_cw)
    spacing = _LINE_SPACING_CONTROL.get(attrs.get("line-spacing", ""), "")
    if spacing:
        parts.append(spacing)
    before = attrs.get("space-before", "")
    if before.isdigit():
        parts.append(f"\\sb{int(before) * 20}")  # points -> twips
    after = attrs.get("space-after", "")
    if after.isdigit():
        parts.append(f"\\sa{int(after) * 20}")
    if include_indent:
        indent = attrs.get("indent", "")
        if indent.isdigit():
            parts.append(f"\\li{int(indent) * 20}")
        first = attrs.get("first-line-indent", "")
        if first.isdigit():
            parts.append(f"\\fi{int(first) * 20}")
    return "".join(parts)


def _inline_to_rtf(text: str, tables: RtfTables) -> str:
    result: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        link = _LINK_MD_RE.match(text, index)
        if link:
            url = escape_rtf_text(link.group(2))
            label = _inline_to_rtf(link.group(1), tables)
            result.append(f'{{\\field{{\\*\\fldinst HYPERLINK "{url}"}}{{\\fldrslt {label}}}}}')
            index = link.end()
            continue
        span = _SPAN_MD_RE.match(text, index)
        if span:
            opens, closes = _span_controls(span.group(2), tables)
            inner = _inline_to_rtf(span.group(1), tables)
            if opens:
                result.append("{" + opens + " " + inner + closes + "}")
            else:
                result.append(inner)
            index = span.end()
            continue
        if text.startswith("**", index):
            close = text.find("**", index + 2)
            if close != -1:
                result.append("{\\b " + _inline_to_rtf(text[index + 2 : close], tables) + "}")
                index = close + 2
                continue
        if text[index] == "*":
            close = text.find("*", index + 1)
            if close != -1:
                result.append("{\\i " + _inline_to_rtf(text[index + 1 : close], tables) + "}")
                index = close + 1
                continue
        result.append(escape_rtf_text(text[index]))
        index += 1
    return "".join(result)


def markdown_to_rtf(markdown: str) -> str:
    """Render QUILL Markdown-style markup to a valid RTF document string.

    Supports the readable subset (headings, bold, italic, bullets, links) plus the
    hidden-codes vocabulary: per-run font family, point size, color, highlight,
    underline, strikethrough and super/subscript (via ``[text]{...}`` spans),
    per-paragraph alignment, line spacing, spacing and indent (via fenced divs),
    and page breaks (``::: pagebreak``). Fonts and colors are collected into RTF
    font and color tables in a single pass over the body.

    Inline HTML emphasis (``<u>``, ``<b>``, ``~~strike~~``) is normalised to that
    span vocabulary first. Markdown has no underline syntax, so Insert Tag writes
    ``<u>text</u>`` -- which this writer had no rule for, and so emitted as four
    literal characters sitting in the paragraph. The words arrived; the underline
    did not, and neither did anything saying so.
    """
    markdown = normalize_inline_markup(markdown)
    tables = RtfTables()
    body: list[str] = []
    block: dict[str, str] = {}
    for line in markdown.split("\n"):
        if _PAGEBREAK_RE.match(line):
            body.append("\\page")
            continue
        opener = _FENCE_OPEN_RE.match(line)
        if opener:
            block = _parse_pairs(opener.group(1))
            continue
        if _FENCE_CLOSE_RE.match(line):
            block = {}
            continue
        prefix = _block_controls(block, include_indent=True)
        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            content = _inline_to_rtf(heading.group(2), tables)
            # A real Word heading, not merely bold text that happens to be large:
            # the \sN reference is what fills Word's style box and its navigation
            # pane, and the size is the editor's own ladder so a saved file reopens
            # at the level it was saved at. The trailing reset matters because
            # \pard resets the paragraph and not the font -- without it every
            # paragraph after a heading would inherit the heading's size.
            half_points = int(round(HEADING_POINT_SIZES[level] * 2))
            body.append(
                f"\\pard{prefix}\\s{level}\\outlinelevel{level - 1}\\keepn"
                f"\\b\\fs{half_points} {content}\\b0\\fs{DEFAULT_HALF_POINTS}\\par"
            )
            continue
        item = _LIST_RE.match(line)
        if item:
            bullet_prefix = _block_controls(block, include_indent=False)
            content = _inline_to_rtf(item.group(1), tables)
            body.append(
                f"\\pard{bullet_prefix}\\fi-360\\li720{{\\pntext\\bullet\\tab}}{content}\\par"
            )
            continue
        body.append(f"\\pard{prefix} {_inline_to_rtf(line, tables)}\\par")
    # A size in the preamble, before the first paragraph: it is what every
    # paragraph that never names one is written at. Without it that size was
    # the *reader's* default, which RTF puts at twelve points -- and twelve
    # points is Heading 4 on the editor's ladder, so body text in every file
    # QUILL wrote was indistinguishable from a heading as soon as somebody
    # bolded it.
    header = (
        "{\\rtf1\\ansi\\deff0"
        + tables.font_table()
        + tables.color_table()
        + heading_stylesheet()
        + f"\\fs{DEFAULT_HALF_POINTS}"
        + "\n"
    )
    return header + "\n".join(body) + "\n}"


# --------------------------------------------------------------------------- #
# RTF -> Markdown
# --------------------------------------------------------------------------- #
def _strip_rtf_inline(fragment: str) -> str:
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", fragment)
    text = text.replace("{", "").replace("}", "")
    return text.strip()


def _tokenize(rtf: str) -> list[tuple[str, object, object]]:
    tokens: list[tuple[str, object, object]] = []
    index = 0
    length = len(rtf)
    while index < length:
        char = rtf[index]
        if char == "\\":
            nxt = rtf[index + 1] if index + 1 < length else ""
            if nxt.isalpha():
                end = index + 1
                while end < length and rtf[end].isalpha():
                    end += 1
                word = rtf[index + 1 : end]
                param: int | None = None
                if end < length and (rtf[end] == "-" or rtf[end].isdigit()):
                    start = end
                    if rtf[end] == "-":
                        end += 1
                    while end < length and rtf[end].isdigit():
                        end += 1
                    param = int(rtf[start:end])
                if end < length and rtf[end] == " ":
                    end += 1
                tokens.append(("word", word, param))
                index = end
            elif nxt == "'":
                hex_digits = rtf[index + 2 : index + 4]
                try:
                    tokens.append(("char", chr(int(hex_digits, 16)), None))
                except ValueError:
                    pass
                index += 4
            else:  # "\\", "\{" and "\}" are literal text, not control symbols
                tokens.append(("char" if nxt in "\\{}" else "symbol", nxt, None))
                index += 2
        elif char == "{":
            tokens.append(("group_open", None, None))
            index += 1
        elif char == "}":
            tokens.append(("group_close", None, None))
            index += 1
        elif char in "\r\n":
            index += 1
        else:
            tokens.append(("char", char, None))
            index += 1
    return tokens


#: The extras signature carried per run: (color, highlight, underline, strike,
#: superscript, subscript). Bold/italic are emitted inline as ``**``/``*`` markers;
#: these wrap the run in a ``[text]{...}`` span when present.
_Sig = tuple[str | None, str | None, bool, bool, bool, bool, str | None, str | None]


def _sig_to_attrs(sig: _Sig) -> str:
    color, highlight, underline, strike, superscript, subscript, family, size = sig
    parts: list[str] = []
    if family:
        parts.append(f'font-family="{family}"')
    if size:
        parts.append(f'font-size="{size}"')
    if color:
        parts.append(f'color="{color}"')
    if highlight:
        parts.append(f'highlight="{highlight}"')
    if underline:
        parts.append("underline")
    if strike:
        parts.append("strike")
    if superscript:
        parts.append("superscript")
    if subscript:
        parts.append("subscript")
    return " ".join(parts)


def _parse_font_table(rtf: str) -> dict[int, str]:
    """``{\fonttbl}`` as ``index -> family name``.

    Scanned from the raw RTF rather than walked by the tokenizer, which skips
    the whole destination. Without it ``\f1`` in the body is an index into a
    table nobody read, so the font a person chose came back as no font at all.
    """
    start = rtf.find(chr(123) + chr(92) + "fonttbl")
    if start < 0:
        return {}
    end_match = _FONT_TABLE_END_RE.search(rtf, start + 9)
    window = rtf[start : end_match.start() if end_match else len(rtf)]
    fonts: dict[int, str] = {}
    for index, name in _FONT_TABLE_RE.findall(window):
        cleaned = name.strip()
        if cleaned:
            fonts[int(index)] = cleaned
    return fonts


class _RtfReader:
    """Parse RTF into QUILL markup, recovering the readable subset plus the run
    attributes the writer materializes: underline, strikethrough, super/subscript,
    text color and highlight. Bold/italic stay inline ``**``/``*``; the other
    attributes wrap a run in a hidden-codes span ``[text]{...}``. ``\\colortbl`` is
    parsed so ``\\cfN`` / ``\\highlightN`` resolve to ``#RRGGBB`` values.
    """

    def __init__(self, rtf: str) -> None:
        self._tokens = _tokenize(rtf)
        self._font_table = _parse_font_table(rtf)
        self._paragraphs: list[str] = []
        self._parts: list[str] = []
        self._run_parts: list[str] = []
        self._bold = False
        self._italic = False
        self._emitted_bold = False
        self._emitted_italic = False
        self._underline = False
        self._strike = False
        self._super = False
        self._sub = False
        self._color: str | None = None
        self._highlight: str | None = None
        self._run_sig: _Sig = (None, None, False, False, False, False, None, None)
        #: Font table index -> family name, parsed from {onttbl}. Without
        #: it a 1 in the body is a number with nothing behind it, which is
        #: why font family used to be the one run attribute that did not
        #: survive a save and reopen.
        self._font: str | None = None
        self._fontsize: str | None = None
        self._outline: int | None = None
        #: Block attributes seen on the current paragraph, rebuilt into a
        #: fenced div when it is flushed.
        self._block: dict[str, str] = {}
        self._is_list = False
        self._stack: list[tuple[object, ...]] = []
        self._depth = 0
        self._skip_to_depth: int | None = None
        self._skip_chars = 0
        # Color table state.
        self._colors: list[str | None] = []
        self._colortbl_depth: int | None = None
        self._ct_rgb = [0, 0, 0]
        self._ct_seen = False

    def _current_sig(self) -> _Sig:
        return (
            self._color,
            self._highlight,
            self._underline,
            self._strike,
            self._super,
            self._sub,
            self._font,
            self._fontsize,
        )

    def _sync(self) -> None:
        if self._bold != self._emitted_bold:
            self._run_parts.append("**")
            self._emitted_bold = self._bold
        if self._italic != self._emitted_italic:
            self._run_parts.append("*")
            self._emitted_italic = self._italic

    def _close_emphasis(self) -> None:
        # Close in reverse of the open order (_sync emits ``**`` then ``*``).
        if self._emitted_italic:
            self._run_parts.append("*")
            self._emitted_italic = False
        if self._emitted_bold:
            self._run_parts.append("**")
            self._emitted_bold = False

    def _flush_run(self) -> None:
        self._close_emphasis()
        content = "".join(self._run_parts)
        self._run_parts = []
        if content:
            attrs = _sig_to_attrs(self._run_sig)
            self._parts.append(f"[{content}]{{{attrs}}}" if attrs else content)
        self._run_sig = self._current_sig()

    def _append_text(self, text: str) -> None:
        if self._current_sig() != self._run_sig:
            self._flush_run()
        self._sync()
        self._run_parts.append(text)

    def _reset_run_formatting(self) -> None:
        self._bold = self._italic = False
        self._underline = self._strike = self._super = self._sub = False
        self._color = self._highlight = None
        self._font = self._fontsize = None

    def _flush_paragraph(self) -> None:
        self._reset_run_formatting()
        self._flush_run()
        content = "".join(self._parts)
        if self._outline is not None:
            prefix = "#" * (self._outline + 1) + " "
            content = prefix + content
        elif self._is_list:
            content = "- " + content
        else:
            content = self._wrap_block_attributes(content)
        self._paragraphs.append(content)
        self._parts = []
        self._run_sig = self._current_sig()
        self._outline = None
        self._is_list = False
        self._block = {}

    def _wrap_block_attributes(self, content: str) -> str:
        """Wrap a paragraph in a fenced div when it carries block formatting.

        The writer emits alignment, line spacing, indent and named styles as
        paragraph controls; without this the reader dropped every one of them,
        so a centred quotation came back as an ordinary left-aligned paragraph.
        Nothing said so -- the words were all there -- and saving again wrote
        the flattened version over the original.
        """
        if not self._block or not content.strip():
            return content
        attributes = " ".join(f'{name}="{value}"' for name, value in sorted(self._block.items()))
        return f"::: {{{attributes}}}\n{content}\n:::"

    def _push_color(self) -> None:
        if self._ct_seen:
            self._colors.append("#{:02X}{:02X}{:02X}".format(*self._ct_rgb))
        else:
            self._colors.append(None)  # the auto/default slot
        self._ct_rgb = [0, 0, 0]
        self._ct_seen = False

    def _color_at(self, param: int | None) -> str | None:
        if param is None or param <= 0 or param >= len(self._colors):
            return None
        return self._colors[param]

    def parse(self) -> str:
        for kind, value, param in self._tokens:
            if kind == "group_open":
                self._depth += 1
                self._stack.append((
                    self._bold,
                    self._italic,
                    self._underline,
                    self._strike,
                    self._super,
                    self._sub,
                    self._color,
                    self._highlight,
                    self._font,
                    self._fontsize,
                ))
                continue
            if kind == "group_close":
                if self._stack:
                    (
                        self._bold,
                        self._italic,
                        self._underline,
                        self._strike,
                        self._super,
                        self._sub,
                        self._color,
                        self._highlight,
                        self._font,
                        self._fontsize,
                    ) = self._stack.pop()  # type: ignore[assignment]
                self._depth -= 1
                if self._skip_to_depth is not None and self._depth < self._skip_to_depth:
                    self._skip_to_depth = None
                if self._colortbl_depth is not None and self._depth < self._colortbl_depth:
                    self._colortbl_depth = None
                continue
            if self._skip_to_depth is not None:
                continue
            if kind == "symbol":
                if value == "*":
                    self._skip_to_depth = self._depth
                continue
            if kind == "word":
                self._handle_word(str(value), param if isinstance(param, int) else None)
                continue
            if kind == "char":
                if self._colortbl_depth is not None:
                    if value == ";":
                        self._push_color()
                    continue
                if self._skip_chars > 0:
                    self._skip_chars -= 1
                    continue
                self._append_text(str(value))
        if self._parts or self._run_parts:
            # Trailing content with no final \par still becomes a paragraph.
            self._flush_paragraph()
        result = "\n".join(self._paragraphs)
        return _SENTINEL_RE.sub(lambda m: f"[{m.group(2)}]({m.group(1)})", result)

    def _handle_word(self, word: str, param: int | None) -> None:
        if self._colortbl_depth is not None:
            if word == "red":
                self._ct_rgb[0] = param or 0
                self._ct_seen = True
            elif word == "green":
                self._ct_rgb[1] = param or 0
                self._ct_seen = True
            elif word == "blue":
                self._ct_rgb[2] = param or 0
                self._ct_seen = True
            return
        if word == "colortbl":
            self._colortbl_depth = self._depth
            self._colors = []
            self._ct_rgb = [0, 0, 0]
            self._ct_seen = False
            return
        if word in _SKIP_DESTINATIONS:
            self._skip_to_depth = self._depth
            return
        if word == "par":
            self._flush_paragraph()
        elif word == "page":
            # The writer emits ``\page`` for ``::: pagebreak``; the reader had no
            # rule for it, so a page break was the one construct that did not
            # survive a save-and-reopen -- it simply vanished, and a document
            # that paginated correctly yesterday quietly stopped doing so.
            self._flush_paragraph()
            # The flush closes whatever paragraph the break interrupted, which
            # on a break standing alone is an empty one -- drop it, or the
            # marker arrives with a blank line in front that was not there.
            if self._paragraphs and not self._paragraphs[-1].strip():
                self._paragraphs.pop()
            self._paragraphs.append("::: pagebreak")
        elif word == "pard":
            self._outline = None
            self._is_list = False
        elif word == "plain":
            self._reset_run_formatting()
        elif word == "b":
            # Headings carry visual \b in RTF but are conveyed by the "#" prefix
            # in Markdown, so don't also emit bold markers inside a heading.
            self._bold = param != 0 and self._outline is None
        elif word == "i":
            self._italic = param != 0
        elif word == "ul":
            self._underline = param != 0
        elif word == "ulnone":
            self._underline = False
        elif word == "strike":
            self._strike = param != 0
        elif word == "super":
            self._super = True
            self._sub = False
        elif word == "sub":
            self._sub = True
            self._super = False
        elif word == "nosupersub":
            self._super = self._sub = False
        elif word == "cf":
            self._color = self._color_at(param)
        elif word == "highlight":
            self._highlight = self._color_at(param)
        elif word == "f" and param is not None:
            family = self._font_table.get(param)
            # 0 is the document default (Calibri), which is the absence of
            # a font choice rather than a choice of Calibri -- writing it into
            # a span would put a font on every character in the document.
            self._font = family if param else None
        elif word == "fs" and param is not None:
            # A heading's size comes from its style, not from the author, and
            # the body default is not a choice either. Recording those would
            # wrap every heading and paragraph in a font-size span.
            if self._outline is not None or param == DEFAULT_HALF_POINTS:
                self._fontsize = None
            else:
                self._fontsize = str(param // 2)
        elif word == "outlinelevel":
            self._outline = param if param is not None else 0
        elif word == "s":
            named = NAMED_STYLE_BY_INDEX.get(param if param is not None else -1)
            if named:
                self._block["pstyle"] = named
        elif word in {"qc", "qr", "qj"}:
            self._block["align"] = {"qc": "center", "qr": "right", "qj": "justify"}[word]
        elif word == "sl" and param:
            # \slN at \slmult1 is a multiple of a single line (240 twips).
            spacing = {240: "1", 360: "1.5", 480: "2"}.get(param)
            if spacing:
                self._block["line-spacing"] = spacing
        elif word == "sb" and param:
            self._block["space-before"] = str(param // 20)  # twips -> points
        elif word == "sa" and param:
            self._block["space-after"] = str(param // 20)
        elif word == "fi" and param:
            if param < 0:
                # The bullet's hanging indent. This is the only thing that tells
                # a list item from an indented paragraph: both carry \li720, so
                # \li alone read a 36pt indent as a bullet and put "- " in front
                # of it.
                self._is_list = True
                self._block.pop("indent", None)
            else:
                self._block["first-line-indent"] = str(param // 20)
        elif word == "li":
            # Written after \fi by the bullet path, so _is_list already knows.
            if param and not self._is_list:
                self._block["indent"] = str(param // 20)
        elif word == "tab":
            self._append_text("\t")
        elif word == "u" and param is not None:
            code = param + 65536 if param < 0 else param
            self._append_text(chr(code))
            self._skip_chars = 1


def rtf_to_markdown(rtf: str) -> str:
    """Convert an RTF document string to QUILL Markdown-style markup."""
    pre = _FIELD_RE.sub(
        lambda m: (
            f"{_LINK_OPEN}{m.group(1)}{_LINK_SEP}{_strip_rtf_inline(m.group(2))}{_LINK_CLOSE}"
        ),
        rtf,
    )
    return _RtfReader(pre).parse()


# --------------------------------------------------------------------------- #
# io contract
# --------------------------------------------------------------------------- #
def read_rtf_sanitized(path: Path) -> RtfSafetyReport:
    """Read + sanitize an RTF file for a native rich ingest (no conversion).

    Rich mode loads real RTF into the native control, so the same
    :func:`quill.io.rtf_safety.scan_rtf_safety` gate that protects the
    conversion path runs here first — embedded objects and binary payloads are
    stripped, remote references flagged — and the *sanitized* RTF is what
    reaches the control. Every RTF ingest goes through safety, no exceptions.
    """
    raw = path.read_text(encoding=_detect_rtf_encoding(path), errors="replace")
    return scan_rtf_safety(raw)


def read_rtf_document(path: Path) -> Document:
    """Read an RTF file into a Document whose text is Markdown-style markup.

    The raw bytes are scanned and sanitized first (embedded objects and binary
    payloads stripped, remote references flagged) before any conversion, so the
    rich surface never receives a dangerous construct. The safety outcome is
    recorded in ``source_metadata`` for the UI to surface.
    """
    raw = path.read_text(encoding=_detect_rtf_encoding(path), errors="replace")
    safety = scan_rtf_safety(raw)
    metadata: dict[str, object] = {
        "source_kind": "rtf",
        "engine": "rtf",
        "quality_score": 100,
        "rtf_safe": safety.safe,
    }
    if safety.blocked:
        metadata["rtf_blocked"] = list(safety.blocked)
    if safety.warnings:
        metadata["rtf_warnings"] = list(safety.warnings)
    return Document(
        text=rtf_to_markdown(safety.sanitized_rtf),
        path=path,
        modified=False,
        encoding="utf-8",
        line_ending="\n",
        source_metadata=metadata,
    )


def write_rtf_document(document: Document, path: Path | None = None) -> Path:
    """Write a Document's Markdown-style markup out as valid RTF.

    When the document has a Header/Footer Builder spec (#892), real
    ``{\\header}``/``{\\footer}`` groups (with a live PAGE field) are injected
    into the output — best-effort, never the reason a save fails.
    """
    target_path = path or document.path
    if target_path is None:
        raise ValueError("A path is required to save this document.")
    rtf = markdown_to_rtf(document.text)
    try:
        import datetime

        from quill.core.header_footer_store import HeaderFooterStore, key_for
        from quill.io.header_footer_export import inject_rtf_header_footer

        spec = HeaderFooterStore.load().get(key_for(document.path or target_path))
        if spec is not None:
            name = Path(target_path).name
            rtf = inject_rtf_header_footer(
                rtf,
                spec,
                title=name.rsplit(".", 1)[0] if "." in name else name,
                filename=name,
                date=datetime.date.today().isoformat(),
            )
    except Exception:  # noqa: BLE001 - header export must never break a save
        pass
    from quill.core.storage import write_bytes_atomic

    # Write atomically (temp + os.replace): a crash or disk-full mid-save must
    # leave the previous file intact, never a truncated one. Encode with the RTF
    # code page first (errors="replace" keeps the old writer's out-of-codepage
    # robustness) and write the bytes atomically.
    write_bytes_atomic(target_path, rtf.encode(_RTF_ENCODING, errors="replace"))
    document.mark_saved(target_path)
    return target_path
