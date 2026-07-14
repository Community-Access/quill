"""Tests for the broader Convert File format catalogue."""

from __future__ import annotations

from quill.core import convert_formats, pandoc_formats


def test_primary_extension_is_canonical_not_alphabetical() -> None:
    # Regression: export defaulted to the alphabetically-first extension
    # (.markdown, .htm); it must use the canonical one instead.
    assert pandoc_formats.primary_extension_for("markdown") == ".md"
    assert pandoc_formats.primary_extension_for("html") == ".html"
    assert pandoc_formats.primary_extension_for("docx") == ".docx"
    assert pandoc_formats.primary_extension_for("not-a-format") is None
    # The primary extension is always a member of the format's extension set.
    for fmt in pandoc_formats.all_formats():
        assert fmt.primary_extension in fmt.extensions


def test_curated_outputs_have_extensions() -> None:
    for fmt in convert_formats.CURATED_OUTPUTS:
        assert fmt.extension.startswith(".")
        assert fmt.token
        assert fmt.label


def test_extension_for_known_and_unknown() -> None:
    assert convert_formats.extension_for("gfm") == ".md"
    assert convert_formats.extension_for("docx") == ".docx"
    # Runtime long-tail mapping.
    assert convert_formats.extension_for("epub3") == ".epub"
    # Unknown alnum token guesses ".token".
    assert convert_formats.extension_for("rst") == ".rst"
    # Unknown non-alnum falls back to .txt.
    assert convert_formats.extension_for("weird-token") == ".txt"


def test_label_for_falls_back_to_token() -> None:
    assert convert_formats.label_for("gfm") == "Markdown (GitHub-Flavored)"
    assert convert_formats.label_for("totally_unknown") == "totally_unknown"


def test_is_text_output() -> None:
    assert convert_formats.is_text_output("gfm") is True
    assert convert_formats.is_text_output("html5") is True
    assert convert_formats.is_text_output("plain") is True
    assert convert_formats.is_text_output("docx") is False
    assert convert_formats.is_text_output("pdf") is False
    assert convert_formats.is_text_output("epub") is False


def test_reader_for_path() -> None:
    assert convert_formats.reader_for_path("notes.md") == "markdown"
    assert convert_formats.reader_for_path("report.docx") == "docx"
    assert convert_formats.reader_for_path("page.html") == "html"
    # Unknown extension -> empty (Pandoc auto-detect).
    assert convert_formats.reader_for_path("mystery.xyz") == ""
    assert convert_formats.reader_for_path("no_extension") == ""


def test_input_wildcard_is_wellformed() -> None:
    wildcard = convert_formats.input_wildcard()
    assert "Supported documents" in wildcard
    assert "All files (*.*)|*.*" in wildcard
    assert wildcard.count("|") >= 3
