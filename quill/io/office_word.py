"""Word-processing documents as Markdown-shaped text, standard library only.

Part of QUILL's own Office readers (:mod:`quill.io.office_text`). These two
readers need nothing outside Python itself -- no MarkItDown, no python-docx,
no lxml -- because every one of those can be missing from a shipped build:
the shared QuillVille runtime excludes ``lxml`` (so python-docx cannot import
there) and ``onnxruntime`` (so MarkItDown cannot import there either).

* :func:`read_docx_xml` walks ``word/document.xml`` in body order. Headings
  come from the paragraph style (looked up by name in ``styles.xml``, so a
  renamed or localised style id still reads as "Heading 2") or from a direct
  outline level; list paragraphs become ``-`` or ``1.`` items, indented by
  their list level and told apart by ``numbering.xml``; tables become
  Markdown tables; a Shift+Enter line break becomes a Markdown hard break; an
  image's alternative text is kept as ``[Image: ...]``. Deleted tracked
  changes and field codes are left out because they are not the text a
  reader of the document sees.
* :func:`read_odt_xml` does the same for an OpenDocument text file
  (``.odt``): ``text:h`` with its outline level, nested ``text:list``,
  ``table:table``, and the ``text:s``/``text:tab``/``text:line-break``
  spacing elements.

Not kept, on purpose or by limit: headers, footers, footnotes, comments,
text boxes floating outside the body, and character formatting (bold and
italic). The text is the document's own; nothing is added above it.

wx-free; strict-typed. Both functions raise ``KeyError`` (a part is missing),
``zipfile.BadZipFile`` (not a package) or ``xml.etree.ElementTree.ParseError``
(damaged XML); :mod:`quill.io.office_text` turns those into one sentence.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.etree.ElementTree import Element

from quill.core.markdown_breaks import hard_break_suffix
from quill.core.safe_archive import open_zip
from quill.core.safe_xml import fromstring as safe_xml_fromstring
from quill.io.office_sheets import escape_cell, markdown_table

__all__ = ["read_docx_xml", "read_odt_xml"]

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_ODF_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_ODF_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
_ODF_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"

#: The same hard-break spelling the python-docx reader writes (quill.io.docx_text).
_BREAK = hard_break_suffix("backslash")
_HEADING = re.compile(r"^heading\s*(\d)$", re.IGNORECASE)


def _w(name: str) -> str:
    return f"{{{_W}}}{name}"


def _join_blocks(blocks: list[str]) -> str:
    """Blocks separated by a blank line, except consecutive list items."""
    lines: list[str] = []
    previous_list = False
    for block in blocks:
        is_list = block.lstrip().startswith(("- ", "1. "))
        if lines and not (is_list and previous_list):
            lines.append("")
        lines.append(block)
        previous_list = is_list
    return "\n".join(lines).strip("\n") + "\n" if lines else ""


def _with_breaks(text: str) -> str:
    pieces = [piece.rstrip() for piece in text.split("\n")]
    return (_BREAK + "\n").join(piece for piece in pieces if piece.strip())


# ----------------------------------------------------------------- .docx


class _WordContext:
    """What a paragraph needs from the rest of the package to be read right."""

    def __init__(self, styles: dict[str, str], ordered: dict[tuple[str, int], bool]) -> None:
        self.styles = styles
        self.ordered = ordered


def read_docx_xml(path: Path) -> str:
    """Render a ``.docx``/``.docm`` body as Markdown-shaped text, or ``""``."""
    with open_zip(path) as archive:
        names = set(archive.namelist())
        body_xml = archive.read("word/document.xml")
        styles = (
            _style_names(archive.read("word/styles.xml")) if ("word/styles.xml" in names) else {}
        )
        ordered = (
            _ordered_lists(archive.read("word/numbering.xml"))
            if ("word/numbering.xml" in names)
            else {}
        )
    root = safe_xml_fromstring(body_xml)
    body = root.find(_w("body"))
    if body is None:
        return ""
    return _join_blocks(_body_blocks(body, _WordContext(styles, ordered)))


def _style_names(data: bytes) -> dict[str, str]:
    root = safe_xml_fromstring(data)
    names: dict[str, str] = {}
    for style in root.findall(_w("style")):
        style_id = style.get(_w("styleId")) or ""
        name = style.find(_w("name"))
        names[style_id] = ((name.get(_w("val")) if name is not None else None) or style_id).lower()
    return names


def _ordered_lists(data: bytes) -> dict[tuple[str, int], bool]:
    """``(numId, level) -> True`` for a numbered level, ``False`` for bullets."""
    root = safe_xml_fromstring(data)
    abstract: dict[str, dict[int, bool]] = {}
    for item in root.findall(_w("abstractNum")):
        levels: dict[int, bool] = {}
        for level in item.findall(_w("lvl")):
            fmt = level.find(_w("numFmt"))
            value = (fmt.get(_w("val")) if fmt is not None else None) or "bullet"
            levels[int(level.get(_w("ilvl")) or 0)] = value not in {"bullet", "none"}
        abstract[item.get(_w("abstractNumId")) or ""] = levels
    found: dict[tuple[str, int], bool] = {}
    for num in root.findall(_w("num")):
        link = num.find(_w("abstractNumId"))
        levels = abstract.get((link.get(_w("val")) if link is not None else None) or "", {})
        for level_number, ordered in levels.items():
            found[(num.get(_w("numId")) or "", level_number)] = ordered
    return found


def _body_blocks(container: Element, context: _WordContext) -> list[str]:
    blocks: list[str] = []
    for child in container:
        if child.tag == _w("p"):
            rendered = _paragraph(child, context)
            if rendered:
                blocks.append(rendered)
        elif child.tag == _w("tbl"):
            table = markdown_table(_table_rows(child))
            if table:
                blocks.append("\n".join(table))
        elif child.tag == _w("sdt"):
            content = child.find(_w("sdtContent"))
            if content is not None:
                blocks.extend(_body_blocks(content, context))
    return blocks


def _run_text(paragraph: Element) -> str:
    parts: list[str] = []
    _collect_runs(paragraph, parts)
    return "".join(parts)


def _collect_runs(node: Element, parts: list[str]) -> None:
    for child in node:
        tag = child.tag
        if tag == f"{{{_MC}}}Fallback":
            # A drawing is stored twice, modern and legacy, inside one
            # mc:AlternateContent; reading both would say its text twice.
            continue
        if tag == _w("t") and child.text:
            parts.append(child.text)
        elif tag == _w("tab"):
            parts.append("\t")
        elif tag in (_w("br"), _w("cr")) and child.get(_w("type")) not in ("page", "column"):
            parts.append("\n")
        elif tag == f"{{{_WP}}}docPr":
            description = (child.get("descr") or child.get("title") or "").strip()
            if description:
                parts.append(f" [Image: {' '.join(description.split())}] ")
        _collect_runs(child, parts)


def _paragraph(paragraph: Element, context: _WordContext) -> str:
    text = _with_breaks(_run_text(paragraph).strip())
    if not text:
        return ""
    properties = paragraph.find(_w("pPr"))
    style = ""
    outline = -1
    numbering: tuple[str, int] | None = None
    if properties is not None:
        style_node = properties.find(_w("pStyle"))
        style_id = (style_node.get(_w("val")) if style_node is not None else None) or ""
        style = context.styles.get(style_id, style_id.lower())
        level_node = properties.find(_w("outlineLvl"))
        if level_node is not None and (level_node.get(_w("val")) or "").isdigit():
            outline = int(level_node.get(_w("val")) or "0")
        num = properties.find(_w("numPr"))
        if num is not None:
            num_id = num.find(_w("numId"))
            ilvl = num.find(_w("ilvl"))
            numbering = (
                (num_id.get(_w("val")) if num_id is not None else None) or "",
                int((ilvl.get(_w("val")) if ilvl is not None else None) or 0),
            )
    heading = _HEADING.match(style)
    if heading:
        return f"{'#' * min(int(heading.group(1)), 6)} {text}"
    if style == "title":
        return f"# {text}"
    if style == "subtitle":
        return f"## {text}"
    if 0 <= outline < 6:
        return f"{'#' * (outline + 1)} {text}"
    if numbering is not None and numbering[0] != "0":
        ordered = context.ordered.get(numbering, False)
        return f"{'  ' * numbering[1]}{'1.' if ordered else '-'} {text}"
    if style.startswith("list number"):
        return f"1. {text}"
    if style.startswith(("list bullet", "list paragraph")):
        return f"- {text}"
    return text


def _table_rows(table: Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall(_w("tr")):
        cells = []
        for cell in row.findall(_w("tc")):
            paragraphs = [_run_text(p).strip() for p in cell.iter(_w("p"))]
            cells.append(escape_cell(" ".join(p for p in paragraphs if p)))
        rows.append(cells)
    return rows


# ----------------------------------------------------------------- .odt


def _t(name: str) -> str:
    return f"{{{_ODF_TEXT}}}{name}"


def read_odt_xml(path: Path) -> str:
    """Render an OpenDocument text file (``.odt``) as Markdown-shaped text."""
    with open_zip(path) as archive:
        raw = archive.read("content.xml")
    try:
        root = safe_xml_fromstring(raw)
    except ET.ParseError:
        # A content.xml a strict parser refuses (an undeclared prefix, a stray
        # ampersand) still has its words; keep them rather than nothing.
        words = " ".join(
            html.unescape(re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "ignore"))).split()
        )
        return f"{words}\n" if words else ""
    blocks: list[str] = []
    for text_root in root.iter(f"{{{_ODF_OFFICE}}}text"):
        blocks.extend(_odt_blocks(text_root, depth=0))
    return _join_blocks(blocks)


def _odt_text(node: Element) -> str:
    parts: list[str] = [node.text or ""]
    for child in node:
        tag = child.tag
        if tag == _t("s"):
            parts.append(" " * max(1, int(child.get(_t("c")) or "1")))
        elif tag == _t("tab"):
            parts.append("\t")
        elif tag == _t("line-break"):
            parts.append("\n")
        elif tag in (_t("note"), _t("tracked-changes")):
            pass  # footnotes and change records are not body text
        else:
            parts.append(_odt_text(child))
        parts.append(child.tail or "")
    return "".join(parts)


def _odt_blocks(container: Element, *, depth: int) -> list[str]:
    blocks: list[str] = []
    for child in container:
        tag = child.tag
        if tag == _t("h"):
            text = _with_breaks(_odt_text(child).strip())
            level = int(child.get(_t("outline-level")) or "1")
            if text:
                blocks.append(f"{'#' * max(1, min(level, 6))} {text}")
        elif tag == _t("p"):
            text = _with_breaks(_odt_text(child).strip())
            if text:
                blocks.append(text)
        elif tag == _t("list"):
            for item in child:
                for inner in _odt_blocks(item, depth=depth + 1):
                    nested = inner.lstrip().startswith(("- ", "1. "))
                    blocks.append(inner if nested else f"{'  ' * depth}- {inner}")
        elif tag == f"{{{_ODF_TABLE}}}table":
            table = markdown_table(_odt_table_rows(child))
            if table:
                blocks.append("\n".join(table))
        elif tag == _t("section"):
            blocks.extend(_odt_blocks(child, depth=depth))
    return blocks


def _odt_table_rows(table: Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.iter(f"{{{_ODF_TABLE}}}table-row"):
        cells = []
        for cell in row:
            if cell.tag.endswith("}table-cell") or cell.tag.endswith("}covered-table-cell"):
                text = " ".join(_odt_text(p).strip() for p in cell.iter(_t("p")))
                cells.append(escape_cell(text))
        rows.append(cells)
    return rows
