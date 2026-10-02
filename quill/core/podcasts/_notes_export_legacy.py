"""The four ways show notes go to the clipboard, and the page the browser gets.

qc.md 5c. Jeff: "copy show notes to the clipboard in full form either as plain
text without links or fully formatted, configurable". One wx-free module, one
function per format, a test per format -- because "copy as Markdown" that drops
a heading is worse than no Markdown at all.

* ``plain`` -- paragraphs and lists kept as lines, headings as lines, links
  reduced to their text, timestamps kept. The shipped default; what pastes
  cleanly into an email or a chat.
* ``plain_links`` -- the same, with each link's address in brackets after its
  text, so nothing is lost and nothing is hidden.
* ``markdown`` -- headings, lists and links as Markdown. QUILL is a writing
  app; this is the format a QUILL document wants.
* ``formatted`` -- HTML (for ``CF_HTML``) with an RTF copy beside it, so Word,
  Outlook and QUILL's rich editor paste the formatting and Notepad pastes
  text. Images are referenced by address, never embedded; the renderer never
  kept any, so there are none here.

The same four apply to a podcast's description and to a transcript, from the
same button, so there is one Copy vocabulary.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from html import escape

from quill.core.podcasts.notes_render import (
    HEADING,
    LIST_ITEM,
    PREFORMATTED,
    Block,
    NotesDocument,
)

PLAIN = "plain"
PLAIN_LINKS = "plain_links"
MARKDOWN = "markdown"
FORMATTED = "formatted"
FORMATS: tuple[str, ...] = (PLAIN, PLAIN_LINKS, MARKDOWN, FORMATTED)
FORMAT_LABELS: dict[str, str] = {
    PLAIN: "Plain text",
    PLAIN_LINKS: "Plain text with links",
    MARKDOWN: "Markdown",
    FORMATTED: "Formatted",
}
DEFAULT_FORMAT = PLAIN


def normalize_format(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if text in FORMATS else DEFAULT_FORMAT


def _with_links(block: Block, render: Callable[[str, str], str]) -> str:
    """The block's text with each link rewritten by *render(text, url)*."""
    out: list[str] = []
    cursor = 0
    for span in sorted(block.links, key=lambda s: s.start):
        out.append(block.text[cursor : span.start])
        out.append(render(block.text[span.start : span.end], span.url))
        cursor = span.end
    out.append(block.text[cursor:])
    return "".join(out)


def to_plain(doc: NotesDocument, *, with_links: bool = False) -> str:
    """Lines: a heading is a line, a list item keeps its bullet, links are text."""
    lines: list[str] = []
    for block in doc.blocks:
        if with_links:
            text = _with_links(
                block, lambda t, u: f"{t} [{u}]" if t.strip() and t.strip() != u else u
            )
        else:
            text = block.text
        if block.kind == HEADING and lines:
            lines.append("")
        lines.append(text)
        if block.kind == HEADING:
            lines.append("")
    return "\n".join(lines).strip() + ("\n" if lines else "")


def to_markdown(doc: NotesDocument) -> str:
    lines: list[str] = []
    for block in doc.blocks:
        text = _with_links(block, lambda t, u: f"[{t}]({u})" if t.strip() else f"<{u}>")
        if block.kind == HEADING:
            if lines:
                lines.append("")
            lines.append("#" * max(1, min(6, block.level or 2)) + " " + text)
            lines.append("")
        elif block.kind == LIST_ITEM:
            body = text[2:] if text.startswith("• ") else text
            lines.append("- " + body)
        elif block.kind == PREFORMATTED:
            lines.extend(("```", block.text, "```"))
        else:
            if lines and lines[-1] != "" and not lines[-1].startswith("- "):
                lines.append("")
            lines.append(text)
    return "\n".join(lines).strip() + ("\n" if lines else "")


def to_html(doc: NotesDocument, *, title: str = "", page_title: str = "") -> str:
    """An HTML fragment, or a whole page when *title* is given."""
    parts: list[str] = []
    in_list = False
    for block in doc.blocks:
        text = (
            _with_links(
                block, lambda t, u: f'<a href="{escape(u, quote=True)}">{escape(t or u)}</a>'
            )
            if block.links
            else escape(block.text)
        )
        if block.kind == LIST_ITEM:
            if not in_list:
                parts.append("<ul>")
                in_list = True
            body = text[2:] if text.startswith("• ") else text
            parts.append(f"<li>{body}</li>")
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        if block.kind == HEADING:
            level = max(1, min(6, block.level or 2))
            parts.append(f"<h{level}>{text}</h{level}>")
        elif block.kind == PREFORMATTED:
            parts.append(f"<pre>{escape(block.text)}</pre>")
        else:
            parts.append(f"<p>{text}</p>")
    if in_list:
        parts.append("</ul>")
    fragment = "\n".join(parts)
    if not title:
        return fragment
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>{escape(page_title or title)}</title></head>\n<body>\n<main>\n"
        f"<h1>{escape(title)}</h1>\n{fragment}\n</main>\n</body></html>\n"
    )


_SCRIPTS = re.compile(
    r"<(script|style|iframe|object|embed)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)
_EVENT_ATTRS = re.compile(r"\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)


def browser_page(html: str, *, title: str, page_title: str = "") -> str:
    """The notes as the podcast wrote them, with images, as a page without scripts.

    Scripts, styles, frames and event handlers are removed; everything else --
    images by address, formatting, links -- is the podcast's own.
    """
    body = _EVENT_ATTRS.sub("", _SCRIPTS.sub("", html or ""))
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>{escape(page_title or title)}</title></head>\n<body>\n<main>\n"
        f"<h1>{escape(title)}</h1>\n{body}\n</main>\n</body></html>\n"
    )


def _rtf_escape(text: str) -> str:
    out: list[str] = []
    for char in text:
        code = ord(char)
        if char in "\\{}":
            out.append("\\" + char)
        elif code < 128:
            out.append(char)
        else:
            out.append(f"\\u{code if code < 32768 else code - 65536}?")
    return "".join(out)


def to_rtf(doc: NotesDocument) -> str:
    """A small RTF document: headings bold and larger, lists bulleted, links as fields."""
    body: list[str] = []
    for block in doc.blocks:
        if block.kind == HEADING:
            size = {1: 32, 2: 28, 3: 26}.get(block.level or 2, 24)
            body.append(f"\\pard\\sa120\\b\\fs{size} {_rtf_escape(block.text)}\\b0\\fs22\\par")
            continue
        text = (
            _with_links(
                block,
                lambda t, u: (
                    '{\\field{\\*\\fldinst{HYPERLINK "' + _rtf_escape(u) + '"}}'
                    "{\\fldrslt{\\ul\\cf1 " + _rtf_escape(t or u) + "}}}"
                ),
            )
            if block.links
            else _rtf_escape(block.text)
        )
        if block.kind == LIST_ITEM:
            body.append(
                "\\pard\\li360\\fi-360 "
                + text.replace(_rtf_escape("• "), "\\bullet  ", 1)
                + "\\par"
            )
        elif block.kind == PREFORMATTED:
            body.append("\\pard\\f1 " + _rtf_escape(block.text).replace("\n", "\\line ") + "\\par")
        else:
            body.append("\\pard\\sa120 " + text + "\\par")
    return (
        "{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Segoe UI;}{\\f1 Consolas;}}"
        "{\\colortbl;\\red0\\green0\\blue238;}\\fs22\n" + "\n".join(body) + "\n}"
    )


def export(doc: NotesDocument, fmt: str) -> str:
    """The clipboard text for *fmt* (``formatted`` gives the HTML fragment)."""
    kind = normalize_format(fmt)
    if kind == PLAIN:
        return to_plain(doc)
    if kind == PLAIN_LINKS:
        return to_plain(doc, with_links=True)
    if kind == MARKDOWN:
        return to_markdown(doc)
    return to_html(doc)


def spoken_copy(fmt: str, doc: NotesDocument, *, what: str = "the show notes") -> str:
    """ "Copied the show notes as plain text, 412 words.\""""
    label = FORMAT_LABELS[normalize_format(fmt)].lower()
    words = doc.word_count
    return f"Copied {what} as {label}, {words} word{'' if words == 1 else 's'}."


__all__ = [
    "DEFAULT_FORMAT",
    "FORMATS",
    "FORMATTED",
    "FORMAT_LABELS",
    "MARKDOWN",
    "PLAIN",
    "PLAIN_LINKS",
    "browser_page",
    "export",
    "normalize_format",
    "spoken_copy",
    "to_html",
    "to_markdown",
    "to_plain",
    "to_rtf",
]
