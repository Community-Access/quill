from pathlib import Path

from quill.core.document import Document
from quill.io.rtf import (
    markdown_to_rtf,
    read_rtf_document,
    rtf_to_markdown,
    write_rtf_document,
)


def test_write_produces_valid_rtf_header() -> None:
    rtf = markdown_to_rtf("hello")
    assert rtf.startswith("{\\rtf1\\ansi")
    assert rtf.rstrip().endswith("}")
    assert "hello" in rtf


def test_read_simple_rtf() -> None:
    rtf = "{\\rtf1\\ansi{\\fonttbl{\\f0 Calibri;}}\\pard Plain text here\\par}"
    assert rtf_to_markdown(rtf) == "Plain text here"


def test_read_bold_and_italic() -> None:
    rtf = "{\\rtf1\\ansi\\pard This is {\\b bold} and {\\i italic}\\par}"
    assert rtf_to_markdown(rtf) == "This is **bold** and *italic*"


def test_round_trip_formatting() -> None:
    markdown = "\n".join([
        "# Heading One",
        "",
        "A paragraph with **bold** and *italic* words.",
        "- first item",
        "- second item",
        "See [QUILL](https://example.com/quill) for more.",
    ])
    restored = rtf_to_markdown(markdown_to_rtf(markdown))
    assert restored == markdown


def test_round_trip_heading_levels() -> None:
    markdown = "## Level Two\n### Level Three"
    assert rtf_to_markdown(markdown_to_rtf(markdown)) == markdown


def test_read_write_document(tmp_path: Path) -> None:
    source = tmp_path / "sample.rtf"
    write_rtf_document(Document(text="# Title\n**strong**"), source)
    document = read_rtf_document(source)
    assert document.text == "# Title\n**strong**"
    assert document.source_metadata["source_kind"] == "rtf"
    assert document.path == source


def test_span_emits_font_and_color_tables() -> None:
    rtf = markdown_to_rtf('[Hi]{font-family="Arial" font-size="14" color="#C00000"}')
    assert "{\\f1 Arial;}" in rtf
    assert "\\red192\\green0\\blue0;" in rtf
    # 14pt -> \fs28 (RTF font size is in half-points); color index 1 -> \cf1.
    assert "\\f1\\fs28\\cf1" in rtf


def test_span_underline_and_highlight() -> None:
    rtf = markdown_to_rtf('[Hi]{underline highlight="yellow"}')
    assert "\\ul Hi\\ulnone" in rtf
    assert "\\highlight" in rtf


def test_alignment_control_words() -> None:
    rtf = markdown_to_rtf('::: {align="center"}\nhi\n:::')
    assert "\\pard\\qc hi\\par" in rtf


def test_plain_subset_writer_unchanged() -> None:
    # Documents without hidden codes keep the original Calibri-only header and
    # carry no color table, so existing readers round-trip unaffected.
    rtf = markdown_to_rtf("plain text")
    assert rtf.startswith("{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Calibri;}}")
    assert "\\colortbl" not in rtf


def test_strike_super_sub_control_words() -> None:
    rtf = markdown_to_rtf("[a]{strike} [b]{superscript} [c]{subscript}")
    assert "\\strike a" in rtf
    assert "\\super b" in rtf
    assert "\\sub c" in rtf


def test_block_control_words_for_spacing_and_indent() -> None:
    rtf = markdown_to_rtf(
        '::: {line-spacing="2" space-before="12" indent="36" first-line-indent="18"}\nx\n:::'
    )
    assert "\\sl480\\slmult1" in rtf  # double spacing
    assert "\\sb240" in rtf  # 12pt before -> 240 twips
    assert "\\li720" in rtf  # 36pt indent -> 720 twips
    assert "\\fi360" in rtf  # 18pt first-line -> 360 twips


def test_page_break_emits_page_control() -> None:
    assert "\\page" in markdown_to_rtf("a\n::: pagebreak\nb")


def test_reader_recovers_underline_and_color_via_colortbl() -> None:
    rtf = r"{\rtf1\ansi{\colortbl;\red255\green0\blue0;}\pard {\cf1\ul Hot}\par}"
    assert rtf_to_markdown(rtf) == '[Hot]{color="#FF0000" underline}'


def test_reader_recovers_strike_super_sub() -> None:
    rtf = r"{\rtf1\ansi\pard {\strike x}{\super y}{\sub z}\par}"
    assert rtf_to_markdown(rtf) == "[x]{strike}[y]{superscript}[z]{subscript}"


def test_write_then_read_underline_color_round_trips() -> None:
    md = '[Hot]{color="#FF0000" underline} text'
    assert rtf_to_markdown(markdown_to_rtf(md)) == md


def test_cyrillic_rtf_decoded_with_ansicpg(tmp_path: Path) -> None:
    # M-13: an RTF file declaring \ansicpg1251 (Cyrillic) must be decoded as
    # cp1251, not cp1252. The Cyrillic word for "hello" in cp1251 is bytes
    # \xef\xf0\xe8\xe2\xe5\xf2 which decodes correctly as "привет".
    cyrillic_word_cp1251 = "привет".encode("cp1251")
    # Build a minimal RTF header with \ansicpg1251 and embed the word.
    rtf_bytes = b"{\\rtf1\\ansi\\ansicpg1251\\deff0\\pard " + cyrillic_word_cp1251 + b"\\par}"
    rtf_file = tmp_path / "cyrillic.rtf"
    rtf_file.write_bytes(rtf_bytes)

    from quill.io.rtf import _detect_rtf_encoding

    assert _detect_rtf_encoding(rtf_file) == "cp1251"
