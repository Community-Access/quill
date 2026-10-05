"""A page you can share: one self-contained, accessible HTML file.

What Export as HTML writes in both editors. One file with its styles inside and
no scripts, so it opens the same from an email attachment, a USB stick or a web
server, and needs nothing from the network. The idea of the shareable page is
PlanCake's (Andre of Oire Software).

The stylesheet is deliberately small and does four jobs: a readable column and
size, a ``lang`` on the page so a screen reader speaks it in the right voice,
tables with visible header cells, and notes (when included) marked in words as
well as by a coloured rule, so the marking never depends on colour. It follows
the reader's light or dark setting and prints cleanly.

QUILL runs Pandoc for Markdown when it is installed (:func:`pandoc_html_args`
gives it ``--standalone``, the title, the language and this same stylesheet),
and both editors fall back to QUILL's own renderer
(:func:`standalone_html`), which knows task lists and strikethrough.
"""

from __future__ import annotations

import html
import re

from quill.core.browser_preview import render_preview_body
from quill.core.inline_notes_file import NOTE_LINE_MARK, mark_notes_for_render, parse_file_notes

__all__ = [
    "EXPORT_STYLESHEET",
    "count_file_notes",
    "normalise_language",
    "pandoc_html_args",
    "prepare_for_pandoc",
    "standalone_html",
    "style_block",
]

EXPORT_STYLESHEET = (
    ":root{color-scheme:light dark;}"
    "body{font-family:system-ui,'Segoe UI',Arial,sans-serif;font-size:1.0625rem;"
    "line-height:1.6;max-width:46rem;margin:0 auto;padding:1.5rem 1rem;"
    "color:#1a1a1a;background:#fff;}"
    "h1,h2,h3,h4,h5,h6{line-height:1.25;margin:1.6em 0 .5em;}"
    "a{color:#0b57d0;}"
    "a:focus,input:focus{outline:3px solid #b8860b;outline-offset:2px;}"
    "pre,code{font-family:Consolas,Menlo,monospace;}"
    "pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem;border-radius:6px;}"
    "blockquote{border-left:4px solid #888;margin-left:0;padding-left:1rem;}"
    "table{border-collapse:collapse;margin:1rem 0;}"
    "th,td{border:1px solid #777;padding:.4rem .6rem;text-align:left;vertical-align:top;}"
    "th{background:#eee;}"
    "img{max-width:100%;height:auto;}"
    "label.task input{margin-right:.4rem;}"
    ".quill-note{border-left:4px solid #b8860b;background:#fff8e6;padding:.25rem 1rem;"
    "margin:.5rem 0;}"
    "@media (prefers-color-scheme:dark){"
    "body{background:#1e1e1e;color:#e6e6e6;}a{color:#8ab4f8;}"
    "pre,th{background:#2a2a2a;}th,td{border-color:#666;}"
    ".quill-note{background:#2b2618;}}"
    "@media print{body{max-width:none;padding:0;}a{color:inherit;}}"
)

_LANG_RE = re.compile(r"^[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*$")


def style_block() -> str:
    """The stylesheet as a ``<style>`` element, for a page head or Pandoc's ``-H``."""
    return f"<style>{EXPORT_STYLESHEET}</style>\n"


def normalise_language(value: str) -> str:
    """``en_US`` -> ``en-US``; anything unusable -> ``en``."""
    tag = (value or "").strip().replace("_", "-")
    return tag if _LANG_RE.match(tag) else "en"


def count_file_notes(text: str, kind: str) -> int:
    """How many ``quill-note`` comments a page could include."""
    return len(parse_file_notes(text, kind)) if kind in {"markdown", "html"} else 0


def _plain_body(text: str) -> str:
    """Plain text as paragraphs: blank lines part them, line breaks are kept."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "\n".join(
        "<p>" + "<br>".join(html.escape(line) for line in p.split("\n")) + "</p>"
        for p in paragraphs
    )


def standalone_html(
    text: str, kind: str, title: str, *, lang: str = "en", include_notes: bool = False
) -> str:
    """A whole page for *text*, from QUILL's own renderer.

    A document that is already a whole HTML page is kept as it is, with its
    notes either marked or removed; anything else is wrapped in a page with
    :data:`EXPORT_STYLESHEET`, a title and a language.
    """
    text = text.replace("\r\n", "\n")
    if kind == "html" and re.search(r"<html[\s>]", text, re.IGNORECASE):
        return mark_notes_for_render(text, "html", include_notes)
    if kind in {"markdown", "html"}:
        body = render_preview_body(text, kind, notes=include_notes)
    else:
        body = _plain_body(text)
    return (
        "<!doctype html>\n"
        f'<html lang="{html.escape(normalise_language(lang), quote=True)}">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title or 'Untitled')}</title>\n"
        f"{style_block()}"
        "</head>\n"
        f"<body>\n<main>\n{body}\n</main>\n</body>\n"
        "</html>\n"
    )


def prepare_for_pandoc(text: str, include_notes: bool) -> str:
    """Markdown for Pandoc: notes as raw ``aside`` blocks, or gone."""
    marked = mark_notes_for_render(text.replace("\r\n", "\n"), "markdown", include_notes)
    return marked.replace(NOTE_LINE_MARK, "")


def pandoc_html_args(title: str, lang: str, header_path: str) -> tuple[str, ...]:
    """The Pandoc arguments for a standalone page: title, language, stylesheet."""
    return (
        "--standalone",
        f"--metadata=title:{title or 'Untitled'}",
        f"--metadata=lang:{normalise_language(lang)}",
        f"--include-in-header={header_path}",
    )
