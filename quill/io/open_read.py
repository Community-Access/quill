"""Document reading for the editor's open flow.

This module centralizes how a path is turned into a :class:`Document` when the
user opens a file. It is deliberately wx-free so the heavy office and PDF reads
can run on a worker thread (PERF-12) without touching the UI toolkit.

The single public entry point, :func:`read_open_document`, returns the loaded
document together with any parsed EPUB book so the caller can install both on the
UI thread.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.document import Document
from quill.io.text import read_text_document

# PERF-12: heavy office and PDF formats are parsed off the UI thread.
OFFICE_STREAM_SUFFIXES: frozenset[str] = frozenset({
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xlsx",
    ".xls",
    ".pdf",
    ".odt",
    ".rtf",
    ".epub",
    ".pages",
})

# Light structured formats are cheap enough to read on the UI thread.
LIGHT_STRUCTURED_SUFFIXES: frozenset[str] = frozenset({
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".ipynb",
    ".sqlite",
    ".db",
})

_CSV_SUFFIXES: frozenset[str] = frozenset({".csv", ".tsv"})

# Braille Mode (BR-004 / #226). The .brf / .brl / .pef / .ueb family is plain
# ASCII text (NABCC) with a strict byte-for-byte contract on save: form feeds
# are page breaks, trailing spaces count for layout, and line endings are
# preserved. Detection is by extension; see ``quill/core/brf_ascii.py`` for the
# character set, BOM handling, and the non-BRF-ASCII guard.
BRF_SUFFIXES: frozenset[str] = frozenset({".brf", ".brl", ".pef", ".ueb"})


def read_open_document(
    selected_path: Path,
    suffix: str,
    *,
    word_mode: str | None = None,
    csv_mode: str | None = None,
    docx_engine: str = "auto",
) -> tuple[Document, object]:
    """Read ``selected_path`` into a document for the open flow.

    Returns the loaded :class:`Document` and any parsed EPUB book (``None`` for
    non-EPUB inputs). ``word_mode`` and ``csv_mode`` carry UI choices that must be
    resolved before calling this function so it never needs the UI toolkit;
    ``docx_engine`` carries the ``docx_read_engine`` setting the same way.
    """
    if suffix in _CSV_SUFFIXES:
        loaded = read_text_document(selected_path)
        engine = "csv grid" if csv_mode == "grid" else "csv text"
        mode = "grid" if csv_mode == "grid" else "text"
        loaded.source_metadata = {
            "source_kind": suffix.lstrip("."),
            "engine": engine,
            "quality_score": 100,
            "csv_open_mode": mode,
        }
        return loaded, None

    if suffix in OFFICE_STREAM_SUFFIXES:
        from quill.io.structured import read_structured_document

        loaded = read_structured_document(selected_path, docx_engine=docx_engine)
        if word_mode is not None:
            loaded.source_metadata["word_open_mode"] = word_mode
        epub_book: object = None
        if suffix == ".epub":
            from quill.core.epub import load_epub_book

            epub_book = load_epub_book(selected_path)
        return loaded, epub_book

    if suffix in LIGHT_STRUCTURED_SUFFIXES:
        from quill.io.structured import read_structured_document

        return read_structured_document(selected_path), None

    if suffix in BRF_SUFFIXES:
        # Braille Mode: read raw bytes, strip a UTF-8 BOM if present, and
        # surface a non-BRF-ASCII warning in source_metadata so the UI can
        # announce it on open. The save path (quill.io.text.write_text_document
        # + the braille_sanitized_input guard added in #228) preserves form
        # feeds, trailing spaces, and line endings byte-for-byte. A
        # BRFDocument is built alongside the Document so downstream modules
        # (brf_page_map, braille_position, braille_status) can consume a
        # single, typed snapshot.
        from quill.core.brf_ascii import (
            find_non_brf_ascii_offsets,
            strip_bom,
        )
        from quill.core.brf_document import BRFDocument

        raw_bytes = selected_path.read_bytes()
        text, had_bom = strip_bom(raw_bytes)
        non_ascii = find_non_brf_ascii_offsets(text)
        brf_doc = BRFDocument.from_text_and_suffix(
            text,
            suffix.lstrip("."),
            had_bom=had_bom,
            non_ascii_offsets=non_ascii,
        )
        loaded = Document(
            text=text,
            path=selected_path,
            modified=False,
            encoding=brf_doc.encoding,
            line_ending=brf_doc.line_ending,
            source_metadata={
                "source_kind": "brf",
                "engine": "braille text",
                "quality_score": 100,
                "brf_suffix": brf_doc.suffix,
                "brf_had_bom": had_bom,
                "brf_non_ascii_offsets": non_ascii,
                "brf_non_ascii_count": len(non_ascii),
                "brf_form_feed_count": brf_doc.form_feed_count,
                "brf_is_mixed_line_endings": brf_doc.is_mixed_line_endings,
                "brf_profile": brf_doc.profile,
                "brf_cell_width": brf_doc.cell_width,
                "brf_line_height": brf_doc.line_height,
            },
        )
        return loaded, None

    return read_text_document(selected_path), None
