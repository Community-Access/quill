from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from quill.core.document import Document
from quill.core.marks import line_column_for_position
from quill.core.pdf_open import doubtful_pages_sentence

#: Below this extraction score the PDF text is treated as low confidence.
_LOW_CONFIDENCE_SCORE = 50

#: Advice for a low-confidence extraction. Reported by the open announcement and
#: the intake report; never written into the document text (#1279).
LOW_CONFIDENCE_HINT = "low-confidence extraction -- OCR (File > Import > OCR) may read it better."

#: Reported when a Word/PowerPoint/Excel/PDF read fell back to the built-in
#: extractor because the optional "PDF and Office text extraction" pack is not
#: installed. The fallback works, but MarkItDown reads these formats far better,
#: and the pack is a one-click download -- so the pointer belongs where the user
#: just felt the difference (#1279).
EXTRACTION_PACK_HINT = (
    "for better Word, PowerPoint, Excel, and PDF text, install PDF and Office "
    "text extraction from Help > Download Optional Components."
)


def build_intake_summary(document: Document, cursor_position: int | None = None) -> str:
    metadata = document.source_metadata
    source_kind = str(metadata.get("source_kind", "text"))
    source_name = document.name
    parts = [f"Opened {source_name}"]
    if source_kind == "pdf":
        page_count = int(metadata.get("page_count", 0) or 0)  # type: ignore[call-overload]
        engine = str(metadata.get("engine", "local"))
        quality = int(metadata.get("quality_score", 0) or 0)  # type: ignore[call-overload]
        if page_count:
            parts.append(f"{page_count} pages")
        parts.append(f"extracted by {engine}")
        parts.append(f"quality {quality}/100")
        # #1279: this warning used to be prepended to the document text itself.
        # It belongs in the open announcement and the intake report, not in the
        # first line of the user's file.
        if quality < _LOW_CONFIDENCE_SCORE:
            parts.append(LOW_CONFIDENCE_HINT.rstrip("."))
        doubtful = doubtful_pages_sentence(_doubtful_pages(metadata))
        if doubtful:
            parts.append(doubtful.rstrip("."))
    elif metadata.get("reader"):
        # An Office file (quill.io.office_text, 2026-10-16): who read it, in
        # words, and its sheets or slides -- not an engine's internal name.
        parts.append(f"read by {metadata['reader']}")
        if metadata.get("units"):
            parts.append(str(metadata["units"]))
        if metadata.get("extraction_notes"):
            parts.append("part of it was too large and was cut short; the intake report says where")
    elif source_kind in {"csv", "tsv", "xlsx", "xls"}:
        engine = str(metadata.get("engine", source_kind))
        parts.append(f"{engine} table extract")
    elif source_kind != "text":
        engine = str(metadata.get("engine", source_kind))
        parts.append(f"{engine} extract")
    if metadata.get("ocr_used"):
        parts.append("OCR used")
    if metadata.get("extraction_pack_missing"):
        parts.append(EXTRACTION_PACK_HINT.rstrip("."))
    return ". ".join(parts) + "."


def build_intake_report(document: Document) -> str:
    metadata = document.source_metadata
    lines = [f"Document intake report for {document.name}", ""]
    lines.append(f"Format: {metadata.get('source_kind', 'text')}")
    lines.append(f"Engine: {metadata.get('engine', 'plain text')}")
    if metadata.get("reader"):
        lines.append(f"Read by: {metadata['reader']}")
    if metadata.get("units"):
        lines.append(f"Contents: {metadata['units']}")
    if metadata.get("markitdown_failure"):
        lines.append(f"MarkItDown: not used. {metadata['markitdown_failure']}")
    notes = metadata.get("extraction_notes")
    for note in notes if isinstance(notes, list) else []:
        lines.append(f"Note: {note}")
    if document.path is not None:
        lines.append(f"Path: {document.path}")
        writable = document.path.exists() and _is_writable(document.path)
        lines.append(f"Original writable: {'yes' if writable else 'no'}")
    if "page_count" in metadata:
        lines.append(f"Pages: {metadata.get('page_count', 0)}")
    if "extracted_pages" in metadata:
        lines.append(f"Pages with text: {metadata.get('extracted_pages', 0)}")
    if "quality_score" in metadata:
        quality = int(metadata.get("quality_score", 0) or 0)  # type: ignore[call-overload]
        lines.append(f"Quality score: {quality}/100")
        if quality < _LOW_CONFIDENCE_SCORE:
            lines.append(f"Note: {LOW_CONFIDENCE_HINT}")
    if metadata.get("ocr_used"):
        lines.append("OCR: yes")
    else:
        lines.append("OCR: no")
    if metadata.get("ai_used"):
        lines.append("AI: yes")
    else:
        lines.append("AI: no")
    if metadata.get("extraction_pack_missing"):
        lines.append(f"Note: {EXTRACTION_PACK_HINT}")
    if metadata.get("sidecar_path"):
        lines.append(f"Sidecar: {metadata['sidecar_path']}")
    chosen = _engines_used(metadata)
    if chosen:
        lines.append(f"Text chosen per page: {chosen}")
    doubtful = _doubtful_lines(metadata)
    if doubtful:
        lines.append("")
        lines.append("Pages that may read poorly:")
        lines.extend(doubtful)
    return "\n".join(lines).rstrip() + "\n"


def _page_list(metadata: dict[str, object], key: str) -> list[Any]:
    value = metadata.get(key)
    return list(value) if isinstance(value, (list, tuple)) else []


def _doubtful_pages(metadata: dict[str, object]) -> list[int]:
    """The shared rule (``quill.io.pdf.doubtful_pages``) over stored metadata."""
    from quill.io.pdf import doubtful_pages

    scores = [int(s) if isinstance(s, int) else 100 for s in _page_list(metadata, "page_scores")]
    engines = [str(e) for e in _page_list(metadata, "page_engines")]
    unreadable = [
        int(n) if isinstance(n, int) else 0 for n in _page_list(metadata, "page_unreadable")
    ]
    return doubtful_pages(scores, engines, unreadable)


def _engines_used(metadata: dict[str, object]) -> str:
    """``"pdfplumber (10 pages), pypdf (2 pages)"``: whose reading each page kept."""
    counts: dict[str, int] = {}
    for engine in _page_list(metadata, "page_engines"):
        if engine in {"blank", "image-only", "failed"}:
            continue
        counts[str(engine)] = counts.get(str(engine), 0) + 1
    return ", ".join(
        f"{engine} ({count} page{'s' if count != 1 else ''})" for engine, count in counts.items()
    )


def _doubtful_lines(metadata: dict[str, object]) -> list[str]:
    """One plain line per doubtful page, saying why."""
    scores = _page_list(metadata, "page_scores")
    engines = _page_list(metadata, "page_engines")
    unreadable = _page_list(metadata, "page_unreadable")
    lines = []
    for number in _doubtful_pages(metadata):
        engine = engines[number - 1] if number <= len(engines) else ""
        count = unreadable[number - 1] if number <= len(unreadable) else 0
        score = scores[number - 1] if number <= len(scores) else 0
        if engine == "image-only":
            lines.append(f"Page {number}: a picture with no text; OCR may read it")
        elif engine == "failed":
            lines.append(f"Page {number}: could not be read")
        elif isinstance(count, int) and count:
            lines.append(
                f"Page {number}: {count} character{'s' if count != 1 else ''} could not be "
                f"read ({score}/100)"
            )
        else:
            lines.append(f"Page {number}: possible extraction issue ({score}/100)")
    return lines


def build_extraction_quality_report(document: Document) -> str:
    metadata = document.source_metadata
    if metadata.get("source_kind") != "pdf":
        return "Extraction quality review is available for PDF-derived documents."
    page_scores = metadata.get("page_scores")
    if not isinstance(page_scores, list) or not page_scores:
        return "No per-page extraction scores are available for this document."
    lines = [f"Extraction quality review for {document.name}", ""]
    chosen = _engines_used(metadata)
    if chosen:
        lines.append(f"Text chosen per page: {chosen}")
        lines.append("")
    low_pages = _doubtful_lines(metadata)
    if low_pages:
        lines.append("Warnings:")
        lines.extend(low_pages)
    else:
        lines.append("No low-confidence pages detected.")
    return "\n".join(lines).rstrip() + "\n"


def build_context_help(document: Document, has_selection: bool) -> str:
    metadata = document.source_metadata
    source_kind = str(metadata.get("source_kind", "text"))
    lines = [f"What can I do here in {document.name}?", ""]
    if source_kind == "pdf":
        lines.append(
            "Available actions: intake report, review extraction quality, copy with source, "
            "go to page, find, compare with file."
        )
    elif source_kind in {"doc", "docx", "docm", "ppt", "pptx", "epub", "odt", "rtf", "sqlite"}:
        lines.append(
            "Available actions: intake report, copy with source, word count, find, "
            "compare with file."
        )
    else:
        lines.append(
            "Available actions: copy with source, find, word count, command palette, "
            "status bar review."
        )
    if has_selection:
        lines.append(
            "Selection actions: copy, copy with source, transform, comment, indent, case change."
        )
    return "\n".join(lines).rstrip() + "\n"


def build_bad_extraction_package(
    document: Document, settings: object, version: str
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": version,
        "document": {
            "name": document.name,
            "path": str(document.path) if document.path is not None else None,
            "encoding": document.encoding,
            "line_ending": document.line_ending,
            "source_metadata": _json_safe(document.source_metadata),
        },
        "settings": {
            "theme": getattr(settings, "theme", "system"),
            "soft_wrap": getattr(settings, "soft_wrap", True),
            "spellcheck_as_you_type": getattr(settings, "spellcheck_as_you_type", False),
            "status_bar_order": list(getattr(settings, "status_bar_order", [])),
            "status_bar_hidden": list(getattr(settings, "status_bar_hidden", [])),
        },
    }
    return payload


def build_source_reference(document: Document, cursor_position: int, text: str) -> str:
    metadata = document.source_metadata
    path_name = document.name
    line, column = line_column_for_position(text, cursor_position)
    source_kind = str(metadata.get("source_kind", "text"))
    if source_kind == "pdf":
        page_number = _estimate_pdf_page(metadata, cursor_position, len(text))
        engine = str(metadata.get("engine", "local"))
        quality = int(metadata.get("quality_score", 0) or 0)  # type: ignore[call-overload]
        return (
            f"Source: {path_name}, page {page_number}, line {line}, column {column}, "
            f"extracted by {engine} ({quality}/100)."
        )
    if source_kind in {"doc", "docx", "docm", "ppt", "pptx", "epub", "odt", "rtf", "sqlite"}:
        return f"Source: {path_name}, line {line}, column {column}."
    return f"Source: {path_name}, line {line}, column {column}."


def _estimate_pdf_page(metadata: dict[str, Any], cursor_position: int, text_length: int) -> int:
    page_count = int(metadata.get("page_count", 0) or 0)
    if page_count <= 0 or text_length <= 0:
        return 1
    ratio = min(1.0, max(0.0, cursor_position / max(text_length, 1)))
    page = int(ratio * page_count) + 1
    return max(1, min(page, page_count))


def _is_writable(path: Path) -> bool:
    return path.exists() and os.access(path, os.W_OK)


def _json_safe(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
