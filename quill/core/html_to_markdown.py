"""Convert copied HTML into Markdown for the Paste HTML as Markdown command.

The QUILL key, then ``M``, pastes clipboard HTML as Markdown. On Windows the
clipboard's ``HTML Format`` payload is wrapped in a CF_HTML header that points at
the real fragment with byte offsets; :func:`extract_cf_html_fragment` unwraps it.
:func:`html_to_markdown` then turns common structural and inline HTML into
Markdown. Both are UI-framework agnostic so they can be unit-tested without
``wx``; the editor layer only supplies the clipboard payload and inserts the
result.

The converter targets the everyday "copied from a web page or word processor"
case (headings, paragraphs, bold/italic, links, lists, code, block quotes). It is
deliberately forgiving: unknown tags are dropped and their text is kept.

Migration note: the same converter is now vendored into
``quill/quillins_bundled/text-tools/html_ops.py`` for the ``ext.text.html_to_markdown``
Quillin command. The first-party "Paste HTML as Markdown" (QUILL Key + M) still
uses this module. When that command is retired (migration plan Wave N), this
module can be removed and the Quillin becomes the sole implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

__all__ = ["contains_html_markup", "extract_cf_html_fragment", "html_to_markdown"]

#: Tags whose text belongs to the document's *machinery*, not its body, and so
#: must never be emitted as Markdown. ``title`` is the one that bit: a standalone
#: page written by ``markdown_to_html`` carries ``<title>`` in its head, and
#: reading it back turned the file's own name into a first line of body text.
#: Switching a document Markdown -> HTML -> Markdown therefore *grew a line
#: every time*, and because the line is the document's title it reads as
#: something the author wrote rather than as damage.
_SKIPPED_TEXT_TAGS = frozenset({"script", "style", "title"})

#: The tags whose presence means a buffer is HTML rather than Markdown that
#: happens to contain a tag. Block-level only, deliberately: QUILL Lite writes
#: ``<u>`` into *Markdown* documents (there is no native syntax for underline),
#: so an inline tag proves nothing, while a ``<p>`` or an ``<h2>`` is structure
#: no Markdown writer produces. The same set QUILL sniffs content with.
_HTML_BLOCK_TAGS = (
    "html",
    "head",
    "body",
    "div",
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "table",
    "tr",
    "td",
    "th",
    "section",
    "article",
    "header",
    "footer",
    "blockquote",
    "pre",
    "br",
    "hr",
)

_HTML_BLOCK_RE = re.compile(
    r"<\s*/?\s*(?:" + "|".join(_HTML_BLOCK_TAGS) + r")\b[^>]*>", re.IGNORECASE
)


def contains_html_markup(text: str) -> bool:
    """Whether *text* really is HTML, as opposed to being *called* HTML.

    Asked before anything flattens a buffer with :func:`html_to_markdown`. The
    converter is an HTML parser, and HTML has no significant newlines: run it
    over Markdown and every blank line between paragraphs disappears, leaving
    one enormous line with the ``#`` markers still in it. That is not a
    theoretical failure -- ringing Alt+Shift+F round the document kinds did
    exactly it, because the ring re-labels a Markdown buffer "HTML" without
    rewriting a character of it (markup-to-markup switches keep the text; the
    label decides how the *next* insertion is spelled). The next stop then
    believed the label and converted a document that had nothing to convert.
    """
    return _HTML_BLOCK_RE.search(text) is not None


@dataclass
class _ListContext:
    kind: str
    index: int = 0


_BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "tr",
    "hr",
}


def extract_cf_html_fragment(payload: str) -> str:
    """Return the HTML fragment from a Windows CF_HTML clipboard ``payload``.

    A CF_HTML payload begins with a header of ``Key:Value`` lines including
    ``StartFragment``/``EndFragment`` offsets and usually ``<!--StartFragment-->``
    / ``<!--EndFragment-->`` markers. When neither is present the payload is
    returned unchanged, so plain HTML passes straight through.
    """
    start_marker = "<!--StartFragment-->"
    end_marker = "<!--EndFragment-->"
    start = payload.find(start_marker)
    end = payload.find(end_marker)
    if start != -1 and end != -1 and end > start:
        return payload[start + len(start_marker) : end].strip()
    # Fall back to the byte-offset header if the comment markers are absent.
    match_start = re.search(r"StartFragment:(\d+)", payload)
    match_end = re.search(r"EndFragment:(\d+)", payload)
    if match_start and match_end:
        try:
            begin = int(match_start.group(1))
            finish = int(match_end.group(1))
            if 0 <= begin < finish <= len(payload):
                return payload[begin:finish].strip()
        except ValueError:
            pass
    return payload


#: Inline tags that mean one run attribute, mapped to the span keyword that
#: carries it. These are what ``markdown_to_html`` emits for a span it can say
#: in a tag, and what a person hand-writing HTML uses.
_SPAN_TAGS: dict[str, str] = {
    "u": "underline",
    "ins": "underline",
    "s": "strike",
    "strike": "strike",
    "del": "strike",
    "sup": "superscript",
    "sub": "subscript",
}

#: ``style`` declarations back to span attributes -- the exact inverse of what
#: ``markdown_to_html`` writes, so a document that goes out to HTML and comes
#: back keeps its fonts, colours and super/subscripts instead of arriving as
#: bare words. Keyed by CSS property; the value either names a bare flag (when
#: the declaration's own value identifies it) or a span attribute to quote.
_STYLE_FLAGS: dict[tuple[str, str], str] = {
    ("text-decoration", "underline"): "underline",
    ("text-decoration", "line-through"): "strike",
    ("vertical-align", "super"): "superscript",
    ("vertical-align", "sub"): "subscript",
}
_STYLE_ATTRIBUTES: dict[str, str] = {
    "color": "color",
    "background-color": "highlight",
    "background": "highlight",
    "font-family": "font-family",
}


#: ``<div style>`` declarations back to the fenced-div vocabulary -- the inverse
#: of ``_div_style_from_attrs``. Values carrying a unit ("36pt", "1.5") keep only
#: what the fenced div stores.
_BLOCK_STYLE_ATTRIBUTES: dict[str, str] = {
    "text-align": "align",
    "line-height": "line-spacing",
    "margin-top": "space-before",
    "margin-bottom": "space-after",
    "margin-left": "indent",
    "text-indent": "first-line-indent",
}


def _block_attributes_from_style(style: str, pstyle: str) -> str:
    """Translate a ``<div style>`` back into fenced-div attributes.

    ``pstyle`` arrives separately, from ``data-quill-pstyle``, because a named
    style renders as ordinary CSS that nothing can distinguish from somebody
    having asked for that CSS directly.
    """
    pairs: list[str] = []
    for declaration in style.split(";"):
        name, separator, value = declaration.partition(":")
        if not separator:
            continue
        attribute = _BLOCK_STYLE_ATTRIBUTES.get(name.strip().lower())
        value = value.strip()
        if not attribute or not value:
            continue
        if attribute in {"space-before", "space-after", "indent", "first-line-indent"}:
            digits = "".join(ch for ch in value if ch.isdigit())
            if digits:
                pairs.append(f'{attribute}="{digits}"')
            continue
        pairs.append(f'{attribute}="{value}"')
    if pstyle:
        pairs.append(f'pstyle="{pstyle}"')
    return " ".join(pairs)


def _span_attributes_from_style(style: str) -> str:
    """Translate a ``style`` attribute into QUILL's span vocabulary.

    Returns "" when the style says nothing QUILL's markup can carry, so the
    caller emits the text plainly rather than an empty ``[text]{}``.
    """
    flags: list[str] = []
    pairs: list[str] = []
    for declaration in style.split(";"):
        name, separator, value = declaration.partition(":")
        if not separator:
            continue
        name = name.strip().lower()
        value = value.strip()
        if not value:
            continue
        matched = False
        for (flag_name, flag_value), keyword in _STYLE_FLAGS.items():
            if name == flag_name and flag_value in value.lower():
                flags.append(keyword)
                matched = True
        if matched:
            continue
        attribute = _STYLE_ATTRIBUTES.get(name)
        if attribute:
            pairs.append(f'{attribute}="{value.strip(chr(34) + chr(39))}"')
            continue
        if name == "font-size":
            # Written as "18pt" by markdown_to_html; the span carries the number.
            digits = "".join(ch for ch in value if ch.isdigit())
            if digits:
                pairs.append(f'font-size="{digits}"')
    return " ".join(flags + pairs)


class _MarkdownWriter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._list_stack: list[_ListContext] = []
        self._pre_depth = 0
        self._link_href: str | None = None
        self._link_text: list[str] = []
        self._skip_depth = 0  # inside a tag whose text is not body text
        #: Open run spans, as ``(index into _parts, attribute text)``. The index
        #: is where the span's content starts, so closing it lifts the content
        #: back out and re-emits it wrapped -- the same trick the table cells use.
        self._span_stack: list[tuple[int, str]] = []
        #: Rows of the table being read, innermost last. A list per table because
        #: a table inside a table must not append cells to its parent's last row.
        self._table_stack: list[list[list[str]]] = []
        self._cell_start: int | None = None
        #: One entry per open <div>: True when it opened a ``:::`` fence that
        #: must be closed, False when it was an ordinary layout div.
        self._open_divs: list[bool] = []
        self._header_rows = 0

    # -- run spans -------------------------------------------------------
    def _open_span(self, attributes: str) -> None:
        self._span_stack.append((len(self._parts), attributes))

    def _close_span(self) -> None:
        if not self._span_stack:
            return
        start, attributes = self._span_stack.pop()
        inner = "".join(self._parts[start:])
        del self._parts[start:]
        self._parts.append(f"[{inner}]{{{attributes}}}" if inner and attributes else inner)

    # -- helpers ---------------------------------------------------------
    def _emit(self, text: str) -> None:
        if self._link_href is not None:
            self._link_text.append(text)
        else:
            self._parts.append(text)

    def _newline_block(self) -> None:
        if self._parts and not self._parts[-1].endswith("\n\n"):
            if self._parts[-1].endswith("\n"):
                self._parts.append("\n")
            else:
                self._parts.append("\n\n")

    # -- tag handling ----------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED_TEXT_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"strong", "b"}:
            self._emit("**")
        elif tag in {"em", "i"}:
            self._emit("*")
        elif tag == "code" and self._pre_depth == 0:
            self._emit("`")
        elif tag == "pre":
            self._pre_depth += 1
            self._newline_block()
            self._parts.append("```\n")
        elif tag == "br":
            self._emit("\n")
        elif tag == "hr":
            self._newline_block()
            self._parts.append("---")
            self._newline_block()
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._newline_block()
            self._parts.append("#" * int(tag[1]) + " ")
        elif tag in {"ul", "ol"}:
            self._list_stack.append(_ListContext(kind=tag))
            self._newline_block()
        elif tag == "li":
            self._write_list_marker()
        elif tag == "blockquote":
            self._newline_block()
            self._parts.append("> ")
        elif tag == "a":
            href = next((value for name, value in attrs if name == "href"), None)
            self._link_href = href or ""
            self._link_text = []
        elif tag == "img":
            source = next((value for name, value in attrs if name == "src"), None) or ""
            alt = next((value for name, value in attrs if name == "alt"), None) or ""
            self._emit(f"![{alt}]({source})")
        elif tag in _SPAN_TAGS:
            self._open_span(_SPAN_TAGS[tag])
        elif tag == "span":
            style = next((value for name, value in attrs if name == "style"), None) or ""
            self._open_span(_span_attributes_from_style(style))
        elif tag == "div":
            style = next((value for name, value in attrs if name == "style"), None) or ""
            pstyle = (
                next((value for name, value in attrs if name == "data-quill-pstyle"), None) or ""
            )
            if "page-break-after" in style:
                # The page break is a whole empty div; emit the marker and record
                # nothing to close, or the ``:::`` fence would be opened twice.
                self._newline_block()
                self._parts.append("::: pagebreak")
                self._newline_block()
                self._open_divs.append(False)
                return
            attributes = _block_attributes_from_style(style, pstyle)
            if attributes:
                self._newline_block()
                self._parts.append(f"::: {{{attributes}}}" + "\n")
                self._open_divs.append(True)
            else:
                self._open_divs.append(False)
                self._newline_block()
        elif tag == "table":
            self._newline_block()
            self._table_stack.append([])
            self._header_rows = 0
        elif tag == "tr" and self._table_stack:
            self._table_stack[-1].append([])
        elif tag in {"td", "th"} and self._table_stack:
            if not self._table_stack[-1]:
                self._table_stack[-1].append([])
            self._cell_start = len(self._parts)
        elif tag in _BLOCK_TAGS:
            self._newline_block()

    def _write_list_marker(self) -> None:
        if not self._list_stack:
            self._parts.append("- ")
            return
        depth = len(self._list_stack) - 1
        context = self._list_stack[-1]
        indent = "  " * depth
        if self._parts and not self._parts[-1].endswith("\n"):
            self._parts.append("\n")
        if context.kind == "ol":
            context.index += 1
            self._parts.append(f"{indent}{context.index}. ")
        else:
            self._parts.append(f"{indent}- ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_TEXT_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in {"strong", "b"}:
            self._emit("**")
        elif tag in {"em", "i"}:
            self._emit("*")
        elif tag == "code" and self._pre_depth == 0:
            self._emit("`")
        elif tag == "pre":
            self._pre_depth = max(0, self._pre_depth - 1)
            if not self._parts[-1].endswith("\n"):
                self._parts.append("\n")
            self._parts.append("```")
            self._newline_block()
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._newline_block()
        elif tag in {"ul", "ol"}:
            if self._list_stack:
                self._list_stack.pop()
            self._newline_block()
        elif tag == "li":
            if self._parts and not self._parts[-1].endswith("\n"):
                self._parts.append("\n")
        elif tag == "blockquote":
            self._newline_block()
        elif tag == "a":
            text = "".join(self._link_text).strip()
            href = self._link_href or ""
            self._link_href = None
            self._link_text = []
            if href and text:
                self._parts.append(f"[{text}]({href})")
            elif text:
                self._parts.append(text)
        elif tag in _SPAN_TAGS or tag == "span":
            self._close_span()
        elif tag in {"td", "th"} and self._table_stack:
            start = self._cell_start
            self._cell_start = None
            if start is not None:
                cell = "".join(self._parts[start:]).strip().replace("\n", " ")
                del self._parts[start:]
                if self._table_stack[-1]:
                    self._table_stack[-1][-1].append(cell)
                if tag == "th":
                    self._header_rows = 1
        elif tag == "table" and self._table_stack:
            self._emit_table(self._table_stack.pop())
        elif tag == "div":
            if self._open_divs and self._open_divs.pop():
                # One newline before the closing fence, not the blank line
                # _newline_block would leave: ``:::`` belongs against the last
                # line of the block it closes.
                while self._parts and self._parts[-1].endswith("\n\n"):
                    self._parts[-1] = self._parts[-1][:-1]
                if self._parts and not self._parts[-1].endswith("\n"):
                    self._parts.append("\n")
                self._parts.append(":::")
            self._newline_block()
        elif tag in {"p", "section", "article", "tr"}:
            self._newline_block()

    def _emit_table(self, rows: list[list[str]]) -> None:
        """Write a parsed table back as a Markdown pipe table.

        Tables used to be read a cell at a time with no structure at all, so
        ``| a | b |`` came back as ``ab`` -- the header, the columns and the
        alignment row all gone, and the two cells run together into one word.
        A table is the one construct where losing the markup also loses the
        *meaning*, because nothing else says which value sits under which
        heading.
        """
        rows = [row for row in rows if row]
        if not rows:
            return
        width = max(len(row) for row in rows)
        padded = [row + [""] * (width - len(row)) for row in rows]
        header = padded[0] if self._header_rows else [""] * width
        body = padded[1:] if self._header_rows else padded
        self._newline_block()
        lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * width) + "|"]
        lines += ["| " + " | ".join(row) + " |" for row in body]
        self._parts.append("\n".join(lines))
        self._newline_block()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._pre_depth:
            self._emit(data)
            return
        collapsed = re.sub(r"\s+", " ", data)
        if collapsed:
            self._emit(collapsed)

    def result(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # A fenced div's markers belong against the block they wrap. The blank
        # line comes from the whitespace *between* the HTML tags, which is data
        # to an HTML parser and nothing to a reader -- but it makes the round
        # trip differ from what went in, and a round trip that changes the text
        # is one nobody can tell apart from one that damaged it.
        # Only a fence that *opens* a block (``::: {...}``) -- a standalone
        # ``::: pagebreak`` is its own paragraph and keeps the blank line after it.
        text = re.sub(r"(?m)^(:::\s*\{[^\n]*)\n\n", r"\1\n", text)
        text = re.sub(r"\n\n(:::\s*)$", r"\n\1", text)
        text = re.sub(r"\n\n(:::\n)", r"\n\1", text)
        return text.strip() + "\n"


def html_to_markdown(html: str) -> str:
    """Convert an HTML fragment to Markdown.

    Handles headings, paragraphs, line breaks, bold/italic, inline code, code
    blocks, links, ordered/unordered lists (with nesting), block quotes, and
    horizontal rules. Unknown tags are dropped but their text is kept. Returns a
    single trailing newline; an empty or whitespace-only input yields ``""``.
    """
    fragment = extract_cf_html_fragment(html)
    if not fragment.strip():
        return ""
    writer = _MarkdownWriter()
    writer.feed(fragment)
    writer.close()
    rendered = writer.result()
    return rendered if rendered.strip() else ""
