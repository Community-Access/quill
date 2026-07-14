"""Tier-1 Pandoc format registry tests (issue #262)."""

from __future__ import annotations

from pathlib import Path

from quill.core import pandoc_formats


def test_tier1_inputs_match_issue_262() -> None:
    expected = {
        "markdown",
        "commonmark",
        "gfm",
        "html",
        "docx",
        "odt",
        "rtf",
        "plain_text",
        "csv",
        "epub",
        "latex",
    }
    assert pandoc_formats.TIER1_INPUTS == frozenset(expected)


def test_tier1_outputs_match_issue_262() -> None:
    expected = {
        "markdown",
        "commonmark",
        "gfm",
        "html",
        "docx",
        "odt",
        "rtf",
        "plain_text",
        "epub",
        "pdf",
    }
    assert pandoc_formats.TIER1_OUTPUTS == frozenset(expected)


def test_pdf_is_export_only() -> None:
    assert "pdf" in pandoc_formats.TIER1_OUTPUTS
    assert "pdf" not in pandoc_formats.TIER1_INPUTS


def test_pandoc_format_for_path_known_extensions() -> None:
    assert pandoc_formats.pandoc_format_for_path(Path("report.docx")) == "docx"
    assert pandoc_formats.pandoc_format_for_path(Path("page.html")) == "html"
    assert pandoc_formats.pandoc_format_for_path(Path("page.htm")) == "html"
    assert pandoc_formats.pandoc_format_for_path(Path("notes.md")) == "markdown"
    assert pandoc_formats.pandoc_format_for_path(Path("book.epub")) == "epub"
    assert pandoc_formats.pandoc_format_for_path(Path("slides.pptx")) is None
    assert pandoc_formats.pandoc_format_for_path(Path("image.png")) is None


def test_pandoc_format_for_path_case_insensitive() -> None:
    assert pandoc_formats.pandoc_format_for_path(Path("REPORT.DOCX")) == "docx"
    assert pandoc_formats.pandoc_format_for_path(Path("Mixed.MD")) == "markdown"


def test_pandoc_format_for_path_string_input() -> None:
    """The helper accepts strings as well as Path objects."""

    assert pandoc_formats.pandoc_format_for_path("file.html") == "html"
    assert pandoc_formats.pandoc_format_for_path("no_extension") is None


def test_get_format_round_trip() -> None:
    fmt = pandoc_formats.get_format("docx")
    assert fmt is not None
    assert fmt.display_name == "Word Document"
    assert ".docx" in fmt.extensions


def test_get_format_unknown_returns_none() -> None:
    assert pandoc_formats.get_format("not-a-format") is None


def test_extensions_for_known() -> None:
    assert ".html" in pandoc_formats.extensions_for("html")
    assert ".htm" in pandoc_formats.extensions_for("html")


def test_extensions_for_unknown() -> None:
    assert pandoc_formats.extensions_for("not-a-format") == frozenset()


def test_formats_for_direction_returns_ordered_subset() -> None:
    inputs = pandoc_formats.formats_for_direction("import")
    outputs = pandoc_formats.formats_for_direction("export")
    # Every input is in the input set; every output is in the output set.
    for fmt in inputs:
        assert fmt.name in pandoc_formats.TIER1_INPUTS
    for fmt in outputs:
        assert fmt.name in pandoc_formats.TIER1_OUTPUTS
    # PDF is in outputs only.
    assert any(f.name == "pdf" for f in outputs)
    assert not any(f.name == "pdf" for f in inputs)


def test_formats_for_direction_rejects_unknown() -> None:
    import pytest

    with pytest.raises(ValueError):
        pandoc_formats.formats_for_direction("sideways")


def test_is_editable_in_quill() -> None:
    assert pandoc_formats.is_editable_in_quill("markdown") is True
    assert pandoc_formats.is_editable_in_quill("html") is True
    assert pandoc_formats.is_editable_in_quill("plain_text") is True
    # CSV is an import-only format; Pandoc does not write CSV.
    assert pandoc_formats.is_editable_in_quill("csv") is False
    # Non-editable outputs:
    assert pandoc_formats.is_editable_in_quill("pdf") is False
    assert pandoc_formats.is_editable_in_quill("docx") is False
    assert pandoc_formats.is_editable_in_quill("epub") is False
    assert pandoc_formats.is_editable_in_quill("odt") is False
    assert pandoc_formats.is_editable_in_quill("rtf") is False
    assert pandoc_formats.is_editable_in_quill("latex") is False
    # Inputs that are not Tier-1 outputs are not editable:
    assert pandoc_formats.is_editable_in_quill("not-a-format") is False


def test_probe_pandoc_version_returns_string_or_none() -> None:
    """The probe is best-effort. We only assert it returns str | None and does not raise."""

    result = pandoc_formats.probe_pandoc_version()
    assert result is None or isinstance(result, str)
