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

#: The tags whose presence means a buffer is HTML rather than Markdown that
#: happens to contain a tag. Block-level only, deliberately: QuillLite writes
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


class _MarkdownWriter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._list_stack: list[_ListContext] = []
        self._pre_depth = 0
        self._link_href: str | None = None
        self._link_text: list[str] = []
        self._skip_depth = 0  # inside <script>/<style>

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
        if tag in {"script", "style"}:
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
        if tag in {"script", "style"}:
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
        elif tag in {"p", "div", "section", "article", "tr"}:
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
