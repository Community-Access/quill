from __future__ import annotations

from pathlib import Path

from quill.core.document import Document
from quill.core.intake import (
    build_bad_extraction_package,
    build_context_help,
    build_extraction_quality_report,
    build_intake_report,
    build_intake_summary,
    build_source_reference,
)


def test_build_intake_summary_for_pdf() -> None:
    document = Document(
        path=Path("sample.pdf"),
        source_metadata={
            "source_kind": "pdf",
            "engine": "pypdf",
            "quality_score": 72,
            "page_count": 3,
        },
    )
    summary = build_intake_summary(document)
    assert "sample.pdf" in summary
    assert "3 pages" in summary
    assert "quality 72/100" in summary


def test_build_intake_summary_reports_low_confidence_instead_of_prepending_it() -> None:
    # #1279: the low-confidence/OCR advice used to be written into the document
    # text itself. It now travels with the open announcement.
    document = Document(
        path=Path("scan.pdf"),
        source_metadata={
            "source_kind": "pdf",
            "engine": "pdfplumber",
            "quality_score": 12,
            "page_count": 2,
        },
    )
    summary = build_intake_summary(document)
    assert "low-confidence extraction" in summary
    assert "OCR" in summary


def test_build_intake_report_notes_low_confidence_extraction() -> None:
    document = Document(
        path=Path("scan.pdf"),
        source_metadata={"source_kind": "pdf", "engine": "pdfplumber", "quality_score": 12},
    )
    report = build_intake_report(document)
    assert "Quality score: 12/100" in report
    assert "low-confidence extraction" in report


def test_build_intake_surfaces_missing_extraction_pack() -> None:
    # #1279: when the optional PDF/Office extraction pack is absent the read
    # still succeeds on the built-in fallback, so the pointer to the one-click
    # download rides along with the open announcement and the intake report.
    document = Document(
        path=Path("report.docx"),
        source_metadata={
            "source_kind": "docx",
            "engine": "docx",
            "quality_score": 100,
            "extraction_pack_missing": True,
        },
    )
    summary = build_intake_summary(document)
    report = build_intake_report(document)
    assert "Download Optional Components" in summary
    assert "Download Optional Components" in report


def test_build_intake_summary_omits_pack_hint_when_pack_is_present() -> None:
    document = Document(
        path=Path("report.docx"),
        source_metadata={"source_kind": "docx", "engine": "markitdown", "quality_score": 90},
    )
    assert "Download Optional Components" not in build_intake_summary(document)


def test_build_intake_summary_for_spreadsheet_mentions_table_extract() -> None:
    document = Document(
        path=Path("sample.xlsx"),
        source_metadata={
            "source_kind": "xlsx",
            "engine": "markitdown",
            "quality_score": 90,
        },
    )
    summary = build_intake_summary(document)
    assert "table extract" in summary
    assert "markitdown" in summary


def test_build_intake_report_lists_quality() -> None:
    document = Document(
        path=Path("sample.pdf"),
        source_metadata={
            "source_kind": "pdf",
            "engine": "pdfplumber",
            "quality_score": 35,
            "page_count": 2,
            "extracted_pages": 1,
            "page_scores": [35, 80],
        },
    )
    report = build_intake_report(document)
    assert "Format: pdf" in report
    assert "Low-confidence pages:" in report


def test_build_source_reference_for_pdf() -> None:
    document = Document(
        path=Path("sample.pdf"),
        source_metadata={
            "source_kind": "pdf",
            "engine": "pypdf",
            "quality_score": 72,
            "page_count": 4,
        },
    )
    source = build_source_reference(document, cursor_position=40, text="alpha beta gamma delta")
    assert "sample.pdf" in source
    assert "page" in source


def test_build_source_reference_for_legacy_office_documents() -> None:
    doc = Document(path=Path("sample.doc"), source_metadata={"source_kind": "doc"})
    ppt = Document(path=Path("sample.ppt"), source_metadata={"source_kind": "ppt"})

    doc_source = build_source_reference(doc, cursor_position=12, text="alpha beta")
    ppt_source = build_source_reference(ppt, cursor_position=12, text="alpha beta")

    assert "sample.doc" in doc_source
    assert "sample.ppt" in ppt_source
    assert "line" in doc_source
    assert "line" in ppt_source


def test_build_extraction_quality_report_for_pdf() -> None:
    document = Document(
        path=Path("sample.pdf"),
        source_metadata={"source_kind": "pdf", "page_scores": [80, 20, 90]},
    )
    report = build_extraction_quality_report(document)
    assert "Page 2" in report


def test_build_bad_extraction_package_omits_content() -> None:
    document = Document(
        text="hello", path=Path("sample.pdf"), source_metadata={"source_kind": "pdf"}
    )
    settings = type(
        "Settings",
        (),
        {
            "theme": "dark",
            "soft_wrap": False,
            "spellcheck_as_you_type": True,
            "status_bar_order": ["message"],
            "status_bar_hidden": [],
        },
    )()
    package = build_bad_extraction_package(document, settings, "1.0.0")
    assert package["document"]["path"] == str(Path("sample.pdf"))
    assert "text" not in package["document"]


def test_build_context_help_switches_on_source_kind() -> None:
    document = Document(path=Path("sample.pdf"), source_metadata={"source_kind": "pdf"})
    help_text = build_context_help(document, has_selection=True)
    assert (
        "Review Extraction Quality" in help_text or "review extraction quality" in help_text.lower()
    )


def test_build_context_help_handles_legacy_office_documents() -> None:
    document = Document(path=Path("sample.doc"), source_metadata={"source_kind": "doc"})
    help_text = build_context_help(document, has_selection=False)
    assert "compare with file" in help_text.lower()
