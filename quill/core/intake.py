from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from quill.core.document import Document
from quill.core.marks import line_column_for_position


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
    elif source_kind in {"csv", "tsv", "xlsx", "xls"}:
        engine = str(metadata.get("engine", source_kind))
        parts.append(f"{engine} table extract")
    elif source_kind != "text":
        engine = str(metadata.get("engine", source_kind))
        parts.append(f"{engine} extract")
    if metadata.get("ocr_used"):
        parts.append("OCR used")
    return ". ".join(parts) + "."


def build_intake_report(document: Document) -> str:
    metadata = document.source_metadata
    lines = [f"Document intake report for {document.name}", ""]
    lines.append(f"Format: {metadata.get('source_kind', 'text')}")
    lines.append(f"Engine: {metadata.get('engine', 'plain text')}")
    if document.path is not None:
        lines.append(f"Path: {document.path}")
        writable = document.path.exists() and _is_writable(document.path)
        lines.append(f"Original writable: {'yes' if writable else 'no'}")
    if "page_count" in metadata:
        lines.append(f"Pages: {metadata.get('page_count', 0)}")
    if "extracted_pages" in metadata:
        lines.append(f"Pages with text: {metadata.get('extracted_pages', 0)}")
    if "quality_score" in metadata:
        lines.append(f"Quality score: {metadata.get('quality_score', 0)}/100")
    if metadata.get("ocr_used"):
        lines.append("OCR: yes")
    else:
        lines.append("OCR: no")
    if metadata.get("ai_used"):
        lines.append("AI: yes")
    else:
        lines.append("AI: no")
    if metadata.get("sidecar_path"):
        lines.append(f"Sidecar: {metadata['sidecar_path']}")
    if metadata.get("page_scores"):
        page_scores = metadata["page_scores"]
        if isinstance(page_scores, list):
            low_pages = [
                f"Page {index + 1}: {score}/100"
                for index, score in enumerate(page_scores)
                if isinstance(score, int) and score < 40
            ]
            if low_pages:
                lines.append("")
                lines.append("Low-confidence pages:")
                lines.extend(low_pages)
    return "\n".join(lines).rstrip() + "\n"


def build_extraction_quality_report(document: Document) -> str:
    metadata = document.source_metadata
    if metadata.get("source_kind") != "pdf":
        return "Extraction quality review is available for PDF-derived documents."
    page_scores = metadata.get("page_scores")
    if not isinstance(page_scores, list) or not page_scores:
        return "No per-page extraction scores are available for this document."
    lines = [f"Extraction quality review for {document.name}", ""]
    low_pages = []
    for index, score in enumerate(page_scores, start=1):
        if not isinstance(score, int):
            continue
        if score < 40:
            low_pages.append(f"Page {index}: possible extraction issue ({score}/100)")
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
