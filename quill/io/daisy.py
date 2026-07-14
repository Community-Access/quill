"""Write a document out as a DAISY 2.02 text-only talking book (#251).

A DAISY 2.02 text-only book is a *folder* of plain-XML files that DAISY readers
and hardware players (Victor Reader Stream, Plextalk, APH units, Book Wizard
Producer, and so on) can open and read with their own text-to-speech. The folder
contains three files for a single-document export:

- ``ncc.html`` -- the Navigation Control Center: book metadata plus a flat list
  of heading links that drive a player's heading navigation.
- ``content.html`` -- an XHTML document holding the actual text, with an ``id``
  on every readable element.
- ``book.smil`` -- a SMIL 1.0 time container whose ``<par>`` elements point at
  the content fragments in reading order. Text-only books carry no audio, so the
  durations are all zero.

QUILL's editor keeps its canonical text as Markdown-style markup. This module
turns that markup into the structure above. It is wx-free so it can live in
``quill/io`` and be unit-tested without a display. :func:`write_daisy_textonly`
is the single entry point the UI calls.
"""

from __future__ import annotations

import html
import re
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from quill.io.export import markdown_to_plain_text

__all__ = [
    "write_daisy_textonly",
    "NCC_FILENAME",
    "CONTENT_FILENAME",
    "SMIL_FILENAME",
]

NCC_FILENAME = "ncc.html"
CONTENT_FILENAME = "content.html"
SMIL_FILENAME = "book.smil"

_GENERATOR = "QUILL"

_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")

_XHTML_DOCTYPE = (
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\n'
    ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
)
_SMIL_DOCTYPE = (
    '<!DOCTYPE smil PUBLIC "-//W3C//DTD SMIL 1.0//EN"\n "http://www.w3.org/TR/REC-smil/SMIL10.dtd">'
)


@dataclass(frozen=True, slots=True)
class _Block:
    """One readable element of the book: a heading or a paragraph."""

    kind: str  # "heading" or "p"
    level: int  # 1-6 for headings, 0 for paragraphs
    text: str


def _parse_blocks(text: str) -> list[_Block]:
    """Split QUILL Markdown-style markup into headings and paragraphs.

    Headings are recognised by their ``#`` prefix and kept as single blocks.
    Runs of consecutive non-blank lines become one paragraph block (joined with
    spaces). Fenced code is emitted verbatim, one paragraph per line, so a player
    reads each line on its own. Inline markup is stripped from the visible text.
    """
    blocks: list[_Block] = []
    para_lines: list[str] = []
    in_fence = False

    def flush_paragraph() -> None:
        nonlocal para_lines
        if para_lines:
            joined = " ".join(line.strip() for line in para_lines).strip()
            cleaned = markdown_to_plain_text(joined).strip()
            if cleaned:
                blocks.append(_Block("p", 0, cleaned))
        para_lines = []

    for raw in text.splitlines():
        if _FENCE_RE.match(raw):
            flush_paragraph()
            in_fence = not in_fence
            continue
        if in_fence:
            if raw.strip():
                blocks.append(_Block("p", 0, raw.rstrip()))
            continue
        heading = _HEADING_RE.match(raw)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            title = markdown_to_plain_text(heading.group(2)).strip()
            blocks.append(_Block("heading", level, title or "Untitled"))
            continue
        if not raw.strip():
            flush_paragraph()
            continue
        para_lines.append(raw)
    flush_paragraph()
    return blocks


def _ensure_top_heading(blocks: list[_Block], title: str) -> list[_Block]:
    """Guarantee the book opens with an h1 so player navigation is well-formed.

    DAISY readers expect the first navigable element to be a level-1 heading. If
    the document has no headings, or its first heading is deeper than h1, we
    prepend a synthetic h1 carrying the book title.
    """
    first_heading = next((b for b in blocks if b.kind == "heading"), None)
    if first_heading is not None and first_heading.level == 1:
        return blocks
    return [_Block("heading", 1, title)] + blocks


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _render_content(blocks: list[_Block], ids: list[str], title: str) -> str:
    """Render the XHTML content document holding the book's text."""
    body_lines: list[str] = []
    for block, elem_id in zip(blocks, ids, strict=True):
        if block.kind == "heading":
            tag = f"h{block.level}"
            body_lines.append(f'<{tag} id="{elem_id}">{_escape(block.text)}</{tag}>')
        else:
            body_lines.append(f'<p id="{elem_id}">{_escape(block.text)}</p>')
    body = "\n".join(body_lines)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f"{_XHTML_DOCTYPE}\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n'
        "<head>\n"
        f"<title>{_escape(title)}</title>\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
        "</head>\n"
        f"<body>\n{body}\n</body>\n"
        "</html>\n"
    )


def _render_smil(blocks: list[_Block], ids: list[str], par_ids: list[str], title: str) -> str:
    """Render the SMIL 1.0 reading-order container (text-only, zero duration)."""
    par_lines: list[str] = []
    for elem_id, par_id in zip(ids, par_ids, strict=True):
        par_lines.append(
            f'<par id="{par_id}" endsync="last">\n'
            f'<text id="tx_{par_id}" src="{CONTENT_FILENAME}#{elem_id}" />\n'
            "</par>"
        )
    pars = "\n".join(par_lines)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f"{_SMIL_DOCTYPE}\n"
        "<smil>\n"
        "<head>\n"
        '<meta name="dc:format" content="Daisy 2.02" />\n'
        f'<meta name="dc:title" content="{_escape(title)}" />\n'
        f'<meta name="ncc:generator" content="{_GENERATOR}" />\n'
        '<meta name="ncc:timeInThisSmil" content="00:00:00" />\n'
        "<layout>\n"
        '<region id="txtView" />\n'
        "</layout>\n"
        "</head>\n"
        "<body>\n"
        '<seq id="root_seq" dur="0.00s">\n'
        f"{pars}\n"
        "</seq>\n"
        "</body>\n"
        "</smil>\n"
    )


def _render_ncc(
    blocks: list[_Block],
    par_ids: list[str],
    title: str,
    author: str,
    identifier: str,
    toc_items: int,
    depth: int,
) -> str:
    """Render the Navigation Control Center with metadata and heading links."""
    nav_lines: list[str] = []
    nav_index = 0
    for block, par_id in zip(blocks, par_ids, strict=True):
        if block.kind != "heading":
            continue
        nav_index += 1
        tag = f"h{block.level}"
        nav_lines.append(
            f'<{tag} id="ncc_{nav_index}" class="section">'
            f'<a href="{SMIL_FILENAME}#{par_id}">{_escape(block.text)}</a>'
            f"</{tag}>"
        )
    nav = "\n".join(nav_lines)
    creator_meta = (
        f'<meta name="dc:creator" content="{_escape(author)}" />\n' if author.strip() else ""
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f"{_XHTML_DOCTYPE}\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n'
        "<head>\n"
        f"<title>{_escape(title)}</title>\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
        f'<meta name="dc:title" content="{_escape(title)}" />\n'
        f"{creator_meta}"
        f'<meta name="dc:identifier" content="{_escape(identifier)}" />\n'
        '<meta name="dc:format" content="Daisy 2.02" />\n'
        f'<meta name="dc:date" content="{date.today().isoformat()}" scheme="yyyy-mm-dd" />\n'
        '<meta name="dc:language" content="en" />\n'
        '<meta name="ncc:charset" content="utf-8" />\n'
        '<meta name="ncc:pageNormal" content="0" />\n'
        '<meta name="ncc:pageFront" content="0" />\n'
        '<meta name="ncc:pageSpecial" content="0" />\n'
        f'<meta name="ncc:tocItems" content="{toc_items}" />\n'
        '<meta name="ncc:totalTime" content="00:00:00" />\n'
        '<meta name="ncc:multimediaType" content="textNCX" />\n'
        f'<meta name="ncc:depth" content="{depth}" />\n'
        '<meta name="ncc:files" content="3" />\n'
        f'<meta name="ncc:generator" content="{_GENERATOR}" />\n'
        "</head>\n"
        f"<body>\n{nav}\n</body>\n"
        "</html>\n"
    )


def write_daisy_textonly(
    text: str,
    out_dir: Path,
    *,
    title: str,
    author: str = "",
    identifier: str | None = None,
) -> Path:
    """Write ``text`` as a DAISY 2.02 text-only talking book in ``out_dir``.

    The folder is created if needed and the three book files (``ncc.html``,
    ``content.html``, ``book.smil``) are written into it. ``title`` names the book
    and seeds a synthetic top heading when the document has none. ``identifier``
    defaults to a fresh UUID URN. Returns ``out_dir``.
    """
    book_title = title.strip() or "Untitled"
    blocks = _ensure_top_heading(_parse_blocks(text), book_title)
    ids = [f"e{index:04d}" for index in range(1, len(blocks) + 1)]
    par_ids = [f"p{index:04d}" for index in range(1, len(blocks) + 1)]
    toc_items = sum(1 for block in blocks if block.kind == "heading")
    depth = max((block.level for block in blocks if block.kind == "heading"), default=1)
    book_id = identifier or f"urn:uuid:{uuid.uuid4()}"

    out_dir.mkdir(parents=True, exist_ok=True)
    content = _render_content(blocks, ids, book_title)
    smil = _render_smil(blocks, ids, par_ids, book_title)
    ncc = _render_ncc(blocks, par_ids, book_title, author, book_id, toc_items, depth)

    (out_dir / CONTENT_FILENAME).write_text(content, encoding="utf-8", newline="\n")
    (out_dir / SMIL_FILENAME).write_text(smil, encoding="utf-8", newline="\n")
    (out_dir / NCC_FILENAME).write_text(ncc, encoding="utf-8", newline="\n")
    return out_dir
