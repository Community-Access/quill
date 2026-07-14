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
from quill.io.rtf_safety import RtfSafetyReport, scan_rtf_safety

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
_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
}


def _parse_pairs(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in _ATTR_PAIR_RE.finditer(raw):
        if match.group(1) is not None:
            attrs[match.group(1).lower()] = match.group(2)
        elif match.group(3) is not None:
            attrs.setdefault(match.group(3).lower(), "")
    return attrs


def _parse_color(value: str) -> tuple[int, int, int] | None:
    text = value.strip()
    if text.startswith("#"):
        digits = text[1:]
        if len(digits) == 3:
            digits = "".join(char * 2 for char in digits)
        if len(digits) == 6:
            try:
                return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
            except ValueError:
                return None
        return None
    return _NAMED_COLORS.get(text.lower())


_FIELD_RE = re.compile(
    r'\{\\field\{\\\*\\fldinst\s*HYPERLINK\s*"([^"]*)"\s*\}\{\\fldrslt\s*(.*?)\}\}',
    re.DOTALL,
)
_SENTINEL_RE = re.compile(f"{_LINK_OPEN}(.*?){_LINK_SEP}(.*?){_LINK_CLOSE}", re.DOTALL)

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


# --------------------------------------------------------------------------- #
# Markdown -> RTF
# --------------------------------------------------------------------------- #
def _escape_rtf_text(text: str) -> str:
    out: list[str] = []
    for char in text:
        code = ord(char)
        if char in "\\{}":
            out.append("\\" + char)
        elif code < 128:
            out.append(char)
        else:
            out.append(f"\\u{code}?")
    return "".join(out)


class _RtfTables:
    """Font and color tables built in a pre-pass and referenced by the writer.

    Index 0 is reserved in both tables (``\\f0`` Calibri default; color index 0 is
    the RTF "auto" slot), so user fonts/colors start at index 1.
    """

    def __init__(self) -> None:
        self.fonts: dict[str, int] = {}
        self.colors: dict[tuple[int, int, int], int] = {}

    def font_index(self, family: str) -> int:
        key = family.strip()
        if not key:
            return 0
        if key not in self.fonts:
            self.fonts[key] = len(self.fonts) + 1
        return self.fonts[key]

    def color_index(self, value: str) -> int:
        rgb = _parse_color(value)
        if rgb is None:
            return 0
        if rgb not in self.colors:
            self.colors[rgb] = len(self.colors) + 1
        return self.colors[rgb]

    def font_table(self) -> str:
        entries = ["{\\f0 Calibri;}"]
        for family, index in sorted(self.fonts.items(), key=lambda item: item[1]):
            entries.append(f"{{\\f{index} {_escape_rtf_text(family)};}}")
        return "{\\fonttbl" + "".join(entries) + "}"

    def color_table(self) -> str:
        if not self.colors:
            return ""
        # Color indices are assigned in insertion order (1..N); sorting by index
        # restores that order for the table body.
        ordered = sorted(self.colors.items(), key=lambda item: item[1])
        body = "".join(f"\\red{rgb[0]}\\green{rgb[1]}\\blue{rgb[2]};" for rgb, _index in ordered)
        # Leading ';' produces the empty auto entry at index 0.
        return "{\\colortbl;" + body + "}"


def _span_controls(raw: str, tables: _RtfTables) -> tuple[str, str]:
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


def _inline_to_rtf(text: str, tables: _RtfTables) -> str:
    result: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        link = _LINK_MD_RE.match(text, index)
        if link:
            url = _escape_rtf_text(link.group(2))
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
        result.append(_escape_rtf_text(text[index]))
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
    """
    tables = _RtfTables()
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
            body.append(f"\\pard{prefix}\\outlinelevel{level - 1}\\b {content}\\b0\\par")
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
    header = "{\\rtf1\\ansi\\deff0" + tables.font_table() + tables.color_table() + "\n"
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
            else:
                tokens.append(("symbol", nxt, None))
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
_Sig = tuple[str | None, str | None, bool, bool, bool, bool]


def _sig_to_attrs(sig: _Sig) -> str:
    color, highlight, underline, strike, superscript, subscript = sig
    parts: list[str] = []
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


class _RtfReader:
    """Parse RTF into QUILL markup, recovering the readable subset plus the run
    attributes the writer materializes: underline, strikethrough, super/subscript,
    text color and highlight. Bold/italic stay inline ``**``/``*``; the other
    attributes wrap a run in a hidden-codes span ``[text]{...}``. ``\\colortbl`` is
    parsed so ``\\cfN`` / ``\\highlightN`` resolve to ``#RRGGBB`` values.
    """

    def __init__(self, rtf: str) -> None:
        self._tokens = _tokenize(rtf)
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
        self._run_sig: _Sig = (None, None, False, False, False, False)
        self._outline: int | None = None
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

    def _flush_paragraph(self) -> None:
        self._reset_run_formatting()
        self._flush_run()
        content = "".join(self._parts)
        if self._outline is not None:
            prefix = "#" * (self._outline + 1) + " "
            content = prefix + content
        elif self._is_list:
            content = "- " + content
        self._paragraphs.append(content)
        self._parts = []
        self._run_sig = self._current_sig()
        self._outline = None
        self._is_list = False

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
        elif word == "outlinelevel":
            self._outline = param if param is not None else 0
        elif word == "li":
            if param:
                self._is_list = True
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
    target_path.write_text(rtf, encoding=_RTF_ENCODING, errors="replace")
    document.mark_saved(target_path)
    return target_path
