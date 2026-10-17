"""Presentations as readable text, standard library only (.pptx, .odp).

Part of QUILL's own Office readers (:mod:`quill.io.office_text`); moved here
from ``quill.io.structured`` (2026-10-16) so File > Open and Import / Convert
Document read a deck the same way.

Every slide starts with a level-1 heading, ``# Slide 3: Quarterly results``
(``# Slide 3`` when the slide has no title), so heading navigation moves one
slide at a time and the slide number is heard before its title. Under it come
the body text as a bulleted list indented by outline level, any tables as
``## Tables``, the alternative text of pictures as ``[Image: ...]``, and the
speaker notes as ``## Notes``.

Slides are read in the order the presentation shows them
(``ppt/presentation.xml``), not in the order their files happen to be
numbered: a deck whose slides were reordered in PowerPoint keeps the new
order. Hidden slides are included and say so, because a hidden slide's text
is still the author's text.

Not kept: charts, SmartArt graphics, animations, and character formatting.

wx-free; strict-typed.
"""

from __future__ import annotations

import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import Element

from quill.core.safe_archive import open_zip
from quill.core.safe_xml import fromstring as safe_xml_fromstring
from quill.io.office_sheets import escape_cell, markdown_table

__all__ = ["PPTX_NAMESPACES", "SlideText", "read_odp_text", "read_pptx_text", "slide_table_blocks"]

PPTX_NAMESPACES = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}
_NS = PPTX_NAMESPACES
_TITLE_TYPES = {"title", "ctrTitle"}
_ODF_DRAW = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
_ODF_PRESENTATION = "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0"
_ODF_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_ODF_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"


@dataclass(frozen=True, slots=True)
class SlideText:
    """A deck rendered as text, and how many slides it had."""

    text: str
    engine: str
    slides: int


def _slide_heading(number: int, title: str, *, hidden: bool = False) -> str:
    heading = f"# Slide {number}: {title}" if title else f"# Slide {number}"
    return heading + (" (hidden slide)" if hidden else "")


# ----------------------------------------------------------------- .pptx


def read_pptx_text(path: Path) -> SlideText:
    """Read a ``.pptx`` deck in presentation order. ``ValueError`` if it has no slides."""
    with open_zip(path) as archive:
        slide_paths = _slide_order(archive)
        if not slide_paths:
            raise ValueError(f"{path.name} has no slides QUILL could read.")
        lines: list[str] = []
        for number, slide_path in enumerate(slide_paths, start=1):
            root = safe_xml_fromstring(archive.read(slide_path))
            lines.append(_slide_heading(number, _slide_title(root), hidden=root.get("show") == "0"))
            lines.append("")
            lines.extend(_slide_body_lines(root) or ["(This slide has no body text.)"])
            _append_sections(
                lines, slide_table_blocks(root), _slide_notes_lines(archive, slide_path)
            )
    return SlideText("\n".join(lines).rstrip() + "\n", "slide-xml", len(slide_paths))


def _append_sections(lines: list[str], tables: list[list[str]], notes: list[str]) -> None:
    """A slide's tables and speaker notes, each under its own heading."""
    if tables:
        lines.extend(["", "## Tables"])
        for table in tables:
            lines.extend(["", *table])
    if notes:
        lines.extend(["", "## Notes", "", *notes])
    lines.append("")


def _number_key(path: str) -> tuple[int, str]:
    match = re.search(r"(\d+)\.xml$", path)
    return (int(match.group(1)) if match else 0, path)


def _relationships(archive: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    """``rId -> (type, resolved target)`` for one part, ``{}`` if it has none."""
    folder, name = posixpath.split(part)
    rels_path = posixpath.join(folder, "_rels", f"{name}.rels")
    if rels_path not in archive.namelist():
        return {}
    try:
        root = safe_xml_fromstring(archive.read(rels_path))
    except ET.ParseError:
        return {}
    found: dict[str, tuple[str, str]] = {}
    for relation in root.findall("pr:Relationship", _NS):
        target = relation.get("Target") or ""
        resolved = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join(folder, target))
        )
        found[relation.get("Id") or ""] = (relation.get("Type") or "", resolved)
    return found


def _slide_order(archive: zipfile.ZipFile) -> list[str]:
    names = set(archive.namelist())
    ordered: list[str] = []
    if "ppt/presentation.xml" in names:
        try:
            root = safe_xml_fromstring(archive.read("ppt/presentation.xml"))
        except ET.ParseError:
            root = None
        rels = _relationships(archive, "ppt/presentation.xml")
        if root is not None:
            for slide_id in root.iterfind("p:sldIdLst/p:sldId", _NS):
                target = rels.get(slide_id.get(f"{{{_NS['r']}}}id") or "", ("", ""))[1]
                if target in names:
                    ordered.append(target)
    if ordered:
        return ordered
    return sorted(
        (n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml")),
        key=_number_key,
    )


def _paragraph_text(paragraph: Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{{{_NS['a']}}}t" and node.text:
            parts.append(node.text)
        elif node.tag == f"{{{_NS['a']}}}br":
            parts.append(" ")
    return " ".join("".join(parts).split())


def _is_title(shape: Element) -> bool:
    placeholder = shape.find(".//p:nvSpPr/p:nvPr/p:ph", _NS)
    return placeholder is not None and (placeholder.get("type") or "") in _TITLE_TYPES


def _slide_title(root: Element) -> str:
    for shape in root.iterfind(".//p:sp", _NS):
        if _is_title(shape):
            for paragraph in shape.iterfind(".//a:p", _NS):
                text = _paragraph_text(paragraph)
                if text:
                    return text
    return ""


def _slide_body_lines(root: Element) -> list[str]:
    lines: list[str] = []
    tree = root.find(".//p:spTree", _NS)
    for shape in tree.iter() if tree is not None else iter(()):
        if shape.tag == f"{{{_NS['p']}}}sp" and not _is_title(shape):
            for paragraph in shape.iterfind(".//p:txBody/a:p", _NS):
                text = _paragraph_text(paragraph)
                if not text:
                    continue
                props = paragraph.find("a:pPr", _NS)
                raw = props.get("lvl") if props is not None else None
                level = int(raw) if raw and raw.isdigit() else 0
                lines.append(f"{'  ' * level}- {text}")
        elif shape.tag == f"{{{_NS['p']}}}pic":
            described = shape.find("p:nvPicPr/p:cNvPr", _NS)
            description = (described.get("descr") or "").strip() if described is not None else ""
            if description:
                lines.append(f"- [Image: {' '.join(description.split())}]")
    return lines


def slide_table_blocks(root: Element) -> list[list[str]]:
    """Every table on a slide as Markdown table lines (first row is the header)."""
    tables: list[list[str]] = []
    for table in root.iterfind(".//a:tbl", _NS):
        rows = [
            [
                escape_cell(" ".join(_paragraph_text(p) for p in cell.iterfind(".//a:p", _NS)))
                for cell in row.iterfind("a:tc", _NS)
            ]
            for row in table.iterfind("a:tr", _NS)
        ]
        block = markdown_table(rows)
        if block:
            tables.append(block)
    return tables


def _slide_notes_lines(archive: zipfile.ZipFile, slide_path: str) -> list[str]:
    for kind, target in _relationships(archive, slide_path).values():
        if not kind.endswith("/notesSlide") or target not in archive.namelist():
            continue
        try:
            root = safe_xml_fromstring(archive.read(target))
        except ET.ParseError:
            return []
        lines: list[str] = []
        for shape in root.iterfind(".//p:sp", _NS):
            placeholder = shape.find(".//p:nvSpPr/p:nvPr/p:ph", _NS)
            # The notes page also carries the slide image and its number;
            # only the body placeholder is what the speaker wrote.
            if placeholder is not None and placeholder.get("type") in {"sldImg", "sldNum"}:
                continue
            lines.extend(
                text for p in shape.iterfind(".//a:p", _NS) if (text := _paragraph_text(p))
            )
        return lines
    return []


# ----------------------------------------------------------------- .odp


def read_odp_text(path: Path) -> SlideText:
    """Read an OpenDocument presentation (``.odp``) slide by slide."""
    with open_zip(path) as archive:
        root = safe_xml_fromstring(archive.read("content.xml"))
    lines: list[str] = []
    pages = list(root.iter(f"{{{_ODF_DRAW}}}page"))
    if not pages:
        raise ValueError(f"{path.name} has no slides QUILL could read.")
    for number, page in enumerate(pages, start=1):
        title = ""
        body: list[str] = []
        notes: list[str] = []
        tables: list[list[str]] = []
        for frame in page.findall(f"{{{_ODF_DRAW}}}frame"):
            kind = frame.get(f"{{{_ODF_PRESENTATION}}}class") or ""
            texts = [
                " ".join("".join(p.itertext()).split())
                for p in frame.iter()
                if p.tag in (f"{{{_ODF_TEXT}}}p", f"{{{_ODF_TEXT}}}h")
            ]
            texts = [t for t in texts if t]
            if kind == "title" and not title and texts:
                title = texts[0]
                continue
            frame_tables = [
                block
                for table in frame.iter(f"{{{_ODF_TABLE}}}table")
                if (
                    block := markdown_table([
                        [escape_cell(" ".join(cell.itertext())) for cell in row]
                        for row in table.iter(f"{{{_ODF_TABLE}}}table-row")
                    ])
                )
            ]
            tables.extend(frame_tables)
            if not frame_tables:
                body.extend(f"- {t}" for t in texts)
        for note in page.iter(f"{{{_ODF_PRESENTATION}}}notes"):
            notes.extend(
                t
                for p in note.iter(f"{{{_ODF_TEXT}}}p")
                if (t := " ".join("".join(p.itertext()).split()))
            )
        lines.extend([_slide_heading(number, title), ""])
        lines.extend(body or ["(This slide has no body text.)"])
        _append_sections(lines, tables, notes)
    return SlideText("\n".join(lines).rstrip() + "\n", "odf-xml", len(pages))
