from __future__ import annotations

import csv
import io
import json
import sqlite3
import tomllib
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from quill.core.document import Document
from quill.core.epub import load_epub_book, render_epub_book
from quill.core.pdf_ocr_install import PACK_ASSISTED_SUFFIXES, extraction_pack_missing
from quill.core.pdf_open import read_pdf_for_open
from quill.core.safe_archive import check_zip_safety
from quill.core.safe_xml import fromstring as safe_xml_fromstring
from quill.io.markitdown_bridge import convert_with_markitdown
from quill.io.office_text import OfficeReadError, read_office_text_preferring_markitdown
from quill.io.pages import read_pages_document
from quill.io.pdf import extract_pdf_outline_entries, extract_pdf_text
from quill.io.rtf import read_rtf_document
from quill.io.text import read_text_document

#: The Office formats File > Open reads through quill.io.office_text (Word's
#: own branch above adds the Pandoc preference first). Spreadsheet reads stay
#: bounded (PERF-11): see quill.io.office_sheets.MAX_ROWS.
_OFFICE_OPEN_SUFFIXES = frozenset({".doc", ".odt", ".pptx", ".ppt", ".xlsx", ".xls"})


def read_structured_document(
    path: Path,
    encoding: str = "utf-8",
    *,
    docx_engine: str = "auto",
    pdf_password: str | None = None,
) -> Document:
    suffix = path.suffix.lower()
    if suffix in {".sqlite", ".db"}:
        text = _format_sqlite(path)
        metadata = {"source_kind": "sqlite", "engine": "sqlite", "quality_score": 100}
    elif suffix in {".docx", ".docm"}:
        # .docm is a macro-enabled Word file: byte-for-byte the same OOXML
        # container as .docx, so the same reader chain handles it. QUILL reads
        # its text (it never executes macros); saving routes through Save As
        # like any other imported binary.
        _guard_office_zip(path)
        document = _read_docx_with_pandoc(path) if docx_engine == "pandoc" else None
        if document is not None:
            return document
        text, metadata = _read_office(path)
    elif suffix in _OFFICE_OPEN_SUFFIXES:
        # 2026-10-16 (todo P1 4b): every Office format reads through
        # quill.io.office_text -- MarkItDown when it works, QUILL's own reader
        # whenever it does not, which in a shipped build is always (magika
        # needs onnxruntime, which the shared runtime excludes).
        _guard_office_zip(path)
        text, metadata = _read_office(path)
    elif suffix == ".epub":
        text = render_epub_book(load_epub_book(path))
        metadata = {"source_kind": "epub", "engine": "epub", "quality_score": 100}
    elif suffix == ".pdf":
        text, metadata = _format_pdf(path, password=pdf_password)
    elif suffix == ".pages":
        doc = read_pages_document(path)
        text = doc.text
        metadata = doc.source_metadata
    elif suffix == ".rtf":
        return read_rtf_document(path)
    else:
        # #1278: read_text_document strips a UTF-8 BOM (remembering utf-8-sig so a
        # save re-adds it), keeps the original line ending, and degrades to
        # cp1252/latin-1. The old path.read_text left the BOM in the text, so a
        # BOM-prefixed .json/.xml/.toml failed to parse (and crashed before #1228).
        loaded = read_text_document(path, encoding=encoding)
        text, metadata = _format_structured_text(loaded.text, suffix)
        return Document(
            text=text,
            path=path,
            modified=False,
            encoding=loaded.encoding,
            line_ending=loaded.line_ending,
            source_metadata=metadata,
        )

    # #1279: point at the one-click download only where it can help. Since
    # 2026-10-16 QUILL's own Office readers keep headings, lists, tables, sheets
    # and slides, so a good Office read is not nagged about; what is left is a
    # PDF (MarkItDown may read some pages better) and an .xls nothing else could
    # read (MarkItDown reads that format; QUILL's own readers do not).
    unread_xls = suffix == ".xls" and metadata.get("engine") == "unavailable"
    if (
        suffix in PACK_ASSISTED_SUFFIXES
        and (suffix == ".pdf" or unread_xls)
        and extraction_pack_missing()
    ):
        metadata["extraction_pack_missing"] = True
    line_ending = "\r\n" if "\r\n" in text else "\n"
    return Document(
        text=text,
        path=path,
        modified=False,
        encoding=encoding,
        line_ending=line_ending,
        source_metadata=metadata,
    )


def _guard_office_zip(path: Path) -> None:
    """Reject a decompression bomb before a primary OOXML reader expands it.

    The office formats (.docx/.docm/.pptx/.xlsx) are ZIP containers, and the
    preferred readers (MarkItDown, openpyxl, python-docx) all expand entries
    without a size guard of their own. Running :func:`check_zip_safety` up front
    refuses a crafted archive whose declared expansion exceeds the safe limits
    before any entry is read, raising
    :class:`~quill.core.safe_archive.DecompressionBombError`. A non-ZIP file (a
    legacy .doc/.xls, or a corrupt upload) is left for the downstream reader to
    diagnose -- only a genuine bomb is refused here.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            check_zip_safety(archive)
    except (zipfile.BadZipFile, OSError):
        return


def _call_markitdown(path: Path) -> str:
    # Looked up at call time so a test can stand in for MarkItDown here.
    return convert_with_markitdown(path)


def _read_office(path: Path) -> tuple[str, dict[str, object]]:
    """Any Office format, through :mod:`quill.io.office_text`.

    MarkItDown when it works; QUILL's own reader on any MarkItDown failure.
    A file no reader can open (damaged, password-protected, or a legacy
    .doc/.xls/.ppt with no LibreOffice) opens as one parenthesised paragraph
    saying why and what to do, as every other unreadable format here does.
    """
    try:
        found = read_office_text_preferring_markitdown(path, markitdown=_call_markitdown)
    except OfficeReadError as exc:
        return f"({exc.sentence})\n", {
            "source_kind": path.suffix.lower().lstrip("."),
            "engine": "unavailable",
            "quality_score": 0,
        }
    return found.text, found.metadata()


def _read_docx_with_pandoc(path: Path) -> Document | None:
    """The ``docx_read_engine = pandoc`` preference: Pandoc's Markdown, or ``None``.

    Pandoc keeps footnotes and complex tables better. When it is missing or
    fails, ``None`` sends the caller to the default chain, so an engine
    preference never fails an open.
    """
    try:
        from quill.io import pandoc as pandoc_mod

        result = pandoc_mod.convert_document_with_pandoc(path, "markdown", from_format="docx")
    except Exception:  # noqa: BLE001 - degrade to the default chain
        return None
    text = result.text
    if not text.strip():
        return None
    return Document(
        text=text.rstrip() + "\n",
        path=path,
        modified=False,
        encoding="utf-8",
        line_ending="\n",
        source_metadata={
            "source_kind": path.suffix.lower().lstrip("."),
            "engine": "pandoc",
            "quality_score": 90,
            "fallback_engine": "docx",
        },
    )


def _format_pdf(path: Path, *, password: str | None = None) -> tuple[str, dict[str, object]]:
    # The one PDF read both editors share (quill.core.pdf_open): each page's
    # most readable reading, form feeds between pages, the outline with its
    # levels, and per-page provenance. MarkItDown is no longer a fallback here
    # with an automatic score of 85: the reader offers it the pages itself,
    # scores them by the same rules and keeps page boundaries, so QUILL and
    # QUILL Lite read a PDF identically. The module's own names are passed as
    # the reader so a test that patches them here still reaches them.
    found = read_pdf_for_open(
        path, password=password, extract=extract_pdf_text, read_outline=extract_pdf_outline_entries
    )
    metadata = found.metadata()
    if "markitdown" in found.page_engines:
        metadata["markitdown_used"] = True
    return found.text, metadata


def _format_structured_text(raw_text: str, suffix: str) -> tuple[str, dict[str, object]]:
    """Pretty-print / validate a structured text file, falling back to raw on failure.

    A malformed structured file (invalid JSON, TOML, XML, CSV, or notebook) must never
    crash the open flow — the user asked to *see* the file, most often precisely because
    it is broken and they want to read or repair it. When the format-specific parser
    raises, we return the file's raw text unchanged with a ``structured_parse_error``
    note in the metadata instead of letting the exception propagate (#1228).
    """
    formatters: dict[str, tuple[str, str, object]] = {
        ".json": ("json", "json", lambda t: _format_json(t)),
        ".toml": ("toml", "toml", lambda t: _validate_toml(t)),
        ".xml": ("xml", "xml", lambda t: _format_xml(t)),
        ".csv": ("csv", "delimited", lambda t: _format_delimited(t, delimiter=",")),
        ".tsv": ("tsv", "delimited", lambda t: _format_delimited(t, delimiter="\t")),
        ".ipynb": ("ipynb", "notebook", lambda t: _format_notebook(t)),
    }
    entry = formatters.get(suffix)
    if entry is None:
        return raw_text, {"source_kind": "text", "engine": "plain text", "quality_score": 100}
    source_kind, engine, formatter = entry
    try:
        text = formatter(raw_text)  # type: ignore[operator]
    except (ValueError, SyntaxError, csv.Error) as exc:
        # ValueError covers json.JSONDecodeError and tomllib.TOMLDecodeError;
        # SyntaxError covers ElementTree's ParseError; csv.Error covers delimited parsing.
        return (
            raw_text,
            {
                "source_kind": "text",
                "engine": "plain text",
                "quality_score": 0,
                "structured_parse_error": f"{type(exc).__name__}: {exc}",
            },
        )
    return text, {"source_kind": source_kind, "engine": engine, "quality_score": 100}


def _format_json(text: str) -> str:
    payload = json.loads(text)
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _validate_toml(text: str) -> str:
    tomllib.loads(text)
    return text


def _format_xml(text: str) -> str:
    root = safe_xml_fromstring(text)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n"


def _format_delimited(text: str, delimiter: str) -> str:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
    for row in reader:
        writer.writerow(row)
    return output.getvalue()


def _format_notebook(text: str) -> str:
    payload = json.loads(text)
    cells = payload.get("cells", [])
    if not isinstance(cells, list):
        return "# Notebook\n\n(no cells)\n"
    lines = ["# Notebook", ""]
    for index, cell in enumerate(cells, start=1):
        if not isinstance(cell, dict):
            continue
        kind = str(cell.get("cell_type", "unknown"))
        source = cell.get("source", [])
        if isinstance(source, list):
            content = "".join(str(item) for item in source).strip()
        else:
            content = str(source).strip()
        lines.append(f"## Cell {index} ({kind})")
        lines.append(content or "(empty)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _format_sqlite(path: Path) -> str:
    lines = [f"# SQLite Database: {path.name}", ""]
    with sqlite3.connect(path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        table_names = [row[0] for row in cursor.fetchall()]
        if not table_names:
            lines.append("(no user tables)")
            return "\n".join(lines) + "\n"
        for table in table_names:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            lines.append(f"- {table}: {count} row(s)")
    lines.append("")
    return "\n".join(lines)
